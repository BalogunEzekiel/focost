from flask import Blueprint, request, jsonify, redirect, url_for, flash, abort
from urllib.parse import urlparse
from flask_login import login_required, current_user
from app.services.feature_access_service import FeatureAccessService
from app.services.language_service import LanguageService, LANGUAGES

language_bp = Blueprint("language", __name__, url_prefix="/language")

@language_bp.post("/set")
@login_required
def set_language():
    if not FeatureAccessService.allowed(current_user, "multilingual", "configure"):
        abort(403)
    code = (request.form.get("language") or "").strip().lower()
    if request.is_json:
        code = str((request.get_json(silent=True) or {}).get("language", "")).strip().lower()
    try:
        LanguageService.set(current_user.id, code)
    except ValueError:
        if request.is_json: return jsonify({"success": False, "message": "Unsupported language."}), 400
        flash("Please select a supported language.", "warning")
        return redirect(url_for("admin.dashboard" if current_user.is_admin_group else "dashboard.dashboard"))
    if request.is_json: return jsonify({"success": True, "language": code, "name": LANGUAGES[code]["name"]})
    flash("Language preference saved.", "success")
    referrer = request.referrer
    if referrer:
        parsed = urlparse(referrer)
        if parsed.netloc == request.host and parsed.scheme in {"http", "https"}:
            return redirect(referrer)
    return redirect(url_for("admin.dashboard" if current_user.is_admin_group else "dashboard.dashboard"))
