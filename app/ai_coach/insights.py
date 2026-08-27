from .insights_queries import InsightQueries


class Insights:
    """
    Advanced financial insight engine.

    Handles questions that are more analytical than simple totals.

    Examples:

    - What category increased the most?
    - Show my top spending category.
    - Which merchant do I spend the most with?
    - Compare this month with last month.
    - What is my spending trend?
    """

    @staticmethod
    def answer(user_id, parsed):

        intent = parsed.get("intent")
        period = parsed.get("period")
        normalized = parsed.get("normalized", "")

        # ==========================================
        # EXPENSE TREND
        # ==========================================

        if (
            "trend" in normalized
            or "expense trend" in normalized
            or "spending trend" in normalized
        ):

            trend = InsightQueries.expense_trend(
                user_id
            )

            if not trend:
                return "Not enough data to determine your spending trend."

            return (
                f"Your expenses have "
                f"{trend['direction']} by "
                f"₦{trend['difference']:,.2f} "
                f"({trend['percent']}%)."
            )

        # ==========================================
        # CATEGORY INCREASE
        # ==========================================

        if (
            "increased the most" in normalized
            or "highest category" in normalized
            or "largest category" in normalized
            or "top category" in normalized
        ):

            result = InsightQueries.highest_category(
                user_id,
                period
            )

            if not result:

                return (
                    "No category data found."
                )

            return (
                f"Your highest spending category is "
                f"{result.category} "
                f"with ₦{result.total:,.2f}."
            )

        # ==========================================
        # MERCHANT
        # ==========================================

        if (
            "merchant" in normalized
            or "vendor" in normalized
            or "store" in normalized
            or "shop" in normalized
        ):

            result = InsightQueries.highest_merchant(
                user_id,
                period
            )

            if not result:

                return "No merchant data found."

            return (
                f"You spend the most with "
                f"{result.merchant} "
                f"(₦{result.total:,.2f})."
            )

        # ==========================================
        # PAYMENT METHOD
        # ==========================================

        if (
            "payment method" in normalized
            or "how do i pay" in normalized
            or "most used payment" in normalized
        ):

            payment = InsightQueries.payment_method(
                user_id
            )

            if not payment:

                return (
                    "No payment method data found."
                )

            return (
                f"Your most frequently used payment "
                f"method is {payment.payment_method} "
                f"({payment.count} transactions)."
            )

        # ==========================================
        # INCOME SOURCE
        # ==========================================

        if (
            "income source" in normalized
            or "source of income" in normalized
            or "highest income source" in normalized
        ):

            result = InsightQueries.highest_income_source(
                user_id
            )

            if not result:

                return "No income source found."

            return (
                f"Your largest income source is "
                f"{result.source} "
                f"(₦{result.total:,.2f})."
            )

        # ==========================================
        # SAVINGS RATE
        # ==========================================

        if (
            "saving rate" in normalized
            or "savings rate" in normalized
        ):

            rate = InsightQueries.savings_rate(
                user_id
            )

            return (
                f"Your current savings rate is "
                f"{rate:.2f}%."
            )

        # ==========================================
        # EXPENSE / INCOME RATIO
        # ==========================================

        if (
            "expense ratio" in normalized
            or "income ratio" in normalized
            or "expense income ratio" in normalized
        ):

            ratio = InsightQueries.expense_income_ratio(
                user_id
            )

            return (
                f"Your expenses represent "
                f"{ratio:.2f}% of your income."
            )

        # ==========================================
        # MONTHLY CASH FLOW
        # ==========================================

        if (
            "cash flow" in normalized
            or "cashflow" in normalized
        ):

            flow = InsightQueries.cash_flow(
                user_id
            )

            return (
                f"Income: ₦{flow['income']:,.2f}\n"
                f"Expenses: ₦{flow['expense']:,.2f}\n"
                f"Balance: ₦{flow['balance']:,.2f}"
            )

        return None