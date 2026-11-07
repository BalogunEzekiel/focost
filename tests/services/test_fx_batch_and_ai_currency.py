from datetime import date
from decimal import Decimal

from app.extensions import db
from app.models.exchange_rate import ExchangeRate
from app.models.income import Income
from app.models.expense import Expense
from app.services.exchange_rate_service import ExchangeRateProvider, ExchangeRateService
from app.services.language_service import LanguageService
from app.services.dashboard_service import DashboardService


def test_batch_conversion_fetches_once_per_base_and_date(app, monkeypatch):
    calls = []

    def fake_fetch_all(self, base, on_date=None):
        calls.append((base, on_date))
        return {"NGN": Decimal("1"), "GBP": Decimal("0.0005")}

    monkeypatch.setattr(ExchangeRateProvider, "fetch_all", fake_fetch_all)
    with app.app_context():
        results = ExchangeRateService.convert_many([
            {"amount": "100000", "source_currency": "NGN", "date": date(2026, 10, 1)},
            {"amount": "200000", "source_currency": "NGN", "date": date(2026, 10, 1)},
        ], "GBP")

        assert len(calls) == 1
        assert results[0]["converted_amount"] == Decimal("50.00")
        assert results[1]["converted_amount"] == Decimal("100.00")
        assert results[0]["original_amount"] == Decimal("100000")
        assert results[0]["original_currency"] == "NGN"
        assert ExchangeRate.query.filter_by(
            base_currency="NGN", quote_currency="GBP", rate_date=date(2026, 10, 1)
        ).count() == 1


def test_ai_income_context_aggregates_mixed_currencies_in_display_currency(app, user, monkeypatch):
    def fake_fetch_all(self, base, on_date=None):
        rates = {
            "NGN": {"GBP": Decimal("0.0005")},
            "USD": {"GBP": Decimal("0.8")},
        }
        return rates[base]

    monkeypatch.setattr(ExchangeRateProvider, "fetch_all", fake_fetch_all)
    with app.app_context():
        user.currency = "GBP"
        db.session.add_all([
            Income(user_id=user.id, source="Salary", category="Employment", amount=100000, currency="NGN", received_date=date(2026, 10, 1)),
            Income(user_id=user.id, source="Contract", category="Freelance", amount=100, currency="USD", received_date=date(2026, 10, 1)),
        ])
        db.session.commit()

        context = DashboardService.ai_income_context(user.id, date(2026, 10, 1), date(2026, 10, 31), limit=10)

        assert context["currency"] == "GBP"
        assert context["total"] == 130.0
        assert {row["original_currency"] for row in context["records"]} == {"NGN", "USD"}
        assert all(row["currency"] == "GBP" for row in context["records"])


def test_exact_notification_title_translation_is_safe_for_user_content():
    assert LanguageService.translate_text("ha", "Budget Exceeded") == "An Wuce Kasafin Kuɗi"
    user_text = "Paid by Amaka at Shoprite"
    assert LanguageService.translate_text("ha", user_text) == user_text


def test_ai_expense_context_converts_mixed_currency_totals(app, user, monkeypatch):
    def fake_fetch_all(self, base, on_date=None):
        rates = {
            "NGN": {"GBP": Decimal("0.0005")},
            "USD": {"GBP": Decimal("0.8")},
        }
        return rates[base]

    monkeypatch.setattr(ExchangeRateProvider, "fetch_all", fake_fetch_all)
    with app.app_context():
        user.currency = "GBP"
        db.session.add_all([
            Expense(user_id=user.id, category="Food", merchant="Market", amount=20000, currency="NGN", payment_method="Cash", expense_date=date(2026, 10, 2)),
            Expense(user_id=user.id, category="Travel", merchant="Rail", amount=50, currency="USD", payment_method="Card", expense_date=date(2026, 10, 3)),
        ])
        db.session.commit()

        context = DashboardService.ai_expense_context(user.id, date(2026, 10, 1), date(2026, 10, 31), limit=10)

        assert context["currency"] == "GBP"
        assert context["total_matching_amount"] == 50.0
        assert {row["original_currency"] for row in context["records"]} == {"NGN", "USD"}
        assert all(row["currency"] == "GBP" for row in context["records"])


def test_parameterized_notification_text_is_localized_without_translating_user_name():
    translated = LanguageService.translate_text("ha", "You achieved your 'Emergency Fund' goal.")
    assert "Emergency Fund" in translated
    assert translated != "You achieved your 'Emergency Fund' goal."
