from datetime import datetime, timedelta, timezone
from sqlalchemy import func

from app.extensions import db
from app.models.user import User
from app.models.income import Income
from app.models.expense import Expense
from app.models.budget import Budget
from app.models.goal import Goal
from app.models.goal_contribution import GoalContribution
from app.models.asset import Asset
from app.models.feedback import Feedback
from app.models.subscription import UserSubscription, SubscriptionPlan


class AdminAnalyticsService:
    """Authoritative aggregation layer for the administrative analytics center."""

    @staticmethod
    def _user_ids(plan="all", status="all"):
        query = User.query
        if status == "active":
            query = query.filter(User.is_active.is_(True))
        elif status == "inactive":
            query = query.filter(User.is_active.is_(False))

        users = query.all()
        if plan == "all":
            return [u.id for u in users]

        result = []
        for user in users:
            if user.role_slug in {"admin", "super_admin"}:
                continue
            sub = (
                UserSubscription.query
                .filter_by(user_id=user.id)
                .order_by(UserSubscription.created_at.desc())
                .first()
            )
            if plan == "free_trial":
                matched = bool(sub and sub.is_trial and sub.status == "trial")
            else:
                matched = bool(
                    sub and not sub.is_trial and sub.plan and sub.plan.slug == plan
                )
            if matched:
                result.append(user.id)
        return result

    @staticmethod
    def snapshot(period="all", plan="all", status="all"):
        user_ids = AdminAnalyticsService._user_ids(plan, status)
        base = {}
        now = datetime.now(timezone.utc)

        if period == "30d":
            start = now - timedelta(days=30)
        elif period == "90d":
            start = now - timedelta(days=90)
        elif period == "ytd":
            start = datetime(now.year, 1, 1, tzinfo=timezone.utc)
        else:
            start = None

        def scoped(query, created_column):
            query = query.filter(query._raw_columns[0] == query._raw_columns[0]) if False else query
            if user_ids:
                query = query.filter(created_column.in_(user_ids))
            else:
                query = query.filter(False)
            return query

        user_query = User.query.filter(User.id.in_(user_ids)) if user_ids else User.query.filter(False)
        total_users = user_query.count()
        active = user_query.filter(User.is_active.is_(True)).count()
        inactive = user_query.filter(User.is_active.is_(False)).count()

        income_q = db.session.query(func.coalesce(func.sum(Income.amount), 0)).filter(
            Income.is_active.is_(True), Income.user_id.in_(user_ids) if user_ids else False
        )
        expense_q = db.session.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
            Expense.is_active.is_(True), Expense.user_id.in_(user_ids) if user_ids else False
        )
        budget_q = db.session.query(func.coalesce(func.sum(Budget.amount), 0)).filter(
            Budget.is_active.is_(True), Budget.user_id.in_(user_ids) if user_ids else False
        )
        spent_q = db.session.query(func.coalesce(func.sum(Budget.spent), 0)).filter(
            Budget.is_active.is_(True), Budget.user_id.in_(user_ids) if user_ids else False
        )
        contribution_q = db.session.query(func.coalesce(func.sum(GoalContribution.amount), 0)).filter(
            GoalContribution.user_id.in_(user_ids) if user_ids else False
        )
        investment_value_q = db.session.query(func.coalesce(func.sum(Asset.current_value), 0)).filter(
            Asset.is_active.is_(True),
            Asset.asset_type.ilike("investment"),
            Asset.user_id.in_(user_ids) if user_ids else False,
        )

        if start:
            income_q = income_q.filter(Income.received_date >= start.date())
            expense_q = expense_q.filter(Expense.expense_date >= start.date())
            budget_q = budget_q.filter(Budget.start_date >= start.date())
            contribution_q = contribution_q.filter(GoalContribution.created_at >= start)
            investment_value_q = investment_value_q.filter(Asset.created_at >= start)

        income = float(income_q.scalar() or 0)
        expenses = float(expense_q.scalar() or 0)
        budget_total = float(budget_q.scalar() or 0)
        budget_spent = float(spent_q.scalar() or 0)
        contribution_total = float(contribution_q.scalar() or 0)
        investment_value = float(investment_value_q.scalar() or 0)

        goal_q = Goal.query.filter(Goal.is_active.is_(True), Goal.user_id.in_(user_ids) if user_ids else False)
        asset_q = Asset.query.filter(
            Asset.is_active.is_(True),
            Asset.asset_type.ilike("investment"),
            Asset.user_id.in_(user_ids) if user_ids else False,
        )
        budget_count = Budget.query.filter(Budget.is_active.is_(True), Budget.user_id.in_(user_ids) if user_ids else False).count()
        feedback_count = Feedback.query.filter(Feedback.is_active.is_(True), Feedback.submitted_by_id.in_(user_ids) if user_ids else False).count()

        plan_counts = {}
        for slug in ("free_trial", "basic", "plus", "pro"):
            plan_counts[slug] = len(AdminAnalyticsService._user_ids(slug, status))

        return {
            "filters": {"period": period, "plan": plan, "status": status},
            "users": {"total": total_users, "active": active, "inactive": inactive},
            "finance": {"income": income, "expenses": expenses, "savings": income - expenses},
            "budgets": {
                "total": budget_total, "spent": budget_spent,
                "remaining": max(budget_total - budget_spent, 0),
                "count": budget_count,
            },
            "goals": {
                "count": goal_q.count(),
                "contributions": contribution_total,
                "completed": goal_q.filter(Goal.status == "Completed").count(),
            },
            "investments": {"count": asset_q.count(), "value": investment_value},
            "plans": plan_counts,
            "feedback": {"total": feedback_count},
            "cohorts": {
                "active_users": active,
                "inactive_users": inactive,
                "trial_or_free": plan_counts["free_trial"] + plan_counts["basic"],
                "paid_users": plan_counts["plus"] + plan_counts["pro"],
            },
        }
