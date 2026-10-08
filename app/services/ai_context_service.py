"""Authoritative application context for FOCOST AI.

This service is additive: it does not replace DashboardService financial
context or any existing AI intent/context behavior.  It exposes the user's
available FOCOST application state and workflow metadata while deliberately
excluding credentials, provider secrets, password material and security
secrets.
"""

from datetime import datetime, timezone
import json

from flask import current_app

from app.extensions import db
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.notification import Notification
from app.models.feedback import Feedback
from app.models.ai_usage import AIUsage
from app.models.compliance import PolicyAcceptance
from app.models.subscription import PaymentTransaction
from app.services.ai_usage_service import AIUsageService
from app.subscriptions.service import SubscriptionService
from app.services.dashboard_service import DashboardService


class AIContextService:
    """Build the complete safe application context available to one user."""

    PUBLIC_WORKFLOWS = {
        "dashboard": {
            "purpose": "View financial position, KPIs, trends, health, insights, alerts and recent activity.",
            "routes": ["/dashboard/"],
        },
        "income": {
            "purpose": "Create, view, edit and delete income records.",
            "routes": ["/income/", "/income/add", "/income/edit/<id>", "/income/delete/<id>"],
        },
        "expenses": {
            "purpose": "Create, view, edit and delete expense records.",
            "routes": ["/expense/", "/expense/add", "/expense/edit/<id>", "/expense/delete/<id>"],
        },
        "budgets": {
            "purpose": "Create, view, edit, delete and monitor category budgets and progress.",
            "routes": ["/budget/", "/budget/add", "/budget/edit/<id>", "/budget/progress/<id>", "/budget/delete/<id>"],
        },
        "goals": {
            "purpose": "Create, edit, delete, view and contribute to financial goals and contribution history.",
            "routes": ["/goal/", "/goal/add", "/goal/edit/<id>", "/goal/<id>", "/goal/<id>/contribute", "/goal/<id>/history"],
        },
        "investments": {
            "purpose": "View assets, valuations, investment events, liquidations and related financial effects.",
            "routes": ["/assets/", "/assets/create", "/assets/edit/<id>", "/assets/<id>/liquidate", "/assets/<id>/reverse-liquidation"],
        },
        "transactions_reports": {
            "purpose": "Review transaction records and reporting views.",
            "routes": ["/reports/transactions"],
        },
        "focost_ai": {
            "purpose": "Ask questions about finances, analysis, forecasts, goals, budgets, investments, subscriptions and FOCOST workflows.",
            "routes": ["/ai/", "/ai/chat", "/ai/usage", "/ai/forecast", "/ai/history"],
        },
        "profile": {
            "purpose": "View and update personal profile information and avatar.",
            "routes": ["/profile/", "/profile/avatar/<filename>"],
        },
        "settings": {
            "purpose": "View, update or reset application preferences.",
            "routes": ["/settings/api", "/settings/reset"],
        },
        "notifications": {
            "purpose": "View, read, dismiss and delete notifications and manage push registration.",
            "routes": ["/notifications/", "/notifications/api", "/notifications/read/<id>", "/notifications/mark-all-read", "/notifications/dismiss/<id>", "/notifications/delete/<id>", "/notifications/open/<id>", "/notifications/delete-all", "/notifications/push"],
        },
        "billing_subscription": {
            "purpose": "View plans and current billing state, start payment, complete verification and schedule cancellation.",
            "routes": ["/billing/", "/billing/api/status", "/billing/initialize", "/billing/callback", "/billing/cancel"],
        },
        "account": {
            "purpose": "Export the user's data or permanently close/anonymize the account according to FOCOST policy.",
            "routes": ["/account/export", "/account/delete"],
        },
        "feedback": {
            "purpose": "Submit product feedback/support feedback.",
            "routes": ["/feedback/"],
        },
        "categories": {
            "purpose": "Manage user financial categories where permitted.",
            "routes": ["/categories/"],
        },
    }

    DATA_CATALOG = {
        "profile": "User identity and profile fields available to the authenticated user.",
        "preferences": "Appearance, widgets, analytics, AI, notifications and privacy preferences.",
        "permissions": "Effective role and permission codes governing available operations.",
        "subscription": "Current subscription/trial, public plans, entitlements and billing state.",
        "ai_usage": "Current billing-period AI request/token usage and remaining allowance.",
        "income": "User income records and authoritative income calculations.",
        "expenses": "User expense records, classifications and authoritative expense calculations.",
        "budgets": "Active budgets, spending, remaining amounts and status.",
        "goals": "Goals, targets, progress, contributions and target dates.",
        "investments": "Assets, acquisition cost, current value, gain/loss and returns.",
        "notifications": "User notifications and their current read/dismissed state.",
        "feedback": "Feedback submitted by the authenticated user.",
        "compliance": "Current policy acceptance/version status, excluding security evidence such as IP/user-agent.",
        "payments": "Safe payment history fields such as plan, amount, currency, status and paid date; provider secrets are excluded.",
        "financial_analysis": "DashboardService summaries, comparisons, trends, forecasts, anomalies, scenarios, health, budgets, goals and investment intelligence.",
        "conversation": "Current FOCOST AI conversation history and conversational intent state.",
    }

    @staticmethod
    def _iso(value):
        return value.isoformat() if value else None

    @staticmethod
    def _profile(user):
        role = user.role
        return {
            "public_id": user.public_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "display_name": f"{user.first_name} {user.last_name}".strip(),
            "email": user.email,
            "phone": user.phone,
            "country": user.country,
            "currency": user.currency,
            "occupation": user.occupation,
            "monthly_income_profile": float(user.monthly_income or 0),
            "avatar": user.avatar,
            "email_verified": bool(user.email_verified),
            "account_active": bool(user.is_active),
            "role": role.slug if role else None,
            "role_group": user.role_group,
            "is_normal_user": bool(user.is_normal_user),
            "created_at": AIContextService._iso(user.created_at),
            "updated_at": AIContextService._iso(user.updated_at),
        }

    @staticmethod
    def _preferences(user_id):
        settings = UserSettings.query.filter_by(user_id=user_id).first()
        if not settings:
            return UserSettings.DEFAULTS
        return settings.get_preferences()

    @staticmethod
    def _permissions(user):
        return sorted(user.permissions or set())

    @staticmethod
    def _subscription(user_id):
        current = SubscriptionService.current(user_id)
        entitlements = SubscriptionService.entitlements(user_id)

        plans = []
        for plan in SubscriptionService.plans(public_only=True):
            plans.append({
                "slug": plan.slug,
                "name": plan.name,
                "description": plan.description,
                "price": float(plan.amount),
                "currency": plan.currency,
                "interval": plan.interval,
                "ai_token_limit": plan.ai_token_limit,
                "ai_request_limit": plan.ai_request_limit,
                "transaction_limit": plan.transaction_limit,
                "features": plan.entitlements(),
                "is_public": bool(plan.is_public),
                "is_active": bool(plan.is_active),
            })

        current_data = None
        if current:
            current_data = {
                "status": current.status,
                "is_trial": bool(current.is_trial),
                "is_active_access": bool(current.is_active_access),
                "plan": current.plan.name if current.plan else ("Free Trial" if current.is_trial else None),
                "plan_slug": current.plan.slug if current.plan else None,
                "trial_started_at": AIContextService._iso(current.trial_started_at),
                "trial_ends_at": AIContextService._iso(current.trial_ends_at),
                "started_at": AIContextService._iso(current.started_at),
                "current_period_start": AIContextService._iso(current.current_period_start),
                "current_period_end": AIContextService._iso(current.current_period_end),
                "cancel_at_period_end": bool(current.cancel_at_period_end),
                "canceled_at": AIContextService._iso(current.canceled_at),
                "provider": current.provider,
            }

        return {
            "current": current_data,
            "entitlements": entitlements,
            "public_plans": plans,
            "workflow": {
                "view_plans": "/billing/",
                "initialize_payment": "/billing/initialize",
                "payment_verification": "/billing/callback",
                "cancel_at_period_end": "/billing/cancel",
                "note": "Payment is initialized through FOCOST and verified before subscription activation. FOCOST AI must not claim a payment was completed unless the application confirms it.",
            },
        }

    @staticmethod
    def _ai_usage(user_id):
        return AIUsageService.monthly(user_id)

    @staticmethod
    def _notifications(user_id):
        rows = (
            Notification.query
            .filter_by(user_id=user_id, is_deleted=False)
            .order_by(Notification.created_at.desc())
            .limit(20)
            .all()
        )
        return [
            {
                "title": row.title,
                "message": row.message,
                "type": row.notification_type,
                "source": row.source,
                "priority": row.priority,
                "level": row.level,
                "action_url": row.action_url,
                "is_read": bool(row.is_read),
                "created_at": AIContextService._iso(row.created_at),
                "expires_at": AIContextService._iso(row.expires_at),
            }
            for row in rows
        ]

    @staticmethod
    def _feedback(user_id):
        rows = (
            Feedback.query
            .filter_by(submitted_by_id=user_id)
            .order_by(Feedback.created_at.desc())
            .limit(20)
            .all()
        )
        return [
            {
                "category": row.category,
                "subject": row.subject,
                "message": row.message,
                "rating": row.rating,
                "status": row.status,
                "priority": row.priority,
                "created_at": AIContextService._iso(row.created_at),
            }
            for row in rows
        ]

    @staticmethod
    def _compliance(user_id):
        rows = (
            PolicyAcceptance.query
            .filter_by(user_id=user_id)
            .order_by(PolicyAcceptance.accepted_at.desc())
            .all()
        )
        return [
            {
                "policy_version": row.policy_version,
                "accepted_at": AIContextService._iso(row.accepted_at),
                "action": row.action,
                "source": row.source,
                "authenticated": bool(row.authenticated),
            }
            for row in rows
        ]

    @staticmethod
    def _payments(user_id):
        rows = (
            PaymentTransaction.query
            .filter_by(user_id=user_id)
            .order_by(PaymentTransaction.created_at.desc())
            .limit(20)
            .all()
        )
        return [
            {
                "plan": row.plan.name if row.plan else None,
                "amount": float(row.amount_minor or 0) / 100,
                "currency": row.currency,
                "status": row.status,
                "paid_at": AIContextService._iso(row.paid_at),
                "created_at": AIContextService._iso(row.created_at),
            }
            for row in rows
        ]

    @staticmethod
    def _application_rules():
        return {
            "financial_authority": "DashboardService is the single source of truth for financial facts, calculations, classifications, forecasts, scenarios and financial explanations.",
            "subscription_authority": "SubscriptionService is the single source of truth for plans, subscription state, entitlements, access and billing state.",
            "account_authority": "AccountClosureService owns account closure/anonymization rules.",
            "settings_authority": "SettingsService owns user preference retrieval, update and reset behavior.",
            "usage_authority": "AIUsageService owns AI billing-period usage, limits and consumption eligibility.",
            "permission_authority": "FOCOST RBAC role and permission services determine which application operations the user may perform.",
            "ai_behavior": "FOCOST AI is advisory/conversational. It must not claim an operation was executed unless a real FOCOST action endpoint/service confirms completion.",
            "security": "Never expose passwords, password hashes, auth versions, session secrets, API keys, payment-provider secrets, provider subscription codes, provider email tokens, webhook secrets or private security evidence.",
        }

    @staticmethod
    def _workflow_context(user):
        allowed = []
        permissions = user.permissions or set()
        permission_map = {
            "profile": "profile.view",
            "settings": "settings.view",
            "dashboard": "dashboard.view",
            "income": "income.view",
            "expenses": "expense.view",
            "budgets": "budget.view",
            "goals": "goal.view",
            "investments": "asset.view",
            "transactions_reports": "reports.view",
            "focost_ai": "ai.chat",
        }
        for name, item in AIContextService.PUBLIC_WORKFLOWS.items():
            required = permission_map.get(name)
            if required and required not in permissions:
                continue
            allowed.append({
                "name": name,
                **item,
            })

        # Billing/account/notifications/feedback are authenticated-user
        # workflows and are additionally protected by their own route/service rules.
        for name in ("billing_subscription", "account", "notifications", "feedback", "categories"):
            item = AIContextService.PUBLIC_WORKFLOWS[name]
            allowed.append({"name": name, **item})

        return {
            "available_to_user": allowed,
            "operation_rule": "The AI can explain the workflow and direct the user to the correct FOCOST surface. It must not falsely claim that it clicked, saved, paid, deleted or changed anything.",
        }

    @staticmethod
    def _data_inventory(user_id):
        from app.models.income import Income
        from app.models.expense import Expense
        from app.models.budget import Budget
        from app.models.goal import Goal
        from app.models.asset import Asset

        return {
            "income_records": Income.query.filter_by(user_id=user_id).count(),
            "expense_records": Expense.query.filter_by(user_id=user_id).count(),
            "budget_records": Budget.query.filter_by(user_id=user_id).count(),
            "goal_records": Goal.query.filter_by(user_id=user_id).count(),
            "asset_records": Asset.query.filter_by(user_id=user_id).count(),
            "notification_records": Notification.query.filter_by(user_id=user_id, is_deleted=False).count(),
            "feedback_records": Feedback.query.filter_by(submitted_by_id=user_id).count(),
            "ai_usage_records": AIUsage.query.filter_by(user_id=user_id).count(),
            "payment_records": PaymentTransaction.query.filter_by(user_id=user_id).count(),
        }


    @staticmethod
    def _registered_user_routes():
        """Expose the live Flask route surface instead of maintaining a second route registry."""
        try:
            rules = []
            for rule in current_app.url_map.iter_rules():
                endpoint = rule.endpoint or ""
                if endpoint.startswith((
                    "admin.", "admin_users.", "admin_roles.",
                    "admin_documents.", "admin_analytics.", "admin_communications.",
                    "static",
                )):
                    continue
                if rule.rule.startswith(("/healthz", "/readyz", "/.well-known", "/robots.txt")):
                    continue
                rules.append({
                    "endpoint": endpoint,
                    "path": rule.rule,
                    "methods": sorted(rule.methods - {"HEAD", "OPTIONS"}),
                })
            return sorted(rules, key=lambda item: (item["path"], item["endpoint"]))
        except Exception:
            return []

    @staticmethod
    def _service_capabilities():
        """Expose public service operations as capability metadata, not duplicate business logic."""
        service_classes = {
            "DashboardService": DashboardService,
            "SubscriptionService": SubscriptionService,
            "AIUsageService": AIUsageService,
        }
        result = {}
        for name, cls in service_classes.items():
            result[name] = sorted(
                method_name
                for method_name in dir(cls)
                if not method_name.startswith("_") and callable(getattr(cls, method_name, None))
            )
        return result

    @staticmethod
    def _extended_for_message(message):
        text = (message or "").lower()
        return {
            "notifications": any(x in text for x in ("notification", "alert", "reminder")),
            "feedback": any(x in text for x in ("feedback", "support request", "feedback i sent")),
            "compliance": any(x in text for x in ("policy", "terms", "privacy", "consent", "accepted")),
            "payments": any(x in text for x in ("payment", "paid", "transaction reference", "billing history", "payment history")),
        }

    @staticmethod
    def application_context_for_message(user_id, message):
        """Return additional user/application records relevant to the current question."""
        flags = AIContextService._extended_for_message(message)
        result = {}
        if flags["notifications"]:
            result["notifications"] = AIContextService._notifications(user_id)
        if flags["feedback"]:
            result["feedback"] = AIContextService._feedback(user_id)
        if flags["compliance"]:
            result["compliance"] = AIContextService._compliance(user_id)
        if flags["payments"]:
            result["payments"] = AIContextService._payments(user_id)
        return result

    @staticmethod
    def build(user_id, *, financial_context=None, include_extended=False):
        """Return the additive global FOCOST context for the authenticated user."""
        user = db.session.get(User, user_id)
        if not user:
            return {
                "available": False,
                "reason": "Authenticated user context could not be resolved.",
            }

        context = {
            "available": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "profile": AIContextService._profile(user),
            "preferences": AIContextService._preferences(user_id),
            "permissions": AIContextService._permissions(user),
            "subscription": AIContextService._subscription(user_id),
            "ai_usage": AIContextService._ai_usage(user_id),
            "workflows": AIContextService._workflow_context(user),
            "data_catalog": AIContextService.DATA_CATALOG,
            "data_inventory": AIContextService._data_inventory(user_id),
            "application_rules": AIContextService._application_rules(),
            "registered_user_routes": AIContextService._registered_user_routes(),
            "service_capabilities": AIContextService._service_capabilities(),
            "financial_authority": {
                "service": "DashboardService",
                "available_analysis": [
                    "financial position", "income", "expenses", "savings", "cash flow",
                    "transactions", "categories", "merchants", "budgets", "goals",
                    "investments", "financial health", "trends", "comparisons",
                    "month-end forecasts", "advanced forecasts", "category forecasts",
                    "anomalies", "scenarios", "recommendations", "daily brief",
                    "dashboard KPIs", "dashboard insights", "notifications", "personalization",
                ],
            },
            "conversation_rules": {
                "answer_from_authoritative_context": True,
                "do_not_recalculate_dashboard_facts": True,
                "do_not_invent_missing_user_data": True,
                "concise_response_maximum_tokens": "120 normal / 180 when detail is explicitly required",
            },
        }

        if financial_context is not None:
            # Preserve the entire pre-existing DashboardService context unchanged.
            context["financial_context"] = financial_context

        if include_extended:
            context["notifications"] = AIContextService._notifications(user_id)
            context["feedback"] = AIContextService._feedback(user_id)
            context["compliance"] = AIContextService._compliance(user_id)
            context["payments"] = AIContextService._payments(user_id)

        return context
