from flask import render_template, login_required
from . import admin_bp
from .decorators import admin_required
from .services import AdminService


@admin_bp.route("/")
@admin_required
def dashboard():

    stats = AdminService.dashboard()

    return render_template(

        "admin/dashboard.html",

        stats=stats

    )

@admin_bp.route("/no-access")
@login_required
def no_access():

    return render_template(
        "admin/no_access.html"
    ), 403