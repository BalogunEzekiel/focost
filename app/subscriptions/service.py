from datetime import datetime, timedelta
import json

from app.extensions import db
from app.models.user import User
from app.models.subscription import (
    SubscriptionPlan,
    UserSubscription,
    PaymentTransaction,
    PaystackCustomer,
    SubscriptionEvent,
)
from app.services.notification_service import NotificationService
from app.utils.timezone import as_utc, utc_now
from app.models.role import Role
from app.models.user_role import UserRole


TRIAL_DAYS = 30


class SubscriptionService:
    """Subscription domain service. Billing is deliberately independent of AI processing."""

    @staticmethod
    def ai_context(user_id):
        """Return safe, database-derived subscription context for FOCOST AI.

        Payment-provider secrets, provider subscription codes, and payment
        credentials are deliberately excluded. SubscriptionService remains
        the authoritative source for plan and subscription facts.
        """
        user = db.session.get(User, user_id)

        plans = []
        for plan in SubscriptionService.plans(public_only=True):
            entitlements = plan.entitlements()
            plans.append({
                "slug": plan.slug,
                "name": plan.name,
                "description": plan.description,
                "price": round((plan.amount_minor or 0) / 100, 2),
                "currency": plan.currency,
                "interval": plan.interval,
                "ai_token_limit": plan.ai_token_limit,
                "ai_request_limit": plan.ai_request_limit,
                "transaction_limit": plan.transaction_limit,
                "features": entitlements,
            })

        if user and user.is_admin_group:
            return {
                "account_type": "administrator",
                "current": {
                    "status": "not_applicable",
                    "plan_name": "Administrator",
                },
                "plans": plans,
                "billing": {
                    "available": False,
                    "upgrade_route": "/billing/",
                },
            }

        sub = SubscriptionService.current(user_id)
        entitlements = SubscriptionService.entitlements(user_id)

        current = None
        if sub:
            current = {
                "status": sub.status,
                "is_trial": bool(sub.is_trial),
                "plan_name": sub.plan.name if sub.plan else "Free Trial",
                "plan_slug": sub.plan.slug if sub.plan else None,
                "start_date": (sub.start_date.isoformat() if sub.start_date else None),
                "end_date": (sub.end_date.isoformat() if sub.end_date else None),
                "current_period_start": (sub.current_period_start.isoformat() if sub.current_period_start else None),
                "current_period_end": (sub.current_period_end.isoformat() if sub.current_period_end else None),
                "cancel_at_period_end": bool(sub.cancel_at_period_end),
                "active_access": bool(sub.is_active_access),
            }

        return {
            "account_type": "user",
            "current": current,
            "entitlements": entitlements,
            "plans": plans,
            "billing": {
                "available": True,
                "billing_page": "/billing/",
                "initialize_payment": "/billing/initialize",
                "cancel_subscription": "/billing/cancel",
                "process": [
                    "Open FOCOST Plan & Billing.",
                    "Choose an available plan.",
                    "Start payment through FOCOST.",
                    "Complete payment with the payment provider.",
                    "FOCOST verifies the payment before activating the subscription.",
                ],
            },
        }

    @staticmethod
    def plans(public_only=True):
        q = SubscriptionPlan.query

        if public_only:
            q = q.filter_by(
                is_public=True,
                is_active=True,
            )

        return q.order_by(
            SubscriptionPlan.sort_order.asc()
        ).all()

    @staticmethod
    def get_plan(plan_id):
        return SubscriptionPlan.query.filter_by(
            id=plan_id,
            is_active=True,
        ).first()

    @staticmethod
    def start_trial(user, commit=True):
        if user.is_admin_group:
            return None

        existing = (
            UserSubscription.query
            .filter_by(user_id=user.id)
            .order_by(UserSubscription.created_at.desc())
            .first()
        )

        if existing:
            return existing

        now = utc_now()

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

        db.session.add(
            SubscriptionEvent(
                user_id=user.id,
                subscription_id=trial.id,
                event_type="trial_started",
                new_status="trial",
                source="system",
            )
        )

        if commit:
            db.session.commit()

        NotificationService.create(
            user.id,
            "FOCOST free trial started",
            (
                "Your 30-day FOCOST trial is active until "
                f"{trial.trial_ends_at:%d %b %Y}."
            ),
            notification_type="subscription",
            level="info",
            priority="normal",
            unique_key=f"trial-start:{user.id}:{trial.id}",
            commit=commit,
        )

        return trial

    @staticmethod
    def current(user_id, create_trial=True):
        # Administrators are system operators, not FOCOST plan subscribers.
        # They never receive trials, paid plans, or billing state.
        user = db.session.get(User, user_id)
        if user and user.is_admin_group:
            return None

        now = utc_now()

        sub = (
            UserSubscription.query
            .filter_by(user_id=user_id)
            .order_by(UserSubscription.created_at.desc())
            .first()
        )

        if not sub and create_trial:
            user = db.session.get(
                User,
                user_id,
            )

            if user:
                sub = SubscriptionService.start_trial(user)

        if not sub:
            return None

        trial_ends_at = (
            as_utc(sub.trial_ends_at)
            if sub.trial_ends_at
            else None
        )

        current_period_end = (
            as_utc(sub.current_period_end)
            if sub.current_period_end
            else None
        )

        if (
            sub.status == "trial"
            and trial_ends_at
            and trial_ends_at <= now
        ):
            sub.status = "expired"
            sub.is_trial = False

            db.session.add(
                SubscriptionEvent(
                    user_id=user_id,
                    subscription_id=sub.id,
                    event_type="trial_expired",
                    old_status="trial",
                    new_status="expired",
                    source="system",
                )
            )

            db.session.commit()

        elif (
            sub.status in {"active", "past_due"}
            and current_period_end
            and current_period_end <= now
        ):
            if (
                sub.cancel_at_period_end
                or sub.status != "past_due"
            ):
                old_status = sub.status

                sub.status = "expired"

                db.session.add(
                    SubscriptionEvent(
                        user_id=user_id,
                        subscription_id=sub.id,
                        event_type="subscription_expired",
                        old_status=old_status,
                        new_status="expired",
                        source="system",
                    )
                )

                db.session.commit()

        return sub

    @staticmethod
    def has_access(user_id, feature=None):
        sub = SubscriptionService.current(user_id)

        if not sub or not sub.is_active_access:
            return False

        if not feature or sub.is_trial or not sub.plan:
            return True

        return bool(
            sub.plan.entitlements().get(feature, False)
        )

    @staticmethod
    def entitlements(user_id):
        user = db.session.get(User, user_id)

        if user and user.is_admin_group:
            return {
                "active": False,
                "status": "not_applicable",
                "plan_name": "Administrator",
                "plan_slug": None,
                "ai_token_limit": None,
                "ai_request_limit": None,
                "transaction_limit": None,
            }

        sub = SubscriptionService.current(user_id)

        if not sub:
            return {
                "active": False,
                "status": "none",
            }

        if sub.is_trial:
            import os

            return {
                "active": sub.is_active_access,
                "status": "trial",
                "plan_name": "Free Trial",
                "ai_token_limit": int(
                    os.getenv(
                        "FOCOST_TRIAL_AI_TOKEN_LIMIT",
                        "40000",
                    )
                ),
                "ai_request_limit": int(
                    os.getenv(
                        "FOCOST_TRIAL_AI_REQUEST_LIMIT",
                        "200",
                    )
                ),
            }

        plan = sub.plan

        return {
            "active": sub.is_active_access,
            "status": sub.status,
            "plan_name": (
                plan.name
                if plan
                else "Subscription"
            ),
            "plan_slug": (
                plan.slug
                if plan
                else None
            ),
            "ai_token_limit": (
                plan.ai_token_limit
                if plan
                else 0
            ),
            "ai_request_limit": (
                plan.ai_request_limit
                if plan
                else 0
            ),
            "transaction_limit": (
                plan.transaction_limit
                if plan
                else None
            ),
            **(
                plan.entitlements()
                if plan
                else {}
            ),
        }

    @staticmethod
    def paystack_plan_code(plan):
        import os

        return (
            plan.paystack_plan_code
            or os.getenv(
                f"PAYSTACK_PLAN_{plan.slug.upper()}",
                "",
            ).strip()
            or None
        )

    @staticmethod
    def create_transaction(
        user_id,
        plan,
        reference,
        metadata=None,
    ):
        tx = PaymentTransaction.query.filter_by(
            reference=reference
        ).first()

        if tx:
            return tx

        tx = PaymentTransaction(
            user_id=user_id,
            plan_id=plan.id,
            provider="paystack",
            reference=reference,
            amount_minor=plan.amount_minor,
            currency=plan.currency,
            status="initialized",
            metadata_json=json.dumps(
                metadata or {},
                ensure_ascii=False,
            ),
        )

        db.session.add(tx)
        db.session.commit()

        return tx

    @staticmethod
    def activate_from_payment(
        tx,
        provider_data=None,
    ):
        provider_data = provider_data or {}

        user = db.session.get(User, tx.user_id)
        if user and user.is_admin_group:
            raise PermissionError(
                "Administrative accounts cannot hold FOCOST subscription plans."
            )

        plan = (
            tx.plan
            or SubscriptionPlan.query.get(tx.plan_id)
        )

        if not plan:
            raise ValueError(
                "Subscription plan no longer exists."
            )

        now = utc_now()

        sub = (
            UserSubscription.query
            .filter_by(user_id=tx.user_id)
            .order_by(UserSubscription.created_at.desc())
            .first()
        )

        old_status = (
            sub.status
            if sub
            else None
        )

        if not sub:
            sub = UserSubscription(
                user_id=tx.user_id,
                plan_id=plan.id,
                provider="paystack",
            )

            db.session.add(sub)
            db.session.flush()

        sub.plan_id = plan.id
        sub.status = "active"
        sub.is_trial = False
        sub.started_at = (
            sub.started_at
            or now
        )
        sub.current_period_start = now
        sub.current_period_end = (
            now + timedelta(days=30)
        )

        next_payment = provider_data.get(
            "next_payment_date"
        )

        if next_payment:
            try:
                from datetime import datetime as dt

                parsed_next_payment = dt.fromisoformat(
                    next_payment.replace(
                        "Z",
                        "+00:00",
                    )
                )

                sub.current_period_end = as_utc(
                    parsed_next_payment
                )

            except (TypeError, ValueError):
                pass

        sub.cancel_at_period_end = False
        sub.canceled_at = None

        if provider_data.get("subscription_code"):
            sub.provider_subscription_code = (
                provider_data["subscription_code"]
            )

        if provider_data.get("email_token"):
            sub.provider_email_token = (
                provider_data["email_token"]
            )

        tx.subscription_id = sub.id
        tx.status = "success"
        tx.paid_at = now
        tx.gateway_response = json.dumps(
            provider_data,
            ensure_ascii=False,
        )

        db.session.add(
            SubscriptionEvent(
                user_id=tx.user_id,
                subscription_id=sub.id,
                event_type="payment_activated",
                old_status=old_status,
                new_status="active",
                source="paystack",
            )
        )

        db.session.commit()

        NotificationService.create(
            tx.user_id,
            "Subscription activated",
            (
                f"Your {plan.name} subscription "
                "is now active."
            ),
            notification_type="subscription",
            level="success",
            priority="high",
            action_url="/billing",
            unique_key=f"subscription-active:{sub.id}:{tx.reference}",
        )

        return sub

    @staticmethod
    def can_add_transaction(user_id):
        user = db.session.get(User, user_id)

        if user and user.is_admin_group:
            return (
                False,
                "Administrative accounts cannot create normal-user financial records.",
            )

        ent = SubscriptionService.entitlements(user_id)

        limit = ent.get("transaction_limit")

        if not limit:
            return True, None

        from app.models.income import Income
        from app.models.expense import Expense

        count = (
            Income.query
            .filter_by(
                user_id=user_id,
                is_active=True,
            )
            .count()
            +
            Expense.query
            .filter_by(
                user_id=user_id,
                is_active=True,
            )
            .count()
        )

        if count >= limit:
            return (
                False,
                (
                    f"Your {ent.get('plan_name', 'subscription')} "
                    f"allows up to {limit:,} tracked transactions. "
                    "Upgrade your plan to add more."
                ),
            )

        return True, None

    @staticmethod
    def cancel_at_period_end(user_id):
        sub = SubscriptionService.current(user_id)

        if not sub or sub.status not in {
            "active",
            "past_due",
        }:
            raise ValueError(
                "No active subscription is available to cancel."
            )

        sub.cancel_at_period_end = True
        sub.canceled_at = utc_now()

        db.session.add(
            SubscriptionEvent(
                user_id=user_id,
                subscription_id=sub.id,
                event_type="cancellation_requested",
                old_status=sub.status,
                new_status=sub.status,
                source="user",
            )
        )

        db.session.commit()

        NotificationService.create(
            user_id,
            "Subscription cancellation scheduled",
            (
                "Your paid access will remain available "
                "through the current billing period."
            ),
            notification_type="subscription",
            level="warning",
            priority="high",
            unique_key=f"cancel:{sub.id}",
        )

        return sub

    @staticmethod
    def admin_summary():
        """
        Return subscription administration metrics.

        Normal users are identified by Role.group_slug == "user".
        Administrative accounts are identified by Role.group_slug in
        {"super_admin", "admin"}.

        Subscription and payment metrics intentionally exclude all
        administrative accounts.
        """

        normal_user_ids = (
            db.session.query(User.id)
            .join(
                UserRole,
                UserRole.user_id == User.id,
            )
            .join(
                Role,
                Role.id == UserRole.role_id,
            )
            .filter(
                Role.group_slug == "user"
            )
            .subquery()
        )

        admin_user_ids = (
            db.session.query(User.id)
            .join(
                UserRole,
                UserRole.user_id == User.id,
            )
            .join(
                Role,
                Role.id == UserRole.role_id,
            )
            .filter(
                Role.group_slug.in_(
                    ["super_admin", "admin"]
                )
            )
            .subquery()
        )

        return {
            # --------------------------------------------------
            # CUSTOMER KPIs
            # --------------------------------------------------

            # Normal users only.
            # Includes Free Trial, Basic, Plus, Pro and users
            # whose subscription has expired/canceled.
            "total_users": (
                User.query
                .filter(
                    User.id.in_(normal_user_ids)
                )
                .count()
            ),

            # Normal users with active paid subscriptions.
            "active_subscriptions": (
                UserSubscription.query
                .filter(
                    UserSubscription.user_id.in_(
                        normal_user_ids
                    ),
                    UserSubscription.status == "active",
                )
                .count()
            ),

            # Normal users currently on trial.
            "trial_subscriptions": (
                UserSubscription.query
                .filter(
                    UserSubscription.user_id.in_(
                        normal_user_ids
                    ),
                    UserSubscription.status == "trial",
                )
                .count()
            ),

            # Normal users with expired/canceled subscriptions.
            "expired_subscriptions": (
                UserSubscription.query
                .filter(
                    UserSubscription.user_id.in_(
                        normal_user_ids
                    ),
                    UserSubscription.status.in_(
                        ["expired", "canceled"]
                    ),
                )
                .count()
            ),

            # --------------------------------------------------
            # ADMINISTRATIVE KPI
            # --------------------------------------------------

            "admin_users": (
                User.query
                .filter(
                    User.id.in_(admin_user_ids)
                )
                .count()
            ),

            # --------------------------------------------------
            # PLANS
            # --------------------------------------------------

            "plans": SubscriptionService.plans(False),

            # --------------------------------------------------
            # CUSTOMER SUBSCRIPTIONS
            # --------------------------------------------------

            "subscriptions": (
                UserSubscription.query
                .filter(
                    UserSubscription.user_id.in_(
                        normal_user_ids
                    )
                )
                .order_by(
                    UserSubscription.created_at.desc()
                )
                .limit(100)
                .all()
            ),

            # --------------------------------------------------
            # CUSTOMER PAYMENT TRANSACTIONS
            # --------------------------------------------------

            "payment_transactions": (
                PaymentTransaction.query
                .filter(
                    PaymentTransaction.user_id.in_(
                        normal_user_ids
                    )
                )
                .order_by(
                    PaymentTransaction.created_at.desc()
                )
                .limit(100)
                .all()
            ),
        }