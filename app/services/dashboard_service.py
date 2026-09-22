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

class DashboardService:

    @staticmethod
    def _operating_expense_filter(query):
        """Restrict expense reporting to true expenses, excluding transfers to assets/goals."""
        return query.filter(
            or_(Expense.transaction_class == "expense", Expense.transaction_class.is_(None))
        )


    """

    Central Intelligent Dashboard Service

    This service builds every section of the dashboard.

    All dashboard templates should obtain their data

    exclusively through this service.

    """

    @staticmethod
    def available_balance(user_id, exclude_expense_id=None, as_of=None):
        """Authoritative available cash balance used by goal and investment funding."""
        income_q = Income.query.filter(Income.user_id == user_id, Income.is_active == True)
        expense_q = Expense.query.filter(Expense.user_id == user_id, Expense.is_active == True)
        if as_of:
            income_q = income_q.filter(Income.received_date <= as_of)
            expense_q = expense_q.filter(Expense.expense_date <= as_of)
        if exclude_expense_id is not None:
            expense_q = expense_q.filter(Expense.id != exclude_expense_id)

        incomes = income_q.all()
        expenses = expense_q.all()
        # Valuation gains/losses are accounting events, not cash movements.
        # They remain visible in income/expense reporting but do not increase
        # or reduce spendable cash until an investment is actually liquidated.
        valuation_income_ids = {
            event.income_id for event in InvestmentEvent.query.filter(InvestmentEvent.user_id == user_id, InvestmentEvent.event_type == "valuation", InvestmentEvent.income_id.isnot(None)).all()
        }
        valuation_expense_ids = {
            event.expense_id for event in InvestmentEvent.query.filter(InvestmentEvent.user_id == user_id, InvestmentEvent.event_type == "valuation", InvestmentEvent.expense_id.isnot(None)).all()
        }
        total_income = sum(float(x.amount or 0) for x in incomes if x.id not in valuation_income_ids)
        total_outflows = sum(float(x.amount or 0) for x in expenses if x.id not in valuation_expense_ids)
        return total_income - total_outflows

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
            page=request.args.get("page", 1, type=int),
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

        today = date.today()

        return float(
            db.session.query(
                func.coalesce(func.sum(Income.amount), 0)
            )
            .filter(
                Income.user_id == user_id,
                extract("year", Income.received_date) == today.year,
                extract("month", Income.received_date) == today.month,
            )
            .scalar()
            or 0
        )


    @staticmethod
    def monthly_expense(user_id):

        today = date.today()

        return float(
            db.session.query(
                func.coalesce(func.sum(Expense.amount), 0)
            )
            .filter(
                Expense.user_id == user_id,
                Expense.expense_date.isnot(None),
                extract("year", Expense.expense_date) == today.year,
                extract("month", Expense.expense_date) == today.month,
            )
            .scalar()
            or 0
        )

    @staticmethod
    def current_balance(user_id):
        """
        Returns the user's current balance.
        """

        return (
            DashboardService.monthly_income(user_id)
            - DashboardService.monthly_expense(user_id)
        )

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
    def build_summary(user_id, period="month"):

        start, end = DashboardService.get_period_dates(period)

        monthly_income = (
            db.session.query(
                func.coalesce(func.sum(Income.amount), 0)
            )
            .filter(
                Income.user_id == user_id,
                Income.received_date.between(start, end)
            )
            .scalar()
        )

        monthly_expenses = (
            db.session.query(func.coalesce(func.sum(Expense.amount), 0))
            .filter(Expense.user_id == user_id, Expense.expense_date.between(start, end))
            .scalar()
        )

        # Authoritative available cash includes all genuine cash inflows and
        # outflows, including goal contributions and investment funding.
        balance = DashboardService.available_balance(user_id)

        # Monthly savings
        savings = monthly_income - monthly_expenses

        if monthly_income > 0:

            savings_rate = round(

                (savings / monthly_income) * 100,

                2

            )

        else:

            savings_rate = 0

        # Top Spending Category
        top_expense = (
            db.session.query(
                Expense.category,
                func.sum(Expense.amount).label("total")
            )
            .filter(
                Expense.user_id == user_id,
                or_(Expense.transaction_class == "expense", Expense.transaction_class.is_(None)),
                Expense.expense_date.between(start, end)
            )
            .group_by(Expense.category)
            .order_by(func.sum(Expense.amount).desc())
            .first()
        )

        top_spending = top_expense.category if top_expense else "None"
        top_spending_amount = float(top_expense.total) if top_expense else 0.0

        # Top Income Source
        top_income = (
            db.session.query(
                Income.source,
                func.sum(Income.amount).label("total")
            )
            .filter(
                Income.user_id == user_id,
                Income.received_date.between(start, end)
            )
            .group_by(Income.source)
            .order_by(func.sum(Income.amount).desc())
            .first()
        )

        top_income_source = top_income.source if top_income else "None"
        top_income_amount = float(top_income.total) if top_income else 0.0

        return {
            "balance": balance,
            "income": monthly_income,
            "expenses": monthly_expenses,
            "savings": savings,
            "savings_rate": savings_rate,

            "top_spending": top_spending,
            "top_spending_amount": top_spending_amount,

            "top_income_source": top_income_source,
            "top_income_amount": top_income_amount,

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

        today = date.today()

        for goal in goals:

            percentage = round(goal.progress_percentage, 2)

            # --------------------------------------------------
            # Goal Status
            # --------------------------------------------------

            if percentage >= 100:
                status = "Completed"

            elif goal.target_date and goal.target_date < today:
                status = "Overdue"

            elif percentage >= 75:
                status = "On Track"

            elif percentage >= 40:
                status = "At Risk"

            elif goal.target_date and goal.target_date > today:
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
                estimated_completion = goal.target_date.strftime("%d %b %Y")

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
            # AI Recommendation
            # --------------------------------------------------

            remaining_months = max(goal.days_remaining / 30, 1)

            required_monthly = round(
                goal.remaining_amount / remaining_months,
                2
            )

            # --------------------------------------------------
            # AI Recommendation
            # --------------------------------------------------

            remaining_months = max(goal.days_remaining / 30, 1)

            required_monthly = round(
                goal.remaining_amount / remaining_months,
                2
            )

            if percentage >= 100:

                recommendation = (
                    f"🎉 Congratulations! You've successfully achieved your "
                    f"<strong>{goal.title}</strong> financial goal. "
                    f"Consider setting a new goal to continue building your wealth."
                )

            elif goal.target_date and goal.target_date < today:

                days_overdue = (today - goal.target_date).days

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

            elif goal.target_date and goal.target_date > today:

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
            # Badge Color
            # --------------------------------------------------

            status_styles = {
                "Completed": {
                    "progress": "bg-success",
                    "badge": "bg-success",
                    "alert": "alert-success",
                },
                "Overdue": {
                    "progress": "bg-danger",
                    "badge": "bg-danger",
                    "alert": "alert-danger",
                },
                "Behind": {
                    "progress": "bg-danger",
                    "badge": "bg-danger",
                    "alert": "alert-danger",
                },
                "At Risk": {
                    "progress": "bg-warning",
                    "badge": "bg-warning text-dark",
                    "alert": "alert-warning",
                },
                "On Track": {
                    "progress": "bg-primary",
                    "badge": "bg-primary",
                    "alert": "alert-primary",
                },
            }

            style = status_styles.get(status, {
                "progress": "bg-secondary",
                "badge": "bg-secondary",
                "alert": "alert-secondary",
            })

            progress_color = style["progress"]
            badge_class = style["badge"]
            alert_class = style["alert"]

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
                "badge_class": badge_class
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

        today = date.today()

        days_elapsed = max(today.day, 1)

        days_in_month = calendar.monthrange(
            today.year,
            today.month
        )[1]

        budgets = (
            Budget.query
            .filter_by(user_id=user_id)
            .order_by(Budget.category)
            .all()
        )

        warnings = []

        for budget in budgets:

            spent = (
                db.session.query(
                    func.coalesce(func.sum(Expense.amount), 0)
                )
                .filter(
                    Expense.user_id == user_id,
                    or_(Expense.transaction_class == "expense", Expense.transaction_class.is_(None)),
                    Expense.category == budget.category,
                    Expense.expense_date >= budget.start_date,
                    Expense.expense_date <= budget.end_date
                )
                .scalar()
                or 0
            )

            budget.spent = float(spent)

            projected = (
                budget.spent / days_elapsed
            ) * days_in_month

            pct = min(budget.percentage_used, 100)

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

                "budget": float(budget.amount),

                "spent": budget.spent,

                "remaining": budget.remaining,

                "projected": round(projected, 2),

                "percentage": pct,

                "status": budget.status,

                "risk": budget.risk,

                "recommendation": recommendation,

                "progress_color": budget.progress_color

            })

        warnings.sort(
            key=lambda x: x["percentage"],
            reverse=True
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

    # =====================================================
    # NOTIFICATIONS
    # =====================================================

    @staticmethod
    def build_notifications(user_id):

        return NotificationService.get_recent(
            user_id=user_id,
            limit=5
        )

    # ==========================================================
    # DAILY BRIEF
    # ==========================================================

    @staticmethod
    def build_daily_brief(user_id):

        today = date.today()

        today_income = (
            db.session.query(
                func.coalesce(func.sum(Income.amount), 0)
            )
            .filter(
                Income.user_id == user_id,
                Income.received_date == today
            )
            .scalar()
        )

        today_expense = (
            db.session.query(
                func.coalesce(func.sum(Expense.amount), 0)
            )
            .filter(
                Expense.user_id == user_id,
                Expense.expense_date == today
            )
            .scalar()
        )

        today_income = float(today_income or 0)
        today_expense = float(today_expense or 0)

        today_balance = today_income - today_expense

        return {
            "date": datetime.today(),
            "today_income": today_income,
            "today_expense": today_expense,
            "today_balance": today_balance,
            "message": (
                f"Today your financial position shows "
                f"₦{today_income:,.2f} income, "
                f"₦{today_expense:,.2f} expenses "
                f"and a remaining balance of "
                f"₦{today_balance:,.2f}. "
                f"Continue monitoring your budgets "
                f"and contribute toward your savings goals."
            )
        }

    # ==========================================================
    # EXPENSE BREAKDOWN (DOUGHNUT CHART)
    # ==========================================================

    @staticmethod
    def expense_breakdown(user_id):
        """
        Doughnut Chart
        Current Month Expense Breakdown
        """

        today = date.today()

        rows = (
            db.session.query(
                Expense.category,
                func.sum(Expense.amount)
            )
            .filter(
                Expense.user_id == user_id,
                or_(Expense.transaction_class == "expense", Expense.transaction_class.is_(None)),
                extract("year", Expense.expense_date) == today.year,
                extract("month", Expense.expense_date) == today.month,
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
            "labels": [row[0] for row in rows],
            "values": [float(row[1]) for row in rows],
        }

    # ==========================================================
    # INCOME VS EXPENSE (CURRENT MONTH)
    # ==========================================================

    @staticmethod
    def income_vs_expense(user_id):
        """
        Current Month Income vs Expense
        """

        today = date.today()

        income = (
            db.session.query(
                func.coalesce(func.sum(Income.amount), 0)
            )
            .filter(
                Income.user_id == user_id,
                extract("year", Income.received_date) == today.year,
                extract("month", Income.received_date) == today.month,
            )
            .scalar()
            or 0
        )

        expense = (
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

        return {
            "labels": ["Income", "Expenses"],
            "values": [
                float(income),
                float(expense),
            ],
        }

    # ==========================================================
    # CASHFLOW CHART
    # ==========================================================

    @staticmethod
    def cashflow_chart(user_id):
        """
        Monthly Cash Flow Trend (Current Year)
        """

        today = date.today()

        months = [
            "Jan", "Feb", "Mar", "Apr",
            "May", "Jun", "Jul", "Aug",
            "Sep", "Oct", "Nov", "Dec"
        ]

        income = [0.0] * 12
        expense = [0.0] * 12

        # ---------------------------------------------------------
        # Income by Month (Current Year)
        # ---------------------------------------------------------

        income_rows = (
            db.session.query(
                extract("month", Income.received_date),
                func.sum(Income.amount)
            )
            .filter(
                Income.user_id == user_id,
                extract("year", Income.received_date) == today.year,
            )
            .group_by(
                extract("month", Income.received_date)
            )
            .all()
        )

        # ---------------------------------------------------------
        # Expenses by Month (Current Year)
        # ---------------------------------------------------------

        expense_rows = (
            db.session.query(
                extract("month", Expense.expense_date),
                func.sum(Expense.amount)
            )
            .filter(
                Expense.user_id == user_id,
                extract("year", Expense.expense_date) == today.year,
            )
            .group_by(
                extract("month", Expense.expense_date)
            )
            .all()
        )

        for month, amount in income_rows:
            income[int(month) - 1] = float(amount)

        for month, amount in expense_rows:
            expense[int(month) - 1] = float(amount)

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
        Returns dashboard transactions.

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

        today = date.today()

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

        income_query = Income.query.filter(
            Income.user_id == user_id
        )

        expense_query = Expense.query.filter(
            Expense.user_id == user_id
        )


        # ------------------------------------------------------
        # DATE FILTER
        # ------------------------------------------------------

        if period == "today":

            income_query = income_query.filter(
                Income.received_date == today
            )

            expense_query = expense_query.filter(
                Expense.expense_date == today
            )


        elif period == "week":

            start = today - timedelta(
                days=today.weekday()
            )

            income_query = income_query.filter(
                Income.received_date >= start
            )

            expense_query = expense_query.filter(
                Expense.expense_date >= start
            )


        elif period == "month":

            income_query = income_query.filter(
                extract(
                    "year",
                    Income.received_date
                ) == today.year,

                extract(
                    "month",
                    Income.received_date
                ) == today.month,
            )

            expense_query = expense_query.filter(
                extract(
                    "year",
                    Expense.expense_date
                ) == today.year,

                extract(
                    "month",
                    Expense.expense_date
                ) == today.month,
            )


        elif period == "year":

            income_query = income_query.filter(
                extract(
                    "year",
                    Income.received_date
                ) == today.year
            )

            expense_query = expense_query.filter(
                extract(
                    "year",
                    Expense.expense_date
                ) == today.year
            )


        elif period == "custom" and start_date and end_date:

            income_query = income_query.filter(
                Income.received_date.between(
                    start_date,
                    end_date
                )
            )

            expense_query = expense_query.filter(
                Expense.expense_date.between(
                    start_date,
                    end_date
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

                    Income.note.ilike(
                        search_pattern
                    )

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

                    Expense.note.ilike(
                        search_pattern
                    )

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
            "Income"
        ):

            for item in income_query.all():

                transactions.append({
                    "id": item.id,
                    "type": "Income",
                    "title": item.source,
                    "category": item.category,
                    "amount": float(item.amount or 0),
                    "date": item.received_date,
                    "note": getattr(
                        item,
                        "notes",
                        None
                    ),
                    "flagged": False
                })

        # ------------------------------------------------------
        # EXPENSE
        # ------------------------------------------------------

        if transaction_type in (
            None,
            "",
            "Expense"
        ):

            for item in expense_query.all():

                flagged = getattr(
                    item,
                    "flagged",
                    False
                )

                transactions.append({
                    "id": item.id,
                    "transaction_id": item.id,
                    "transaction_type": "Expense",
                    "type": "Expense",
                    "title": item.merchant,
                    "category": item.category,
                    "amount": float(item.amount or 0),
                    "date": item.expense_date,
                    "note": getattr(
                        item,
                        "notes",
                        None
                    ),
                    "flagged": False
                })

        # ------------------------------------------------------
        # SORT
        # ------------------------------------------------------

        transactions.sort(

            key=lambda x: (
                x["date"],
                x["id"]
            ),

            reverse=True

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
            (total + limit - 1)
            // limit
            if total
            else 1
        )


        # Prevent invalid page numbers

        if page > pages:
            page = pages


        start = (
            (page - 1)
            * limit
        )

        end = start + limit


        paginated_transactions = transactions[
            start:end
        ]


        # ------------------------------------------------------
        # RETURN
        # ------------------------------------------------------

        return {

            "items":
                paginated_transactions,

            "total":
                total,

            "categories":
                categories,

            "period":
                period,

            "limit":
                limit,

            "page":
                page,

            "pages":
                pages,

            "has_prev":
                page > 1,

            "has_next":
                page < pages,

            "prev_num":
                page - 1
                if page > 1
                else None,

            "next_num":
                page + 1
                if page < pages
                else None,

        }

    # ==========================================================
    # SPENDING TREND
    # ==========================================================

    @staticmethod
    def spending_trend(user_id):

        today = date.today()

        this_month = (
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
        )

        previous_month = today.month - 1
        previous_year = today.year

        if previous_month == 0:
            previous_month = 12
            previous_year -= 1

        last_month = (
            db.session.query(
                func.coalesce(func.sum(Expense.amount), 0)
            )
            .filter(
                Expense.user_id == user_id,
                or_(Expense.transaction_class == "expense", Expense.transaction_class.is_(None)),
                extract("year", Expense.expense_date) == previous_year,
                extract("month", Expense.expense_date) == previous_month
            )
            .scalar()
        )

        this_month = float(this_month or 0)
        last_month = float(last_month or 0)

        if last_month == 0:

            return {
                "trend": "No previous data",
                "change": 0
            }

        pct = round(
            ((this_month - last_month) / last_month) * 100,
            1
        )

        if pct > 0:
            trend = "Increasing"

        elif pct < 0:
            trend = "Decreasing"

        else:
            trend = "Stable"

        return {
            "trend": trend,
            "change": abs(pct)
        }

    # ==========================================================
    # MONTH-END FORECAST
    # ==========================================================

    @staticmethod
    def month_end_forecast(user_id):

        today = date.today()

        days_in_month = calendar.monthrange(
            today.year,
            today.month
        )[1]

        days_elapsed = max(today.day, 1)

        # ------------------------------------------------------
        # Current Month Totals
        # ------------------------------------------------------

        monthly_expenses = DashboardService.monthly_expenses(user_id)

        # ------------------------------------------------------
        # Variable (Non-Salary) Income
        # ------------------------------------------------------

        variable_income = (
            db.session.query(
                func.coalesce(func.sum(Income.amount), 0)
            )
            .filter(
                Income.user_id == user_id,
                extract("year", Income.received_date) == today.year,
                extract("month", Income.received_date) == today.month,
                Income.category != "Salary"
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

        salary_income = (
            db.session.query(
                func.coalesce(func.sum(Income.amount), 0)
            )
            .filter(
                Income.user_id == user_id,
                extract("year", Income.received_date) == today.year,
                extract("month", Income.received_date) == today.month,
                Income.category == "Salary"
            )
            .scalar()
            or 0
        )

        # ------------------------------------------------------
        # Estimate Salary (Only If None Received This Month)
        # ------------------------------------------------------

        if salary_income == 0:

            previous_month = today.month - 1
            previous_year = today.year

            if previous_month == 0:
                previous_month = 12
                previous_year -= 1

            # Last month's salary
            estimated_salary = (
                db.session.query(
                    func.coalesce(func.sum(Income.amount), 0)
                )
                .filter(
                    Income.user_id == user_id,
                    extract("year", Income.received_date) == previous_year,
                    extract("month", Income.received_date) == previous_month,
                    Income.category == "Salary"
                )
                .scalar()
                or 0
            )

            # If last month has no salary,
            # use the most recent salary only if
            # it was received within the last 3 months.
            if estimated_salary == 0:

                latest_salary = (
                    Income.query
                    .filter(
                        Income.user_id == user_id,
                        Income.category == "Salary"
                    )
                    .order_by(
                        Income.received_date.desc()
                    )
                    .first()
                )

                if latest_salary:

                    months_since = (
                        (today.year - latest_salary.received_date.year) * 12
                        + (today.month - latest_salary.received_date.month)
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
            salary_income +
            projected_variable_income
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
            projected_income -
            projected_expenses
        )

        # ------------------------------------------------------
        # Forecast Status
        # ------------------------------------------------------

        if projected_savings < 0:

            forecast_status = (
                "⚠️ Based on your current income and spending trends, "
                "you are projected to overspend before the end of the month."
            )

        elif projected_income > 0 and projected_savings < (projected_income * 0.20):

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
            "projected_income": round(projected_income, 2),
            "projected_expenses": round(projected_expenses, 2),
            "projected_savings": round(projected_savings, 2),
            "forecast_status": forecast_status
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

        Financial data is fetched on demand according to the detected AI
        intent. The entire financial database must never be dumped into
        an ordinary AI prompt.
        """
        if start is None:
            start = date.today().replace(day=1)

        if end is None:
            end = date.today()

        intent = (intent or "summary").strip().lower()
        message = (message or "").strip()

        limit = max(int(transaction_limit or 20), 0)

        # ------------------------------------------------------
        # Simple point-in-time / period queries
        # ------------------------------------------------------
        if intent == "balance":
            return DashboardService.ai_balance_context(user_id)

        if intent == "savings":
            return DashboardService.ai_savings_context(
                user_id=user_id,
                start=start,
                end=end,
            )

        if intent == "income":
            return DashboardService.ai_income_context(
                user_id=user_id,
                start=start,
                end=end,
            )

        if intent == "expenses":
            return DashboardService.ai_expense_context(
                user_id=user_id,
                start=start,
                end=end,
                message=message or focus or "",
                limit=limit,
            )

        if intent == "transactions":
            return DashboardService.ai_transaction_context(
                user_id=user_id,
                start=start,
                end=end,
                message=message or focus or "",
                limit=limit,
                expense_only=False,
            )

        # ------------------------------------------------------
        # Financial planning / structured records
        # ------------------------------------------------------
        if intent == "goals":
            return DashboardService.ai_goals_context(user_id)

        if intent == "budgets":
            return DashboardService.ai_budgets_context(
                user_id=user_id,
                start=start,
                end=end,
            )

        if intent == "investments":
            return DashboardService.ai_investments_context(user_id)

        # ------------------------------------------------------
        # Summary
        # ------------------------------------------------------
        if intent == "summary":
            return DashboardService.ai_summary_context(
                user_id=user_id,
                start=start,
                end=end,
            )

        # ------------------------------------------------------
        # Comparison
        # ------------------------------------------------------
        if intent == "comparison":
            return DashboardService.ai_comparison_context(
                user_id=user_id,
                message=message,
            )

        # ------------------------------------------------------
        # Forecasting
        # ------------------------------------------------------
        if intent == "forecast":
            user_context = DashboardService._ai_user_context(user_id)

            return {
                "user": user_context,
                "currency": user_context.get("currency", "NGN"),
                "requested_period": {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                },
                "monthly_history": DashboardService.monthly_series(
                    user_id,
                    months=12,
                ),
                "advanced_forecast": DashboardService.advanced_forecast(
                    user_id,
                    months_ahead=3,
                ),
                "month_end_forecast": DashboardService.month_end_forecast(
                    user_id,
                ),
                "category_forecasts": DashboardService.category_forecasts(
                    user_id,
                    months=3,
                ),
            }

        # ------------------------------------------------------
        # Financial health
        # ------------------------------------------------------
        if intent == "health":
            return {
                "user": DashboardService._ai_user_context(user_id),
                "financial_health": DashboardService.build_financial_health(
                    user_id
                ),
                "period_summary": DashboardService.ai_summary_context(
                    user_id=user_id,
                    start=start,
                    end=end,
                ),
            }

        # ------------------------------------------------------
        # Data-grounded financial advice
        # ------------------------------------------------------
        if intent == "advice":
            return {
                "user": DashboardService._ai_user_context(user_id),
                "requested_period": {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                },
                "summary": DashboardService.ai_summary_context(
                    user_id=user_id,
                    start=start,
                    end=end,
                ),
                "budgets": DashboardService.ai_budgets_context(
                    user_id=user_id,
                    start=start,
                    end=end,
                ),
                "goals": DashboardService.ai_goals_context(user_id),
                "financial_health": DashboardService.build_financial_health(
                    user_id
                ),
                "monthly_trends": DashboardService.monthly_series(
                    user_id,
                    months=6,
                ),
            }

        # ------------------------------------------------------
        # Safe fallback
        # ------------------------------------------------------
        return DashboardService.ai_summary_context(
            user_id=user_id,
            start=start,
            end=end,
        )

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
        Compact authoritative cash-position context.
        """

        total_income = float(
            db.session.query(
                func.coalesce(
                    func.sum(Income.amount),
                    0,
                )
            )
            .filter(
                Income.user_id == user_id
            )
            .scalar()
            or 0
        )

        total_cash_outflows = float(
            db.session.query(
                func.coalesce(
                    func.sum(Expense.amount),
                    0,
                )
            )
            .filter(
                Expense.user_id == user_id
            )
            .scalar()
            or 0
        )

        operating_expenses = float(
            db.session.query(
                func.coalesce(
                    func.sum(Expense.amount),
                    0,
                )
            )
            .filter(
                Expense.user_id == user_id,
                or_(
                    Expense.transaction_class == "expense",
                    Expense.transaction_class.is_(None),
                ),
            )
            .scalar()
            or 0
        )

        investments = max(
            total_cash_outflows -
            operating_expenses,
            0,
        )

        return {
            "user": DashboardService._ai_user_context(
                user_id
            ),
            "all_time_income": round(
                total_income,
                2,
            ),
            "all_time_cash_outflows": round(
                total_cash_outflows,
                2,
            ),
            "all_time_operating_expenses": round(
                operating_expenses,
                2,
            ),
            "all_time_investment_and_transfer_outflows": round(
                investments,
                2,
            ),
            "current_cash_balance": round(
                DashboardService.available_balance(user_id),
                2,
            ),
        }

    @staticmethod
    def ai_savings_context(
        user_id,
        start,
        end,
    ):
        income = float(
            db.session.query(
                func.coalesce(
                    func.sum(Income.amount),
                    0,
                )
            )
            .filter(
                Income.user_id == user_id,
                Income.received_date.between(
                    start,
                    end,
                ),
            )
            .scalar()
            or 0
        )

        expenses = float(
            db.session.query(
                func.coalesce(
                    func.sum(Expense.amount),
                    0,
                )
            )
            .filter(
                Expense.user_id == user_id,
                or_(
                    Expense.transaction_class == "expense",
                    Expense.transaction_class.is_(None),
                ),
                Expense.expense_date.between(
                    start,
                    end,
                ),
            )
            .scalar()
            or 0
        )

        savings = income - expenses

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
            "income": round(
                income,
                2,
            ),
            "operating_expenses": round(
                expenses,
                2,
            ),
            "savings": round(
                savings,
                2,
            ),
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
    ):
        rows = (
            Income.query
            .filter(
                Income.user_id == user_id,
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

        records = [
            {
                "id": row.id,
                "date": row.received_date.isoformat(),
                "source": row.source,
                "category": row.category,
                "amount": float(
                    row.amount or 0
                ),
                "notes": row.notes,
                "recurring": bool(
                    row.recurring
                ),
            }
            for row in rows
        ]

        return {
            "user": DashboardService._ai_user_context(
                user_id
            ),
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "total": round(
                sum(
                    item["amount"]
                    for item in records
                ),
                2,
            ),
            "records": records,
        }

    @staticmethod
    def ai_expense_context(
        user_id,
        start,
        end,
        message="",
        limit=20,
    ):
        return DashboardService.ai_transaction_context(
            user_id=user_id,
            start=start,
            end=end,
            message=message,
            limit=limit,
            expense_only=True,
        )

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

        query = Expense.query.filter(
            Expense.user_id == user_id,
            Expense.expense_date.between(
                start,
                end,
            ),
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
        income = float(
            db.session.query(
                func.coalesce(
                    func.sum(Income.amount),
                    0,
                )
            )
            .filter(
                Income.user_id == user_id,
                Income.received_date.between(
                    start,
                    end,
                ),
            )
            .scalar()
            or 0
        )

        expenses = float(
            db.session.query(
                func.coalesce(
                    func.sum(Expense.amount),
                    0,
                )
            )
            .filter(
                Expense.user_id == user_id,
                or_(
                    Expense.transaction_class == "expense",
                    Expense.transaction_class.is_(None),
                ),
                Expense.expense_date.between(
                    start,
                    end,
                ),
            )
            .scalar()
            or 0
        )

        savings = income - expenses

        return {
            "user": DashboardService._ai_user_context(
                user_id
            ),
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "income": round(
                income,
                2,
            ),
            "operating_expenses": round(
                expenses,
                2,
            ),
            "savings": round(
                savings,
                2,
            ),
            "savings_rate_percent": round(
                (
                    savings / income * 100
                    if income
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
            "january": 1, "jan": 1,
            "february": 2, "feb": 2,
            "march": 3, "mar": 3,
            "april": 4, "apr": 4,
            "may": 5,
            "june": 6, "jun": 6,
            "july": 7, "jul": 7,
            "august": 8, "aug": 8,
            "september": 9, "sep": 9, "sept": 9,
            "october": 10, "oct": 10,
            "november": 11, "nov": 11,
            "december": 12, "dec": 12,
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

            income = float(
                db.session.query(
                    func.coalesce(
                        func.sum(
                            Income.amount
                        ),
                        0,
                    )
                )
                .filter(
                    Income.user_id == user_id,
                    Income.received_date.between(
                        start,
                        end,
                    ),
                )
                .scalar()
                or 0
            )

            expenses = float(
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
                    Expense.expense_date.between(
                        start,
                        end,
                    ),
                )
                .scalar()
                or 0
            )

            rows.append(
                {
                    "month": start.isoformat(),
                    "income": round(
                        income,
                        2,
                    ),
                    "expenses": round(
                        expenses,
                        2,
                    ),
                    "savings": round(
                        income - expenses,
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
    def monthly_series(user_id, months=12):
        """Actual monthly income, operating expense, cash outflow and net cash series."""
        if months is None:
            first_income = Income.query.filter_by(user_id=user_id).order_by(Income.received_date.asc()).first()
            first_expense = Expense.query.filter_by(user_id=user_id).order_by(Expense.expense_date.asc()).first()
            first_date = min([d for d in [getattr(first_income, "received_date", None), getattr(first_expense, "expense_date", None)] if d], default=date.today())
            months = max(1, (date.today().year - first_date.year) * 12 + date.today().month - first_date.month + 1)
        today = date.today()
        rows = []
        for offset in range(months - 1, -1, -1):
            year = today.year; month = today.month - offset
            while month <= 0:
                month += 12; year -= 1
            start = date(year, month, 1); end = date(year, month, calendar.monthrange(year, month)[1])
            income = float(db.session.query(func.coalesce(func.sum(Income.amount), 0)).filter(Income.user_id == user_id, Income.received_date.between(start, end)).scalar() or 0)
            operating = float(db.session.query(func.coalesce(func.sum(Expense.amount), 0)).filter(Expense.user_id == user_id, or_(Expense.transaction_class == "expense", Expense.transaction_class.is_(None)), Expense.expense_date.between(start, end)).scalar() or 0)
            cash_outflows = float(db.session.query(func.coalesce(func.sum(Expense.amount), 0)).filter(Expense.user_id == user_id, Expense.expense_date.between(start, end)).scalar() or 0)
            rows.append({"month": start.isoformat(), "income": round(income, 2), "expenses": round(operating, 2), "cash_outflows": round(cash_outflows, 2), "investments": round(cash_outflows - operating, 2), "net": round(income - cash_outflows, 2), "operating_net": round(income - operating, 2)})
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
        start = date.today() - __import__('datetime').timedelta(days=90)
        rows = Expense.query.filter(Expense.user_id == user_id, Expense.expense_date >= start).all()
        values = [float(x.amount or 0) for x in rows]
        if len(values) < 5:
            return {"available": False, "reason": "At least five recent expenses are needed for anomaly analysis.", "anomalies": []}
        avg = mean(values); sd = pstdev(values)
        threshold = avg + (2 * sd)
        anomalies = [{"date": x.expense_date.isoformat(), "merchant": x.merchant, "category": x.category, "amount": float(x.amount), "z_score": round((float(x.amount)-avg)/sd, 2) if sd else 0} for x in rows if sd and float(x.amount) > threshold]
        return {"available": True, "mean": round(avg, 2), "standard_deviation": round(sd, 2), "threshold": round(threshold, 2), "anomalies": sorted(anomalies, key=lambda x: x["amount"], reverse=True)}

    @staticmethod
    def scenario(user_id, income_change_pct=0, expense_change_pct=0):
        summary = DashboardService.build_summary(user_id)
        income = float(summary.get("income", 0)); expenses = float(summary.get("expenses", 0))
        adjusted_income = income * (1 + float(income_change_pct) / 100)
        adjusted_expenses = expenses * (1 + float(expense_change_pct) / 100)
        return {"baseline_income": round(income, 2), "baseline_expenses": round(expenses, 2), "adjusted_income": round(adjusted_income, 2), "adjusted_expenses": round(adjusted_expenses, 2), "baseline_net": round(income-expenses, 2), "scenario_net": round(adjusted_income-adjusted_expenses, 2)}

    @staticmethod
    def month_end_forecast(user_id):
        """Conservative month-end run-rate forecast; no fabricated salary/category assumptions."""
        today = date.today()
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        elapsed = max(today.day, 1)
        income = DashboardService.monthly_income(user_id)
        expenses = DashboardService.monthly_expense(user_id)
        projected_income = (income / elapsed) * days_in_month
        projected_expenses = (expenses / elapsed) * days_in_month
        projected_savings = projected_income - projected_expenses
        if income == 0 and expenses == 0:
            status = "Insufficient current-month activity for a reliable run-rate forecast."
        elif projected_savings < 0:
            status = "Forecast indicates a potential month-end cash-flow deficit if the current run rate continues."
        else:
            status = "Forecast indicates positive month-end cash flow if the current run rate continues."
        confidence = round(min(90, 35 + (elapsed / days_in_month) * 55), 1)
        return {"projected_income": round(projected_income, 2), "projected_expenses": round(projected_expenses, 2), "projected_savings": round(projected_savings, 2), "forecast_status": status, "confidence": confidence, "method": "current_month_run_rate", "is_guaranteed": False}

    @staticmethod
    def category_forecasts(user_id, months=3):
        """Project category spending using actual historical category totals."""
        today = date.today()
        categories = {}
        for offset in range(11, -1, -1):
            year = today.year; month = today.month - offset
            while month <= 0:
                month += 12; year -= 1
            start = date(year, month, 1); end = date(year, month, calendar.monthrange(year, month)[1])
            rows = db.session.query(Expense.category, func.sum(Expense.amount)).filter(Expense.user_id == user_id, or_(Expense.transaction_class == "expense", Expense.transaction_class.is_(None)), Expense.expense_date.between(start, end)).group_by(Expense.category).all()
            for cat, amount in rows:
                categories.setdefault(cat, []).append(float(amount or 0))
        result = []
        for cat, values in categories.items():
            if len(values) < 3: continue
            recent = values[-3:]
            baseline = sum(recent) / len(recent)
            result.append({"category": cat, "average_recent": round(baseline, 2), "projected_monthly": round(baseline, 2), "history_points": len(values)})
        return sorted(result, key=lambda x: x["projected_monthly"], reverse=True)
