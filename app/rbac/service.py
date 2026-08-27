from flask_login import current_user
import logging

from app.extensions import db
from app.models.role import Role
from app.models.user_role import UserRole

logger = logging.getLogger(__name__)

class RBACService:
    """
    Centralized Role-Based Access Control (RBAC) service.
    """

    # ======================================================
    # Default permissions for every User
    # ======================================================

    DEFAULT_USER_PERMISSIONS = {

        "dashboard.view",

        "income.view",
        "income.create",
        "income.edit",
        "income.delete",

        "expenses.view",
        "expenses.create",
        "expenses.edit",
        "expenses.delete",

        "budgets.view",
        "budgets.create",
        "budgets.edit",
        "budgets.delete",

        "goals.view",
        "goals.create",
        "goals.edit",
        "goals.delete",

        "reports.view",

        "profile.view",
        "profile.edit",

        "notifications.view",

        "ai.chat",

        "settings.view_profile"
    }

    # ======================================================
    # Authentication
    # ======================================================

    @staticmethod
    def is_authenticated():
        return current_user.is_authenticated

    # ======================================================
    # Roles
    # ======================================================

    @staticmethod
    def has_role(role):

        if not RBACService.is_authenticated():
            return False

        return current_user.has_role(role)

    @staticmethod
    def has_any_role(*roles):

        if not RBACService.is_authenticated():
            return False

        return current_user.has_any_role(*roles)

    @staticmethod
    def has_all_roles(*roles):

        if not RBACService.is_authenticated():
            return False

        return current_user.has_all_roles(*roles)

    # ======================================================
    # Permissions
    # ======================================================

    @staticmethod
    def has_permission(permission):

        if not RBACService.is_authenticated():
            logger.info(
                "Anonymous user attempted permission check: %s",
                permission
            )
            return False

        role = getattr(
            current_user,
            "primary_role",
            None
        )

        logger.info(
            "User=%s Role=%s Permission=%s",
            getattr(current_user, "email", None),
            getattr(role, "slug", None),
            permission,
        )

        if role is None:
            logger.info("No primary role found.")
            return False

        if role.slug == "super_admin":
            return True

        if role.slug == "user":
            return permission in RBACService.DEFAULT_USER_PERMISSIONS

        return current_user.has_permission(permission)


    @staticmethod
    def has_any_permission(*permissions):

        return any(
            RBACService.has_permission(permission)
            for permission in permissions
        )


    @staticmethod
    def has_all_permissions(*permissions):

        return all(
            RBACService.has_permission(permission)
            for permission in permissions
        )

    # ======================================================
    # Convenience Methods
    # ======================================================

    @staticmethod
    def is_super_admin():
        return RBACService.has_role("super_admin")

    @staticmethod
    def is_admin():

        if not RBACService.is_authenticated():
            return False

        role = current_user.primary_role

        if role is None:
            return False

        return role.slug in ("super_admin", "admin")

    @staticmethod
    def is_user():
        return RBACService.has_role("user")

    # ======================================================
    # Information
    # ======================================================

    @staticmethod
    def roles():

        if not RBACService.is_authenticated():
            return []

        return current_user.roles_list

    @staticmethod
    def permissions():

        if not RBACService.is_authenticated():
            return set()

        role = current_user.primary_role

        if role is None:
            return set()

        if role.slug == "super_admin":
            return {"*"}

        if role.slug == "user":
            return set(RBACService.DEFAULT_USER_PERMISSIONS)

        return current_user.permissions

    # app/rbac/service.py

    @staticmethod
    def assign_default_role(user):
        """
        Assign the default 'user' role to a newly registered user.
        """

        role = Role.query.filter_by(
            slug="user",
            is_active=True
        ).first()

        if role is None:
            raise ValueError(
                "Default 'user' role not found."
            )

        assignment = UserRole(
            user=user,
            role=role,
            assigned_by_id=None
        )

        db.session.add(assignment)

        logger.info(
            "Assigned role '%s' to user %s",
            role.slug,
            user.email
        )