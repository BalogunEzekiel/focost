####################################################################################################
# FILE: app/services/ai_service.py
####################################################################################################

from datetime import date, timedelta

from app.utils.timezone import today
import calendar
import json
import re
import time
import uuid

from flask import session
from app.extensions import db

from app.services.dashboard_service import DashboardService
from app.services.llm_service import LLMService
from app.services.ai_usage_service import AIUsageService
from app.services.ai_context_service import AIContextService


class AIService:
    """FOCOST AI domain service.

    Financial data is retrieved on demand from DashboardService.
    Conversation history and lightweight conversation context are temporary
    Flask-session state only. Financial records are never stored in session.
    """

    # Visible conversation history is retained for the current session.
    # The AI receives only a smaller recent window to control token usage.
    MAX_VISIBLE_HISTORY_MESSAGES = 100
    MAX_TRANSACTION_CONTEXT = 6
    MAX_AI_HISTORY_MESSAGES = 2

    @staticmethod
    def _is_explanation_followup(message):
        text = re.sub(
            r"\s+",
            " ",
            message.lower().strip(),
        )

        explanation_patterns = (
            r"\bbreak\s*(it|them)?\s*down\b",
            r"\bbreakdown\b",
            r"\bbreak\s+this\s+down\b",
            r"\bhow\s+did\s+you\s+(calculate|arrive|work)\b",
            r"\bhow\s+did\s+you\s+get\b",
            r"\bhow\s+was\s+this\s+calculated\b",
            r"\bhow\s+was\s+that\s+calculated\b",
            r"\bwhere\s+did\s+that\s+figure\s+come\s+from\b",
            r"\bwhere\s+did\s+this\s+figure\s+come\s+from\b",
            r"\bexplain\s+(that|this|it|the figure)\b",
            r"\bshow\s+(me\s+)?the\s+calculation\b",
            r"\bshow\s+(me\s+)?how\b",
            r"\bwhy\s+is\s+(that|this)\b",
            r"\bwhat\s+makes\s+(that|this)\b",
        )

        return any(
            re.search(
                pattern,
                text,
            )
            for pattern in explanation_patterns
        )

    @staticmethod
    def _is_contextual_followup(message):
        """
        Detect short conversational follow-ups that should inherit
        the previous financial subject.
        """
        text = re.sub(
            r"\s+",
            " ",
            message.lower().strip(),
        )

        return text in {
            "yes",
            "yeah",
            "yep",
            "yup",
            "okay",
            "ok",
            "sure",
            "go ahead",
            "continue",
            "more",
            "details",
            "detail",
            "for what",
            "what for",
            "what was it for",
            "which ones",
            "which one",
            "what were they",
            "what are they",
            "how so",
            "why",
            "why?",
        }

    @staticmethod
    def _period_from_message(message):
        text = re.sub(r"\s+", " ", message.lower().strip())
        today_date = today()

        months = {
            name: number
            for number, names in enumerate([
                ("january", "jan"),
                ("february", "feb"),
                ("march", "mar"),
                ("april", "apr"),
                ("may",),
                ("june", "jun"),
                ("july", "jul"),
                ("august", "aug"),
                ("september", "sep", "sept"),
                ("october", "oct"),
                ("november", "nov"),
                ("december", "dec"),
            ], 1)
            for name in names
        }

        iso_range = re.search(
            r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\s*"
            r"(?:to|through|-)\s*"
            r"(20\d{2})-(\d{1,2})-(\d{1,2})\b",
            text,
        )

        if iso_range:
            try:
                return (
                    date(
                        int(iso_range.group(1)),
                        int(iso_range.group(2)),
                        int(iso_range.group(3)),
                    ),
                    date(
                        int(iso_range.group(4)),
                        int(iso_range.group(5)),
                        int(iso_range.group(6)),
                    ),
                )
            except ValueError:
                pass

        month_matches = list(re.finditer(
            r"\b(january|jan|february|feb|march|mar|april|apr|may|"
            r"june|jun|july|jul|august|aug|september|sep|sept|"
            r"october|oct|november|nov|december|dec)"
            r"(?:\s+(20\d{2}))?\b",
            text,
        ))

        if month_matches:
            parsed = []

            for match in month_matches[:2]:
                month = months[match.group(1)]
                year = int(match.group(2) or today_date.year)
                parsed.append((year, month))

            if len(parsed) >= 2 and parsed[1] >= parsed[0]:
                y1, m1 = parsed[0]
                y2, m2 = parsed[1]

                return (
                    date(y1, m1, 1),
                    date(
                        y2,
                        m2,
                        calendar.monthrange(y2, m2)[1],
                    ),
                )

            year, month = parsed[0]

            return (
                date(year, month, 1),
                date(
                    year,
                    month,
                    calendar.monthrange(year, month)[1],
                ),
            )

        iso = re.search(
            r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b",
            text,
        )

        if iso:
            try:
                d = date(
                    int(iso.group(1)),
                    int(iso.group(2)),
                    int(iso.group(3)),
                )
                return d, d
            except ValueError:
                pass

        if "yesterday" in text:
            d = today_date - timedelta(days=1)
            return d, d

        if "last week" in text:
            end = today_date - timedelta(days=today_date.weekday() + 1)
            return end - timedelta(days=6), end

        if "this week" in text:
            return (
                today_date - timedelta(days=today_date.weekday()),
                today_date,
            )

        if "last month" in text:
            first = today_date.replace(day=1)
            end = first - timedelta(days=1)
            return end.replace(day=1), end

        if "this month" in text:
            return today_date.replace(day=1), today_date

        if "last quarter" in text:
            q = (today_date.month - 1) // 3
            year = today_date.year

            if q == 0:
                q, year = 4, year - 1

            return (
                date(year, (q - 1) * 3 + 1, 1),
                date(
                    year,
                    q * 3,
                    calendar.monthrange(year, q * 3)[1],
                ),
            )

        if "this quarter" in text:
            q = (today_date.month - 1) // 3 + 1

            return (
                date(today_date.year, (q - 1) * 3 + 1, 1),
                today_date,
            )

        if "last year" in text:
            return (
                date(today_date.year - 1, 1, 1),
                date(today_date.year - 1, 12, 31),
            )

        if "this year" in text:
            return date(today_date.year, 1, 1), today_date

        return today_date.replace(day=1), today_date

    @staticmethod
    def _is_explicit_period(message):
        """Return True when the message explicitly specifies a time period."""
        text = re.sub(r"\s+", " ", message.lower().strip())

        period_patterns = (
            r"\b20\d{2}-\d{1,2}-\d{1,2}\b",
            r"\b(january|jan|february|feb|march|mar|april|apr|may|"
            r"june|jun|july|jul|august|aug|september|sep|sept|"
            r"october|oct|november|nov|december|dec)\b",
            r"\b(today|yesterday|this week|last week|this month|"
            r"last month|this quarter|last quarter|this year|last year)\b",
        )

        return any(re.search(pattern, text) for pattern in period_patterns)

    @staticmethod
    def _is_month_only_message(message):
        text = re.sub(r"\s+", " ", message.lower().strip())

        return bool(re.fullmatch(
            r"(january|jan|february|feb|march|mar|april|apr|may|"
            r"june|jun|july|jul|august|aug|september|sep|sept|"
            r"october|oct|november|nov|december|dec)"
            r"(?:\s+20\d{2})?",
            text,
        ))

    @staticmethod
    def _is_casual_message(message):
        text = re.sub(r"\s+", " ", message.lower().strip())

        return text in {
            "hi",
            "hello",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
            "how are you",
            "how are you doing",
            "how are things",
            "thanks",
            "thank you",
            "thanks a lot",
            "thank you so much",
            "ok",
            "okay",
            "alright",
            "great",
            "nice",
            "bye",
            "goodbye",
        }

    @staticmethod
    def _classify_intent(message):
        """Deterministic intent routing; no second LLM call is required."""
        text = re.sub(r"\s+", " ", message.lower().strip())

        # ----------------------------------------------------------
        # FOCOST APPLICATION / ACCOUNT DOMAINS
        # ----------------------------------------------------------
        if any(x in text for x in (
            "subscription", "plan", "free plan", "premium plan",
            "trial", "entitlement", "upgrade", "downgrade",
        )):
            return "subscription"

        if any(x in text for x in (
            "billing", "bill", "payment", "paid", "pay for",
            "payment history", "billing history", "renewal",
            "cancel subscription", "cancel my plan",
        )):
            return "billing"

        if any(x in text for x in (
            "notification", "notifications", "alert", "alerts",
            "reminder", "reminders",
        )):
            return "notifications"

        if any(x in text for x in (
            "feedback", "support request", "feedback i sent",
        )):
            return "feedback"

        if any(x in text for x in (
            "policy", "policies", "terms", "privacy", "consent",
            "accepted the terms", "acceptance",
        )):
            return "compliance"

        if any(x in text for x in (
            "my profile", "profile information", "my account details",
            "my name", "my email", "my phone", "my occupation",
        )):
            return "profile"

        if any(x in text for x in (
            "settings", "preferences", "preference", "notification settings",
        )):
            return "settings"

        if any(x in text for x in (
            "permission", "permissions", "what can i access",
            "what am i allowed", "access rights",
        )):
            return "permissions"

        if any(x in text for x in (
            "ai usage", "ai usage limit", "ai requests", "ai token",
            "how many ai", "remaining ai", "usage limit",
        )):
            return "ai_usage"

        if any(x in text for x in (
            "how do i", "where do i", "how can i", "where can i",
            "workflow", "workflows", "feature", "features",
            "how does focost", "can focost",
        )):
            return "workflows"

        # Action questions about a financial feature are workflow questions,
        # not requests to invent an operation from financial records.
        if (
            any(x in text for x in (
                "can i", "create", "add", "edit", "delete", "remove",
                "liquidate", "cancel", "contribute", "reverse",
            ))
            and any(x in text for x in (
                "income", "expense", "budget", "goal", "investment",
                "asset", "transaction", "report", "profile", "setting",
            ))
        ):
            return "workflows"

        # A direct question containing both income and expense facts is a
        # combined financial summary, not an income-only or expense-only request.
        # Advice/comparison questions are handled by their dedicated intents below.
        has_income = any(x in text for x in (
            "income", "earned", "earnings", "salary", "revenue",
        ))
        has_expenses = any(x in text for x in (
            "expense", "expenses", "spent", "spending", "cost", "costs",
            "purchase", "purchases",
        ))
        is_comparison_request = any(x in text for x in (
            "compare", "comparison", "versus", " vs ", "trend",
            "trends", "over time", "historical",
        ))
        is_advice_request = any(x in text for x in (
            "advice", "advise", "improve", "recommend", "suggest",
            "what should i do", "what can i do",
        ))
        if has_income and has_expenses and not is_comparison_request and not is_advice_request:
            return "summary"

        if any(x in text for x in (
            "advice",
            "advise",
            "how can i do better",
            "how should i improve",
            "improve my finances",
            "improve my financial",
            "what should i do",
            "what can i do",
            "recommend",
            "recommendation",
            "suggest",
            "suggestion",
            "help me improve",
        )):
            return "advice"

        if any(x in text for x in (
            "forecast",
            "predict",
            "prediction",
            "project",
            "projection",
            "next month",
            "next year",
            "future",
            "expected",
            "estimate",
            "runway",
        )):
            return "forecast"

        if any(x in text for x in (
            "compare",
            "comparison",
            "versus",
            " vs ",
            "trend",
            "trends",
            "over time",
            "historical",
        )):
            return "comparison"

        if any(x in text for x in (
            "financial health",
            "health score",
            "how healthy",
            "health of my finances",
        )):
            return "health"

        if any(x in text for x in (
            "goal",
            "goals",
            "target",
        )):
            return "goals"

        if any(x in text for x in (
            "budget",
            "budgets",
            "budgeting",
        )):
            return "budgets"

        if any(x in text for x in (
            "investment",
            "investments",
            "asset",
            "assets",
            "portfolio",
            "return on investment",
            "gain",
            "loss",
        )):
            return "investments"

        if any(x in text for x in (
            "transaction",
            "transactions",
            "ledger",
            "records",
            "show me what i spent",
            "show my spending",
        )):
            return "transactions"

        if any(x in text for x in (
            "saving",
            "savings",
            "save",
            "saved",
            "savings rate",
        )):
            return "savings"

        if any(x in text for x in (
            "income",
            "earned",
            "earnings",
            "salary",
            "revenue",
        )):
            return "income"

        if any(x in text for x in (
            "expense",
            "expenses",
            "spent",
            "spending",
            "cost",
            "costs",
            "purchase",
            "purchases",
        )):
            return "expenses"

        if any(x in text for x in (
            "balance",
            "cash balance",
            "cashflow",
            "cash flow",
            "money do i have",
            "how much do i have",
        )):
            return "balance"

        return "summary"

    @staticmethod
    def _extract_focus_term(message):
        text = re.sub(r"\s+", " ", message.lower().strip())

        patterns = (
            r"(?:spend|spent|expense|expenses|cost|costs|purchase|purchases)"
            r"\s+(?:on|for|at)\s+"
            r"([a-z0-9][a-z0-9 &'_-]{1,40}?)"
            r"(?=\s+(?:in|on|for|during|this|last|from|between|$))",

            r"(?:what did i spend|spending|expenses?)"
            r"\s+(?:on|for|at)\s+"
            r"([a-z0-9][a-z0-9 &'_-]{1,40})$",

            r"(?:category|merchant)\s*[:=]?\s*"
            r"([a-z0-9][a-z0-9 &'_-]{1,40})$",
        )

        for pattern in patterns:
            match = re.search(pattern, text)

            if match:
                term = match.group(1).strip(" .?,")

                if term:
                    return term

        return None

    @staticmethod
    def _get_session_history(limit=None):
        """
        Return valid conversation history.

        The complete session history is retained for the UI.
        A smaller limit can be requested when preparing context for the LLM.
        """
        history = session.get("ai_history", [])

        if not isinstance(history, list):
            return []

        valid = []

        for item in history:
            if (
                isinstance(item, dict)
                and item.get("role") in {"user", "assistant"}
                and isinstance(item.get("content"), str)
            ):
                valid.append({
                    "role": item["role"],
                    "content": item["content"],
                })

        if limit is not None:
            return valid[-limit:]

        return valid

    @staticmethod
    def _save_session_history(history):
        """
        Preserve the complete visible conversation for the current session.

        AI context is trimmed separately when sending a request to the LLM.
        """
        session["ai_history"] = history[
            -AIService.MAX_VISIBLE_HISTORY_MESSAGES:
        ]

        session.modified = True

    @staticmethod
    def clear_session_history():
        session.pop("ai_history", None)
        session.pop("ai_context", None)
        session.modified = True

    @staticmethod
    def _resolve_context(message, history):
        """Resolve period/intent for conversational follow-ups.

        Only lightweight metadata is kept in session. No financial data is
        stored here.
        """
        current_intent = AIService._classify_intent(message)
        contextual_followup = (
            AIService._is_contextual_followup(message)
        )

        explanation_followup = (
            AIService._is_explanation_followup(message)
        )

        explicit_period = AIService._is_explicit_period(message)
        month_only = AIService._is_month_only_message(message)

        start, end = AIService._period_from_message(message)

        previous_context = session.get("ai_context", {})

        if not isinstance(previous_context, dict):
            previous_context = {}

        previous_start = previous_context.get("start")
        previous_end = previous_context.get("end")
        previous_intent = previous_context.get("intent")
        previous_focus = previous_context.get("focus")
        prior_intent = previous_intent

        # Recover previous context from the last user messages when possible.
        recent_user_messages = [
            item["content"]
            for item in history
            if item.get("role") == "user"
        ]

        previous_user_message = (
            recent_user_messages[-1]
            if recent_user_messages
            else ""
        )

        # Short conversational follow-ups such as:
        # "for what?", "yes", "which ones?", and "why?"
        # must inherit the previous financial subject.
        if (
            contextual_followup
            and previous_intent
            and previous_intent != "summary"
        ):
            current_intent = previous_intent

        if previous_user_message:
            previous_detected_intent = AIService._classify_intent(
                previous_user_message
            )

            if previous_detected_intent != "summary":
                previous_intent = previous_detected_intent

            if AIService._is_explicit_period(previous_user_message):
                previous_start, previous_end = AIService._period_from_message(
                    previous_user_message
                )

            previous_message_focus = AIService._extract_focus_term(
                previous_user_message
            )

            if previous_message_focus:
                previous_focus = previous_message_focus

        # An explanation follow-up such as:
        # "why?", "explain that", "how did you arrive at that?"
        # should remain on the previous financial subject instead of being
        # reclassified as a generic summary/advice intent.
        if (
            explanation_followup
            and previous_intent
            and previous_intent != "summary"
        ):
            current_intent = previous_intent

        # "What about income?" / "What about expenses?"
        # inherit the previous period.
        if (
            not explicit_period
            and not month_only
            and previous_start
            and previous_end
        ):
            try:
                start = date.fromisoformat(str(previous_start))
                end = date.fromisoformat(str(previous_end))
            except (TypeError, ValueError):
                pass

        # A bare month such as "August" changes the period but keeps the
        # previous subject/intent.
        if month_only:
            if previous_intent and previous_intent != "summary":
                current_intent = previous_intent

            if previous_focus:
                focus = previous_focus
            else:
                focus = None
        else:
            focus = AIService._extract_focus_term(message)

            if not focus:
                focus = previous_focus

        # IMPORTANT: an explicit period always wins.
        # For example, after discussing September, "What should I prioritize
        # this month?" must use October rather than silently inheriting September.

        resolved_context = {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "intent": current_intent,
            "focus": focus,
            "previous_intent": prior_intent,
        }

        session["ai_context"] = resolved_context
        session.modified = True

        return start, end, current_intent, focus

    @staticmethod
    def _application_intent(intent, message):
        """Return whether the request is primarily about a FOCOST application domain."""
        return intent in {
            "subscription",
            "billing",
            "payments",
            "notifications",
            "feedback",
            "compliance",
            "profile",
            "settings",
            "permissions",
            "ai_usage",
            "workflows",
        }

    @staticmethod
    def _financial_intent(intent):
        return intent in {
            "balance",
            "savings",
            "income",
            "expenses",
            "transactions",
            "goals",
            "budgets",
            "investments",
            "summary",
            "comparison",
            "forecast",
            "health",
            "advice",
        }

    @staticmethod
    def _workflow_prompt_context(full_workflows, message):
        """Return only workflow entries relevant to the current question."""
        available = []
        if isinstance(full_workflows, dict):
            available = full_workflows.get("available_to_user", []) or []

        text = (message or "").lower()
        keyword_map = {
            "dashboard": "dashboard",
            "income": "income",
            "expense": "expenses",
            "spend": "expenses",
            "budget": "budgets",
            "goal": "goals",
            "investment": "investments",
            "liquidat": "investments",
            "asset": "investments",
            "transaction": "transactions_reports",
            "report": "transactions_reports",
            "profile": "profile",
            "setting": "settings",
            "notification": "notifications",
            "alert": "notifications",
            "subscription": "billing_subscription",
            "billing": "billing_subscription",
            "payment": "billing_subscription",
            "account": "account",
            "feedback": "feedback",
            "category": "categories",
            "ai": "focost_ai",
        }

        wanted = {
            workflow_name
            for keyword, workflow_name in keyword_map.items()
            if keyword in text
        }

        if wanted:
            filtered = [
                item for item in available
                if item.get("name") in wanted
            ]
        else:
            filtered = available

        return {
            "available_to_user": filtered,
            "operation_rule": full_workflows.get(
                "operation_rule",
                "The AI can explain workflows but must not claim an operation was executed.",
            ) if isinstance(full_workflows, dict) else "The AI can explain workflows but must not claim an operation was executed.",
        }

    @staticmethod
    def _prompt_context(
        user_id,
        message,
        intent,
        financial_context=None,
    ):
        """
        Build the LLM-facing projection of the comprehensive FOCOST context.

        IMPORTANT:
            This is NOT a replacement for application context.
            AIContextService.build() remains the complete safe context layer.

            This projection exists only because sending every route, service
            method, notification, payment, plan, preference and financial
            record on every request wastes tokens and can exceed provider limits.

            Financial requests receive the complete authoritative context for
            the requested financial domain. Application requests receive the
            relevant application domain. Nothing is character-truncated.
        """
        full = AIContextService.build(
            user_id,
            financial_context=financial_context,
            include_extended=False,
        )

        profile = full.get("profile", {})
        preferences = full.get("preferences", {})
        permissions = full.get("permissions", [])
        subscription = full.get("subscription", {})
        ai_usage = full.get("ai_usage", {})
        workflows = full.get("workflows", {})
        rules = full.get("application_rules", {})

        # These are deliberately small, stable application facts that help
        # the model answer without dragging the complete application catalog
        # into every financial request.
        base = {
            "profile": profile,
            "preferences": preferences,
            "currency": profile.get("currency", "NGN"),
            "permissions": permissions,
            "application_rules": rules,
        }

        if AIService._financial_intent(intent):
            base["financial_authority"] = full.get(
                "financial_authority", {}
            )
            base["financial_context"] = financial_context or {}

            # Subscription state is intentionally not attached to ordinary
            # financial prompts. It belongs to subscription/billing/usage
            # questions and was a major source of unnecessary prompt growth.
            return base

        if intent == "subscription":
            base.update({
                "subscription": subscription,
                "workflows": workflows,
            })
            return base

        if intent in {"billing", "payments"}:
            base["subscription"] = subscription
            base["workflows"] = workflows
            base["payments"] = AIContextService.application_context_for_message(
                user_id, message
            ).get("payments", [])
            return base

        if intent == "notifications":
            base["notifications"] = AIContextService.application_context_for_message(
                user_id, message
            ).get("notifications", [])
            return base

        if intent == "feedback":
            base["feedback"] = AIContextService.application_context_for_message(
                user_id, message
            ).get("feedback", [])
            return base

        if intent == "compliance":
            base["compliance"] = AIContextService.application_context_for_message(
                user_id, message
            ).get("compliance", [])
            return base

        if intent == "profile":
            return {
                "profile": profile,
                "preferences": preferences,
                "permissions": permissions,
                "application_rules": rules,
            }

        if intent == "settings":
            return {
                "profile": profile,
                "preferences": preferences,
                "application_rules": rules,
                "workflows": workflows,
            }

        if intent == "permissions":
            return {
                "profile": profile,
                "permissions": permissions,
                "workflows": workflows,
                "application_rules": rules,
            }

        if intent == "ai_usage":
            return {
                "profile": profile,
                "subscription": subscription,
                "ai_usage": ai_usage,
                "workflows": workflows,
                "application_rules": rules,
            }

        if intent == "workflows":
            workflow_context = AIService._workflow_prompt_context(
                workflows,
                message,
            )
            broad_capability_question = any(
                phrase in message.lower()
                for phrase in (
                    "what can i do",
                    "what can focost",
                    "all features",
                    "all capabilities",
                    "available features",
                    "available capabilities",
                )
            )

            result = {
                "profile": profile,
                "permissions": permissions,
                "workflows": workflow_context,
                "application_rules": rules,
            }

            if broad_capability_question:
                result["registered_user_routes"] = full.get(
                    "registered_user_routes", []
                )
                result["service_capabilities"] = full.get(
                    "service_capabilities", {}
                )

            return result

        # Unknown/application-general requests retain the broad safe metadata
        # layer without attaching large user record collections.
        return {
            **base,
            "subscription": subscription,
            "ai_usage": ai_usage,
            "workflows": workflows,
            "data_catalog": full.get("data_catalog", {}),
            "financial_authority": full.get("financial_authority", {}),
        }

    @staticmethod
    def build_system_prompt(user_id, message="", history=None):
        history = history or []

        if AIService._is_casual_message(message):
            return "You are FOCOST AI. Reply naturally in one short sentence."

        start, end, intent, focus = AIService._resolve_context(
            message, history
        )

        financial_context = None
        if AIService._financial_intent(intent):
            financial_context = DashboardService.financial_context(
                user_id,
                start,
                end,
                intent=intent,
                focus=focus,
                message=message,
                transaction_limit=AIService.MAX_TRANSACTION_CONTEXT,
            )

            financial_context["today"] = today().isoformat()
            financial_context["intent"] = intent

            if focus:
                financial_context["focus"] = focus

        context = AIService._prompt_context(
            user_id=user_id,
            message=message,
            intent=intent,
            financial_context=financial_context,
        )

        prompt = (
            "You are FOCOST AI, a concise but highly capable personal financial assistant.\n\n"
            "AUTHORITATIVE SOURCES:\n"
            "- DashboardService is the sole authority for financial facts, calculations, classifications, rules and forecasts.\n"
            "- SubscriptionService is authoritative for plans, subscription state, entitlements and billing state.\n"
            "- Use only the supplied context. Never invent figures, records, dates, categories, balances or capabilities.\n\n"
            "RESPONSE RULES:\n"
            "- Answer the exact question directly in the shortest complete form.\n"
            "- Use the user's configured currency. For NGN, use ₦.\n"
            "- Simple lookups: one concise sentence or a few bullets.\n"
            "- Breakdowns: use the actual supplied categories/records; never say details are unavailable when they are supplied.\n"
            "- If several financial domains are explicitly requested, answer all requested domains.\n"
            "- Distinguish historical facts, calculated values, forecasts and advice.\n"
            "- Never silently replace an explicit period with a previous conversation period.\n"
            "- For health, clearly distinguish an overall health score from the requested period's income/expense summary when the context does so.\n"
            "- For advice, ground recommendations in supplied financial facts and do not invent arbitrary targets or thresholds.\n"
            "- For investment liquidation, explain the actual FOCOST workflow supplied in context; never claim an action was executed.\n"
            "- Never claim that a payment, update, deletion, liquidation or other operation was completed unless FOCOST confirms it.\n"
            "- Do not repeat the question. Do not add methodology unless asked.\n"
            "- A response must finish completely. Prefer 2-4 compact bullets for complex requests rather than starting a long answer that may be truncated.\n\n"
            f"Requested period: {start.isoformat()} to {end.isoformat()}. Intent: {intent}.\n\n"
            "CONTEXT:\n"
            + json.dumps(
                context,
                ensure_ascii=False,
                default=str,
            )
        )

        return prompt

    @staticmethod
    def chat(user_id, message):
        from app.models.user import User
        user = db.session.get(User, user_id)
        if user and user.is_admin_group:
            return {
                "success": False,
                "code": "AI_ADMIN_FORBIDDEN",
                "message": "FOCOST AI is available only to normal users.",
            }

        # Full history is retained for the current session/UI.
        full_history = AIService._get_session_history()

        # Only a small recent window is sent to the LLM
        # to control token usage.
        ai_history = [
            {
                "role": item.get("role"),
                "content": str(item.get("content", ""))[:500],
            }
            for item in AIService._get_session_history(
                limit=AIService.MAX_AI_HISTORY_MESSAGES
            )
        ]

        # Casual messages do not consume AI usage.
        if AIService._is_casual_message(message):
            text = re.sub(
                r"\s+",
                " ",
                message.lower().strip(),
            )

            casual_responses = {
                "hi": "Hey!",
                "hello": "Hello!",
                "hey": "Hey!",
                "good morning": "Good morning!",
                "good afternoon": "Good afternoon!",
                "good evening": "Good evening!",
                "how are you": "I'm doing well. How can I help?",
                "how are you doing": "I'm doing well. How can I help?",
                "how are things": "I'm doing well. How can I help?",
                "thanks": "You're welcome!",
                "thank you": "You're welcome!",
                "thanks a lot": "You're welcome!",
                "thank you so much": "You're welcome!",
                "ok": "Alright!",
                "okay": "Alright!",
                "alright": "Alright!",
                "great": "Great!",
                "nice": "Nice!",
                "bye": "Goodbye!",
                "goodbye": "Goodbye!",
            }

            response = casual_responses.get(
                text,
                "Alright!",
            )

            AIService._save_session_history(
                full_history + [
                    {
                        "role": "user",
                        "content": message,
                    },
                    {
                        "role": "assistant",
                        "content": response,
                    },
                ]
            )

            return {
                "success": True,
                "message": response,
                "request_id": None,
            }

        # Financial/AI requests consume AI usage.
        allowed, reason = AIUsageService.can_consume(user_id)

        if not allowed:
            return {
                "success": False,
                "code": "AI_USAGE_LIMIT",
                "message": reason,
            }

        # Use the full session history for context resolution so that
        # conversational follow-ups can inherit the previous subject.
        system_prompt = AIService.build_system_prompt(
            user_id,
            message,
            history=full_history,
        )

        request_id = uuid.uuid4().hex
        started = time.perf_counter()

        lower_message = message.lower()
        detailed_request = (
            AIService._is_explanation_followup(message)
            or any(
                phrase in lower_message
                for phrase in (
                    "breakdown", "break it down", "show me", "explain",
                    "how did", "why did", "calculate", "complete",
                    "advice", "advise", "what should i do",
                    "what are my biggest", "trend", "compare",
                )
            )
        )

        result = LLMService().chat(
            user_message=message,
            system_prompt=system_prompt,

            # Only send the limited recent history to the LLM.
            history=ai_history,

            # Short responses by default.
            # More room only when the user explicitly requests detail.
            max_tokens=(
                200
                if detailed_request
                else 150
            ),
        )

        duration_ms = int(
            (time.perf_counter() - started) * 1000
        )

        result["request_id"] = request_id

        AIUsageService.record(
            user_id,
            request_id,
            result,
            duration_ms,
        )

        if result.get("success"):
            AIService._save_session_history(
                full_history + [
                    {
                        "role": "user",
                        "content": message,
                    },
                    {
                        "role": "assistant",
                        "content": result["message"],
                    },
                ]
            )

        return result