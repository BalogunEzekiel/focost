from flask import Blueprint, jsonify
from flask_login import login_required, current_user

from app.models.announcement import Announcement
from app.services.announcement_service import AnnouncementService


communications_bp = Blueprint(
    "communications",
    __name__,
    url_prefix="/communications"
)


@communications_bp.post("/<public_id>/dismiss")
@login_required
def dismiss_announcement(public_id):

    announcement = Announcement.query.filter_by(
        public_id=public_id
    ).first_or_404()

    if not AnnouncementService.can_receive(
        announcement,
        current_user.id,
    ):
        return jsonify({
            "success": False,
            "message": "Communication is not available to this account.",
        }), 404

    AnnouncementService.dismiss(
        announcement.id,
        current_user.id,
    )

    return jsonify({
        "success": True,
        "public_id": announcement.public_id,
    })