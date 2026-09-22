from datetime import date, timedelta
import calendar
import json
import re
import time
import uuid

from flask import session

from app.services.dashboard_service import DashboardService
from app.services.llm_service import LLMService
from app.services.ai_usage_service import AIUsageService


class AIService:
    """FOCOST AI domain service.

    Financial data is retrieved on demand from DashboardService.
    Conversation history and lightweight conversation context are temporary
    Flask-session state only. Financial records are never stored in session.
    """

    MAX_HISTORY_MESSAGES = 4
    MAX_TRANSACTION_CONTEXT = 30
    MAX_MONTHLY_HISTORY = 12

    @staticmethod
    def _period_from_message(message):
        text = re.sub(r"\s+", " ", message.lower().strip())
        today = date.today()

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
                year = int(match.group(2) or today.year)
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
            d = today - timedelta(days=1)
            return d, d

        if "last week" in text:
            end = today - timedelta(days=today.weekday() + 1)
            return end - timedelta(days=6), end

        if "this week" in text:
            return today - timedelta(days=today.weekday()), today

        if "last month" in text:
            first = today.replace(day=1)
            end = first - timedelta(days=1)
            return end.replace(day=1), end

        if "this month" in text:
            return today.replace(day=1), today

        if "last quarter" in text:
            q = (today.month - 1) // 3
            year = today.year

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
            q = (today.month - 1) // 3 + 1

            return (
                date(today.year, (q - 1) * 3 + 1, 1),
                today,
            )

        if "last year" in text:
            return (
                date(today.year - 1, 1, 1),
                date(today.year - 1, 12, 31),
            )

        if "this year" in text:
            return date(today.year, 1, 1), today

        return today.replace(day=1), today

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
    def _get_session_history():
        history = session.get("ai_history", [])

        if not isinstance(history, list):
            return []

        valid = []

        for item in history[-AIService.MAX_HISTORY_MESSAGES:]:
            if (
                isinstance(item, dict)
                and item.get("role") in {"user", "assistant"}
                and isinstance(item.get("content"), str)
            ):
                valid.append({
                    "role": item["role"],
                    "content": item["content"],
                })

        return valid

    @staticmethod
    def _save_session_history(history):
        session["ai_history"] = history[-AIService.MAX_HISTORY_MESSAGES:]
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

        context = DashboardService.financial_context(
            user_id=user_id,
            start=start,
            end=end,
            intent=intent,
            focus=focus,
            message=message,
            transaction_limit=AIService.MAX_TRANSACTION_CONTEXT,
        )

        context["today"] = date.today().isoformat()
        context["intent"] = intent

        if focus:
            context["focus"] = focus

        if intent == "comparison":
            context["monthly_history"] = DashboardService.monthly_series(
                user_id,
                months=AIService.MAX_MONTHLY_HISTORY,
            )

        elif intent == "forecast":
            user_context = DashboardService._ai_user_context(user_id)

            context["user"] = user_context
            context["currency"] = user_context.get("currency", "NGN")

            context["monthly_history"] = DashboardService.monthly_series(
                user_id,
                months=AIService.MAX_MONTHLY_HISTORY,
            )

            context["advanced_forecast"] = (
                DashboardService.advanced_forecast(
                    user_id,
                    months_ahead=3,
                )
            )

            context["month_end_forecast"] = (
                DashboardService.month_end_forecast(user_id)
            )

            context["category_forecasts"] = (
                DashboardService.category_forecasts(
                    user_id,
                    months=3,
                )
            )

        elif intent in {"health", "advice"}:
            context["financial_health"] = (
                DashboardService.build_financial_health(user_id)
            )

        if intent == "advice":
            context["monthly_history"] = DashboardService.monthly_series(
                user_id,
                months=6,
            )

        return (
            "You are FOCOST AI, a concise personal financial assistant.\n\n"

            "STRICT RESPONSE RULES:\n"
            "- Answer the user's question directly.\n"
            "- Use clear, simple Nigerian English and maintain a friendly, warm, and approachable tone.\n"
            "- Default to 1-3 short sentences.\n"
            "- Use at most 3 brief bullet points when necessary.\n"
            "- Never repeat the user's question.\n"
            "- Never invent financial figures, transactions, categories, "
            "merchants, dates, balances, or account facts.\n"
            "- Use only the supplied database-derived context.\n"
            "- Distinguish historical facts, calculations, forecasts, and "
            "recommendations.\n"
            "- Forecasts are estimates, not guarantees.\n"
            "- Recommendations must be grounded in the user's actual "
            "financial data supplied in the context.\n"
            "- Do not introduce arbitrary financial thresholds, percentages, "
            "ratios, savings targets, expense caps, or budgeting rules.\n"
            "- Do not recommend a percentage-based target unless that percentage "
            "is explicitly present in the supplied financial context or the user "
            "explicitly asks for a general percentage-based guideline.\n"
            "- Do not invent a weekly, monthly, or category spending limit.\n"
            "- Prefer concrete actions derived directly from the user's actual "
            "income, expenses, savings, goals, budgets, cash flow, and trends.\n"
            "- Do not promise or predict a specific financial outcome unless it "
            "can be directly calculated from the supplied data.\n"
            "- Prefer recommendations based on the user's actual income, "
            "expenses, savings, goals, budgets, cash flow, and trends.\n"
            "- If the supplied context does not contain the requested "
            "information, say so briefly.\n"
            "- Distinguish operating expenses from investments and goal "
            "contributions when the context provides transaction_class.\n"
            "- Use the user's configured currency from the database-derived context.\n"
            "- Treat the configured currency as authoritative.\n"
            "- Never assume USD or use \"$\" unless the configured currency is USD.\n"
            "- If the configured currency is NGN, display monetary amounts using \"₦\".\n"
            "- Never convert financial amounts between currencies unless the user explicitly requests conversion.\n"
            "- Never invent or substitute a currency symbol.\n"
            "- Keep the answer concise unless the user explicitly asks "
            "for detail.\n\n"

            "AUTHORITATIVE DATABASE CONTEXT:\n"
            + json.dumps(
                context,
                ensure_ascii=False,
                default=str,
            )
        )

    @staticmethod
    def chat(user_id, message):
        history = AIService._get_session_history()

        # Casual messages do not consume AI usage.
        if AIService._is_casual_message(message):
            text = re.sub(r"\s+", " ", message.lower().strip())

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
                history + [
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

        system_prompt = AIService.build_system_prompt(
            user_id,
            message,
            history=history,
        )

        request_id = uuid.uuid4().hex
        started = time.perf_counter()

        result = LLMService().chat(
            user_message=message,
            system_prompt=system_prompt,
            history=history,
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
                history + [
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