import os
import time
from datetime import datetime
from imap_tools import MailBox, AND
import smtplib
from email.message import EmailMessage

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
        for att in msg.attachments:
            forward_msg.add_attachment(att.payload, maintype=att.maintype, subtype=att.subtype, filename=att.filename)

        # Send via Gmail
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(forward_msg)

        print(f"[{datetime.now()}] ✅ Forwarded: {msg.subject} | From: {msg.from_}")
        return True
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Error forwarding '{msg.subject}': {e}")
        return False


def main():
    print(f"[{datetime.now()}] 🚀 Mailo → Gmail forwarder started (interval: {CHECK_INTERVAL}s)")

    while True:
        try:
            with MailBox(IMAP_SERVER, IMAP_PORT, ssl=True).login(IMAP_USER, IMAP_PASS, 'INBOX') as mailbox:
                # Fetch only unseen messages
                for msg in mailbox.fetch(AND(seen=False), mark_seen=False):
                    if forward_email(msg):
                        # Mark as read on Mailo
                        mailbox.flag(msg.uid, ['\\Seen'], True)
                        # Optional: mailbox.delete(msg.uid)  # or move to another folder

        except Exception as e:
            print(f"[{datetime.now()}] ❌ Connection error: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    if not all([IMAP_USER, IMAP_PASS, FORWARD_TO]):
        raise ValueError("Missing required environment variables: IMAP_USER, IMAP_PASS, FORWARD_TO")
    main()
