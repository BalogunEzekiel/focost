from app.extensions import db

from app.models.user import User
from app.models.user_role import UserRole
from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import RolePermission

from app.rbac.constants import (
    SYSTEM_ROLES,
    SYSTEM_PERMISSIONS,
    SYSTEM_ROLE_SLUGS,
    ADMIN_FORBIDDEN_PERMISSION_CODES,
    DEFAULT_USER_PERMISSION_CODES,
)

import os


ADMIN_DEFAULT_PERMISSION_CODES = {
    "admin.dashboard.view",
    "users.view",
    "users.create",
    "users.edit",
    "users.update",
    "users.delete",
    "roles.view",
    "roles.create",
    "roles.edit",
    "roles.update",
    "roles.delete",
    "roles.assign",
    "roles.remove",
    "permissions.assign",
    "notifications.view",
    "notifications.manage",
    "profile.view",
    "profile.edit",
    "settings.view",
    "settings.edit",
}


class RBACSeed:
    """
    Seeds the default RBAC data and the initial Super Admin.

    Rules:
        - Roles are created once.
        - Permissions are created once.
        - Role permissions are created once.
        - Each user can have ONLY ONE role.
        - The initial Super Admin is created from environment variables.
        - Safe to run multiple times.
    """

    # ==========================================================
    # ROLES
    # ==========================================================

    @staticmethod
    def seed_roles():
        """Create/synchronize the three system groups and custom admin roles."""

        for role_data in SYSTEM_ROLES:
            role = Role.query.filter_by(
                slug=role_data["slug"]
            ).first()

            if role:
                # Keep the configured display name intact; synchronize only
                # protected structural identity fields.
                role.group_slug = role_data["group_slug"]
                role.is_system = True
                role.is_active = True
                continue

            db.session.add(
                Role(
                    slug=role_data["slug"],
                    name=role_data["name"],
                    description=role_data.get("description"),
                    is_system=True,
                    group_slug=role_data["group_slug"],
                )
            )

        db.session.flush()

        # Every non-reserved role is a custom administrative role. This
        # repairs older roles such as developer/content_creator that predate
        # the explicit group field.
        for role in Role.query.all():
            if role.slug in SYSTEM_ROLE_SLUGS:
                continue
            role.group_slug = "admin"
            role.is_system = False
            role.is_active = True

        db.session.commit()
        print("✓ Roles/groups synchronized")

    # ==========================================================
    # PERMISSIONS
    # ==========================================================

    @staticmethod
    def seed_permissions():

        for permission_data in SYSTEM_PERMISSIONS:

            permission = Permission.query.filter_by(
                code=permission_data["code"]
            ).first()

            if permission:
                permission.module = permission_data["module"]
                permission.action = permission_data["action"]
                permission.name = permission_data["name"]
                permission.description = permission_data.get("description")
                continue

            db.session.add(
                Permission(
                    code=permission_data["code"],
                    module=permission_data["module"],
                    action=permission_data["action"],
                    name=permission_data["name"],
                    description=permission_data.get("description")
                )
            )

        db.session.commit()

        print("✓ Permissions seeded")

    @staticmethod
    def assign_default_admin_permissions():
        """Synchronize the reserved Admin group's core employee permissions."""
        admin_role = Role.query.filter_by(slug="admin").first()
        if not admin_role:
            return

        permissions = Permission.query.filter(
            Permission.code.in_(ADMIN_DEFAULT_PERMISSION_CODES)
        ).all()
        existing = {
            rp.permission_id: rp
            for rp in RolePermission.query.filter_by(
                role_id=admin_role.id
            ).all()
        }

        added = 0
        for permission in permissions:
            if permission.id not in existing:
                db.session.add(
                    RolePermission(
                        role_id=admin_role.id,
                        permission_id=permission.id,
                    )
                )
                added += 1

        db.session.commit()
        print(
            f"✓ Admin group permissions synchronized "
            f"(+{added})"
        )

    # ==========================================================
    # SUPER ADMIN PERMISSIONS
    # ==========================================================

    @staticmethod
    def assign_super_admin_permissions():
        super_admin = Role.query.filter_by(
            slug="super_admin"
        ).first()

        if not super_admin:
            print("✗ Super Admin role not found.")
            return

        permissions = Permission.query.all()
        allowed_codes = {
            permission.code
            for permission in permissions
            if permission.code not in ADMIN_FORBIDDEN_PERMISSION_CODES
        }

        existing = {
            rp.permission_id: rp
            for rp in RolePermission.query.filter_by(
                role_id=super_admin.id
            ).all()
        }

        added = 0
        removed = 0

        for permission in permissions:
            rp = existing.get(permission.id)
            if permission.code in allowed_codes:
                if not rp:
                    db.session.add(
                        RolePermission(
                            role_id=super_admin.id,
                            permission_id=permission.id,
                        )
                    )
                    added += 1
            elif rp:
                db.session.delete(rp)
                removed += 1

        db.session.commit()
        print(
            f"✓ Super Admin permissions synchronized "
            f"(+{added}, -{removed})"
        )


    @staticmethod
    def sanitize_role_permissions():
        """Remove structurally invalid permissions from every role group."""
        removed = 0

        for role in Role.query.all():
            allowed = None

            if role.group_slug in {"super_admin", "admin"}:
                allowed = lambda code: code not in ADMIN_FORBIDDEN_PERMISSION_CODES
            elif role.group_slug == "user":
                allowed = lambda code: code in DEFAULT_USER_PERMISSION_CODES

            if allowed is None:
                continue

            for rp in list(role.permissions):
                permission = rp.permission
                if permission and not allowed(permission.code):
                    db.session.delete(rp)
                    removed += 1

        db.session.commit()
        print(f"✓ Role permission boundaries synchronized (-{removed})")


    @staticmethod
    def assign_default_user_permissions():
        user_role = Role.query.filter_by(slug="user").first()
        if not user_role:
            return

        permissions = Permission.query.filter(
            Permission.code.in_(DEFAULT_USER_PERMISSION_CODES)
        ).all()
        desired_ids = {permission.id for permission in permissions}

        existing = {
            rp.permission_id: rp
            for rp in RolePermission.query.filter_by(
                role_id=user_role.id
            ).all()
        }

        added = 0
        removed = 0

        for permission in permissions:
            if permission.id not in existing:
                db.session.add(
                    RolePermission(
                        role_id=user_role.id,
                        permission_id=permission.id,
                    )
                )
                added += 1

        for permission_id, rp in existing.items():
            if permission_id not in desired_ids:
                db.session.delete(rp)
                removed += 1

        db.session.commit()
        print(
            f"✓ Default User permissions synchronized "
            f"(+{added}, -{removed})"
        )

    # ==========================================================
    # INITIAL / PRIMARY SUPER ADMIN
    # ==========================================================

    @staticmethod
    def seed_super_admin():

        # ------------------------------------------------------
        # Read credentials from environment
        # ------------------------------------------------------

        email = os.getenv(
            "FOCOST_SUPER_ADMIN_EMAIL"
        )

        password = os.getenv(
            "FOCOST_SUPER_ADMIN_PASSWORD"
        )

        first_name = os.getenv(
            "FOCOST_SUPER_ADMIN_FIRST_NAME",
            "Focost"
        )

        last_name = os.getenv(
            "FOCOST_SUPER_ADMIN_LAST_NAME",
            "SuperAdmin"
        )

        # ------------------------------------------------------
        # Validate credentials
        # ------------------------------------------------------

        if not email or not password:

            print(
                "⚠ Super Admin not created/updated."
            )

            print(
                "Set FOCOST_SUPER_ADMIN_EMAIL "
                "and FOCOST_SUPER_ADMIN_PASSWORD "
                "before running the seed."
            )

            return

        email = email.strip().lower()

        # ------------------------------------------------------
        # Find Super Admin role
        # ------------------------------------------------------

        super_admin_role = Role.query.filter_by(
            slug="super_admin"
        ).first()

        if not super_admin_role:

            print(
                "✗ Cannot create/update Super Admin."
            )

            print(
                "Super Admin role does not exist."
            )

            return

        # ------------------------------------------------------
        # Find the existing Super Admin account
        #
        # IMPORTANT:
        # We find the account through its role assignment,
        # NOT through the new email.
        #
        # This preserves the existing User.id and all related
        # records.
        # ------------------------------------------------------

        existing_super_admin_assignment = (
            UserRole.query
            .filter_by(
                role_id=super_admin_role.id
            )
            .first()
        )

        # ------------------------------------------------------
        # CASE 1:
        # Existing Super Admin found
        # ------------------------------------------------------

        if existing_super_admin_assignment:

            user = User.query.get(
                existing_super_admin_assignment.user_id
            )

            if not user:

                raise RuntimeError(
                    "Super Admin role assignment points "
                    "to a missing user."
                )

            # --------------------------------------------------
            # Safety check:
            # Do not silently take over another user account
            # that already owns the configured email.
            # --------------------------------------------------

            email_owner = User.query.filter(
                User.email == email,
                User.id != user.id
            ).first()

            if email_owner:

                raise RuntimeError(
                    f"Cannot update Super Admin email to "
                    f"'{email}'. That email already belongs "
                    f"to User ID {email_owner.id}."
                )

            old_email = user.email
            old_first_name = user.first_name
            old_last_name = user.last_name

            # --------------------------------------------------
            # Update ONLY the Super Admin identity fields
            # --------------------------------------------------

            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.email_verified = True

            # Set the new password
            user.set_password(password)

            db.session.commit()

            print(
                "✓ Existing Super Admin account updated."
            )

            print(
                f"   User ID preserved: {user.id}"
            )

            print(
                f"   Name: "
                f"{old_first_name} {old_last_name}"
                f" → "
                f"{user.first_name} {user.last_name}"
            )

            print(
                f"   Email: "
                f"{old_email}"
                f" → "
                f"{user.email}"
            )

            print(
                "   Password: updated"
            )

            print(
                "   Role: super_admin"
            )

            print(
                "   Existing user data and relationships preserved."
            )

            return

        # ------------------------------------------------------
        # CASE 2:
        # No existing Super Admin exists
        #
        # Only in this situation do we create a new account.
        # ------------------------------------------------------

        user = User.query.filter_by(
            email=email
        ).first()

        if user:

            raise RuntimeError(
                f"User with email '{email}' already exists "
                "but is not the Super Admin. "
                "Refusing to take over the account."
            )

        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            email_verified=True
        )

        user.set_password(password)

        db.session.add(user)

        db.session.flush()

        assignment = UserRole(
            user_id=user.id,
            role_id=super_admin_role.id,
            assigned_by_id=None
        )

        db.session.add(assignment)

        db.session.commit()

        print(
            f"✓ Super Admin user created: {user.email}"
        )

        print(
            f"   User ID: {user.id}"
        )

    # ==========================================================
    # VALIDATE ONE-ROLE RULE
    # ==========================================================

    @staticmethod
    def validate_single_role_rule():

        duplicate_users = (
            db.session.query(
                UserRole.user_id
            )
            .group_by(
                UserRole.user_id
            )
            .having(
                db.func.count(UserRole.id) > 1
            )
            .all()
        )

        if duplicate_users:

            print(
                "✗ RBAC validation failed."
            )

            print(
                "The following user IDs have "
                "multiple role assignments:"
            )

            for row in duplicate_users:

                print(
                    f"   User ID: {row[0]}"
                )

            raise RuntimeError(
                "One-user-one-role rule violated."
            )

        print(
            "✓ One-user-one-role rule validated"
        )

    # ==========================================================
    # RUN
    # ==========================================================

    @classmethod
    def run(cls):

        print(
            "\n========== RBAC SEED ==========\n"
        )

        cls.seed_roles()

        cls.seed_permissions()

        cls.assign_default_admin_permissions()

        cls.assign_super_admin_permissions()

        cls.assign_default_user_permissions()

        cls.sanitize_role_permissions()

        cls.seed_super_admin()

        cls.validate_single_role_rule()

        print(
            "\n✓ RBAC seed completed successfully.\n"
        )