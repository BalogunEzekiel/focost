from datetime import timedelta
import hashlib
import secrets

from app.extensions import db
from app.models.compliance import AuthToken, AuthThrottle
from app.utils.timezone import as_utc, utc_now


class AuthService:
    @staticmethod
    def _hash(raw):
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def issue_token(user_id, purpose, minutes):
        raw = secrets.token_urlsafe(48)

        db.session.add(
            AuthToken(
                user_id=user_id,
                token_hash=AuthService._hash(raw),
                purpose=purpose,
                expires_at=utc_now() + timedelta(minutes=minutes),
            )
        )

        db.session.commit()
        return raw

    @staticmethod
    def consume_token(raw, purpose):
        if not raw:
            return None

        token = AuthToken.query.filter_by(
            token_hash=AuthService._hash(raw),
            purpose=purpose,
        ).first()

        if (
            not token
            or token.used_at
            or as_utc(token.expires_at) < utc_now()
        ):
            return None

        token.used_at = utc_now()
        db.session.commit()

        return token.user

    @staticmethod
    def revoke_tokens(user_id, purpose):
        AuthToken.query.filter_by(
            user_id=user_id,
            purpose=purpose,
            used_at=None,
        ).update(
            {"used_at": utc_now()},
            synchronize_session=False,
        )

        db.session.commit()

    @staticmethod
    def throttle(key, limit, window_seconds, block_seconds):
        now = utc_now()

        row = AuthThrottle.query.filter_by(
            throttle_key=key
        ).first()

        if row:
            blocked_until = as_utc(row.blocked_until)

            if blocked_until and blocked_until > now:
                return False

        if (
            not row
            or (
                now - as_utc(row.window_started_at)
            ).total_seconds() >= window_seconds
        ):
            if not row:
                row = AuthThrottle(
                    throttle_key=key,
                    attempts=0,
                    window_started_at=now,
                )
                db.session.add(row)

            row.attempts = 0
            row.window_started_at = now
            row.blocked_until = None

        row.attempts += 1

        if row.attempts > limit:
            row.blocked_until = now + timedelta(
                seconds=block_seconds
            )
            db.session.commit()
            return False

        db.session.commit()
        return True

    @staticmethod
    def reset_throttle(key):
        row = AuthThrottle.query.filter_by(
            throttle_key=key
        ).first()

        if row:
            db.session.delete(row)
            db.session.commit()