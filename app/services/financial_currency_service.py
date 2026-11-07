"""Currency-aware financial aggregation and conversion helpers.

Ledger amounts remain in their original currencies. Financial values
are converted only when calculating or presenting values in another
currency. Original transaction records are never rewritten.
"""

from decimal import Decimal

from app.extensions import db
from app.models.user import User
from app.services.exchange_rate_service import ExchangeRateService


class FinancialCurrencyService:

    @staticmethod
    def display_currency(user_id):
        """Return the user's selected display currency."""

        user = db.session.get(User, user_id)

        return (
            (user.currency if user else None) or "NGN"
        ).upper()

    @staticmethod
    def base_currency(user_id):
        """Return the user's accounting/base currency."""

        user = db.session.get(User, user_id)

        return (
            (
                getattr(user, "base_currency", None)
                if user else None
            ) or "NGN"
        ).upper()

    @staticmethod
    def convert_record(
        record,
        target_currency=None,
        amount_field="amount",
        date_field=None,
    ):
        """
        Convert one financial record into the target currency.

        The original amount and currency on the record remain
        unchanged. The record's transaction date is used for
        historical conversion when date_field is supplied.
        """

        target = (
            target_currency
            or FinancialCurrencyService.display_currency(
                record.user_id
            )
        ).upper()

        source = (
            getattr(record, "currency", None) or "NGN"
        ).upper()

        raw_amount = getattr(record, amount_field, None)

        amount = (
            Decimal(str(raw_amount))
            if raw_amount is not None
            else Decimal("0")
        )

        effective_date = (
            getattr(record, date_field, None)
            if date_field
            else None
        )

        return ExchangeRateService.convert(
            amount,
            source,
            target,
            on_date=effective_date,
        )

    @staticmethod
    def convert_records(
        records,
        target_currency=None,
        amount_field="amount",
        date_field=None,
    ):
        """
        Return conversion details for multiple records.

        Original source amounts and currencies are retained in
        the returned metadata.
        """

        records = list(records or [])

        if not records:
            return []

        target = (
            target_currency
            or FinancialCurrencyService.display_currency(
                records[0].user_id
            )
        ).upper()

        items = []

        for record in records:
            raw_amount = getattr(
                record,
                amount_field,
                None,
            )

            items.append({
                "amount": (
                    Decimal(str(raw_amount))
                    if raw_amount is not None
                    else Decimal("0")
                ),
                "source_currency": (
                    getattr(record, "currency", None)
                    or "NGN"
                ).upper(),
                "date": (
                    getattr(record, date_field, None)
                    if date_field
                    else None
                ),
            })

        batch_size = ExchangeRateService.MAX_BATCH_SIZE
        converted = []

        for offset in range(0, len(items), batch_size):
            batch = items[offset:offset + batch_size]

            converted.extend(
                ExchangeRateService.convert_many(
                    batch,
                    target,
                )
            )

        return converted

    @staticmethod
    def sum_records(
        records,
        target_currency=None,
        amount_field="amount",
        date_field=None,
        on_date=None,
    ):
        """
        Convert and sum financial records.

        Returns a float for compatibility with existing dashboard,
        report, and JSON consumers. All internal arithmetic uses
        Decimal.
        """

        records = list(records or [])

        if not records:
            return 0.0

        target = (
            target_currency
            or FinancialCurrencyService.display_currency(
                records[0].user_id
            )
        ).upper()

        items = []

        for record in records:
            raw_amount = getattr(
                record,
                amount_field,
                None,
            )

            effective_date = (
                on_date
                if on_date is not None
                else (
                    getattr(record, date_field, None)
                    if date_field
                    else None
                )
            )

            items.append({
                "amount": (
                    Decimal(str(raw_amount))
                    if raw_amount is not None
                    else Decimal("0")
                ),
                "source_currency": (
                    getattr(record, "currency", None)
                    or "NGN"
                ).upper(),
                "date": effective_date,
            })

        batch_size = ExchangeRateService.MAX_BATCH_SIZE
        total = Decimal("0")

        for offset in range(0, len(items), batch_size):
            batch = items[offset:offset + batch_size]

            converted = ExchangeRateService.convert_many(
                batch,
                target,
            )

            total += sum(
                (
                    Decimal(str(item["converted_amount"]))
                    for item in converted
                ),
                Decimal("0"),
            )

        return float(total)

    @staticmethod
    def convert_value(
        amount,
        source_currency,
        target_currency,
        on_date=None,
    ):
        """Convert a standalone amount between currencies."""

        value = (
            Decimal(str(amount))
            if amount is not None
            else Decimal("0")
        )

        converted = ExchangeRateService.convert(
            value,
            (source_currency or "NGN").upper(),
            (target_currency or "NGN").upper(),
            on_date=on_date,
        )

        return float(converted)

    @staticmethod
    def budget_spent(
        budget,
        include_classes=("expense", None),
        start_date=None,
        end_date=None,
    ):
        """
        Return eligible spending in the budget's own currency.

        The original expense amounts and currencies are preserved.
        """

        from app.models.expense import Expense

        query = Expense.query.filter(
            Expense.user_id == budget.user_id,
            Expense.category == budget.category,
            Expense.expense_date >= budget.start_date,
            Expense.expense_date <= budget.end_date,
            Expense.is_active.is_(True),
        )

        if include_classes is not None:
            from sqlalchemy import or_

            query = query.filter(
                or_(
                    *[
                        (
                            Expense.transaction_class == item
                            if item is not None
                            else Expense.transaction_class.is_(None)
                        )
                        for item in include_classes
                    ]
                )
            )

        if start_date is not None:
            query = query.filter(
                Expense.expense_date
                >= max(budget.start_date, start_date)
            )

        if end_date is not None:
            query = query.filter(
                Expense.expense_date
                <= min(budget.end_date, end_date)
            )

        rows = query.all()

        return FinancialCurrencyService.sum_records(
            rows,
            budget.currency or "NGN",
            date_field="expense_date",
        )

    @staticmethod
    def ai_currency_provenance(
        user_id,
        start=None,
        end=None,
    ):
        """Return machine-readable currency assumptions for AI."""

        display = FinancialCurrencyService.display_currency(
            user_id
        )

        return {
            "display_currency": display,
            "base_currency": (
                FinancialCurrencyService.base_currency(
                    user_id
                )
            ),
            "ledger_policy": (
                "Original transaction amounts and currencies "
                "are immutable; display conversion does not "
                "rewrite ledger records."
            ),
            "flow_conversion_policy": (
                "Period income and expense records are converted "
                "individually using their transaction dates before "
                "aggregation, where transaction-level conversion "
                "is available."
            ),
            "valuation_conversion_policy": (
                "Current balances and current asset valuations "
                "use the latest available valuation-date rate."
            ),
            "budget_policy": (
                "Budget spending is first reconciled in the "
                "budget currency; budget values are then translated "
                "into the display currency for cross-budget comparisons."
            ),
            "historical_policy": (
                "Historical report values must use the applicable "
                "historical rate; missing rates must be reported "
                "as unavailable rather than estimated silently."
            ),
            "requested_period": {
                "start": (
                    start.isoformat()
                    if start else None
                ),
                "end": (
                    end.isoformat()
                    if end else None
                ),
            },
            "rounding": (
                "Amounts are rounded using the target currency's "
                "configured minor-unit precision and ROUND_HALF_UP."
            ),
            "source_of_truth": (
                "DashboardService and FinancialCurrencyService; "
                "the AI must explain supplied values and must not "
                "independently recalculate currency conversions."
            ),
        }