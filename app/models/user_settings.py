import json

from app.extensions import db


class UserSettings(db.Model):
    __tablename__ = "user_settings"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    preferences = db.Column(
        db.Text,
        nullable=False,
        default="{}"
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now()
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "settings",
            uselist=False,
            cascade="all, delete-orphan"
        )
    )

    DEFAULTS = {
        "appearance": {
            "theme": "system",
            "density": "comfortable"
        },

        "widgets": {
            "summary": True,
            "insights": True,
            "budgets": True,
            "goals": True,
            "health": True,
            "recommendations": True,
            "transactions": True
        },

        "analytics": {
            "default_chart": "Income vs Expenses"
        },

        "ai": {
            "daily_brief": True,
            "smart_alerts": True,
            "goal_reminders": True,
            "weekly_report": True
        },

        "notifications": {
            "financial_alerts": True,
            "budget_alerts": True,
            "goal_alerts": True,
            "subscription_alerts": True,
            "ai_usage_alerts": True,
            "insights": True,
            "email": False
        },

        "privacy": {
            "analytics": True
        }
    }

    def get_preferences(self):
        try:
            stored = json.loads(
                self.preferences or "{}"
            )
        except (TypeError, ValueError):
            stored = {}

        return self._deep_merge(
            self.DEFAULTS,
            stored
        )

    def set_preferences(self, preferences):
        merged = self._deep_merge(
            self.DEFAULTS,
            preferences or {}
        )

        self.preferences = json.dumps(
            merged,
            ensure_ascii=False
        )

    @classmethod
    def _deep_merge(cls, base, override):
        result = dict(base)

        for key, value in override.items():

            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = cls._deep_merge(
                    result[key],
                    value
                )
            else:
                result[key] = value

        return result