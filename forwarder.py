import os
import time
import sys
import socket
import imaplib
import logging
from datetime import datetime
from imap_tools import MailBox, AND
import smtplib
from email.message import EmailMessage

# Setup logging to both console and file
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FILE = os.getenv('LOG_FILE', '/app/logs/forwarder.log')

# Ensure log directory exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
IMAP_SERVER = 'mail.mailo.com'
IMAP_PORT = 993
IMAP_USER = os.getenv('IMAP_USER')
IMAP_PASS = os.getenv('IMAP_PASS')

SMTP_SERVER = 'mail.mailo.com'
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))  # 587 for STARTTLS, 465 for SSL
SMTP_USER = os.getenv('IMAP_USER')  # Same as IMAP credentials for Mailo SMTP
SMTP_PASS = os.getenv('IMAP_PASS')  # Same as IMAP password for Mailo SMTP
FORWARD_TO = os.getenv('FORWARD_TO')

CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 300))  # 5 minutes default
SMTP_TIMEOUT = int(os.getenv('SMTP_TIMEOUT', 30))  # SMTP connection timeout in seconds
DELETE_AFTER_FORWARD = os.getenv('DELETE_AFTER_FORWARD', 'false').lower() == 'true'  # Delete original after forwarding


def _sanitize_header(value: str) -> str:
    """Strip CR/LF characters that are illegal in email header values."""
    return value.replace('\r', ' ').replace('\n', ' ').strip()


def forward_email(msg, mailbox):
    """Forward a single email via SMTP with retry logic."""
    max_retries = 2
    subject = _sanitize_header(msg.subject or "")
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Forwarding email: '{subject}' from {msg.from_} (attempt {attempt}/{max_retries})")

            # Create forwarded message
            # Use authenticated Mailo address as From to prevent SMTP rejection
            forward_msg = EmailMessage()
            forward_msg['From'] = SMTP_USER  # Must be the authenticated Mailo address
            forward_msg['To'] = FORWARD_TO
            forward_msg['Subject'] = f"Fwd: {subject}"
            forward_msg['Reply-To'] = _sanitize_header(msg.from_ or "")
            forward_msg['X-Original-From'] = _sanitize_header(msg.from_ or "")

            # Copy body and attachments
            if msg.html:
                forward_msg.add_alternative(msg.html, subtype='html')
            else:
                forward_msg.set_content(msg.text or "")

            # Add attachments if any
            attachment_count = len(msg.attachments)
            if attachment_count > 0:
                logger.debug(f"Processing {attachment_count} attachment(s)")
            for att in msg.attachments:
                # Parse content_type (e.g., "application/pdf") into maintype and subtype
                content_type = getattr(att, 'content_type', 'application/octet-stream')
                if '/' in content_type:
                    maintype, subtype = content_type.split('/', 1)
                else:
                    maintype, subtype = 'application', 'octet-stream'
                forward_msg.add_attachment(att.payload, maintype=maintype, subtype=subtype, filename=att.filename)

            # Send via Mailo SMTP with timeout
            logger.debug(f"Connecting to SMTP server {SMTP_SERVER}:{SMTP_PORT} (timeout={SMTP_TIMEOUT}s)")
            if SMTP_PORT == 465:
                # SSL connection (implicit TLS)
                with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
                    server.login(SMTP_USER, SMTP_PASS)
                    server.send_message(forward_msg)
            else:
                # STARTTLS connection (explicit TLS on port 587)
                with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
                    server.starttls()
                    server.login(SMTP_USER, SMTP_PASS)
                    server.send_message(forward_msg)

            logger.info(f"✅ Successfully forwarded: '{subject}' | From: {msg.from_}")
            return True
        except (socket.timeout, TimeoutError) as e:
            logger.warning(f"⏱️ SMTP timeout on attempt {attempt}: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying in 5 seconds...")
                time.sleep(5)
                continue
            else:
                logger.error(f"❌ SMTP connection failed after {max_retries} attempts")
                return False
        except smtplib.SMTPAuthenticationError as e:
            # 535 "Currently not available" is a transient server-side error, not a bad password
            logger.warning(f"⚠️ SMTP auth error on attempt {attempt} (code {e.smtp_code}): {e.smtp_error}")
            if attempt < max_retries:
                logger.info(f"Retrying in 30 seconds...")
                time.sleep(30)
                continue
            else:
                logger.error(f"❌ Failed to forward '{subject}' after {max_retries} attempts: SMTP auth error {e.smtp_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to forward '{subject}': {e}", exc_info=True)
            return False
    
    return False


def main():
    logger.info(f"🚀 Mailo → Gmail forwarder started")
    logger.info(f"Configuration: IMAP={IMAP_SERVER}:{IMAP_PORT}, SMTP={SMTP_SERVER}:{SMTP_PORT}, interval={CHECK_INTERVAL}s")
    logger.info(f"Forwarding from {IMAP_USER} to {FORWARD_TO}")
    logger.info(f"Delete after forward: {DELETE_AFTER_FORWARD}")

    while True:
        try:
            logger.info(f"⏳ Checking for new emails...")
            logger.debug(f"Connecting to IMAP server {IMAP_SERVER}:{IMAP_PORT}")
            with MailBox(IMAP_SERVER, IMAP_PORT).login(IMAP_USER, IMAP_PASS, 'INBOX') as mailbox:
                logger.debug("IMAP connection successful")
                
                # Fetch only unseen messages
                messages = list(mailbox.fetch(AND(seen=False), mark_seen=False))
                message_count = len(messages)
                
                if message_count > 0:
                    logger.info(f"📧 Found {message_count} unread message(s)")
                else:
                    logger.info("✓ No unread messages")
                
                for msg in messages:
                    if forward_email(msg, mailbox):
                        # Mark as read on Mailo
                        mailbox.flag(msg.uid, ['\\Seen'], True)
                        logger.debug(f"Marked message as read: UID {msg.uid}")
                        
                        # Optionally delete original after forwarding
                        if DELETE_AFTER_FORWARD:
                            try:
                                # Mark as deleted and then delete (some servers need both)
                                mailbox.flag(msg.uid, ['\\Deleted'], True)
                                mailbox.delete(msg.uid)
                                # Try expunge to permanently remove (may not be supported by all servers)
                                try:
                                    mailbox.client.expunge()
                                except Exception as e:
                                    logger.debug(f"Expunge not supported or failed: {e}")
                                logger.info(f"🗑️ Deleted original message: UID {msg.uid}")
                            except Exception as e:
                                logger.warning(f"⚠️ Failed to delete message UID {msg.uid}: {e}")
                    else:
                        # If forwarding failed, don't mark as read so we can retry next cycle
                        logger.warning(f"⚠️ Keeping message unread due to forwarding failure: '{msg.subject or ''}'")

        except imaplib.IMAP4.abort as e:
            # IMAP session closed by server (typically because SMTP retries kept the
            # connection idle too long). Emails were already processed; log as warning.
            logger.warning(f"⚠️ IMAP session dropped during logout (server closed idle connection): {e}")
        except Exception as e:
            logger.error(f"❌ Connection error: {e}", exc_info=True)

        logger.debug(f"Sleeping for {CHECK_INTERVAL} seconds...")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    if not all([IMAP_USER, IMAP_PASS, FORWARD_TO]):
        logger.error("Missing required environment variables: IMAP_USER, IMAP_PASS, FORWARD_TO")
        raise ValueError("Missing required environment variables: IMAP_USER, IMAP_PASS, FORWARD_TO")
    main()
