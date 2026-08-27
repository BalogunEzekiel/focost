
from flask import Blueprint, render_template

showcase_bp = Blueprint("showcase", __name__)


@showcase_bp.get("/platform")
def platform():
    return render_template("platform.html")


@showcase_bp.get("/security")
def security():
    return render_template("security.html")
