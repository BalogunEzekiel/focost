from app.extensions import db
from app.models.budget import Budget
from app.models.user import User

class BudgetService:

    @staticmethod
    def create_budget(form, user_id):

        user = db.session.get(User, user_id)
        budget = Budget(
            user_id=user_id,
            currency=(user.base_currency if user else "NGN") or "NGN",
            category=form.category.data,
            amount=float(form.amount.data),
            period=form.period.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            spent=0,
        )

        db.session.add(budget)
        db.session.commit()

        return budget