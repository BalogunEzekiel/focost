import os
import smtplib
from email.message import EmailMessage

from app.models.user_settings import UserSettings
from app.models.user import User


class NotificationDeliveryService:
    """Optional outbound delivery. In-app notifications remain the system of record."""
    @staticmethod
    def send_email(user_id, title, message):
        if os.getenv("MAIL_ENABLED", "false").lower() != "true":
            return False
        user = User.query.get(user_id)
        if not user or not user.email:
            return False
        settings = UserSettings.query.filter_by(user_id=user_id).first()
        prefs = settings.get_preferences() if settings else UserSettings.DEFAULTS
        if not prefs.get("notifications", {}).get("email", False):
            return False
        host = os.getenv("MAIL_HOST")
        username = os.getenv("MAIL_USERNAME")
        password = os.getenv("MAIL_PASSWORD")
        sender = os.getenv("MAIL_FROM") or username
        if not host or not sender:
            return False
        msg = EmailMessage()
        msg["Subject"] = f"FOCOST: {title}"
        msg["From"] = sender
        msg["To"] = user.email
        msg.set_content(message)
        port = int(os.getenv("MAIL_PORT", "587"))
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(msg)
        return True
