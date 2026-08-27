from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    request,
    current_app
)

from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user
)

from app.extensions import db
from app.models.user import User
from app.forms.auth_forms import RegisterForm, LoginForm

from app.ai_coach.chat_history import clear_session

from app.audit.service import AuditService
from app.audit.constants import (
    AUTH,
    USER,
    AUTH_LOGIN,
    AUTH_LOGOUT,
    AUTH_LOGIN_FAILED,
    USER_CREATED
)

from app.rbac.service import RBACService


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth"
)


# ==========================================================
# REGISTER
# ==========================================================

@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(
            url_for("dashboard.dashboard")
        )

    form = RegisterForm()

    if form.validate_on_submit():

        email = form.email.data.strip().lower()

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            flash(
                "Email already exists.",
                "danger"
            )

            return redirect(
                url_for("auth.register")
            )

        try:

            user = User(
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                email=email
            )

            user.set_password(
                form.password.data
            )

            db.session.add(user)

            # Generate user.id
            db.session.flush()

            # Assign default user role
            RBACService.assign_default_role(user)

            # Save everything
            db.session.commit()

        except Exception:

            db.session.rollback()

            current_app.logger.exception(
                "REGISTRATION FAILED"
            )

            flash(
                "Registration failed. Please try again.",
                "danger"
            )

            return render_template(
                "auth/register.html",
                form=form
            ), 500

        # --------------------------------------------------
        # AUDIT
        # --------------------------------------------------

        try:

            AuditService.log(
                action=USER_CREATED,
                category=USER,
                resource="User",
                resource_id=user.public_id,
                status="success",
                description=(
                    f"New user registered ({user.email})"
                ),
                metadata={
                    "ip": request.remote_addr,
                    "user_agent": request.user_agent.string
                }
            )

        except Exception:

            current_app.logger.exception(
                "REGISTRATION AUDIT FAILED"
            )

        flash(
            "Registration successful. Please login.",
            "success"
        )

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "auth/register.html",
        form=form
    )


# ==========================================================
# ROLE-BASED LANDING
# ==========================================================

def get_role_landing_url(user):
    """
    Determine where a successfully authenticated user
    should be redirected.
    """

    current_app.logger.warning(
        "========== ROLE LANDING =========="
    )

    try:

        role_slug = user.role_slug

        current_app.logger.warning(
            "USER: %s",
            getattr(user, "email", None)
        )

        current_app.logger.warning(
            "ROLE: %s",
            role_slug
        )

    except Exception:

        current_app.logger.exception(
            "FAILED TO READ USER ROLE"
        )

        return url_for(
            "auth.no_access"
        )

    # ------------------------------------------------------
    # NO ROLE
    # ------------------------------------------------------

    if not role_slug:

        current_app.logger.warning(
            "USER HAS NO ROLE"
        )

        return url_for(
            "auth.no_access"
        )

    # ------------------------------------------------------
    # SUPER ADMIN
    # ------------------------------------------------------

    if role_slug == "super_admin":

        current_app.logger.warning(
            "SUPER ADMIN LOGIN"
        )

        try:

            return url_for(
                "admin.dashboard"
            )

        except Exception:

            current_app.logger.exception(
                "ADMIN DASHBOARD ENDPOINT NOT FOUND"
            )

            return url_for(
                "auth.no_access"
            )

    # ------------------------------------------------------
    # NORMAL USER
    # ------------------------------------------------------

    if role_slug == "user":

        current_app.logger.warning(
            "NORMAL USER LOGIN"
        )

        try:

            return url_for(
                "dashboard.dashboard"
            )

        except Exception:

            current_app.logger.exception(
                "USER DASHBOARD ENDPOINT NOT FOUND"
            )

            return url_for(
                "auth.no_access"
            )

    # ------------------------------------------------------
    # OTHER ADMINISTRATIVE ROLES
    # ------------------------------------------------------

    administrative_pages = [

        (
            "admin.dashboard.view",
            "admin.dashboard"
        ),

        (
            "users.view",
            "admin_users.index"
        ),

        (
            "roles.view",
            "admin_roles.index"
        ),

        (
            "permissions.view",
            "admin.permissions"
        ),

        (
            "audit.view",
            "admin.audit_logs"
        ),

        (
            "subscriptions.view",
            "admin.subscriptions"
        ),

        (
            "ai.view",
            "admin.ai_settings"
        ),

        (
            "settings.view",
            "admin.settings"
        ),

    ]

    for permission_code, endpoint in administrative_pages:

        try:

            if user.has_permission(
                permission_code
            ):

                current_app.logger.warning(
                    "ADMIN LANDING: %s -> %s",
                    permission_code,
                    endpoint
                )

                return url_for(endpoint)

        except Exception:

            current_app.logger.exception(
                "RBAC CHECK FAILED: user=%s permission=%s",
                user.email,
                permission_code
            )

    # ------------------------------------------------------
    # GENERAL FINANCIAL PAGES
    # ------------------------------------------------------

    general_pages = [

        (
            "dashboard.view",
            "dashboard.dashboard"
        ),

        (
            "income.view",
            "income.list_income"
        ),

        (
            "expenses.view",
            "expense.list_expense"
        ),

        (
            "budgets.view",
            "budget.list_budgets"
        ),

        (
            "goals.view",
            "goal.list_goals"
        ),

        (
            "reports.view",
            "reports.index"
        ),

    ]

    for permission_code, endpoint in general_pages:

        try:

            if user.has_permission(
                permission_code
            ):

                current_app.logger.warning(
                    "GENERAL LANDING: %s -> %s",
                    permission_code,
                    endpoint
                )

                return url_for(endpoint)

        except Exception:

            current_app.logger.exception(
                "GENERAL RBAC CHECK FAILED: "
                "user=%s permission=%s",
                user.email,
                permission_code
            )

    # ------------------------------------------------------
    # NO ACCESS
    # ------------------------------------------------------

    current_app.logger.warning(
        "NO LANDING PAGE AVAILABLE FOR USER: %s",
        user.email
    )

    return url_for(
        "auth.no_access"
    )


