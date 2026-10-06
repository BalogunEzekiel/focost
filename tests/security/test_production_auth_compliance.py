import hashlib
from datetime import timedelta

from app.extensions import db
from app.models.compliance import AuthToken, PolicyDocument
from app.services.auth_service import AuthService
from app.utils.timezone import utc_now


def test_auth_token_is_hashed_and_single_use(app, user):
    with app.app_context():
        raw = AuthService.issue_token(
            user.id,
            "password_reset",
            10,
        )

        row = AuthToken.query.filter_by(
            user_id=user.id
        ).one()

        assert row.token_hash != raw

        consumed_user = AuthService.consume_token(
            raw,
            "password_reset",
        )

        assert consumed_user is not None
        assert consumed_user.id == user.id

        assert AuthService.consume_token(
            raw,
            "password_reset",
        ) is None


def test_expired_auth_token_is_rejected(app, user):
    with app.app_context():
        raw = AuthService.issue_token(
            user.id,
            "email_verification",
            10,
        )

        row = AuthToken.query.filter_by(
            user_id=user.id
        ).one()

        row.expires_at = utc_now() - timedelta(seconds=1)

        db.session.commit()

        assert AuthService.consume_token(
            raw,
            "email_verification",
        ) is None


def test_policy_versions_are_seedable(app):
    with app.app_context():
        content_html = "<p>Terms</p>"
        content_hash = hashlib.sha256(
            content_html.encode("utf-8")
        ).hexdigest()

        db.session.add(
            PolicyDocument(
                slug="terms",
                title="Terms",
                version="1.0",
                document_type="terms",
                content_html=content_html,
                content_hash=content_hash,
                effective_at=utc_now(),
                is_current=True,
            )
        )

        db.session.commit()

        policy = (
            PolicyDocument.query
            .filter_by(
                slug="terms",
                is_current=True,
            )
            .one()
        )

        assert policy.version == "1.0"
        assert policy.content_hash == content_hash