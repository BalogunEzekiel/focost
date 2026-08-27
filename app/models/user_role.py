from app.extensions import db
from app.models.base import BaseModel


class UserRole(BaseModel):

    __tablename__ = "user_roles"

    # ==========================================================
    # ONE USER = ONE ROLE
    # ==========================================================

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            name="uq_user_single_role"
        ),
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    role_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "roles.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    assigned_by_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id"
        ),
        nullable=True,
        index=True
    )

    # ==========================================================
    # RELATIONSHIPS
    # ==========================================================

    user = db.relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="role_assignment",
        lazy="selectin"
    )

    role = db.relationship(
        "Role",
        back_populates="users",
        lazy="selectin"
    )

    assigned_by = db.relationship(
        "User",
        foreign_keys=[assigned_by_id],
        lazy="selectin"
    )

    def __repr__(self):

        role_name = (
            self.role.slug
            if self.role
            else "none"
        )

        return (
            f"<UserRole "
            f"user={self.user_id} "
            f"role={role_name}>"
        )