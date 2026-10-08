from flask import Flask, jsonify, render_template, request, g, session, redirect, url_for
from flask_login import current_user
from sqlalchemy import text
import logging
import time
import uuid

from .config import Config
from .extensions import db, migrate, login_manager, csrf
from .models import *


def create_app(config_override=None):
    app = Flask(__name__)
    app.config.from_object(Config)

    if config_override:
        app.config.update(config_override)

    if app.config.get("TESTING"):
        database_uri = str(app.config.get("SQLALCHEMY_DATABASE_URI") or "")

        if database_uri not in {"sqlite:///:memory:", "sqlite://"}:
            raise RuntimeError(
                "TESTING=True requires an in-memory SQLite database. "
                f"Refusing to initialize tests against: {database_uri}"
            )

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY must be configured.")

    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URL must be configured.")

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # ---------------------------------------------------------
    # Request correlation + security headers
    # ---------------------------------------------------------
    @app.before_request
    def start_request():
        g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        g.request_started_at = time.perf_counter()

    @app.before_request
    def enforce_authenticated_account_state():
        if current_user.is_authenticated:
            if not current_user.is_active:
                from flask_login import logout_user
                logout_user()
                return redirect(url_for("auth.login"))

            if (
                session.get("auth_version") is not None
                and session.get("auth_version") != current_user.auth_version
            ):
                from flask_login import logout_user
                logout_user()
                return redirect(url_for("auth.login"))

            if (
                request.endpoint
                and not request.endpoint.startswith("auth.")
                and not request.endpoint.startswith("compliance.")
                and not request.endpoint.startswith("static")
                and not app.config.get("TESTING")
            ):
                from .services.compliance_service import ComplianceService

                required = [
                    s
                    for s in ("terms", "privacy", "ai-disclosure")
                    if ComplianceService.current_policy(s)
                ]

                if required and not all(
                    ComplianceService.accepted_current(current_user, s)
                    for s in required
                ):
                    if request.path.startswith("/api"):
                        return jsonify({
                            "success": False,
                            "message": "Updated policies require acknowledgement.",
                            "code": "POLICY_REACCEPT_REQUIRED",
                        }), 409

                    return redirect(url_for("auth.reaccept_policies"))

    @app.before_request
    def enforce_admin_surface_isolation():
        if not current_user.is_authenticated:
            return None

        if not current_user.is_admin_group:
            return None

        endpoint = request.endpoint or ""

        allowed_prefixes = (
            "auth.", "admin.", "admin_users.", "admin_roles.",
            "admin_documents.", "admin_analytics.", "admin_communications.",
            "compliance.", "notifications.", "profile.", "static",
        )

        # Administrators operate the administrative surface only. They never
        # enter ordinary users' financial/AI/billing screens.
        if endpoint.startswith(allowed_prefixes):
            return None

        if endpoint in {"dashboard.home", "dashboard.dashboard"}:
            return redirect(url_for("admin.dashboard"))

        if endpoint.startswith((
            "income.", "expense.", "budget.", "goal.", "assets.",
            "reports.", "ai.", "billing.", "categories.",
        )):
            return redirect(url_for("admin.dashboard"))

        return None

    @app.after_request
    def harden_response(response):
        response.headers["X-Request-ID"] = g.get("request_id", "")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"

        if request.path.startswith(("/auth", "/account", "/admin")):
            response.headers["Cache-Control"] = "no-store"

        # HSTS is only safe when HTTPS is actually enabled.
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response

    # ---------------------------------------------------------
    # Health/readiness endpoints
    # ---------------------------------------------------------
    @app.get("/healthz")
    def healthz():
        return jsonify({
            "status": "ok",
            "service": app.config["APP_NAME"],
            "version": app.config["APP_VERSION"],
            "request_id": g.request_id,
        })

    @app.get("/readyz")
    def readyz():
        try:
            db.session.execute(text("SELECT 1"))

            return jsonify({
                "status": "ready",
                "database": "ok",
                "version": app.config["APP_VERSION"],
            }), 200

        except Exception:
            app.logger.exception("Readiness check failed")

            return jsonify({
                "status": "not_ready",
                "database": "unavailable",
                "version": app.config["APP_VERSION"],
            }), 503

    @app.get("/robots.txt")
    def robots():
        return (
            "User-agent: *\n"
            "Allow: /\n"
            "Disallow: /admin\n"
            "Disallow: /api\n"
            "Disallow: /healthz\n"
            "Disallow: /readyz\n"
        ), 200, {
            "Content-Type": "text/plain; charset=utf-8"
        }

    @app.get("/.well-known/security.txt")
    def security_txt():
        """
        RFC 9116-style security contact information.

        The Policy and Canonical URLs are generated dynamically so they
        remain correct across local, staging, and production environments.
        """
        policy_url = url_for("showcase.security", _external=True)
        canonical_url = url_for("security_txt", _external=True)

        return (
            f"Contact: mailto:{app.config['FOCOST_SECURITY_EMAIL']}\n"
            "Expires: 2027-10-02T00:00:00Z\n"
            "Preferred-Languages: en\n"
            f"Policy: {policy_url}\n"
            f"Canonical: {canonical_url}\n"
        ), 200, {
            "Content-Type": "text/plain; charset=utf-8",
            "Cache-Control": "public, max-age=86400",
        }

    # ---------------------------------------------------------
    # Error handlers: never expose stack traces in production.
    # ---------------------------------------------------------
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api"):
            return jsonify({
                "success": False,
                "message": "Resource not found."
            }), 404

        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()

        app.logger.exception(
            "Unhandled application error; request_id=%s",
            g.get("request_id")
        )

        if request.path.startswith("/api"):
            return jsonify({
                "success": False,
                "message": "An unexpected error occurred.",
                "request_id": g.get("request_id"),
            }), 500

        return render_template(
            "errors/500.html",
            request_id=g.get("request_id")
        ), 500

    # ---------------------------------------------------------
    # Blueprints
    # ---------------------------------------------------------
    from .routes.dashboard import dashboard_bp
    from .routes.auth import auth_bp
    from .routes.income import income_bp
    from .routes.expense import expense_bp
    from .routes.budget import budget_bp
    from .routes.goal import goal_bp
    from .reports import reports_bp
    from .routes.ai import ai_bp
    from .routes.notifications import notifications_bp
    from .routes.account import account_bp
    from .routes.showcase import showcase_bp
    from .routes.admin import admin_bp
    from .routes.admin_users import admin_users_bp
    from .routes.admin_roles import admin_roles_bp
    from .rbac.middleware import RBACMiddleware
    from .context_processors import register_context_processors
    from app.routes.settings import settings_bp
    from .routes.billing import billing_bp
    from .routes.profile import profile_bp
    from .routes.assets import assets_bp
    from .routes.compliance import compliance_bp
    from .routes.admin_documents import admin_documents_bp
    from .routes.categories import categories_bp
    from .routes.admin_analytics import admin_analytics_bp
    from .routes.admin_communications import admin_communications_bp
    from .routes.feedback import feedback_bp
    from .routes.communications import communications_bp


    app.register_blueprint(dashboard_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(income_bp)
    app.register_blueprint(expense_bp)
    app.register_blueprint(budget_bp)
    app.register_blueprint(goal_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(showcase_bp, url_prefix="/showcase")
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_users_bp)
    app.register_blueprint(admin_roles_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(assets_bp)
    app.register_blueprint(compliance_bp)
    app.register_blueprint(admin_documents_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(admin_analytics_bp)
    app.register_blueprint(admin_communications_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(communications_bp)


    RBACMiddleware.init_app(app)
    register_context_processors(app)

    from .seeds.rbac_seed import RBACSeed
    from .seeds.compliance_seed import seed_policies
    import click

    @app.cli.command("seed-compliance")
    def seed_compliance():
        seed_policies()
        print("✓ Compliance policies seeded")

    @app.cli.command("seed-rbac")
    def seed_rbac():
        RBACSeed.run()

    from .seeds.manager import SeedManager

    @app.cli.command("seed")
    @click.argument("name")
    def seed_command(name):
        SeedManager.run(name)

    @app.cli.command("create-paystack-plans")
    def create_paystack_plans():
        """Create missing monthly Paystack plans from FOCOST's DB plan catalog."""
        from .subscriptions.paystack import PaystackService

        for item in PaystackService.create_or_sync_plans():
            print(item)

    # ---------------------------------------------------------
    # Authentication / authorization error handlers
    # ---------------------------------------------------------
    @app.errorhandler(401)
    def unauthorized(error):
        if request.path.startswith("/api"):
            return jsonify({
                "success": False,
                "message": "Authentication required."
            }), 401

        return render_template("errors/401.html"), 401

    @app.errorhandler(403)
    def forbidden(error):
        if request.path.startswith("/api"):
            return jsonify({
                "success": False,
                "message": "Permission denied."
            }), 403

        return render_template("errors/403.html"), 403

    return app