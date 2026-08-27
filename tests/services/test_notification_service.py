from app.extensions import db
from app.models.notification import Notification
from app.services.notification_service import NotificationService


def test_create_notification(app, user):

    with app.app_context():

        notification = NotificationService.create(
            user_id=user.id,
            title="Test Notification",
            message="This is a test.",
            notification_type="test",
            unique_key="TEST_001",
        )

        assert notification.id is not None
        assert notification.user_id == user.id
        assert notification.title == "Test Notification"


def test_duplicate_notification_is_not_created(app, user):

    with app.app_context():

        first = NotificationService.create(
            user_id=user.id,
            title="Duplicate Test",
            message="First",
            unique_key="DUPLICATE_001",
        )

        second = NotificationService.create(
            user_id=user.id,
            title="Duplicate Test",
            message="Second",
            unique_key="DUPLICATE_001",
        )

        assert first.id == second.id

        count = Notification.query.filter_by(
            user_id=user.id,
            unique_key="DUPLICATE_001",
        ).count()

        assert count == 1


def test_unread_count(app, user):

    with app.app_context():

        NotificationService.create(
            user_id=user.id,
            title="One",
            message="One",
        )

        NotificationService.create(
            user_id=user.id,
            title="Two",
            message="Two",
        )

        assert NotificationService.get_unread_count(user.id) == 2


def test_mark_read(app, user):

    with app.app_context():

        notification = NotificationService.create(
            user_id=user.id,
            title="Read Me",
            message="Please read.",
        )

        result = NotificationService.mark_read(
            notification.id,
            user.id,
        )

        assert result is True
        assert notification.is_read is True


def test_mark_all_read(app, user):

    with app.app_context():

        for i in range(3):

            NotificationService.create(
                user_id=user.id,
                title=f"Notification {i}",
                message="Test",
            )

        count = NotificationService.mark_all_read(user.id)

        assert count == 3
        assert NotificationService.get_unread_count(user.id) == 0


def test_delete_notification(app, user):

    with app.app_context():

        notification = NotificationService.create(
            user_id=user.id,
            title="Delete",
            message="Delete me.",
        )

        notification_id = notification.id

        result = NotificationService.delete(
            notification_id,
            user.id,
        )

        assert result is True

        assert NotificationService.get(
            notification_id,
            user.id,
        ) is None