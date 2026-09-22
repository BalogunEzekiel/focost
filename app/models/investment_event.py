from app.extensions import db
from app.models.base import BaseModel


class InvestmentEvent(BaseModel):
    """Immutable audit trail for investment funding, valuation and liquidation events."""

    __tablename__ = "investment_events"
    __table_args__ = (db.CheckConstraint("amount >= 0", name="ck_investment_event_amount_nonnegative"),)

    asset_id = db.Column(
        db.Integer,
        db.ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = db.Column(db.String(30), nullable=False, index=True)
    event_date = db.Column(db.Date, nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False, default=0)
    previous_value = db.Column(db.Float)
    new_value = db.Column(db.Float)
    cost_basis_change = db.Column(db.Float, nullable=False, default=0)
    realized_gain_loss = db.Column(db.Float, nullable=False, default=0)
    proceeds = db.Column(db.Float, nullable=False, default=0)
    expense_id = db.Column(db.Integer, db.ForeignKey("expenses.id", ondelete="SET NULL"), unique=True)
    income_id = db.Column(db.Integer, db.ForeignKey("income.id", ondelete="SET NULL"), unique=True)
    notes = db.Column(db.Text)

    asset = db.relationship(
        "Asset",
        backref=db.backref("investment_events", lazy=True, cascade="all, delete-orphan"),
    )
    user = db.relationship("User", backref=db.backref("investment_events", lazy=True))
    expense = db.relationship("Expense", foreign_keys=[expense_id], backref=db.backref("investment_event_expense", uselist=False))
    income = db.relationship("Income", foreign_keys=[income_id], backref=db.backref("investment_event_income", uselist=False))
