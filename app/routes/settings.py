from flask import (
    Blueprint,
    jsonify,
    request
)

from flask_login import (
    login_required,
    current_user
)

from app.services.settings_service import SettingsService


settings_bp = Blueprint(
    "settings",
    __name__,
    url_prefix="/settings"
)


# ============================================================
# GET USER SETTINGS
# ============================================================

@settings_bp.get("/api")
@login_required
def get_settings():

    preferences = SettingsService.get_preferences(
        current_user.id
    )

    return jsonify({
        "success": True,
        "preferences": preferences
    })


# ============================================================
# SAVE USER SETTINGS
# ============================================================

@settings_bp.put("/api")
@login_required
def update_settings():

    data = request.get_json(
        silent=True
    ) or {}

    preferences = data.get(
        "preferences",
        {}
    )

    if not isinstance(preferences, dict):

        return jsonify({
            "success": False,
            "message": "Invalid settings format."
        }), 400

    settings = SettingsService.update(
        current_user.id,
        preferences
    )

    return jsonify({
        "success": True,
        "message": "Preferences saved successfully.",
        "preferences": settings.get_preferences()
    })


# ============================================================
# RESET USER SETTINGS
# ============================================================

@settings_bp.post("/reset")
@login_required
def reset_settings():

    settings = SettingsService.reset(
        current_user.id
    )

    return jsonify({
        "success": True,
        "message": "Preferences restored to default.",
        "preferences": settings.get_preferences()
    })