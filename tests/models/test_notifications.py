from datetime import datetime, timedelta

from app.models.notification import Notification


def make_notification():

    return Notification(
        user_id=1,
        title="Budget Alert",
        message="Your budget is almost exhausted.",
        notification_type="budget",
        source="System",
        priority="normal",
        level="warning",
        icon="bi-wallet2",
        unique_key="TEST_BUDGET_001",
        is_read=False,
        is_deleted=False,
        created_at=datetime.utcnow(),
    )


def test_notification_mark_as_read(app):

    with app.app_context():

        notification = make_notification()

        assert notification.is_read is False

        notification.mark_as_read()

        assert notification.is_read is True
        assert notification.read_at is not None


def test_notification_soft_delete(app):

    with app.app_context():

        notification = make_notification()

        assert notification.is_deleted is False

        notification.soft_delete()

        assert notification.is_deleted is True


def test_notification_to_dict(app):

    with app.app_context():

        notification = make_notification()

        data = notification.to_dict()

        assert data["title"] == "Budget Alert"
        assert data["message"] == (
            "Your budget is almost exhausted."
        )
        assert data["notification_type"] == "budget"
        assert data["level"] == "warning"
        assert data["is_read"] is False
        assert data["is_deleted"] is False


def test_notification_time(app):

    with app.app_context():

        notification = make_notification()

        notification.created_at = datetime.utcnow()

        assert notification.time == "Just now"