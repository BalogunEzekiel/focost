from app.extensions import db

from app.models.base import BaseModel


class RolePermission(BaseModel):
    __tablename__ = "role_permissions"

    __table_args__ = (
        db.UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_role_permission"
        ),
    )

    role_id = db.Column(
        db.Integer,
        db.ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    permission_id = db.Column(
        db.Integer,
        db.ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    role = db.relationship(
        "Role",
        back_populates="permissions",
        lazy="selectin"
    )

    permission = db.relationship(
        "Permission",
        back_populates="roles",
        lazy="selectin"
    )

    def __repr__(self):
        return f"<RolePermission {self.role_id}:{self.permission_id}>"