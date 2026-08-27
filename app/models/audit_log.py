from app.extensions import db
from app.models.base import BaseModel

class AuditLog(BaseModel):

    __tablename__ = "audit_logs"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
        index=True
    )

    action = db.Column(
        db.String(120),
        nullable=False,
        index=True
    )

    category = db.Column(
        db.String(60),
        nullable=False,
        index=True
    )

    resource = db.Column(
        db.String(120),
        nullable=True
    )

    resource_id = db.Column(
        db.String(120),
        nullable=True
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    ip_address = db.Column(
        db.String(50)
    )

    user_agent = db.Column(
        db.Text
    )

    request_path = db.Column(
        db.String(255)
    )

    http_method = db.Column(
        db.String(10)
    )

    endpoint = db.Column(
        db.String(255)
    )

    method = db.Column(
        db.String(10)
    )

    status = db.Column(
        db.String(20),
        default="success"
    )

    session_id = db.Column(
        db.String(255)
    )
    
    extra_data = db.Column(
        db.JSON,
        nullable=True
    )

    user = db.relationship(
        "User",
        back_populates="audit_logs",
        lazy="selectin"
    )

    def __repr__(self):
        return f"<AuditLog {self.action}>"