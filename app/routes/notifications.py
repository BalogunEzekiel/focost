from flask import (
    Blueprint,
    jsonify,
    redirect,
    request,
    url_for,
    flash,
    render_template,
)

from flask_login import login_required, current_user

from app.rbac.decorators import permission_required
from app.services.notification_service import NotificationService


notifications_bp = Blueprint(
    "notifications",
    __name__,
    url_prefix="/notifications",
)


# ---------------------------------------------------------
# Notifications Page
# ---------------------------------------------------------

@notifications_bp.route("/")
@permission_required("notifications.view")
def index():

    notifications = NotificationService.get_all(
        current_user.id
    )

    return render_template(
        "notifications/index.html",
        notifications=notifications,
        page_title="Notifications",
    )


# ---------------------------------------------------------
# Notification API
# ---------------------------------------------------------

@notifications_bp.route("/api")
@permission_required("notifications.view")
def api():
    limit = max(1, min(request.args.get("limit", 10, type=int), 100))
    page = max(1, request.args.get("page", 1, type=int))
    kind = (request.args.get("type") or "").strip()
    status = (request.args.get("status") or "").strip().lower()
    q = NotificationService.get_all(current_user.id)
    if kind:
        q = [n for n in q if n.notification_type == kind]
    if status == "unread":
        q = [n for n in q if not n.is_read]
    elif status == "read":
        q = [n for n in q if n.is_read]
    total = len(q)
    start = (page - 1) * limit
    items = q[start:start + limit]
    return jsonify({
        "notification_count": NotificationService.get_unread_count(current_user.id),
        "page": page, "limit": limit, "total": total, "pages": max(1, (total + limit - 1) // limit),
        "notifications": [notification.to_dict() for notification in items],
    })

# ---------------------------------------------------------
# Mark One Read
# ---------------------------------------------------------

@notifications_bp.route("/read/<int:notification_id>", methods=["POST"])
@permission_required("notifications.view")
def mark_read(notification_id):

    success = NotificationService.mark_read(
        notification_id,
        current_user.id,
    )

    return jsonify(
        {
            "success": success,
            "notification_count": NotificationService.get_unread_count(
                current_user.id
            ),
        }
    )


# ---------------------------------------------------------
# Mark All Read
# ---------------------------------------------------------

@notifications_bp.route("/mark-all-read", methods=["POST"])
@permission_required("notifications.view")
def mark_all_read():

    NotificationService.mark_all_read(
        current_user.id
    )

    return jsonify(
        {
            "success": True,
            "notification_count": 0,
        }
    )


# ---------------------------------------------------------
# Dismiss Notification
# ---------------------------------------------------------

@notifications_bp.route("/dismiss/<int:notification_id>", methods=["POST"])
@permission_required("notifications.manage")
def dismiss(notification_id):
    success = NotificationService.dismiss(notification_id, current_user.id)
    return jsonify({"success": success, "notification_count": NotificationService.get_unread_count(current_user.id)})


# ---------------------------------------------------------
# Delete Notification
# ---------------------------------------------------------

@notifications_bp.route("/delete/<int:notification_id>", methods=["POST"])
@permission_required("notifications.manage")
def delete(notification_id):

    success = NotificationService.delete(
        notification_id,
        current_user.id,
    )

    return jsonify(
        {
            "success": success,
            "notification_count": NotificationService.get_unread_count(
                current_user.id
            ),
        }
    )


# ---------------------------------------------------------
# Open Notification
# ---------------------------------------------------------

@notifications_bp.route("/open/<int:notification_id>")
@permission_required("notifications.view")
def open_notification(notification_id):

    notification = NotificationService.get(
        notification_id,
        current_user.id,
    )

    if notification is None:

        flash(
            "Notification not found.",
            "warning",
        )

        return redirect(url_for("notifications.index"))

    NotificationService.mark_read(
        notification.id,
        current_user.id,
    )

    if notification.action_url:

        return redirect(notification.action_url)

    return redirect(url_for("notifications.index"))

@notifications_bp.route("/delete-all", methods=["POST"])
@permission_required("notifications.manage")
def delete_all():

    deleted = NotificationService.delete_all(
        current_user.id
    )

    return jsonify(
        {
            "success": True,
            "deleted": deleted,
            "notification_count": 0,
        }
    )

@notifications_bp.post("/push/register")
@permission_required("notifications.manage")
def register_push_device():
    from app.models.push_device import PushDevice
    from app.extensions import db
    from app.utils.timezone import utc_now

    data = request.get_json(silent=True) or {}
    token = str(data.get("token", "")).strip()
    platform = str(data.get("platform", "android")).strip().lower()
    provider = str(data.get("provider", "fcm")).strip().lower()
    if not token or platform not in {"android", "ios", "web"}:
        return jsonify({"success": False, "message": "A valid push token and platform are required."}), 400

    device = PushDevice.query.filter_by(token=token).first()
    if device and device.user_id != current_user.id:
        return jsonify({"success": False, "message": "Push token is already registered."}), 409
    if not device:
        device = PushDevice(
            user_id=current_user.id,
            token=token,
            platform=platform,
            provider=provider,
        )
        db.session.add(device)
    device.platform = platform
    device.provider = provider
    device.app_version = str(data.get("app_version", "")).strip()[:40] or None
    device.last_seen_at = utc_now()
    device.is_enabled = True
    db.session.commit()
    return jsonify({"success": True, "device_id": device.public_id})


# ---------------------------------------------------------
# Browser Web Push subscription management
# ---------------------------------------------------------

@notifications_bp.get("/web-push/public-key")
@login_required
def web_push_public_key():
    from flask import current_app

    config = current_app.config
    enabled = config.get("WEB_PUSH_ENABLED", False)
    public_key = config.get("WEB_PUSH_VAPID_PUBLIC_KEY", "")

    if not enabled or not public_key:
        return jsonify({
            "success": False,
            "message": "Web Push notifications are not configured.",
        }), 503

    return jsonify({
        "success": True,
        "publicKey": public_key,
    })


@notifications_bp.post("/web-push/subscribe")
@login_required
def subscribe_web_push():
    from app.extensions import db
    from app.models.web_push_subscription import WebPushSubscription
    from app.services.settings_service import SettingsService
    from app.utils.timezone import utc_now
    from flask import current_app
    from urllib.parse import urlparse

    config = current_app.config
    if (
        not config.get("WEB_PUSH_ENABLED", False)
        or not config.get("WEB_PUSH_VAPID_PUBLIC_KEY")
        or not config.get("WEB_PUSH_VAPID_PRIVATE_KEY")
    ):
        return jsonify({
            "success": False,
            "message": "Web Push notifications are not configured.",
        }), 503

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "A valid subscription object is required.",
        }), 400

    subscription = data.get("subscription")
    if not isinstance(subscription, dict):
        return jsonify({
            "success": False,
            "message": "A valid subscription object is required.",
        }), 400

    endpoint = subscription.get("endpoint")
    keys = subscription.get("keys")

    if (
        not isinstance(endpoint, str)
        or not endpoint
        or len(endpoint) > 4096
        or not isinstance(keys, dict)
    ):
        return jsonify({
            "success": False,
            "message": "The subscription endpoint or keys are invalid.",
        }), 400

    parsed_endpoint = urlparse(endpoint)
    if (
        parsed_endpoint.scheme != "https"
        or not parsed_endpoint.netloc
        or parsed_endpoint.username
        or parsed_endpoint.password
        or parsed_endpoint.fragment
    ):
        return jsonify({
            "success": False,
            "message": "The subscription endpoint is invalid.",
        }), 400

    p256dh = keys.get("p256dh")
    auth = keys.get("auth")

    if (
        not isinstance(p256dh, str)
        or not p256dh
        or len(p256dh) > 512
        or not isinstance(auth, str)
        or not auth
        or len(auth) > 256
    ):
        return jsonify({
            "success": False,
            "message": "The subscription encryption keys are invalid.",
        }), 400

    existing = WebPushSubscription.query.filter_by(
        endpoint=endpoint
    ).first()

    if existing and existing.user_id != current_user.id:
        return jsonify({
            "success": False,
            "message": "This subscription is already registered to another account.",
        }), 409

    now = utc_now()

    try:
        if existing:
            existing.p256dh = p256dh
            existing.auth = auth
            existing.last_seen_at = now
            existing.is_enabled = True
            existing.is_active = True
        else:
            existing = WebPushSubscription(
                user_id=current_user.id,
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth,
                last_seen_at=now,
                is_enabled=True,
                is_active=True,
            )
            db.session.add(existing)

        settings = SettingsService.get(current_user.id)
        preferences = settings.get_preferences()
        preferences.setdefault("notifications", {})["push"] = True
        settings.set_preferences(preferences)

        db.session.commit()

    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "Failed to save Web Push subscription for user %s",
            current_user.id,
        )
        return jsonify({
            "success": False,
            "message": "The subscription could not be saved.",
        }), 500

    return jsonify({
        "success": True,
        "message": "Web Push subscription registered.",
    }), 200


