from app.extensions import db
from app.models.user_settings import UserSettings


class SettingsService:

    @staticmethod
    def get(user_id):
        settings = UserSettings.query.filter_by(
            user_id=user_id
        ).first()

        if not settings:

            settings = UserSettings(
                user_id=user_id
            )

            settings.set_preferences({})

            db.session.add(settings)
            db.session.commit()

        return settings

    @staticmethod
    def get_preferences(user_id):

        settings = SettingsService.get(
            user_id
        )

        return settings.get_preferences()

    @staticmethod
    def update(user_id, preferences):
        settings = SettingsService.get(user_id)

        # Preserve existing preferences when updating only selected fields.
        existing_preferences = settings.get_preferences()

        merged_preferences = UserSettings._deep_merge(
            existing_preferences,
            preferences or {}
        )

        settings.set_preferences(merged_preferences)

        db.session.commit()

        return settings

    @staticmethod
    def reset(user_id):

        settings = SettingsService.get(
            user_id
        )

        settings.set_preferences({})

        db.session.commit()

        return settings