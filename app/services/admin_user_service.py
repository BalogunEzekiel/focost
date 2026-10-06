from datetime import datetime

from sqlalchemy import or_
from flask_login import current_user

from app.extensions import db
from app.models.user import User
from app.models.user_role import UserRole
from app.models.role import Role
from app.services.account_closure_service import (
    AccountClosureService,
)


class AdminUserService:
    """Authoritative user administration policy and persistence."""

    @staticmethod
    def get_user(public_id):
        return User.query.filter_by(
            public_id=public_id
        ).first()

    @staticmethod
    def list_users(page=1, search=""):
        query = User.query

        if search:
            term = f"%{search}%"

            query = query.filter(
                or_(
                    User.first_name.ilike(term),
                    User.last_name.ilike(term),
                    User.email.ilike(term),
                )
            )

        return query.order_by(
            User.created_at.desc()
        ).paginate(
            page=page,
            per_page=10,
            error_out=False,
        )

    @staticmethod
    def user_statistics():
        now = datetime.utcnow()

        start_month = datetime(
            now.year,
            now.month,
            1,
        )

        return {
            "total": User.query.count(),

            "active": User.query.filter_by(
                is_active=True
            ).count(),

            "inactive": User.query.filter_by(
                is_active=False
            ).count(),

            "new_this_month": (
                User.query
                .filter(
                    User.created_at >= start_month
                )
                .count()
            ),
        }

    @staticmethod
    def _actor_is_super_admin():
        return bool(
            current_user.is_authenticated
            and current_user.role_slug == "super_admin"
        )

    @staticmethod
    def _protected_target(user):
        return bool(
            user
            and user.role_slug == "super_admin"
        )

    @staticmethod
    def _assert_target_action(user, action):
        if not user:
            raise ValueError(
                "User not found."
            )

        # ----------------------------------------------------------
        # SUPER ADMIN IS SYSTEM-PROTECTED
        # ----------------------------------------------------------

        if user.role_slug == "super_admin":
            raise PermissionError(
                "The Super Admin account is system-protected."
            )

        # ----------------------------------------------------------
        # ONLY SUPER ADMIN CAN DELETE ADMINISTRATORS
        # ----------------------------------------------------------

        if (
            action == "delete"
            and user.role_slug == "admin"
            and not AdminUserService._actor_is_super_admin()
        ):
            raise PermissionError(
                "Only a Super Admin can delete an Administrator."
            )

        # ----------------------------------------------------------
        # ONLY SUPER ADMIN CAN CHANGE ADMINISTRATOR ROLE
        # ----------------------------------------------------------

        if (
            action == "role"
            and user.role_slug == "admin"
            and not AdminUserService._actor_is_super_admin()
        ):
            raise PermissionError(
                "Only a Super Admin can change an Administrator's role."
            )

    @staticmethod
    def create_user(
        first_name,
        last_name,
        email,
        password,
        role_slug=None,
    ):
        if (
            current_user.is_authenticated
            and current_user.role_slug != "super_admin"
            and role_slug in {"admin", "super_admin"}
        ):
            raise PermissionError(
                "Only a Super Admin can create administrative accounts."
            )

        email = email.lower().strip()

        if User.query.filter_by(
            email=email
        ).first():
            raise ValueError(
                "Email already exists."
            )

        user = User(
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            email=email,
            email_verified=True,
            created_by_id=(
                current_user.id
                if current_user.is_authenticated
                else None
            ),
        )

        user.set_password(password)

        db.session.add(user)
        db.session.flush()

        if role_slug:
            role = Role.query.filter_by(
                slug=role_slug,
                is_active=True,
            ).first()

            if not role:
                raise ValueError(
                    "Role not found."
                )

            if role.slug == "super_admin":
                raise PermissionError(
                    "Super Admin accounts can only be created "
                    "by the developer seed."
                )

            db.session.add(
                UserRole(
                    user_id=user.id,
                    role_id=role.id,
                    assigned_by_id=(
                        current_user.id
                        if current_user.is_authenticated
                        else None
                    ),
                )
            )

        if role_slug == "user":
            from app.subscriptions.service import (
                SubscriptionService,
            )

            SubscriptionService.start_trial(
                user,
                commit=False,
            )

        db.session.commit()

        return user

    @staticmethod
    def update_user(public_id, **data):
        user = AdminUserService.get_user(
            public_id
        )

        AdminUserService._assert_target_action(
            user,
            "edit",
        )

        if "first_name" in data:
            user.first_name = (
                data["first_name"] or ""
            ).strip()

        if "last_name" in data:
            user.last_name = (
                data["last_name"] or ""
            ).strip()

        if "email" in data:
            email = (
                data["email"]
                .lower()
                .strip()
            )

            if (
                User.query
                .filter(
                    User.email == email,
                    User.id != user.id,
                )
                .first()
            ):
                raise ValueError(
                    "Email already exists."
                )

            user.email = email

        if data.get("password"):
            user.set_password(
                data["password"]
            )

            user.auth_version += 1

        db.session.commit()

        return user

    @staticmethod
    def activate_user(public_id):
        user = AdminUserService.get_user(
            public_id
        )

        AdminUserService._assert_target_action(
            user,
            "edit",
        )

        user.is_active = True
        user.auth_version += 1

        db.session.commit()

        return user

    @staticmethod
    def deactivate_user(public_id):
        user = AdminUserService.get_user(
            public_id
        )

        AdminUserService._assert_target_action(
            user,
            "edit",
        )

        user.is_active = False
        user.auth_version += 1

        db.session.commit()

        return user

    @staticmethod
    def delete_user(public_id):
        """
        Close and anonymize an administrator/user account.

        The User row is intentionally retained rather than physically
        deleted. This prevents cascading deletion of PolicyAcceptance
        and other retained compliance/payment/security evidence.

        Existing authorization rules remain unchanged:
            - Super Admin cannot be deleted.
            - Only Super Admin can delete an Administrator.
        """

        user = AdminUserService.get_user(
            public_id
        )

        # Preserve all existing governance protections.
        AdminUserService._assert_target_action(
            user,
            "delete",
        )

        AccountClosureService.close_account(
            user,
            audit_action="admin.account.deleted_anonymized",
        )

        return True

    @staticmethod
    def remove_role(user, role_slug):
        if not user:
            raise ValueError(
                "User not found."
            )

        if user.role_slug == "super_admin":
            raise PermissionError(
                "The Super Admin role is system-protected."
            )

        if (
            user.role_slug == "admin"
            and not AdminUserService._actor_is_super_admin()
        ):
            raise PermissionError(
                "Only a Super Admin can modify an Administrator role."
            )

        role = Role.query.filter_by(
            slug=role_slug
        ).first()

        if not role:
            return

        assignment = UserRole.query.filter_by(
            user_id=user.id,
            role_id=role.id,
        ).first()

        if assignment:
            db.session.delete(
                assignment
            )

            db.session.commit()

    @staticmethod
    def change_role(user, role_slug):
        if not user:
            raise ValueError(
                "User not found."
            )

        if user.role_slug == "super_admin":
            raise PermissionError(
                "The Super Admin role is system-protected."
            )

        if (
            user.role_slug == "admin"
            and not AdminUserService._actor_is_super_admin()
        ):
            raise PermissionError(
                "Only a Super Admin can change an Administrator's role."
            )

        role = Role.query.filter_by(
            slug=role_slug,
            is_active=True,
        ).first()

        if not role:
            raise ValueError(
                "Role not found."
            )

        if role.slug == "super_admin":
            raise PermissionError(
                "Super Admin can only be assigned by the developer seed."
            )

        UserRole.query.filter_by(
            user_id=user.id
        ).delete(
            synchronize_session=False
        )

        db.session.add(
            UserRole(
                user_id=user.id,
                role_id=role.id,
                assigned_by_id=(
                    current_user.id
                    if current_user.is_authenticated
                    else None
                ),
            )
        )

        db.session.commit()