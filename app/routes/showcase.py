from flask import Blueprint, render_template

from app.subscriptions.service import SubscriptionService


showcase_bp = Blueprint("showcase", __name__)


@showcase_bp.get("/platform")
def platform():
    return render_template("platform.html")


@showcase_bp.get("/pricing")
def pricing():
    plans = SubscriptionService.plans()
    return render_template("pricing.html", plans=plans)


@showcase_bp.get("/faq")
def faq():
    return render_template("faq.html")


@showcase_bp.get("/about")
def about():
    return render_template("about.html")


@showcase_bp.get("/support")
def support():
    return render_template("support.html")


@showcase_bp.get("/security")
def security():
    return render_template("security.html")