@notifications_bp.post("/web-push/unsubscribe")
@login_required
def unsubscribe_web_push():
    from app.extensions import db
    from app.models.web_push_subscription import WebPushSubscription
    from app.services.settings_service import SettingsService
    from flask import current_app

    data = request.get_json(silent=True)
    endpoint = data.get("endpoint") if isinstance(data, dict) else None

    if not isinstance(endpoint, str) or not endpoint or len(endpoint) > 4096:
        return jsonify({
            "success": False,
            "message": "A valid subscription endpoint is required.",
        }), 400

    subscription = WebPushSubscription.query.filter_by(
        endpoint=endpoint,
        user_id=current_user.id,
    ).first()

    if subscription:
        try:
            subscription.is_enabled = False
            subscription.is_active = False

            settings = SettingsService.get(current_user.id)
            preferences = settings.get_preferences()
            preferences.setdefault("notifications", {})["push"] = False
            settings.set_preferences(preferences)

            db.session.commit()

        except Exception:
            db.session.rollback()
            current_app.logger.exception(
                "Failed to disable Web Push subscription for user %s",
                current_user.id,
            )
            return jsonify({
                "success": False,
                "message": "The subscription could not be disabled.",
            }), 500

    return jsonify({
        "success": True,
        "message": "Web Push subscription disabled.",
    })
