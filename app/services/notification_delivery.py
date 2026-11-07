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
        from app.services.language_service import LanguageService
        language_code = LanguageService.get(user_id)
        title = LanguageService.translate_text(language_code, title)
        message = LanguageService.translate_text(language_code, message)
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
        msg.set_content(f"{message}\n\nFOCOST")
        from html import escape
        msg.add_alternative(
            "<!doctype html><html><body style=\"font-family:Arial,sans-serif;color:#263238;line-height:1.6\">"
            f"<h2>{escape(str(title))}</h2><p>{escape(str(message))}</p>"
            "<p style=\"color:#607d8b;font-size:12px\">FOCOST</p></body></html>",
            subtype="html",
        )
        port = int(os.getenv("MAIL_PORT", "587"))
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(msg)
        return True
