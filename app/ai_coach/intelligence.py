"""
FOCOST AI Coach intelligence layer.

This module intentionally contains no database access and no financial
source-of-truth calculations. It consumes the authoritative context produced
by DashboardService and adds higher-order statistical/interpretive signals
that help FOCOST AI reason about the supplied data.

DashboardService remains the authority for:
- financial totals and balances
- classifications and definitions
- budgets, goals and investments
- forecasts, anomalies and dashboard metrics

The coach layer may summarize, rank, classify, and assess evidence quality
from those supplied values, but it must never replace or recalculate a
DashboardService financial fact.
"""

from __future__ import annotations

from math import sqrt
from statistics import mean, pstdev
from typing import Any


class CoachIntelligence:
    """Pure analytical lens over DashboardService-provided AI context."""

    @staticmethod
    def _numbers(values):
        return [
            float(value)
            for value in values
            if isinstance(value, (int, float))
        ]

    @staticmethod
    def _variation(values):
        values = CoachIntelligence._numbers(values)
        if len(values) < 2:
            return None
        average = mean(values)
        if average == 0:
            return None
        return round(pstdev(values) / abs(average), 4)

    @staticmethod
    def _trend_signal(values):
        """Return a descriptive trend signal without replacing source values."""
        values = CoachIntelligence._numbers(values)
        if len(values) < 3:
            return "insufficient_history"

        first = mean(values[: max(1, len(values) // 3)])
        last = mean(values[-max(1, len(values) // 3):])

        if first == last:
            return "stable"
        if last > first:
            return "rising"
        return "falling"

    @staticmethod
    def _history_statistics(history):
        if not isinstance(history, list):
            return {}

        incomes = [
            item.get("income")
            for item in history
            if isinstance(item, dict)
        ]
        expenses = [
            item.get("expenses", item.get("expense"))
            for item in history
            if isinstance(item, dict)
        ]
        savings = [
            item.get("savings")
            for item in history
            if isinstance(item, dict)
        ]

        income_values = CoachIntelligence._numbers(incomes)
        expense_values = CoachIntelligence._numbers(expenses)
        savings_values = CoachIntelligence._numbers(savings)

        result = {
            "history_points": len(history),
            "income_variability": CoachIntelligence._variation(income_values),
            "expense_variability": CoachIntelligence._variation(expense_values),
            "savings_variability": CoachIntelligence._variation(savings_values),
            "income_trend": CoachIntelligence._trend_signal(income_values),
            "expense_trend": CoachIntelligence._trend_signal(expense_values),
            "savings_trend": CoachIntelligence._trend_signal(savings_values),
        }

        if savings_values:
            result["positive_savings_periods"] = sum(
                value > 0 for value in savings_values
            )
            result["negative_savings_periods"] = sum(
                value < 0 for value in savings_values
            )

        return result

    @staticmethod
    def _concentration(rows, share_key="percentage_of_total"):
        if not isinstance(rows, list):
            return {}

        shares = [
            float(row.get(share_key) or 0)
            for row in rows
            if isinstance(row, dict)
            and isinstance(row.get(share_key), (int, float))
        ]

        if not shares:
            return {}

        ranked = sorted(
            (
                row for row in rows
                if isinstance(row, dict)
                and isinstance(row.get(share_key), (int, float))
            ),
            key=lambda row: float(row.get(share_key) or 0),
            reverse=True,
        )

        top = ranked[:3]
        return {
            "top_share_percent": round(shares[0], 2),
            "top_three_share_percent": round(
                sum(float(row.get(share_key) or 0) for row in top),
                2,
            ),
            "concentration_level": (
                "high"
                if shares[0] >= 50
                else "moderate"
                if shares[0] >= 30
                else "distributed"
            ),
        }

    @staticmethod
    def _evidence_quality(context):
        if not isinstance(context, dict):
            return {
                "level": "insufficient",
                "reasons": ["No authoritative context was supplied."],
            }

        reasons = []
        available = 0

        for key in (
            "summary",
            "income",
            "expenses",
            "savings",
            "financial_health",
            "budgets",
            "goals",
            "investments",
            "monthly_history",
            "advanced_forecast",
            "month_end_forecast",
            "category_forecasts",
            "records",
        ):
            if key in context and context[key] not in (None, [], {}):
                available += 1

        record_count = context.get("record_count")
        returned = context.get("record_count_returned")

        if isinstance(record_count, int) and isinstance(returned, int):
            if returned < record_count:
                reasons.append(
                    "Detailed records are intentionally limited; "
                    "authoritative totals remain available separately."
                )

        calculation_context = context.get("calculation_context")
        if isinstance(calculation_context, dict):
            reasons.append(
                "DashboardService calculation rules are attached to the context."
            )
            available += 1

        if available >= 5:
            level = "strong"
        elif available >= 2:
            level = "moderate"
        else:
            level = "limited"

        return {
            "level": level,
            "context_sections_available": available,
            "reasons": reasons,
        }

    @staticmethod
    def analyze(context: dict[str, Any], intent: str | None = None):
        """
        Build higher-order intelligence from authoritative AI context.

        No database query is performed here. No DashboardService financial
        total is recomputed here.
        """
        context = context if isinstance(context, dict) else {}
        result = {
            "role": "interpretive_layer",
            "source": "DashboardService.financial_context",
            "intent": intent or context.get("intent"),
            "evidence_quality": CoachIntelligence._evidence_quality(context),
        }

        history = (
            context.get("monthly_history")
            or context.get("monthly_series")
            or context.get("history")
        )
        history_stats = CoachIntelligence._history_statistics(history)
        if history_stats:
            result["historical_statistics"] = history_stats

        expense_concentration = CoachIntelligence._concentration(
            context.get("category_breakdown")
        )
        if expense_concentration:
            result["expense_concentration"] = expense_concentration

        merchant_concentration = CoachIntelligence._concentration(
            context.get("merchant_breakdown"),
            share_key="percentage_of_total",
        )
        if merchant_concentration:
            result["merchant_concentration"] = merchant_concentration

        forecast = context.get("advanced_forecast")
        if isinstance(forecast, dict):
            result["forecast_evidence"] = {
                "available": forecast.get("available"),
                "method": forecast.get("method"),
                "income_confidence": forecast.get("income_confidence"),
                "expense_confidence": forecast.get("expense_confidence"),
                "history_months": forecast.get("history_months"),
            }

        anomalies = context.get("anomalies")
        if isinstance(anomalies, dict):
            anomaly_rows = anomalies.get("anomalies") or []
            result["anomaly_evidence"] = {
                "available": anomalies.get("available"),
                "count": len(anomaly_rows),
                "highest_z_score": max(
                    (
                        float(item.get("z_score") or 0)
                        for item in anomaly_rows
                        if isinstance(item, dict)
                    ),
                    default=None,
                ),
            }

        signals = []
        if history_stats.get("expense_trend") == "rising":
            signals.append("Historical expense levels are rising.")
        if history_stats.get("savings_trend") == "falling":
            signals.append("Historical savings levels are falling.")
        if expense_concentration.get("concentration_level") == "high":
            signals.append("Spending is concentrated in a small number of categories.")
        if merchant_concentration.get("concentration_level") == "high":
            signals.append("Spending is concentrated among a small number of merchants.")

        if signals:
            result["interpretive_signals"] = signals

        return result
