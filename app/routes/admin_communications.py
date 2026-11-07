from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.rbac.decorators import permission_required
from app.services.announcement_service import AnnouncementService
from app.services.email_service import EmailService
from app.models.announcement import Announcement
from app.models.announcement_user_state import AnnouncementUserState
from app.models.notification import Notification
from app.audit.service import AuditService
from app.extensions import db
import json

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
        sender_options=EmailService.SENDERS,
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
            audience=data.getlist("audience_groups")[:1] and data.getlist("audience_groups")[0] or "all",
            audience_groups=data.getlist("audience_groups") or ["all"],
            priority=data.get("priority", "normal"),
            in_app="in_app" in data,
            dashboard_banner="dashboard_banner" in data,
            flyer="flyer" in data,
            email="email" in data,
            push="push" in data,
            action_url=data.get("action_url", "").strip() or None,
            action_label=data.get("action_label", "").strip() or None,
            image_url=data.get("image_url", "").strip() or None,
            message_background=data.get("message_background", "plain"),
            email_signature_enabled="email_signature_enabled" in data,
            email_signature=data.get("email_signature", "").strip() or None,
            recipient_emails_raw=data.get("recipient_emails", ""),
            sender_identity=data.get("sender_identity", "team"),
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


@admin_communications_bp.route("/<public_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("communications.manage")
def edit(public_id):
    item = Announcement.query.filter_by(public_id=public_id).first_or_404()
    if item.status == "published":
        flash("Published communications cannot be edited. Create a new draft instead.", "warning")
        return redirect(url_for("admin_communications.index"))
    if request.method == "POST":
        data = request.form
        try:
            audiences = AnnouncementService.normalize_audiences(data.getlist("audience_groups"))
            item.title = data.get("title", "").strip()
            item.message = AnnouncementService.sanitize_message(data.get("message", ""))
            if not item.title or not AnnouncementService.plain_text(item.message):
                raise ValueError("A title and message are required.")
            item.audience = audiences[0]
            item.audience_groups = json.dumps(audiences)
            item.announcement_type = data.get("announcement_type", "notice")
            item.priority = data.get("priority", "normal")
            item.in_app = "in_app" in data
            item.dashboard_banner = "dashboard_banner" in data
            item.flyer = "flyer" in data
            item.email = "email" in data
            item.push = "push" in data
            item.action_url = data.get("action_url", "").strip() or None
            item.action_label = data.get("action_label", "").strip() or None
            item.image_url = data.get("image_url", "").strip() or None
            item.message_background = data.get("message_background", "plain")
            item.email_signature_enabled = "email_signature_enabled" in data
            item.email_signature = AnnouncementService.sanitize_message(data.get("email_signature", "").strip()) or None
            item.recipient_emails = json.dumps(AnnouncementService.normalize_individual_emails(data.get("recipient_emails", "")))
            item.sender_identity = AnnouncementService.normalize_sender(data.get("sender_identity", "team"))
            item.action_url = AnnouncementService.validate_url(item.action_url, "Action URL")
            item.image_url = AnnouncementService.validate_url(item.image_url, "Image/Flyer URL")
            if data.get("publish") == "1":
                AnnouncementService.publish(item, current_user.id)
            else:
                db.session.commit()
            flash("Communication updated successfully.", "success")
        except Exception as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        return redirect(url_for("admin_communications.index"))
    return render_template("admin/communications_edit.html", item=item,
                           audience_options=AnnouncementService.audience_options(),
                           sender_options=EmailService.SENDERS)


@admin_communications_bp.post("/<public_id>/delete")
@login_required
@permission_required("communications.manage")
def delete(public_id):
    item = Announcement.query.filter_by(public_id=public_id).first_or_404()
    try:
        # Remove per-user dismissal/read state and generated in-app
        # notification copies before deleting the source communication.
        AnnouncementUserState.query.filter_by(
            announcement_id=item.id
        ).delete(synchronize_session=False)
        Notification.query.filter_by(
            unique_key=f"ANNOUNCEMENT:{item.public_id}"
        ).delete(synchronize_session=False)
        db.session.delete(item)
        db.session.commit()
        flash("Communication and its generated notification copies deleted.", "success")
    except Exception:
        db.session.rollback()
        flash("Unable to delete this communication because a related record prevents deletion.", "danger")
    return redirect(url_for("admin_communications.index"))
