import re


class IntentDetector:
    """
    Detects user intent, category, merchant,
    payment method and period.

    Returns a dictionary consumed by
    AICoachService.
    """

    # ============================================
    # CATEGORY MAP
    # ============================================

    CATEGORY_MAP = {

        # Transportation
        "transport": "Transportation",
        "transportation": "Transportation",
        "fuel": "Transportation",
        "petrol": "Transportation",
        "diesel": "Transportation",
        "uber": "Transportation",
        "bolt": "Transportation",
        "taxi": "Transportation",
        "bus": "Transportation",
        "parking": "Transportation",

        # Food
        "food": "Food",
        "restaurant": "Food",
        "groceries": "Food",
        "groceries": "Food",
        "lunch": "Food",
        "breakfast": "Food",
        "dinner": "Food",

        # Telephone
        "telephone": "Telephone",
        "phone": "Telephone",
        "airtime": "Telephone",
        "data": "Telephone",
        "internet": "Telephone",

        # Utilities
        "electricity": "Utilities",
        "water": "Utilities",
        "utility": "Utilities",

        # Housing
        "rent": "Housing",
        "house": "Housing",

        # Medical
        "hospital": "Medical",
        "medical": "Medical",
        "drug": "Medical",
        "pharmacy": "Medical",

        # Education
        "school": "Education",
        "education": "Education",
        "tuition": "Education",

        # Entertainment
        "movie": "Entertainment",
        "cinema": "Entertainment",
        "netflix": "Entertainment",

        # Investment
        "investment": "Investment",
        "invest": "Investment",
        "shares": "Investment",
        "stocks": "Investment",

        # Salary
        "salary": "Salary",
        "wages": "Salary",

        # Business
        "business": "Business",
    }

    # ============================================
    # MERCHANTS
    # ============================================

    MERCHANTS = [

        "mtn",
        "glo",
        "airtel",
        "9mobile",
        "gtbank",
        "zenith bank",
        "access bank",
        "uba",
        "first bank",
        "opay",
        "moniepoint",
        "kuda",
        "haggai mortgage bank"
    ]

    # ============================================
    # PAYMENT METHODS
    # ============================================

    PAYMENT_METHODS = [

        "cash",
        "card",
        "bank transfer",
        "transfer",
        "cheque",
        "pos",
        "mobile money"

    ]

    # ============================================
    # MAIN DETECTOR
    # ============================================

    @staticmethod
    def detect(question):

        q = question.lower().strip()

        intent = "unknown"

        # ============================================
        # INCOME
        # ============================================

        if any(x in q for x in [

            "income",
            "salary",
            "earned",
            "earn",
            "earning",
            "revenue",
            "received",
            "receive",
            "credit"

        ]):

            intent = "income"

        # ============================================
        # EXPENSE
        # ============================================

        elif any(x in q for x in [

            "expense",
            "expenses",
            "spent",
            "spending",
            "payment",
            "paid",
            "cost",
            "costs",
            "debit"

        ]):

            intent = "expense"

        # ============================================
        # BALANCE
        # ============================================

        elif any(x in q for x in [

            "balance",
            "cash",
            "wallet",
            "remaining",
            "money left",
            "available"

        ]):

            intent = "balance"

        # ---------------------------------
        # SPENDING PATTERN
        # ---------------------------------

        elif any(x in q for x in [

            "spending pattern",
            "spending trends",
            "expense trend",
            "monthly trend",
            "expense history",
            "monthly history",
            "top spending",
            "highest category",
            "largest category",
            "top category",
            "most expensive category",
            "highest merchant",
            "top merchant",
            "top merchants",
            "where do i spend",
            "where can i reduce spending"

        ]):

            intent = "spending_pattern"

        # ============================================
        # BUDGET
        # ============================================

        elif any(x in q for x in [

            "budget",
            "budgets",
            "budgeted"

        ]):

            intent = "budget"

        # ============================================
        # GOALS
        # ============================================

        elif any(x in q for x in [

            "goal",
            "goals",
            "target"

        ]):

            intent = "goal"

        # ---------------------------------
        # FINANCIAL HEALTH
        # ---------------------------------

        elif any(x in q for x in [

            "financial health",
            "health score",
            "financial score",
            "finance score",
            "money score",
            "financial grade",
            "financial status"

        ]):

            intent = "financial_health"

        # ---------------------------------
        # FORECAST
        # ---------------------------------

        elif any(x in q for x in [

            "forecast",
            "predict",
            "prediction",
            "projection",
            "future",
            "future spending",
            "future expenses",
            "future income",
            "cash flow",
            "cashflow",
            "best income month",
            "highest income month",
            "highest expense month",
            "worst expense month",
            "best savings",
            "worst savings",
            "average income",
            "average expense",
            "monthly savings",
            "expense ratio",
            "expense income ratio"

        ]):

            intent = "forecast"

        # ============================================
        # COMPARE
        # ============================================

        elif any(x in q for x in [

            "compare",
            "comparison",
            "vs",
            "versus"

        ]):

            intent = "compare"

        # ============================================
        # TOP 5
        # ============================================

        elif any(x in q for x in [

            "top 5",
            "top five",
            "largest 5",
            "highest 5",
            "biggest 5"

        ]):

            intent = "top5"

        # ============================================
        # MERCHANT
        # ============================================

        elif any(x in q for x in [

            "merchant",
            "vendor",
            "store",
            "shop"

        ]):

            intent = "merchant"

        # ---------------------------------
        # RECOMMENDATION
        # ---------------------------------

        elif any(x in q for x in [

            "recommend",
            "recommendation",
            "recommendations",
            "advice",
            "suggest",
            "suggestion",
            "tips",
            "help me",
            "improve finances",
            "improve financial health",
            "reduce spending",
            "cut spending",
            "cut expenses",
            "save money",
            "lower expenses",
            "spend less",
            "what should i do",
            "how can i improve"

        ]):

            intent = "reduce"

        # ============================================
        # SAVINGS
        # ============================================

        elif any(x in q for x in [

            "saving",
            "savings",
            "saving rate"

        ]):

            intent = "savings"

        # ============================================
        # CASH FLOW
        # ============================================

        elif any(x in q for x in [

            "cash flow",
            "cashflow"

        ]):

            intent = "cashflow"

        # ============================================
        # FINANCIAL HEALTH
        # ============================================

        elif any(x in q for x in [

            "financial health",
            "health score",
            "financial score"

        ]):

            intent = "financial_health"

        # ============================================
        # CATEGORY
        # ============================================

        category = None

        for key, value in IntentDetector.CATEGORY_MAP.items():

            if re.search(rf"\b{re.escape(key)}\b", q):

                category = value
                break

        # ============================================
        # PERIOD
        # ============================================

        period = None

        if "today" in q:

            period = "today"

        elif "yesterday" in q:

            period = "yesterday"

        elif "last week" in q:

            period = "last_week"

        elif "this week" in q or "current week" in q:

            period = "week"

        elif "last month" in q:

            period = "last_month"

        elif "this month" in q or "current month" in q:

            period = "month"

        elif "this year" in q or "current year" in q:

            period = "year"

        # ============================================
        # MERCHANT
        # ============================================

        merchant = None

        for company in IntentDetector.MERCHANTS:

            if company in q:

                merchant = company.title()
                break

        # ============================================
        # PAYMENT METHOD
        # ============================================

        payment_method = None

        for method in IntentDetector.PAYMENT_METHODS:

            if method in q:

                payment_method = method.title()
                break

        # ============================================
        # RETURN
        # ============================================

        return {

            "intent": intent,

            "category": category,

            "merchant": merchant,

            "payment_method": payment_method,

            "period": period,

            "question": question,

            "normalized": q

        }