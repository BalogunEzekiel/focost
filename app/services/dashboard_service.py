from datetime import date, datetime, timedelta
from sqlalchemy import func, extract, or_
import calendar
from flask import request

from app.extensions import db
from app.models.income import Income
from app.models.expense import Expense
from app.models.budget import Budget
from app.models.goal import Goal
from app.models.goal_contribution import GoalContribution
from app.services.notification_service import NotificationService

class DashboardService:

    """

    Central Intelligent Dashboard Service

    This service builds every section of the dashboard.

    All dashboard templates should obtain their data

    exclusively through this service.

    """

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

        # -------------------------------------------------------
        # AI Confidence
        # -------------------------------------------------------

        dashboard["ai_confidence"] = min(
            100,
            40
            + len(transactions) * 2
            + len(budgets) * 5
            + len(goal_progress) * 5
        )

        return dashboard

    # ==========================================================
    # SUMMARY
    # ==========================================================

    @staticmethod
    def build_summary(user_id):

        raise NotImplementedError

    # ==========================================================
    # KPI CARDS
    # ==========================================================

    @staticmethod
    def build_kpis(user_id):

        raise NotImplementedError

    # ==========================================================
    # AI FINANCIAL INSIGHT
    # ==========================================================

    @staticmethod
    def build_ai_financial_insight(user_id):

        raise NotImplementedError
    
    # ==========================================================
    # AI SUMMARY
    # ==========================================================

    @staticmethod
    def build_ai_summary(user_id):

        raise NotImplementedError

    # ==========================================================
    # SMART INSIGHTS
    # ==========================================================

    @staticmethod
    def build_insights(user_id):

        raise NotImplementedError

    # ==========================================================
    # BUDGET WARNING
    # ==========================================================

    @staticmethod
    def build_budget_warning(user_id):

        raise NotImplementedError

    # ==========================================================
    # GOAL PROGRESS
    # ==========================================================

    @staticmethod
    def build_goal_progress(user_id):

        raise NotImplementedError

    # ==========================================================
    # FINANCIAL HEALTH
    # ==========================================================

    @staticmethod
    def build_financial_health(user_id):

        raise NotImplementedError

    # ==========================================================
    # AI RECOMMENDATIONS
    # ==========================================================

    @staticmethod
    def build_recommendations(user_id):

        raise NotImplementedError

    # ==========================================================
    # DAILY BRIEF
    # ==========================================================

    @staticmethod
    def build_daily_brief(user_id):

        raise NotImplementedError

    # ==========================================================
    # RECENT TRANSACTIONS
    # ==========================================================

    @staticmethod
    def build_recent_transactions(user_id):

        raise NotImplementedError
    
    # ==========================================================
    # PERSONALIZATION
    # ==========================================================

    @staticmethod
    def build_personalization(user_id):

        raise NotImplementedError

    # ==========================================================
    # CHARTS
    # ==========================================================

    @staticmethod
    def build_charts(user_id):

        raise NotImplementedError

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

            db.session.query(

                func.coalesce(func.sum(Expense.amount), 0)
            )
            .filter(
                Expense.user_id == user_id,
                Expense.expense_date.between(start, end)
            )
            .filter(
                Expense.user_id == user_id,
                Expense.expense_date.between(start, end)
            )
            .scalar()
        )

        # Lifetime balance (all-time savings)
        balance = (
            db.session.query(
                func.coalesce(func.sum(Income.amount), 0)
            )
            .filter(Income.user_id == user_id)
            .scalar()
            -
            db.session.query(
                func.coalesce(func.sum(Expense.amount), 0)
            )
            .filter(Expense.user_id == user_id)
            .scalar()
        )

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
