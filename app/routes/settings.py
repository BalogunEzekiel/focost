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
from app.services.currency_service import CurrencyService
from app.services.language_service import LanguageService
from app.services.feature_access_service import FeatureAccessService


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
        "preferences": {**preferences, "currency": current_user.currency or "NGN", "base_currency": current_user.base_currency or "NGN", "language": LanguageService.get(current_user.id)}
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

    # Preferences are user-scoped. Validate the dedicated settings before saving.
    if "currency" in preferences:
        try:
            CurrencyService.set(current_user, preferences.pop("currency"))
        except ValueError as exc:
            return jsonify({"success": False, "message": str(exc)}), 400
    if "language" in preferences:
        if not FeatureAccessService.allowed(current_user, "multilingual", "configure"):
            return jsonify({"success": False, "message": "Your account does not have access to language preferences."}), 403
        try:
            LanguageService.set(current_user.id, preferences.pop("language"))
        except ValueError as exc:
            return jsonify({"success": False, "message": str(exc)}), 400
    settings = SettingsService.update(
        current_user.id,
        preferences
    )

    return jsonify({
        "success": True,
        "message": "Preferences saved successfully.",
        "preferences": {**settings.get_preferences(), "currency": current_user.currency or "NGN", "base_currency": current_user.base_currency or "NGN", "language": LanguageService.get(current_user.id)}
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
        "preferences": {**settings.get_preferences(), "currency": current_user.currency or "NGN", "base_currency": current_user.base_currency or "NGN", "language": LanguageService.get(current_user.id)}
    })

@settings_bp.post("/currency/convert")
@login_required
def convert_currency():
    """Convert an amount without mutating the source financial record."""
    from datetime import date
    from decimal import Decimal
    from app.services.exchange_rate_service import ExchangeRateService, ExchangeRateUnavailable

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"success": False, "message": "Invalid conversion request."}), 400
    try:
        source = str(data.get("from_currency") or current_user.base_currency or "NGN").upper()
        target = str(data.get("to_currency") or current_user.currency or "NGN").upper()
        on_date = date.fromisoformat(data["date"]) if data.get("date") else None
        rate = ExchangeRateService.get_rate(source, target, on_date=on_date)
        amount = data.get("amount", 0)
        converted = ExchangeRateService.convert(amount, source, target, on_date=on_date)
        return jsonify({
            "success": True,
            "from_currency": source,
            "to_currency": target,
            "original_amount": str(Decimal(str(amount))),
            "converted_amount": str(converted),
            "exchange_rate": str(rate),
            "rate_date": (on_date or date.today()).isoformat(),
        })
    except (ValueError, TypeError) as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except ExchangeRateUnavailable as exc:
        return jsonify({"success": False, "code": "EXCHANGE_RATE_UNAVAILABLE", "message": str(exc)}), 503
