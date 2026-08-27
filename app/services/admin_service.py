from datetime import datetime, timedelta
from flask import current_app

from sqlalchemy import func

from app.extensions import db

from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.user_role import UserRole
from app.models.role_permission import RolePermission
from app.models.audit_log import AuditLog

# Optional models
try:
    from app.models.income import Income
except Exception:
    Income = None

try:
    from app.models.expense import Expense
except Exception:
    Expense = None

try:
    from app.models.goal import Goal
except Exception:
    Goal = None

try:
    from app.models.budget import Budget
except Exception:
    Budget = None


class AdminService:
    """
    Provides all statistics required by the Admin Dashboard.

    Every method is defensive.
    Missing models simply return zero instead of crashing.
    """

    # ======================================================
    # USER STATISTICS
    # ======================================================

    @staticmethod
    def user_stats():

        today = datetime.utcnow().date()

        total_users = User.query.count()

        active_users = User.query.filter_by(
            is_active=True
        ).count()

        inactive_users = User.query.filter_by(
            is_active=False
        ).count()

        new_today = User.query.filter(
            func.date(User.created_at) == today
        ).count()

        return {
            "total": total_users,
            "active": active_users,
            "inactive": inactive_users,
            "today": new_today
        }

    # ======================================================
    # ADMINISTRATOR STATISTICS
    # ======================================================

    @staticmethod
    def admin_users():

        return (

            db.session.query(
                func.count(func.distinct(User.id))
            )

            .join(
                UserRole,
                User.id == UserRole.user_id
            )

            .join(
                Role,
                Role.id == UserRole.role_id
            )

            .filter(

                Role.slug.in_(

                    [

                        "super_admin",

                        "administrator"

                    ]

                )

            )

            .scalar()

        ) or 0

    # ======================================================
    # RBAC
    # ======================================================

    @staticmethod
    def rbac_stats():

        return {
            "roles": Role.query.count(),
            "permissions": Permission.query.count(),
            "user_roles": UserRole.query.count(),
            "role_permissions": RolePermission.query.count()
        }

    # ======================================================
    # FINANCE
    # ======================================================

    @staticmethod
    def finance_stats():

        total_income = 0
        total_expense = 0

        income_count = 0
        expense_count = 0

        if Income:

            total_income = (
                db.session.query(
                    func.coalesce(
                        func.sum(Income.amount),
                        0
                    )
                ).scalar()
            )

            income_count = Income.query.count()

        if Expense:

            total_expense = (
                db.session.query(
                    func.coalesce(
                        func.sum(Expense.amount),
                        0
                    )
                ).scalar()
            )

            expense_count = Expense.query.count()

        return {

            "income": float(total_income),

            "expense": float(total_expense),

            "balance": float(total_income - total_expense),

            "budgets":
                Budget.query.count()
                if Budget else 0,

            "goals":
                Goal.query.count()
                if Goal else 0,

            # Total financial records
            "transactions":
                income_count + expense_count

        }

    # ======================================================
    # SECURITY
    # ======================================================

    @staticmethod
    def security_stats():

        today = datetime.utcnow().date()

        total_logs = AuditLog.query.count()

        failed_logins = AuditLog.query.filter_by(
            action="auth.login_failed"
        ).count()

        today_logs = AuditLog.query.filter(
            func.date(
                AuditLog.created_at
            ) == today
        ).count()

        return {

            "audit_logs": total_logs,

            "today_logs": today_logs,

            "failed_logins": failed_logins
        }

    # ======================================================
    # SUBSCRIPTIONS
    # ======================================================

    @staticmethod
    def subscription_stats():

        return {

            "total": 0,

            "basic": 0,

            "pro": 0,

            "enterprise": 0

        }

    # ======================================================
    # AI
    # ======================================================

    @staticmethod
    def ai_stats():

        return {

            "requests": 0,

            "success": 0,

            "failed": 0,

            "providers": {}

        }

    # ======================================================
    # RECENT AUDIT EVENTS
    # ======================================================

    @staticmethod
    def recent_activity(limit=10):

        return (

            AuditLog.query

            .order_by(
                AuditLog.created_at.desc()
            )

            .limit(limit)

            .all()
        )

    # ======================================================
    # SYSTEM
    # ======================================================

    @staticmethod
    def system_stats():

        return {

            "database": db.engine.name,

            "server_time":
                datetime.utcnow(),

            "version": current_app.config.get("APP_VERSION", "FOCOST"),

            "generated":
                datetime.utcnow()
        }

    # ======================================================
    # ROLE DISTRIBUTION
    # ======================================================

    @staticmethod
    def role_statistics():

        rows = (
            db.session.query(
                Role.name,
                func.count(UserRole.user_id)
            )
            .outerjoin(
                UserRole,
                Role.id == UserRole.role_id
            )
            .group_by(Role.id)
            .all()
        )

        return [

            {
                "name": name,
                "count": count
            }

            for name, count in rows

        ]


    # ======================================================
    # LATEST USERS
    # ======================================================

    @staticmethod
    def latest_users(limit=8):

        return (

            User.query

            .order_by(User.created_at.desc())

            .limit(limit)

            .all()

        )


    # ======================================================
    # MONTHLY CHART
    # ======================================================

    @staticmethod
    def finance_chart():

        labels = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]

        income = [0] * 12
        expenses = [0] * 12

        if Income:

            rows = (

                db.session.query(

                    func.strftime("%m", Income.received_date),

                    func.sum(Income.amount)

                )

                .group_by(

                    func.strftime("%m", Income.received_date)

                )

                .all()

            )

            for month, total in rows:

                income[int(month) - 1] = float(total)


        if Expense:

            rows = (

                db.session.query(

                    func.strftime("%m", Expense.expense_date),

                    func.sum(Expense.amount)

                )

                .group_by(

                    func.strftime("%m", Expense.expense_date)

                )

                .all()

            )

            for month, total in rows:

                expenses[int(month) - 1] = float(total)

        return {

            "labels": labels,

            "income": income,

            "expenses": expenses

        }


    # ======================================================
    # COMPLETE DASHBOARD DATA
    # ======================================================

    @classmethod
    def dashboard_data(cls):

        dashboard = {

            "users": cls.user_stats(),

            "rbac": cls.rbac_stats(),

            "finance": cls.finance_stats(),

            "security": cls.security_stats(),

            "subscriptions": cls.subscription_stats(),

            "ai": cls.ai_stats(),

            "system": cls.system_stats()

        }

        admin_users = cls.admin_users()

        return {

            # ==========================================
            # Main Dashboard Object
            # ==========================================

            "dashboard": dashboard,

            # ==========================================
            # Statistics
            # ==========================================

            "stats": {

                "total_users":
                    dashboard["users"]["total"],

                "active_users":
                    dashboard["users"]["active"],

                "inactive_users":
                    dashboard["users"]["inactive"],

                "admin_users":
                    admin_users,

                "new_users":
                    dashboard["users"]["today"]

            },

            # ==========================================
            # Charts
            # ==========================================

            "chart":
                cls.finance_chart(),

            # ==========================================
            # Audit Logs
            # ==========================================

            "recent_logs":
                cls.recent_activity(),

            # ==========================================
            # Roles
            # ==========================================

            "role_stats":
                cls.role_statistics(),

            # ==========================================
            # Latest Users
            # ==========================================

            "latest_users":
                cls.latest_users(),

            # ==========================================
            # Convenience Variables
            # ==========================================

            "users":
                dashboard["users"],

            "finance":
                dashboard["finance"],

            "rbac":
                dashboard["rbac"],

            "security":
                dashboard["security"],

            "subscriptions":
                dashboard["subscriptions"],

            "ai":
                dashboard["ai"],

            "system":
                dashboard["system"]

        }