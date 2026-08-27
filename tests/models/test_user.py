from app.models.user import User


def test_user_password_hashing(app):

    with app.app_context():

        user = User(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
        )

        user.set_password("StrongPassword123!")

        assert user.password_hash
        assert user.password_hash != "StrongPassword123!"

        assert user.check_password("StrongPassword123!") is True
        assert user.check_password("WrongPassword") is False


def test_user_role_defaults(app):

    with app.app_context():

        user = User(
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
        )

        assert user.role is None
        assert user.role_slug is None
        assert user.primary_role is None
        assert user.roles_list == []
        assert user.is_super_admin is False


def test_user_permission_without_role(app):

    with app.app_context():

        user = User(
            first_name="Permission",
            last_name="Test",
            email="permission@example.com",
        )

        assert user.has_permission("test.permission") is False
        assert user.permissions == set()
        assert user.has_any_permission("a", "b") is False
        assert user.has_all_permissions("a", "b") is False