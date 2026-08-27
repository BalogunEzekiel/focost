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
                continue

            db.session.add(
                Permission(
                    code=permission_data["code"],
                    module=permission_data["module"],
                    action=permission_data["action"],
                    name=permission_data["name"],
                    description=permission_data.get(
                        "description"
                    )
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

    # ==========================================================
    # INITIAL SUPER ADMIN
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
                "⚠ Super Admin not created."
            )

            print(
                "Set FOCOST_SUPER_ADMIN_EMAIL "
                "and FOCOST_SUPER_ADMIN_PASSWORD "
                "before running the seed."
            )

            return

        # ------------------------------------------------------
        # Find Super Admin role
        # ------------------------------------------------------

        super_admin_role = Role.query.filter_by(
            slug="super_admin"
        ).first()

        if not super_admin_role:

            print(
                "✗ Cannot create Super Admin user."
            )

            print(
                "Super Admin role does not exist."
            )

            return

        # ------------------------------------------------------
        # Find existing user
        # ------------------------------------------------------

        user = User.query.filter_by(
            email=email.strip().lower()
        ).first()

        # ------------------------------------------------------
        # Create user if necessary
        # ------------------------------------------------------

        if not user:

            user = User(
                first_name=first_name,
                last_name=last_name,
                email=email.strip().lower(),
                email_verified=True
            )

            user.set_password(password)

            db.session.add(user)

            db.session.flush()

            print(
                f"✓ Super Admin user created: {user.email}"
            )

        else:

            print(
                f"✓ Super Admin user already exists: "
                f"{user.email}"
            )

        # ------------------------------------------------------
        # ONE USER = ONE ROLE
        # ------------------------------------------------------
        #
        # A user must NEVER have another role in addition
        # to Super Admin.
        #
        # Because UserRole.user_id is UNIQUE, only one
        # UserRole record can exist for this user.
        # ------------------------------------------------------

        existing_assignment = UserRole.query.filter_by(
            user_id=user.id
        ).first()

        if existing_assignment:

            if existing_assignment.role_id == super_admin_role.id:

                print(
                    "✓ User already has Super Admin role"
                )

            else:

                old_role = existing_assignment.role

                old_role_name = (
                    old_role.slug
                    if old_role
                    else "unknown"
                )

                print(
                    f"⚠ User already has role "
                    f"'{old_role_name}'."
                )

                print(
                    "No automatic role replacement "
                    "was performed."
                )

                print(
                    "Each account may have only one role."
                )

                return

        else:

            assignment = UserRole(
                user_id=user.id,
                role_id=super_admin_role.id,
                assigned_by_id=None
            )

            db.session.add(assignment)

            db.session.commit()

            print(
                f"✓ Super Admin role assigned "
                f"to {user.email}"
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

        cls.seed_super_admin()

        cls.validate_single_role_rule()

        print(
            "\n✓ RBAC seed completed successfully.\n"
        )