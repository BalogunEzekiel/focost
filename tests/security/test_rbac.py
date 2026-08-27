from app.models.user import User


def test_user_without_role_has_no_permissions(app):

    with app.app_context():

        user = User(
            first_name="RBAC",
            last_name="Test",
            email="rbac@example.com",
        )

        assert user.role is None
        assert user.role_slug is None
        assert user.permissions == set()


def test_user_role_checks_without_role(app):

    with app.app_context():

        user = User(
            first_name="RBAC",
            last_name="Test",
            email="rbac2@example.com",
        )

        assert user.has_role("admin") is False
        assert user.has_any_role(
            "admin",
            "super_admin",
        ) is False

        assert user.has_all_roles(
            "admin",
            "super_admin",
        ) is False