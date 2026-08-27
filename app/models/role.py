from app.extensions import db

from app.models.base import BaseModel


class Role(BaseModel):
    
    __tablename__ = "roles"
    
    slug = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True
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

    def __repr__(self):
        return f"<Role {self.slug}>"

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "is_system": self.is_system,
            "is_active": self.is_active
        })
        return data