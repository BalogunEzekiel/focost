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
from app.forms.auth_forms import RegisterForm, LoginForm, ForgotPasswordForm, ResetPasswordForm

from app.audit.service import AuditService
from app.audit.constants import (
    AUTH,
    USER,
    AUTH_LOGIN,
    AUTH_LOGOUT,
    AUTH_LOGIN_FAILED,
    AUTH_EMAIL_VERIFIED,
    AUTH_PASSWORD_RESET,
    USER_CREATED
)

from app.rbac.service import RBACService
from app.services.ai_service import AIService
from app.services.auth_service import AuthService
from app.services.email_service import EmailService
from app.services.compliance_service import ComplianceService
from app.models.compliance import AuthToken

auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth"
)


def _user_display_name(user):
    """Return the user's real name, falling back to email if unavailable."""
    name = " ".join(
        part
        for part in [
            (user.first_name or "").strip(),
            (user.last_name or "").strip(),
        ]
        if part
    ).strip()

    return name or user.email


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

        if not form.accept_terms.data and not current_app.config.get("TESTING", False):
            flash("You must accept the Terms, Privacy Policy and AI disclosure to create an account.", "danger")
            return render_template("auth/register.html", form=form)

        try:

            user = User(
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                email=email,
                is_active=not current_app.config.get("AUTH_EMAIL_VERIFICATION_REQUIRED", True),
            )

            user.set_password(
                form.password.data
            )

            db.session.add(user)

            # Generate user.id
            db.session.flush()

            # Record the exact policy versions accepted at registration.
            ComplianceService.accept(
                user,
                ["terms", "privacy", "ai-disclosure"],
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string,
            )

            # Assign default user role
            RBACService.assign_default_role(user)

            # Start the time-limited trial. Trial state belongs to the
            # subscription domain and is independent of AI processing.
            from app.subscriptions.service import SubscriptionService
            SubscriptionService.start_trial(user, commit=False)

            # Save everything
            db.session.commit()

            if current_app.config.get("AUTH_EMAIL_VERIFICATION_REQUIRED", True):
                verification_ttl = current_app.config[
                    "AUTH_EMAIL_VERIFICATION_TTL_MINUTES"
                ]

                verification_token = AuthService.issue_token(
                    user.id,
                    "email_verification",
                    verification_ttl,
                )

                verify_url = (
                    f"{current_app.config['APP_BASE_URL']}"
                    f"{url_for('auth.verify_email', token=verification_token)}"
                )

                user_name = _user_display_name(user)

                try:
                    verification_ttl_hours = verification_ttl / 60

                    if verification_ttl_hours.is_integer():
                        verification_ttl_display = (
                            f"{int(verification_ttl_hours)} "
                            f"{'hour' if verification_ttl_hours == 1 else 'hours'}"
                        )
                    else:
                        verification_ttl_display = f"{verification_ttl_hours:g} hours"

                    sent = EmailService.send(
                        user.email,
                        "Verify your FOCOST email address",
                        (
                            f"Hello {user_name},\n\n"
                            "Welcome to FOCOST.\n\n"
                            "Thank you for creating your FOCOST account. "
                            "Please verify your email address to activate your account "
                            "and complete your registration.\n\n"
                            f"Verify your email address: {verify_url}\n\n"
                            "For your security, this verification link is valid for "
                            f"{verification_ttl_display} and will expire automatically "
                            "after that time.\n\n"
                            "If you did not create this FOCOST account, you can safely "
                            "ignore this email.\n\n"
                            "Regards,\n"
                            "FOCOST Team"
                        ),
                        (
                            f"<p>Hello {user_name},</p>"
                            "<p>Welcome to <strong>FOCOST</strong>.</p>"
                            "<p>"
                            "Thank you for creating your FOCOST account. "
                            "Please verify your email address to activate your account "
                            "and complete your registration."
                            "</p>"
                            f'<p><a href="{verify_url}">'
                            "<strong>Verify Your Email Address</strong>"
                            "</a></p>"
                            "<p>"
                            "For your security, this verification link is valid for "
                            f"<strong>{verification_ttl_display}</strong> and will "
                            "expire automatically after that time."
                            "</p>"
                            "<p>"
                            "If you did not create this FOCOST account, you can safely "
                            "ignore this email."
                            "</p>"
                            "<p>Regards,<br><strong>FOCOST Team</strong></p>"
                        ),
                    )

                    if not sent:
                        current_app.logger.warning(
                            "Verification email is enabled as a requirement but "
                            "mail delivery is disabled."
                        )
                except Exception:
                    current_app.logger.exception("Verification email delivery failed")
                    flash("Your account was created, but the verification email could not be sent. Please use Resend verification or contact support.", "warning")
                    return redirect(url_for("auth.verify_notice"))

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

        flash("Registration successful. Check your email to verify and activate your account before logging in.", "success")
        return redirect(url_for("auth.verify_notice", email=user.email))

    return render_template(
        "auth/register.html",
        form=form
    )


