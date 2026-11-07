from app.extensions import db
from app.models.announcement import Announcement
from app.models.notification import Notification
from app.services.subscription_gate import SubscriptionGate
from app.utils.timezone import utc_now
from app.services.email_service import EmailService
from app.models.announcement_user_state import AnnouncementUserState
import json
import re
from email_validator import validate_email, EmailNotValidError
import bleach
from urllib.parse import urlparse
from markupsafe import escape

class AnnouncementService:
    """Authoritative communications/announcement service."""

    TYPES = ("notice", "announcement", "advertisement", "legal", "security", "maintenance")
    AUDIENCES = (
        "all",
        "super_admin",
        "admin",
        "user",
        "free_trial",
        "basic",
        "plus",
        "pro",
        "subscription_expired",
        "inactive_user",
    )

    AUDIENCE_LABELS = {
        "all": "All Audiences",
        "super_admin": "Super Admin",
        "admin": "Admin",
        "user": "User",
        "free_trial": "Free Trial",
        "basic": "Basic",
        "plus": "Plus",
        "pro": "Pro",
        "subscription_expired": "Subscription Expired",
        "inactive_user": "Inactive User",
    }

    PRIORITIES = ("low", "normal", "high", "urgent")
    ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS) | {
        "p", "br", "div", "span", "strong", "b", "em", "i", "u",
        "s", "ul", "ol", "li", "blockquote", "h2", "h3", "h4",
        "hr", "a", "table", "thead", "tbody", "tr", "th", "td"
    }
    ALLOWED_ATTRIBUTES = {
        "a": ["href", "title", "target", "rel"],
        "div": ["class"], "span": ["class"], "p": ["class"]
    }

    @classmethod
    def sanitize_message(cls, value):
        return bleach.clean(
            value or "", tags=cls.ALLOWED_TAGS,
            attributes=cls.ALLOWED_ATTRIBUTES,
            protocols={"http", "https", "mailto"}, strip=True
        )

    @staticmethod
    def plain_text(value):
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()

    @staticmethod
    def validate_url(value, field_name):
        if not value:
            return None
        parsed = urlparse(value.strip())
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise ValueError(f"{field_name} must be a valid http:// or https:// URL.")
        return value.strip()

    @classmethod
    def normalize_individual_emails(cls, raw):
        """Parse, validate and de-duplicate comma/semicolon/newline-separated addresses."""
        values = re.split(r"[,;\n\r]+", raw or "")
        cleaned, invalid = [], []
        seen = set()
        for value in values:
            value = value.strip()
            if not value:
                continue
            try:
                address = validate_email(value, check_deliverability=False).normalized
            except EmailNotValidError:
                invalid.append(value)
                continue
            key = address.casefold()
            if key not in seen:
                seen.add(key)
                cleaned.append(address)
        if invalid:
            raise ValueError("Invalid email address(es): " + ", ".join(invalid))
        return cleaned

    @classmethod
    def normalize_sender(cls, value):
        if value not in EmailService.SENDERS:
            raise ValueError("Select a valid FOCOST sender identity.")
        return value

    @classmethod
    def normalize_audiences(cls, values):
        raw_values = list(values or [])
        invalid = sorted(set(raw_values) - set(cls.AUDIENCES))
        if invalid:
            raise ValueError("Invalid audience group: " + ", ".join(invalid))
        values = list(dict.fromkeys(raw_values))
        if not values:
            values = ["all"]
        if "all" in values and len(values) > 1:
            raise ValueError("All Audiences cannot be combined with other audience groups.")
        return values

    @classmethod
    def audience_options(cls):
        return tuple(
            (slug, cls.AUDIENCE_LABELS[slug])
            for slug in cls.AUDIENCES
        )

    @staticmethod
    def _is_inactive_user(user):
        """
        Identify pending, unverified normal-user accounts.

        Excludes:
        - Active accounts.
        - Verified but deactivated accounts.
        - Admin accounts.
        - Accounts without a normal-user role assignment.
        - Deleted/anonymized accounts.
        """
        if not user:
            return False

        email = (user.email or "").strip().lower()

        return bool(
            user.is_normal_user
            and not user.is_active
            and not user.email_verified
            and email
            and not email.endswith("@deleted.focost.invalid")
        )

    @staticmethod
    def _matches_user(item, user_id):
        from app.models.user import User
        user = db.session.get(User, user_id)
        if not user:
            return False

        if item.target_user_id and item.target_user_id != user_id:
            return False

        if item.announcement_type == "advertisement" and not SubscriptionGate.ads_allowed(user_id):
            return False

        audiences = item.audiences
        role_group = user.role_group

        # Inactive User is deliberately narrow: only normal consumer
        # accounts that are both unactivated and unverified qualify.
        # Closed/anonymized accounts have no role assignment and are
        # therefore excluded even though their retained User row is inactive.
        if "inactive_user" in audiences and AnnouncementService._is_inactive_user(user):
            return True

        if "all" in audiences:
            return True

        if role_group == "user" and "subscription_expired" in audiences:
            if AnnouncementService.has_expired_subscription(user_id):
                return True

        plan_slug = SubscriptionGate.current_plan_slug(user_id)
        return any(
            (audience == "super_admin" and role_group == "super_admin")
            or (audience == "admin" and role_group == "admin")
            or (audience == "user" and role_group == "user")
            or (audience in {"free_trial", "basic", "plus", "pro"}
                and role_group == "user" and plan_slug == audience)
            for audience in audiences
        )

    @staticmethod
    def has_expired_subscription(user_id):
        """Identify normal users whose latest trial/paid subscription has expired.

        This deliberately reads the latest subscription directly instead of
        calling SubscriptionService.current(), which can create a new trial
        or mutate subscription status as a side effect.
        """
        from app.models.user import User
        from app.models.subscription import UserSubscription
        from app.utils.timezone import as_utc, utc_now

        user = db.session.get(User, user_id)
        if not user or user.role_group != "user":
            return False

        subscription = (
            UserSubscription.query
            .filter_by(user_id=user_id)
            .order_by(UserSubscription.created_at.desc())
            .first()
        )
        if not subscription:
            return False

        status = (subscription.status or "").lower()
        if status in {"expired", "canceled", "cancelled"}:
            return True

        expiry = (
            subscription.trial_ends_at if subscription.is_trial
            else subscription.current_period_end
        )
        if expiry:
            expiry = as_utc(expiry)
            return expiry <= utc_now()

        return status not in {"trial", "active", "past_due"}


    @staticmethod
    def can_receive(announcement, user_id):
        """Return whether the announcement is targeted to this account."""
        return AnnouncementService._matches_user(announcement, user_id)

    @staticmethod
    def active_for_user(user_id, channel=None):
        now = utc_now()

        query = Announcement.query.filter(
            Announcement.is_active.is_(True),
            Announcement.status == "published",
            db.or_(
                Announcement.starts_at.is_(None),
                Announcement.starts_at <= now
            ),
            db.or_(
                Announcement.ends_at.is_(None),
                Announcement.ends_at > now
            ),
        )

        if channel == "banner":
            query = query.filter(
                Announcement.dashboard_banner.is_(True)
            )

        elif channel == "flyer":
            query = query.filter(
                Announcement.flyer.is_(True)
            )

        elif channel == "in_app":
            query = query.filter(
                Announcement.in_app.is_(True)
            )

        elif channel == "dashboard":
            query = query.filter(
                db.or_(
                    Announcement.dashboard_banner.is_(True),
                    Announcement.flyer.is_(True)
                )
            )

        items = query.order_by(
            Announcement.priority.desc(),
            Announcement.published_at.desc()
        ).all()

        results = []

        for item in items:

            if not AnnouncementService._matches_user(
                item,
                user_id
            ):
                continue

            # Dismissal applies only to dashboard presentation
            # channels. It does not remove the communication from
            # the notification/in-app communication history.
            if channel in {"banner", "flyer", "dashboard"}:

                if AnnouncementService.is_dismissed(
                    item.id,
                    user_id
                ):
                    continue

            results.append(item)

        return results

    @staticmethod
    def is_dismissed(announcement_id, user_id):
        state = AnnouncementUserState.query.filter_by(
            announcement_id=announcement_id,
            user_id=user_id,
        ).first()

        return bool(
            state and state.dismissed_at
        )


    @staticmethod
    def dismiss(announcement_id, user_id):
        state = AnnouncementUserState.query.filter_by(
            announcement_id=announcement_id,
            user_id=user_id,
        ).first()

        if not state:

            state = AnnouncementUserState(
                announcement_id=announcement_id,
                user_id=user_id,
            )

            db.session.add(state)

        state.dismissed_at = utc_now()

        db.session.commit()

        return state


    @staticmethod
    def publish(announcement, published_by_id):
        if announcement.announcement_type not in AnnouncementService.TYPES:
            raise ValueError("Invalid communication type.")
        audiences = announcement.audiences
        AnnouncementService.normalize_audiences(audiences)

        # Advertising remains restricted to Free Trial/Basic targeting.
        if (
            announcement.announcement_type == "advertisement"
            and not set(audiences).issubset({"free_trial", "basic"})
        ):
            raise ValueError(
                "Advertising can only target Free Trial or Basic users."
            )

        announcement.message = AnnouncementService.sanitize_message(announcement.message)
        if not announcement.title or not AnnouncementService.plain_text(announcement.message):
            raise ValueError("A title and message are required.")
        announcement.action_url = AnnouncementService.validate_url(announcement.action_url, "Action URL")
        announcement.image_url = AnnouncementService.validate_url(announcement.image_url, "Image/Flyer URL")
        announcement.email_signature = AnnouncementService.sanitize_message(announcement.email_signature or "")
        announcement.sender_identity = AnnouncementService.normalize_sender(announcement.sender_identity or "team")
        announcement.status = "published"
        announcement.published_at = utc_now()
        announcement.published_by_id = published_by_id
        db.session.commit()

        # Email remains an independent delivery channel.
        if announcement.email:
            AnnouncementService.dispatch_email(announcement)

        # Push delivery is best-effort: it must never undo publication
        # or interfere with email if the push provider fails.
        if announcement.push and announcement.is_live:
            try:
                from app.services.web_push_service import WebPushService

                WebPushService.send_announcement(announcement)
            except Exception:
                import logging

                logging.getLogger(__name__).exception(
                    "Web Push dispatch failed for announcement %s",
                    announcement.public_id,
                )

        return announcement


    @staticmethod
    def create(**data):
        audiences = AnnouncementService.normalize_audiences(
            data.pop("audience_groups", [data.get("audience", "all")])
        )
        data["audience"] = audiences[0]
        data["audience_groups"] = json.dumps(audiences)
        data["message"] = AnnouncementService.sanitize_message(data.get("message", ""))
        if not data.get("title") or not AnnouncementService.plain_text(data["message"]):
            raise ValueError("A title and message are required.")
        data["action_url"] = AnnouncementService.validate_url(data.get("action_url"), "Action URL")
        data["image_url"] = AnnouncementService.validate_url(data.get("image_url"), "Image/Flyer URL")
        data["email_signature"] = AnnouncementService.sanitize_message(data.get("email_signature", ""))
        data["recipient_emails"] = json.dumps(AnnouncementService.normalize_individual_emails(data.get("recipient_emails_raw", "")))
        data.pop("recipient_emails_raw", None)
        data["sender_identity"] = AnnouncementService.normalize_sender(data.get("sender_identity", "team"))
        announcement = Announcement(**data)
        db.session.add(announcement)
        db.session.commit()
        return announcement

    @staticmethod
    def email_html(announcement, recipient=None, greeting="Hello,"):
        from flask import render_template, url_for
        logo_url = url_for("static", filename="images/pwa-512.png", _external=True)
        return render_template(
            "emails/announcement.html",
            announcement=announcement,
            recipient=recipient,
            greeting=greeting,
            logo_url=logo_url,
            sender_name=EmailService.SENDERS.get(announcement.sender_identity or "team", EmailService.SENDERS["team"])[0],
            sender_email=EmailService.SENDERS.get(announcement.sender_identity or "team", EmailService.SENDERS["team"])[1],
            signature=(
                AnnouncementService.sanitize_message(announcement.email_signature or "")
                if announcement.email_signature_enabled and announcement.email_signature
                else ""
            ),
        )

    @staticmethod
    def dispatch_email(announcement):
        if not announcement.email or not EmailService.enabled():
            return 0
        from app.models.user import User
        audiences = announcement.audiences
        targets = {}
        for user in User.query.order_by(User.id.asc()).all():
            is_pending_user = AnnouncementService._is_inactive_user(user)
            if not user.is_active and not ("inactive_user" in audiences and is_pending_user):
                continue
            address = (user.email or "").strip()
            if address and AnnouncementService._matches_user(announcement, user.id):
                targets.setdefault(address.casefold(), (address, user))
        try:
            individual = json.loads(announcement.recipient_emails or "[]")
        except (TypeError, ValueError):
            individual = []
        for address in individual if isinstance(individual, list) else []:
            if address and "@" in address:
                targets.setdefault(address.casefold(), (address, None))

        sent = 0
        for address, user in targets.values():
            try:
                full_name = " ".join(part for part in ((user.first_name or "").strip(), (user.last_name or "").strip()) if part) if user else ""
                greeting = f"Dear {full_name}," if full_name else "Hello,"
                html_body = AnnouncementService.email_html(announcement, recipient=user, greeting=greeting)
                text_body = "\n\n".join((greeting, AnnouncementService.plain_text(announcement.message), "\nVisit FOCOST: https://focost.pythonanywhere.com", f"{EmailService.SENDERS[announcement.sender_identity][0]}: {EmailService.SENDERS[announcement.sender_identity][1]}"))
                if EmailService.send(address, announcement.title, text_body, html_body, sender_identity=announcement.sender_identity):
                    sent += 1
            except Exception:
                import logging
                logging.getLogger(__name__).exception("Announcement email failed for recipient %s", address)
        return sent

    @staticmethod
    def ensure_in_app_delivery(user_id):
        items = AnnouncementService.active_for_user(user_id, "in_app")
        created = 0
        for item in items:
            if Notification.query.filter_by(
                user_id=user_id,
                unique_key=f"ANNOUNCEMENT:{item.public_id}",
            ).first():
                continue
            db.session.add(Notification(
                user_id=user_id,
                title=item.title,
                message=AnnouncementService.plain_text(item.message),
                notification_type="announcement",
                source="FOCOST",
                priority=item.priority,
                level="info" if item.announcement_type != "security" else "warning",
                icon="bi-megaphone-fill",
                action_url=item.action_url,
                unique_key=f"ANNOUNCEMENT:{item.public_id}",
                expires_at=item.ends_at,
            ))
            created += 1
        if created:
            db.session.commit()
        return created
