from app.extensions import db

from app.models.user import User
from app.models.user_role import UserRole
from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import RolePermission

from app.rbac.constants import (
    SYSTEM_ROLES,
    SYSTEM_PERMISSIONS
)

import os


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

        for role_data in SYSTEM_ROLES:

            role = Role.query.filter_by(
                slug=role_data["slug"]
            ).first()

            if role:
                continue

            db.session.add(
                Role(
                    slug=role_data["slug"],
                    name=role_data["name"],
                    description=role_data.get("description"),
                    is_system=role_data.get(
                        "is_system",
                        True
                    )
                )
            )

        db.session.commit()

        print("✓ Roles seeded")

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

    # ==========================================================
    # SUPER ADMIN PERMISSIONS
    # ==========================================================

    @staticmethod
    def assign_super_admin_permissions():

        super_admin = Role.query.filter_by(
            slug="super_admin"
        ).first()

        if not super_admin:

            print(
                "✗ Super Admin role not found."
            )

            return

        permissions = Permission.query.all()

        added = 0

        for permission in permissions:

            exists = RolePermission.query.filter_by(
                role_id=super_admin.id,
                permission_id=permission.id
            ).first()

            if exists:
                continue

            db.session.add(
                RolePermission(
                    role_id=super_admin.id,
                    permission_id=permission.id
                )
            )

            added += 1

        db.session.commit()

        print(
            f"✓ {added} permissions assigned "
            "to Super Admin"
        )



    @staticmethod
    def assign_default_user_permissions():
        user_role = Role.query.filter_by(slug="user").first()
        if not user_role:
            return

        default_codes = {
            "dashboard.view", "income.view", "income.create", "income.edit", "income.delete",
            "expenses.view", "expenses.create", "expenses.edit", "expenses.delete",
            "budgets.view", "budgets.create", "budgets.edit", "budgets.delete",
            "goals.view", "goals.create", "goals.edit", "goals.delete",
            "reports.view", "profile.view", "profile.edit", "notifications.view",
            "ai.chat", "settings.view_profile", "investments.view",
        }
        permissions = Permission.query.filter(Permission.code.in_(default_codes)).all()
        for permission in permissions:
            exists = RolePermission.query.filter_by(
                role_id=user_role.id, permission_id=permission.id
            ).first()
            if not exists:
                db.session.add(RolePermission(
                    role_id=user_role.id, permission_id=permission.id
                ))
        db.session.commit()
        print("✓ Default User permissions synchronized")

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

        cls.assign_super_admin_permissions()

        cls.assign_default_user_permissions()

        cls.seed_super_admin()

        cls.validate_single_role_rule()

        print(
            "\n✓ RBAC seed completed successfully.\n"
        )