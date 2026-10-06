from app.models.feedback import Feedback
from app.services.feedback_service import FeedbackService


def test_feedback_service_creates_and_updates_review(db_session, user):
    item = FeedbackService.create(
        submitted_by_id=user.id,
        submitted_name="Test User",
        submitted_email=user.email,
        category="general",
        subject="Useful dashboard",
        message="The dashboard is clear and useful.",
        rating=4,
    )

    assert item.status == "new"
    assert item.priority == "normal"
    assert item.submitted_by_id == user.id

    FeedbackService.update_review(
        item,
        status="under_review",
        priority="high",
        admin_notes="Review during the next product planning cycle.",
        reviewed_by_id=user.id,
    )

    refreshed = db_session.get(Feedback, item.id)

    assert refreshed.status == "under_review"
    assert refreshed.priority == "high"
    assert refreshed.reviewed_by_id == user.id
    assert refreshed.reviewed_at is not None


def test_feedback_service_statistics(db_session):
    FeedbackService.create(
        submitted_name="Visitor",
        submitted_email="visitor@example.com",
        category="bug",
        subject="Example bug",
        message="This is an example issue for statistics.",
    )

    stats = FeedbackService.statistics()

    assert stats["total"] == 1
    assert stats["new"] == 1