# ==========================================================
# EMAIL VERIFICATION / PASSWORD RECOVERY
# ==========================================================

@auth_bp.route("/verify", methods=["GET"])
def verify_email():
    token = request.args.get("token", "")
    user = AuthService.consume_token(token, "email_verification")
    if not user:
        flash("That verification link is invalid or has expired. Please request a new one.", "danger")
        return redirect(url_for("auth.verify_notice"))
    user.email_verified = True
    user.is_active = True
    db.session.commit()
    AuditService.log(action=AUTH_EMAIL_VERIFIED, category=AUTH, resource="User", resource_id=user.public_id, description="Email address verified and account activated")
    flash("Email verified. Your FOCOST account is now active.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/verify-notice")
def verify_notice():
    return render_template("auth/verify_notice.html", email=request.args.get("email", ""))


@auth_bp.route("/resend-verification", methods=["GET", "POST"])
def resend_verification():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        if not AuthService.throttle(f"verify:{request.remote_addr}", 5, 900, 900):
            flash("Please wait before requesting another verification email.", "warning")
            return redirect(url_for("auth.verify_notice"))
        user = User.query.filter_by(email=email).first()
        if user and not user.email_verified:
            AuthService.revoke_tokens(user.id, "email_verification")

            verification_ttl = current_app.config[
                "AUTH_EMAIL_VERIFICATION_TTL_MINUTES"
            ]

            raw = AuthService.issue_token(
                user.id,
                "email_verification",
                verification_ttl,
            )

            verify_url = (
                f"{current_app.config['APP_BASE_URL']}"
                f"{url_for('auth.verify_email', token=raw)}"
            )

            user_name = _user_display_name(user)

            try:
                verification_ttl_hours = verification_ttl / 60

                if verification_ttl_hours.is_integer():
                    verification_ttl_display = (
                        f"{int(verification_ttl_hours)} "
                        f"{'hour' if verification_ttl_hours == 1 else 'hours'}"
                    )
                else:
                    verification_ttl_display = f"{verification_ttl_hours:g} hours"

                sent = EmailService.send(
                    user.email,
                    "Verify your FOCOST email address",
                    (
                        f"Hello {user_name},\n\n"
                        "Welcome to FOCOST.\n\n"
                        "Thank you for creating your FOCOST account. "
                        "Please verify your email address to activate your account "
                        "and complete your registration.\n\n"
                        f"Verify your email address: {verify_url}\n\n"
                        "For your security, this verification link is valid for "
                        f"{verification_ttl_display} and will expire automatically "
                        "after that time.\n\n"
                        "If you did not create this FOCOST account, you can safely "
                        "ignore this email.\n\n"
                        "Regards,\n"
                        "FOCOST Team"
                    ),
                    (
                        f"<p>Hello {user_name},</p>"
                        "<p>Welcome to <strong>FOCOST</strong>.</p>"
                        "<p>"
                        "Thank you for creating your FOCOST account. "
                        "Please verify your email address to activate your account "
                        "and complete your registration."
                        "</p>"
                        f'<p><a href="{verify_url}">'
                        "<strong>Verify Your Email Address</strong>"
                        "</a></p>"
                        "<p>"
                        "For your security, this verification link is valid for "
                        f"<strong>{verification_ttl_display}</strong> and will "
                        "expire automatically after that time."
                        "</p>"
                        "<p>"
                        "If you did not create this FOCOST account, you can safely "
                        "ignore this email."
                        "</p>"
                        "<p>Regards,<br><strong>FOCOST Team</strong></p>"
                    ),
                )

                if not sent:
                    current_app.logger.warning(
                        "Verification resend email delivery is disabled."
                    )

            except Exception:
                current_app.logger.exception("Verification resend failed")

        flash("If an eligible account exists, a verification email has been sent.", "info")
        return redirect(url_for("auth.verify_notice"))

    return render_template("auth/verify_notice.html", email="")


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        allowed = AuthService.throttle(
            f"reset:{request.remote_addr}:{email}",
            current_app.config["AUTH_PASSWORD_RESET_LIMIT"],
            current_app.config["AUTH_PASSWORD_RESET_WINDOW_SECONDS"],
            current_app.config["AUTH_PASSWORD_RESET_BLOCK_SECONDS"]
        )
        if allowed:
            user = User.query.filter_by(email=email).first()
            if user and user.is_active:
                AuthService.revoke_tokens(user.id, "password_reset")

                password_reset_ttl = current_app.config[
                    "AUTH_PASSWORD_RESET_TTL_MINUTES"
                ]

                raw = AuthService.issue_token(
                    user.id,
                    "password_reset",
                    password_reset_ttl
                )

                reset_url = (
                    f"{current_app.config['APP_BASE_URL']}"
                    f"{url_for('auth.reset_password', token=raw)}"
                )

                user_name = _user_display_name(user)

                try:
                    password_reset_ttl_hours = password_reset_ttl / 60

                    if password_reset_ttl_hours.is_integer():
                        password_reset_ttl_display = (
                            f"{int(password_reset_ttl_hours)} "
                            f"{'hour' if password_reset_ttl_hours == 1 else 'hours'}"
                        )
                    else:
                        password_reset_ttl_display = f"{password_reset_ttl_hours:g} hours"

                    sent = EmailService.send(
                        user.email,
                        "Reset your FOCOST password",
                        (
                            f"Hello {user_name},\n\n"
                            "We received a request to reset the password for your "
                            "FOCOST account.\n\n"
                            "If you made this request, use the link below to create "
                            "a new password:\n\n"
                            f"Reset your password: {reset_url}\n\n"
                            "For your security, this password-reset link is valid for "
                            f"{password_reset_ttl_display} and can be used only once. "
                            "After it expires or is used, you will need to request a "
                            "new password-reset link.\n\n"
                            "If you did not request a password reset, no action is "
                            "required. Your password will remain unchanged.\n\n"
                            "Regards,\n"
                            "FOCOST Team"
                        ),
                        (
                            f"<p>Hello {user_name},</p>"
                            "<p>"
                            "We received a request to reset the password for your "
                            "FOCOST account."
                            "</p>"
                            "<p>"
                            "If you made this request, use the link below to create "
                            "a new password:"
                            "</p>"
                            f'<p><a href="{reset_url}">'
                            "<strong>Reset Your Password</strong>"
                            "</a></p>"
                            "<p>"
                            "For your security, this password-reset link is valid for "
                            f"<strong>{password_reset_ttl_display}</strong> and can "
                            "be used only once. After it expires or is used, you will "
                            "need to request a new password-reset link."
                            "</p>"
                            "<p>"
                            "If you did not request a password reset, no action is "
                            "required. Your password will remain unchanged."
                            "</p>"
                            "<p>Regards,<br><strong>FOCOST Team</strong></p>"
                        )
                    )

                    if not sent:
                        current_app.logger.warning(
                            "Password reset email delivery is disabled."
                        )

                except Exception:
                    current_app.logger.exception(
                        "Password reset email delivery failed"
                    )

        flash("If the email is registered, a password-reset link has been sent.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    token_hash = AuthService._hash(token)
    auth_token = AuthToken.query.filter_by(token_hash=token_hash, purpose="password_reset").first()
    if not auth_token or auth_token.used_at or auth_token.expires_at < __import__("datetime").datetime.utcnow():
        flash("That password-reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = auth_token.user
        user.set_password(form.password.data)
        user.auth_version += 1
        auth_token.used_at = __import__("datetime").datetime.utcnow()
        AuthService.revoke_tokens(user.id, "password_reset")
        db.session.commit()
        AuditService.log(action=AUTH_PASSWORD_RESET, category=AUTH, resource="User", resource_id=user.public_id, description="Password reset completed")
        flash("Password reset successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", form=form)


@auth_bp.route("/reaccept", methods=["GET", "POST"])
@login_required
def reaccept_policies():
    policies = [ComplianceService.current_policy(slug) for slug in ("terms", "privacy", "ai-disclosure")]
    if not all(policies):
        return redirect(get_role_landing_url(current_user))
    if request.method == "POST":
        if request.form.get("accept") != "yes":
            flash("You must accept the current policies to continue using FOCOST.", "danger")
            return render_template("auth/reaccept.html", policies=policies)
        ComplianceService.accept(current_user, [p.slug for p in policies], request.remote_addr, request.user_agent.string)
        db.session.commit()
        flash("Policy acknowledgement updated.", "success")
        return redirect(get_role_landing_url(current_user))
    return render_template("auth/reaccept.html", policies=policies)


# ==========================================================
# ROLE-BASED LANDING
# ==========================================================

def get_role_landing_url(user):
    """
    Determine the post-authentication landing page from the immutable
    system role group, not from a custom role slug.
    """

    role_group = getattr(user, "role_group", None)

    current_app.logger.warning(
        "ROLE LANDING: user=%s role=%s group=%s",
        getattr(user, "email", None),
        getattr(user, "role_slug", None),
        role_group,
    )

    if not role_group:
        return url_for("auth.no_access")

    if role_group == "super_admin":
        return url_for("admin.dashboard")

    if role_group == "user":
        return url_for("dashboard.dashboard")

    if role_group != "admin":
        return url_for("auth.no_access")

    administrative_pages = (
        ("admin.dashboard.view", "admin.dashboard"),
        ("users.view", "admin_users.index"),
        ("roles.view", "admin_roles.index"),
        ("permissions.view", "admin.permissions"),
        ("audit.view", "admin.audit_logs"),
        ("subscriptions.view", "admin.subscriptions"),
        ("ai.view", "admin.ai_settings"),
        ("settings.view", "admin.settings"),
        ("communications.view", "admin_communications.index"),
        ("analytics.view", "admin_analytics.index"),
        ("documents.view", "admin_documents.index"),
        ("feedback.view", "admin.feedback"),
    )

    for permission_code, endpoint in administrative_pages:
        try:
            if user.has_permission(permission_code):
                return url_for(endpoint)
        except Exception:
            current_app.logger.exception(
                "RBAC landing check failed: user=%s permission=%s",
                getattr(user, "email", None),
                permission_code,
            )

    return url_for("auth.no_access")


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

        if not AuthService.throttle(f"login:{request.remote_addr}:{email}", current_app.config["AUTH_LOGIN_LIMIT"], current_app.config["AUTH_LOGIN_WINDOW_SECONDS"], current_app.config["AUTH_LOGIN_BLOCK_SECONDS"]):
            flash("Too many login attempts. Please wait and try again.", "warning")
            return render_template("auth/login.html", form=form), 429

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

        email_verification_required = current_app.config.get(
            "AUTH_EMAIL_VERIFICATION_REQUIRED",
            True
        )

        # --------------------------------------------------
        # ACCOUNT STATUS
        # --------------------------------------------------

        if not user.is_active:

            # A newly registered account that has not yet verified
            # its email is inactive by design.
            if email_verification_required and not user.email_verified:

                flash(
                    "Please verify your email address before logging in. "
                    "Check your inbox or request a new verification email.",
                    "warning"
                )

                return redirect(
                    url_for(
                        "auth.verify_notice",
                        email=user.email
                    )
                )

            # A previously verified account that has subsequently
            # been deactivated must receive an explicit status message.
            flash(
                "Your account has been deactivated. "
                "Please contact FOCOST Support for assistance.",
                "warning"
            )

            return redirect(
                url_for("auth.login")
            )

        # --------------------------------------------------
        # EMAIL VERIFICATION
        # --------------------------------------------------

        if email_verification_required and not user.email_verified:

            flash(
                "Please verify your email address before logging in. "
                "Check your inbox or request a new verification email.",
                "warning"
            )

            return redirect(
                url_for(
                    "auth.verify_notice",
                    email=user.email
                )
            )

        AuthService.reset_throttle(
            f"login:{request.remote_addr}:{email}"
        )

        # --------------------------------------------------
        # LOGIN USER
        # --------------------------------------------------

        try:

            login_user(user)
            session["auth_version"] = user.auth_version

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

    # Clear non-persistent AI chat history.
    AIService.clear_session_history()

    logout_user()

    return redirect(
        url_for("auth.login")
    )
