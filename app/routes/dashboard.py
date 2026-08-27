from datetime import date, timedelta
from math import ceil

from flask import (
    Blueprint,
    render_template,
    request,
    abort
)

from flask_login import (
    login_required,
    current_user
)

from sqlalchemy import or_, func

from app.services.dashboard_service import DashboardService
from app.services.notification_service import NotificationService

from app.models.income import Income
from app.models.expense import Expense


dashboard_bp = Blueprint(
    "dashboard",
    __name__
)


# ==========================================================
# SIMPLE PAGINATION OBJECT
# ==========================================================

class TransactionPagination:

    def __init__(
        self,
        items,
        total,
        page,
        per_page
    ):

        self.items = items
        self.total = total
        self.page = page
        self.per_page = per_page

        self.pages = max(
            1,
            ceil(total / per_page)
        )

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def prev_num(self):
        return self.page - 1

    @property
    def next_num(self):
        return self.page + 1

    @property
    def first(self):

        if not self.items:
            return 0

        return (
            (self.page - 1) * self.per_page
        ) + 1

    @property
    def last(self):

        return min(
            self.page * self.per_page,
            self.total
        )

    def iter_pages(
        self,
        left_edge=1,
        right_edge=1,
        left_current=2,
        right_current=2
    ):

        last = 0

        for num in range(
            1,
            self.pages + 1
        ):

            if (
                num <= left_edge
                or
                num > self.pages - right_edge
                or
                (
                    num >= self.page - left_current
                    and
                    num <= self.page + right_current
                )
            ):

                if last + 1 != num:
                    yield None

                yield num

                last = num


# ==========================================================
# TRANSACTION PERIOD
# ==========================================================

def get_transaction_period(period):

    today = date.today()

    if period == "today":

        return today, today

    if period == "week":

        start_date = (
            today
            - timedelta(days=today.weekday())
        )

        return start_date, today

    if period == "month":

        start_date = date(
            today.year,
            today.month,
            1
        )

        return start_date, today

    if period == "year":

        start_date = date(
            today.year,
            1,
            1
        )

        return start_date, today

    return None, None


# ==========================================================
# BUILD TRANSACTIONS
# ==========================================================

def get_dashboard_transactions(
    user_id,
    search=None,
    transaction_type=None,
    category=None,
    period="month"
):
    """
    Build a unified Income + Expense transaction list.

    Filtering is performed BEFORE pagination.

    Supported filters:
        - search
        - transaction type
        - category
        - period
    """

    transactions = []

    # ------------------------------------------------------
    # NORMALIZE FILTER VALUES
    # ------------------------------------------------------

    search = (search or "").strip()

    transaction_type = (
        transaction_type or ""
    ).strip().lower()

    category = (category or "").strip()

    # ------------------------------------------------------
    # DATE RANGE
    # ------------------------------------------------------

    start_date, end_date = get_transaction_period(
        period
    )

    # ======================================================
    # INCOME
    # ======================================================

    if transaction_type in ("", "income"):

        income_query = Income.query.filter(
            Income.user_id == user_id
        )

        # --------------------------------------------------
        # DATE FILTER
        # --------------------------------------------------

        if start_date:

            income_query = income_query.filter(
                Income.received_date >= start_date
            )

        if end_date:

            income_query = income_query.filter(
                Income.received_date <= end_date
            )

        # --------------------------------------------------
        # CATEGORY FILTER
        # --------------------------------------------------

        if category:

            income_query = income_query.filter(
                func.lower(
                    func.trim(
                        Income.category
                    )
                )
                ==
                category.lower()
            )

        # --------------------------------------------------
        # SEARCH FILTER
        # --------------------------------------------------

        if search:

            search_value = f"%{search}%"

            income_query = income_query.filter(
                or_(
                    Income.source.ilike(
                        search_value
                    ),

                    Income.category.ilike(
                        search_value
                    ),

                    Income.notes.ilike(
                        search_value
                    )
                )
            )

        # --------------------------------------------------
        # BUILD TRANSACTION DICTIONARIES
        # --------------------------------------------------

        for item in income_query.all():

            transactions.append({

                "id": item.id,

                "transaction_id": item.id,

                "transaction_type": "Income",

                "type": "Income",

                "title": item.source or "Income",

                "description": item.source or "Income",

                "category": (
                    item.category.strip()
                    if item.category
                    else "Uncategorized"
                ),

                "amount": float(
                    item.amount or 0
                ),

                "date": item.received_date,

                "note": getattr(
                    item,
                    "notes",
                    None
                ),

                "flagged": False

            })

    # ======================================================
    # EXPENSE
    # ======================================================

    if transaction_type in ("", "expense"):

        expense_query = Expense.query.filter(
            Expense.user_id == user_id
        )

        # --------------------------------------------------
        # DATE FILTER
        # --------------------------------------------------

        if start_date:

            expense_query = expense_query.filter(
                Expense.expense_date >= start_date
            )

        if end_date:

            expense_query = expense_query.filter(
                Expense.expense_date <= end_date
            )

        # --------------------------------------------------
        # CATEGORY FILTER
        # --------------------------------------------------

        if category:

            expense_query = expense_query.filter(
                func.lower(
                    func.trim(
                        Expense.category
                    )
                )
                ==
                category.lower()
            )

        # --------------------------------------------------
        # SEARCH FILTER
        # --------------------------------------------------

        if search:

            search_value = f"%{search}%"

            expense_query = expense_query.filter(
                or_(
                    Expense.merchant.ilike(
                        search_value
                    ),

                    Expense.category.ilike(
                        search_value
                    ),

                    Expense.description.ilike(
                        search_value
                    ),

                    Expense.notes.ilike(
                        search_value
                    )
                )
            )

        # --------------------------------------------------
        # BUILD TRANSACTION DICTIONARIES
        # --------------------------------------------------

        for item in expense_query.all():

            transactions.append({

                "id": item.id,

                "transaction_id": item.id,

                "transaction_type": "Expense",

                "type": "Expense",

                "title": item.merchant or "Expense",

                "description": (
                    item.description
                    or item.merchant
                    or "Expense"
                ),

                "category": (
                    item.category.strip()
                    if item.category
                    else "Uncategorized"
                ),

                "amount": float(
                    item.amount or 0
                ),

                "date": item.expense_date,

                "note": getattr(
                    item,
                    "notes",
                    None
                ),

                "flagged": False

            })

    # ======================================================
    # SORT
    # ======================================================
    #
    # Latest transactions first.
    #
    # Primary sort:
    #   Transaction date - newest first
    #
    # Secondary sort:
    #   Transaction ID - newest record first
    #
    # This also guarantees a consistent order when
    # multiple transactions have the same date.
    #

    transactions.sort(
        key=lambda item: (
            item.get("date") or date.min,
            item.get("id") or 0
        ),
        reverse=True
    )

    return transactions


