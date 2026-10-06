from app.extensions import db
from app.models.user import User


class SubscriptionGate:
    """Central entitlement checks shared by UI, routes and services."""

    @staticmethod
    def is_admin_user(user_or_id):
        user = (
            user_or_id
            if isinstance(user_or_id, User)
            else db.session.get(User, user_or_id)
        )
        return bool(user and user.role_slug in {"admin", "super_admin"})

    @staticmethod
    def current_plan_slug(user_id):
        if SubscriptionGate.is_admin_user(user_id):
            return None

        from app.services.subscription_service_facade import current_subscription

        sub = current_subscription(user_id)

        if not sub or not sub.is_active_access:
            return None

        if sub.is_trial:
            return "free_trial"

        return sub.plan.slug if sub.plan else None

    @staticmethod
    def has_paid_plan(user_id, allowed_slugs):
        slug = SubscriptionGate.current_plan_slug(user_id)
        return slug in set(allowed_slugs)

    @staticmethod
    def ads_allowed(user_id):
        slug = SubscriptionGate.current_plan_slug(user_id)
        return slug in {"free_trial", "basic", None}