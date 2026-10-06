from flask import Blueprint, render_template, request
from flask_login import login_required

from app.rbac.decorators import permission_required
from app.services.admin_analytics_service import AdminAnalyticsService

admin_analytics_bp = Blueprint("admin_analytics", __name__, url_prefix="/admin/analytics")


@admin_analytics_bp.get("/")
@login_required
@permission_required("analytics.view")
def index():
    period = request.args.get("period", "all")
    plan = request.args.get("plan", "all")
    status = request.args.get("status", "all")
    if period not in {"all", "30d", "90d", "ytd"}:
        period = "all"
    if plan not in {"all", "free_trial", "basic", "plus", "pro"}:
        plan = "all"
    if status not in {"all", "active", "inactive"}:
        status = "all"
    return render_template(
        "admin/analytics.html",
        analytics=AdminAnalyticsService.snapshot(period, plan, status),
    )
