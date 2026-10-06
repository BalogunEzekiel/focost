from app.extensions import db
from app.models.base import BaseModel


class Feedback(BaseModel):
    """
    Central record for public and authenticated FOCOST feedback.

    Anonymous submissions are supported by allowing submitted_by_id to be
    NULL while retaining the contact details supplied with the submission.
    Administrative workflow is tracked directly on the record.
    """

    __tablename__ = "feedback"

    __table_args__ = (
        db.CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 5)",
            name="ck_feedback_rating_range",
        ),
        db.Index(
            "ix_feedback_status_created_at",
            "status",
            "created_at",
        ),
        db.Index(
            "ix_feedback_category_created_at",
            "category",
            "created_at",
        ),
        db.Index(
            "ix_feedback_priority_created_at",
            "priority",
            "created_at",
        ),
    )

    submitted_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    reviewed_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    submitted_name = db.Column(
        db.String(160),
        nullable=True,
    )

    submitted_email = db.Column(
        db.String(160),
        nullable=True,
        index=True,
    )

    category = db.Column(
        db.String(40),
        nullable=False,
        default="general",
        index=True,
    )

    subject = db.Column(
        db.String(180),
        nullable=False,
    )

    message = db.Column(
        db.Text,
        nullable=False,
    )

    rating = db.Column(
        db.Integer,
        nullable=True,
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="new",
        index=True,
    )

    priority = db.Column(
        db.String(20),
        nullable=False,
        default="normal",
        index=True,
    )

    admin_notes = db.Column(
        db.Text,
        nullable=True,
    )

    reviewed_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    submitted_by = db.relationship(
        "User",
        foreign_keys=[submitted_by_id],
        backref=db.backref(
            "submitted_feedback",
            lazy="dynamic",
        ),
    )

    reviewed_by = db.relationship(
        "User",
        foreign_keys=[reviewed_by_id],
        backref=db.backref(
            "reviewed_feedback",
            lazy="dynamic",
        ),
    )

    @property
    def submitter_display_name(self):
        if self.submitted_by:
            full_name = (
                f"{self.submitted_by.first_name} "
                f"{self.submitted_by.last_name}"
            ).strip()
            return full_name or self.submitted_by.email

        return self.submitted_name or "Anonymous visitor"

    @property
    def category_label(self):
        return {
            "general": "General Feedback",
            "feature": "Feature Request",
            "bug": "Bug Report",
            "usability": "Usability",
            "billing": "Account & Billing",
            "security": "Security",
            "other": "Other",
        }.get(self.category, self.category.replace("_", " ").title())

    @property
    def status_label(self):
        return {
            "new": "New",
            "under_review": "Under Review",
            "planned": "Planned",
            "in_progress": "In Progress",
            "resolved": "Resolved",
            "closed": "Closed",
        }.get(self.status, self.status.replace("_", " ").title())

    @property
    def priority_label(self):
        return self.priority.title()

    def __repr__(self):
        return f"<Feedback {self.public_id} {self.status}>"
