from app.extensions import db
from app.models.base import BaseModel


class AIUsage(BaseModel):
    __tablename__ = "ai_usage"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    request_id = db.Column(db.String(80), unique=True, nullable=False, index=True)
    provider = db.Column(db.String(80))
    model = db.Column(db.String(160))
    input_tokens = db.Column(db.Integer, nullable=False, default=0)
    output_tokens = db.Column(db.Integer, nullable=False, default=0)
    total_tokens = db.Column(db.Integer, nullable=False, default=0)
    duration_ms = db.Column(db.Integer)
    estimated_cost_minor = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(30), nullable=False, default="success", index=True)
    error_message = db.Column(db.Text)

    # Identifies the subscription/trial billing period consumed by this request.
    # Historical usage remains immutable and can be analysed across periods.
    billing_period_start = db.Column(
        db.DateTime,
        nullable=True,
        index=True
    )

    user = db.relationship("User", backref=db.backref("ai_usage", lazy=True, cascade="all, delete-orphan"))
