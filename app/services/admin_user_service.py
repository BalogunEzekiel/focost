from datetime import datetime

from sqlalchemy import or_
from flask_login import current_user

from app.extensions import db
from app.models.user import User
from app.models.user_role import UserRole
from app.models.role import Role
from app.services.account_closure_service import AccountClosureService


class AdminUserService:
    """Authoritative user-administration policy and persistence."""

    @staticmethod
    def get_user(public_id):
        return User.query.filter_by(public_id=public_id).first()

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
        return query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=10, error_out=False
        )

    @staticmethod
    def user_statistics():
        now = datetime.utcnow()
        start_month = datetime(now.year, now.month, 1)
        return {
            "total": User.query.count(),
            "active": User.query.filter_by(is_active=True).count(),
            "inactive": User.query.filter_by(is_active=False).count(),
            "new_this_month": User.query.filter(
                User.created_at >= start_month
            ).count(),
        }

    @staticmethod
    def assignable_roles():
        """Return active roles assignable by an administrator; never Super Admin."""
        return (
            Role.query
            .filter(
                Role.is_active.is_(True),
                Role.slug != "super_admin",
            )
            .order_by(Role.group_slug, Role.name)
            .all()
        )

    @staticmethod
    def _actor_is_admin_group():
        return bool(
            current_user.is_authenticated
            and current_user.role_group in {"super_admin", "admin"}
        )

    @staticmethod
    def _assert_target_action(user, action):
        if not user:
            raise ValueError("User not found.")

        if user.role_group == "super_admin":
            raise PermissionError(
                "The Super Admin account is system-protected."
            )

        if (
            user.id == getattr(current_user, "id", None)
            and action in {"role", "delete"}
        ):
            raise PermissionError(
                "You cannot change or close your own administrative account here."
            )

        if user.role_group not in {"admin", "user", None}:
            raise PermissionError("The target account has an invalid role group.")

    @staticmethod
    def create_user(
        first_name,
        last_name,
        email,
        password,
        role_slug="user",
    ):
        if not AdminUserService._actor_is_admin_group():
            raise PermissionError(
                "Only Super Admin or Admin accounts can create managed accounts."
            )

        role_slug = (role_slug or "user").strip().lower()
        email = (email or "").lower().strip()

        if not email:
            raise ValueError("Email is required.")
        if not password:
            raise ValueError("Password is required.")
        if User.query.filter_by(email=email).first():
            raise ValueError("Email already exists.")

        role = Role.query.filter_by(
            slug=role_slug,
            is_active=True,
        ).first()

        if not role:
            raise ValueError("Role not found.")

        if role.group_slug == "super_admin":
            raise PermissionError(
                "Super Admin accounts can only be created by the system seed."
            )

        if role.group_slug not in {"admin", "user"}:
            raise ValueError("Invalid role group.")

        user = User(
            first_name=(first_name or "").strip(),
            last_name=(last_name or "").strip(),
            email=email,
            email_verified=True,
            created_by_id=(
                current_user.id if current_user.is_authenticated else None
            ),
        )

        if not user.first_name or not user.last_name:
            raise ValueError("First name and last name are required.")

        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        db.session.add(
            UserRole(
                user_id=user.id,
                role_id=role.id,
                assigned_by_id=(
                    current_user.id if current_user.is_authenticated else None
                ),
            )
        )

        if role.group_slug == "user":
            from app.subscriptions.service import SubscriptionService
            SubscriptionService.start_trial(user, commit=False)

        db.session.commit()
        return user

    @staticmethod
    def update_user(public_id, **data):
        user = AdminUserService.get_user(public_id)
        AdminUserService._assert_target_action(user, "edit")

        if "first_name" in data:
            user.first_name = (data["first_name"] or "").strip()
        if "last_name" in data:
            user.last_name = (data["last_name"] or "").strip()

        if "email" in data:
            email = (data["email"] or "").lower().strip()
            if User.query.filter(
                User.email == email,
                User.id != user.id,
            ).first():
                raise ValueError("Email already exists.")
            user.email = email

        if data.get("password"):
            user.set_password(data["password"])
            user.auth_version += 1

        db.session.commit()
        return user

    @staticmethod
    def activate_user(public_id):
        user = AdminUserService.get_user(public_id)
        AdminUserService._assert_target_action(user, "edit")
        user.is_active = True
        user.auth_version += 1
        db.session.commit()
        return user

    @staticmethod
    def deactivate_user(public_id):
        user = AdminUserService.get_user(public_id)
        AdminUserService._assert_target_action(user, "edit")
        user.is_active = False
        user.auth_version += 1
        db.session.commit()
        return user

    @staticmethod
    def delete_user(public_id):
        user = AdminUserService.get_user(public_id)
        AdminUserService._assert_target_action(user, "delete")
        AccountClosureService.close_account(
            user,
            audit_action="admin.account.deleted_anonymized",
        )
        return True

    @staticmethod
    def remove_role(user, role_slug):
        if not user:
            raise ValueError("User not found.")
        if user.role_group == "super_admin":
            raise PermissionError(
                "The Super Admin role is system-protected."
            )
        raise PermissionError(
            "A user must always have one system role. Change the role instead of removing it."
        )

    @staticmethod
    def change_role(user, role_slug):
        if not user:
            raise ValueError("User not found.")

        AdminUserService._assert_target_action(user, "role")

        role_slug = (role_slug or "").strip().lower()
        role = Role.query.filter_by(
            slug=role_slug,
            is_active=True,
        ).first()

        if not role:
            raise ValueError("Role not found.")

        if role.group_slug == "super_admin":
            raise PermissionError(
                "Super Admin can only be assigned by the system seed."
            )

        if role.group_slug not in {"admin", "user"}:
            raise ValueError("Invalid role group.")

        previous_group = user.role_group
        new_group = role.group_slug

        # A normal user becoming an employee/admin must not retain a live
        # consumer subscription. Require it to be inactive before promotion.
        if previous_group == "user" and new_group == "admin":
            from app.subscriptions.service import SubscriptionService
            existing = SubscriptionService.current(
                user.id,
                create_trial=False,
            )
            if existing and existing.is_active_access:
                raise PermissionError(
                    "Cancel or allow the user's active subscription/trial to expire "
                    "before converting the account to an administrative role."
                )

        UserRole.query.filter_by(user_id=user.id).delete(
            synchronize_session=False
        )

        db.session.add(
            UserRole(
                user_id=user.id,
                role_id=role.id,
                assigned_by_id=(
                    current_user.id if current_user.is_authenticated else None
                ),
            )
        )

        if new_group == "user" and previous_group != "user":
            from app.subscriptions.service import SubscriptionService
            SubscriptionService.start_trial(user, commit=False)

        db.session.commit()
        return user
