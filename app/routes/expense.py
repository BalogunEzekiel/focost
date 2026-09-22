from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
)

from flask_login import (
    login_required,
    current_user,
)

from sqlalchemy import or_

from app.extensions import db
from app.forms.expense_forms import ExpenseForm
from app.models.expense import Expense
from app.models.asset import Asset
from app.audit.service import AuditService


expense_bp = Blueprint(
    "expense",
    __name__,
    url_prefix="/expense",
)


# ==========================================================
# EXPENSE LIST
# ==========================================================

@expense_bp.route("/")
@login_required
def list_expense():

    # ======================================================
    # SEARCH
    # ======================================================

    search = request.args.get(
        "search",
        "",
        type=str,
    ).strip()


    # ======================================================
    # PAGINATION
    # ======================================================

    page = request.args.get(
        "page",
        1,
        type=int,
    )

    per_page = request.args.get(
        "per_page",
        10,
        type=int,
    )


    # ------------------------------------------------------
    # Validate page
    # ------------------------------------------------------

    if page < 1:
        page = 1


    # ------------------------------------------------------
    # Validate per_page
    # ------------------------------------------------------

    if per_page not in (
        10,
        20,
        50,
        100,
    ):
        per_page = 10


    # ======================================================
    # BASE QUERY
    # ======================================================

    expense_query = (
        Expense.query
        .filter(
            Expense.user_id == current_user.id
        )
    )


    # ======================================================
    # SEARCH
    # ======================================================
    #
    # Search:
    # - Category
    # - Merchant
    # - Description
    # - Payment method
    # - Notes
    #
    # ======================================================

    if search:

        search_value = f"%{search}%"


        expense_query = expense_query.filter(
            or_(
                Expense.category.ilike(
                    search_value
                ),

                Expense.merchant.ilike(
                    search_value
                ),

                Expense.description.ilike(
                    search_value
                ),

                Expense.payment_method.ilike(
                    search_value
                ),

                Expense.notes.ilike(
                    search_value
                ),
            )
        )


    # ======================================================
    # SORT
    # ======================================================
    #
    # Latest expense first.
    #
    # expense_date DESC:
    #     newest date first.
    #
    # id DESC:
    #     if two expenses have the same date,
    #     the most recently created record appears first.
    #
    # ======================================================

    expense_query = expense_query.order_by(
        Expense.expense_date.desc(),
        Expense.id.desc(),
    )


    # ======================================================
    # FILTERED EXPENSES FOR KPI CARDS
    # ======================================================
    #
    # IMPORTANT:
    #
    # This uses the SAME filtered query as the table.
    #
    # Therefore, when the user searches:
    #
    #     "Fuel"
    #
    # the KPI cards will also show statistics for
    # the Fuel search results only.
    #
    # ======================================================

    filtered_expenses = expense_query.all()


    # ======================================================
    # PAGINATION
    # ======================================================

    pagination = expense_query.paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )


    # ======================================================
    # CURRENT PAGE EXPENSES
    # ======================================================

    expenses = pagination.items


    # ======================================================
    # RENDER
    # ======================================================

    return render_template(
        "expense/list.html",

        # Current page records
        expenses=expenses,

        # Pagination object
        pagination=pagination,

        # Search term
        search=search,

        # All FILTERED records
        # Used by KPI cards
        all_expenses=filtered_expenses,
    )


# ==========================================================
# ADD EXPENSE
# ==========================================================

@expense_bp.route(
    "/add",
    methods=["GET", "POST"]
)
@login_required
def add_expense():

    form = ExpenseForm()


    if form.validate_on_submit():

        from app.subscriptions.service import SubscriptionService
        allowed, limit_message = SubscriptionService.can_add_transaction(current_user.id)
        if not allowed:
            flash(limit_message, "warning")
            return render_template("expense/add.html", form=form), 402

        expense = Expense(

            user_id=current_user.id,

            category=form.category.data,

            merchant=form.merchant.data,

            description=form.description.data,

            amount=float(
                form.amount.data
            ),

            payment_method=form.payment_method.data,

            expense_date=form.expense_date.data,

            notes=form.notes.data,

            recurring=form.recurring.data,

        )


        db.session.add(expense)
        db.session.commit()


        flash(
            "Expense added successfully.",
            "success",
        )


        return redirect(
            url_for(
                "expense.list_expense"
            )
        )


    return render_template(
        "expense/add.html",
        form=form,
    )


# ==========================================================
# EDIT EXPENSE
# ==========================================================

@expense_bp.route(
    "/edit/<int:expense_id>",
    methods=["GET", "POST"]
)
@login_required
def edit_expense(expense_id):

    expense = Expense.query.filter_by(
        id=expense_id,
        user_id=current_user.id
    ).first_or_404()

    if expense.transaction_class not in (None, "expense"):
        flash(
            "This transaction originated from a Goal or Investment. Please manage it from the originating page.",
            "info",
        )
        return redirect(url_for("expense.list_expense"))

    form = ExpenseForm(
        obj=expense
    )


    if form.validate_on_submit():

        expense.category = (
            form.category.data
        )

        expense.merchant = (
            form.merchant.data
        )

        expense.description = (
            form.description.data
        )

        expense.amount = float(
            form.amount.data
        )

        expense.payment_method = (
            form.payment_method.data
        )

        expense.expense_date = (
            form.expense_date.data
        )

        expense.notes = (
            form.notes.data
        )

        expense.recurring = (
            form.recurring.data
        )

        if expense.transaction_class not in (None, "expense"):
            flash(
                "This record originated from a Goal or Investment. Update it from the originating page instead.",
                "warning",
            )
            return redirect(url_for("expense.list_expense"))

        expense.transaction_class = "expense"
        db.session.commit()


        flash(
            "Expense updated successfully.",
            "success",
        )


        return redirect(
            url_for(
                "expense.list_expense"
            )
        )


    return render_template(
        "expense/edit.html",

        form=form,

        expense=expense,
    )


# ==========================================================
# DELETE EXPENSE
# ==========================================================

@expense_bp.route(
    "/delete/<int:expense_id>",
    methods=["POST"]
)
@login_required
def delete_expense(expense_id):

    expense = Expense.query.filter_by(
        id=expense_id,
        user_id=current_user.id
    ).first_or_404()

    if expense.transaction_class not in (None, "expense"):
        flash(
            "This transaction originated from a Goal or Investment and cannot be deleted here. Manage it from the originating page.",
            "warning",
        )
        return redirect(url_for("expense.list_expense"))

    db.session.delete(expense)

    db.session.commit()


    flash(
        "Expense deleted successfully.",
        "success",
    )


    return redirect(
        url_for(
            "expense.list_expense"
        )
    )