# ==========================================================
# GET ALL AVAILABLE CATEGORIES
# ==========================================================

def get_dashboard_categories(
    user_id,
    period="month"
):

    categories = set()

    start_date, end_date = (
        get_transaction_period(period)
    )

    # ------------------------------------------------------
    # INCOME CATEGORIES
    # ------------------------------------------------------

    income_query = Income.query.filter(
        Income.user_id == user_id
    )

    if start_date:

        income_query = income_query.filter(
            Income.received_date >= start_date
        )

    if end_date:

        income_query = income_query.filter(
            Income.received_date <= end_date
        )

    for category in income_query.with_entities(
        Income.category
    ).distinct().all():

        if category[0]:

            categories.add(
                category[0].strip()
            )

    # ------------------------------------------------------
    # EXPENSE CATEGORIES
    # ------------------------------------------------------

    expense_query = Expense.query.filter(
        Expense.user_id == user_id
    )

    if start_date:

        expense_query = expense_query.filter(
            Expense.expense_date >= start_date
        )

    if end_date:

        expense_query = expense_query.filter(
            Expense.expense_date <= end_date
        )

    for category in expense_query.with_entities(
        Expense.category
    ).distinct().all():

        if category[0]:

            categories.add(
                category[0].strip()
            )

    return sorted(categories)


# ==========================================================
# LANDING PAGE
# ==========================================================

@dashboard_bp.route("/")
def home():

    return render_template(
        "index.html"
    )


# ==========================================================
# DASHBOARD
# ==========================================================

