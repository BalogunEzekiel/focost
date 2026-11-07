"""Auditable, batched FX conversion with persistent historical snapshots.

Provider: ExchangeRate-API v6. Historical quotes require a plan that enables
historical endpoints. A provider response contains all supported quotes for a
base currency, so report conversion fetches one snapshot per base/date instead
of one HTTP request per currency pair. Original ledger values are never changed.
"""
from __future__ import annotations

import os
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import httpx
from flask import current_app, g, has_request_context
from sqlalchemy import select

from app.extensions import db
from app.models.exchange_rate import ExchangeRate
from app.services.currency_service import CURRENCIES


class ExchangeRateUnavailable(RuntimeError):
    """Raised when an authoritative exchange rate cannot be obtained."""


class ExchangeRateProvider:
    name = "exchangerate-api"
    base_url = "https://v6.exchangerate-api.com/v6"

    def __init__(self, api_key=None, timeout=8.0):
        self.api_key = (
            api_key
            or current_app.config.get("EXCHANGE_RATE_API_KEY")
            or os.getenv("EXCHANGE_RATE_API_KEY")
        )
        self.timeout = timeout

    def fetch_all(self, base: str, on_date: date | None = None) -> dict[str, Decimal]:
        if not self.api_key:
            raise ExchangeRateUnavailable(
                "Exchange-rate provider is not configured. Set EXCHANGE_RATE_API_KEY."
            )
        path = (
            f"history/{base}/{on_date.year}/{on_date.month}/{on_date.day}"
            if on_date else f"latest/{base}"
        )
        url = f"{self.base_url}/{self.api_key}/{path}"
        try:
            response = httpx.get(url, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ExchangeRateUnavailable(
                "Exchange-rate provider request failed. Please try again later."
            ) from exc
        if payload.get("result") != "success":
            raise ExchangeRateUnavailable(
                payload.get("error-type") or "Exchange-rate provider returned an unsuccessful response."
            )

        rates = {}
        for quote, raw in (payload.get("conversion_rates") or {}).items():
            quote = str(quote).upper()
            if quote not in CURRENCIES:
                continue
            try:
                rate = Decimal(str(raw))
            except (InvalidOperation, TypeError):
                continue
            if rate.is_finite() and rate > 0:
                rates[quote] = rate
        if base not in rates:
            rates[base] = Decimal("1")
        if len(rates) <= 1:
            raise ExchangeRateUnavailable(f"No usable rates were returned for {base}.")
        return rates

    def fetch(self, base: str, quote: str, on_date: date | None = None) -> Decimal:
        rates = self.fetch_all(base, on_date=on_date)
        try:
            return rates[quote]
        except KeyError as exc:
            raise ExchangeRateUnavailable(f"No {base}/{quote} rate was returned.") from exc


class ExchangeRateService:
    LATEST_TTL_SECONDS = 6 * 60 * 60
    MAX_BATCH_SIZE = 5000

    @staticmethod
    def _valid_code(code: str) -> str:
        code = str(code or "").strip().upper()
        if code not in CURRENCIES:
            raise ValueError(f"Unsupported currency: {code or '(empty)'}")
        return code

    @staticmethod
    def _effective_date(on_date=None):
        return on_date or datetime.now(timezone.utc).date()

    @classmethod
    def get_rates(cls, base: str, quotes, on_date: date | None = None, refresh=False) -> dict[str, Decimal]:
        """Return multiple quotes with one provider fetch per base/date.

        Historical snapshots are immutable cache entries. Latest snapshots are
        refreshed after the configured TTL. A request-local cache avoids repeat
        ORM queries when multiple services format the same report.
        """
        base = cls._valid_code(base)
        quote_codes = sorted({cls._valid_code(code) for code in (quotes or [])})
        if not quote_codes:
            return {}
        effective_date = cls._effective_date(on_date)
        result = {code: Decimal("1") for code in quote_codes if code == base}
        needed = [code for code in quote_codes if code != base]
        if not needed:
            return result

        request_cache = getattr(g, "_focost_fx_rates", None) if has_request_context() else None
        if request_cache is None and has_request_context():
            request_cache = {}
            g._focost_fx_rates = request_cache

        missing = []
        now = datetime.now(timezone.utc)
        for quote in needed:
            cache_key = (base, quote, effective_date.isoformat())
            if request_cache is not None and not refresh and cache_key in request_cache:
                result[quote] = request_cache[cache_key]
                continue
            missing.append(quote)

        if not missing:
            return result

        rows = db.session.execute(
            select(ExchangeRate).where(
                ExchangeRate.base_currency == base,
                ExchangeRate.rate_date == effective_date,
            )
        ).scalars().all()
        by_quote = {row.quote_currency: row for row in rows}

        stale = []
        for quote in missing:
            row = by_quote.get(quote)
            fetched_at = row.fetched_at if row else None
            if fetched_at and fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=timezone.utc)
            fresh = bool(
                row and (
                    row.is_manual
                    or on_date is not None
                    or (fetched_at and (now - fetched_at).total_seconds() < cls.LATEST_TTL_SECONDS)
                )
            )
            if fresh and not refresh:
                rate = Decimal(row.rate)
                result[quote] = rate
                if request_cache is not None:
                    request_cache[(base, quote, effective_date.isoformat())] = rate
            else:
                stale.append(quote)

        if stale:
            provider = ExchangeRateProvider()
            fetch_all = getattr(provider, "fetch_all", None)
            if callable(fetch_all):
                all_rates = fetch_all(base, on_date=on_date)
            else:
                # Backward-compatible adapter contract for test providers and
                # custom providers that implement only fetch(base, quote, date).
                all_rates = {quote: provider.fetch(base, quote, on_date=on_date) for quote in stale}
            # Persist the provider's complete quote set for this base/date.
            # A later report requesting another quote can reuse this snapshot
            # without another network round-trip.
            for quote, rate in all_rates.items():
                if quote == base or quote not in CURRENCIES:
                    continue
                row = by_quote.get(quote)
                if row and row.is_manual:
                    continue
                if row:
                    row.rate = rate
                    row.source = provider.name
                    row.fetched_at = now
                else:
                    db.session.add(ExchangeRate(
                        base_currency=base,
                        quote_currency=quote,
                        rate=rate,
                        rate_date=effective_date,
                        source=provider.name,
                        fetched_at=now,
                    ))
                if request_cache is not None:
                    request_cache[(base, quote, effective_date.isoformat())] = rate
            for quote in stale:
                if quote not in all_rates and quote not in result:
                    raise ExchangeRateUnavailable(f"No {base}/{quote} rate was returned.")
                if quote in all_rates:
                    result[quote] = all_rates[quote]
                elif quote in by_quote and by_quote[quote].is_manual:
                    result[quote] = Decimal(by_quote[quote].rate)
            db.session.commit()
        return result

    @classmethod
    def get_rate(cls, base: str, quote: str, on_date: date | None = None, refresh=False) -> Decimal:
        base, quote = cls._valid_code(base), cls._valid_code(quote)
        if base == quote:
            return Decimal("1")
        return cls.get_rates(base, [quote], on_date=on_date, refresh=refresh)[quote]

    @classmethod
    def convert(cls, amount, source_currency: str, target_currency: str,
                on_date: date | None = None, refresh=False) -> Decimal:
        try:
            value = Decimal(str(amount if amount is not None else 0))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("Amount must be a valid number.") from exc
        if not value.is_finite():
            raise ValueError("Amount must be finite.")
        source = cls._valid_code(source_currency)
        target = cls._valid_code(target_currency)
        rate = cls.get_rate(source, target, on_date=on_date, refresh=refresh)
        quantum = Decimal("1").scaleb(-CURRENCIES[target]["decimals"])
        return (value * rate).quantize(quantum, rounding=ROUND_HALF_UP)

    @classmethod
    def convert_many(cls, items, target_currency: str):
        """Convert iterable records in batches grouped by source currency/date.

        Each item is a mapping with amount, source_currency and optional date.
        The result preserves input order and includes amount, rate and date.
        """
        target = cls._valid_code(target_currency)
        normalized = []
        groups = defaultdict(set)
        for index, item in enumerate(items or []):
            if index >= cls.MAX_BATCH_SIZE:
                raise ValueError(f"A single conversion batch cannot exceed {cls.MAX_BATCH_SIZE} items.")
            source = cls._valid_code(item.get("source_currency") or "NGN")
            effective_date = item.get("date")
            key_date = effective_date.isoformat() if effective_date else "latest"
            groups[(source, key_date, effective_date)].add(target)
            normalized.append((item, source, effective_date))

        rate_map = {}
        for (source, _key, effective_date), quotes in groups.items():
            rate_map[(source, _key)] = cls.get_rates(source, quotes, on_date=effective_date)

        converted = []
        quantum = Decimal("1").scaleb(-CURRENCIES[target]["decimals"])
        for item, source, effective_date in normalized:
            raw_amount = item.get("amount", 0)
            try:
                amount = Decimal(str(raw_amount if raw_amount is not None else 0))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise ValueError("Amount must be a valid number.") from exc
            if not amount.is_finite():
                raise ValueError("Amount must be finite.")
            key_date = effective_date.isoformat() if effective_date else "latest"
            rate = rate_map[(source, key_date)][target]
            converted.append({
                "original_amount": amount,
                "original_currency": source,
                "converted_amount": (amount * rate).quantize(quantum, rounding=ROUND_HALF_UP),
                "display_currency": target,
                "exchange_rate": rate,
                "rate_date": cls._effective_date(effective_date),
                "rate_source": "exchangerate-api-cache-or-provider",
            })
        return converted
