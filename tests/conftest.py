import os

import pytest

from app import create_app
from app.extensions import db
from app.models.user import User


@pytest.fixture(scope="session")
def app():
    """
    Create a dedicated Flask application for the test suite.

    The test database is isolated from the developer's normal database.
    """

    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["FLASK_ENV"] = "testing"

    application = create_app()

    application.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        LOGIN_DISABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
    )

    with application.app_context():
        db.create_all()

        yield application

        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


@pytest.fixture()
def db_session(app):
    with app.app_context():
        yield db.session


@pytest.fixture()
def user(app):
    """
    Create a normal test user.
    """

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
        db.session.commit()

        return test_user


@pytest.fixture()
def authenticated_client(client, user):
    """
    Authenticate through Flask-Login without depending on
    the authentication form implementation.
    """

    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True

    return client