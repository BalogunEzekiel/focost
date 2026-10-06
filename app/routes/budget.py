from flask import Blueprint
from flask import render_template
from flask import redirect
from flask import flash
from flask import url_for

from flask_login import login_required
from flask_login import current_user

from app.rbac.decorators import permission_required
from app.forms.budget_form import BudgetForm
from app.services.budget_service import BudgetService
from app.models.budget import Budget
from app.extensions import db
from sqlalchemy import func
from app.models.expense import Expense
from app.services.category_service import CategoryService

budget_bp = Blueprint(
    "budget",
    __name__,
    url_prefix="/budget",
)

@budget_bp.route("/add", methods=["GET", "POST"])
@permission_required("budgets.create")
def add():

    form = BudgetForm()
    form.category.choices = [(c.name, c.name) for c in CategoryService.budget_categories(current_user.id)]

    if form.validate_on_submit():
        if not CategoryService.is_valid_for_user(current_user.id, 'expense', form.category.data):
            flash('Please select an available expense category.', 'danger')
            return render_template('budget/add.html', form=form), 400

        BudgetService.create_budget(
            form,
            current_user.id,
        )

        flash(
            "Budget created successfully.",
            "success",
        )

        return redirect(url_for("budget.list_budgets"))

    return render_template(
        "budget/add.html",
        form=form,
    )

@budget_bp.route("/")
@permission_required("budgets.view")
def list_budgets():

    budgets = (
        Budget.query
        .filter_by(user_id=current_user.id)
        .order_by(Budget.start_date.desc())
        .all()
    )

    for budget in budgets:

        spent = (
            db.session.query(
                func.coalesce(func.sum(Expense.amount), 0)
            )
            .filter(
                Expense.user_id == budget.user_id,
                Expense.category == budget.category,
                Expense.expense_date >= budget.start_date,
                Expense.expense_date <= budget.end_date
            )
            .scalar()
        )

        # Only update spent
        budget.spent = spent

    return render_template(
        "budget/budgets.html",
        budgets=budgets,
    )

@budget_bp.route("/edit/<int:budget_id>", methods=["GET", "POST"])
@permission_required("budgets.edit")
def edit(budget_id):

    budget = Budget.query.filter_by(
        id=budget_id,
        user_id=current_user.id
    ).first_or_404()

    form = BudgetForm(obj=budget)
    form.category.choices = [(c.name, c.name) for c in CategoryService.budget_categories(current_user.id)]

    if form.validate_on_submit():
        if not CategoryService.is_valid_for_user(current_user.id, 'expense', form.category.data):
            flash('Please select an available expense category.', 'danger')
            return render_template('budget/edit.html', form=form, budget=budget), 400

        budget.category = form.category.data
        budget.amount = form.amount.data
        budget.period = form.period.data
        budget.start_date = form.start_date.data
        budget.end_date = form.end_date.data

        db.session.commit()

        flash(
            "Budget updated successfully.",
            "success"
        )

        return redirect(
            url_for("budget.list_budgets")
        )

    return render_template(
        "budget/edit.html",
        form=form,
        budget=budget
    )

@budget_bp.route("/progress/<int:budget_id>")
@permission_required("budgets.view")
def progress(budget_id):

    budget = Budget.query.filter_by(
        id=budget_id,
        user_id=current_user.id
    ).first_or_404()

    spent = (
        db.session.query(
            func.coalesce(func.sum(Expense.amount), 0)
        )
        .filter(
            Expense.user_id == current_user.id,
            Expense.category == budget.category,
            Expense.expense_date >= budget.start_date,
            Expense.expense_date <= budget.end_date
        )
        .scalar()
    )

    remaining = budget.amount - spent

    percentage = 0

    if budget.amount > 0:
        percentage = round((spent / budget.amount) * 100, 2)

    return render_template(
        "budget/progress.html",
        budget=budget,
        spent=spent,
        remaining=remaining,
        percentage=percentage,
    )

@budget_bp.route("/delete/<int:budget_id>")
@permission_required("budgets.delete")
def delete(budget_id):

    budget = Budget.query.filter_by(
        id=budget_id,
        user_id=current_user.id
    ).first_or_404()

    db.session.delete(budget)

    db.session.commit()

    flash(
        "Budget deleted successfully.",
        "success"
    )

    return redirect(
        url_for("budget.list_budgets")
    )
