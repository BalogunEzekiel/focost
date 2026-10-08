from flask_login import current_user
import logging

from app.extensions import db
from app.models.role import Role
from app.models.user_role import UserRole
from app.rbac.constants import (
    ADMIN_FORBIDDEN_PERMISSION_CODES,
    ADMIN_GROUP,
    SUPER_ADMIN_GROUP,
    USER_GROUP,
    DEFAULT_USER_PERMISSION_CODES,
)

logger = logging.getLogger(__name__)

class RBACService:
    """
    Centralized Role-Based Access Control (RBAC) service.
    """

    # ======================================================
    # Default permissions for every User
    # ======================================================

    DEFAULT_USER_PERMISSIONS = DEFAULT_USER_PERMISSION_CODES

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
    def has_role_group(group_slug):
        if not RBACService.is_authenticated():
            return False
        return current_user.has_role_group(group_slug)

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
                permission,
            )
            return False

        role = getattr(current_user, "primary_role", None)

        logger.info(
            "User=%s Role=%s Group=%s Permission=%s",
            getattr(current_user, "email", None),
            getattr(role, "slug", None),
            getattr(role, "group_slug", None),
            permission,
        )

        if role is None or not getattr(role, "is_active", False):
            return False

        group = getattr(role, "group_slug", None)

        # Administrative accounts can never use normal-user financial
        # operations or end-user AI chat/use, regardless of assigned
        # role permissions.
        if group == ADMIN_GROUP and permission in ADMIN_FORBIDDEN_PERMISSION_CODES:
            return False

        # Super Admin is unrestricted within the administrative permission
        # surface, but is still explicitly excluded from normal-user
        # financial operations and end-user AI use above.
        if group == SUPER_ADMIN_GROUP:
            return True

        # Normal users may only exercise the canonical normal-user
        # permission set. This prevents accidental assignment of an
        # administrative permission from becoming effective.
        if group == USER_GROUP:
            if permission not in RBACService.DEFAULT_USER_PERMISSIONS:
                return False

        return current_user.has_permission(permission)


    @staticmethod
    def permission_allowed_for_group(group_slug, permission_code):
        """Return whether a permission is structurally valid for a role group."""
        if group_slug in {"super_admin", "admin"}:
            return permission_code not in ADMIN_FORBIDDEN_PERMISSION_CODES

        if group_slug == USER_GROUP:
            return permission_code in RBACService.DEFAULT_USER_PERMISSIONS

        return False

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
        return RBACService.is_admin_group()

    @staticmethod
    def is_admin_group():
        return (
            RBACService.is_authenticated()
            and getattr(current_user, "role_group", None)
            in {"super_admin", "admin"}
        )

    @staticmethod
    def is_user_group():
        return (
            RBACService.is_authenticated()
            and getattr(current_user, "role_group", None) == USER_GROUP
        )

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
        if role is None or not getattr(role, "is_active", False):
            return set()

        group = getattr(role, "group_slug", None)

        if group == SUPER_ADMIN_GROUP:
            return {
                code
                for code in RBACService._all_permission_codes()
                if code not in ADMIN_FORBIDDEN_PERMISSION_CODES
            }

        if group == USER_GROUP:
            return set(RBACService.DEFAULT_USER_PERMISSIONS)

        return {
            code
            for code in current_user.permissions
            if code not in ADMIN_FORBIDDEN_PERMISSION_CODES
        }

    @staticmethod
    def _all_permission_codes():
        from app.rbac.constants import SYSTEM_PERMISSIONS
        return {item["code"] for item in SYSTEM_PERMISSIONS}


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