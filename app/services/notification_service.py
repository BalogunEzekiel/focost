from datetime import datetime, date

from sqlalchemy import func

from app.extensions import db
from app.models.notification import Notification


class NotificationService:
    """
    ===========================================================
    Centralized Notification Service
    ===========================================================

    Used throughout FOCOST by:

    - Dashboard
    - Income
    - Expenses
    - Budgets
    - Goals
    - Reports
    - AI Coach
    - Tax Engine
    - Settings
    - Top Navigation
    """

    DEFAULT_LIMIT = 10

    # ==========================================================
    # Create Notification
    # ==========================================================

    # ==========================================================
    # Create Notification
    # ==========================================================

    @staticmethod
    def create(
        user_id,
        title,
        message,
        level="info",
        notification_type="general",
        action_url=None,
        icon=None,
        unique_key=None,
        commit=True,
    ):
        """
        Creates a notification.

        If an unread notification with the same unique_key already
        exists, no new notification is created.

        Once the user reads or deletes it, another one may be created.
        """

        # --------------------------------------------
        # Duplicate Protection
        # --------------------------------------------

        if unique_key:

            existing = (
                Notification.query
                .filter(
                    Notification.user_id == user_id,
                    Notification.unique_key == unique_key,
                    Notification.is_read == False,
                    Notification.is_deleted == False,
                )
                .first()
            )

            if existing:
                return existing

        notification = Notification(

            user_id=user_id,

            title=title,

            message=message,

            level=level,

            notification_type=notification_type,

            action_url=action_url,

            icon=icon,

            unique_key=unique_key,

            created_at=datetime.utcnow(),

        )

        db.session.add(notification)

        if commit:
            db.session.commit()

        return notification

    # ==========================================================
    # Get Notification
    # ==========================================================

    @staticmethod
    def get(notification_id, user_id=None):
        """
        Get one notification.
        """

        query = Notification.query.filter_by(
            id=notification_id
        )

        if user_id is not None:
            query = query.filter_by(
                user_id=user_id
            )

        return query.first()

    # ==========================================================
    # Recent Notifications
    # ==========================================================

    @staticmethod
    def get_recent(
        user_id,
        limit=DEFAULT_LIMIT
    ):
        """
        Latest notifications.
        """

        return (
            Notification.query
            .filter_by(user_id=user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .all()
        )

    # ==========================================================
    # All Notifications
    # ==========================================================

    @staticmethod
    def get_all(user_id):

        return (
            Notification.query
            .filter_by(user_id=user_id)
            .order_by(Notification.created_at.desc())
            .all()
        )

    # ==========================================================
    # Notifications By Type
    # ==========================================================

    @staticmethod
    def get_by_type(
        user_id,
        notification_type,
        limit=None,
    ):
        """
        Examples:

        NotificationService.get_by_type(
            user_id,
            "budget"
        )
        """

        query = (
            Notification.query
            .filter_by(
                user_id=user_id,
                notification_type=notification_type,
            )
            .order_by(
                Notification.created_at.desc()
            )
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    # ==========================================================
    # Unread Notifications
    # ==========================================================

    @staticmethod
    def get_unread(user_id):

        return (
            Notification.query
            .filter_by(
                user_id=user_id,
                is_read=False,
            )
            .order_by(
                Notification.created_at.desc()
            )
            .all()
        )

    # ==========================================================
    # Unread Count
    # ==========================================================

    @staticmethod
    def get_unread_count(user_id):

        return (
            Notification.query
            .filter_by(
                user_id=user_id,
                is_read=False,
            )
            .count()
        )

    # ==========================================================
    # Total Count
    # ==========================================================

    @staticmethod
    def get_total_count(user_id):

        return (
            Notification.query
            .filter_by(
                user_id=user_id
            )
            .count()
        )

    # ==========================================================
    # Mark Read
    # ==========================================================

    @staticmethod
    def mark_read(
        notification_id,
        user_id=None,
    ):

        notification = NotificationService.get(
            notification_id,
            user_id,
        )

        if notification is None:
            return False

        if not notification.is_read:

            notification.is_read = True
            notification.read_at = datetime.utcnow()

            db.session.commit()

        return True

    # ==========================================================
    # Mark All Read
    # ==========================================================

    @staticmethod
    def mark_all_read(user_id):

        notifications = (
            Notification.query
            .filter_by(
                user_id=user_id,
                is_read=False,
            )
            .all()
        )

        now = datetime.utcnow()

        for notification in notifications:

            notification.is_read = True
            notification.read_at = now

        db.session.commit()

        return len(notifications)

    # ==========================================================
    # Delete Notification
    # ==========================================================

    @staticmethod
    def delete(
        notification_id,
        user_id=None,
    ):

        notification = NotificationService.get(
            notification_id,
            user_id,
        )

        if notification is None:
            return False

        db.session.delete(notification)

        db.session.commit()

        return True

    # ==========================================================
    # Delete All Notifications
    # ==========================================================

    @staticmethod
    def delete_all(user_id):

        notifications = (
            Notification.query
            .filter_by(user_id=user_id)
            .all()
        )

        count = len(notifications)

        for notification in notifications:
            db.session.delete(notification)

        db.session.commit()

        return count

    # ==========================================================
    # Dashboard Summary
    # ==========================================================

    @staticmethod
    def summary(user_id):
        """
        Data used by the bell dropdown and dashboard.
        """

        return {

            "notifications": NotificationService.get_recent(
                user_id,
                limit=5,
            ),

            "notification_count": NotificationService.get_unread_count(
                user_id
            ),

            "total_notifications": NotificationService.get_total_count(
                user_id
            ),

            "unread_notifications": NotificationService.get_unread(
                user_id
            ),
        }
    
    # ==========================================================
    # Budget Notification
    # ==========================================================

    @staticmethod
    def budget_exceeded(
        user_id,
        budget_name,
        amount,
        action_url=None,
        commit=True,
    ):
        return NotificationService.create(
            user_id=user_id,
            title="Budget Exceeded",
            message=f"{budget_name} exceeded by ₦{amount:,.2f}.",
            level="warning",
            notification_type="budget",
            icon="bi-exclamation-triangle-fill",
            action_url=action_url,
            commit=commit,
        )

    # ==========================================================
    # Budget Warning
    # ==========================================================

    @staticmethod
    def budget_warning(
        user_id,
        budget_name,
        percentage,
        action_url=None,
        commit=True,
    ):
        return NotificationService.create(
            user_id=user_id,
            title="Budget Warning",
            message=(
                f"{budget_name} budget has reached "
                f"{percentage:.0f}%."
            ),
            level="info",
            notification_type="budget",
            icon="bi-wallet2",
            action_url=action_url,
            commit=commit,
        )

    # ==========================================================
    # Budget Critical
    # ==========================================================

    @staticmethod
    def budget_critical(
        user_id,
        budget_name,
        percentage,
        action_url=None,
        commit=True,
    ):
        return NotificationService.create(
            user_id=user_id,
            title="Budget Critical",
            message=(
                f"{budget_name} budget has reached "
                f"{percentage:.0f}%."
            ),
            level="warning",
            notification_type="budget",
            icon="bi-wallet2",
            action_url=action_url,
            commit=commit,
        )

    # ==========================================================
    # Goal Completed
    # ==========================================================

    @staticmethod
    def goal_completed(
        user_id,
        goal_name,
        action_url=None,
        commit=True,
    ):
        return NotificationService.create(
            user_id=user_id,
            title="Goal Achieved",
            message=f"You achieved your '{goal_name}' goal.",
            level="success",
            notification_type="goal",
            icon="bi-trophy-fill",
            action_url=action_url,
            commit=commit,
        )

    # ==========================================================
    # Goal Due
    # ==========================================================

    @staticmethod
    def goal_due(
        user_id,
        goal_name,
        days_remaining,
        action_url=None,
        commit=True,
    ):
        return NotificationService.create(
            user_id=user_id,
            title="Goal Due",
            message=(
                f"Your goal '{goal_name}' "
                f"is due in {days_remaining} day(s)."
            ),
            level="warning",
            notification_type="goal",
            icon="bi-flag-fill",
            action_url=action_url,
            commit=commit,
        )

    # ==========================================================
    # Goal Behind Schedule
    # ==========================================================

    @staticmethod
    def goal_behind(
        user_id,
        goal_name,
        percentage,
        action_url=None,
        commit=True,
    ):
        return NotificationService.create(
            user_id=user_id,
            title="Goal Behind Schedule",
            message=(
                f"'{goal_name}' is only "
                f"{percentage:.0f}% funded."
            ),
            level="info",
            notification_type="goal",
            icon="bi-bullseye",
            action_url=action_url,
            commit=commit,
        )

    # ==========================================================
    # Low Balance
    # ==========================================================

    @staticmethod
    def low_balance(
        user_id,
        balance,
        action_url=None,
        commit=True,
    ):
        return NotificationService.create(
            user_id=user_id,
            title="Low Balance",
            message=f"Current balance is ₦{balance:,.2f}.",
            level="danger",
            notification_type="system",
            icon="bi-wallet2",
            action_url=action_url,
            commit=commit,
        )

    # ==========================================================
    # Income Recorded
    # ==========================================================

    @staticmethod
    def income_added(
        user_id,
        source,
        amount,
        action_url=None,
        commit=True,
    ):
        return NotificationService.create(
            user_id=user_id,
            title="Income Added",
            message=(
                f"₦{amount:,.2f} income "
                f"received from {source}."
            ),
            level="success",
            notification_type="income",
            icon="bi-cash-stack",
            action_url=action_url,
            commit=commit,
        )

    # ==========================================================
    # Expense Recorded
    # ==========================================================

    @staticmethod
    def expense_added(
        user_id,
        category,
        amount,
        action_url=None,
        commit=True,
    ):
        return NotificationService.create(
            user_id=user_id,
            title="Expense Recorded",
            message=(
                f"₦{amount:,.2f} spent on "
                f"{category}."
            ),
            level="info",
            notification_type="expense",
            icon="bi-receipt",
            action_url=action_url,
            commit=commit,
        )

    # ==========================================================
    # Recurring Bill Reminder
    # ==========================================================

    @staticmethod
    def recurring_bill_due(
        user_id,
        bill_name,
        due_date,
        action_url=None,
        commit=True,
    ):
        return NotificationService.create(
            user_id=user_id,
            title="Bill Due",
            message=f"{bill_name} is due on {due_date}.",
            level="warning",
            notification_type="reminder",
            icon="bi-calendar-event",
            action_url=action_url,
            commit=commit,
        )

    # ==========================================================
    # Tax Reminder
    # ==========================================================

    @staticmethod
    def tax_reminder(
        user_id,
        message,
        action_url=None,
        commit=True,
    ):
        return NotificationService.create(
            user_id=user_id,
            title="Tax Reminder",
            message=message,
            level="warning",
            notification_type="tax",
            icon="bi-calculator",
            action_url=action_url,
            commit=commit,
        )

    # ==========================================================
    # Report Ready
    # ==========================================================

    @staticmethod
    def report_ready(
        user_id,
        report_name,
        action_url=None,
        commit=True,
    ):
        return NotificationService.create(
            user_id=user_id,
            title="Report Ready",
            message=f"{report_name} has been generated.",
            level="success",
            notification_type="report",
            icon="bi-file-earmark-bar-graph",
            action_url=action_url,
            commit=commit,
        )

    # ==========================================================
    # AI Insight
    # ==========================================================

    @staticmethod
    def ai_insight(
        user_id,
        message,
        action_url=None,
        commit=True,
    ):
        return NotificationService.create(
            user_id=user_id,
            title="AI Insight",
            message=message,
            level="info",
            notification_type="ai",
            icon="bi-stars",
            action_url=action_url,
            commit=commit,
        )

    # ==========================================================
    # Generic System Notification
    # ==========================================================

    @staticmethod
    def system(
        user_id,
        title,
        message,
        level="info",
        icon="bi-bell-fill",
        action_url=None,
        commit=True,
    ):
        return NotificationService.create(
            user_id=user_id,
            title=title,
            message=message,
            level=level,
            notification_type="system",
            icon=icon,
            action_url=action_url,
            commit=commit,
        )
    
    # ==========================================================
    # Generate Dashboard Notifications
    # ==========================================================

    @staticmethod
    def generate_system_notifications(user_id):
        """
        Automatically generate dashboard notifications.

        Safe to call on every request.

        Duplicate Prevention
        --------------------
        An unread notification with the same unique_key
        will never be created twice.
        """

        from app.models.income import Income
        from app.models.expense import Expense
        from app.models.budget import Budget
        from app.models.goal import Goal

        # ------------------------------------------------------
        # Current Balance
        # ------------------------------------------------------

        total_income = (
            db.session.query(
                func.coalesce(
                    func.sum(Income.amount),
                    0
                )
            )
            .filter(
                Income.user_id == user_id
            )
            .scalar()
        )

        total_expense = (
            db.session.query(
                func.coalesce(
                    func.sum(Expense.amount),
                    0
                )
            )
            .filter(
                Expense.user_id == user_id
            )
            .scalar()
        )

        balance = total_income - total_expense

        if balance < 0:

            NotificationService.create(

                user_id=user_id,

                title="Low Balance",

                message=f"Current balance is ₦{balance:,.2f}.",

                level="danger",

                notification_type="system",

                icon="bi-wallet2",

                unique_key="LOW_BALANCE",

                commit=False,

            )

        # ------------------------------------------------------
        # Budget Alerts
        # ------------------------------------------------------

        budgets = Budget.query.filter_by(
            user_id=user_id
        ).all()

        for budget in budgets:

            pct = budget.percentage_used

            if pct >= 100:

                NotificationService.create(

                    user_id=user_id,

                    title="Budget Exceeded",

                    message=(
                        f"{budget.category} budget has been exceeded "
                        f"({pct:.0f}% used)."
                    ),

                    level="danger",

                    notification_type="budget",

                    icon="bi-exclamation-triangle-fill",

                    unique_key=f"BUDGET_EXCEEDED_{budget.id}",

                    commit=False,

                )

            elif pct >= 90:

                NotificationService.create(

                    user_id=user_id,

                    title="Budget Critical",

                    message=(
                        f"{budget.category} budget has reached "
                        f"{pct:.0f}%."
                    ),

                    level="warning",

                    notification_type="budget",

                    icon="bi-wallet2",

                    unique_key=f"BUDGET_CRITICAL_{budget.id}",

                    commit=False,

                )

            elif pct >= 75:

                NotificationService.create(

                    user_id=user_id,

                    title="Budget Warning",

                    message=(
                        f"{budget.category} budget has reached "
                        f"{pct:.0f}%."
                    ),

                    level="info",

                    notification_type="budget",

                    icon="bi-wallet2",

                    unique_key=f"BUDGET_WARNING_{budget.id}",

                    commit=False,

                )

        # ------------------------------------------------------
        # Goal Notifications
        # ------------------------------------------------------

        goals = Goal.query.filter_by(
            user_id=user_id
        ).all()

        for goal in goals:

            if goal.progress_percentage >= 100:

                if goal.status != "Completed":

                    NotificationService.create(

                        user_id=user_id,

                        title="Goal Achieved",

                        message=(
                            f"You achieved your '{goal.title}' goal."
                        ),

                        level="success",

                        notification_type="goal",

                        icon="bi-trophy-fill",

                        unique_key=f"GOAL_COMPLETED_{goal.id}",

                        commit=False,

                    )

                    goal.status = "Completed"

                    goal.completed_at = datetime.utcnow()

                continue

            days = goal.days_remaining

            if 0 <= days <= 7:

                NotificationService.create(

                    user_id=user_id,

                    title="Goal Due",

                    message=(
                        f"Your goal '{goal.title}' is due in "
                        f"{days} day(s)."
                    ),

                    level="warning",

                    notification_type="goal",

                    icon="bi-flag-fill",

                    unique_key=f"GOAL_DUE_{goal.id}",

                    commit=False,

                )

            if goal.progress_percentage < 40 and days > 0:

                NotificationService.create(

                    user_id=user_id,

                    title="Goal Behind Schedule",

                    message=(
                        f"'{goal.title}' is only "
                        f"{goal.progress_percentage:.0f}% funded."
                    ),

                    level="info",

                    notification_type="goal",

                    icon="bi-bullseye",

                    unique_key=f"GOAL_BEHIND_{goal.id}",

                    commit=False,

                )

        db.session.commit()

        return True