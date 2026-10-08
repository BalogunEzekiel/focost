from app.extensions import db
from sqlalchemy import CheckConstraint, event, inspect

from app.rbac.constants import ROLE_GROUPS, ADMIN_GROUP

from app.models.base import BaseModel


class Role(BaseModel):
    
    __tablename__ = "roles"
    
    slug = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True
    )

    # Immutable system group identity. System roles use their own
    # reserved group slug; every custom role belongs to the admin group.
    group_slug = db.Column(
        db.String(30),
        nullable=False,
        default=ADMIN_GROUP,
        server_default=ADMIN_GROUP,
        index=True,
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    description = db.Column(
        db.String(255)
    )

    is_system = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    permissions = db.relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    users = db.relationship(
        "UserRole",
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "group_slug IN ('super_admin', 'admin', 'user')",
            name="ck_roles_group_slug",
        ),
    )

    def __repr__(self):
        return f"<Role {self.slug}>"

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "slug": self.slug,
            "group_slug": self.group_slug,
            "name": self.name,
            "description": self.description,
            "is_system": self.is_system,
            "is_active": self.is_active
        })
        return data

@event.listens_for(Role, "before_update")
def _protect_role_identity(mapper, connection, target):
    """Role slug and system-group identity are immutable after creation."""
    state = inspect(target)

    if state.attrs.slug.history.has_changes():
        raise ValueError("Role slugs are immutable system identifiers.")

    if state.attrs.group_slug.history.has_changes():
        raise ValueError("Role groups are immutable system identifiers.")

    if state.attrs.is_system.history.has_changes():
        raise ValueError("System-role status cannot be changed after creation.")

    if target.group_slug not in ROLE_GROUPS:
        raise ValueError("Invalid role group.")

    if target.slug in ROLE_GROUPS and target.group_slug != target.slug:
        raise ValueError("System role group must match its reserved slug.")

    if target.slug not in ROLE_GROUPS and target.group_slug != ADMIN_GROUP:
        raise ValueError("Custom roles must belong to the admin group.")
