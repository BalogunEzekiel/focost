from flask_login import UserMixin
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from app.extensions import db, login_manager
from app.models.base import BaseModel


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class User(BaseModel, UserMixin):

    __tablename__ = "users"

    first_name = db.Column(
        db.String(80),
        nullable=False
    )

    last_name = db.Column(
        db.String(80),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
        index=True
    )

    phone = db.Column(
        db.String(20)
    )

    country = db.Column(
        db.String(80),
        default="Nigeria"
    )

    currency = db.Column(
        db.String(10),
        default="NGN"
    )

    occupation = db.Column(
        db.String(120)
    )

    monthly_income = db.Column(
        db.Float,
        default=0
    )

    avatar = db.Column(
        db.String(255),
        default="default-avatar.png"
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    email_verified = db.Column(
        db.Boolean,
        default=False
    )

    # ==========================================================
    # ROLE ASSIGNMENT
    # ONE USER = ONE ROLE
    # ==========================================================

    role_assignment = db.relationship(
        "UserRole",
        foreign_keys="UserRole.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin"
    )

    # ==========================================================
    # AUDIT LOGS
    # ==========================================================

    audit_logs = db.relationship(
        "AuditLog",
        back_populates="user",
        lazy="selectin"
    )

    # ==========================================================
    # PASSWORD
    # ==========================================================

    def set_password(self, password):

        self.password_hash = generate_password_hash(
            password
        )

    def check_password(self, password):

        return check_password_hash(
            self.password_hash,
            password
        )

    # ==========================================================
    # ROLE
    # ==========================================================

    @property
    def role(self):

        if not self.role_assignment:
            return None

        return self.role_assignment.role

    @property
    def role_slug(self):

        if not self.role:
            return None

        return self.role.slug

    @property
    def primary_role(self):

        return self.role

    @property
    def roles_list(self):

        if not self.role:
            return []

        return [self.role.slug]

    @property
    def is_super_admin(self):

        return self.role_slug == "super_admin"

    # ==========================================================
    # ROLE CHECKS
    # ==========================================================

    def has_role(self, slug):

        return self.role_slug == slug

    def has_any_role(self, *roles):

        return self.role_slug in roles

    def has_all_roles(self, *roles):

        if not self.role_slug:
            return False

        return all(
            self.role_slug == role
            for role in roles
        )

    # ==========================================================
    # PERMISSION CHECK
    # ==========================================================

    def has_permission(self, permission_code):

        role = self.role

        if not role:
            return False

        # Only check this if your Role model
        # actually has an is_active field.
        if hasattr(role, "is_active"):

            if not role.is_active:
                return False

        for role_permission in role.permissions:

            permission = role_permission.permission

            if not permission:
                continue

            if hasattr(permission, "is_active"):

                if not permission.is_active:
                    continue

            if permission.code == permission_code:

                return True

        return False

    # ==========================================================
    # USER PERMISSIONS
    # ==========================================================

    @property
    def permissions(self):

        permissions = set()

        role = self.role

        if not role:
            return permissions

        for role_permission in role.permissions:

            permission = role_permission.permission

            if not permission:
                continue

            if hasattr(permission, "is_active"):

                if not permission.is_active:
                    continue

            permissions.add(
                permission.code
            )

        return permissions

    # ==========================================================
    # MULTIPLE PERMISSION CHECKS
    # ==========================================================

    def has_any_permission(
        self,
        *permissions
    ):

        return any(
            permission in self.permissions
            for permission in permissions
        )

    def has_all_permissions(
        self,
        *permissions
    ):

        return all(
            permission in self.permissions
            for permission in permissions
        )

    # ==========================================================
    # REPRESENTATION
    # ==========================================================

    def __repr__(self):

        return f"<User {self.email}>"