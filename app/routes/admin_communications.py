from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.rbac.decorators import permission_required
from app.services.announcement_service import AnnouncementService
from app.models.announcement import Announcement
from app.audit.service import AuditService

admin_communications_bp = Blueprint("admin_communications", __name__, url_prefix="/admin/communications")


@admin_communications_bp.get("/")
@login_required
@permission_required("communications.view")
def index():
    items = Announcement.query.order_by(Announcement.created_at.desc()).limit(100).all()
    return render_template(
        "admin/communications.html",
        announcements=items,
        audience_options=AnnouncementService.audience_options(),
    )


@admin_communications_bp.post("/create")
@login_required
@permission_required("communications.manage")
def create():
    data = request.form
    try:
        item = AnnouncementService.create(
            title=data.get("title", "").strip(),
            message=data.get("message", "").strip(),
            announcement_type=data.get("announcement_type", "notice"),
            audience=data.get("audience", "all"),
            priority=data.get("priority", "normal"),
            in_app="in_app" in data,
            dashboard_banner="dashboard_banner" in data,
            flyer="flyer" in data,
            email="email" in data,
            push="push" in data,
            action_url=data.get("action_url", "").strip() or None,
            image_url=data.get("image_url", "").strip() or None,
        )
        if data.get("publish") == "1":
            AnnouncementService.publish(item, current_user.id)
        AuditService.log(
            action="communications.created",
            category="ADMIN",
            resource="Announcement",
            resource_id=item.public_id,
            description=f"Created communication: {item.title}",
        )
        flash("Communication created successfully.", "success")
    except Exception as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin_communications.index"))


@admin_communications_bp.post("/<public_id>/publish")
@login_required
@permission_required("communications.manage")
def publish(public_id):
    item = Announcement.query.filter_by(public_id=public_id).first_or_404()
    try:
        AnnouncementService.publish(item, current_user.id)
        flash("Communication published.", "success")
    except Exception as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin_communications.index"))
