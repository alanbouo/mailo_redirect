import os
import time
import sys
import logging
from datetime import datetime
from imap_tools import MailBoxTls, AND
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
SMTP_PORT = 465
SMTP_USER = os.getenv('IMAP_USER')  # Same as IMAP credentials for Mailo SMTP
SMTP_PASS = os.getenv('IMAP_PASS')  # Same as IMAP password for Mailo SMTP
FORWARD_TO = os.getenv('FORWARD_TO')

CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 300))  # 5 minutes default


def forward_email(msg):
    try:
        logger.info(f"Forwarding email: '{msg.subject}' from {msg.from_}")
        
        # Create forwarded message preserving original content
        forward_msg = EmailMessage()
        forward_msg['From'] = msg.from_
        forward_msg['To'] = FORWARD_TO
        forward_msg['Subject'] = f"Fwd: {msg.subject}"
        forward_msg['X-Forwarded-From'] = IMAP_USER
        forward_msg['X-Forwarded-To'] = FORWARD_TO

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
            forward_msg.add_attachment(att.payload, maintype=att.maintype, subtype=att.subtype, filename=att.filename)

        # Send via Mailo SMTP
        logger.debug(f"Connecting to SMTP server {SMTP_SERVER}:{SMTP_PORT}")
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(forward_msg)

        logger.info(f"✅ Successfully forwarded: '{msg.subject}' | From: {msg.from_}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to forward '{msg.subject}': {e}", exc_info=True)
        return False


def main():
    logger.info(f"🚀 Mailo → Gmail forwarder started")
    logger.info(f"Configuration: IMAP={IMAP_SERVER}:{IMAP_PORT}, SMTP={SMTP_SERVER}:{SMTP_PORT}, interval={CHECK_INTERVAL}s")
    logger.info(f"Forwarding from {IMAP_USER} to {FORWARD_TO}")

    while True:
        try:
            logger.debug(f"Connecting to IMAP server {IMAP_SERVER}:{IMAP_PORT}")
            with MailBoxTls(IMAP_SERVER, IMAP_PORT).login(IMAP_USER, IMAP_PASS, 'INBOX') as mailbox:
                logger.debug("IMAP connection successful")
                
                # Fetch only unseen messages
                messages = list(mailbox.fetch(AND(seen=False), mark_seen=False))
                message_count = len(messages)
                
                if message_count > 0:
                    logger.info(f"📧 Found {message_count} unread message(s)")
                else:
                    logger.debug("No unread messages found")
                
                for msg in messages:
                    if forward_email(msg):
                        # Mark as read on Mailo
                        mailbox.flag(msg.uid, ['\\Seen'], True)
                        logger.debug(f"Marked message as read: UID {msg.uid}")
                        # Optional: mailbox.delete(msg.uid)  # or move to another folder

        except Exception as e:
            logger.error(f"❌ Connection error: {e}", exc_info=True)

        logger.debug(f"Sleeping for {CHECK_INTERVAL} seconds...")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    if not all([IMAP_USER, IMAP_PASS, FORWARD_TO]):
        logger.error("Missing required environment variables: IMAP_USER, IMAP_PASS, FORWARD_TO")
        raise ValueError("Missing required environment variables: IMAP_USER, IMAP_PASS, FORWARD_TO")
    main()