# ==========================================================
# NO ACCESS
# ==========================================================

@auth_bp.route("/no-access")
def no_access():

    return render_template(
        "auth/no_access.html"
    )


# ==========================================================
# LOGIN
# ==========================================================

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    current_app.logger.warning(
        "========== LOGIN ROUTE =========="
    )

    current_app.logger.warning(
        "METHOD: %s",
        request.method
    )

    current_app.logger.warning(
        "AUTHENTICATED: %s",
        current_user.is_authenticated
    )

    # ------------------------------------------------------
    # ALREADY LOGGED IN
    # ------------------------------------------------------

    if current_user.is_authenticated:

        current_app.logger.warning(
            "USER ALREADY AUTHENTICATED: %s",
            current_user.email
        )

        return redirect(
            get_role_landing_url(
                current_user
            )
        )

    # ------------------------------------------------------
    # FORM
    # ------------------------------------------------------

    form = LoginForm()

    # ------------------------------------------------------
    # POST
    # ------------------------------------------------------

    if request.method == "POST":

        current_app.logger.warning(
            "LOGIN POST RECEIVED"
        )

        current_app.logger.warning(
            "FORM KEYS: %s",
            list(request.form.keys())
        )

        # --------------------------------------------------
        # VALIDATION
        # --------------------------------------------------

        if not form.validate_on_submit():

            current_app.logger.warning(
                "LOGIN FORM VALIDATION FAILED"
            )

            current_app.logger.warning(
                "FORM ERRORS: %s",
                form.errors
            )

            flash(
                "Please correct the highlighted fields.",
                "danger"
            )

            return render_template(
                "auth/login.html",
                form=form
            )

        # --------------------------------------------------
        # EMAIL
        # --------------------------------------------------

        email = (
            form.email.data.strip().lower()
            if form.email.data
            else ""
        )

        current_app.logger.warning(
            "LOGIN ATTEMPT: %s",
            email
        )

        # --------------------------------------------------
        # FIND USER
        # --------------------------------------------------

        try:

            user = User.query.filter_by(
                email=email
            ).first()

        except Exception:

            current_app.logger.exception(
                "DATABASE ERROR WHILE FINDING USER"
            )

            flash(
                "Unable to process login right now.",
                "danger"
            )

            return render_template(
                "auth/login.html",
                form=form
            ), 500

        # --------------------------------------------------
        # INVALID CREDENTIALS
        # --------------------------------------------------

        if not user:

            current_app.logger.warning(
                "USER NOT FOUND: %s",
                email
            )

            try:

                AuditService.log(
                    action=AUTH_LOGIN_FAILED,
                    category=AUTH,
                    status="failed",
                    description=(
                        f"Failed login attempt ({email})"
                    ),
                    metadata={
                        "ip": request.remote_addr,
                        "user_agent":
                            request.user_agent.string
                    }
                )

            except Exception:

                current_app.logger.exception(
                    "FAILED LOGIN AUDIT ERROR"
                )

            flash(
                "Invalid email or password.",
                "danger"
            )

            return render_template(
                "auth/login.html",
                form=form
            )

        # --------------------------------------------------
        # CHECK PASSWORD
        # --------------------------------------------------

        try:

            password_valid = user.check_password(
                form.password.data
            )

        except Exception:

            current_app.logger.exception(
                "PASSWORD CHECK FAILED FOR %s",
                email
            )

            flash(
                "Unable to process login right now.",
                "danger"
            )

            return render_template(
                "auth/login.html",
                form=form
            ), 500

        # --------------------------------------------------
        # WRONG PASSWORD
        # --------------------------------------------------

        if not password_valid:

            current_app.logger.warning(
                "INVALID PASSWORD FOR: %s",
                email
            )

            try:

                AuditService.log(
                    action=AUTH_LOGIN_FAILED,
                    category=AUTH,
                    status="failed",
                    description=(
                        f"Failed login attempt ({email})"
                    ),
                    metadata={
                        "ip": request.remote_addr,
                        "user_agent":
                            request.user_agent.string
                    }
                )

            except Exception:

                current_app.logger.exception(
                    "FAILED LOGIN AUDIT ERROR"
                )

            flash(
                "Invalid email or password.",
                "danger"
            )

            return render_template(
                "auth/login.html",
                form=form
            )

        # --------------------------------------------------
        # VALID LOGIN
        # --------------------------------------------------

        current_app.logger.warning(
            "VALID CREDENTIALS: %s",
            user.email
        )

        # --------------------------------------------------
        # LOGIN USER
        # --------------------------------------------------

        try:

            login_user(user)

        except Exception:

            current_app.logger.exception(
                "FLASK-LOGIN login_user() FAILED"
            )

            flash(
                "Unable to establish your session.",
                "danger"
            )

            return render_template(
                "auth/login.html",
                form=form
            ), 500

        current_app.logger.warning(
            "USER LOGGED IN: %s",
            user.email
        )

        # --------------------------------------------------
        # AUDIT
        # --------------------------------------------------

        try:

            AuditService.log(
                action=AUTH_LOGIN,
                category=AUTH,
                resource="User",
                resource_id=user.public_id,
                status="success",
                description=(
                    f"{user.email} logged in"
                ),
                metadata={
                    "ip": request.remote_addr,
                    "user_agent":
                        request.user_agent.string,
                    "role":
                        user.role_slug
                }
            )

        except Exception:

            current_app.logger.exception(
                "LOGIN AUDIT FAILED"
            )

        # --------------------------------------------------
        # LANDING PAGE
        # --------------------------------------------------

        try:

            landing_url = get_role_landing_url(
                user
            )

        except Exception:

            current_app.logger.exception(
                "LANDING PAGE RESOLUTION FAILED"
            )

            landing_url = url_for(
                "auth.no_access"
            )

        current_app.logger.warning(
            "LANDING URL: %s",
            landing_url
        )

        return redirect(
            landing_url
        )

    # ------------------------------------------------------
    # GET
    # ------------------------------------------------------

    return render_template(
        "auth/login.html",
        form=form
    )


# ==========================================================
# LOGOUT
# ==========================================================

@auth_bp.route("/logout")
@login_required
def logout():

    try:

        AuditService.log(
            action=AUTH_LOGOUT,
            category=AUTH,
            resource="User",
            resource_id=current_user.public_id,
            status="success",
            description=(
                f"{current_user.email} logged out"
            ),
            metadata={
                "ip": request.remote_addr,
                "user_agent":
                    request.user_agent.string
            }
        )

    except Exception:

        current_app.logger.exception(
            "LOGOUT AUDIT FAILED"
        )

    try:

        clear_session(
            current_user.id
        )

    except Exception:

        current_app.logger.exception(
            "CHAT SESSION CLEAR FAILED"
        )

    session.pop(
        "ai_history",
        None
    )

    logout_user()

    return redirect(
        url_for("auth.login")
    )

