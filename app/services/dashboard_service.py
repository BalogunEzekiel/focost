####################################################################################################
# FILE: app/services/dashboard_service.py
####################################################################################################

from datetime import date, datetime, timedelta

from sqlalchemy import func, extract, or_
import calendar
from flask import request
import re

from app.extensions import db
from app.models.income import Income
from app.models.expense import Expense
from app.models.budget import Budget
from app.models.goal import Goal
from app.models.goal_contribution import GoalContribution
from app.models.investment_event import InvestmentEvent
from app.services.notification_service import NotificationService
from app.utils.timezone import now, today

class DashboardService:

    @staticmethod
    def ai_calculation_context(
        user_id,
        start=None,
        end=None,
    ):
        """
        Authoritative explanation layer for FOCOST AI.

        This does not introduce new financial logic.

        It exposes the existing DashboardService calculations,
        definitions and relationships in a machine-readable form
        so that FOCOST AI can explain exactly how dashboard figures
        were produced.
        """

        if start is None:
            start = date.today().replace(day=1)

        if end is None:
            end = date.today()

        # ------------------------------------------------------
        # Authoritative cash-flow totals
        # ------------------------------------------------------

        totals = DashboardService._cash_flow_totals(
            user_id=user_id,
            start_date=start,
            end_date=end,
        )

        income = totals["income"]
        expenses = totals["expenses"]
        savings = totals["savings"]

        savings_rate = (
            (savings / income) * 100
            if income
            else 0
        )

        # ------------------------------------------------------
        # Operating expenses
        #
        # Operating expenses are intentionally separate from
        # total cash expenses.
        #
        # Total expenses include:
        # - ordinary expenses
        # - investment funding
        # - goal contributions
        #
        # Operating expenses include only:
        # - transaction_class = "expense"
        # - legacy/null transaction_class
        # ------------------------------------------------------

        operating_expenses = float(
            DashboardService
            ._active_operating_expense_query(user_id)
            .filter(
                Expense.expense_date.between(
                    start,
                    end,
                ),
            )
            .with_entities(
                func.coalesce(
                    func.sum(Expense.amount),
                    0,
                )
            )
            .scalar()
            or 0
        )

        # ------------------------------------------------------
        # Lifetime available balance
        # ------------------------------------------------------

        balance_context = (
            DashboardService.ai_balance_context(user_id)
        )

        # ------------------------------------------------------
        # Month-end forecast
        # ------------------------------------------------------

        month_end = (
            DashboardService.month_end_forecast(user_id)
        )

        # ------------------------------------------------------
        # Recent monthly history
        # ------------------------------------------------------

        monthly_history = (
            DashboardService.monthly_series(
                user_id,
                months=12,
            )
        )

        return {
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },

            "facts": {
                "income": round(income, 2),
                "total_expenses": round(expenses, 2),
                "operating_expenses": round(
                    operating_expenses,
                    2,
                ),
                "non_operating_expenses": round(
                    expenses - operating_expenses,
                    2,
                ),
                "savings": round(savings, 2),
                "savings_rate_percent": round(
                    savings_rate,
                    2,
                ),
            },

            "formulas": {
                "monthly_savings": (
                    "income - total_expenses"
                ),
                "savings_rate": (
                    "(savings / income) * 100 "
                    "when income > 0"
                ),
                "available_balance": (
                    "cumulative monthly savings "
                    "through the current date"
                ),
                "monthly_expense": (
                    "sum of all active Expense.amount "
                    "records in the current month"
                ),
            },

            "accounting_rules": {
                "investment_funding": (
                    "expense"
                ),
                "goal_contribution": (
                    "expense"
                ),
                "investment_liquidation": (
                    "income"
                ),
                "investment_valuation": (
                    "non-cash investment value adjustment; never an "
                    "Income or Expense transaction"
                ),
                "valuation_reversal": (
                    "original valuation transaction "
                    "and linked accounting entry are "
                    "permanently removed"
                ),
            },

            "balance": balance_context,

            "month_end_forecast": month_end,

            "forecast_formula": {
                "method": "current_month_run_rate",
                "projected_income": (
                    "current_month_income / elapsed_days "
                    "* days_in_month"
                ),
                "projected_expenses": (
                    "current_month_expenses / elapsed_days "
                    "* days_in_month"
                ),
                "projected_savings": (
                    "projected_income - projected_expenses"
                ),
                "guarantee": False,
            },

            "monthly_history": monthly_history,
        }

    # ==========================================================
    # AUTHORITATIVE FINANCIAL QUERY SOURCES
    # ==========================================================

    @staticmethod
    def _active_income_query(user_id):
        """
        Authoritative source for active cash income.

        Only active Income records are included.

        Investment valuation/revaluation is never represented in
        Income and therefore cannot enter cash-flow calculations
        through this query.
        """
        return Income.query.filter(
            Income.user_id == user_id,
            Income.is_active.is_(True),
        )

    @staticmethod
    def _active_expense_query(user_id):
        """
        Authoritative source for all active cash expenses.

        This includes:
        - ordinary expenses
        - investment funding
        - goal contributions

        Investment valuation/revaluation is not represented in
        Expense and therefore cannot enter cash flow through this
        query.
        """
        return Expense.query.filter(
            Expense.user_id == user_id,
            Expense.is_active.is_(True),
        )

    @staticmethod
    def _active_operating_expense_query(user_id):
        """
        Authoritative source for operating expenses only.

        Operating expense means:
            transaction_class == 'expense'
            OR transaction_class IS NULL

        Investment funding and goal contributions intentionally
        remain excluded from operating-expense analytics.

        This must NOT be used for total cash-flow calculations.
        """
        return DashboardService._active_expense_query(
            user_id
        ).filter(
            or_(
                Expense.transaction_class == "expense",
                Expense.transaction_class.is_(None),
            )
        )

    @staticmethod
    def _cash_flow_totals(
        user_id,
        exclude_expense_id=None,
        as_of=None,
        start_date=None,
        end_date=None,
    ):
        """
        Authoritative cash-flow calculation.

        Cash income:
            all active Income records.

        Cash expenses:
            all active Expense records.

        Therefore:

            savings = income - expenses

        Investment funding and goal contributions are real cash
        outflows and remain included.

        Investment valuation/revaluation gains and losses are
        non-cash and are never represented in Income or Expense,
        so they cannot enter this calculation.

        Optional date parameters allow callers to request either:
            - a specific reporting period via start_date/end_date, or
            - a historical cumulative balance via as_of.

        This method is the single source of truth for cash-flow totals.
        """

        income_query = DashboardService._active_income_query(
            user_id
        )

        expense_query = DashboardService._active_expense_query(
            user_id
        )

        # ----------------------------------------------------------
        # Reporting-period filters
        # ----------------------------------------------------------

        if start_date is not None:
            income_query = income_query.filter(
                Income.received_date >= start_date
            )

            expense_query = expense_query.filter(
                Expense.expense_date >= start_date
            )

        if end_date is not None:
            income_query = income_query.filter(
                Income.received_date <= end_date
            )

            expense_query = expense_query.filter(
                Expense.expense_date <= end_date
            )

        # ----------------------------------------------------------
        # Historical "as of" cutoff
        #
        # This is cumulative up to the supplied date.
        # ----------------------------------------------------------

        if as_of is not None:
            income_query = income_query.filter(
                Income.received_date <= as_of
            )

            expense_query = expense_query.filter(
                Expense.expense_date <= as_of
            )

        # ----------------------------------------------------------
        # Optional expense exclusion
        #
        # Used when validating whether a new/edited expense can
        # be afforded without counting that same expense twice.
        # ----------------------------------------------------------

        if exclude_expense_id is not None:
            expense_query = expense_query.filter(
                Expense.id != exclude_expense_id
            )

        # ----------------------------------------------------------
        # Aggregate income
        # ----------------------------------------------------------

        income = float(
            income_query.with_entities(
                func.coalesce(
                    func.sum(Income.amount),
                    0,
                )
            ).scalar()
            or 0
        )

        # ----------------------------------------------------------
        # Aggregate expenses
        # ----------------------------------------------------------

        expenses = float(
            expense_query.with_entities(
                func.coalesce(
                    func.sum(Expense.amount),
                    0,
                )
            ).scalar()
            or 0
        )

        # ----------------------------------------------------------
        # Authoritative savings
        # ----------------------------------------------------------

        savings = income - expenses

        return {
            "income": round(income, 2),
            "expenses": round(expenses, 2),
            "savings": round(savings, 2),
        }

    @staticmethod
    def _operating_expense_filter(query):
        """
        Restrict an Expense query to operating expenses.

        This is intentionally different from total cash expenses.
        """
        return query.filter(
            or_(
                Expense.transaction_class == "expense",
                Expense.transaction_class.is_(None),
            )
        )


    """

    Central Intelligent Dashboard Service

    This service builds every section of the dashboard.

    All dashboard templates should obtain their data

    exclusively through this service.

    """

    @staticmethod
    def _monthly_savings_rows(
        user_id,
        start_date=None,
        end_date=None,
        exclude_expense_id=None,
    ):
        """
        Authoritative monthly cash-savings ledger.

        Every month's savings is:

            all active income
            - all active expenses

        Investment funding and goal contributions remain expenses.

        Investment valuation/revaluation is excluded because it is
        not stored in Income or Expense.
        """

        if end_date is None:
            end_date = today()

        if start_date is None:
            first_income = (
                DashboardService._active_income_query(user_id)
                .order_by(Income.received_date.asc())
                .first()
            )

            first_expense = (
                DashboardService._active_expense_query(user_id)
                .order_by(Expense.expense_date.asc())
                .first()
            )

            dates = [
                value
                for value in (
                    getattr(
                        first_income,
                        "received_date",
                        None,
                    ),
                    getattr(
                        first_expense,
                        "expense_date",
                        None,
                    ),
                )
                if value is not None
            ]

            start_date = (
                min(dates)
                if dates
                else end_date
            )

        first_month = start_date.replace(day=1)
        current_month = end_date.replace(day=1)

        rows = []

        cursor = first_month

        while cursor <= current_month:
            month_start = cursor
            month_end = cursor.replace(
                day=calendar.monthrange(
                    cursor.year,
                    cursor.month,
                )[1]
            )

            period_end = min(
                month_end,
                end_date,
            )

            totals = DashboardService._cash_flow_totals(
                user_id=user_id,
                exclude_expense_id=exclude_expense_id,
                start_date=month_start,
                end_date=period_end,
            )

            rows.append(
                {
                    "month": month_start.isoformat(),
                    "income": totals["income"],
                    "expenses": totals["expenses"],
                    "savings": totals["savings"],
                }
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

        return rows

    @staticmethod
    def available_balance(
        user_id,
        exclude_expense_id=None,
        as_of=None,
    ):
        """
        Authoritative cumulative available cash balance.

        Defined as:

            cumulative active income
            - cumulative active cash expenses

        Investment funding and goal contributions remain cash
        expenses.

        Investment valuation/revaluation remains completely outside
        this calculation.

        `as_of` allows callers to determine the balance available at
        a historical transaction date.
        """

        totals = DashboardService._cash_flow_totals(
            user_id=user_id,
            exclude_expense_id=exclude_expense_id,
            as_of=as_of,
        )

        return totals["savings"]

    @staticmethod
    def investment_summary(user_id):
        from app.models.asset import Asset
        assets = Asset.query.filter_by(user_id=user_id, is_active=True).filter(Asset.asset_type.ilike("investment")).all()
        cost = sum(float(a.cost_basis if a.cost_basis is not None else a.acquisition_cost or 0) for a in assets)
        value = sum(float(a.current_value or 0) for a in assets)
        return {
            "count": len(assets),
            "cost_basis": cost,
            "current_value": value,
            "gain_loss": value - cost,
            "assets": assets,
        }

    @staticmethod
    def financial_position_summary(user_id):
        """
        Authoritative current financial-position summary used by reporting.

        The available balance is the spendable cash balance after recorded cash
        inflows and outflows. Goal contributions and investment holdings are
        separate stores of value that have already reduced available cash, so
        they are added back once when deriving total net worth. Investment
        valuation gains/losses remain non-cash until liquidation and therefore
        affect the investment carrying value rather than available cash.
        """
        investment_summary = DashboardService.investment_summary(user_id)
        goal_contributions = (
            db.session.query(func.coalesce(func.sum(GoalContribution.amount), 0))
            .filter(
                GoalContribution.user_id == user_id,
                GoalContribution.is_active == True,
            )
            .scalar()
            or 0
        )

        cash_flow = DashboardService._cash_flow_totals(user_id)

        cash_income = cash_flow["income"]
        cash_expenses = cash_flow["expenses"]
        available_balance = DashboardService.available_balance(user_id)
        goal_contributions = float(goal_contributions)
        investment_current_value = float(investment_summary["current_value"] or 0)
        net_worth = available_balance + goal_contributions + investment_current_value

        return {
            "cash_income": float(cash_income),
            "cash_expenses": float(cash_expenses),
            "available_balance": float(available_balance),
            "goal_contributions": goal_contributions,
            "investment_current_value": investment_current_value,
            "investment_cost_basis": float(investment_summary["cost_basis"] or 0),
            "investment_gain_loss": float(investment_summary["gain_loss"] or 0),
            "investment_count": investment_summary["count"],
            "net_worth": float(net_worth),
        }

    # ==========================================================
    # DATE FILTER
    # ==========================================================

    @staticmethod
    def get_period_dates(period="month"):
        today = date.today()

        if period == "month":
            start = date(today.year, today.month, 1)
            end = date(
                today.year,
                today.month,
                calendar.monthrange(today.year, today.month)[1]
            )

        elif period == "year":
            start = date(today.year, 1, 1)
            end = date(today.year, 12, 31)

        else:
            start = date(2000,1,1)
            end = today

        return start, end

    # ==========================================================
    # MAIN DASHBOARD
    # ==========================================================

    @staticmethod
    def get_dashboard_data(
        user_id,
        period="month",
        transaction_type=None,
        category=None,
        search=None
    ):

        # -------------------------------------------------------
        # SUMMARY
        # -------------------------------------------------------

        summary = DashboardService.build_summary(user_id)

        # -------------------------------------------------------
        # KPI CARDS
        # -------------------------------------------------------

        kpis = DashboardService.build_kpis(user_id)

        # -------------------------------------------------------
        # MONTH-END FORECAST
        # -------------------------------------------------------


        # -------------------------------------------------------
        # FORECAST
        # -------------------------------------------------------


        # -------------------------------------------------------
        # AI SUMMARY
        # -------------------------------------------------------

        ai_summary = DashboardService.build_ai_summary(user_id)

        # -------------------------------------------------------
        # SMART INSIGHTS
        # -------------------------------------------------------

        insights = DashboardService.build_insights(user_id)

        # -------------------------------------------------------
        # SAVINGS OPPORTUNITY
        # -------------------------------------------------------

        ai_financial_insight = DashboardService.build_ai_financial_insight(user_id)

        # -------------------------------------------------------
        # BUDGET WARNING
        # -------------------------------------------------------

        budget_warnings = DashboardService.build_budget_warning(user_id)

        active_budgets = len(budget_warnings)

        if budget_warnings:

            highest = budget_warnings[0]

            budget_risk = highest["risk"]

            budget_warning = (
                f'{highest["category"]}: '
                f'{highest["percentage"]:.0f}% used'
            )

        else:

            budget_risk = "Low"

            budget_warning = "All budgets are healthy."

        # -------------------------------------------------------
        # GOALS
        # -------------------------------------------------------

        goal_progress = DashboardService.build_goal_progress(user_id)

        # -------------------------------------------------------
        # FINANCIAL HEALTH
        # -------------------------------------------------------

        financial_health = DashboardService.build_financial_health(user_id)

        health_score = financial_health["score"]
        health_message = financial_health["message"]
        health_income = financial_health["income"]
        health_expenses = financial_health["expenses"]
        health_savings = financial_health["savings"]

        # -------------------------------------------------------
        # AI RECOMMENDATIONS
        # -------------------------------------------------------

        recommendations = DashboardService.build_recommendations(user_id)

        # -------------------------------------------------------
        # DAILY BRIEF
        # -------------------------------------------------------

        daily_brief = DashboardService.build_daily_brief(user_id)

        # -------------------------------------------------------
        # NOTIFICATIONS
        # -------------------------------------------------------

        notifications = DashboardService.build_notifications(user_id)

        # -------------------------------------------------------
        # CHARTS
        # -------------------------------------------------------

        expense_chart = DashboardService.expense_breakdown(user_id)

        income_expense_chart = DashboardService.income_vs_expense(user_id)

        cashflow = DashboardService.cashflow_chart(user_id)

        # -------------------------------------------------------
        # BUDGETS
        # -------------------------------------------------------

        budgets = DashboardService.budget_overview(user_id)

        # -------------------------------------------------------
        # TRANSACTIONS
        # -------------------------------------------------------

        transactions = DashboardService.build_recent_transactions(
            user_id=user_id,
            limit=10,
            period=period,
            transaction_type=transaction_type,
            category=category,
            search=search,
            page=1,
        )

        # -------------------------------------------------------
        # AI ANALYTICS
        # -------------------------------------------------------

        trend = DashboardService.spending_trend(user_id)

        # -------------------------------------------------------
        # SAVINGS OPPORTUNITY
        # -------------------------------------------------------

        savings_opportunity = DashboardService.savings_opportunity(user_id)

        # -------------------------------------------------------
        # PERSONALIZATION
        # -------------------------------------------------------

        personalization = DashboardService.build_personalization(user_id)

        assert isinstance(summary, dict), f"summary is {type(summary)} -> {summary}"
        assert isinstance(kpis, dict), f"kpis is {type(kpis)} -> {kpis}"
        assert isinstance(daily_brief, dict), f"daily_brief is {type(daily_brief)} -> {daily_brief}"

        # -------------------------------------------------------
        # EXECUTIVE SUMMARY VARIABLES
        # -------------------------------------------------------

        # Savings Rate
        savings_rate = summary.get("savings_rate", 0)

        # Overrall Balance
        balance = summary.get("balance", 0)

        # Cash Flow Status (Current Month Only)
        monthly_income = summary.get("monthly_income", 0)
        monthly_expenses = summary.get("monthly_expenses", 0)

        monthly_balance = monthly_income - monthly_expenses

        if monthly_balance > 0:
            cashflow_status = "Positive"
        elif monthly_balance < 0:
            cashflow_status = "Negative"
        else:
            cashflow_status = "Neutral"

        # Budget Status
        if not budget_warnings:

            budget_status = "Healthy"

        elif any(
            item["percentage"] >= 100
            for item in budget_warnings
        ):

            budget_status = "Exceeded"

        elif any(
            item["percentage"] >= 80
            for item in budget_warnings
        ):

            budget_status = "Warning"

        else:

            budget_status = "On Track"

        # -------------------------------------------------------
        # AI Strengths
        # -------------------------------------------------------

        ai_strengths = []

        if savings_rate >= 20:
            ai_strengths.append(
                f"Strong savings rate ({savings_rate:.1f}%)."
            )

        if balance > 0:
            ai_strengths.append(
                "You are maintaining a positive cash balance."
            )

        if not budget_warnings:
            ai_strengths.append(
                "All budgets are currently under control."
            )

        if health_score >= 85:
            ai_strengths.append(
                "Excellent financial health."
            )

        if not ai_strengths:
            ai_strengths.append(
                "Keep recording your financial activities."
            )

        # -------------------------------------------------------
        # AI Attention
        # -------------------------------------------------------

        ai_attention = []

        if balance < 0:
            ai_attention.append(
                "Expenses currently exceed income."
            )

        if savings_rate < 20:
            ai_attention.append(
                "Increase your monthly savings rate."
            )

        for warning in budget_warnings:

            percentage = warning.get("percentage", 0)

            if percentage >= 100:
                ai_attention.append(
                    f'{warning["category"]} budget has been exceeded.'
                )

            elif percentage >= 80:
                ai_attention.append(
                    f'{warning["category"]} budget is almost exhausted.'
                )

        if health_score < 70:
            ai_attention.append(
                "Financial health requires improvement."
            )

        if not ai_attention:
            ai_attention.append(
                "No immediate financial concerns."
            )

        # ---------------------------------------------------
        # Month-End Forecast
        # ---------------------------------------------------

        forecast = DashboardService.month_end_forecast(
            user_id
        )

        # -------------------------------------------------------
        # COMPLETE DASHBOARD OBJECT
        # -------------------------------------------------------

        investment_summary = DashboardService.investment_summary(user_id)
        financial_position = DashboardService.financial_position_summary(user_id)

        dashboard = {

            # ---------------------------------------------------
            # Flattened Summary & KPI values
            # ---------------------------------------------------

            **summary,
            **kpis,

            # ---------------------------------------------------
            # Flattened Financial Health
            # ---------------------------------------------------

            "health_score": health_score,
            "health_message": health_message,
            "health_income": health_income,
            "health_expenses": health_expenses,
            "health_savings": health_savings,

            # ---------------------------------------------------
            # Grouped Objects
            # ---------------------------------------------------

            "summary": summary,
            "kpis": kpis,
            "investments": investment_summary,
            "financial_position": financial_position,
            "financial_health": financial_health,
            "health": financial_health,

            "ai_summary": ai_summary,
            "insights": insights,
            "budget_warning": budget_warning,
            "goal_progress": goal_progress,
            "recommendations": recommendations,
            "daily_brief": daily_brief,
            "notifications": notifications,

            # ---------------------------------------------------
            # Transactions & Budgets
            # ---------------------------------------------------

            "budget_overview": budgets,
            "ai_financial_insight": ai_financial_insight,

            # Recent Transactions
            "recent_transactions": transactions["items"],
            "transaction_count": transactions["total"],
            "transaction_total": transactions["total"],
            "categories": transactions["categories"],

            # ---------------------------------------------------
            # Charts
            # ---------------------------------------------------

            "charts": {
                "expense_chart": expense_chart,
                "income_expense_chart": income_expense_chart,
                "cashflow": cashflow,
            },

            # Backward compatibility
            "expense_chart": expense_chart,
            "income_expense_chart": income_expense_chart,
            "cashflow": cashflow,

            # ---------------------------------------------------
            # AI Analytics
            # ---------------------------------------------------

            "spending_trend": trend["trend"],
            "spending_change": trend["change"],
            "savings_opportunity": savings_opportunity,
            "forecast_balance": forecast["projected_savings"],
            "forecast_income": forecast["projected_income"],
            "forecast_expenses": forecast["projected_expenses"],
            "forecast_status": forecast.get("forecast_status", "Unavailable"),
            "forecast_confidence": forecast.get("confidence"),

            # ---------------------------------------------------
            # Personalization
            # ---------------------------------------------------

            "personalization": personalization,

            # ---------------------------------------------------
            # Forecast
            # ---------------------------------------------------


        }

        dashboard["active_budgets"] = active_budgets
        dashboard["budget_risk"] = budget_risk
        dashboard["budget_warning"] = budget_warning      # Summary string
        dashboard["budget_warnings"] = budget_warnings    # List of budget dictionaries

        dashboard.update({
            "goal_progress": goal_progress,
            "goal_achieved": kpis["goal_achieved"],
            "completed_goals": kpis["completed_goals"],
            "total_goals": kpis["total_goals"],
            "active_goals": kpis["active_goals"],
        })

        # =======================================================
        # NORMALIZE DATA FOR TEMPLATES
        # =======================================================

        dashboard["ai_summary"] = {
            "score": ai_summary.get("score", health_score),
            "message": ai_summary.get("message", ""),
        }

        dashboard["health_score"] = health_score
        dashboard["savings_rate"] = savings_rate
        dashboard["cashflow_status"] = cashflow_status
        dashboard["budget_status"] = budget_status
        dashboard["ai_strengths"] = ai_strengths
        dashboard["ai_attention"] = ai_attention
        dashboard["ai_generated"] = datetime.now().strftime("%d %b %Y %I:%M %p")

        # -------------------------------------------------------
        # Savings Advice
        # -------------------------------------------------------

        dashboard["savings_advice"] = (
            f"You could save approximately "
            f"₦{savings_opportunity:,.2f} by reducing "
            f"discretionary spending by 10%."
            if savings_opportunity
            else "No savings opportunity detected."
        )

        # -------------------------------------------------------
        # Cash Flow
        # -------------------------------------------------------

        if summary["income"] > summary["expenses"]:
            dashboard["cashflow_trend"] = "Positive"
            dashboard["cashflow_message"] = (
                "Income exceeds expenses."
            )
        elif summary["income"] < summary["expenses"]:
            dashboard["cashflow_trend"] = "Negative"
            dashboard["cashflow_message"] = (
                "Expenses exceed income."
            )
        else:
            dashboard["cashflow_trend"] = "Balanced"
            dashboard["cashflow_message"] = (
                "Income equals expenses."
            )

        return dashboard

        # -------------------------------------------------------
        # AI Confidence
        # -------------------------------------------------------

#        dashboard["ai_confidence"] = min(
#            100,
#            40
#            + int(transactions.get("total", 0)) * 2
#            + len(budgets) * 5
#            + len(goal_progress) * 5
#        )
#
#        return dashboard

    # ==========================================================
    # HELPER METHODS
    # ==========================================================

    @staticmethod
    def monthly_income(user_id):
        today_date = today()

        start = today_date.replace(day=1)
        end = today_date

        totals = DashboardService._cash_flow_totals(
            user_id=user_id,
            start_date=start,
            end_date=end,
        )

        return totals["income"]


    @staticmethod
    def monthly_expense(user_id):
        today_date = today()

        start = today_date.replace(day=1)
        end = today_date

        totals = DashboardService._cash_flow_totals(
            user_id=user_id,
            start_date=start,
            end_date=end,
        )

        return totals["expenses"]

    @staticmethod
    def average_daily_spending(user_id):
        """
        Returns the average daily spending for the current month.
        """

        today = date.today()

        total_spent = (
            db.session.query(
                func.coalesce(func.sum(Expense.amount), 0)
            )
            .filter(
                Expense.user_id == user_id,
                or_(Expense.transaction_class == "expense", Expense.transaction_class.is_(None)),
                extract("year", Expense.expense_date) == today.year,
                extract("month", Expense.expense_date) == today.month
            )
            .scalar()
            or 0
        )

        days_elapsed = max(today.day, 1)

        return round(
            float(total_spent) / days_elapsed,
            2
        )

    @staticmethod
    def monthly_expenses(user_id):
        """
        Compatibility alias.
        """

        return DashboardService.monthly_expense(user_id)

    # ==========================================================
    # SUMMARY
    # ==========================================================

    @staticmethod
    def build_summary(
        user_id,
        period="month",
    ):

        start, end = (
            DashboardService.get_period_dates(
                period
            )
        )

        # ------------------------------------------------------
        # Authoritative cash-flow calculation.
        #
        # Income and expenses are calculated only by
        # DashboardService._cash_flow_totals().
        # This keeps savings consistent across FOCOST.
        # ------------------------------------------------------

        totals = DashboardService._cash_flow_totals(
            user_id=user_id,
            start_date=start,
            end_date=end,
        )

        monthly_income = totals["income"]
        monthly_expenses = totals["expenses"]
        savings = totals["savings"]

        savings_rate = (
            (savings / monthly_income) * 100
            if monthly_income
            else 0
        )

        # ------------------------------------------------------
        # Lifetime balance comes from cumulative monthly savings.
        # ------------------------------------------------------

        balance = DashboardService.available_balance(
            user_id
        )

        # ------------------------------------------------------
        # Top spending category.
        # ------------------------------------------------------

        top_expense = (
            db.session.query(
                Expense.category,
                func.sum(
                    Expense.amount
                ).label("total"),
            )
            .filter(
                Expense.user_id == user_id,
                Expense.is_active.is_(True),
                Expense.expense_date.between(
                    start,
                    end,
                ),
            )
            .group_by(
                Expense.category
            )
            .order_by(
                func.sum(
                    Expense.amount
                ).desc()
            )
            .first()
        )

        top_spending = (
            top_expense.category
            if top_expense
            else "None"
        )

        top_spending_amount = (
            float(top_expense.total)
            if top_expense
            else 0.0
        )

        # ------------------------------------------------------
        # Top income source.
        # ------------------------------------------------------

        top_income = (
            db.session.query(
                Income.source,
                func.sum(
                    Income.amount
                ).label("total"),
            )
            .filter(
                Income.user_id == user_id,
                Income.is_active.is_(True),
                Income.received_date.between(
                    start,
                    end,
                ),
            )
            .group_by(
                Income.source
            )
            .order_by(
                func.sum(
                    Income.amount
                ).desc()
            )
            .first()
        )

        top_income_source = (
            top_income.source
            if top_income
            else "None"
        )

        top_income_amount = (
            float(top_income.total)
            if top_income
            else 0.0
        )

        return {
            "balance": round(balance, 2),
            "income": round(monthly_income, 2),
            "expenses": round(monthly_expenses, 2),
            "savings": round(savings, 2),
            "savings_rate": round(savings_rate, 2),
            "monthly_income": round(monthly_income, 2),
            "monthly_expenses": round(monthly_expenses, 2),
            "top_spending": top_spending,
            "top_spending_amount": round(top_spending_amount, 2),
            "top_income_source": top_income_source,
            "top_income_amount": round(top_income_amount, 2),
        }

    # ==========================================================
    # AI FINANCIAL INSIGHT
    # ==========================================================

    # ==========================================================
    # AI FINANCIAL INSIGHT
    # ==========================================================

    @staticmethod
    def build_ai_financial_insight(user_id):

        # --------------------------------------------
        # Current Month Figures
        # --------------------------------------------

        monthly_income = DashboardService.monthly_income(user_id)
        monthly_expenses = DashboardService.monthly_expense(user_id)

        savings = monthly_income - monthly_expenses

        # --------------------------------------------
        # Default Values
        # --------------------------------------------

        insight = {
            "monthly_income": monthly_income,
            "monthly_expenses": monthly_expenses,
            "total_savings": savings,
        }

        if monthly_income <= 0:

            insight.update({

                "prediction":
                    "No income has been recorded for this month. "
                    "Add your income to receive personalized financial insights.",

                "forecast_status":
                    "Not enough financial data to generate a forecast.",

                "projected_income": 0.0,
                "projected_expenses": 0.0,
                "projected_savings": 0.0,
            })

            return insight

        savings_ratio = savings / monthly_income

        advice = []

        # --------------------------------------------
        # Overall Financial Health
        # --------------------------------------------

        if savings < 0:

            advice.append(
                "🚫 <strong>You are currently spending more than you earn this month. Reduce non-essential expenses immediately and address the follwing observations:</strong>"
            )

        elif savings_ratio < 0.10:

            advice.append(
                "❗ <strong>Your savings rate this month is below 10%. Consider increasing your monthly savings and address the follwing observations:</strong>"
            )

        elif savings_ratio >= 0.30:

            advice.append(
                "✅ <strong>Excellent! You are saving more than 30% of your income this month. Note the follwing observations:</strong>"
            )

        else:

            advice.append(
                "✔️ <strong>Your spending this month looks good. Note the follwing observations:</strong>"
            )

        # --------------------------------------------
        # Category Analysis (Current Month)
        # --------------------------------------------

        current_month = date.today().month
        current_year = date.today().year

        category_totals = {}

        expenses = (
            Expense.query
            .filter_by(user_id=user_id)
            .all()
        )

        for expense in expenses:

            if (
                expense.expense_date.year == current_year
                and expense.expense_date.month == current_month
            ):

                category_totals.setdefault(
                    expense.category,
                    0
                )

                category_totals[
                    expense.category
                ] += expense.amount

        for category, amount in category_totals.items():

            ratio = amount / monthly_income

            if ratio >= 0.40:

                advice.append(
                    f"⚠️ High spending detected on <strong>{category}</strong> "
                    f"(₦{amount:,.2f}), representing "
                    f"<strong>{ratio:.0%}</strong> of this month's income."
                )

            elif ratio <= 0.05:

                advice.append(
                    f"ℹ️ Spending on <strong>{category}</strong> "
                    f"<strong>(₦{amount:,.2f})</strong>, "
                    f"is relatively low this month."
                )

        # --------------------------------------------
        # Budget Analysis
        # --------------------------------------------

        budget_warnings = DashboardService.build_budget_warning(
            user_id
        )

        if budget_warnings:

            for budget in budget_warnings:

                if budget["percentage"] >= 100:

                    advice.append(
                        f"🚨 Your <strong>{budget['category']}</strong> "
                        f"budget has been exceeded "
                        f"({budget['percentage']:.0f}% used)."
                    )

                elif budget["percentage"] >= 80:

                    advice.append(
                        f"⚠️ Your <strong>{budget['category']}</strong> "
                        f"budget is almost exhausted "
                        f"({budget['percentage']:.0f}% used)."
                    )

        else:

            advice.append(
                "✅ All your budgets are currently within safe limits."
            )

        # --------------------------------------------
        # Goal Progress
        # --------------------------------------------

        goals = DashboardService.build_goal_progress(
            user_id
        )

        if goals:

            for goal in goals:

                if goal["percentage"] >= 100:

                    advice.append(
                        f"🎉 Congratulations! You've successfully achieved your "
                        f"<strong>{goal['title']}</strong> goal. "
                        f"Celebrate this milestone and consider setting a new financial goal to keep building your wealth."
                    )

                elif goal["percentage"] >= 90:

                    advice.append(
                        f"🏆 Excellent progress! Your "
                        f"<strong>{goal['title']}</strong> goal "
                        f"is <strong>{goal['percentage']:.0f}%</strong> complete. "
                        f"You're in the final stretch—keep it up!"
                    )

                elif goal["percentage"] < 50:

                    advice.append(
                        f"🎯 Your "
                        f"<strong>{goal['title']}</strong> goal "
                        f"is only <strong>{goal['percentage']:.0f}%</strong> complete. "
                        f"Consider increasing your contributions to reach your target sooner."
                    )


        # --------------------------------------------
        # Month-End Forecast
        # --------------------------------------------

        forecast = DashboardService.month_end_forecast(user_id)

        # --------------------------------------------
        # Financial Health
        # --------------------------------------------

        health = DashboardService.build_financial_health(
            user_id
        )

        advice.append(
            f"❤️ Your financial health score is "
            f"<strong>{health['score']}%</strong> "
            f"({health['status']})."
        )

        # --------------------------------------------
        # Final Insight
        # --------------------------------------------

        insight["prediction"] = "<br>".join(
            advice
        )

        insight["forecast_status"] = (
            forecast["forecast_status"]
        )

        insight["projected_income"] = (
            forecast["projected_income"]
        )

        insight["projected_expenses"] = (
            forecast["projected_expenses"]
        )

        insight["projected_savings"] = (
            forecast["projected_savings"]
        )

        return insight

    # ==========================================================
    # SAVINGS OPPORTUNITY
    # ==========================================================

    @staticmethod
    def savings_opportunity(user_id):
        """
        Estimated amount the user could save this month by reducing
        discretionary spending by 10%.
        """

        today = date.today()

        discretionary_categories = [
            "Entertainment",
            "Dining",
            "Shopping",
            "Travel",
            "Lifestyle",
            "Miscellaneous"
        ]

        amount = (
            db.session.query(
                func.coalesce(func.sum(Expense.amount), 0)
            )
            .filter(
                Expense.user_id == user_id,
                Expense.category.in_(discretionary_categories),
                extract("year", Expense.expense_date) == today.year,
                extract("month", Expense.expense_date) == today.month,
            )
            .scalar()
            or 0
        )

        return round(float(amount) * 0.10, 2)

    # ==========================================================
    # KPI CARDS
    # ==========================================================

    @staticmethod
    def build_kpis(user_id):

        today = date.today()

        # ---------------------------------------------------------
        # Largest Income (Current Month)
        # ---------------------------------------------------------

        largest_income = (
            Income.query
            .filter(
                Income.user_id == user_id,
                extract("year", Income.received_date) == today.year,
                extract("month", Income.received_date) == today.month,
            )
            .order_by(Income.amount.desc())
            .first()
        )

        # ---------------------------------------------------------
        # Largest Expense (Current Month)
        # ---------------------------------------------------------

        largest_expense = (
            Expense.query
            .filter(
                Expense.user_id == user_id,
                or_(Expense.transaction_class == "expense", Expense.transaction_class.is_(None)),
                extract("year", Expense.expense_date) == today.year,
                extract("month", Expense.expense_date) == today.month,
            )
            .order_by(Expense.amount.desc())
            .first()
        )

        # ---------------------------------------------------------
        # Monthly Transaction Count
        # ---------------------------------------------------------

        transaction_count = (
            Income.query.filter(
                Income.user_id == user_id,
                extract("year", Income.received_date) == today.year,
                extract("month", Income.received_date) == today.month,
            ).count()
            +
            Expense.query.filter(
                Expense.user_id == user_id,
                or_(Expense.transaction_class == "expense", Expense.transaction_class.is_(None)),
                extract("year", Expense.expense_date) == today.year,
                extract("month", Expense.expense_date) == today.month,
            ).count()
        )

        # ---------------------------------------------------------
        # Monthly Expenses
        # ---------------------------------------------------------

        monthly_expenses = (
            db.session.query(
                func.coalesce(func.sum(Expense.amount), 0)
            )
            .filter(
                Expense.user_id == user_id,
                or_(Expense.transaction_class == "expense", Expense.transaction_class.is_(None)),
                extract("year", Expense.expense_date) == today.year,
                extract("month", Expense.expense_date) == today.month,
            )
            .scalar()
            or 0
        )

        # ---------------------------------------------------------
        # Average Daily Spending (Current Month)
        # ---------------------------------------------------------

        days_elapsed = max(today.day, 1)

        average_daily_spending = round(
            float(monthly_expenses) / days_elapsed,
            2
        )

        # ---------------------------------------------------------
        # Budgets
        # ---------------------------------------------------------

        budget_count = (
            Budget.query
            .filter_by(user_id=user_id)
            .count()
        )

        budgets = Budget.query.filter_by(user_id=user_id).all()

        active_budgets = len(budgets)

        if budgets:

            total_budget = sum(float(b.amount) for b in budgets)

            total_spent = 0

            for budget in budgets:

                spent = (
                    db.session.query(
                        func.coalesce(func.sum(Expense.amount), 0)
                    )
                    .filter(
                        Expense.user_id == user_id,
                        Expense.category == budget.category,
                        Expense.expense_date >= budget.start_date,
                        Expense.expense_date <= budget.end_date
                    )
                    .scalar()
                )

                total_spent += float(spent)

            budget_used = round(
                (total_spent / total_budget) * 100,
                1
            ) if total_budget else 0

        else:

            active_budgets = 0
            budget_used = 0

        # ---------------------------------------------------------
        # Goals
        # ---------------------------------------------------------

        active_goals = (
            Goal.query
            .filter(
                Goal.user_id == user_id,
                Goal.status != "Completed"
            )
            .count()
        )

        completed_goals = (
            Goal.query
            .filter(
                Goal.user_id == user_id,
                Goal.status == "Completed"
            )
            .count()
        )

        goals = Goal.query.filter_by(
            user_id=user_id
        ).all()

        total_goals = len(goals)

        goal_completion = sum(
            1 for goal in goals
            if goal.progress_percentage >= 100
        )

        if total_goals:

            goal_achieved = round(
                sum(goal.progress_percentage for goal in goals) / total_goals,
                1
            )

        else:

            goal_achieved = 0

        return {

            "largest_income":
                float(largest_income.amount)
                if largest_income else 0,

            "largest_expense":
                float(largest_expense.amount)
                if largest_expense else 0,

            "transaction_count":
                transaction_count,

            "average_daily_spending":
                average_daily_spending,

            "budget_count":
                budget_count,

            "active_goals":
                active_goals,

            "completed_goals":
                completed_goals,

            "goal_completion": goal_completion,

            "goal_achieved": goal_achieved,

            "active_budgets": active_budgets,

            "budget_used": budget_used,

            "total_goals": total_goals,

        }

    # ==========================================================
    # AI SUMMARY
    # ==========================================================

    @staticmethod
    def build_ai_summary(user_id):

        summary = DashboardService.build_summary(user_id)

        income = summary["income"]

        expenses = summary["expenses"]

        savings = summary["savings"]

        savings_rate = summary["savings_rate"]

        if income == 0:

            score = 0

            message = (
                "Welcome to FOCOST AI. "
                "Add your first income record to begin your financial journey."
            )

        else:

            expense_ratio = expenses / income

            if expense_ratio <= 0.50:
                score = 95

            elif expense_ratio <= 0.70:
                score = 85

            elif expense_ratio <= 0.90:
                score = 70

            else:
                score = 55

            message = (
                f"You earned ₦{income:,.2f}, spent ₦{expenses:,.2f}, "
                f"and currently have ₦{savings:,.2f}. "
                f"Your savings rate is {savings_rate:.2f}%."
            )

        return {
            "score": score,
            "message": message,
            "savings_rate": savings_rate
        }

    # ==========================================================
    # SMART INSIGHTS
    # ==========================================================

    @staticmethod
    def build_insights(user_id):

        summary = DashboardService.build_summary(user_id)
        insights = []
        if summary["income"] == 0:
            insights.append(
                "No income has been recorded."
            )

            return insights
        expense_ratio = (
            summary["expenses"] /
            summary["income"]
        )

        if expense_ratio > 0.90:
            insights.append(
                "You are spending more than 90% of your income."
            )

        elif expense_ratio > 0.75:
            insights.append(
                "Your expenses are becoming high."
            )

        else:
            insights.append(
                "Your spending is under control."
            )

        if summary["savings_rate"] >= 30:
            insights.append(
                "Excellent savings rate."
            )

        elif summary["savings_rate"] >= 20:
            insights.append(
                "Good savings habit."
            )

        else:
            insights.append(
                "Increase your monthly savings."
            )

        return insights
    # ==========================================================
    # GOAL PROGRESS
    # ==========================================================

    @staticmethod
    def build_goal_progress(user_id):

        goals = (
            Goal.query
            .filter_by(user_id=user_id)
            .order_by(Goal.target_date)
            .all()
        )

        progress = []

        today_date = today()

        for goal in goals:

            percentage = round(
                goal.progress_percentage,
                2,
            )

            # --------------------------------------------------
            # Goal Status
            # --------------------------------------------------

            if percentage >= 100:
                status = "Completed"

            elif goal.target_date and goal.target_date < today_date:
                status = "Overdue"

            elif percentage >= 75:
                status = "On Track"

            elif percentage >= 40:
                status = "At Risk"

            elif goal.target_date and goal.target_date > today_date:
                # A future target date is not behind schedule merely because
                # the goal is below an arbitrary funding percentage.
                status = "In Progress"

            else:
                status = "Behind"

            # --------------------------------------------------
            # Progress Bar Color
            # --------------------------------------------------

            if status == "Completed":
                progress_color = "bg-success"

            elif status == "Overdue":
                progress_color = "bg-danger"

            elif status == "Behind":
                progress_color = "bg-danger"

            elif status == "At Risk":
                progress_color = "bg-warning"

            elif status == "On Track":
                progress_color = "bg-primary"

            else:
                progress_color = "bg-secondary"

            # --------------------------------------------------
            # Estimated Completion
            # --------------------------------------------------

            if percentage >= 100:
                estimated_completion = "Completed"

            elif goal.target_date:
                estimated_completion = goal.target_date.strftime(
                    "%d %b %Y"
                )

            else:
                estimated_completion = "Not Available"

            # --------------------------------------------------
            # Funding Pace
            # --------------------------------------------------

            if percentage >= 100:
                funding_pace = "Completed"

            elif percentage >= 80:
                funding_pace = "Excellent"

            elif percentage >= 60:
                funding_pace = "On Track"

            elif percentage >= 40:
                funding_pace = "Moderate"

            else:
                funding_pace = "Slow"

            # --------------------------------------------------
            # Completion / Funding Calculation
            # --------------------------------------------------
            # Calculate once and reuse throughout this method.

            remaining_months = max(
                goal.days_remaining / 30,
                1,
            )

            required_monthly = round(
                goal.remaining_amount / remaining_months,
                2,
            )

            # --------------------------------------------------
            # AI Recommendation
            # --------------------------------------------------

            if percentage >= 100:

                recommendation = (
                    f"🎉 Congratulations! You've successfully achieved your "
                    f"<strong>{goal.title}</strong> financial goal. "
                    f"Consider setting a new goal to continue building your wealth."
                )

            elif (
                goal.target_date
                and goal.target_date < today_date
            ):

                days_overdue = (
                    today_date - goal.target_date
                ).days

                recommendation = (
                    f"This goal is overdue by <strong>{days_overdue}</strong> "
                    f"day{'s' if days_overdue != 1 else ''}. "
                    f"To complete <strong>{goal.title}</strong>, increase your monthly savings "
                    f"to approximately <strong>₦{required_monthly:,.2f}</strong> "
                    f"or extend the target date."
                )

            elif percentage >= 75:

                recommendation = (
                    f"✅ Excellent progress! Continue contributing at least "
                    f"<strong>₦{goal.monthly_contribution:,.2f}</strong> each month "
                    f"to complete <strong>{goal.title}</strong> on schedule."
                )

            elif percentage >= 40:

                recommendation = (
                    f"⚠️ You're making steady progress. Increasing your monthly savings "
                    f"to approximately <strong>₦{required_monthly:,.2f}</strong> "
                    f"will improve your chances of reaching "
                    f"<strong>{goal.title}</strong> by the target date."
                )

            elif (
                goal.target_date
                and goal.target_date > today_date
            ):

                recommendation = (
                    f"Your <strong>{goal.title}</strong> goal is in progress. "
                    f"Continue contributing toward the remaining "
                    f"<strong>₦{goal.remaining_amount:,.2f}</strong> before "
                    f"the target date."
                )

            else:

                recommendation = (
                    f"🚨 Your goal is behind schedule. To reach "
                    f"<strong>{goal.title}</strong> on time, aim to save about "
                    f"<strong>₦{required_monthly:,.2f}</strong> each month "
                    f"and reduce non-essential spending where possible."
                )

            # --------------------------------------------------
            # Alert Class
            # --------------------------------------------------

            if status == "Completed":
                alert_class = "alert-success"

            elif status == "Overdue":
                alert_class = "alert-danger"

            elif status == "Behind":
                alert_class = "alert-danger"

            elif status == "At Risk":
                alert_class = "alert-warning"

            elif status == "On Track":
                alert_class = "alert-primary"

            else:
                alert_class = "alert-secondary"

            # --------------------------------------------------
            # Badge / Style
            # --------------------------------------------------

            status_styles = {
                "Completed": {
                    "progress": goal.progress_color,
                    "badge": goal.badge_class,
                    "alert": "alert-success",
                },
                "Overdue": {
                    "progress": goal.progress_color,
                    "badge": goal.badge_class,
                    "alert": "alert-danger",
                },
                "Behind": {
                    "progress": "bg-danger",
                    "badge": "bg-danger",
                    "alert": "alert-danger",
                },
                "At Risk": {
                    "progress": goal.progress_color,
                    "badge": goal.badge_class,
                    "alert": "alert-warning",
                },
                "On Track": {
                    "progress": goal.progress_color,
                    "badge": goal.badge_class,
                    "alert": "alert-primary",
                },
                "In Progress": {
                    "progress": goal.progress_color,
                    "badge": goal.badge_class,
                    "alert": "alert-secondary",
                },
            }

            style = status_styles.get(
                status,
                {
                    "progress": "bg-secondary",
                    "badge": "bg-secondary",
                    "alert": "alert-secondary",
                },
            )

            progress_color = style["progress"]
            badge_class = style["badge"]
            alert_class = style["alert"]

            # --------------------------------------------------
            # Final Progress Record
            # --------------------------------------------------

            progress.append({
                "id": goal.id,
                "title": goal.title,
                "goal_type": goal.goal_type,
                "saved": goal.saved_amount,
                "target": goal.target_amount,
                "remaining": goal.remaining_amount,
                "percentage": percentage,
                "status": status,
                "days_remaining": goal.days_remaining,
                "monthly_contribution": goal.monthly_contribution,
                "recommendation": recommendation,
                "estimated_completion": estimated_completion,
                "funding_pace": funding_pace,
                "alert_class": alert_class,
                "progress_color": progress_color,
                "badge_class": badge_class,
                "background_class": goal.background_class,
            })

        return progress

    # ==========================================================
    # NOTIFICATIONS
    # ==========================================================

    @staticmethod
    def build_notifications(user_id):
        """
        Returns the latest notifications for the dashboard.
        """

        return NotificationService.get_recent(
            user_id=user_id,
            limit=5
        )

    # ==========================================================
    # BUDGET WARNING
    # ==========================================================

    @staticmethod
    def build_budget_warning(user_id):

        today_date = today()

        days_elapsed = max(
            today_date.day,
            1,
        )

        days_in_month = calendar.monthrange(
            today_date.year,
            today_date.month,
        )[1]

        budgets = (
            Budget.query
            .filter_by(user_id=user_id)
            .order_by(Budget.category)
            .all()
        )

        warnings = []

        for budget in budgets:

            spent = float(
                DashboardService
                ._active_operating_expense_query(user_id)
                .filter(
                    Expense.category == budget.category,
                    Expense.expense_date.between(
                        budget.start_date,
                        budget.end_date,
                    ),
                )
                .with_entities(
                    func.coalesce(
                        func.sum(Expense.amount),
                        0,
                    )
                )
                .scalar()
                or 0
            )

            budget.spent = spent

            projected = (
                budget.spent / days_elapsed
            ) * days_in_month

            pct = min(
                budget.percentage_used,
                100,
            )

            if pct >= 100:

                recommendation = (
                    "Budget exceeded. Stop discretionary spending immediately."
                )

            elif projected > budget.amount:

                recommendation = (
                    "Current spending indicates this budget will likely be exceeded before month-end."
                )

            elif pct >= 90:

                recommendation = (
                    "You are very close to reaching this budget. Limit further spending."
                )

            elif pct >= 75:

                recommendation = (
                    "Monitor this category carefully over the remaining days."
                )

            else:

                recommendation = (
                    "This budget is performing well."
                )

            warnings.append({

                "category": budget.category,

                "budget": float(
                    budget.amount
                ),

                "spent": budget.spent,

                "remaining": budget.remaining,

                "projected": round(
                    projected,
                    2,
                ),

                "percentage": pct,

                "status": budget.status,

                "risk": budget.risk,

                "recommendation": recommendation,

                "progress_color": budget.progress_color,

                "badge_class": budget.badge_class,

                "background_class": budget.background_class,

            })

        warnings.sort(
            key=lambda x: x["percentage"],
            reverse=True,
        )

        return warnings

    # ==========================================================
    # FINANCIAL HEALTH
    # ==========================================================

    @staticmethod
    def build_financial_health(user_id):

        income = DashboardService.monthly_income(user_id)
        expenses = DashboardService.monthly_expense(user_id)
        savings = income - expenses

        if income == 0:
            score = 100
        else:
            ratio = expenses / income

            if ratio <= 0.50:
                score = 95
            elif ratio <= 0.70:
                score = 85
            elif ratio <= 0.90:
                score = 70
            else:
                score = 55

        if score >= 90:
            grade = "A"
            status = "Excellent"
            color = "success"

        elif score >= 80:
            grade = "B"
            status = "Good"
            color = "primary"

        elif score >= 70:
            grade = "C"
            status = "Fair"
            color = "warning"

        else:
            grade = "D"
            status = "Needs Attention"
            color = "danger"

        return {
            "score": score,
            "grade": grade,
            "status": status,
            "color": color,
            "message": DashboardService.health_message(score),
            "income": income,
            "expenses": expenses,
            "savings": savings,
            "balance": savings,
        }

    # ==========================================================
    # AI RECOMMENDATIONS
    # ==========================================================

    @staticmethod
    def build_recommendations(user_id):

        recommendations = []

        health = DashboardService.build_financial_health(user_id)

        if health["score"] < 70:
            recommendations.append(
                "Reduce discretionary spending."
            )

        if health["expenses"] > health["income"]:
            recommendations.append(
                "Your expenses exceed your income."
            )

        budgets = DashboardService.build_budget_warning(user_id)

        for budget in budgets:

            if budget["percentage"] >= 90:

                recommendations.append(
                    f'{budget["category"]} budget is almost exhausted.'
                )

        goals = DashboardService.build_goal_progress(user_id)

        for goal in goals:

            if (
                goal["days_remaining"] <= 30
                and goal["percentage"] < 70
            ):
                recommendations.append(
                    f"Increase savings toward your {goal['title']} goal."
                )

        if not recommendations:
            recommendations.append(
                "Excellent work. Your finances are progressing well."
            )

        return recommendations

    # ==========================================================
    # PERSONALIZATION
    # ==========================================================

    @staticmethod
    def build_personalization(user_id):

        return {
            "welcome": "Welcome back to FOCOST AI",
            "greeting": "Welcome back! Here's your financial overview.",
            "currency": "NGN",
            "theme": "Modern",
            "assistant": "FOCOST Financial Intelligence",
            "dashboard_layout": "AI"
        }

    # ==========================================================
    # HEALTH MESSAGE
    # ==========================================================

    @staticmethod
    def health_message(score):

        if score >= 90:

            return "Excellent financial health."

        elif score >= 75:
            return "Very good financial health."
        elif score >= 60:
            return "Fair financial health."
        elif score >= 40:
            return "You should reduce your expenses."
        return "Immediate financial attention is recommended."

    # ==========================================================
    # DAILY BRIEF
    # ==========================================================

    @staticmethod
    def build_daily_brief(user_id):

        today_date = today()

        # ------------------------------------------------------
        # Today's Authoritative Cash-Flow Totals
        # ------------------------------------------------------

        totals = DashboardService._cash_flow_totals(
            user_id=user_id,
            start_date=today_date,
            end_date=today_date,
        )

        income = totals["income"]
        expenses = totals["expenses"]
        savings = totals["savings"]

        return {
            "date": today_date,
            "today_income": income,
            "today_expense": expenses,
            "today_balance": savings,
            "message": (
                f"Today your financial position shows "
                f"₦{income:,.2f} income, "
                f"₦{expenses:,.2f} expenses "
                f"and a remaining balance of "
                f"₦{savings:,.2f}. "
                f"Continue monitoring your budgets "
                f"and contribute toward your savings goals."
            ),
        }

    # ==========================================================
    # EXPENSE BREAKDOWN (DOUGHNUT CHART)
    # ==========================================================

    @staticmethod
    def expense_breakdown(user_id):
        """
        Doughnut Chart
        Current Month Operating Expense Breakdown.
        """

        today_date = today()

        start = today_date.replace(day=1)
        end = today_date

        rows = (
            DashboardService
            ._active_operating_expense_query(user_id)
            .filter(
                Expense.expense_date.between(
                    start,
                    end,
                )
            )
            .with_entities(
                Expense.category,
                func.sum(Expense.amount),
            )
            .group_by(
                Expense.category
            )
            .order_by(
                func.sum(Expense.amount).desc()
            )
            .all()
        )

        return {
            "labels": [
                row[0]
                for row in rows
            ],
            "values": [
                float(row[1] or 0)
                for row in rows
            ],
        }

    # ==========================================================
    # INCOME VS EXPENSE (CURRENT MONTH)
    # ==========================================================

    @staticmethod
    def income_vs_expense(user_id):
        """
        Current Month Total Cash Flow: Income vs Expenses.
        """

        today_date = today()

        start = today_date.replace(day=1)
        end = today_date

        totals = DashboardService._cash_flow_totals(
            user_id=user_id,
            start_date=start,
            end_date=end,
        )

        return {
            "labels": ["Income", "Expenses"],
            "values": [
                totals["income"],
                totals["expenses"],
            ],
            "income": totals["income"],
            "expenses": totals["expenses"],
            "savings": totals["savings"],
        }

    # ==========================================================
    # CASHFLOW CHART
    # ==========================================================

    @staticmethod
    def cashflow_chart(user_id):
        """
        Monthly Cash Flow Trend (Current Year).

        Includes all active cash expenses:
            - ordinary expenses
            - investment funding
            - goal contributions

        Investment valuation/revaluation is excluded because it
        does not enter the Income or Expense tables.
        """

        today_date = today()

        months = [
            "Jan", "Feb", "Mar", "Apr",
            "May", "Jun", "Jul", "Aug",
            "Sep", "Oct", "Nov", "Dec",
        ]

        income = [0.0] * 12
        expense = [0.0] * 12

        year_start = date(
            today_date.year,
            1,
            1,
        )

        year_end = date(
            today_date.year,
            12,
            31,
        )

        # ---------------------------------------------------------
        # Active Income by Month (Current Year)
        # ---------------------------------------------------------

        income_query = (
            DashboardService
            ._active_income_query(user_id)
            .filter(
                Income.received_date.between(
                    year_start,
                    year_end,
                )
            )
        )

        income_rows = (
            income_query
            .with_entities(
                extract(
                    "month",
                    Income.received_date,
                ),
                func.sum(Income.amount),
            )
            .group_by(
                extract(
                    "month",
                    Income.received_date,
                )
            )
            .all()
        )

        # ---------------------------------------------------------
        # Active Cash Expenses by Month (Current Year)
        # ---------------------------------------------------------

        expense_query = (
            DashboardService
            ._active_expense_query(user_id)
            .filter(
                Expense.expense_date.between(
                    year_start,
                    year_end,
                )
            )
        )

        expense_rows = (
            expense_query
            .with_entities(
                extract(
                    "month",
                    Expense.expense_date,
                ),
                func.sum(Expense.amount),
            )
            .group_by(
                extract(
                    "month",
                    Expense.expense_date,
                )
            )
            .all()
        )

        # ---------------------------------------------------------
        # Populate Monthly Series
        # ---------------------------------------------------------

        for month, amount in income_rows:
            income[int(month) - 1] = float(
                amount or 0
            )

        for month, amount in expense_rows:
            expense[int(month) - 1] = float(
                amount or 0
            )

        return {
            "labels": months,
            "income": income,
            "expenses": expense,
        }

    # ==========================================================
    # BUDGET OVERVIEW
    # ==========================================================

    @staticmethod
    def budget_overview(user_id):

        budgets = (
            Budget.query
            .filter_by(user_id=user_id)
            .order_by(Budget.category)
            .all()
        )

        for budget in budgets:

            spent = (
                db.session.query(
                    func.coalesce(
                        func.sum(Expense.amount),
                        0
                    )
                )
                .filter(
                    Expense.user_id == user_id,
                    or_(Expense.transaction_class == "expense", Expense.transaction_class.is_(None)),
                    Expense.category == budget.category,
                    Expense.expense_date >= budget.start_date,
                    Expense.expense_date <= budget.end_date
                )
                .scalar()
            )

            budget.spent = float(spent)

        return budgets

    # ==========================================================
    # RECENT TRANSACTIONS
    # ==========================================================

    @staticmethod
    def build_recent_transactions(
        user_id,
        limit=10,
        period="month",
        transaction_type=None,
        category=None,
        search=None,
        start_date=None,
        end_date=None,
        page=1,
    ):
        """
        Returns active dashboard transactions.

        Supports:
            - Today
            - Week
            - Month
            - Year
            - Lifetime
            - Custom Date

        Optional filters:
            - Type
            - Category
            - Search

        Pagination:
            - page
            - limit
        """

        today_date = today()

        # ------------------------------------------------------
        # Normalize inputs
        # ------------------------------------------------------

        period = (period or "month").lower()

        transaction_type = (
            transaction_type.strip()
            if transaction_type
            else None
        )

        search = (
            search.strip()
            if search
            else None
        )

        category = (
            category.strip()
            if category
            else None
        )

        try:
            page = max(int(page), 1)
        except (TypeError, ValueError):
            page = 1

        try:
            limit = max(int(limit), 1)
        except (TypeError, ValueError):
            limit = 10

        # ------------------------------------------------------
        # Base Queries
        # ------------------------------------------------------

        income_query = (
            DashboardService
            ._active_income_query(user_id)
        )

        expense_query = (
            DashboardService
            ._active_expense_query(user_id)
        )

        # ------------------------------------------------------
        # DATE FILTER
        # ------------------------------------------------------

        if period == "today":

            income_query = income_query.filter(
                Income.received_date == today_date
            )

            expense_query = expense_query.filter(
                Expense.expense_date == today_date
            )

        elif period == "week":

            start = today_date - timedelta(
                days=today_date.weekday()
            )

            income_query = income_query.filter(
                Income.received_date >= start
            )

            expense_query = expense_query.filter(
                Expense.expense_date >= start
            )

        elif period == "month":

            start = today_date.replace(day=1)

            income_query = income_query.filter(
                Income.received_date.between(
                    start,
                    today_date,
                )
            )

            expense_query = expense_query.filter(
                Expense.expense_date.between(
                    start,
                    today_date,
                )
            )

        elif period == "year":

            start = date(
                today_date.year,
                1,
                1,
            )

            income_query = income_query.filter(
                Income.received_date.between(
                    start,
                    today_date,
                )
            )

            expense_query = expense_query.filter(
                Expense.expense_date.between(
                    start,
                    today_date,
                )
            )

        elif period == "custom" and start_date and end_date:

            income_query = income_query.filter(
                Income.received_date.between(
                    start_date,
                    end_date,
                )
            )

            expense_query = expense_query.filter(
                Expense.expense_date.between(
                    start_date,
                    end_date,
                )
            )

        elif period == "lifetime":

            # Intentionally no date filter.
            pass

        # ------------------------------------------------------
        # CATEGORY FILTER
        # ------------------------------------------------------

        if category:

            income_query = income_query.filter(
                Income.category == category
            )

            expense_query = expense_query.filter(
                Expense.category == category
            )

        # ------------------------------------------------------
        # SEARCH FILTER
        # ------------------------------------------------------

        if search:

            search_pattern = f"%{search}%"

            income_query = income_query.filter(
                db.or_(
                    Income.source.ilike(
                        search_pattern
                    ),
                    Income.category.ilike(
                        search_pattern
                    ),
                    Income.notes.ilike(
                        search_pattern
                    ),
                )
            )

            expense_query = expense_query.filter(
                db.or_(
                    Expense.merchant.ilike(
                        search_pattern
                    ),
                    Expense.category.ilike(
                        search_pattern
                    ),
                    Expense.notes.ilike(
                        search_pattern
                    ),
                )
            )

        # ------------------------------------------------------
        # BUILD TRANSACTIONS
        # ------------------------------------------------------

        transactions = []

        # ------------------------------------------------------
        # INCOME
        # ------------------------------------------------------

        if transaction_type in (
            None,
            "",
            "Income",
        ):

            for item in income_query.all():

                transactions.append({
                    "id": item.id,
                    "type": "Income",
                    "title": item.source,
                    "category": item.category,
                    "amount": float(
                        item.amount or 0
                    ),
                    "date": item.received_date,
                    "note": getattr(
                        item,
                        "notes",
                        None,
                    ),
                    "flagged": bool(
                        getattr(
                            item,
                            "flagged",
                            False,
                        )
                    ),
                })

        # ------------------------------------------------------
        # EXPENSE
        # ------------------------------------------------------

        if transaction_type in (
            None,
            "",
            "Expense",
        ):

            for item in expense_query.all():

                transactions.append({
                    "id": item.id,
                    "transaction_id": item.id,
                    "transaction_type": "Expense",
                    "type": "Expense",
                    "title": item.merchant,
                    "category": item.category,
                    "amount": float(
                        item.amount or 0
                    ),
                    "date": item.expense_date,
                    "note": getattr(
                        item,
                        "notes",
                        None,
                    ),
                    "flagged": bool(
                        getattr(
                            item,
                            "flagged",
                            False,
                        )
                    ),
                })

        # ------------------------------------------------------
        # SORT
        # ------------------------------------------------------

        transactions.sort(
            key=lambda x: (
                x["date"],
                x["id"],
            ),
            reverse=True,
        )

        # ------------------------------------------------------
        # TOTAL
        # ------------------------------------------------------

        total = len(transactions)

        # ------------------------------------------------------
        # CATEGORIES
        # ------------------------------------------------------

        categories = sorted({
            x["category"]
            for x in transactions
            if x["category"]
        })

        # ------------------------------------------------------
        # PAGINATION
        # ------------------------------------------------------

        pages = (
            (total + limit - 1) // limit
            if total
            else 1
        )

        if page > pages:
            page = pages

        start = (
            (page - 1) * limit
        )

        end = start + limit

        paginated_transactions = transactions[
            start:end
        ]

        # ------------------------------------------------------
        # RETURN
        # ------------------------------------------------------

        return {
            "items": paginated_transactions,
            "total": total,
            "categories": categories,
            "period": period,
            "limit": limit,
            "page": page,
            "pages": pages,
            "has_prev": page > 1,
            "has_next": page < pages,
            "prev_num": (
                page - 1
                if page > 1
                else None
            ),
            "next_num": (
                page + 1
                if page < pages
                else None
            ),
        }

    # ==========================================================
    # SPENDING TREND
    # ==========================================================

    @staticmethod
    def spending_trend(user_id):

        today_date = today()

        query = (
            DashboardService
            ._active_operating_expense_query(user_id)
        )

        # ------------------------------------------------------
        # Current Month
        # ------------------------------------------------------

        current_month_start = today_date.replace(day=1)

        this_month = float(
            query
            .filter(
                Expense.expense_date.between(
                    current_month_start,
                    today_date,
                )
            )
            .with_entities(
                func.coalesce(
                    func.sum(Expense.amount),
                    0,
                )
            )
            .scalar()
            or 0
        )

        # ------------------------------------------------------
        # Previous Month
        # ------------------------------------------------------

        previous_month = today_date.month - 1
        previous_year = today_date.year

        if previous_month == 0:
            previous_month = 12
            previous_year -= 1

        previous_month_start = date(
            previous_year,
            previous_month,
            1,
        )

        previous_month_end = date(
            previous_year,
            previous_month,
            calendar.monthrange(
                previous_year,
                previous_month,
            )[1],
        )

        last_month = float(
            query
            .filter(
                Expense.expense_date.between(
                    previous_month_start,
                    previous_month_end,
                )
            )
            .with_entities(
                func.coalesce(
                    func.sum(Expense.amount),
                    0,
                )
            )
            .scalar()
            or 0
        )

        # ------------------------------------------------------
        # Trend
        # ------------------------------------------------------

        if last_month == 0:

            return {
                "trend": "No previous data",
                "change": 0,
            }

        pct = round(
            (
                (this_month - last_month)
                / last_month
            ) * 100,
            1,
        )

        if pct > 0:
            trend = "Increasing"

        elif pct < 0:
            trend = "Decreasing"

        else:
            trend = "Stable"

        return {
            "trend": trend,
            "change": abs(pct),
        }

    # ==========================================================
    # MONTH-END FORECAST
    # ==========================================================

    @staticmethod
    def month_end_forecast(user_id):

        today_date = today()

        days_in_month = calendar.monthrange(
            today_date.year,
            today_date.month,
        )[1]

        days_elapsed = max(today_date.day, 1)

        month_start = today_date.replace(day=1)

        # ------------------------------------------------------
        # Current Month Totals
        # ------------------------------------------------------

        monthly_expenses = DashboardService.monthly_expense(
            user_id
        )

        # ------------------------------------------------------
        # Variable (Non-Salary) Income
        # ------------------------------------------------------

        variable_income = float(
            DashboardService
            ._active_income_query(user_id)
            .filter(
                Income.received_date.between(
                    month_start,
                    today_date,
                ),
                Income.category != "Salary",
            )
            .with_entities(
                func.coalesce(
                    func.sum(Income.amount),
                    0,
                )
            )
            .scalar()
            or 0
        )

        average_daily_variable_income = (
            variable_income / days_elapsed
        )

        projected_variable_income = (
            average_daily_variable_income * days_in_month
        )

        # ------------------------------------------------------
        # Salary Received This Month
        # ------------------------------------------------------

        salary_income = float(
            DashboardService
            ._active_income_query(user_id)
            .filter(
                Income.received_date.between(
                    month_start,
                    today_date,
                ),
                Income.category == "Salary",
            )
            .with_entities(
                func.coalesce(
                    func.sum(Income.amount),
                    0,
                )
            )
            .scalar()
            or 0
        )

        # ------------------------------------------------------
        # Estimate Salary (Only If None Received This Month)
        # ------------------------------------------------------

        if salary_income == 0:

            previous_month = today_date.month - 1
            previous_year = today_date.year

            if previous_month == 0:
                previous_month = 12
                previous_year -= 1

            previous_month_start = date(
                previous_year,
                previous_month,
                1,
            )

            previous_month_end = date(
                previous_year,
                previous_month,
                calendar.monthrange(
                    previous_year,
                    previous_month,
                )[1],
            )

            # --------------------------------------------------
            # Previous Month Salary
            # --------------------------------------------------

            estimated_salary = float(
                DashboardService
                ._active_income_query(user_id)
                .filter(
                    Income.received_date.between(
                        previous_month_start,
                        previous_month_end,
                    ),
                    Income.category == "Salary",
                )
                .with_entities(
                    func.coalesce(
                        func.sum(Income.amount),
                        0,
                    )
                )
                .scalar()
                or 0
            )

            # --------------------------------------------------
            # Latest Salary Fallback
            # --------------------------------------------------

            if estimated_salary == 0:

                latest_salary = (
                    DashboardService
                    ._active_income_query(user_id)
                    .filter(
                        Income.category == "Salary",
                    )
                    .order_by(
                        Income.received_date.desc(),
                        Income.id.desc(),
                    )
                    .first()
                )

                if latest_salary:

                    months_since = (
                        (
                            today_date.year
                            - latest_salary.received_date.year
                        ) * 12
                        + (
                            today_date.month
                            - latest_salary.received_date.month
                        )
                    )

                    if months_since <= 3:
                        estimated_salary = float(
                            latest_salary.amount
                        )

            salary_income = estimated_salary

        # ------------------------------------------------------
        # Projected Income
        # ------------------------------------------------------

        projected_income = (
            salary_income
            + projected_variable_income
        )

        # ------------------------------------------------------
        # Projected Expenses
        # ------------------------------------------------------

        average_daily_expense = (
            monthly_expenses / days_elapsed
        )

        projected_expenses = (
            average_daily_expense * days_in_month
        )

        # ------------------------------------------------------
        # Projected Savings
        # ------------------------------------------------------

        projected_savings = (
            projected_income
            - projected_expenses
        )

        # ------------------------------------------------------
        # Forecast Status
        # ------------------------------------------------------

        if projected_savings < 0:

            forecast_status = (
                "⚠️ Based on your current income and spending trends, "
                "you are projected to overspend before the end of the month."
            )

        elif (
            projected_income > 0
            and projected_savings < (projected_income * 0.20)
        ):

            forecast_status = (
                "⚠️ Based on your current finances, you may save less than "
                "20% of your income by the end of this month. "
                "Consider reducing unnecessary expenses where possible."
            )

        else:

            forecast_status = (
                "✅ Based on your current income and spending trends, "
                "you are on track to achieve healthy month-end savings."
            )

        # ------------------------------------------------------
        # Return Forecast
        # ------------------------------------------------------

        return {
            "projected_income": round(
                projected_income,
                2,
            ),
            "projected_expenses": round(
                projected_expenses,
                2,
            ),
            "projected_savings": round(
                projected_savings,
                2,
            ),
            "forecast_status": forecast_status,
        }

    # ==========================================================
    # FORECAST BALANCE
    # ==========================================================

    @staticmethod
    def forecast_balance(user_id):

        forecast = DashboardService.month_end_forecast(
            user_id
        )

        return forecast["projected_savings"]

    # ==========================================================
    # AUTHORITATIVE AI FINANCIAL CONTEXT
    # ==========================================================
    @staticmethod
    def financial_context(
        user_id,
        start=None,
        end=None,
        intent="summary",
        focus=None,
        message="",
        transaction_limit=20,
    ):
        """
        Return compact, intent-scoped, database-derived financial context.

        IMPORTANT:
            Every AI financial context includes `calculation_context`.

            `calculation_context` contains the authoritative calculations,
            rules, formulas, classifications, and explanatory metadata used
            by DashboardService.

        The LLM must explain the supplied calculations rather than inventing
        or independently recalculating financial figures.

        Financial data is fetched on demand according to the detected AI
        intent. The entire financial database must never be dumped into an
        ordinary AI prompt.
        """

        if start is None:
            start = date.today().replace(day=1)

        if end is None:
            end = date.today()

        intent = (intent or "summary").strip().lower()
        message = (message or "").strip()

        limit = max(int(transaction_limit or 20), 0)

        # ----------------------------------------------------------
        # AUTHORITATIVE CALCULATION CONTEXT
        # ----------------------------------------------------------
        #
        # This is deliberately generated once and attached to every
        # financial AI context.
        #
        # It allows FOCOST AI to explain:
        #   - where a figure came from
        #   - which records were included
        #   - which records were excluded
        #   - formulas used
        #   - transaction classifications
        #   - period rules
        #   - balance/savings logic
        #   - forecast logic
        #   - dashboard calculation rules
        #
        calculation_context = (
            DashboardService.ai_calculation_context(
                user_id=user_id,
                start=start,
                end=end,
            )
        )

        def attach_calculation_context(context):
            """
            Attach authoritative calculation metadata to every AI context.

            This helper also guarantees that a malformed/None context does not
            break the AI response pipeline.
            """
            if not isinstance(context, dict):
                context = {}

            context["calculation_context"] = calculation_context

            return context

        # ==========================================================
        # SIMPLE POINT-IN-TIME / PERIOD QUERIES
        # ==========================================================

        if intent == "balance":
            context = DashboardService.ai_balance_context(
                user_id
            )

            return attach_calculation_context(context)

        if intent == "savings":
            context = DashboardService.ai_savings_context(
                user_id=user_id,
                start=start,
                end=end,
            )

            return attach_calculation_context(context)

        if intent == "income":
            context = DashboardService.ai_income_context(
                user_id=user_id,
                start=start,
                end=end,
                limit=limit,
            )

            return attach_calculation_context(context)

        if intent == "expenses":
            context = DashboardService.ai_expense_context(
                user_id=user_id,
                start=start,
                end=end,
                message=message or focus or "",
                limit=limit,
            )

            return attach_calculation_context(context)

        if intent == "transactions":
            context = DashboardService.ai_transaction_context(
                user_id=user_id,
                start=start,
                end=end,
                message=message or focus or "",
                limit=limit,
                expense_only=False,
            )

            return attach_calculation_context(context)

        # ==========================================================
        # FINANCIAL PLANNING / STRUCTURED RECORDS
        # ==========================================================

        if intent == "goals":
            context = DashboardService.ai_goals_context(
                user_id
            )

            return attach_calculation_context(context)

        if intent == "budgets":
            context = DashboardService.ai_budgets_context(
                user_id=user_id,
                start=start,
                end=end,
            )

            return attach_calculation_context(context)

        if intent == "investments":
            context = DashboardService.ai_investments_context(
                user_id
            )

            return attach_calculation_context(context)

        # ==========================================================
        # SUMMARY
        # ==========================================================

        if intent == "summary":
            context = DashboardService.ai_summary_context(
                user_id=user_id,
                start=start,
                end=end,
            )

            return attach_calculation_context(context)

        # ==========================================================
        # COMPARISON
        # ==========================================================

        if intent == "comparison":
            context = DashboardService.ai_comparison_context(
                user_id=user_id,
                message=message,
            )

            return attach_calculation_context(context)

        # ==========================================================
        # FORECASTING
        # ==========================================================

        if intent == "forecast":

            user_context = DashboardService._ai_user_context(
                user_id
            )

            context = {
                "user": user_context,

                "currency": user_context.get(
                    "currency",
                    "NGN",
                ),

                "requested_period": {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                },

                # Historical basis used by forecasting logic.
                "monthly_history": DashboardService.monthly_series(
                    user_id,
                    months=12,
                ),

                # Multi-month forecast.
                "advanced_forecast": (
                    DashboardService.advanced_forecast(
                        user_id,
                        months_ahead=3,
                    )
                ),

                # Current-month projection.
                "month_end_forecast": (
                    DashboardService.month_end_forecast(
                        user_id,
                    )
                ),

                # Category-level forecast.
                "category_forecasts": (
                    DashboardService.category_forecasts(
                        user_id,
                        months=3,
                    )
                ),
            }

            return attach_calculation_context(context)

        # ==========================================================
        # FINANCIAL HEALTH
        # ==========================================================

        if intent == "health":

            context = {
                "user": DashboardService._ai_user_context(
                    user_id
                ),

                "financial_health": (
                    DashboardService.build_financial_health(
                        user_id
                    )
                ),

                "period_summary": (
                    DashboardService.ai_summary_context(
                        user_id=user_id,
                        start=start,
                        end=end,
                    )
                ),
            }

            return attach_calculation_context(context)

        # ==========================================================
        # DATA-GROUNDED FINANCIAL ADVICE
        # ==========================================================

        if intent == "advice":

            context = {
                "user": DashboardService._ai_user_context(
                    user_id
                ),

                "requested_period": {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                },

                "summary": (
                    DashboardService.ai_summary_context(
                        user_id=user_id,
                        start=start,
                        end=end,
                    )
                ),

                "budgets": (
                    DashboardService.ai_budgets_context(
                        user_id=user_id,
                        start=start,
                        end=end,
                    )
                ),

                "goals": (
                    DashboardService.ai_goals_context(
                        user_id
                    )
                ),

                "financial_health": (
                    DashboardService.build_financial_health(
                        user_id
                    )
                ),

                "monthly_trends": (
                    DashboardService.monthly_series(
                        user_id,
                        months=6,
                    )
                ),
            }

            return attach_calculation_context(context)

        # ==========================================================
        # SAFE FALLBACK
        # ==========================================================

        context = DashboardService.ai_summary_context(
            user_id=user_id,
            start=start,
            end=end,
        )

        return attach_calculation_context(context)

    # ==========================================================
    # AI TARGETED CONTEXT
    # ==========================================================

    @staticmethod
    def _ai_user_context(user_id):
        from app.models.user import User

        user = db.session.get(User, user_id)

        if not user:
            return {
                "currency": "NGN"
            }

        return {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "currency": user.currency or "NGN",
            "occupation": user.occupation,
        }

    @staticmethod
    def ai_balance_context(user_id):
        """
        Compact authoritative financial-position context.

        All cash-flow values come from DashboardService._cash_flow_totals().
        Investment valuation/revaluation remains non-cash and is excluded.
        """

        totals = DashboardService._cash_flow_totals(
            user_id=user_id,
        )

        return {
            "user": DashboardService._ai_user_context(
                user_id
            ),
            "income": totals["income"],
            "expenses": totals["expenses"],
            "savings": totals["savings"],
            "available_balance": totals["savings"],
        }

    @staticmethod
    def ai_savings_context(
        user_id,
        start,
        end,
    ):
        """
        AI savings context using the authoritative cash-flow source.

        Period savings is always:

            period income - period expenses

        The actual calculation is delegated to
        DashboardService._cash_flow_totals().

        Investment funding and goal contributions remain cash expenses.

        Investment liquidation proceeds remain cash income.

        Investment valuation/revaluation gains and losses are non-cash
        investment-value changes and are never included in Income or Expense.
        """

        totals = DashboardService._cash_flow_totals(
            user_id=user_id,
            start_date=start,
            end_date=end,
        )

        income = totals["income"]
        expenses = totals["expenses"]
        savings = totals["savings"]

        savings_rate = (
            (savings / income) * 100
            if income
            else 0
        )

        return {
            "user": DashboardService._ai_user_context(
                user_id
            ),
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "income": income,
            "expenses": expenses,
            "savings": savings,
            "savings_rate_percent": round(
                savings_rate,
                2,
            ),
        }

    @staticmethod
    def ai_income_context(
        user_id,
        start,
        end,
        limit=20,
    ):
        """
        Authoritative AI income context.

        Provides:
            - total income across ALL matching records
            - category breakdown across ALL matching records
            - transaction-class breakdown across ALL matching records
            - detailed income records up to `limit`

        IMPORTANT:
        The detailed record limit must never hide the existence of income
        components needed to reconcile the authoritative total.
        """

        from sqlalchemy import func

        # ------------------------------------------------------
        # Authoritative active-income query
        # ------------------------------------------------------

        rows = (
            DashboardService
            ._active_income_query(user_id)
            .filter(
                Income.received_date.between(
                    start,
                    end,
                ),
            )
            .order_by(
                Income.received_date.asc(),
                Income.id.asc(),
            )
            .all()
        )

        # ------------------------------------------------------
        # Base income query
        # ------------------------------------------------------

        base_query = Income.query.filter(
            Income.user_id == user_id,
            Income.is_active == True,
            Income.received_date.between(
                start,
                end,
            ),
        )

        # ------------------------------------------------------
        # AUTHORITATIVE TOTAL
        # ------------------------------------------------------

        total = float(
            base_query.with_entities(
                func.coalesce(
                    func.sum(Income.amount),
                    0,
                )
            ).scalar()
            or 0
        )

        # ------------------------------------------------------
        # TOTAL RECORD COUNT
        # ------------------------------------------------------

        record_count = int(
            base_query.with_entities(
                func.count(Income.id)
            ).scalar()
            or 0
        )

        # ------------------------------------------------------
        # CATEGORY BREAKDOWN
        #
        # This is calculated across ALL income records,
        # not just the limited detailed records.
        # ------------------------------------------------------

        category_rows = (
            base_query.with_entities(
                Income.category,
                func.coalesce(
                    func.sum(Income.amount),
                    0,
                ).label("total"),
                func.count(Income.id).label("count"),
            )
            .group_by(Income.category)
            .order_by(
                func.sum(Income.amount).desc()
            )
            .all()
        )

        category_breakdown = [
            {
                "category": category or "Uncategorized",
                "amount": round(float(amount or 0), 2),
                "count": int(count or 0),
                "percentage_of_total": round(
                    (
                        float(amount or 0) / total * 100
                        if total
                        else 0
                    ),
                    2,
                ),
            }
            for category, amount, count in category_rows
        ]

        # ------------------------------------------------------
        # TRANSACTION CLASS BREAKDOWN
        # ------------------------------------------------------

        class_rows = (
            base_query.with_entities(
                Income.transaction_class,
                func.coalesce(
                    func.sum(Income.amount),
                    0,
                ).label("total"),
                func.count(Income.id).label("count"),
            )
            .group_by(Income.transaction_class)
            .order_by(
                func.sum(Income.amount).desc()
            )
            .all()
        )

        transaction_class_breakdown = [
            {
                "transaction_class": (
                    transaction_class or "income"
                ),
                "amount": round(float(amount or 0), 2),
                "count": int(count or 0),
                "percentage_of_total": round(
                    (
                        float(amount or 0) / total * 100
                        if total
                        else 0
                    ),
                    2,
                ),
            }
            for transaction_class, amount, count
            in class_rows
        ]

        # ------------------------------------------------------
        # DETAILED RECORDS
        #
        # This can still be limited for token efficiency.
        # The authoritative breakdown above is NOT limited.
        # ------------------------------------------------------

        rows = (
            base_query
            .order_by(
                Income.received_date.asc(),
                Income.id.asc(),
            )
            .limit(max(int(limit or 20), 1))
            .all()
        )

        records = [
            {
                "id": row.id,
                "date": row.received_date.isoformat(),
                "source": row.source,
                "category": row.category,
                "amount": float(row.amount or 0),
                "notes": row.notes,
                "recurring": bool(row.recurring),
                "transaction_class": (
                    getattr(
                        row,
                        "transaction_class",
                        "income",
                    )
                    or "income"
                ),
            }
            for row in rows
        ]

        # ------------------------------------------------------
        # RETURN
        # ------------------------------------------------------

        return {
            "user": DashboardService._ai_user_context(
                user_id
            ),

            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },

            # Authoritative total across ALL records.
            "total": round(total, 2),

            "record_count": record_count,

            # Number actually supplied as individual records.
            "record_count_returned": len(records),

            "records_truncated": (
                len(records) < record_count
            ),

            # ALL matching income, regardless of detailed-record limit.
            "category_breakdown": category_breakdown,

            "transaction_class_breakdown": (
                transaction_class_breakdown
            ),

            # Detailed records.
            "records": records,

            # Explicit reconciliation helper.
            "calculation": {
                "formula": (
                    "total_income = sum(all active Income.amount "
                    "records in the requested period)"
                ),
                "result": round(total, 2),
            },

            # Explicit accounting rules.
            "accounting_rules": {
                "investment_liquidation": (
                    "Investment liquidation proceeds are recorded "
                    "as income."
                ),
                "goal_termination": (
                    "When a goal is terminated, all contributed "
                    "amounts are returned as a new Income transaction "
                    "with transaction_class='goal_termination'."
                ),
            },
        }

    @staticmethod
    def ai_expense_context(
        user_id,
        start,
        end,
        message="",
        limit=30,
    ):
        """
        Authoritative AI expense context.

        IMPORTANT:
        This uses the same expense definition as the dashboard's
        monthly_expense() and _monthly_savings_rows():

            total expenses = all legitimate Expense records

        Therefore this includes:
            - ordinary expenses
            - investment funding/cost
            - goal contributions
            - other legitimate cash-outflows

        The AI receives both:
            1. the authoritative total
            2. operating-expense-only total
            3. category breakdown
            4. transaction-class breakdown
            5. merchant breakdown
            6. individual records

        This prevents the AI from saying that expenses do not exist merely
        because the expenses are investment-related.
        """

        from sqlalchemy import func

        base_query = Expense.query.filter(
            Expense.user_id == user_id,
            Expense.is_active == True,
            Expense.expense_date.between(start, end),
        )

        # ------------------------------------------------------
        # Optional category / merchant filtering
        # ------------------------------------------------------

        text = (message or "").lower().strip()

        categories = [
            row[0]
            for row in (
                db.session.query(Expense.category)
                .filter(
                    Expense.user_id == user_id,
                    Expense.category.isnot(None),
                )
                .distinct()
                .all()
            )
            if row[0]
        ]

        category_match = None

        for category in categories:
            category_text = str(category).lower().strip()

            if category_text and category_text in text:
                category_match = category
                break

        if category_match:
            base_query = base_query.filter(
                Expense.category == category_match
            )

        merchants = [
            row[0]
            for row in (
                db.session.query(Expense.merchant)
                .filter(
                    Expense.user_id == user_id,
                    Expense.merchant.isnot(None),
                )
                .distinct()
                .all()
            )
            if row[0]
        ]

        merchant_match = None

        for merchant in merchants:
            merchant_text = str(merchant).lower().strip()

            if merchant_text and merchant_text in text:
                merchant_match = merchant
                break

        if merchant_match:
            base_query = base_query.filter(
                Expense.merchant == merchant_match
            )

        # ------------------------------------------------------
        # Authoritative total
        # ------------------------------------------------------

        total = float(
            base_query.with_entities(
                func.coalesce(
                    func.sum(Expense.amount),
                    0,
                )
            ).scalar()
            or 0
        )

        # ------------------------------------------------------
        # Category breakdown
        # ------------------------------------------------------

        category_rows = (
            base_query.with_entities(
                Expense.category,
                func.coalesce(
                    func.sum(Expense.amount),
                    0,
                ).label("total"),
                func.count(Expense.id).label("count"),
            )
            .group_by(Expense.category)
            .order_by(
                func.sum(Expense.amount).desc()
            )
            .all()
        )

        category_breakdown = [
            {
                "category": category or "Uncategorized",
                "amount": round(float(amount or 0), 2),
                "count": int(count or 0),
                "percentage_of_total": round(
                    (
                        float(amount or 0) / total * 100
                        if total
                        else 0
                    ),
                    2,
                ),
            }
            for category, amount, count in category_rows
        ]

        # ------------------------------------------------------
        # Transaction-class breakdown
        # ------------------------------------------------------

        class_rows = (
            base_query.with_entities(
                Expense.transaction_class,
                func.coalesce(
                    func.sum(Expense.amount),
                    0,
                ).label("total"),
                func.count(Expense.id).label("count"),
            )
            .group_by(Expense.transaction_class)
            .order_by(
                func.sum(Expense.amount).desc()
            )
            .all()
        )

        transaction_class_breakdown = [
            {
                "transaction_class": (
                    transaction_class or "expense"
                ),
                "amount": round(float(amount or 0), 2),
                "count": int(count or 0),
                "percentage_of_total": round(
                    (
                        float(amount or 0) / total * 100
                        if total
                        else 0
                    ),
                    2,
                ),
            }
            for transaction_class, amount, count
            in class_rows
        ]

        # ------------------------------------------------------
        # Operating-expense total
        # ------------------------------------------------------

        operating_total = float(
            base_query.filter(
                or_(
                    Expense.transaction_class == "expense",
                    Expense.transaction_class.is_(None),
                )
            )
            .with_entities(
                func.coalesce(
                    func.sum(Expense.amount),
                    0,
                )
            )
            .scalar()
            or 0
        )

        # ------------------------------------------------------
        # Merchant breakdown
        # ------------------------------------------------------

        merchant_rows = (
            base_query.with_entities(
                Expense.merchant,
                func.coalesce(
                    func.sum(Expense.amount),
                    0,
                ).label("total"),
                func.count(Expense.id).label("count"),
            )
            .group_by(Expense.merchant)
            .order_by(
                func.sum(Expense.amount).desc()
            )
            .all()
        )

        merchant_breakdown = [
            {
                "merchant": merchant or "Unknown",
                "amount": round(float(amount or 0), 2),
                "count": int(count or 0),
            }
            for merchant, amount, count in merchant_rows
        ]

        # ------------------------------------------------------
        # Detailed records
        # ------------------------------------------------------

        rows = (
            base_query
            .order_by(
                Expense.expense_date.desc(),
                Expense.id.desc(),
            )
            .limit(max(int(limit or 30), 1))
            .all()
        )

        records = [
            {
                "id": row.id,
                "date": row.expense_date.isoformat(),
                "merchant": row.merchant,
                "category": row.category,
                "description": row.description,
                "amount": float(row.amount or 0),
                "payment_method": row.payment_method,
                "notes": row.notes,
                "recurring": bool(row.recurring),
                "transaction_class": (
                    getattr(
                        row,
                        "transaction_class",
                        "expense",
                    )
                    or "expense"
                ),
            }
            for row in rows
        ]

        # ------------------------------------------------------
        # Authoritative calculation explanation
        # ------------------------------------------------------

        return {
            "user": DashboardService._ai_user_context(user_id),

            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },

            "definition": {
                "total_expenses": (
                    "Sum of all active Expense records in the "
                    "requested period."
                ),
                "operating_expenses": (
                    "Expenses whose transaction_class is "
                    "'expense' or NULL."
                ),
                "investment_costs": (
                    "Investment funding is recorded as an expense "
                    "and therefore reduces savings."
                ),
                "investment_valuation": (
                    "Investment valuation gains/losses are non-cash "
                    "investment-value changes and are never recorded "
                    "as expenses."
                ),
                "goal_contributions": (
                    "Goal contributions are treated as expenses "
                    "by the dashboard accounting model."
                ),
            },

            "calculation": {
                "formula": "total_expenses = sum(all active Expense.amount)",
                "result": round(total, 2),
            },

            "total_matching_amount": round(total, 2),

            "operating_expenses": round(
                operating_total,
                2,
            ),

            "non_operating_expenses": round(
                total - operating_total,
                2,
            ),

            "category_breakdown": category_breakdown,

            "transaction_class_breakdown": (
                transaction_class_breakdown
            ),

            "merchant_breakdown": merchant_breakdown,

            "filters": {
                "category": category_match,
                "merchant": merchant_match,
            },

            "record_count": (
                int(
                    base_query.with_entities(
                        func.count(Expense.id)
                    ).scalar()
                    or 0
                )
            ),

            "record_count_returned": len(records),

            "records": records,
        }

    @staticmethod
    def ai_transaction_context(
        user_id,
        start,
        end,
        message="",
        limit=20,
        expense_only=False,
    ):
        from sqlalchemy import or_

        # ------------------------------------------------------
        # Authoritative active-expense query
        # ------------------------------------------------------

        query = (
            DashboardService
            ._active_expense_query(user_id)
            .filter(
                Expense.expense_date.between(
                    start,
                    end,
                ),
            )
        )

        text = (message or "").lower().strip()

        # ------------------------------------------------------
        # Category filtering
        # ------------------------------------------------------

        categories = [
            row[0]
            for row in (
                db.session.query(
                    Expense.category
                )
                .filter(
                    Expense.user_id == user_id,
                    Expense.is_active.is_(True),
                    Expense.category.isnot(None),
                )
                .distinct()
                .all()
            )
            if row[0]
        ]

        category_match = None

        for category in categories:
            category_text = str(
                category
            ).lower().strip()

            if (
                category_text
                and category_text in text
            ):
                category_match = category
                break

        if category_match:
            query = query.filter(
                Expense.category == category_match
            )

        # ------------------------------------------------------
        # Merchant filtering
        # ------------------------------------------------------

        merchants = [
            row[0]
            for row in (
                db.session.query(
                    Expense.merchant
                )
                .filter(
                    Expense.user_id == user_id,
                    Expense.is_active.is_(True),
                    Expense.merchant.isnot(None),
                )
                .distinct()
                .all()
            )
            if row[0]
        ]

        merchant_match = None

        for merchant in merchants:
            merchant_text = str(
                merchant
            ).lower().strip()

            if (
                merchant_text
                and merchant_text in text
            ):
                merchant_match = merchant
                break

        if merchant_match:
            query = query.filter(
                Expense.merchant == merchant_match
            )

        # ------------------------------------------------------
        # Exclude non-operating transactions when appropriate
        # ------------------------------------------------------

        if expense_only:
            query = query.filter(
                or_(
                    Expense.transaction_class == "expense",
                    Expense.transaction_class.is_(None),
                )
            )

        # ------------------------------------------------------
        # Detailed transaction records
        # ------------------------------------------------------

        rows = (
            query
            .order_by(
                Expense.expense_date.desc(),
                Expense.id.desc(),
            )
            .limit(max(int(limit or 20), 1))
            .all()
        )

        records = [
            {
                "id": row.id,
                "date": row.expense_date.isoformat(),
                "merchant": row.merchant,
                "category": row.category,
                "description": row.description,
                "amount": float(
                    row.amount or 0
                ),
                "payment_method": row.payment_method,
                "notes": row.notes,
                "recurring": bool(
                    row.recurring
                ),
                "transaction_class": (
                    getattr(
                        row,
                        "transaction_class",
                        "expense",
                    )
                    or "expense"
                ),
            }
            for row in rows
        ]

        # ------------------------------------------------------
        # Authoritative total for the same filtered query
        # ------------------------------------------------------

        total_query = query.with_entities(
            func.coalesce(
                func.sum(Expense.amount),
                0,
            )
        )

        total = float(
            total_query.scalar()
            or 0
        )

        return {
            "user": DashboardService._ai_user_context(
                user_id
            ),
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "filters": {
                "category": category_match,
                "merchant": merchant_match,
                "expense_only": expense_only,
            },
            "total_matching_amount": round(
                total,
                2,
            ),
            "record_count_returned": len(
                records
            ),
            "records": records,
        }

    @staticmethod
    def ai_goals_context(user_id):
        goals = (
            Goal.query
            .filter_by(
                user_id=user_id,
                is_active=True,
            )
            .order_by(
                Goal.target_date.asc()
            )
            .all()
        )

        result = []

        for goal in goals:
            result.append(
                {
                    "id": goal.id,
                    "title": goal.title,
                    "goal_type": goal.goal_type,
                    "target": float(
                        goal.target_amount or 0
                    ),
                    "saved": float(
                        goal.saved_amount or 0
                    ),
                    "remaining": float(
                        goal.remaining_amount or 0
                    ),
                    "target_date": (
                        goal.target_date.isoformat()
                        if goal.target_date
                        else None
                    ),
                    "status": goal.progress_status,
                    "progress_percent": round(
                        float(
                            goal.progress_percentage
                            or 0
                        ),
                        2,
                    ),
                    "monthly_contribution": float(
                        goal.monthly_contribution
                        or 0
                    ),
                }
            )

        return {
            "user": DashboardService._ai_user_context(
                user_id
            ),
            "goal_count": len(result),
            "goals": result,
        }

    @staticmethod
    def ai_budgets_context(
        user_id,
        start,
        end,
    ):
        budgets = (
            Budget.query
            .filter(
                Budget.user_id == user_id,
                Budget.is_active == True,
            )
            .all()
        )

        result = []

        for budget in budgets:
            spent = float(
                db.session.query(
                    func.coalesce(
                        func.sum(
                            Expense.amount
                        ),
                        0,
                    )
                )
                .filter(
                    Expense.user_id == user_id,
                    or_(
                        Expense.transaction_class == "expense",
                        Expense.transaction_class.is_(None),
                    ),
                    Expense.category == budget.category,
                    Expense.expense_date.between(
                        start,
                        end,
                    ),
                )
                .scalar()
                or 0
            )

            amount = float(
                budget.amount or 0
            )

            result.append(
                {
                    "id": budget.id,
                    "category": budget.category,
                    "budget": round(
                        amount,
                        2,
                    ),
                    "spent": round(
                        spent,
                        2,
                    ),
                    "remaining": round(
                        amount - spent,
                        2,
                    ),
                    "percentage_used": round(
                        (
                            spent / amount * 100
                            if amount
                            else 0
                        ),
                        2,
                    ),
                    "status": budget.status,
                    "start_date": (
                        budget.start_date.isoformat()
                        if budget.start_date
                        else None
                    ),
                    "end_date": (
                        budget.end_date.isoformat()
                        if budget.end_date
                        else None
                    ),
                }
            )

        return {
            "user": DashboardService._ai_user_context(
                user_id
            ),
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "budgets": result,
        }

    @staticmethod
    def ai_investments_context(user_id):
        from app.models.asset import Asset

        assets = (
            Asset.query
            .filter_by(
                user_id=user_id,
                is_active=True,
            )
            .order_by(
                Asset.acquisition_date.asc()
            )
            .all()
        )

        records = []

        for asset in assets:
            records.append(
                {
                    "id": asset.id,
                    "name": asset.name,
                    "asset_type": asset.asset_type,
                    "investment_type": asset.investment_type,
                    "acquisition_date": (
                        asset.acquisition_date.isoformat()
                        if asset.acquisition_date
                        else None
                    ),
                    "acquisition_cost": float(
                        asset.acquisition_cost or 0
                    ),
                    "current_value": float(
                        asset.current_value or 0
                    ),
                    "quantity": asset.quantity,
                    "cost_basis": asset.cost_basis,
                    "gain_loss": round(
                        float(
                            asset.gain_loss or 0
                        ),
                        2,
                    ),
                    "return_pct": float(
                        asset.return_pct or 0
                    ),
                    "source_expense_id": (
                        asset.source_expense_id
                    ),
                }
            )

        return {
            "user": DashboardService._ai_user_context(
                user_id
            ),
            "asset_count": len(records),
            "assets": records,
            "total_acquisition_cost": round(
                sum(
                    item["acquisition_cost"]
                    for item in records
                ),
                2,
            ),
            "total_current_value": round(
                sum(
                    item["current_value"]
                    for item in records
                ),
                2,
            ),
            "total_gain_loss": round(
                sum(
                    item["gain_loss"]
                    for item in records
                ),
                2,
            ),
        }

    @staticmethod
    def ai_summary_context(
        user_id,
        start,
        end,
    ):
        totals = DashboardService._cash_flow_totals(
            user_id=user_id,
            start_date=start,
            end_date=end,
        )

        operating_expenses = float(
            DashboardService
            ._active_operating_expense_query(user_id)
            .filter(
                Expense.expense_date.between(
                    start,
                    end,
                ),
            )
            .with_entities(
                func.coalesce(
                    func.sum(Expense.amount),
                    0,
                )
            )
            .scalar()
            or 0
        )

        return {
            "user": DashboardService._ai_user_context(
                user_id
            ),
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "income": totals["income"],
            "expenses": totals["expenses"],
            "operating_expenses": round(
                operating_expenses,
                2,
            ),
            "savings": totals["savings"],
            "savings_rate_percent": round(
                (
                    totals["savings"] / totals["income"] * 100
                    if totals["income"]
                    else 0
                ),
                2,
            ),
        }

    @staticmethod
    def ai_comparison_context(
        user_id,
        message,
    ):
        """
        Compact comparison context.

        Supports explicit month comparisons while keeping the payload small.
        """

        months = re.findall(
            r"\b("
            r"january|jan|february|feb|march|mar|april|apr|may|"
            r"june|jun|july|jul|august|aug|september|sep|sept|"
            r"october|oct|november|nov|december|dec"
            r")"
            r"(?:\s+(20\d{2}))?\b",
            message.lower(),
        )

        month_map = {
            "january": 1,
            "jan": 1,
            "february": 2,
            "feb": 2,
            "march": 3,
            "mar": 3,
            "april": 4,
            "apr": 4,
            "may": 5,
            "june": 6,
            "jun": 6,
            "july": 7,
            "jul": 7,
            "august": 8,
            "aug": 8,
            "september": 9,
            "sep": 9,
            "sept": 9,
            "october": 10,
            "oct": 10,
            "november": 11,
            "nov": 11,
            "december": 12,
            "dec": 12,
        }

        today = date.today()

        selected = []

        for month_name, year_text in months[:2]:
            month = month_map[month_name]
            year = int(
                year_text
                or today.year
            )

            selected.append(
                (
                    year,
                    month,
                )
            )

        if len(selected) < 2:
            series = DashboardService.monthly_series(
                user_id,
                months=3,
            )

            return {
                "user": DashboardService._ai_user_context(
                    user_id
                ),
                "comparison_type": "recent_months",
                "months": series,
            }

        rows = []

        for year, month in selected:
            start = date(
                year,
                month,
                1,
            )

            end = date(
                year,
                month,
                calendar.monthrange(
                    year,
                    month,
                )[1],
            )

            # --------------------------------------------------
            # Authoritative cash-flow totals for this period.
            # --------------------------------------------------

            totals = DashboardService._cash_flow_totals(
                user_id=user_id,
                start_date=start,
                end_date=end,
            )

            rows.append(
                {
                    "month": start.isoformat(),
                    "income": round(
                        totals["income"],
                        2,
                    ),
                    "expenses": round(
                        totals["expenses"],
                        2,
                    ),
                    "savings": round(
                        totals["savings"],
                        2,
                    ),
                }
            )

        return {
            "user": DashboardService._ai_user_context(
                user_id
            ),
            "comparison_type": "explicit_periods",
            "periods": rows,
        }

    @staticmethod
    def monthly_series(
        user_id,
        months=12,
    ):
        """
        Authoritative monthly cash-flow series.

        Monthly savings is always:

            income - all active cash expenses

        All cash expense classifications are included:
            - ordinary expenses
            - investment funding
            - goal contributions

        Investment valuation/revaluation is excluded because it is
        non-cash and never enters the Income or Expense tables.
        """

        today = date.today()

        if months is None:

            first_income = (
                Income.query
                .filter(
                    Income.user_id == user_id,
                    Income.is_active.is_(True),
                )
                .order_by(
                    Income.received_date.asc()
                )
                .first()
            )

            first_expense = (
                Expense.query
                .filter(
                    Expense.user_id == user_id,
                    Expense.is_active.is_(True),
                )
                .order_by(
                    Expense.expense_date.asc()
                )
                .first()
            )

            first_dates = [
                d
                for d in [
                    getattr(
                        first_income,
                        "received_date",
                        None,
                    ),
                    getattr(
                        first_expense,
                        "expense_date",
                        None,
                    ),
                ]
                if d
            ]

            if not first_dates:
                months = 1

            else:

                first_date = min(
                    first_dates
                )

                months = max(
                    1,
                    (
                        (
                            today.year
                            - first_date.year
                        )
                        * 12
                    )
                    + today.month
                    - first_date.month
                    + 1,
                )

        rows = []

        for offset in range(
            months - 1,
            -1,
            -1,
        ):

            year = today.year

            month = (
                today.month
                - offset
            )

            while month <= 0:
                month += 12
                year -= 1

            start = date(
                year,
                month,
                1,
            )

            end = date(
                year,
                month,
                calendar.monthrange(
                    year,
                    month,
                )[1],
            )

            # --------------------------------------------------
            # Authoritative cash-flow calculation for the month.
            # --------------------------------------------------

            totals = DashboardService._cash_flow_totals(
                user_id=user_id,
                start_date=start,
                end_date=end,
            )

            rows.append(
                {
                    "month": start.isoformat(),
                    "income": totals["income"],
                    "expenses": totals["expenses"],
                    "savings": totals["savings"],
                    "net": totals["savings"],
                }
            )

        return rows

    # ==========================================================
    # ADVANCED FORECASTING / STATISTICS
    # ==========================================================
    @staticmethod
    def advanced_forecast(user_id, months_ahead=3):
        import math
        series = DashboardService.monthly_series(user_id, months=12)
        if not series:
            return {"available": False, "reason": "Insufficient financial history."}
        incomes = [x["income"] for x in series]
        expenses = [x["expenses"] for x in series]
        def projection(values):
            n = len(values)
            if n < 3:
                return {"next": values[-1] if values else 0, "confidence": 0, "method": "insufficient_history"}
            xs = list(range(n))
            mean_x = sum(xs) / n; mean_y = sum(values) / n
            denom = sum((x - mean_x) ** 2 for x in xs)
            slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values)) / denom if denom else 0
            intercept = mean_y - slope * mean_x
            fitted = [intercept + slope * x for x in xs]
            residual = math.sqrt(sum((y - f) ** 2 for y, f in zip(values, fitted)) / max(n - 2, 1))
            next_value = max(0, intercept + slope * n)
            cv = residual / max(abs(mean_y), 1)
            confidence = round(max(0, min(95, 95 - cv * 100)), 1)
            return {"next": round(next_value, 2), "confidence": confidence, "slope": round(slope, 2), "residual": round(residual, 2), "method": "linear_trend"}
        inc = projection(incomes); exp = projection(expenses)
        forecast = []
        for i in range(1, months_ahead + 1):
            forecast.append({"month_index": i, "projected_income": round(max(0, inc["next"] + inc["slope"] * (i - 1)), 2), "projected_expenses": round(max(0, exp["next"] + exp["slope"] * (i - 1)), 2)})
            forecast[-1]["projected_net"] = round(forecast[-1]["projected_income"] - forecast[-1]["projected_expenses"], 2)
        return {"available": True, "history_months": len(series), "forecast": forecast, "income_confidence": inc["confidence"], "expense_confidence": exp["confidence"], "method": "linear_trend_with_residual_uncertainty", "historical": series}

    @staticmethod
    def anomaly_analysis(user_id):
        from statistics import mean, pstdev

        current_date = today()

        query = (
            DashboardService
            ._active_expense_query(user_id)
            .filter(
                Expense.expense_date >= (
                    current_date
                    - timedelta(days=90)
                )
            )
        )

        rows = query.all()

        values = [
            float(
                x.amount or 0
            )
            for x in rows
        ]

        if len(values) < 5:
            return {
                "available": False,
                "reason": (
                    "At least five recent expenses "
                    "are needed for anomaly analysis."
                ),
                "anomalies": [],
            }

        avg = mean(values)
        sd = pstdev(values)

        threshold = (
            avg
            + (2 * sd)
        )

        anomalies = [
            {
                "date": x.expense_date.isoformat(),
                "merchant": x.merchant,
                "category": x.category,
                "amount": float(
                    x.amount
                ),
                "z_score": round(
                    (
                        (
                            float(x.amount)
                            - avg
                        )
                        / sd
                    ),
                    2,
                )
                if sd
                else 0,
            }
            for x in rows
            if (
                sd
                and float(x.amount)
                > threshold
            )
        ]

        return {
            "available": True,
            "mean": round(
                avg,
                2,
            ),
            "standard_deviation": round(
                sd,
                2,
            ),
            "threshold": round(
                threshold,
                2,
            ),
            "anomalies": sorted(
                anomalies,
                key=lambda x: x[
                    "amount"
                ],
                reverse=True,
            ),
        }

    @staticmethod
    def scenario(user_id, income_change_pct=0, expense_change_pct=0):
        summary = DashboardService.build_summary(user_id)
        income = float(summary.get("income", 0)); expenses = float(summary.get("expenses", 0))
        adjusted_income = income * (1 + float(income_change_pct) / 100)
        adjusted_expenses = expenses * (1 + float(expense_change_pct) / 100)
        return {"baseline_income": round(income, 2), "baseline_expenses": round(expenses, 2), "adjusted_income": round(adjusted_income, 2), "adjusted_expenses": round(adjusted_expenses, 2), "baseline_net": round(income-expenses, 2), "scenario_net": round(adjusted_income-adjusted_expenses, 2)}

        # @staticmethod
        # def month_end_forecast(user_id):
        #     """Conservative month-end run-rate forecast; no fabricated salary/category assumptions."""
        #     today = date.today()
        #     days_in_month = calendar.monthrange(today.year, today.month)[1]
        #     elapsed = max(today.day, 1)
        #     income = DashboardService.monthly_income(user_id)
        #     expenses = DashboardService.monthly_expense(user_id)
        #     projected_income = (income / elapsed) * days_in_month
        #     projected_expenses = (expenses / elapsed) * days_in_month
        #     projected_savings = projected_income - projected_expenses
        #
        #     if income == 0 and expenses == 0:
        #         status = "Insufficient current-month activity for a reliable run-rate forecast."
        #     elif projected_savings < 0:
        #         status = "Forecast indicates a potential month-end cash-flow deficit if the current run rate continues."
        #     else:
        #         status = "Forecast indicates positive month-end cash flow if the current run rate continues."
        #
        #     confidence = round(
        #         min(90, 35 + (elapsed / days_in_month) * 55),
        #         1,
        #     )
        #
        #     return {
        #         "projected_income": round(
        #             projected_income,
        #             2,
        #         ),
        #         "projected_expenses": round(
        #             projected_expenses,
        #             2,
        #         ),
        #         "projected_savings": round(
        #             projected_savings,
        #             2,
        #         ),
        #
        #         "current_income": round(
        #             income,
        #             2,
        #         ),
        #         "current_expenses": round(
        #             expenses,
        #             2,
        #         ),
        #
        #         "days_elapsed": elapsed,
        #         "days_in_month": days_in_month,
        #         "days_remaining": max(
        #             days_in_month - today.day,
        #             0,
        #         ),
        #
        #         "daily_income_run_rate": round(
        #             income / elapsed,
        #             2,
        #         ),
        #
        #         "daily_expense_run_rate": round(
        #             expenses / elapsed,
        #             2,
        #         ),
        #
        #         "daily_savings_run_rate": round(
        #             (income - expenses) / elapsed,
        #             2,
        #         ),
        #
        #         "calculation": {
        #             "projected_income": (
        #                 "current_income / days_elapsed "
        #                 "* days_in_month"
        #             ),
        #             "projected_expenses": (
        #                 "current_expenses / days_elapsed "
        #                 "* days_in_month"
        #             ),
        #             "projected_savings": (
        #                 "projected_income - projected_expenses"
        #             ),
        #         },
        #
        #         "forecast_status": status,
        #         "confidence": confidence,
        #         "method": "current_month_run_rate",
        #         "is_guaranteed": False,
        #     }

    @staticmethod
    def category_forecasts(
        user_id,
        months=3,
    ):
        """
        Forecast operating spending by category.

        Category forecasting is intentionally restricted to active
        operating expenses only.

        It is a category-spending forecast, not a total cash-outflow
        forecast. Therefore, investment funding, goal contributions,
        and other non-operating cash expenses are excluded.
        """

        today = date.today()

        categories = {}

        for offset in range(
            11,
            -1,
            -1,
        ):
            year = today.year
            month = today.month - offset

            while month <= 0:
                month += 12
                year -= 1

            start = date(
                year,
                month,
                1,
            )

            end = date(
                year,
                month,
                calendar.monthrange(
                    year,
                    month,
                )[1],
            )

            rows = (
                db.session.query(
                    Expense.category,
                    func.sum(
                        Expense.amount
                    ),
                )
                .filter(
                    Expense.user_id == user_id,
                    Expense.is_active.is_(True),
                    or_(
                        Expense.transaction_class == "expense",
                        Expense.transaction_class.is_(None),
                    ),
                    Expense.expense_date.between(
                        start,
                        end,
                    ),
                )
                .group_by(
                    Expense.category
                )
                .all()
            )

            for cat, amount in rows:
                categories.setdefault(
                    cat,
                    [],
                ).append(
                    float(amount or 0)
                )

        result = []

        for cat, values in categories.items():
            if len(values) < 3:
                continue

            recent = values[-3:]

            baseline = (
                sum(recent)
                / len(recent)
            )

            result.append(
                {
                    "category": cat,
                    "average_recent": round(
                        baseline,
                        2,
                    ),
                    "projected_monthly": round(
                        baseline,
                        2,
                    ),
                    "history_points": len(
                        values
                    ),
                }
            )

        return sorted(
            result,
            key=lambda x: x[
                "projected_monthly"
            ],
            reverse=True,
        )