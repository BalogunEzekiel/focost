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


class AIService:
    """FOCOST AI domain service.

    Financial data is retrieved on demand from DashboardService.
    Conversation history and lightweight conversation context are temporary
    Flask-session state only. Financial records are never stored in session.
    """

    # Visible conversation history is retained for the current session.
    # The AI receives only a smaller recent window to control token usage.
    MAX_VISIBLE_HISTORY_MESSAGES = 100
    MAX_AI_HISTORY_MESSAGES = 6
    MAX_TRANSACTION_CONTEXT = 12
    MAX_MONTHLY_HISTORY = 6

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

        # A generic follow-up such as "how can I do better?" should retain
        # the previous period but use the new advice intent.
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

        resolved_context = {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "intent": current_intent,
            "focus": focus,
        }

        session["ai_context"] = resolved_context
        session.modified = True

        return start, end, current_intent, focus

    @staticmethod
    def build_system_prompt(user_id, message="", history=None):
        history = history or []

        if AIService._is_casual_message(message):
            return (
                "You are FOCOST AI.\n"
                "Respond naturally and briefly. For greetings, thanks, "
                "acknowledgements, or casual conversation, use one short "
                "sentence. Do not discuss financial data unless asked."
            )

        start, end, intent, focus = AIService._resolve_context(
            message,
            history,
        )

        # DashboardService is the single authoritative financial-data source.
        # All required financial context should be supplied here rather than
        # being fetched again below.
        context = DashboardService.financial_context(
            user_id,
            start,
            end,
            intent=intent,
            focus=focus,
            message=message,
            transaction_limit=AIService.MAX_TRANSACTION_CONTEXT,
        )

        context["today"] = today().isoformat()
        context["intent"] = intent

        if focus:
            context["focus"] = focus

        return (
            "You are FOCOST AI, a concise but highly capable personal financial assistant.\n\n"

            "CORE PRINCIPLE:\n"
            "DashboardService is the authoritative financial calculation engine.\n"
            "The supplied AUTHORITATIVE DATABASE CONTEXT and its "
            "`calculation_context` are the source of truth.\n"
            "You must explain DashboardService's calculations and records rather "
            "than inventing your own figures or claiming that information is "
            "unavailable when the supplied context contains it.\n\n"

            "STRICT RESPONSE RULES:\n"

            "- Answer the user's question directly.\n"

            "- Use clear, simple Nigerian English and maintain a friendly, warm, "
            "and approachable tone.\n"

            "- Default to the shortest useful answer. For a simple lookup, answer "
            "with one sentence whenever possible. Do not add explanations, methodology, "
            "tables, classifications, or extra context unless the user asks for them.\n"

            "- For simple lookups such as 'income', 'expenses', 'savings', 'balance', "
            "or 'goals', give the requested figure/summary directly. Do not add a table, "
            "methodology, raw records, or explanation unless the user asks for a breakdown.\n"

            "- For a simple period summary such as 'last month', give only the requested "
            "key figures. Do not automatically provide calculation methodology.\n"

            "- Use tables only when the user explicitly asks for a table, detailed breakdown, "
            "or when a table is clearly necessary to answer the request.\n"

            "- Become more detailed only when the user asks 'how', 'why', 'breakdown', "
            "'explain', 'where did this come from', 'how did you calculate', 'show me', "
            "or asks for supporting details.\n"

            "- Never repeat the user's question.\n"

            "- Never invent financial figures, transactions, categories, merchants, "
            "dates, balances, formulas, or account facts.\n"

            "- Use only the supplied database-derived context.\n"

            "- Treat `calculation_context` as the authoritative explanation of "
            "how DashboardService-derived figures were calculated.\n"

            "- When a figure is questioned, explain the exact calculation using "
            "the supplied calculation_context.\n"

            "- When the user asks for a breakdown, use the actual underlying "
            "transaction records, categories, classifications, and calculation "
            "details supplied in the context.\n"

            "- For expense breakdowns, include Goal Contributions and Investment "
            "Funding when they are recorded as expenses. Do not hide or merge "
            "those transactions into a generic expense category.\n"

            "- A Goal Contribution is a legitimate expense transaction for "
            "financial reporting and expense analysis. If multiple Goal "
            "Contributions make up a requested expense total, identify the "
            "individual contribution amounts when those records are supplied.\n"

            "- For example, if today's expense total is ₦50,000 and the supplied "
            "records contain Goal Contributions of ₦45,000 and ₦5,000, answer "
            "that the ₦50,000 consists of those two Goal Contributions. Do not "
            "invent merchants or categories.\n"

            "- Never respond that you do not have a category breakdown, transaction "
            "breakdown, calculation explanation, or supporting information if the "
            "supplied context contains those details.\n"

            "- If a total can be reconciled from supplied records, explicitly "
            "reconcile it.\n"

            "- When explaining a total, show the relevant components and the "
            "relationship between them.\n"

            "- When appropriate, use a compact equation such as:\n"
            "  Total expenses = Expense A + Expense B + Expense C\n"

            "- If the user asks why two dashboard figures differ, explain the "
            "different definitions, classifications, periods, or calculation "
            "rules supplied in the context.\n"

            "- Distinguish historical facts, calculated values, forecasts, "
            "recommendations, and interpretations.\n"

            "- Forecasts are estimates based on the supplied DashboardService "
            "forecast methodology, not guarantees.\n"

            "- When explaining a forecast, identify the current-period inputs, "
            "calculation method, projected components, and resulting forecast "
            "where those details are supplied.\n"

            "- If a forecast contains projected income, projected expenses, and "
            "projected savings, explain how the projected savings relates to the "
            "projected income and projected expenses.\n"

            "- If category forecasts are supplied, use them to explain the "
            "category-level contribution to the forecast.\n"

            "- Recommendations must be grounded in the user's actual financial "
            "data and DashboardService rules.\n"

            "- Do not introduce arbitrary financial thresholds, percentages, "
            "ratios, savings targets, expense caps, or budgeting rules.\n"

            "- Do not recommend a percentage-based target unless that percentage "
            "is explicitly present in the supplied financial context or the user "
            "explicitly asks for a general percentage-based guideline.\n"

            "- Do not invent a weekly, monthly, or category spending limit.\n"

            "- Prefer concrete actions derived directly from the user's actual "
            "income, expenses, savings, goals, budgets, cash flow, and trends.\n"

            "- Never promise or predict a specific financial outcome unless it "
            "can be directly calculated from the supplied data.\n"

            "- Distinguish operating expenses from investment funding, liquidation "
            "proceeds, and goal contributions when "
            "the context provides transaction_class or equivalent classification.\n"

            "- Do not silently treat an investment funding transaction as an "
            "ordinary operating expense when DashboardService identifies it as "
            "investment funding.\n"

            "- Do not silently treat investment liquidation proceeds as ordinary "
            "operating income when the supplied classification identifies their "
            "investment origin. Investment valuation gains/losses are non-cash "
            "and are not income.\n"

            "- Use the user's configured currency from the database-derived context.\n"

            "- Treat the configured currency as authoritative.\n"

            "- Never assume USD or use '$' unless the configured currency is USD.\n"

            "- If the configured currency is NGN, display monetary amounts using '₦'.\n"

            "- Never convert financial amounts between currencies unless the user "
            "explicitly requests conversion.\n"

            "- Never invent or substitute a currency symbol.\n"

            "- Keep simple answers concise, but provide sufficient evidence and "
            "calculation detail whenever the user asks for an explanation or "
            "breakdown.\n\n"

            "CONCISE RESPONSE STYLE:\n"

            "For a direct metric request, prefer: 'Income for September: ₦270,000.' "
            "If useful, add only the key components in one short sentence. Do not repeat "
            "database classifications or internal service names unless the user asks why.\n"

            "CALCULATION EXPLANATION PROTOCOL:\n"

            "When the user asks how a DashboardService figure was obtained:\n"

            "1. Identify the figure being discussed.\n"
            "2. Identify its period or point-in-time definition.\n"
            "3. Identify the source records or components supplied in context.\n"
            "4. Identify the DashboardService formula or rule supplied in "
            "calculation_context.\n"
            "5. Show the calculation using the actual supplied numbers.\n"
            "6. State the resulting figure.\n"
            "7. If useful, explain what the result means for the user's finances.\n\n"

            "BREAKDOWN PROTOCOL:\n"

            "If the user asks for an expense, income, savings, balance, investment, "
            "budget, goal, or forecast breakdown, do not merely repeat the total. "
            "Break the figure into the relevant supplied components.\n\n"

            "FORECAST EXPLANATION PROTOCOL:\n"

            "If the user asks how a forecast was produced, explain the actual "
            "DashboardService methodology supplied in calculation_context. "
            "Do not replace that methodology with a generic forecasting method.\n\n"

            "CONTEXT AVAILABILITY RULE:\n"

            "If the requested information is genuinely absent from the supplied "
            "context, say so briefly and specifically. Do not make a generic claim "
            "that information is unavailable when related records or calculations "
            "are present.\n\n"

            "AUTHORITATIVE DATABASE CONTEXT:\n"
            + json.dumps(
                context,
                ensure_ascii=False,
                default=str,
            )
        )

    @staticmethod
    def chat(user_id, message):
        from app.models.user import User
        user = db.session.get(User, user_id)
        if user and user.role_slug in {"admin", "super_admin"}:
            return {
                "success": False,
                "code": "AI_ADMIN_FORBIDDEN",
                "message": "FOCOST AI is available only to normal users.",
            }

        # Full history is retained for the current session/UI.
        full_history = AIService._get_session_history()

        # Only a small recent window is sent to the LLM
        # to control token usage.
        ai_history = AIService._get_session_history(
            limit=AIService.MAX_AI_HISTORY_MESSAGES
        )

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

        detailed_request = (
            AIService._is_explanation_followup(message)
            or any(
                phrase in message.lower()
                for phrase in (
                    "breakdown",
                    "break it down",
                    "show me",
                    "explain",
                    "how did",
                    "why did",
                    "calculate",
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
                320
                if detailed_request
                else 120
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