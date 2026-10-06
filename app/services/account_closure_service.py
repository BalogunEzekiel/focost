from pathlib import Path
import secrets

from flask import current_app

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.user_role import UserRole
from app.models.income import Income
from app.models.expense import Expense
from app.models.budget import Budget
from app.models.asset import Asset
from app.models.goal import Goal
from app.models.category import FinancialCategory
from app.models.notification import Notification
from app.models.user_settings import UserSettings
from app.models.chat_session import ChatSession
from app.models.feedback import Feedback


class AccountClosureService:
    """
    Authoritative account-closure/anonymization service.

    A closed FOCOST account is NOT physically deleted.

    User-owned application/financial data is removed where appropriate,
    while the User row remains as a minimized anchor so that required
    compliance, consent, payment, security, and audit evidence can remain
    associated with the account.

    PolicyAcceptance records are deliberately retained.
    """

    @staticmethod
    def close_account(user, *, audit_action="account.deleted_anonymized"):
        """
        Permanently close and anonymize a user account.

        This method intentionally does NOT delete the User row.

        Retained:
            - User identity anchor in minimized form
            - PolicyAcceptance records
            - Payment/subscription records
            - Required compliance/security evidence

        Removed:
            - User-owned financial/application data
            - Application roles
            - User avatar file

        De-identified:
            - Feedback submitter information
            - Existing audit-log user references
        """
        if not user:
            raise ValueError("User is required.")

        public_id = user.public_id

        # ----------------------------------------------------------
        # REMOVE USER AVATAR
        # ----------------------------------------------------------

        if user.avatar and user.avatar.startswith("uploads/avatars/"):
            avatar_path = Path(current_app.instance_path) / user.avatar

            if avatar_path.exists():
                try:
                    avatar_path.unlink()
                except OSError:
                    current_app.logger.warning(
                        "Unable to remove closed user's avatar: %s",
                        avatar_path,
                    )

        # ----------------------------------------------------------
        # DELETE USER-OWNED APPLICATION / FINANCIAL DATA
        # ----------------------------------------------------------

        Income.query.filter_by(
            user_id=user.id
        ).delete(synchronize_session=False)

        Expense.query.filter_by(
            user_id=user.id
        ).delete(synchronize_session=False)

        Budget.query.filter_by(
            user_id=user.id
        ).delete(synchronize_session=False)

        Asset.query.filter_by(
            user_id=user.id
        ).delete(synchronize_session=False)

        Goal.query.filter_by(
            user_id=user.id
        ).delete(synchronize_session=False)

        FinancialCategory.query.filter_by(
            user_id=user.id
        ).delete(synchronize_session=False)

        Notification.query.filter_by(
            user_id=user.id
        ).delete(synchronize_session=False)

        UserSettings.query.filter_by(
            user_id=user.id
        ).delete(synchronize_session=False)

        ChatSession.query.filter_by(
            user_id=user.id
        ).delete(synchronize_session=False)

        # ----------------------------------------------------------
        # DE-IDENTIFY FEEDBACK
        # ----------------------------------------------------------

        Feedback.query.filter_by(
            submitted_by_id=user.id
        ).update(
            {
                "submitted_by_id": None,
                "submitted_name": "Deleted User",
                "submitted_email": None,
            },
            synchronize_session=False,
        )

        # ----------------------------------------------------------
        # MINIMIZE THE USER RECORD
        # ----------------------------------------------------------

        user.first_name = "Deleted"
        user.last_name = "User"
        user.email = (
            f"deleted+{public_id}@deleted.focost.invalid"
        )
        user.phone = None
        user.country = None
        user.currency = None
        user.occupation = None
        user.monthly_income = 0
        user.avatar = "default-avatar.png"

        user.email_verified = False
        user.is_active = False

        # Invalidate existing authenticated sessions/tokens.
        user.auth_version += 1

        # Replace the password with an unusable random value.
        user.password_hash = secrets.token_urlsafe(48)

        # ----------------------------------------------------------
        # REMOVE APPLICATION ROLE ACCESS
        # ----------------------------------------------------------

        UserRole.query.filter_by(
            user_id=user.id
        ).delete(synchronize_session=False)

        # ----------------------------------------------------------
        # RETAIN AUDIT EVIDENCE BUT REMOVE PERSONAL USER LINK
        # ----------------------------------------------------------

        AuditLog.query.filter_by(
            user_id=user.id
        ).update(
            {
                "user_id": None,
            },
            synchronize_session=False,
        )

        # ----------------------------------------------------------
        # CREATE FINAL ACCOUNT-CLOSURE AUDIT EVENT
        # ----------------------------------------------------------

        db.session.add(
            AuditLog(
                user_id=None,
                action=audit_action,
                category="SECURITY",
                resource="User",
                resource_id=public_id,
                description=(
                    "User account closed; personal data minimized while "
                    "required operational, compliance, payment, security "
                    "and legal evidence was retained."
                ),
            )
        )

        # ----------------------------------------------------------
        # IMPORTANT:
        # Do NOT delete PolicyAcceptance.
        #
        # Do NOT delete UserSubscription.
        # Do NOT delete PaymentTransaction.
        # Do NOT delete required compliance evidence.
        #
        # The User row remains specifically so these records retain
        # their legitimate relational anchor.
        # ----------------------------------------------------------

        db.session.commit()

        return user