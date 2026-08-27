from datetime import date, datetime
from sqlalchemy import func, extract, or_

from app.extensions import db
from app.models.income import Income
from app.models.expense import Expense
from app.models.budget import Budget
from app.models.goal import Goal


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
            return value.date()

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

        income_total = sum(float(x.amount or 0) for x in incomes)
        expense_total = sum(float(x.amount or 0) for x in expenses)
        savings = income_total - expense_total
        savings_rate = (savings / income_total * 100) if income_total else 0

        return {
            "income": income_total,
            "expenses": expense_total,
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
        }

    @staticmethod
    def income_by_category(user_id, start_date=None, end_date=None, category=None):
        q = db.session.query(Income.category, func.sum(Income.amount))
        q = ReportService._filters(q, Income, user_id, ReportService._date(start_date), ReportService._date(end_date), category, Income.received_date)
        rows = q.group_by(Income.category).order_by(func.sum(Income.amount).desc()).all()
        return {"labels": [r[0] or "Uncategorized" for r in rows], "values": [float(r[1] or 0) for r in rows]}

    @staticmethod
    def expense_by_category(user_id, start_date=None, end_date=None, category=None):
        q = db.session.query(Expense.category, func.sum(Expense.amount))
        q = ReportService._filters(q, Expense, user_id, ReportService._date(start_date), ReportService._date(end_date), category, Expense.expense_date)
        rows = q.group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).all()
        return {"labels": [r[0] or "Uncategorized" for r in rows], "values": [float(r[1] or 0) for r in rows]}

    @staticmethod
    def monthly_trend(user_id, start_date=None, end_date=None, category=None):
        # Use a calendar-year/month aggregation, then fill missing months with zero.
        # This avoids the old implementation's problem of mixing different years.
        start = ReportService._date(start_date)
        end = ReportService._date(end_date)
        if not start and not end:
            today = date.today()
            start = date(today.year, 1, 1)
            end = date(today.year, 12, 31)
        elif start and not end:
            end = date(start.year, 12, 31)
        elif end and not start:
            start = date(end.year, 1, 1)

        if start.year != end.year:
            # For multi-year reports, use month labels with year and aggregate chronologically.
            income_rows = db.session.query(
                extract("year", Income.received_date), extract("month", Income.received_date), func.sum(Income.amount)
            ).filter(Income.user_id == user_id, Income.received_date >= start, Income.received_date <= end)
            expense_rows = db.session.query(
                extract("year", Expense.expense_date), extract("month", Expense.expense_date), func.sum(Expense.amount)
            ).filter(Expense.user_id == user_id, Expense.expense_date >= start, Expense.expense_date <= end)
            if category:
                income_rows = income_rows.filter(Income.category == category)
                expense_rows = expense_rows.filter(Expense.category == category)
            income_rows = income_rows.group_by(extract("year", Income.received_date), extract("month", Income.received_date)).all()
            expense_rows = expense_rows.group_by(extract("year", Expense.expense_date), extract("month", Expense.expense_date)).all()
            keys = sorted({(int(y), int(m)) for y, m, _ in income_rows} | {(int(y), int(m)) for y, m, _ in expense_rows})
            imap = {(int(y), int(m)): float(v or 0) for y, m, v in income_rows}
            emap = {(int(y), int(m)): float(v or 0) for y, m, v in expense_rows}
            return {
                "labels": [date(y, m, 1).strftime("%b %Y") for y, m in keys],
                "income": [imap.get(k, 0) for k in keys],
                "expenses": [emap.get(k, 0) for k in keys],
            }

        year = start.year
        income_rows = db.session.query(extract("month", Income.received_date), func.sum(Income.amount)).filter(
            Income.user_id == user_id, Income.received_date >= start, Income.received_date <= end
        )
        expense_rows = db.session.query(extract("month", Expense.expense_date), func.sum(Expense.amount)).filter(
            Expense.user_id == user_id, Expense.expense_date >= start, Expense.expense_date <= end
        )
        if category:
            income_rows = income_rows.filter(Income.category == category)
            expense_rows = expense_rows.filter(Expense.category == category)
        income_rows = income_rows.group_by(extract("month", Income.received_date)).all()
        expense_rows = expense_rows.group_by(extract("month", Expense.expense_date)).all()
        income_map = {int(m): float(v or 0) for m, v in income_rows}
        expense_map = {int(m): float(v or 0) for m, v in expense_rows}
        labels = [date(year, m, 1).strftime("%b") for m in range(1, 13)]
        return {"labels": labels, "income": [income_map.get(m, 0) for m in range(1, 13)], "expenses": [expense_map.get(m, 0) for m in range(1, 13)]}

    @staticmethod
    def get_summary(user_id, start_date=None, end_date=None, category=None):
        return ReportService.dashboard(user_id, start_date, end_date, category)

    @staticmethod
    def report_data(user_id, start_date=None, end_date=None, category=None):
        summary = ReportService.dashboard(user_id, start_date, end_date, category)
        return {
            "summary": summary,
            "income_categories": ReportService.income_by_category(user_id, start_date, end_date, category),
            "expense_categories": ReportService.expense_by_category(user_id, start_date, end_date, category),
            "monthly_trend": ReportService.monthly_trend(user_id, start_date, end_date, category),
        }
