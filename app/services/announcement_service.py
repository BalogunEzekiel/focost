from app.extensions import db
from app.models.announcement import Announcement
from app.models.notification import Notification
from app.services.subscription_gate import SubscriptionGate
from app.utils.timezone import utc_now
from app.services.email_service import EmailService


class AnnouncementService:
    """Authoritative communications/announcement service."""

    TYPES = ("notice", "announcement", "advertisement", "legal", "security", "maintenance")
    AUDIENCES = ("all", "free_trial", "basic", "plus", "pro", "user")
    PRIORITIES = ("low", "normal", "high", "urgent")

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

        audience = item.audience
        if audience in {"all", "user"}:
            return True
        if audience in {"free_trial", "basic", "plus", "pro"}:
            return SubscriptionGate.current_plan_slug(user_id) == audience
        return False

    @staticmethod
    def active_for_user(user_id, channel=None):
        now = utc_now()
        query = Announcement.query.filter(
            Announcement.is_active.is_(True),
            Announcement.status == "published",
            db.or_(Announcement.starts_at.is_(None), Announcement.starts_at <= now),
            db.or_(Announcement.ends_at.is_(None), Announcement.ends_at > now),
        )
        if channel == "banner":
            query = query.filter(Announcement.dashboard_banner.is_(True))
        elif channel == "flyer":
            query = query.filter(Announcement.flyer.is_(True))
        elif channel == "in_app":
            query = query.filter(Announcement.in_app.is_(True))

        return [
            item for item in query.order_by(
                Announcement.priority.desc(), Announcement.published_at.desc()
            ).all()
            if AnnouncementService._matches_user(item, user_id)
        ]

    @staticmethod
    def publish(announcement, published_by_id):
        if announcement.announcement_type not in AnnouncementService.TYPES:
            raise ValueError("Invalid communication type.")
        if announcement.audience not in AnnouncementService.AUDIENCES:
            raise ValueError("Invalid audience.")

        # Advertising is intentionally restricted to Free Trial/Basic targeting.
        if announcement.announcement_type == "advertisement" and announcement.audience not in {"free_trial", "basic"}:
            raise ValueError("Advertising can only target Free Trial or Basic users.")

        announcement.status = "published"
        announcement.published_at = utc_now()
        announcement.published_by_id = published_by_id
        db.session.commit()

        if announcement.email:
            AnnouncementService.dispatch_email(announcement)

        return announcement

    @staticmethod
    def create(**data):
        announcement = Announcement(**data)
        db.session.add(announcement)
        db.session.commit()
        return announcement

    @staticmethod
    def dispatch_email(announcement):
        if not announcement.email or not EmailService.enabled():
            return 0
        from app.models.user import User
        users = User.query.filter_by(is_active=True).all()
        sent = 0
        for user in users:
            if not AnnouncementService._matches_user(announcement, user.id):
                continue
            try:
                if EmailService.send(
                    user.email,
                    announcement.title,
                    announcement.message,
                    f"<p>{announcement.message.replace(chr(10), '<br>')}</p>",
                ):
                    sent += 1
            except Exception:
                # Email is a secondary channel; failure must not roll back the
                # published announcement or in-app delivery.
                continue
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
                message=item.message,
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
