from app.extensions import db
from app.models.category import FinancialCategory
from app.services.subscription_gate import SubscriptionGate


SYSTEM_CATEGORIES = {
    "income": (
        "Salary", "Business", "Freelance", "Investment", "Rental Income",
        "Commission", "Ride Business", "Gift", "Bonus", "Dividend", "Other",
    ),
    "expense": (
        "Food", "Transportation", "Housing", "Telephone", "Utilities", "Gas",
        "Healthcare", "Education", "Entertainment", "Support/Assistance",
        "Shopping", "Petrol", "Petrol Contribution", "Insurance", "Travel",
        "Rent", "Repairs", "Family", "Toiletries", "Clothing", "Personal Care",
        "Tax", "Gift", "Salary", "Business", "Other",
    ),
}


class CategoryService:
    """Single source of truth for financial categories and budget categories."""

    @staticmethod
    def ensure_system_categories(commit=True):
        created = 0
        for category_type, names in SYSTEM_CATEGORIES.items():
            for name in names:
                existing = FinancialCategory.query.filter_by(
                    user_id=None,
                    category_type=category_type,
                    name=name,
                ).first()
                if existing:
                    if not existing.is_system:
                        existing.is_system = True
                    existing.is_active = True
                    continue
                db.session.add(
                    FinancialCategory(
                        user_id=None,
                        category_type=category_type,
                        name=name,
                        is_system=True,
                        is_active=True,
                    )
                )
                created += 1
        if commit and created:
            db.session.commit()
        return created

    @staticmethod
    def can_customize(user_id):
        return SubscriptionGate.has_paid_plan(user_id, {"plus", "pro"})

    @staticmethod
    def list_for_user(user_id, category_type, include_inactive=False):
        CategoryService.ensure_system_categories()
        ownership_filter = FinancialCategory.user_id.is_(None)
        if CategoryService.can_customize(user_id):
            ownership_filter = db.or_(
                FinancialCategory.user_id.is_(None),
                FinancialCategory.user_id == user_id,
            )
        query = FinancialCategory.query.filter(
            FinancialCategory.category_type == category_type,
            ownership_filter,
        )
        if not include_inactive:
            query = query.filter(FinancialCategory.is_active.is_(True))
        return query.order_by(
            FinancialCategory.user_id.isnot(None),
            FinancialCategory.name.asc(),
        ).all()

    @staticmethod
    def names_for_user(user_id, category_type):
        return [item.name for item in CategoryService.list_for_user(user_id, category_type)]

    @staticmethod
    def is_valid_for_user(user_id, category_type, name):
        name = (name or "").strip()
        if not name:
            return False
        return FinancialCategory.query.filter(
            FinancialCategory.category_type == category_type,
            FinancialCategory.name == name,
            FinancialCategory.is_active.is_(True),
            db.or_(
                FinancialCategory.user_id.is_(None),
                FinancialCategory.user_id == user_id,
            ),
        ).first() is not None

    @staticmethod
    def create_personal(user_id, category_type, name, description=None):
        if not CategoryService.can_customize(user_id):
            raise PermissionError(
                "Personal categories are available only on Plus and Pro plans."
            )

        category_type = (category_type or "").strip().lower()
        name = " ".join((name or "").strip().split())

        if category_type not in SYSTEM_CATEGORIES:
            raise ValueError("Invalid category type.")

        if not name or len(name) > 100:
            raise ValueError("Category name must contain 1 to 100 characters.")

        if FinancialCategory.query.filter(
            FinancialCategory.category_type == category_type,
            FinancialCategory.name.ilike(name),
            db.or_(
                FinancialCategory.user_id.is_(None),
                FinancialCategory.user_id == user_id,
            ),
        ).first():
            raise ValueError("A category with this name already exists.")

        category = FinancialCategory(
            user_id=user_id,
            category_type=category_type,
            name=name,
            description=(description or "").strip()[:255] or None,
            is_system=False,
            is_active=True,
        )
        db.session.add(category)
        db.session.commit()
        return category

    @staticmethod
    def update_personal(user_id, category_id, name, description=None):
        if not CategoryService.can_customize(user_id):
            raise PermissionError(
                "Personal categories are available only on Plus and Pro plans."
            )

        category = FinancialCategory.query.filter_by(
            id=category_id,
            user_id=user_id,
            is_system=False,
            is_active=True,
        ).first()
        if not category:
            raise ValueError("Personal category not found.")

        name = " ".join((name or "").strip().split())
        if not name or len(name) > 100:
            raise ValueError("Category name must contain 1 to 100 characters.")

        duplicate = FinancialCategory.query.filter(
            FinancialCategory.id != category.id,
            FinancialCategory.category_type == category.category_type,
            FinancialCategory.name.ilike(name),
            FinancialCategory.user_id == user_id,
        ).first()
        if duplicate:
            raise ValueError("A personal category with this name already exists.")

        category.name = name
        category.description = (description or "").strip()[:255] or None
        db.session.commit()
        return category

    @staticmethod
    def archive_personal(user_id, category_id):
        if not CategoryService.can_customize(user_id):
            raise PermissionError(
                "Personal categories are available only on Plus and Pro plans."
            )

        category = FinancialCategory.query.filter_by(
            id=category_id,
            user_id=user_id,
            is_system=False,
            is_active=True,
        ).first()
        if not category:
            raise ValueError("Personal category not found.")

        category.is_active = False
        db.session.commit()
        return category

    @staticmethod
    def budget_categories(user_id):
        # Budgets intentionally use the expense registry; there is no
        # independent budget-category source.
        return CategoryService.list_for_user(user_id, "expense")
