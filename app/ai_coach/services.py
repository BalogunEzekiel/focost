from .intent import IntentDetector
from .queries import FinanceQueries
from .analytics import Analytics
from .forecasting import Forecast
from .advisor import Advisor
from .recommendation import Recommendation
from .response_builder import ResponseBuilder
from .insights import Insights
from .insights_queries import InsightQueries
from .chat_history import (
    add,
    get,
    conversation,
    has_history,
    last_message,
    last_question,
    last_answer,
    save_intent,
    get_intent,
    last_intent,
    last_category,
    last_period,
    last_merchant,
    clear_intent,
    clear_session
)
import json


def respond(user_id, message):
    """
    Save assistant reply before returning it.
    """

    add(
        user_id,
        "assistant",
        message
    )

    return message
    
class AICoachService:
    """
    AI Financial Coach Service

    Responsibilities
    ----------------
    - Parse user intent
    - Route requests to the appropriate intelligence engine
    - Build conversational responses
    - Record chat history
    - Keep all database access centralized through FinanceQueries
    """

    @staticmethod
    def get_response(user, question):
        """
        Main entry point for all AI chat requests.
        """

        # ------------------------------------------
        # Save user message
        # ------------------------------------------

        add(
            user.id,
            "user",
            question
        )

        # ------------------------------------------
        # Detect intent
        # ------------------------------------------

        parsed = IntentDetector.detect(question)

        intent = parsed.get("intent")
        category = parsed.get("category")
        merchant = parsed.get("merchant")
        period = parsed.get("period")
        normalized = parsed.get(
            "normalized",
            ""
        ).lower()



        context = get_intent(user.id)

        if context:

            if parsed["intent"] == "unknown":
                parsed["intent"] = context.get("intent")

            if parsed.get("category") is None:
                parsed["category"] = context.get("category")

            if parsed.get("merchant") is None:
                parsed["merchant"] = context.get("merchant")

            if parsed.get("period") is None:
                parsed["period"] = context.get("period")

        save_intent(
            user.id,
            parsed
        )

        # =====================================================
        # INCOME ENGINE
        # =====================================================

        if intent == "income":

            # ------------------------------------------
            # Income by Category
            # ------------------------------------------

            if category:

                total = FinanceQueries.income_by_category(
                    user.id,
                    category,
                    period
                )

                return respond(user.id,
                    f"Your total {category} income"
                    f"{' for ' + period.replace('_', ' ') if period else ''} "
                    f"is ₦{total:,.2f}."
                )

            # ------------------------------------------
            # Income by Source
            # ------------------------------------------

            income_sources = [
                "salary",
                "business",
                "freelance",
                "investment",
                "bonus",
                "commission",
                "allowance",
                "interest",
                "dividend",
                "rental"
            ]

            for source in income_sources:

                if source in normalized:

                    total = FinanceQueries.income_by_source(
                        user.id,
                        source,
                        period
                    )

                    return respond(user.id,
                        f"You received ₦{total:,.2f} "
                        f"from {source.title()}"
                        f"{' for ' + period.replace('_', ' ') if period else ''}."
                    )

            # ------------------------------------------
            # Largest Income
            # ------------------------------------------

            if any(
                phrase in normalized
                for phrase in [
                    "largest income",
                    "highest income",
                    "biggest income"
                ]
            ):

                income = FinanceQueries.largest_income(
                    user.id
                )

                if not income:

                    return respond(
                        user.id,
                        "No income records found."
                    )
                source = income.source or income.category

                return respond(user.id,
                    f"Your largest income was "
                    f"₦{income.amount:,.2f} "
                    f"from {source}."
                )

            # ------------------------------------------
            # Average Income
            # ------------------------------------------

            if any(
                phrase in normalized
                for phrase in [
                    "average income",
                    "mean income"
                ]
            ):

                average = FinanceQueries.average_income(
                    user.id,
                    period
                )

                return respond(user.id,
                    f"Your average income"
                    f"{' for ' + period.replace('_', ' ') if period else ''} "
                    f"is ₦{average:,.2f}."
                )

            # ------------------------------------------
            # Income Count
            # ------------------------------------------

            if any(
                phrase in normalized
                for phrase in [
                    "income count",
                    "number of income",
                    "how many income"
                ]
            ):

                count = FinanceQueries.income_count(
                    user.id,
                    period
                )

                return respond(user.id,
                    f"You have recorded "
                    f"{count} income transaction"
                    f"{'' if count == 1 else 's'}"
                    f"{' for ' + period.replace('_', ' ') if period else ''}."
                )

            # ------------------------------------------
            # Latest Income
            # ------------------------------------------

            if any(
                phrase in normalized
                for phrase in [
                    "latest income",
                    "last income",
                    "recent income"
                ]
            ):

                income = FinanceQueries.latest_income(
                    user.id
                )

                if not income:

                    return respond(
                        user.id,
                        "No income records found."
                    )

                source = income.source or income.category

                return respond(user.id,
                    f"Your latest income was "
                    f"₦{income.amount:,.2f} "
                    f"from {source} "
                    f"on {income.received_date:%d %b %Y}."
                )

            # ------------------------------------------
            # Recurring Income
            # ------------------------------------------

            if any(
                phrase in normalized
                for phrase in [
                    "recurring income",
                    "repeat income",
                    "automatic income"
                ]
            ):

                recurring = FinanceQueries.recurring_income(
                    user.id
                )

                if not recurring:

                    return respond(
                        user.id,
                        "You have no recurring income."
                    )

                lines = []

                for item in recurring:

                    lines.append(
                        f"• {item.source or item.category}: "
                        f"₦{item.amount:,.2f}"
                    )

                return respond(user.id,
                    "Recurring Income\n\n"
                    + "\n".join(lines)
                )

            # ------------------------------------------
            # Income Categories
            # ------------------------------------------

            if any(
                phrase in normalized
                for phrase in [
                    "income categories",
                    "income by category"
                ]
            ):

                categories = FinanceQueries.income_categories(
                    user.id
                )

                if not categories:

                    return respond(
                        user.id,
                        "No income categories found."
                    )

                lines = [
                    f"• {row.category}: ₦{row.total:,.2f}"
                    for row in categories
                ]

                return respond(user.id,
                    "Income by Category\n\n"
                    + "\n".join(lines)
                )

            # ------------------------------------------
            # Income Sources
            # ------------------------------------------

            if any(
                phrase in normalized
                for phrase in [
                    "income sources",
                    "income by source",
                    "sources of income"
                ]
            ):

                sources = FinanceQueries.income_sources(
                    user.id
                )

                if not sources:

                    return respond(
                        user.id,
                        "No income sources found."
                    )

                lines = [
                    f"• {row.source}: ₦{row.total:,.2f}"
                    for row in sources
                ]

                return respond(user.id,
                    "Income Sources\n\n"
                    + "\n".join(lines)
                )

            # ------------------------------------------
            # Total Income
            # ------------------------------------------

            total = FinanceQueries.total_income(
                user.id,
                period
            )

            return respond(user.id,
                f"Your total income"
                f"{' for ' + period.replace('_', ' ') if period else ''} "
                f"is ₦{total:,.2f}."
            )

        # ==================================================
        # EXPENSE ENGINE
        # ==================================================

        if intent == "expense":

            # ------------------------------------------
            # Expense by Category
            # ------------------------------------------

            if category:

                total = FinanceQueries.expense_by_category(
                    user.id,
                    category,
                    period
                )

                return respond(user.id,
                    f"You spent ₦{total:,.2f} "
                    f"on {category}"
                    f"{' for ' + period.replace('_', ' ') if period else ''}."
                )

            # ------------------------------------------
            # Expense by Merchant
            # ------------------------------------------

            if merchant:

                total = FinanceQueries.expense_by_merchant(
                    user.id,
                    merchant,
                    period
                )

                return respond(user.id,
                    f"You spent ₦{total:,.2f} "
                    f"with {merchant}"
                    f"{' for ' + period.replace('_', ' ') if period else ''}."
                )

            # ------------------------------------------
            # Expense by Payment Method
            # ------------------------------------------

            payment_methods = [
                "cash",
                "card",
                "bank transfer",
                "transfer",
                "pos",
                "cheque",
                "mobile money"
            ]

            for method in payment_methods:

                if method in normalized:

                    total = FinanceQueries.expense_by_payment_method(
                        user.id,
                        method.title(),
                        period
                    )

                    return respond(user.id,
                        f"You spent ₦{total:,.2f} "
                        f"using {method.title()}"
                        f"{' for ' + period.replace('_', ' ') if period else ''}."
                    )

            # ------------------------------------------
            # Expense by Description
            # ------------------------------------------

            if (
                "for " in normalized
                or "description" in normalized
            ):

                keyword = None

                if "for " in normalized:

                    keyword = normalized.split(
                        "for ",
                        1
                    )[1].strip()

                elif "description" in normalized:

                    keyword = normalized.replace(
                        "description",
                        ""
                    ).strip()

                if keyword:

                    total = FinanceQueries.expense_by_description(
                        user.id,
                        keyword,
                        period
                    )

                    return respond(user.id,
                        f"You spent ₦{total:,.2f} "
                        f"on expenses matching "
                        f"'{keyword}'."
                    )

            # ------------------------------------------
            # Largest Expense
            # ------------------------------------------

            if any(

                phrase in normalized

                for phrase in [

                    "largest expense",

                    "highest expense",

                    "biggest expense"

                ]

            ):

                expense = FinanceQueries.largest_expense(
                    user.id
                )

                if not expense:

                    return respond(
                        user.id,
                        "No expenses found."
                    )

                return respond(user.id,
                    f"Your largest expense was "
                    f"₦{expense.amount:,.2f} "
                    f"for {expense.category}."
                )

            # ------------------------------------------
            # Latest Expense
            # ------------------------------------------

            if any(

                phrase in normalized

                for phrase in [

                    "latest expense",

                    "last expense",

                    "recent expense"

                ]

            ):

                expense = FinanceQueries.latest_expense(
                    user.id
                )

                if not expense:

                    return respond(
                        user.id,
                        "No expenses found."
                    )

                return respond(user.id,
                    f"Your latest expense was "
                    f"₦{expense.amount:,.2f} "
                    f"for {expense.category} "
                    f"on {expense.expense_date:%d %b %Y}."
                )

            # ------------------------------------------
            # Average Expense
            # ------------------------------------------

            if any(

                phrase in normalized

                for phrase in [

                    "average expense",

                    "mean expense"

                ]

            ):

                average = FinanceQueries.average_expense(
                    user.id,
                    period
                )

                return respond(user.id,
                    f"Your average expense"
                    f"{' for ' + period.replace('_', ' ') if period else ''} "
                    f"is ₦{average:,.2f}."
                )

            # ------------------------------------------
            # Expense Count
            # ------------------------------------------

            if any(

                phrase in normalized

                for phrase in [

                    "expense count",

                    "number of expenses",

                    "how many expenses"

                ]

            ):

                count = FinanceQueries.expense_count(
                    user.id,
                    period
                )

                return respond(user.id,
                    f"You have "
                    f"{count} expense transaction"
                    f"{'' if count == 1 else 's'}"
                    f"{' for ' + period.replace('_', ' ') if period else ''}."
                )

            # ------------------------------------------
            # Recurring Expenses
            # ------------------------------------------

            if any(

                phrase in normalized

                for phrase in [

                    "recurring expense",

                    "recurring expenses"

                ]

            ):

                expenses = FinanceQueries.recurring_expenses(
                    user.id
                )

                if not expenses:

                    return respond(
                        user.id,
                        "No recurring expenses found."
                    )

                lines = []

                for expense in expenses:

                    lines.append(
                        f"• {expense.category}: "
                        f"₦{expense.amount:,.2f}"
                    )

                return respond(user.id,
                    "Recurring Expenses\n\n"
                    + "\n".join(lines)
                )

            # ------------------------------------------
            # Expense Categories
            # ------------------------------------------

            if any(

                phrase in normalized

                for phrase in [

                    "expense categories",

                    "expenses by category"

                ]

            ):

                categories = FinanceQueries.expense_categories(
                    user.id
                )

                if not categories:

                    return respond(
                        user.id,
                        "No expense categories found."
                    )

                lines = [

                    f"• {row.category}: ₦{row.total:,.2f}"

                    for row in categories

                ]

                return respond(user.id,
                    "Expense Categories\n\n"
                    + "\n".join(lines)
                )

            # ------------------------------------------
            # Top Categories
            # ------------------------------------------

            if any(

                phrase in normalized

                for phrase in [

                    "top category",

                    "highest category",

                    "largest category"

                ]

            ):

                categories = FinanceQueries.top_categories(
                    user.id,
                    period
                )

                if not categories:

                    return respond(
                        user.id,
                        "No expense categories found."
                    )

                top = categories[0]

                return respond(user.id,
                    f"Your highest spending category is "
                    f"{top.category} "
                    f"with ₦{top.total:,.2f}."
                )

            # ------------------------------------------
            # Top Merchants
            # ------------------------------------------

            if any(

                phrase in normalized

                for phrase in [

                    "top merchant",

                    "highest merchant",

                    "largest merchant"

                ]

            ):

                merchants = FinanceQueries.top_merchants(
                    user.id,
                    period
                )

                if not merchants:

                    return respond(
                        user.id,
                        "No merchant data found."
                    )

                top = merchants[0]

                return respond(user.id,
                    f"You spend the most with "
                    f"{top.merchant} "
                    f"(₦{top.total:,.2f})."
                )

            # ------------------------------------------
            # Top 5 Expenses
            # ------------------------------------------

            if any(

                phrase in normalized

                for phrase in [

                    "top 5",

                    "top five",

                    "highest 5",

                    "largest 5",

                    "biggest 5"

                ]

            ):

                expenses = FinanceQueries.top_expenses(
                    user.id
                )

                if not expenses:

                    return respond(
                        user.id,
                        "No expenses found."
                    )

                lines = []

                for i, expense in enumerate(
                    expenses,
                    start=1
                ):

                    lines.append(
                        f"{i}. {expense.category} - ₦{expense.amount:,.2f}"
                    )

                return respond(user.id,
                    "Top 5 Expenses\n\n"
                    + "\n".join(lines)
                )

            # ------------------------------------------
            # Total Expenses
            # ------------------------------------------

            total = FinanceQueries.total_expense(
                user.id,
                period
            )

            return respond(user.id,
                f"Your total expenses"
                f"{' for ' + period.replace('_', ' ') if period else ''} "
                f"are ₦{total:,.2f}."
            )

        # ==================================================
        # STEP 4 — BALANCE & CASH FLOW ENGINE
        # ==================================================

        if intent == "balance":

            income = FinanceQueries.total_income(
                user.id,
                period
            )

            expense = FinanceQueries.total_expense(
                user.id,
                period
            )

            balance = income - expense

            return respond(

                user.id,

                "[BALANCE_CARD]" +

                json.dumps({

                    "income": income,

                    "expense": expense,

                    "balance": balance

                })

            )

        # --------------------------------------------------
        # Cash Flow
        # --------------------------------------------------

        if (
            "cash flow" in normalized
            or "cashflow" in normalized
        ):

            flow = FinanceQueries.monthly_cash_flow(
                user.id
            )

            return respond(user.id,
                "Monthly Cash Flow\n\n"
                f"Income: ₦{flow['income']:,.2f}\n"
                f"Expenses: ₦{flow['expense']:,.2f}\n"
                f"Net Cash Flow: ₦{flow['balance']:,.2f}"
            )

        # --------------------------------------------------
        # Cash Flow Status
        # --------------------------------------------------

        if (
            "cash flow status" in normalized
            or "cashflow status" in normalized
            or "is my cash flow positive" in normalized
            or "is my cash flow negative" in normalized
        ):

            status = FinanceQueries.cash_flow_status(
                user.id
            )

            return respond(user.id,
                f"Your current cash flow is **{status.upper()}**."
            )

        # --------------------------------------------------
        # Income vs Expense
        # --------------------------------------------------

        if (
            "income vs expense" in normalized
            or "income versus expense" in normalized
            or "compare income and expenses" in normalized
        ):

            income = FinanceQueries.total_income(
                user.id,
                period
            )

            expense = FinanceQueries.total_expense(
                user.id,
                period
            )

            difference = income - expense

            return respond(user.id,
                "Income vs Expenses\n\n"
                f"Income: ₦{income:,.2f}\n"
                f"Expenses: ₦{expense:,.2f}\n"
                f"Difference: ₦{difference:,.2f}"
            )

        # --------------------------------------------------
        # Savings
        # --------------------------------------------------

        if intent == "savings":

            income = FinanceQueries.total_income(
                user.id,
                period
            )

            expense = FinanceQueries.total_expense(
                user.id,
                period
            )

            savings = income - expense

            if income > 0:

                rate = round(
                    (savings / income) * 100,
                    2
                )

            else:

                rate = 0

            return respond(user.id,
                "Savings Summary\n\n"
                f"Saved: ₦{savings:,.2f}\n"
                f"Savings Rate: {rate}%"
            )

        # --------------------------------------------------
        # Expense / Income Ratio
        # --------------------------------------------------

        if (
            "expense ratio" in normalized
            or "expense to income ratio" in normalized
            or "income ratio" in normalized
        ):

            ratio = FinanceQueries.expense_income_ratio(
                user.id
            )

            return respond(user.id,
                f"Your Expense-to-Income Ratio is {ratio}%."
            )

        # ==================================================
        # BUDGET INTELLIGENCE
        # ==================================================

        if intent == "budget":

            # -----------------------------------------
            # Budget for a specific category
            # -----------------------------------------

            if category:

                budget = FinanceQueries.budget_by_category(
                    user.id,
                    category
                )

                if not budget:

                    return respond(user.id,
                        f"You don't have a budget for "
                        f"{category}."
                    )

                spent = FinanceQueries.budget_usage(
                    user.id,
                    category
                )

                remaining = FinanceQueries.budget_remaining(
                    user.id,
                    category
                )

                percentage = (
                    FinanceQueries.budget_percentage_used(
                        user.id,
                        category
                    )
                )

                overrun = FinanceQueries.budget_overrun(
                    user.id,
                    category
                )

                lines = [

                    f"Budget Category: {category}",

                    f"Budget: ₦{budget.amount:,.2f}",

                    f"Spent: ₦{spent:,.2f}",

                    f"Remaining: ₦{remaining:,.2f}",

                    f"Used: {percentage}%"

                ]

                if overrun > 0:

                    lines.append(
                        f"Over Budget: ₦{overrun:,.2f}"
                    )

                return respond(
                    user.id, "\n".join(lines)
                )

            # -----------------------------------------
            # Overall Budget Summary
            # -----------------------------------------

            if (
                "overall" in normalized
                or "summary" in normalized
                or "total budget" in normalized
            ):

                total = FinanceQueries.total_budget(
                    user.id
                )

                used = FinanceQueries.total_budget_used(
                    user.id
                )

                remaining = (
                    FinanceQueries.total_budget_remaining(
                        user.id
                    )
                )

                percentage = (
                    FinanceQueries.overall_budget_percentage(
                        user.id
                    )
                )

                return respond(user.id,
                    f"Total Budget: ₦{total:,.2f}\n"
                    f"Used: ₦{used:,.2f}\n"
                    f"Remaining: ₦{remaining:,.2f}\n"
                    f"Usage: {percentage}%"
                )

            # -----------------------------------------
            # Exceeded Budgets
            # -----------------------------------------

            if (
                "exceeded" in normalized
                or "over budget" in normalized
            ):

                exceeded = (
                    FinanceQueries.exceeded_budgets(
                        user.id
                    )
                )

                if not exceeded:

                    return respond(user.id,
                        "Excellent! None of your budgets "
                        "have been exceeded."
                    )

                lines = ["Exceeded Budgets:\n"]

                for item in exceeded:

                    lines.append(

                        f"• {item['category']} "

                        f"(₦{item['overrun']:,.2f} over)"

                    )

                return respond(user.id, "\n".join(lines))

            # -----------------------------------------
            # Budget Closest To Limit
            # -----------------------------------------

            if (
                "closest" in normalized
                or "near limit" in normalized
            ):

                budget = (
                    FinanceQueries.nearest_budget_limit(
                        user.id
                    )
                )

                if not budget:

                    return respond(user.id,
                        "No active budgets found."
                    )

                return respond(user.id,

                    f"{budget['category']} is closest "

                    f"to its limit.\n"

                    f"Used: {budget['percentage']}%"

                )

            # -----------------------------------------
            # Healthiest Budget
            # -----------------------------------------

            if (
                "healthiest" in normalized
                or "best budget" in normalized
            ):

                budget = (
                    FinanceQueries.healthiest_budget(
                        user.id
                    )
                )

                if not budget:

                    return respond(user.id,
                        "No active budgets found."
                    )

                return respond(user.id,

                    f"Your healthiest budget is "

                    f"{budget['category']}.\n"

                    f"Used: {budget['percentage']}%"

                )

            # -----------------------------------------
            # Active Budgets
            # -----------------------------------------

            if (
                "active" in normalized
            ):

                budgets = FinanceQueries.active_budgets(
                    user.id
                )

                if not budgets:

                    return respond(user.id,
                        "You don't have any active budgets."
                    )

                lines = ["Active Budgets:\n"]

                for budget in budgets:

                    lines.append(

                        f"• {budget.category} "

                        f"(₦{budget.amount:,.2f})"

                    )

                return respond(user.id, "\n".join(lines))

            # -----------------------------------------
            # Expiring Soon
            # -----------------------------------------

            if (
                "expiring" in normalized
                or "expire soon" in normalized
            ):

                budgets = (
                    FinanceQueries.budgets_expiring_soon(
                        user.id
                    )
                )

                if not budgets:

                    return respond(user.id,
                        "No budgets are expiring soon."
                    )

                lines = ["Budgets Expiring Soon:\n"]

                for budget in budgets:

                    lines.append(

                        f"• {budget.category}"

                        f" ({budget.end_date})"

                    )

                return respond(
                    user.id, "\n".join(lines)
                )

            # -----------------------------------------
            # Full Budget Report
            # -----------------------------------------

            report = FinanceQueries.all_budget_status(
                user.id
            )

            return respond(
                user.id,
                ResponseBuilder.budget_report(report)
            )

        # ==================================================
        # GOAL INTELLIGENCE
        # ==================================================

        if intent == "goal":

            # -----------------------------------------
            # Goal Summary
            # -----------------------------------------

            if (
                "summary" in normalized
                or "overview" in normalized
                or normalized.strip() in [
                    "goal",
                    "goals",
                    "my goals"
                ]
            ):

                summary = FinanceQueries.goal_summary(
                    user.id
                )

                return respond(
                    user.id,
                    ResponseBuilder.goal_summary(summary)
                )

            # -----------------------------------------
            # Active Goals
            # -----------------------------------------

            if "active" in normalized:

                goals = FinanceQueries.active_goals(
                    user.id
                )

                if not goals:

                    return respond(user.id,
                        "You don't have any active financial goals."
                    )

                lines = ["Active Goals\n"]

                for goal in goals:

                    pct = FinanceQueries.goal_percentage(goal)

                    lines.append(
                        f"• {goal.title} ({pct:.2f}% complete)"
                    )

                return respond(user.id, "\n".join(lines))

            # -----------------------------------------
            # Completed Goals
            # -----------------------------------------

            if (
                "completed" in normalized
                or "finished" in normalized
            ):

                goals = FinanceQueries.completed_goals(
                    user.id
                )

                if not goals:

                    return respond(user.id,
                        "You haven't completed any goals yet."
                    )

                lines = ["Completed Goals\n"]

                for goal in goals:

                    lines.append(
                        f"• {goal.title}"
                    )

                return respond(user.id, "\n".join(lines))

            # -----------------------------------------
            # Closest Goal
            # -----------------------------------------

            if (
                "closest" in normalized
                or "nearest" in normalized
                or "almost completed" in normalized
            ):

                goal = FinanceQueries.closest_goal(
                    user.id
                )

                if not goal:

                    return respond(user.id,
                        "No active goals found."
                    )

                progress = FinanceQueries.goal_progress(
                    goal
                )

                return respond(user.id,
                    f"Your closest goal is '{goal.title}'.\n"
                    f"Progress: {progress['percentage']}%\n"
                    f"Remaining: ₦{progress['remaining']:,.2f}"
                )

            # -----------------------------------------
            # Furthest Goal
            # -----------------------------------------

            if (
                "furthest" in normalized
                or "least progress" in normalized
            ):

                goal = FinanceQueries.furthest_goal(
                    user.id
                )

                if not goal:

                    return respond(user.id,
                        "No active goals found."
                    )

                progress = FinanceQueries.goal_progress(
                    goal
                )

                return respond(user.id,
                    f"Your furthest goal is '{goal.title}'.\n"
                    f"Progress: {progress['percentage']}%"
                )

            # -----------------------------------------
            # Highest Priority Goal
            # -----------------------------------------

            if (
                "priority" in normalized
                or "important goal" in normalized
            ):

                goal = FinanceQueries.highest_priority_goal(
                    user.id
                )

                if not goal:

                    return respond(user.id,
                        "No active goals found."
                    )

                return respond(user.id,
                    f"Highest Priority Goal\n\n"
                    f"{goal.title}\n"
                    f"Priority: {goal.priority}"
                )

            # -----------------------------------------
            # Highest Contribution
            # -----------------------------------------

            if (
                "highest contribution" in normalized
                or "most contributed" in normalized
            ):

                goal = FinanceQueries.highest_contributed_goal(
                    user.id
                )

                if not goal:

                    return respond(user.id,
                        "No goals found."
                    )

                amount = FinanceQueries.goal_contribution(
                    goal.id
                )

                return respond(user.id,
                    f"You've contributed the most to "
                    f"'{goal.title}'.\n"
                    f"Amount: ₦{amount:,.2f}"
                )

            # -----------------------------------------
            # Due Soon
            # -----------------------------------------

            if (
                "due soon" in normalized
                or "upcoming" in normalized
            ):

                goals = FinanceQueries.goals_due_soon(
                    user.id
                )

                if not goals:

                    return respond(user.id,
                        "No goals are due soon."
                    )

                lines = ["Goals Due Soon\n"]

                for goal in goals:

                    lines.append(
                        f"• {goal.title} ({goal.target_date})"
                    )

                return respond(user.id, "\n".join(lines))

            # -----------------------------------------
            # Overdue Goals
            # -----------------------------------------

            if (
                "overdue" in normalized
                or "missed" in normalized
            ):

                goals = FinanceQueries.overdue_goals(
                    user.id
                )

                if not goals:

                    return respond(user.id,
                        "No overdue goals."
                    )

                lines = ["Overdue Goals\n"]

                for goal in goals:

                    lines.append(
                        f"• {goal.title} ({goal.target_date})"
                    )

                return respond(user.id, "\n".join(lines))

            # -----------------------------------------
            # Monthly Required Contribution
            # -----------------------------------------

            if (
                "monthly" in normalized
                and "required" in normalized
            ):

                goal = FinanceQueries.closest_goal(
                    user.id
                )

                if not goal:

                    return respond(user.id,
                        "No active goals found."
                    )

                amount = FinanceQueries.monthly_required(
                    goal
                )

                return respond(user.id,
                    f"To reach '{goal.title}', "
                    f"you should save approximately "
                    f"₦{amount:,.2f} per month."
                )

            # -----------------------------------------
            # Detailed Goal Progress
            # -----------------------------------------

            if (
                "progress" in normalized
                or "status" in normalized
            ):

                goals = FinanceQueries.active_goals(
                    user.id
                )

                if not goals:

                    return respond(user.id,
                        "No active goals."
                    )

                lines = ["Goal Progress\n"]

                for goal in goals:

                    progress = FinanceQueries.goal_progress(
                        goal
                    )

                    lines.append(
                        f"\n{goal.title}"
                    )

                    lines.append(
                        f"Target: ₦{goal.target_amount:,.2f}"
                    )

                    lines.append(
                        f"Saved: ₦{progress['contributed']:,.2f}"
                    )

                    lines.append(
                        f"Remaining: ₦{progress['remaining']:,.2f}"
                    )

                    lines.append(
                        f"Progress: {progress['percentage']}%"
                    )

                return respond(user.id, "\n".join(lines))

            # -----------------------------------------
            # Default Goal Summary
            # -----------------------------------------

            summary = FinanceQueries.goal_summary(
                user.id
            )

            return respond(
                user.id,
                ResponseBuilder.goal_summary(summary)
            )

        # ==================================================
        # FINANCIAL HEALTH ENGINE
        # ==================================================

        if (
            intent == "financial_health"
            or "health" in normalized
            or "financial health" in normalized
            or "financial score" in normalized
            or "health score" in normalized
            or "score" in normalized
            or "grade" in normalized
        ):

            report = FinanceQueries.financial_report(
                user.id
            )

            # -----------------------------------------
            # Grade
            # -----------------------------------------

            if "grade" in normalized:

                return respond(user.id,
                    f"Your financial grade is "
                    f"{report['grade']}."
                )

            # -----------------------------------------
            # Status
            # -----------------------------------------

            if "status" in normalized:

                return respond(user.id,
                    f"Your financial status is "
                    f"{report['status']}."
                )

            # -----------------------------------------
            # Recommendations
            # -----------------------------------------

            if (
                "recommend" in normalized
                or "improve" in normalized
                or "advice" in normalized
            ):

                lines = [
                    "Recommendations\n"
                ]

                for item in report["recommendations"]:

                    lines.append(
                        f"• {item}"
                    )

                return respond(user.id, "\n".join(lines))

            # -----------------------------------------
            # Savings Score
            # -----------------------------------------

            if "savings" in normalized:

                return respond(user.id,
                    f"Your Savings Score is "
                    f"{report['breakdown']['savings']}/25."
                )

            # -----------------------------------------
            # Budget Score
            # -----------------------------------------

            if "budget" in normalized:

                return respond(user.id,
                    f"Your Budget Score is "
                    f"{report['breakdown']['budget']}/25."
                )

            # -----------------------------------------
            # Goal Score
            # -----------------------------------------

            if (
                "goal" in normalized
                or "goals" in normalized
            ):

                return respond(user.id,
                    f"Your Goal Score is "
                    f"{report['breakdown']['goals']}/25."
                )

            # -----------------------------------------
            # Cash Flow Score
            # -----------------------------------------

            if (
                "cash flow" in normalized
                or "cashflow" in normalized
            ):

                return respond(user.id,
                    f"Your Cash Flow Score is "
                    f"{report['breakdown']['cashflow']}/25."
                )

            # -----------------------------------------
            # Full Report
            # -----------------------------------------

            return respond(
                user.id,
                ResponseBuilder.financial_health(report)
            )

        # ==================================================
        # SPENDING PATTERN INTELLIGENCE
        # ==================================================

        if intent == "spending_pattern":

            # -----------------------------------------
            # Expense Trend
            # -----------------------------------------

            if (
                "trend" in normalized
                or "increasing" in normalized
                or "decreasing" in normalized
                or "history" in normalized
            ):

                trend = FinanceQueries.expense_trend(
                    user.id
                )

                if not trend:

                    return respond(user.id,
                        "There isn't enough expense history "
                        "to determine your spending trend."
                    )

                return respond(user.id,
                    f"Your expenses have "
                    f"{trend['direction']} by "
                    f"₦{trend['difference']:,.2f} "
                    f"({trend['percent']}%).\n\n"
                    f"Last Month: ₦{trend['previous']:,.2f}\n"
                    f"This Month: ₦{trend['current']:,.2f}"
                )

            # -----------------------------------------
            # Monthly Expense History
            # -----------------------------------------

            if (
                "history" in normalized
                or "last 6 months" in normalized
                or "monthly history" in normalized
            ):

                history = FinanceQueries.monthly_expense_history(
                    user.id
                )

                if not history:

                    return respond(user.id, "No expense history found.")

                lines = ["Monthly Expense History\n"]

                for item in history:

                    lines.append(
                        f"{item['month']:02}/{item['year']} : "
                        f"₦{item['total']:,.2f}"
                    )

                return respond(user.id, "\n".join(lines))

            # -----------------------------------------
            # Top Spending Categories
            # -----------------------------------------

            if (
                "category" in normalized
                or "categories" in normalized
            ):

                categories = FinanceQueries.top_categories(
                    user.id,
                    period
                )

                if not categories:

                    return respond(user.id, "No spending categories found.")

                lines = ["Top Spending Categories\n"]

                for category_name, total in categories:

                    lines.append(
                        f"• {category_name}: ₦{total:,.2f}"
                    )

                return respond(
                    user.id, "\n".join(lines)
                )

            # -----------------------------------------
            # Highest Spending Category
            # -----------------------------------------

            if (
                "highest category" in normalized
                or "largest category" in normalized
                or "most expensive category" in normalized
                or "top category" in normalized
            ):

                categories = FinanceQueries.top_categories(
                    user.id,
                    period
                )

                if not categories:

                    return respond(user.id, "No spending categories found.")

                category_name, total = categories[0]

                return respond(user.id,
                    f"Your highest spending category is "
                    f"{category_name} "
                    f"(₦{total:,.2f})."
                )

            # -----------------------------------------
            # Top Merchants
            # -----------------------------------------

            if (
                "merchant" in normalized
                or "vendor" in normalized
                or "store" in normalized
                or "shop" in normalized
            ):

                merchants = FinanceQueries.top_merchants(
                    user.id,
                    period
                )

                if not merchants:

                    return respond(user.id, "No merchant data found.")

                lines = ["Top Merchants\n"]

                for merchant_name, total in merchants:

                    lines.append(
                        f"• {merchant_name}: ₦{total:,.2f}"
                    )

                return respond(user.id, "\n".join(lines))

            # -----------------------------------------
            # Biggest Merchant
            # -----------------------------------------

            if (
                "most with" in normalized
                or "highest merchant" in normalized
                or "biggest merchant" in normalized
            ):

                merchant = FinanceQueries.highest_merchant(
                    user.id,
                    period
                )

                if not merchant:

                    return respond(user.id, "No merchant information found.")

                return respond(user.id,
                    f"You spend the most with "
                    f"{merchant.merchant} "
                    f"(₦{merchant.total:,.2f})."
                )

            # -----------------------------------------
            # Top Expenses
            # -----------------------------------------

            expenses = FinanceQueries.top_expenses(
                user.id
            )

            if not expenses:

                return respond(user.id, "No expense records found.")

            lines = ["Top Expenses\n"]

            for i, expense in enumerate(expenses, start=1):

                lines.append(
                    f"{i}. "
                    f"{expense.category} "
                    f"₦{expense.amount:,.2f}"
                )

            return respond(user.id, "\n".join(lines))

        # ==================================================
        # FORECASTING & PREDICTION INTELLIGENCE
        # ==================================================

        if intent == "forecast":

            # -----------------------------------------
            # Cash Flow
            # -----------------------------------------

            if (
                "cash flow" in normalized
                or "cashflow" in normalized
            ):

                flow = FinanceQueries.monthly_cash_flow(
                    user.id
                )

                status = FinanceQueries.cash_flow_status(
                    user.id
                )

                return respond(user.id,
                    f"Monthly Cash Flow\n\n"
                    f"Income: ₦{flow['income']:,.2f}\n"
                    f"Expenses: ₦{flow['expense']:,.2f}\n"
                    f"Balance: ₦{flow['balance']:,.2f}\n\n"
                    f"Status: {status.title()}"
                )

            # -----------------------------------------
            # Best Income Month
            # -----------------------------------------

            if (
                "best income" in normalized
                or "highest income month" in normalized
            ):

                month = FinanceQueries.best_income_month(
                    user.id
                )

                if not month:

                    return respond(user.id, "No income history found.")

                return respond(user.id,
                    f"Your best income month is "
                    f"Month {int(month.month)} "
                    f"with income of ₦{month.total:,.2f}."
                )

            # -----------------------------------------
            # Highest Expense Month
            # -----------------------------------------

            if (
                "highest expense month" in normalized
                or "worst expense month" in normalized
            ):

                month = FinanceQueries.highest_expense_month(
                    user.id
                )

                if not month:

                    return respond(user.id, "No expense history found.")

                return respond(user.id,
                    f"Your highest spending month is "
                    f"Month {int(month.month)} "
                    f"with expenses of ₦{month.total:,.2f}."
                )

            # -----------------------------------------
            # Best Savings Month
            # -----------------------------------------

            if (
                "best savings" in normalized
                or "highest savings" in normalized
            ):

                month = FinanceQueries.best_savings_month(
                    user.id
                )

                if not month:

                    return respond(user.id, "No savings history found.")

                return respond(user.id,
                    f"Your best savings month is "
                    f"Month {month['month']} "
                    f"with savings of ₦{month['savings']:,.2f}."
                )

            # -----------------------------------------
            # Worst Savings Month
            # -----------------------------------------

            if (
                "worst savings" in normalized
                or "lowest savings" in normalized
            ):

                month = FinanceQueries.worst_savings_month(
                    user.id
                )

                if not month:

                    return respond(user.id, "No savings history found.")

                return respond(user.id,
                    f"Your worst savings month is "
                    f"Month {month['month']} "
                    f"with savings of ₦{month['savings']:,.2f}."
                )

            # -----------------------------------------
            # Average Monthly Income
            # -----------------------------------------

            if (
                "average income" in normalized
                or "monthly income average" in normalized
            ):

                avg = FinanceQueries.average_monthly_income(
                    user.id
                )

                return respond(user.id,
                    f"Your average monthly income is "
                    f"₦{avg:,.2f}."
                )

            # -----------------------------------------
            # Average Monthly Expense
            # -----------------------------------------

            if (
                "average expense" in normalized
                or "monthly expense average" in normalized
            ):

                avg = FinanceQueries.average_monthly_expense(
                    user.id
                )

                return respond(user.id,
                    f"Your average monthly expense is "
                    f"₦{avg:,.2f}."
                )

            # -----------------------------------------
            # Expense / Income Ratio
            # -----------------------------------------

            if (
                "expense ratio" in normalized
                or "expense income ratio" in normalized
                or "income ratio" in normalized
            ):

                ratio = FinanceQueries.expense_income_ratio(
                    user.id
                )

                return respond(user.id,
                    f"Your Expense-to-Income ratio is "
                    f"{ratio}%."
                )

            # -----------------------------------------
            # Monthly Savings History
            # -----------------------------------------

            if (
                "savings history" in normalized
                or "monthly savings" in normalized
            ):

                history = FinanceQueries.monthly_savings(
                    user.id
                )

                if not history:

                    return respond(user.id, "No savings history found.")

                lines = ["Monthly Savings\n"]

                for row in history:

                    lines.append(
                        f"Month {row['month']}: "
                        f"₦{row['savings']:,.2f}"
                    )

                return respond(user.id, "\n".join(lines))

            # -----------------------------------------
            # Default Forecast
            # -----------------------------------------

            return respond(
                user.id,
                Forecast.generate(user.id)
            )

        # ==================================================
        # RECOMMENDATION INTELLIGENCE
        # ==================================================

        if intent == "reduce":

            # -----------------------------------------
            # General Spending Reduction
            # -----------------------------------------

            if (
                "reduce" in normalized
                or "cut spending" in normalized
                or "reduce spending" in normalized
                or "save money" in normalized
            ):

                return respond(user.id, Recommendation.reduce_spending(
                    user.id
                ))

            # -----------------------------------------
            # Budget Recommendations
            # -----------------------------------------

            if "budget" in normalized:

                report = FinanceQueries.exceeded_budgets(
                    user.id
                )

                if not report:

                    return respond(user.id,
                        "Excellent. You are currently staying "
                        "within all your budgets."
                    )

                lines = [
                    "Budget Recommendations\n"
                ]

                for item in report:

                    lines.append(
                        f"• Reduce spending on "
                        f"{item['category']} "
                        f"(Over by ₦{item['overrun']:,.2f})"
                    )

                return respond(
                    user.id, "\n".join(lines)
                )

            # -----------------------------------------
            # Financial Health Recommendations
            # -----------------------------------------

            if (
                "health" in normalized
                or "financial health" in normalized
            ):

                report = FinanceQueries.financial_report(
                    user.id
                )

                return respond(
                    user.id,
                    "\n".join(report["recommendations"])
                )

            # -----------------------------------------
            # Goal Recommendations
            # -----------------------------------------

            if "goal" in normalized:

                goal = FinanceQueries.closest_goal(
                    user.id
                )

                if not goal:

                    return respond(user.id,
                        "You currently have no active goals."
                    )

                monthly = FinanceQueries.monthly_required(
                    goal
                )

                return respond(user.id,
                    f"To reach '{goal.title}', "
                    f"consider saving "
                    f"₦{monthly:,.2f} every month."
                )

            # -----------------------------------------
            # Cash Flow Recommendations
            # -----------------------------------------

            if (
                "cash flow" in normalized
                or "cashflow" in normalized
            ):

                status = FinanceQueries.cash_flow_status(
                    user.id
                )

                if status == "positive":

                    return respond(user.id,
                        "Your cash flow is positive. "
                        "Consider investing or increasing "
                        "your savings."
                    )

                if status == "negative":

                    return respond(user.id,
                        "Your expenses exceed your income. "
                        "Reduce discretionary spending "
                        "or increase income."
                    )

                return respond(user.id,
                    "Your cash flow is balanced. "
                    "Maintain your current spending habits."
                )

            # -----------------------------------------
            # Savings Recommendations
            # -----------------------------------------

            if "saving" in normalized:

                report = FinanceQueries.financial_report(
                    user.id
                )

                if report["breakdown"]["savings"] >= 20:

                    return respond(user.id,
                        "Your savings performance is good. "
                        "Continue maintaining your savings rate."
                    )

                return respond(user.id,
                    "Increase your monthly savings before "
                    "taking on additional expenses."
                )

            # -----------------------------------------
            # Default Recommendation Engine
            # -----------------------------------------

            return respond(
                user.id,
                Recommendation.generate(user.id)
            )