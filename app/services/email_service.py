import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from flask import current_app


class EmailService:
    """Provider-neutral SMTP delivery with an explicit approved sender allow-list."""
    SENDERS = {
        "team": ("The FOCOST Team", "focostteam@gmail.com"),
        "support": ("The FOCOST Support", "focostsupport@gmail.com"),
        "privacy": ("The FOCOST Privacy", "focostprivacy@gmail.com"),
        "security": ("The FOCOST Security", "focostsecurity@gmail.com"),
    }

    @staticmethod
    def enabled():
        return os.getenv("MAIL_ENABLED", "false").lower() == "true"

    @classmethod
    def sender_details(cls, identity="team"):
        if identity not in cls.SENDERS:
            raise ValueError("Invalid FOCOST sender identity.")
        name, address = cls.SENDERS[identity]
        # The configured SMTP account must be authorised by the provider to send as this address.
        authorised = {x.strip().lower() for x in os.getenv("MAIL_ALLOWED_FROM", "").split(",") if x.strip()}
        configured = os.getenv("MAIL_FROM", "").strip().lower()
        if address.lower() not in authorised and configured != address.lower():
            raise RuntimeError(f"Sender {address} is not authorised. Configure MAIL_ALLOWED_FROM after verifying it with your SMTP provider.")
        return name, address

    @classmethod
    def send(cls, to, subject, text_body, html_body=None, sender_identity="team"):
        if not cls.enabled():
            current_app.logger.warning("Email disabled; not sending to %s", to)
            return False
        host = os.getenv("MAIL_HOST")
        username = os.getenv("MAIL_USERNAME")
        password = os.getenv("MAIL_PASSWORD")
        port = int(os.getenv("MAIL_PORT", "587"))
        use_tls = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
        sender_name, sender_address = cls.sender_details(sender_identity)
        if not host:
            raise RuntimeError("MAIL_HOST is required when MAIL_ENABLED=true.")
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = formataddr((sender_name, sender_address))
        msg["To"] = to
        msg.set_content(text_body)
        if html_body:
            msg.add_alternative(html_body, subtype="html")
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if use_tls:
                smtp.starttls()
            if username:
                smtp.login(username, password or "")
            smtp.send_message(msg, from_addr=sender_address, to_addrs=[to])
        return True
