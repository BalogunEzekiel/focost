from app.extensions import db

from app.models.base import BaseModel


class Permission(BaseModel):
    
    __tablename__ = "permissions"

    __table_args__ = (
        db.UniqueConstraint(
            "module",
            "action",
            name="uq_permission_module_action"
        ),
    )

    code = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
        index=True
    )

    module = db.Column(
        db.String(80),
        nullable=False,
        index=True
    )

    action = db.Column(
        db.String(50),
        nullable=False
    )

    name = db.Column(
        db.String(120),
        nullable=False
    )

    description = db.Column(
        db.String(255)
    )

    roles = db.relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self):
        return f"<Permission {self.code}>"

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "code": self.code,
            "module": self.module,
            "action": self.action,
            "name": self.name,
            "description": self.description
        })
        return data