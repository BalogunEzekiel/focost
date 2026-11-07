from datetime import date
from decimal import Decimal

import pytest

from app.extensions import db
from app.models.exchange_rate import ExchangeRate
from app.services.exchange_rate_service import ExchangeRateService, ExchangeRateUnavailable


def test_same_currency_conversion_does_not_require_provider(app):
    with app.app_context():
        assert ExchangeRateService.convert("1250.50", "NGN", "NGN") == Decimal("1250.50")


def test_conversion_uses_and_persists_provider_quote(app, monkeypatch):
    with app.app_context():
        class FakeProvider:
            name = "test-provider"

            def fetch(self, base, quote, on_date=None):
                assert (base, quote) == ("NGN", "GBP")
                return Decimal("0.0005")

        monkeypatch.setattr("app.services.exchange_rate_service.ExchangeRateProvider", FakeProvider)
        converted = ExchangeRateService.convert("2000000", "NGN", "GBP", on_date=date(2026, 11, 6))
        assert converted == Decimal("1000.00")
        row = db.session.query(ExchangeRate).filter_by(
            base_currency="NGN", quote_currency="GBP", rate_date=date(2026, 11, 6)
        ).one()
        assert Decimal(row.rate) == Decimal("0.0005")
        assert row.source == "test-provider"


def test_unsupported_currency_is_rejected(app):
    with app.app_context():
        with pytest.raises(ValueError, match="Unsupported currency"):
            ExchangeRateService.convert("100", "NGN", "XYZ")


def test_provider_missing_key_fails_closed(app, monkeypatch):
    with app.app_context():
        app.config["EXCHANGE_RATE_API_KEY"] = ""
        monkeypatch.delenv("EXCHANGE_RATE_API_KEY", raising=False)
        from app.services.exchange_rate_service import ExchangeRateProvider
        with pytest.raises(ExchangeRateUnavailable, match="not configured"):
            ExchangeRateProvider().fetch("NGN", "GBP")


def test_display_currency_is_separate_from_ledger_currency(app, user):
    from app.services.currency_service import CurrencyService
    with app.app_context():
        user.base_currency = "NGN"
        CurrencyService.set(user, "GBP")
        assert user.currency == "GBP"
        assert user.base_currency == "NGN"
