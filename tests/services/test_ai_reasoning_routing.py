import pytest

from app.services.ai_service import AIService


def test_last_month_period_is_resolved_from_application_today():
    start, end = AIService._period_from_message("my expenses last month")

    assert start.day == 1
    assert end >= start
    assert end.day >= 28


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("my expenses last month", "expenses"),
        ("what did I earn this month", "income"),
        ("compare my spending over time", "comparison"),
        ("what should I do to improve my finances", "advice"),
        ("what is my financial health score", "health"),
        ("how much do I have", "balance"),
        ("show my goals", "goals"),
        ("what are my budgets", "budgets"),
        ("what is my investment gain", "investments"),
    ],
)
def test_financial_intent_routing(message, expected):
    assert AIService._classify_intent(message) == expected


def test_explicit_period_wins_over_previous_conversation_period():
    assert AIService._is_explicit_period("my expenses last month")
    assert AIService._is_explicit_period("my expenses in September 2026")
    assert not AIService._is_explicit_period("what about income?")


def test_contextual_followups_are_detected():
    assert AIService._is_contextual_followup("which ones?")
    assert AIService._is_contextual_followup("why?")
    assert AIService._is_contextual_followup("more")
