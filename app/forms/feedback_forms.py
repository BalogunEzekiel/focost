from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional


class FeedbackForm(FlaskForm):
    """Public FOCOST feedback submission form."""

    submitted_name = StringField(
        "Name",
        validators=[
            Optional(),
            Length(max=160),
        ],
    )

    submitted_email = StringField(
        "Email",
        validators=[
            Optional(),
            Email(),
            Length(max=160),
        ],
    )

    category = SelectField(
        "Feedback type",
        choices=[
            ("general", "General Feedback"),
            ("feature", "Feature Request"),
            ("bug", "Bug Report"),
            ("usability", "Usability"),
            ("billing", "Account & Billing"),
            ("security", "Security"),
            ("other", "Other"),
        ],
        validators=[DataRequired()],
    )

    subject = StringField(
        "Subject",
        validators=[
            DataRequired(),
            Length(min=3, max=180),
        ],
    )

    message = TextAreaField(
        "Your feedback",
        validators=[
            DataRequired(),
            Length(min=10, max=5000),
        ],
    )

    rating = IntegerField(
        "How would you rate your FOCOST experience?",
        validators=[
            Optional(),
            NumberRange(min=1, max=5),
        ],
    )

    submit = SubmitField("Send Feedback")


class FeedbackAdminForm(FlaskForm):
    """Administrative feedback workflow form."""

    status = SelectField(
        "Status",
        choices=[
            ("new", "New"),
            ("under_review", "Under Review"),
            ("planned", "Planned"),
            ("in_progress", "In Progress"),
            ("resolved", "Resolved"),
            ("closed", "Closed"),
        ],
        validators=[DataRequired()],
    )

    priority = SelectField(
        "Priority",
        choices=[
            ("low", "Low"),
            ("normal", "Normal"),
            ("high", "High"),
            ("urgent", "Urgent"),
        ],
        validators=[DataRequired()],
    )

    admin_notes = TextAreaField(
        "Internal administrator notes",
        validators=[Optional(), Length(max=5000)],
    )

    submit = SubmitField("Save Review")
