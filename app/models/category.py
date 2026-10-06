from app.extensions import db
from app.models.base import BaseModel


class FinancialCategory(BaseModel):
    """Authoritative income/expense category registry.

    System categories have user_id NULL and are available to every normal user.
    Personal categories belong to one user and require Plus/Pro access.
    """

    __tablename__ = "financial_categories"

    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "category_type", "name",
            name="uq_financial_category_owner_type_name",
        ),
        db.Index(
            "ix_financial_category_type_active",
            "category_type", "is_active",
        ),
        db.CheckConstraint(
            "category_type IN ('income', 'expense')",
            name="ck_financial_category_type",
        ),
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    category_type = db.Column(db.String(20), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    is_system = db.Column(db.Boolean, nullable=False, default=False)

    user = db.relationship(
        "User",
        backref=db.backref(
            "financial_categories",
            lazy=True,
            cascade="all, delete-orphan",
        ),
    )

    @property
    def label(self):
        return self.name

    def __repr__(self):
        owner = "system" if self.is_system else f"user:{self.user_id}"
        return f"<FinancialCategory {owner} {self.category_type}:{self.name}>"
