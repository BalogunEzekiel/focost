import os
import smtplib
from email.message import EmailMessage

from flask import current_app


class EmailService:
    """Small provider-neutral SMTP delivery service for transactional mail."""

    @staticmethod
    def enabled():
        return os.getenv("MAIL_ENABLED", "false").lower() == "true"

    @staticmethod
    def send(to, subject, text_body, html_body=None):
        if not EmailService.enabled():
            current_app.logger.warning("Transactional email disabled; not sending to %s", to)
            return False

        host = os.getenv("MAIL_HOST")
        username = os.getenv("MAIL_USERNAME")
        password = os.getenv("MAIL_PASSWORD")
        sender = os.getenv("MAIL_FROM") or username
        port = int(os.getenv("MAIL_PORT", "587"))
        use_tls = os.getenv("MAIL_USE_TLS", "true").lower() == "true"

        if not host or not sender:
            raise RuntimeError("MAIL_HOST and MAIL_FROM/MAIL_USERNAME are required when MAIL_ENABLED=true.")

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to
        msg.set_content(text_body)
        if html_body:
            msg.add_alternative(html_body, subtype="html")

        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if use_tls:
                smtp.starttls()
            if username:
                smtp.login(username, password or "")
            smtp.send_message(msg)
        return True
