from datetime import datetime, timezone
from io import BytesIO
import json

from flask import Blueprint, send_file
from flask_login import login_required, current_user

from app.models.income import Income
from app.models.expense import Expense
from app.models.budget import Budget
from app.models.goal import Goal
from app.models.asset import Asset
from app.models.goal_contribution import GoalContribution
from app.models.user_settings import UserSettings
from app.models.ai_usage import AIUsage
from app.models.subscription import UserSubscription

account_bp = Blueprint("account", __name__, url_prefix="/account")


def _iso(value):
    return value.isoformat() if value else None


@account_bp.get("/export")
@login_required
def export_data():
    """Portable JSON export of the authenticated user's own financial data."""
    user = {
        "public_id": current_user.public_id,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "country": current_user.country,
        "currency": current_user.currency,
        "occupation": current_user.occupation,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }

    incomes = Income.query.filter_by(user_id=current_user.id).order_by(
        Income.received_date.desc(), Income.id.desc()
    ).all()
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(
        Expense.expense_date.desc(), Expense.id.desc()
    ).all()
    budgets = Budget.query.filter_by(user_id=current_user.id).order_by(
        Budget.start_date.desc(), Budget.id.desc()
    ).all()
    goals = Goal.query.filter_by(user_id=current_user.id).order_by(
        Goal.target_date.asc(), Goal.id.desc()
    ).all()
    assets = Asset.query.filter_by(user_id=current_user.id).order_by(Asset.id.desc()).all()
    settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    usage = AIUsage.query.filter_by(user_id=current_user.id).order_by(AIUsage.created_at.desc()).all()
    subscriptions = UserSubscription.query.filter_by(user_id=current_user.id).order_by(UserSubscription.created_at.desc()).all()

    payload = {
        "schema_version": "1.0",
        "product": "FOCOST",
        "user": user,
        "income": [
            {
                "public_id": x.public_id,
                "source": x.source,
                "category": x.category,
                "amount": float(x.amount or 0),
                "received_date": _iso(x.received_date),
                "notes": x.notes,
                "recurring": bool(x.recurring),
            } for x in incomes
        ],
        "expenses": [
            {
                "public_id": x.public_id,
                "category": x.category,
                "merchant": x.merchant,
                "description": x.description,
                "amount": float(x.amount or 0),
                "payment_method": x.payment_method,
                "expense_date": _iso(x.expense_date),
                "notes": x.notes,
                "recurring": bool(x.recurring),
                "transaction_class": getattr(x, "transaction_class", "expense"),
            } for x in expenses
        ],
        "budgets": [
            {
                "public_id": x.public_id,
                "category": x.category,
                "amount": float(x.amount or 0),
                "period": x.period,
                "start_date": _iso(x.start_date),
                "end_date": _iso(x.end_date),
                "spent": float(x.spent or 0),
            } for x in budgets
        ],
        "assets": [
            {
                "public_id": x.public_id,
                "name": x.name,
                "asset_type": x.asset_type,
                "investment_type": x.investment_type,
                "acquisition_date": _iso(x.acquisition_date),
                "acquisition_cost": float(x.acquisition_cost or 0),
                "current_value": float(x.current_value or 0),
                "quantity": x.quantity,
                "cost_basis": x.cost_basis,
                "currency": x.currency,
                "notes": x.notes,
            } for x in assets
        ],
        "settings": settings.get_preferences() if settings else {},
        "ai_usage": [
            {
                "public_id": x.public_id,
                "request_id": x.request_id,
                "provider": x.provider,
                "model": x.model,
                "input_tokens": x.input_tokens,
                "output_tokens": x.output_tokens,
                "total_tokens": x.total_tokens,
                "duration_ms": x.duration_ms,
                "estimated_cost_minor": x.estimated_cost_minor,
                "status": x.status,
                "created_at": _iso(x.created_at),
            } for x in usage
        ],
        "subscriptions": [
            {
                "public_id": x.public_id,
                "status": x.status,
                "is_trial": bool(x.is_trial),
                "trial_started_at": _iso(x.trial_started_at),
                "trial_ends_at": _iso(x.trial_ends_at),
                "current_period_start": _iso(x.current_period_start),
                "current_period_end": _iso(x.current_period_end),
                "cancel_at_period_end": bool(x.cancel_at_period_end),
            } for x in subscriptions
        ],
        "goals": [
            {
                "public_id": x.public_id,
                "title": x.title,
                "goal_type": x.goal_type,
                "target_amount": float(x.target_amount or 0),
                "target_date": _iso(x.target_date),
                "priority": x.priority,
                "status": x.status,
                "notes": x.notes,
                "reminder": bool(x.reminder),
                "contributions": [
                    {
                        "public_id": c.public_id,
                        "amount": float(c.amount or 0),
                        "date": _iso(getattr(c, "contribution_date", None) or getattr(c, "date", None)),
                        "notes": getattr(c, "note", None),
                        "expense_id": getattr(c, "expense_id", None),
                    }
                    for c in x.contributions
                ],
            } for x in goals
        ],
    }

    raw = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    return send_file(
        BytesIO(raw),
        mimetype="application/json",
        as_attachment=True,
        download_name=(
            f"focost_data_export_"
            f"{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.json"
        ),
    )
