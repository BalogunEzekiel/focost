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
