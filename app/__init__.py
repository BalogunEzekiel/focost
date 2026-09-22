from flask import Flask, jsonify, render_template, request, g
from flask_login import current_user
from sqlalchemy import text
import logging
import time
import uuid

from .config import Config
from .extensions import db, migrate, login_manager, csrf
from .models import *


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

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
        ), 200, {"Content-Type": "text/plain; charset=utf-8"}

    @app.get("/.well-known/security.txt")
    def security_txt():
        return (
            "Contact: mailto:security@focost.ai\n"
            "Preferred-Languages: en\n"
            "Policy: /security\n"
        ), 200, {"Content-Type": "text/plain; charset=utf-8"}

    # ---------------------------------------------------------
    # Error handlers: never expose stack traces in production.
    # ---------------------------------------------------------
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api"):
            return jsonify({"success": False, "message": "Resource not found."}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.exception("Unhandled application error; request_id=%s", g.get("request_id"))
        if request.path.startswith("/api"):
            return jsonify({
                "success": False,
                "message": "An unexpected error occurred.",
                "request_id": g.get("request_id"),
            }), 500
        return render_template("errors/500.html", request_id=g.get("request_id")), 500

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
    app.register_blueprint(showcase_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_users_bp)
    app.register_blueprint(admin_roles_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(assets_bp)

    RBACMiddleware.init_app(app)
    register_context_processors(app)

    from .seeds.rbac_seed import RBACSeed
    import click

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

    @app.errorhandler(401)
    def unauthorized(error):
        if request.path.startswith("/api"):
            return jsonify({"success": False, "message": "Authentication required."}), 401
        return render_template("errors/401.html"), 401

    @app.errorhandler(403)
    def forbidden(error):
        if request.path.startswith("/api"):
            return jsonify({"success": False, "message": "Permission denied."}), 403
        return render_template("errors/403.html"), 403

    return app
