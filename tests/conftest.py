import pytest

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.user_role import UserRole
from app.rbac.service import RBACService
from app.seeds.rbac_seed import RBACSeed


@pytest.fixture()
def app():
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "APP_ENV": "testing",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": True,
            "LOGIN_DISABLED": False,
        }
    )

    with application.app_context():
        # Hard safety verification:
        # tests must NEVER use the real FOCOST database.
        assert application.config["SQLALCHEMY_DATABASE_URI"] in {
            "sqlite:///:memory:",
            "sqlite://",
        }

        assert db.engine.url.drivername == "sqlite"
        assert db.engine.url.database == ":memory:"

        db.session.expire_on_commit = False

        db.create_all()

        # ------------------------------------------------------
        # TEST RBAC INITIALIZATION
        # ------------------------------------------------------
        #
        # Reuse the application's existing RBAC seed definitions.
        # This creates the same system roles, permissions and
        # default User-role permissions used by the application.
        #
        # We intentionally DO NOT call seed_super_admin().
        # Tests must not create or depend on a real Super Admin.
        # ------------------------------------------------------

        RBACSeed.seed_roles()
        RBACSeed.seed_permissions()
        RBACSeed.assign_default_user_permissions()

        yield application

        # Remove the session only.
        #
        # We intentionally do NOT call db.drop_all().
        # The database is an in-memory test database and disappears
        # with the test application's database lifecycle. More
        # importantly, there must be no destructive teardown capable
        # of touching a physical FOCOST database.
        db.session.remove()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


@pytest.fixture()
def user(app):
    with app.app_context():
        test_user = User(
            first_name="Test",
            last_name="User",
            email="testuser@example.com",
            phone="08000000000",
            country="Nigeria",
            currency="NGN",
            occupation="Tester",
        )

        test_user.set_password("TestPassword123!")

        db.session.add(test_user)
        db.session.flush()

        # Give the test user the same default role that a newly
        # registered normal FOCOST user receives.
        RBACService.assign_default_role(test_user)

        db.session.commit()

        yield test_user


@pytest.fixture()
def authenticated_client(client, user):
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True

    return client


@pytest.fixture()
def db_session(app):
    with app.app_context():
        yield db.session
