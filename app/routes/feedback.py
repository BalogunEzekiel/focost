from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.audit.service import AuditService
from app.forms.feedback_forms import FeedbackForm
from app.services.feedback_service import FeedbackService


feedback_bp = Blueprint(
    "feedback",
    __name__,
    url_prefix="/feedback",
)


@feedback_bp.route("/", methods=["GET", "POST"])
def submit():
    form = FeedbackForm()

    if current_user.is_authenticated and request.method == "GET":
        form.submitted_name.data = (
            f"{current_user.first_name} {current_user.last_name}"
        ).strip()
        form.submitted_email.data = current_user.email

    if form.validate_on_submit():
        submitted_name = form.submitted_name.data
        submitted_email = form.submitted_email.data

        if current_user.is_authenticated:
            submitted_name = (
                f"{current_user.first_name} {current_user.last_name}"
            ).strip()
            submitted_email = current_user.email

        feedback = FeedbackService.create(
            submitted_by_id=(
                current_user.id
                if current_user.is_authenticated
                else None
            ),
            submitted_name=submitted_name,
            submitted_email=submitted_email,
            category=form.category.data,
            subject=form.subject.data,
            message=form.message.data,
            rating=form.rating.data,
        )

        AuditService.log(
            action="feedback.submitted",
            category="feedback",
            resource="Feedback",
            resource_id=feedback.public_id,
            description="Public feedback submitted.",
        )

        flash(
            "Thank you. Your feedback has been received by the FOCOST team.",
            "success",
        )

        return redirect(url_for("feedback.submit"))

    return render_template(
        "feedback.html",
        form=form,
    )
