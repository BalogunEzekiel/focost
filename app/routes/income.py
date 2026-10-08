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

from app.rbac.decorators import permission_required
from app.extensions import db
from app.forms.income_forms import IncomeForm
from app.models.income import Income
from app.services.category_service import CategoryService
from app.audit.service import AuditService


income_bp = Blueprint(
    "income",
    __name__,
    url_prefix="/income",
)


# ==========================================================
# INCOME LIST
# ==========================================================

@income_bp.route("/")
@permission_required("income.view")
def list_income():

    # ------------------------------------------------------
    # Search
    # ------------------------------------------------------

    search = request.args.get(
        "search",
        "",
        type=str
    ).strip()

    # ------------------------------------------------------
    # Pagination
    # ------------------------------------------------------

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

    # Keep pagination within sensible limits
    if page < 1:
        page = 1

    if per_page not in [10, 20, 50, 100]:
        per_page = 10

    # ------------------------------------------------------
    # Base Query
    # ------------------------------------------------------

    query = Income.query.filter_by(
        user_id=current_user.id
    )

    # ------------------------------------------------------
    # Search
    #
    # Search source, category and notes.
    # ------------------------------------------------------

    if search:

        search_pattern = f"%{search}%"

        query = query.filter(
            db.or_(
                Income.source.ilike(search_pattern),
                Income.category.ilike(search_pattern),
                Income.notes.ilike(search_pattern),
            )
        )

    # ------------------------------------------------------
    # IMPORTANT:
    # Latest income must always appear first.
    #
    # received_date DESC
    # id DESC handles records having the same date.
    # ------------------------------------------------------

    query = query.order_by(
        Income.received_date.desc(),
        Income.id.desc()
    )

    # ------------------------------------------------------
    # ALL FILTERED INCOME RECORDS
    #
    # This is used for the summary cards.
    # It contains ALL records matching the current search,
    # not just the records on the current pagination page.
    # ------------------------------------------------------

    all_incomes = query.all()

    # ------------------------------------------------------
    # Pagination
    #
    # This is used by the income table only.
    # ------------------------------------------------------

    income_pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    # ------------------------------------------------------
    # Current page records
    # ------------------------------------------------------

    incomes = income_pagination.items

    return render_template(
        "income/list.html",
        incomes=incomes,
        all_incomes=all_incomes,
        income_pagination=income_pagination,
        search=search,
    )


# ==========================================================
# ADD INCOME
# ==========================================================

@income_bp.route("/add", methods=["GET", "POST"])
@permission_required("income.create")
def add_income():

    form = IncomeForm()
    form.category.choices = [(c.name, c.name) for c in CategoryService.list_for_user(current_user.id, 'income')]

    if form.validate_on_submit():
        if not CategoryService.is_valid_for_user(current_user.id, 'income', form.category.data):
            flash('Please select a valid income category.', 'danger')
            return render_template('income/add.html', form=form), 400

        from app.subscriptions.service import SubscriptionService
        allowed, limit_message = SubscriptionService.can_add_transaction(current_user.id)
        if not allowed:
            flash(limit_message, "warning")
            return render_template("income/add.html", form=form), 402

        income = Income(
            user_id=current_user.id,
            source=form.source.data,
            category=form.category.data,
            amount=float(form.amount.data),
            received_date=form.received_date.data,
            notes=form.notes.data,
            recurring=form.recurring.data,
        )

        db.session.add(income)
        db.session.commit()

        AuditService.log(
            action="income.create", category="FINANCE",
            resource="Income", resource_id=income.public_id,
            description=f"Created income record: {income.source}"
        )

        flash(
            "Income added successfully.",
            "success",
        )

        return redirect(
            url_for("income.list_income")
        )

    return render_template(
        "income/add.html",
        form=form,
    )


# ==========================================================
# EDIT INCOME
# ==========================================================

@income_bp.route(
    "/edit/<int:income_id>",
    methods=["GET", "POST"]
)
@permission_required("income.edit")
def edit_income(income_id):

    income = Income.query.filter_by(
        id=income_id,
        user_id=current_user.id
    ).first_or_404()

    if income.transaction_class != "income":

        if income.transaction_class == "investment_liquidation":
            message = (
                "This income record originated from an Investment "
                "and cannot be deleted here."
            )

        elif income.transaction_class == "goal_termination":
            message = (
                "This income record was automatically created when the "
                "goal was terminated and cannot be deleted."
            )

        else:
            message = (
                "This system-generated income record cannot be deleted."
            )

        flash(message, "warning")

        return redirect(
            url_for("income.list_income")
        )

    form = IncomeForm(obj=income)
    form.category.choices = [(c.name, c.name) for c in CategoryService.list_for_user(current_user.id, 'income')]

    if form.validate_on_submit():
        if not CategoryService.is_valid_for_user(current_user.id, 'income', form.category.data):
            flash('Please select a valid income category.', 'danger')
            return render_template('income/edit.html', form=form, income=income), 400

        income.source = form.source.data
        income.category = form.category.data
        income.amount = float(form.amount.data)
        income.received_date = form.received_date.data
        income.notes = form.notes.data
        income.recurring = form.recurring.data

        db.session.commit()

        AuditService.log(
            action="income.update", category="FINANCE",
            resource="Income", resource_id=income.public_id,
            description=f"Updated income record: {income.source}"
        )

        flash(
            "Income updated successfully.",
            "success"
        )

        return redirect(
            url_for("income.list_income")
        )

    return render_template(
        "income/edit.html",
        form=form,
        income=income
    )


# ==========================================================
# DELETE INCOME
# ==========================================================

@income_bp.route(
    "/delete/<int:income_id>",
    methods=["POST"]
)
@permission_required("income.delete")
def delete_income(income_id):

    income = Income.query.filter_by(
        id=income_id,
        user_id=current_user.id
    ).first_or_404()

    if income.transaction_class != "income":
        flash(
            "This income record originated from an Investment and cannot be deleted here.",
            "warning",
        )
        return redirect(url_for("income.list_income"))

    public_id = income.public_id
    source = income.source
    db.session.delete(income)
    db.session.commit()

    AuditService.log(
        action="income.delete", category="FINANCE",
        resource="Income", resource_id=public_id,
        description=f"Deleted income record: {source}"
    )

    flash(
        "Income deleted successfully.",
        "success"
    )

    return redirect(
        url_for("income.list_income")
    )
