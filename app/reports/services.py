from datetime import date, datetime
from app.utils.timezone import today
from sqlalchemy import func, extract, or_

from app.extensions import db
from app.models.income import Income
from app.models.expense import Expense
from app.models.budget import Budget
from app.models.goal import Goal
from app.models.investment_event import InvestmentEvent
from app.models.asset import Asset
from app.services.dashboard_service import DashboardService
from app.services.financial_currency_service import FinancialCurrencyService
from decimal import Decimal

class ReportService:
    """All report calculations live here so the UI, PDF and Excel exports
    use the same filtered dataset and produce consistent figures.
    """

    @staticmethod
    def _date(value):
        """
        Normalize supported date inputs to datetime.date.
        """

        if value is None or value == "":
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, date):
            return value

        if isinstance(value, str):
            return datetime.strptime(
                value.strip(),
                "%Y-%m-%d"
            ).date()

        raise TypeError(
            f"Unsupported date value: {type(value).__name__}"
        )

    @staticmethod
    def _filters(
        query,
        model,
        user_id,
        start_date=None,
        end_date=None,
        category=None,
        date_field=None,
    ):
        """
        Apply common report filters.

        Every query is scoped to the authenticated user before
        any additional filters are applied.
        """

        query = query.filter(model.user_id == user_id)

        if date_field is not None:

            if start_date:
                query = query.filter(date_field >= start_date)

            if end_date:
                query = query.filter(date_field <= end_date)

        if category:
            query = query.filter(model.category == category)

        return query

    @staticmethod
    def categories(user_id):
        income_categories = {
            row[0] for row in db.session.query(Income.category)
            .filter(Income.user_id == user_id, Income.category.isnot(None))
            .distinct().all()
            if row[0]
        }
        expense_categories = {
            row[0] for row in db.session.query(Expense.category)
            .filter(Expense.user_id == user_id, Expense.category.isnot(None))
            .distinct().all()
            if row[0]
        }
        return sorted(income_categories | expense_categories, key=str.lower)

    @staticmethod
    def _income_query(user_id, start_date=None, end_date=None, category=None):
        start_date = ReportService._date(start_date)
        end_date = ReportService._date(end_date)
        query = Income.query.filter(Income.user_id == user_id)
        if start_date:
            query = query.filter(Income.received_date >= start_date)
        if end_date:
            query = query.filter(Income.received_date <= end_date)
        if category:
            query = query.filter(Income.category == category)
        return query

    @staticmethod
    def _expense_query(user_id, start_date=None, end_date=None, category=None):
        start_date = ReportService._date(start_date)
        end_date = ReportService._date(end_date)
        query = Expense.query.filter(Expense.user_id == user_id)
        if start_date:
            query = query.filter(Expense.expense_date >= start_date)
        if end_date:
            query = query.filter(Expense.expense_date <= end_date)
        if category:
            query = query.filter(Expense.category == category)
        return query

    @staticmethod
    def dashboard(user_id, start_date=None, end_date=None, category=None):
        incomes = ReportService._income_query(user_id, start_date, end_date, category).order_by(
            Income.received_date.desc(), Income.id.desc()
        ).all()
        expenses = ReportService._expense_query(user_id, start_date, end_date, category).order_by(
            Expense.expense_date.desc(), Expense.id.desc()
        ).all()

        display_currency = FinancialCurrencyService.display_currency(user_id)
        income_total = FinancialCurrencyService.sum_records(
            incomes, display_currency, date_field="received_date"
        )
        expense_total = FinancialCurrencyService.sum_records(
            expenses, display_currency, date_field="expense_date"
        )
        operating_expense_total = FinancialCurrencyService.sum_records(
            [x for x in expenses if x.transaction_class in (None, "expense")],
            display_currency, date_field="expense_date"
        )
        savings = income_total - expense_total
        savings_rate = (savings / income_total * 100) if income_total else 0

        # ------------------------------------------------------
        # Recent Transactions
        # ------------------------------------------------------
        # Income and expenses are fetched separately for the report
        # calculations above.  Recent Transactions must, however, be
        # presented as ONE chronological stream.  Otherwise the template
        # can consume the five income slots before it ever reaches an
        # investment-funding expense.
        #
        # Investment funding is a real Expense (transaction_class="investment")
        # and therefore belongs in this stream.  Non-cash investment
        # valuation events are not Income/Expense records and are not added.
        recent_transactions = []

        for item in incomes:
            recent_transactions.append({
                "id": item.id,
                "date": item.received_date,
                "type": "Income",
                "category": item.category,
                "description": item.source,
                "amount": FinancialCurrencyService.convert_record(
                    item, display_currency, date_field="received_date"
                ),
                "currency": display_currency,
                "original_amount": float(item.amount or 0),
                "original_currency": item.currency or "NGN",
            })

        for item in expenses:
            recent_transactions.append({
                "id": item.id,
                "date": item.expense_date,
                "type": "Expense",
                "category": item.category,
                "description": item.merchant,
                "amount": FinancialCurrencyService.convert_record(
                    item, display_currency, date_field="expense_date"
                ),
                "currency": display_currency,
                "original_amount": float(item.amount or 0),
                "original_currency": item.currency or "NGN",
            })

        recent_transactions.sort(
            key=lambda row: (row["date"], row["id"]),
            reverse=True,
        )

        # Financial-position components that are intentionally kept separate
        # from ordinary operating income/expense totals.
        investment_funding_rows = Expense.query.filter(
            Expense.user_id == user_id, Expense.transaction_class == "investment",
            Expense.expense_date >= ReportService._date(start_date) if ReportService._date(start_date) else True,
            Expense.expense_date <= ReportService._date(end_date) if ReportService._date(end_date) else True,
        ).all()
        investment_funding = FinancialCurrencyService.sum_records(
            investment_funding_rows, display_currency, date_field="expense_date"
        )
        goal_contribution_rows = Expense.query.filter(
            Expense.user_id == user_id, Expense.transaction_class == "goal_contribution",
            Expense.expense_date >= ReportService._date(start_date) if ReportService._date(start_date) else True,
            Expense.expense_date <= ReportService._date(end_date) if ReportService._date(end_date) else True,
        ).all()
        goal_contributions = FinancialCurrencyService.sum_records(
            goal_contribution_rows, display_currency, date_field="expense_date"
        )
        # Valuation gains/losses are investment-value changes, not
        # Income/Expense transactions. Keep them available as investment
        # reporting metrics, sourced from the investment event ledger.
        valuation_query = InvestmentEvent.query.filter(
            InvestmentEvent.user_id == user_id,
            InvestmentEvent.event_type == "valuation",
        )
        valuation_start = ReportService._date(start_date)
        valuation_end = ReportService._date(end_date)
        if valuation_start:
            valuation_query = valuation_query.filter(
                InvestmentEvent.event_date >= valuation_start
            )
        if valuation_end:
            valuation_query = valuation_query.filter(
                InvestmentEvent.event_date <= valuation_end
            )

        valuation_events = valuation_query.all()
        investment_gains = sum(
            FinancialCurrencyService.convert_record(
                x, display_currency, amount_field="realized_gain_loss", date_field="event_date"
            )
            for x in valuation_events
            if float(x.realized_gain_loss or 0) > 0
        )
        investment_losses = sum(
            abs(FinancialCurrencyService.convert_record(
                x, display_currency, amount_field="realized_gain_loss", date_field="event_date"
            ))
            for x in valuation_events
            if float(x.realized_gain_loss or 0) < 0
        )
        liquidation_rows = Income.query.filter(
            Income.user_id == user_id, Income.transaction_class == "investment_liquidation",
            Income.received_date >= ReportService._date(start_date) if ReportService._date(start_date) else True,
            Income.received_date <= ReportService._date(end_date) if ReportService._date(end_date) else True,
        ).all()
        liquidation_proceeds = FinancialCurrencyService.sum_records(
            liquidation_rows, display_currency, date_field="received_date"
        )
        active_investments = Asset.query.filter_by(user_id=user_id, is_active=True).filter(Asset.asset_type.ilike("investment")).all()
        investment_cost_basis = sum(FinancialCurrencyService.convert_value(
            a.cost_basis if a.cost_basis is not None else a.acquisition_cost or 0,
            a.currency, display_currency, on_date=today()
        ) for a in active_investments)
        investment_current_value = sum(FinancialCurrencyService.convert_value(
            a.current_value or 0, a.currency, display_currency, on_date=today()
        ) for a in active_investments)

        return {
            "income": income_total,
            "expenses": expense_total,
            "operating_expenses": operating_expense_total,
            "cash_outflows": expense_total,
            "savings": savings,
            "savings_rate": savings_rate,
            "savings_progress": max(
                0.0,
                min(100.0, savings_rate)
            ),
            "transactions": len(incomes) + len(expenses),
            "income_transactions": len(incomes),
            "expense_transactions": len(expenses),
            "budgets": Budget.query.filter_by(user_id=user_id).all(),
            "goals": Goal.query.filter_by(user_id=user_id).all(),
            "income_records": incomes,
            "expense_records": expenses,
            "recent_transactions": recent_transactions,
            "goal_contributions": goal_contributions,
            "investment_funding": investment_funding,
            "investment_losses": investment_losses,
            "investment_gains": investment_gains,
            "liquidation_proceeds": liquidation_proceeds,
            "investment_cost_basis": investment_cost_basis,
            "investment_current_value": investment_current_value,
            "investment_gain_loss": investment_current_value - investment_cost_basis,
        }

    @staticmethod
    def income_by_category(
        user_id,
        start_date=None,
        end_date=None,
        category=None,
    ):
        rows = ReportService._income_query(
            user_id,
            start_date,
            end_date,
            category,
        ).all()

        target = FinancialCurrencyService.display_currency(
            user_id
        )

        totals = {}

        for row in rows:
            key = row.category or "Uncategorized"

            converted_amount = FinancialCurrencyService.convert_record(
                row,
                target,
                date_field="received_date",
            )

            totals[key] = (
                totals.get(key, Decimal("0"))
                + converted_amount
            )

        ordered = sorted(
            totals.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        return {
            "labels": [
                item[0]
                for item in ordered
            ],
            "values": [
                round(float(item[1]), 2)
                for item in ordered
            ],
        }

    @staticmethod
    def expense_by_category(
        user_id,
        start_date=None,
        end_date=None,
        category=None,
    ):
        rows = ReportService._expense_query(
            user_id,
            start_date,
            end_date,
            category,
        ).all()

        target = FinancialCurrencyService.display_currency(
            user_id
        )

        totals = {}

        for row in rows:
            key = row.category or "Uncategorized"

            converted_amount = FinancialCurrencyService.convert_record(
                row,
                target,
                date_field="expense_date",
            )

            totals[key] = (
                totals.get(key, Decimal("0"))
                + converted_amount
            )

        ordered = sorted(
            totals.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        return {
            "labels": [
                item[0]
                for item in ordered
            ],
            "values": [
                round(float(item[1]), 2)
                for item in ordered
            ],
        }

    @staticmethod
    def monthly_trend(
        user_id,
        start_date=None,
        end_date=None,
        category=None,
    ):
        start = ReportService._date(start_date)
        end = ReportService._date(end_date)

        if not start and not end:
            today_date = today()

            start = date(
                today_date.year,
                1,
                1,
            )

            end = date(
                today_date.year,
                12,
                31,
            )

        elif start and not end:
            end = date(
                start.year,
                12,
                31,
            )

        elif end and not start:
            start = date(
                end.year,
                1,
                1,
            )

        target = FinancialCurrencyService.display_currency(
            user_id
        )

        income_rows = ReportService._income_query(
            user_id,
            start,
            end,
            category,
        ).all()

        expense_rows = ReportService._expense_query(
            user_id,
            start,
            end,
            category,
        ).all()

        # Decimal accumulators prevent float/Decimal errors.
        income_map = {}
        expense_map = {}

        # ------------------------------------------------------
        # Monthly income aggregation.
        # ------------------------------------------------------

        for row in income_rows:
            if not row.received_date:
                continue

            key = (
                row.received_date.year,
                row.received_date.month,
            )

            converted_amount = FinancialCurrencyService.convert_record(
                row,
                target,
                date_field="received_date",
            )

            income_map[key] = (
                income_map.get(key, Decimal("0"))
                + converted_amount
            )

        # ------------------------------------------------------
        # Monthly expense aggregation.
        # ------------------------------------------------------

        for row in expense_rows:
            if not row.expense_date:
                continue

            key = (
                row.expense_date.year,
                row.expense_date.month,
            )

            converted_amount = FinancialCurrencyService.convert_record(
                row,
                target,
                date_field="expense_date",
            )

            expense_map[key] = (
                expense_map.get(key, Decimal("0"))
                + converted_amount
            )

        # ------------------------------------------------------
        # Generate continuous month labels.
        # ------------------------------------------------------

        cursor = date(
            start.year,
            start.month,
            1,
        )

        keys = []

        while cursor <= end:
            keys.append(
                (
                    cursor.year,
                    cursor.month,
                )
            )

            if cursor.month == 12:
                cursor = date(
                    cursor.year + 1,
                    1,
                    1,
                )
            else:
                cursor = date(
                    cursor.year,
                    cursor.month + 1,
                    1,
                )

        # ------------------------------------------------------
        # Return chart-compatible values.
        # ------------------------------------------------------

        return {
            "labels": [
                date(year, month, 1).strftime(
                    "%b %Y"
                    if start.year != end.year
                    else "%b"
                )
                for year, month in keys
            ],

            "income": [
                round(
                    float(
                        income_map.get(
                            key,
                            Decimal("0"),
                        )
                    ),
                    2,
                )
                for key in keys
            ],

            "expenses": [
                round(
                    float(
                        expense_map.get(
                            key,
                            Decimal("0"),
                        )
                    ),
                    2,
                )
                for key in keys
            ],
        }

    @staticmethod
    def get_summary(user_id, start_date=None, end_date=None, category=None):
        return ReportService.dashboard(user_id, start_date, end_date, category)

    @staticmethod
    def report_data(user_id, start_date=None, end_date=None, category=None):
        summary = ReportService.dashboard(user_id, start_date, end_date, category)

        # DashboardService is the authoritative source for current cash, goal
        # allocations, investment carrying values and the resulting net worth.
        # Keeping this object separate from period-performance data prevents a
        # date/category filter from accidentally changing the user's current
        # financial position or introducing a second source of truth.
        financial_position = DashboardService.financial_position_summary(user_id)

        return {
            "display_currency": FinancialCurrencyService.display_currency(user_id),
            "summary": summary,
            "financial_position": financial_position,
            "income_categories": ReportService.income_by_category(user_id, start_date, end_date, category),
            "expense_categories": ReportService.expense_by_category(user_id, start_date, end_date, category),
            "monthly_trend": ReportService.monthly_trend(user_id, start_date, end_date, category),
        }