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

from app.extensions import db
from app.forms.income_forms import IncomeForm
from app.models.income import Income
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
@login_required
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
    # Pagination
    # ------------------------------------------------------

    income_pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )


    # ------------------------------------------------------
    # Records on current page
    # ------------------------------------------------------

    incomes = income_pagination.items


    return render_template(
        "income/list.html",
        incomes=incomes,
        income_pagination=income_pagination,
        search=search,
    )


# ==========================================================
# ADD INCOME
# ==========================================================

@income_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_income():

    form = IncomeForm()

    if form.validate_on_submit():

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
@login_required
def edit_income(income_id):

    income = Income.query.filter_by(
        id=income_id,
        user_id=current_user.id
    ).first_or_404()

    form = IncomeForm(obj=income)

    if form.validate_on_submit():

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
@login_required
def delete_income(income_id):

    income = Income.query.filter_by(
        id=income_id,
        user_id=current_user.id
    ).first_or_404()

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