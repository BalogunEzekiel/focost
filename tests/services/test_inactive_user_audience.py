import json

from app.models.announcement import Announcement
from app.models.user_role import UserRole
from app.services.announcement_service import AnnouncementService
from app.extensions import db
from app.models.user import User


def test_inactive_user_is_a_selectable_audience():
    options = dict(AnnouncementService.audience_options())
    assert options["inactive_user"] == "Inactive User"


def test_inactive_user_can_be_combined_with_other_groups_but_not_all():
    assert AnnouncementService.normalize_audiences(
        ["inactive_user", "user", "basic"]
    ) == ["inactive_user", "user", "basic"]

    try:
        AnnouncementService.normalize_audiences(["all", "inactive_user"])
    except ValueError as exc:
        assert "All Audiences cannot be combined" in str(exc)
    else:
        raise AssertionError("All Audiences must remain exclusive")


def test_pending_normal_user_matches_inactive_user_group(app, user):
    with app.app_context():
        user.is_active = False
        user.email_verified = False
        db.session.commit()

        item = Announcement(
            title="Verify your account",
            message="Please verify your email.",
            audience="inactive_user",
            audience_groups=json.dumps(["inactive_user"]),
        )
        assert AnnouncementService.can_receive(item, user.id) is True


def test_verified_deactivated_user_is_not_inactive_user_audience(app, user):
    with app.app_context():
        user.is_active = False
        user.email_verified = True
        db.session.commit()

        item = Announcement(
            title="Account status",
            message="Please contact support.",
            audience="inactive_user",
            audience_groups=json.dumps(["inactive_user"]),
        )
        assert AnnouncementService.can_receive(item, user.id) is False


def test_closed_account_without_normal_user_role_is_excluded(app, user):
    with app.app_context():
        user_id = user.id

        user = db.session.get(User, user_id)
        assert user is not None

        user.first_name = "Deleted"
        user.last_name = "User"
        user.email = f"deleted+{user.public_id}@deleted.focost.invalid"
        user.is_active = False
        user.email_verified = False

        UserRole.query.filter_by(
            user_id=user_id
        ).delete(synchronize_session=False)

        db.session.commit()

        # Reload from the database with the role relationship.
        user = (
            User.query
            .filter_by(id=user_id)
            .populate_existing()
            .first()
        )

        assert user is not None
        assert user.role_assignment is None
        assert user.role_group is None

        item = Announcement(
            title="Verify your account",
            message="Please verify your email.",
            audience="inactive_user",
            audience_groups=json.dumps(["inactive_user"]),
        )

        assert AnnouncementService.can_receive(
            item,
            user_id,
        ) is False