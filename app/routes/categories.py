from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.forms.category_forms import CategoryForm
from app.services.category_service import CategoryService
from app.subscriptions.service import SubscriptionService


categories_bp = Blueprint("categories", __name__, url_prefix="/categories")


@categories_bp.before_request
@login_required
def protect():
    if not current_user.is_normal_user:
        from flask import abort
        abort(403)
    if not CategoryService.can_customize(current_user.id):
        from flask import abort
        abort(403)


@categories_bp.get("/")
def index():
    return render_template(
        "categories/index.html",
        income_categories=CategoryService.list_for_user(current_user.id, "income"),
        expense_categories=CategoryService.list_for_user(current_user.id, "expense"),
        plan=SubscriptionService.entitlements(current_user.id).get("plan_name"),
    )


@categories_bp.post("/create")
def create():
    form = CategoryForm()
    if not form.validate_on_submit():
        flash("Please provide a valid category name.", "danger")
        return redirect(url_for("categories.index"))
    try:
        CategoryService.create_personal(
            current_user.id,
            form.category_type.data,
            form.name.data,
            form.description.data,
        )
        flash("Personal category created successfully.", "success")
    except (ValueError, PermissionError) as exc:
        flash(str(exc), "warning")
    return redirect(url_for("categories.index"))


@categories_bp.post("/<int:category_id>/update")
def update(category_id):
    form = CategoryForm()
    if not form.validate_on_submit():
        flash("Please provide a valid category name.", "danger")
        return redirect(url_for("categories.index"))
    try:
        CategoryService.update_personal(
            current_user.id,
            category_id,
            form.name.data,
            form.description.data,
        )
        flash("Category updated successfully.", "success")
    except (ValueError, PermissionError) as exc:
        flash(str(exc), "warning")
    return redirect(url_for("categories.index"))


@categories_bp.post("/<int:category_id>/archive")
def archive(category_id):
    try:
        CategoryService.archive_personal(current_user.id, category_id)
        flash("Category archived. Existing transactions remain unchanged.", "success")
    except (ValueError, PermissionError) as exc:
        flash(str(exc), "warning")
    return redirect(url_for("categories.index"))
