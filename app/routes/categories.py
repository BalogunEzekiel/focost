
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    abort,
)

from flask_login import (
    login_required,
    current_user,
)

from app.forms.category_forms import CategoryForm
from app.services.category_service import CategoryService
from app.subscriptions.service import SubscriptionService


categories_bp = Blueprint(
    "categories",
    __name__,
    url_prefix="/categories",
)


# ==========================================================
# USER PLAN
# ==========================================================

def get_user_plan(user_id):
    """Return the user's canonical or displayed subscription plan."""
    entitlements = SubscriptionService.entitlements(user_id) or {}

    # Prefer the canonical plan slug.
    slug = str(
        entitlements.get("plan_slug") or ""
    ).strip().lower()

    if slug in {"plus", "pro"}:
        return slug

    # Fall back to the displayed plan name.
    name = str(
        entitlements.get("plan_name")
        or entitlements.get("plan")
        or entitlements.get("tier")
        or ""
    ).strip().lower()

    for plan in ("plus", "pro"):
        if name == plan or name.startswith(plan + " "):
            return plan

    return name


# ==========================================================
# AUTHENTICATION AND USER-TYPE PROTECTION
# ==========================================================

@categories_bp.before_request
@login_required
def protect():
    """Restrict the Categories module to authenticated normal users."""
    if not current_user.is_normal_user:
        abort(403)


# ==========================================================
# CATEGORY LIST
# ==========================================================

@categories_bp.get("/")
def index():
    plan = get_user_plan(current_user.id)

    return render_template(
        "category/index.html",
        income_categories=CategoryService.list_for_user(
            current_user.id,
            "income",
        ),
        expense_categories=CategoryService.list_for_user(
            current_user.id,
            "expense",
        ),
        plan=plan,
        can_manage_categories=CategoryService.can_customize(
            current_user.id
        ),
    )


# ==========================================================
# CREATE PERSONAL CATEGORY
# ==========================================================

@categories_bp.post("/create")
def create():
    form = CategoryForm()

    if not form.validate_on_submit():
        flash(
            "Please provide a valid category name.",
            "danger",
        )
        return redirect(url_for("categories.index"))

    try:
        CategoryService.create_personal(
            current_user.id,
            form.category_type.data,
            form.name.data,
            form.description.data,
        )

        flash(
            "Personal category created successfully.",
            "success",
        )

    except (ValueError, PermissionError) as exc:
        flash(str(exc), "warning")

    return redirect(url_for("categories.index"))


# ==========================================================
# UPDATE PERSONAL CATEGORY
# ==========================================================

@categories_bp.post("/<int:category_id>/update")
def update(category_id):
    form = CategoryForm()

    if not form.validate_on_submit():
        flash(
            "Please provide a valid category name.",
            "danger",
        )
        return redirect(url_for("categories.index"))

    try:
        CategoryService.update_personal(
            current_user.id,
            category_id,
            form.name.data,
            form.description.data,
        )

        flash(
            "Category updated successfully.",
            "success",
        )

    except (ValueError, PermissionError) as exc:
        flash(str(exc), "warning")

    return redirect(url_for("categories.index"))


# ==========================================================
# ARCHIVE PERSONAL CATEGORY
# ==========================================================

@categories_bp.post("/<int:category_id>/archive")
def archive(category_id):
    try:
        CategoryService.archive_personal(
            current_user.id,
            category_id,
        )

        flash(
            "Category archived. Existing transactions remain unchanged.",
            "success",
        )

    except (ValueError, PermissionError) as exc:
        flash(str(exc), "warning")

    return redirect(url_for("categories.index"))
