from app.extensions import db
from app.models.base import BaseModel


class Asset(BaseModel):
    __tablename__ = "assets"
    __table_args__ = (
        db.CheckConstraint("current_value >= 0", name="ck_assets_current_value_nonnegative"),
        db.CheckConstraint("acquisition_cost >= 0", name="ck_assets_acquisition_cost_nonnegative"),
        db.CheckConstraint("cost_basis IS NULL OR cost_basis >= 0", name="ck_assets_cost_basis_nonnegative"),
    )

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    asset_type = db.Column(db.String(80), nullable=False, index=True)
    investment_type = db.Column(db.String(100))
    acquisition_date = db.Column(db.Date)
    acquisition_cost = db.Column(db.Float, nullable=False, default=0)
    current_value = db.Column(db.Float, nullable=False, default=0)
    quantity = db.Column(db.Float)
    cost_basis = db.Column(db.Float)
    currency = db.Column(db.String(10), nullable=False, default="NGN")
    notes = db.Column(db.Text)

    @property
    def is_investment(self):
        return (self.asset_type or "").strip().lower() == "investment"

    # Optional source cash-outflow used when an investment is created from an expense.
    source_expense_id = db.Column(
        db.Integer,
        db.ForeignKey("expenses.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True
    )

    source_expense = db.relationship(
        "Expense",
        foreign_keys=[source_expense_id],
        backref=db.backref("investment_asset", uselist=False)
    )

    user = db.relationship("User", backref=db.backref("assets", lazy=True, cascade="all, delete-orphan"))

    @property
    def gain_loss(self):
        return float(self.current_value or 0) - float(self.cost_basis if self.cost_basis is not None else self.acquisition_cost or 0)

    @property
    def return_pct(self):
        basis = float(self.cost_basis if self.cost_basis is not None else self.acquisition_cost or 0)
        if basis <= 0:
            return None
        return round((self.gain_loss / basis) * 100, 2)
