from datetime import datetime
from datetime import timedelta

from app.models.user import User
from app.models.income import Income
from app.models.expense import Expense
from app.extensions import db


class AdminService:

    @staticmethod
    def dashboard():

        today = datetime.utcnow()

        last_30 = today - timedelta(days=30)

        total_users = User.query.count()

        new_users = User.query.filter(
            User.created_at >= last_30
        ).count()

        active_users = User.query.filter_by(
            is_active=True
        ).count()

        total_income = db.session.query(
            db.func.coalesce(
                db.func.sum(Income.amount),
                0
            )
        ).scalar()

        total_expense = db.session.query(
            db.func.coalesce(
                db.func.sum(Expense.amount),
                0
            )
        ).scalar()

        total_transactions = Income.query.count() + Expense.query.count()

        return {

            "total_users": total_users,

            "active_users": active_users,

            "new_users": new_users,

            "total_income": total_income,

            "total_expense": total_expense,

            "total_transactions": total_transactions

        }