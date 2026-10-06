from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user

from app.extensions import db
from app.models.compliance import PolicyDocument

compliance_bp = Blueprint("compliance", __name__)


@compliance_bp.get("/privacy")
def privacy():
    policy = PolicyDocument.query.filter_by(slug="privacy", is_current=True).first()
    return render_template("legal/policy.html", policy=policy)


@compliance_bp.get("/terms")
def terms():
    policy = PolicyDocument.query.filter_by(slug="terms", is_current=True).first()
    return render_template("legal/policy.html", policy=policy)


@compliance_bp.get("/cookies")
def cookies():
    policy = PolicyDocument.query.filter_by(slug="cookies", is_current=True).first()
    return render_template("legal/policy.html", policy=policy)


@compliance_bp.get("/ai-disclosure")
def ai_disclosure():
    policy = PolicyDocument.query.filter_by(slug="ai-disclosure", is_current=True).first()
    return render_template("legal/policy.html", policy=policy)


@compliance_bp.get("/acceptable-use")
def acceptable_use():
    policy = PolicyDocument.query.filter_by(slug="acceptable-use", is_current=True).first()
    return render_template("legal/policy.html", policy=policy)


@compliance_bp.post("/cookie-consent")
def cookie_consent():
    data = request.get_json(silent=True) or request.form
    choice = (data.get("choice") or "essential").lower()
    if choice not in {"essential", "all"}:
        return jsonify({"success": False, "message": "Invalid consent choice."}), 400
    response = jsonify({"success": True, "choice": choice})
    response.set_cookie(
        "focost_cookie_consent",
        choice,
        max_age=31536000,
        secure=request.is_secure,
        httponly=False,
        samesite="Lax",
    )
    return response


@compliance_bp.get("/reaccept-required")
@login_required
def reaccept_required():
    from app.services.compliance_service import ComplianceService
    required = [s for s in ("terms", "privacy", "ai-disclosure") if not ComplianceService.accepted_current(current_user, s)]
    return jsonify({"required": required})


@compliance_bp.get("/history")
@login_required
def history():
    from app.models.compliance import PolicyAcceptance
    records = PolicyAcceptance.query.filter_by(
        user_id=current_user.id
    ).order_by(PolicyAcceptance.accepted_at.desc()).all()
    return render_template("legal/history.html", history=records)
