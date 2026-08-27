import statistics
from app.models.permission import Permission

from flask import (
    Blueprint,
    render_template,
    request,
    abort,
    current_app
)

from flask_login import (
    login_required,
    current_user
)

from app.ai_coach.services import AICoachService
from app.services.llm_service import LLMService
from app.services.admin_service import AdminService
from app.audit.service import AuditService
from app.audit.constants import (
    ADMIN,
    ADMIN_DASHBOARD_VIEW
)

from app.rbac.decorators import permission_required


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
    template_folder="../templates/admin"
)


# ==========================================================
# Protect Entire Blueprint
# ==========================================================

@admin_bp.before_request
@login_required
def protect_admin():

    if not current_user.role_slug:
        abort(403)

# ==========================================================
# Admin Dashboard
# ==========================================================

@admin_bp.route("/")
@permission_required("admin.dashboard.view")
def dashboard():

    data = AdminService.dashboard_data()

    AuditService.log(
        action=ADMIN_DASHBOARD_VIEW,
        category=ADMIN,
        description="Viewed Admin Dashboard"
    )

    return render_template(
        "admin/dashboard.html",
        **data
    )

# ==========================================================
# Permissions
# ==========================================================

@admin_bp.route("/permissions")
@login_required
@permission_required("permissions.view")
def permissions():

    permissions = (
        Permission.query
        .order_by(
            Permission.module,
            Permission.action
        )
        .all()
    )

    return render_template(
        "admin/permissions.html",
        permissions=permissions
    )

# ==========================================================
# Audit Logs
# ==========================================================

@admin_bp.route("/audit")
@permission_required("audit.view")
def audit_logs():

    # Get pagination/search parameters
    page = request.args.get(
        "page",
        1,
        type=int
    )

    search = request.args.get(
        "search",
        "",
        type=str
    ).strip()

    category = request.args.get(
        "category",
        "",
        type=str
    ).strip()

    status = request.args.get(
        "status",
        "",
        type=str
    ).strip()

    # Retrieve audit logs
    logs = AuditService.get_logs(
        page=page,
        search=search,
        category=category,
        status=status
    )

    # Log that the audit page was viewed.
    # This is intentionally after retrieving the existing logs so
    # the page does not recursively depend on its own audit entry.
    AuditService.log(
        action="audit.view",
        category=ADMIN,
        description="Viewed Audit Logs"
    )

    return render_template(
        "admin/audit_logs.html",
        logs=logs,
        search=search,
        category=category,
        status=status
    )

# ==========================================================
# AI CENTER
# ==========================================================

@admin_bp.route("/ai")
@permission_required("ai.view")
def ai_settings():

    AuditService.log(
        action="ai.view",
        category=ADMIN,
        description="Viewed AI Center"
    )

    # ------------------------------------------------------
    # Runtime AI configuration
    # ------------------------------------------------------

    try:

        llm_service = LLMService()

        ai = llm_service.get_runtime_status()

    except Exception as e:

        # Do not expose technical details to the browser.
        current_app.logger.exception(
            "Unable to load AI runtime configuration"
        )

        ai = {

            "operational": False,

            "provider_count": 0,

            "providers": [],

            "rotation_enabled": False,

            "primary_provider": "None",

            "secondary_provider": "None",

            "api_key_source": "Environment",

            "coach_enabled": False,

            "provider_abstraction": True

        }

    # ------------------------------------------------------
    # AI capabilities
    # ------------------------------------------------------

    capabilities = [

        {
            "name": "Conversational AI Coach",

            "description":
                "Provides conversational financial guidance "
                "and responds to users' financial questions.",

            "icon": "bi-chat-dots-fill",

            "enabled": ai["coach_enabled"]
        },

        {
            "name": "Financial Insights",

            "description":
                "Analyses financial activity and provides "
                "personalized observations.",

            "icon": "bi-lightbulb-fill",

            "enabled": ai["operational"]
        },

        {
            "name": "Spending Forecast",

            "description":
                "Uses financial activity to help users "
                "understand potential future spending.",

            "icon": "bi-graph-up-arrow",

            "enabled": ai["operational"]
        },

        {
            "name": "Personalization",

            "description":
                "Adapts financial guidance to each user's "
                "financial context and activity.",

            "icon": "bi-person-check-fill",

            "enabled": ai["operational"]
        }

    ]

    return render_template(

        "admin/ai_settings.html",

        ai=ai,

        capabilities=capabilities

    )


# ==========================================================
# System Settings
# ==========================================================

@admin_bp.route("/settings")
@permission_required("settings.view")
def settings():

    AuditService.log(
        action="settings.view",
        category=ADMIN,
        description="Viewed System Settings"
    )

    return render_template(
        "admin/settings.html"
    )


# ==========================================================
# Subscriptions
# ==========================================================

@admin_bp.route("/subscriptions")
@permission_required("subscriptions.view")
def subscriptions():

    AuditService.log(
        action="subscriptions.view",
        category=ADMIN,
        description="Viewed Subscription Management"
    )

    return render_template(
        "admin/subscriptions.html",
        total_users=0,
        active_subscriptions=0,
        trial_subscriptions=0,
        expired_subscriptions=0,
        plans=[],
        subscriptions=[]
    )