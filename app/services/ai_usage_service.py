from datetime import datetime
import os
from sqlalchemy import func

from app.extensions import db
from app.models.ai_usage import AIUsage
from app.subscriptions.service import SubscriptionService


class AIUsageService:
    """Persistent AI consumption tracking tied to the user's active billing period."""

    @staticmethod
    def current_period(user_id):
        sub = SubscriptionService.current(user_id)
        now = datetime.utcnow()

        if not sub:
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), None

        if sub.is_trial:
            start = sub.trial_started_at or sub.created_at or now
            end = sub.trial_ends_at
        else:
            start = sub.current_period_start or sub.started_at or sub.created_at or now
            end = sub.current_period_end

        return start, end

    @staticmethod
    def period_start(user_id=None):
        if user_id is None:
            now = datetime.utcnow()
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return AIUsageService.current_period(user_id)[0]

    @staticmethod
    def monthly(user_id):
        start, end = AIUsageService.current_period(user_id)

        query = db.session.query(
            func.coalesce(func.sum(AIUsage.input_tokens), 0),
            func.coalesce(func.sum(AIUsage.output_tokens), 0),
            func.coalesce(func.sum(AIUsage.total_tokens), 0),
            func.count(AIUsage.id),
        ).filter(
            AIUsage.user_id == user_id,
            AIUsage.status == "success",
            (
                (AIUsage.billing_period_start == start)
                | (
                    AIUsage.billing_period_start.is_(None)
                    & (AIUsage.created_at >= start)
                )
            ),
        )

        if end:
            query = query.filter(AIUsage.created_at < end)

        row = query.one()
        ent = SubscriptionService.entitlements(user_id)

        used = int(row[2] or 0)
        requests = int(row[3] or 0)
        token_limit = ent.get("ai_token_limit")
        request_limit = ent.get("ai_request_limit")

        return {
            "period_start": start.isoformat() if start else None,
            "period_end": end.isoformat() if end else None,
            "billing_status": ent.get("status"),
            "plan_name": ent.get("plan_name"),
            "input_tokens": int(row[0] or 0),
            "output_tokens": int(row[1] or 0),
            "total_tokens": used,
            "requests": requests,
            "token_limit": token_limit,
            "request_limit": request_limit,
            "remaining_tokens": None if token_limit is None else max(token_limit - used, 0),
            "remaining_requests": None if request_limit is None else max(request_limit - requests, 0),
            "token_exceeded": token_limit is not None and used >= token_limit,
            "request_exceeded": request_limit is not None and requests >= request_limit,
        }

    @staticmethod
    def can_consume(user_id):
        ent = SubscriptionService.entitlements(user_id)
        if not ent.get("active"):
            return False, "Your trial or subscription is not active."

        usage = AIUsageService.monthly(user_id)

        if usage["token_exceeded"] or usage["request_exceeded"]:
            return False, (
                "You have reached your AI usage allowance for this billing period. "
                "Your allowance will renew with your next active billing period."
            )

        return True, None

    @staticmethod
    def record(user_id, request_id, result, duration_ms):
        input_rate = float(os.getenv("FOCOST_AI_INPUT_COST_PER_1M_USD", "0"))
        output_rate = float(os.getenv("FOCOST_AI_OUTPUT_COST_PER_1M_USD", "0"))

        input_tokens = int(result.get("usage", {}).get("input_tokens", 0) or 0)
        output_tokens = int(result.get("usage", {}).get("output_tokens", 0) or 0)
        total_tokens = int(result.get("usage", {}).get("total_tokens", 0) or 0)

        usd = (
            (input_tokens / 1_000_000) * input_rate
            + (output_tokens / 1_000_000) * output_rate
        )

        usd_ngn = float(os.getenv("FOCOST_USD_NGN_RATE", "0"))
        estimated_cost_minor = round(usd * usd_ngn * 100) if usd_ngn else 0

        usage = AIUsage(
            user_id=user_id,
            request_id=request_id,
            provider=result.get("provider"),
            model=result.get("model"),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            duration_ms=duration_ms,
            estimated_cost_minor=estimated_cost_minor,
            status="success" if result.get("success") else "failed",
            error_message=result.get("message") if not result.get("success") else None,
            billing_period_start=AIUsageService.current_period(user_id)[0],
        )

        db.session.add(usage)
        db.session.commit()
        return usage
