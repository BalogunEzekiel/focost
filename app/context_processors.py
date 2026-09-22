import logging

from flask import request
from flask_login import current_user

from app.services.notification_service import NotificationService

from app.rbac.helpers import (
    is_authenticated,
    is_admin,
    has_role,
    has_any_role,
    has_permission,
    has_any_permission,
    has_all_permissions,
)

logger = logging.getLogger(__name__)


def register_context_processors(app):
    """
    Registers variables available to every template.

    These power:

    • Dashboard Topbar
    • Sidebar
    • Notifications
    • User Menu
    • RBAC (roles & permissions)
    """

    @app.context_processor
    def inject_global_template_data():

        endpoint = request.endpoint or ""

        # ==================================================
        # Guest User
        # ==================================================

        if not current_user.is_authenticated:

            return {

                # Notifications
                "notifications": [],
                "notification_count": 0,
                "unread_notifications": [],

                # Navigation
                "page_title": "FOCOST",
                "current_endpoint": endpoint,

                # User
                "current_user": current_user,
                "user_plan": "Guest",

                # RBAC Helpers
                "is_authenticated": is_authenticated,
                "is_admin": is_admin,

                "has_role": has_role,
                "has_any_role": has_any_role,

                "has_permission": has_permission,
                "has_any_permission": has_any_permission,
                "has_all_permissions": has_all_permissions,
            }

        # ==================================================
        # Logged-in User
        # ==================================================

        notifications = []
        unread_count = 0

        try:

            NotificationService.generate_system_notifications(
                current_user.id
            )

            notifications = (
                NotificationService.get_recent(
                    current_user.id,
                    limit=4
                ) or []
            )

            unread_count = (
                NotificationService.get_unread_count(
                    current_user.id
                )
            )

        except Exception as exc:

            logger.exception(
                "Failed loading notifications: %s",
                exc
            )

            notifications = []
            unread_count = 0

        try:
            from app.subscriptions.service import SubscriptionService
            subscription = SubscriptionService.current(current_user.id)
            if subscription and subscription.is_trial:
                user_plan = "Free Trial" if subscription.is_active_access else "Trial Expired"
            elif subscription and subscription.plan:
                user_plan = subscription.plan.name if subscription.is_active_access else "Subscription Expired"
            else:
                user_plan = "No Active Plan"
        except Exception:
            logger.exception("Failed loading subscription status")
            user_plan = "Subscription"

        return {

            # ==================================================
            # Notifications
            # ==================================================

            "notifications": notifications,

            "notification_count": unread_count,

            "unread_notifications": [

                notification

                for notification in notifications

                if not notification.is_read

            ],

            # ==================================================
            # Navigation
            # ==================================================

            "page_title": "Financial Dashboard",

            "current_endpoint": endpoint,

            # ==================================================
            # User
            # ==================================================

            "current_user": current_user,

            "user_plan": user_plan,

            # ==================================================
            # RBAC Helpers
            # ==================================================

            "is_authenticated": is_authenticated,

            "is_admin": is_admin,

            "has_role": has_role,

            "has_any_role": has_any_role,

            "has_permission": has_permission,

            "has_any_permission": has_any_permission,

            "has_all_permissions": has_all_permissions,
        }