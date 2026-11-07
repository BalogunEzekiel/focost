from app.extensions import db
from app.models.base import BaseModel


class ExchangeRate(BaseModel):
    """Auditable FX quote snapshot for a currency pair and effective date."""

    __tablename__ = "exchange_rates"
    __table_args__ = (
        db.UniqueConstraint("base_currency", "quote_currency", "rate_date", name="uq_exchange_rate_pair_date"),
        db.CheckConstraint("rate > 0", name="ck_exchange_rates_rate_positive"),
    )

    base_currency = db.Column(db.String(3), nullable=False, index=True)
    quote_currency = db.Column(db.String(3), nullable=False, index=True)
    rate = db.Column(db.Numeric(24, 12), nullable=False)
    rate_date = db.Column(db.Date, nullable=False, index=True)
    source = db.Column(db.String(80), nullable=False)
    fetched_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    is_manual = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
