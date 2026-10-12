
import json
from urllib.parse import urlparse

from flask import current_app

from app.extensions import db
from app.models.user import User
from app.models.web_push_subscription import WebPushSubscription


class WebPushService:
    """Send browser Web Push notifications through VAPID."""

    @staticmethod
    def enabled():
        config = current_app.config
        return bool(
            config.get("WEB_PUSH_ENABLED")
            and config.get("WEB_PUSH_VAPID_PUBLIC_KEY")
            and config.get("WEB_PUSH_VAPID_PRIVATE_KEY")
        )

    @staticmethod
    def _safe_action_url(action_url):
        """Accept only same-origin relative application paths."""
        if not isinstance(action_url, str) or not action_url.strip():
            return "/dashboard"

        action_url = action_url.strip()
        parsed = urlparse(action_url)

        if (
            not action_url.startswith("/")
            or action_url.startswith("//")
            or parsed.scheme
            or parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.fragment
            or "\\" in action_url
        ):
            return "/dashboard"

        return action_url

    @staticmethod
    def send_subscription(subscription, title, body, action_url=None, tag=None):
        """Send one payload to one saved browser subscription."""
        if not WebPushService.enabled():
            return False

        from pywebpush import WebPushException, webpush

        config = current_app.config

        payload = {
            "title": str(title or "FOCOST Notification")[:120],
            "body": str(body or "")[:500],
            "url": WebPushService._safe_action_url(action_url),
            "tag": str(tag or "focost-notification")[:120],
        }

        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth,
                    },
                },
                data=json.dumps(payload, ensure_ascii=False),
                vapid_private_key=config["WEB_PUSH_VAPID_PRIVATE_KEY"],
                vapid_claims={
                    "sub": config.get(
                        "WEB_PUSH_VAPID_CLAIMS_SUB",
                        "mailto:focostsecurity@gmail.com",
                    )
                },
                ttl=86400,
            )
            return True

        except WebPushException as exc:
            response = getattr(exc, "response", None)
            status_code = getattr(response, "status_code", None)

            if status_code in {404, 410}:
                subscription.is_enabled = False
                subscription.is_active = False
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                    current_app.logger.exception(
                        "Could not disable expired Web Push subscription %s",
                        subscription.id,
                    )
            else:
                current_app.logger.warning(
                    "Web Push delivery failed for subscription %s; HTTP status: %s",
                    subscription.id,
                    status_code,
                )

            return False

        except Exception:
            current_app.logger.exception(
                "Unexpected Web Push failure for subscription %s",
                subscription.id,
            )
            return False

    @staticmethod
    def send_announcement(announcement):
        """
        Send an eligible, currently live push announcement.

        Requires the announcement's push channel and each user's
        explicit push preference to be enabled.
        """
        if not WebPushService.enabled():
            return 0

        if not announcement.push or not announcement.is_live:
            return 0

        from app.services.announcement_service import AnnouncementService
        from app.services.settings_service import SettingsService

        subscriptions = WebPushSubscription.query.filter_by(
            is_enabled=True,
            is_active=True,
        ).all()

        sent = 0

        for subscription in subscriptions:
            try:
                user = db.session.get(User, subscription.user_id)

                if not user or not user.is_active:
                    continue

                if not AnnouncementService.can_receive(
                    announcement,
                    user.id,
                ):
                    continue

                settings = SettingsService.get(user.id)
                preferences = settings.get_preferences()
                notification_preferences = preferences.get(
                    "notifications", {}
                )

                if notification_preferences.get("push") is not True:
                    continue

                if WebPushService.send_subscription(
                    subscription=subscription,
                    title=announcement.title,
                    body=announcement.message,
                    action_url=announcement.action_url,
                    tag=f"announcement-{announcement.public_id}",
                ):
                    sent += 1

            except Exception:
                current_app.logger.exception(
                    "Web Push announcement delivery failed for user %s",
                    subscription.user_id,
                )
                continue

        return sent