@dashboard_bp.route(
    "/dashboard",
    methods=["GET"]
)
@login_required
def dashboard():

    # ------------------------------------------------------
    # Notifications
    # ------------------------------------------------------

    NotificationService.generate_system_notifications(
        current_user.id
    )

    # ======================================================
    # FILTERS
    # ======================================================

    search = request.args.get(
        "search",
        "",
        type=str
    ).strip()

    transaction_type = request.args.get(
        "type",
        "",
        type=str
    ).strip()

    category = request.args.get(
        "category",
        "",
        type=str
    ).strip()

    period = request.args.get(
        "period",
        "month",
        type=str
    ).strip().lower()

    # ======================================================
    # VALIDATE TRANSACTION TYPE
    # ======================================================

    if transaction_type not in (
        "",
        "Income",
        "Expense"
    ):

        transaction_type = ""

    # ======================================================
    # VALIDATE PERIOD
    # ======================================================

    if period not in (
        "today",
        "week",
        "month",
        "year",
        "lifetime"
    ):

        period = "month"

    # ======================================================
    # PAGINATION
    # ======================================================

    page = request.args.get(
        "page",
        1,
        type=int
    )

    per_page = request.args.get(
        "per_page",
        10,
        type=int
    )

    if page < 1:

        page = 1

    if per_page not in (
        5,
        10,
        20,
        25,
        50
    ):

        per_page = 10

    # ======================================================
    # GET FILTERED TRANSACTIONS
    #
    # IMPORTANT:
    # Filtering happens BEFORE pagination.
    # ======================================================

    all_transactions = get_dashboard_transactions(

        user_id=current_user.id,

        search=search,

        transaction_type=transaction_type,

        category=category,

        period=period

    )

    # ======================================================
    # TOTAL
    # ======================================================

    total_transactions = len(
        all_transactions
    )

    # ======================================================
    # TOTAL PAGES
    # ======================================================

    total_pages = max(
        1,
        ceil(
            total_transactions / per_page
        )
    )

    # ======================================================
    # CORRECT INVALID PAGE
    # ======================================================

    if page > total_pages:

        page = total_pages

    # ======================================================
    # SLICE TRANSACTIONS
    # ======================================================

    start = (
        (page - 1)
        * per_page
    )

    end = start + per_page

    paginated_transactions = (
        all_transactions[start:end]
    )

    # ======================================================
    # PAGINATION OBJECT
    # ======================================================

    transaction_pagination = (
        TransactionPagination(

            items=paginated_transactions,

            total=total_transactions,

            page=page,

            per_page=per_page

        )
    )

    # ======================================================
    # BUILD NORMAL DASHBOARD
    #
    # IMPORTANT:
    # Do not allow DashboardService to replace
    # our filtered transaction collection.
    # ======================================================

    dashboard = DashboardService.get_dashboard_data(
        user_id=current_user.id
    )

    # ======================================================
    # OVERRIDE TRANSACTION DATA
    # ======================================================

    dashboard["recent_transactions"] = (
        paginated_transactions
    )

    dashboard["transaction_count"] = (
        total_transactions
    )

    dashboard["transaction_total"] = (
        total_transactions
    )

    # ======================================================
    # CATEGORIES
    #
    # Build categories independently from the
    # filtered/search result.
    # ======================================================

    dashboard["categories"] = (
        get_dashboard_categories(
            user_id=current_user.id,
            period=period
        )
    )

    # ======================================================
    # RENDER
    # ======================================================

    return render_template(

        "dashboard/dashboard.html",

        dashboard=dashboard,

        transaction_pagination=(
            transaction_pagination
        ),

        search=search,

        transaction_type=(
            transaction_type
        ),

        category=category,

        period=period

    )


# ==========================================================
# TRANSACTION DETAILS
# ==========================================================

@dashboard_bp.route(
    "/dashboard/transaction/<transaction_type>/<int:transaction_id>",
    methods=["GET"]
)
@login_required
def transaction_detail(
    transaction_type,
    transaction_id
):

    normalized_type = (
        transaction_type.strip().lower()
    )

    # ======================================================
    # INCOME
    # ======================================================

    if normalized_type == "income":

        transaction = Income.query.filter(
            Income.id == transaction_id,
            Income.user_id == current_user.id
        ).first()

        if not transaction:
            abort(404)

        # Normalize Income object
        transaction_data = {

            "id": transaction.id,

            "transaction_id": transaction.id,

            "transaction_type": "Income",

            "title": transaction.source,

            "description": transaction.source,

            "category": transaction.category,

            "amount": float(
                transaction.amount or 0
            ),

            "date": transaction.received_date,

            "note": getattr(
                transaction,
                "notes",
                None
            )

        }

        return render_template(
            "dashboard/transaction_details.html",

            transaction=transaction_data,

            transaction_type="Income"
        )

    # ======================================================
    # EXPENSE
    # ======================================================

    if normalized_type == "expense":

        transaction = Expense.query.filter(
            Expense.id == transaction_id,
            Expense.user_id == current_user.id
        ).first()

        if not transaction:
            abort(404)

        # Normalize Expense object
        transaction_data = {

            "id": transaction.id,

            "transaction_id": transaction.id,

            "transaction_type": "Expense",

            "title": transaction.merchant,

            "description": transaction.description,

            "category": transaction.category,

            "amount": float(
                transaction.amount or 0
            ),

            "date": transaction.expense_date,

            "note": getattr(
                transaction,
                "notes",
                None
            )

        }

        return render_template(
            "dashboard/transaction_details.html",

            transaction=transaction_data,

            transaction_type="Expense"
        )

    # ======================================================
    # INVALID TYPE
    # ======================================================

    abort(404)