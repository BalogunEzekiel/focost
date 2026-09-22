from datetime import datetime, timedelta
import json
from sqlalchemy import func

from app.extensions import db
from app.models.user import User
from app.models.subscription import (
    SubscriptionPlan, UserSubscription, PaymentTransaction,
    PaystackCustomer, SubscriptionEvent
)
from app.services.notification_service import NotificationService


TRIAL_DAYS = 30


class SubscriptionService:
    """Subscription domain service. Billing is deliberately independent of AI processing."""

    @staticmethod
    def plans(public_only=True):
        q = SubscriptionPlan.query
        if public_only:
            q = q.filter_by(is_public=True, is_active=True)
        return q.order_by(SubscriptionPlan.sort_order.asc()).all()

    @staticmethod
    def get_plan(plan_id):
        return SubscriptionPlan.query.filter_by(id=plan_id, is_active=True).first()

    @staticmethod
    def start_trial(user, commit=True):
        existing = UserSubscription.query.filter_by(user_id=user.id).order_by(UserSubscription.created_at.desc()).first()
        if existing:
            return existing
        now = datetime.utcnow()
        trial = UserSubscription(
            user_id=user.id,
            status="trial",
            is_trial=True,
            trial_started_at=now,
            trial_ends_at=now + timedelta(days=TRIAL_DAYS),
            provider="paystack",
        )
        db.session.add(trial)
        db.session.flush()
        db.session.add(SubscriptionEvent(
            user_id=user.id, subscription_id=trial.id,
            event_type="trial_started", new_status="trial", source="system"
        ))
        if commit:
            db.session.commit()
        NotificationService.create(
            user.id, "FOCOST free trial started",
            f"Your 30-day FOCOST trial is active until {trial.trial_ends_at:%d %b %Y}.",
            notification_type="subscription", level="info", priority="normal",
            unique_key=f"trial-start:{user.id}:{trial.id}", commit=commit,
        )
        return trial

    @staticmethod
    def current(user_id, create_trial=True):
        now = datetime.utcnow()
        sub = UserSubscription.query.filter_by(user_id=user_id).order_by(UserSubscription.created_at.desc()).first()
        if not sub and create_trial:
            from app.models.user import User
            user = db.session.get(User, user_id)
            if user:
                sub = SubscriptionService.start_trial(user)
        if not sub:
            return None
        if sub.status == "trial" and sub.trial_ends_at and sub.trial_ends_at <= now:
            sub.status = "expired"
            sub.is_trial = False
            db.session.add(SubscriptionEvent(user_id=user_id, subscription_id=sub.id, event_type="trial_expired", old_status="trial", new_status="expired", source="system"))
            db.session.commit()
        elif sub.status in {"active", "past_due"} and sub.current_period_end and sub.current_period_end <= now:
            if sub.cancel_at_period_end or sub.status != "past_due":
                sub.status = "expired"
                db.session.add(SubscriptionEvent(user_id=user_id, subscription_id=sub.id, event_type="subscription_expired", old_status="active", new_status="expired", source="system"))
                db.session.commit()
        return sub

    @staticmethod
    def has_access(user_id, feature=None):
        sub = SubscriptionService.current(user_id)
        if not sub or not sub.is_active_access:
            return False
        if not feature or sub.is_trial or not sub.plan:
            return True
        return bool(sub.plan.entitlements().get(feature, False))

    @staticmethod
    def entitlements(user_id):
        sub = SubscriptionService.current(user_id)
        if not sub:
            return {"active": False, "status": "none"}
        if sub.is_trial:
            import os
            return {
                "active": sub.is_active_access, "status": "trial", "plan_name": "Free Trial",
                "ai_token_limit": int(os.getenv("FOCOST_TRIAL_AI_TOKEN_LIMIT", "40000")),
                "ai_request_limit": int(os.getenv("FOCOST_TRIAL_AI_REQUEST_LIMIT", "200")),
            }
        plan = sub.plan
        return {
            "active": sub.is_active_access,
            "status": sub.status,
            "plan_name": plan.name if plan else "Subscription",
            "plan_slug": plan.slug if plan else None,
            "ai_token_limit": plan.ai_token_limit if plan else 0,
            "ai_request_limit": plan.ai_request_limit if plan else 0,
            "transaction_limit": plan.transaction_limit if plan else None,
            **(plan.entitlements() if plan else {}),
        }

    @staticmethod
    def paystack_plan_code(plan):
        import os
        return plan.paystack_plan_code or os.getenv(f"PAYSTACK_PLAN_{plan.slug.upper()}", "").strip() or None

    @staticmethod
    def create_transaction(user_id, plan, reference, metadata=None):
        tx = PaymentTransaction.query.filter_by(reference=reference).first()
        if tx:
            return tx
        tx = PaymentTransaction(
            user_id=user_id, plan_id=plan.id, provider="paystack", reference=reference,
            amount_minor=plan.amount_minor, currency=plan.currency, status="initialized",
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        )
        db.session.add(tx)
        db.session.commit()
        return tx

    @staticmethod
    def activate_from_payment(tx, provider_data=None):
        provider_data = provider_data or {}
        plan = tx.plan or SubscriptionPlan.query.get(tx.plan_id)
        if not plan:
            raise ValueError("Subscription plan no longer exists.")
        now = datetime.utcnow()
        sub = UserSubscription.query.filter_by(user_id=tx.user_id).order_by(UserSubscription.created_at.desc()).first()
        old_status = sub.status if sub else None
        if not sub:
            sub = UserSubscription(user_id=tx.user_id, plan_id=plan.id, provider="paystack")
            db.session.add(sub)
            db.session.flush()
        sub.plan_id = plan.id
        sub.status = "active"
        sub.is_trial = False
        sub.started_at = sub.started_at or now
        sub.current_period_start = now
        sub.current_period_end = now + timedelta(days=30)
        next_payment = provider_data.get("next_payment_date")
        if next_payment:
            try:
                from datetime import datetime as dt
                sub.current_period_end = dt.fromisoformat(next_payment.replace("Z", "+00:00")).replace(tzinfo=None)
            except (TypeError, ValueError):
                pass
        sub.cancel_at_period_end = False
        sub.canceled_at = None
        if provider_data.get("subscription_code"):
            sub.provider_subscription_code = provider_data["subscription_code"]
        if provider_data.get("email_token"):
            sub.provider_email_token = provider_data["email_token"]
        tx.subscription_id = sub.id
        tx.status = "success"
        tx.paid_at = now
        tx.gateway_response = json.dumps(provider_data, ensure_ascii=False)
        db.session.add(SubscriptionEvent(user_id=tx.user_id, subscription_id=sub.id, event_type="payment_activated", old_status=old_status, new_status="active", source="paystack"))
        db.session.commit()
        NotificationService.create(tx.user_id, "Subscription activated", f"Your {plan.name} subscription is now active.", notification_type="subscription", level="success", priority="high", action_url="/billing", unique_key=f"subscription-active:{sub.id}:{tx.reference}")
        return sub

    @staticmethod
    def can_add_transaction(user_id):
        ent = SubscriptionService.entitlements(user_id)
        limit = ent.get("transaction_limit")
        if not limit:
            return True, None
        from app.models.income import Income
        from app.models.expense import Expense
        count = Income.query.filter_by(user_id=user_id, is_active=True).count() + Expense.query.filter_by(user_id=user_id, is_active=True).count()
        if count >= limit:
            return False, f"Your {ent.get('plan_name', 'subscription')} allows up to {limit:,} tracked transactions. Upgrade your plan to add more."
        return True, None

    @staticmethod
    def cancel_at_period_end(user_id):
        sub = SubscriptionService.current(user_id)
        if not sub or sub.status not in {"active", "past_due"}:
            raise ValueError("No active subscription is available to cancel.")
        sub.cancel_at_period_end = True
        sub.canceled_at = datetime.utcnow()
        db.session.add(SubscriptionEvent(user_id=user_id, subscription_id=sub.id, event_type="cancellation_requested", old_status=sub.status, new_status=sub.status, source="user"))
        db.session.commit()
        NotificationService.create(user_id, "Subscription cancellation scheduled", "Your paid access will remain available through the current billing period.", notification_type="subscription", level="warning", priority="high", unique_key=f"cancel:{sub.id}")
        return sub

    @staticmethod
    def admin_summary():
        return {
            "total_users": User.query.count(),
            "active_subscriptions": UserSubscription.query.filter_by(status="active").count(),
            "trial_subscriptions": UserSubscription.query.filter_by(status="trial").count(),
            "expired_subscriptions": UserSubscription.query.filter(UserSubscription.status.in_(["expired", "canceled"])).count(),
            "plans": SubscriptionService.plans(False),
            "subscriptions": UserSubscription.query.order_by(UserSubscription.created_at.desc()).limit(100).all(),
            "payment_transactions": PaymentTransaction.query.order_by(PaymentTransaction.created_at.desc()).limit(100).all(),
        }
