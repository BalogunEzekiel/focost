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
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
def dismiss(notification_id):
    success = NotificationService.dismiss(notification_id, current_user.id)
    return jsonify({"success": success, "notification_count": NotificationService.get_unread_count(current_user.id)})


# ---------------------------------------------------------
# Delete Notification
# ---------------------------------------------------------

@notifications_bp.route("/delete/<int:notification_id>", methods=["POST"])
@login_required
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
@login_required
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
@login_required
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