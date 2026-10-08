from functools import wraps
from flask import jsonify, redirect, url_for
from flask_login import current_user
from .service import SubscriptionService
from app.services.subscription_gate import SubscriptionGate


def subscription_required(feature=None):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if SubscriptionGate.is_admin_user(current_user):
                if fn.__name__ in {"chat"}:
                    return jsonify({
                        "success": False,
                        "code": "ADMIN_FEATURE_FORBIDDEN",
                        "message": "This feature is available only to normal users.",
                    }), 403
                from flask import abort
                abort(403)

            if not SubscriptionService.has_access(current_user.id, feature):
                if fn.__name__ in {"chat"}:
                    return jsonify({"success": False, "code": "SUBSCRIPTION_REQUIRED", "message": "Your FOCOST trial or subscription has expired. Please choose a paid plan to continue using this feature."}), 402
                return redirect(url_for("billing.index"))
            return fn(*args, **kwargs)
        return wrapped
    return decorator
