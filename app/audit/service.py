import logging

from flask import (
    request,
    session,
    has_request_context
)

from flask_login import current_user

from sqlalchemy import or_

from app.extensions import db
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """
    Central service for creating and retrieving application audit logs.

    Responsibilities:
        - Record security and application events
        - Capture request metadata
        - Retrieve paginated audit logs
        - Support filtering by search, category and status
    """

    # ==========================================================
    # CREATE AUDIT LOG
    # ==========================================================

    @staticmethod
    def log(
        action,
        category,
        description=None,
        resource=None,
        resource_id=None,
        status="success",
        metadata=None
    ):
        """
        Creates an audit log.

        Safe to call from anywhere.

        Audit logging should never break the main application flow.
        Therefore, exceptions are caught and logged instead of
        being propagated to the caller.
        """

        try:

            user_id = None
            ip_address = None
            user_agent = None
            request_path = None
            http_method = None
            endpoint = None
            session_id = None

            # --------------------------------------------------
            # Request information
            # --------------------------------------------------

            if has_request_context():

                if current_user.is_authenticated:
                    user_id = current_user.id

                # Handle reverse proxy / deployment environments
                forwarded_for = request.headers.get("X-Forwarded-For")

                if forwarded_for:
                    ip_address = forwarded_for.split(",")[0].strip()
                else:
                    ip_address = request.remote_addr

                user_agent = request.user_agent.string

                request_path = request.path

                http_method = request.method

                endpoint = request.endpoint

                session_id = (
                    session.get("_id")
                    or request.cookies.get("session")
                )

            # --------------------------------------------------
            # Create log
            # --------------------------------------------------

            log = AuditLog(

                user_id=user_id,

                action=action,

                category=category,

                description=description,

                resource=resource,

                resource_id=resource_id,

                ip_address=ip_address,

                user_agent=user_agent,

                request_path=request_path,

                http_method=http_method,

                endpoint=endpoint,

                method=http_method,

                status=status,

                session_id=session_id,

                # IMPORTANT:
                # AuditLog defines "extra_data", not "metadata"
                extra_data=metadata
            )

            db.session.add(log)

            db.session.commit()

            return log

        except Exception:

            db.session.rollback()

            logger.exception(
                "Failed to write audit log."
            )

            return None

    # ==========================================================
    # RETRIEVE AUDIT LOGS
    # ==========================================================

    @staticmethod
    def get_logs(
        page=1,
        per_page=25,
        search="",
        category="",
        status=""
    ):
        """
        Retrieve paginated audit logs.

        Parameters
        ----------
        page : int
            Current page number.

        per_page : int
            Number of records per page.

        search : str
            Searches action, description, resource,
            resource ID and IP address.

        category : str
            Filter by audit category.

        status : str
            Filter by audit status.

        Returns
        -------
        Pagination
            Flask-SQLAlchemy pagination object.
        """

        try:

            # --------------------------------------------------
            # Sanitize pagination
            # --------------------------------------------------

            try:
                page = int(page)
            except (TypeError, ValueError):
                page = 1

            page = max(page, 1)

            try:
                per_page = int(per_page)
            except (TypeError, ValueError):
                per_page = 25

            # Prevent excessively large queries
            per_page = min(max(per_page, 10), 100)

            # --------------------------------------------------
            # Base query
            # --------------------------------------------------

            query = AuditLog.query

            # --------------------------------------------------
            # Search
            # --------------------------------------------------

            if search:

                search_term = f"%{search}%"

                query = query.filter(
                    or_(
                        AuditLog.action.ilike(search_term),
                        AuditLog.category.ilike(search_term),
                        AuditLog.description.ilike(search_term),
                        AuditLog.resource.ilike(search_term),
                        AuditLog.resource_id.ilike(search_term),
                        AuditLog.ip_address.ilike(search_term)
                    )
                )

            # --------------------------------------------------
            # Category filter
            # --------------------------------------------------

            if category:

                query = query.filter(
                    AuditLog.category == category
                )

            # --------------------------------------------------
            # Status filter
            # --------------------------------------------------

            if status:

                query = query.filter(
                    AuditLog.status == status
                )

            # --------------------------------------------------
            # Latest events first
            # --------------------------------------------------

            query = query.order_by(
                AuditLog.created_at.desc()
            )

            # --------------------------------------------------
            # Pagination
            # --------------------------------------------------

            return query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )

        except Exception:

            logger.exception(
                "Failed to retrieve audit logs."
            )

            # Do not allow the admin audit page to crash
            # because of an audit-query problem.

            return AuditLog.query.order_by(
                AuditLog.created_at.desc()
            ).paginate(
                page=1,
                per_page=per_page,
                error_out=False
            )

    # ==========================================================
    # GET CATEGORIES
    # ==========================================================

    @staticmethod
    def get_categories():
        """
        Return available audit categories.
        """

        try:

            rows = (
                db.session.query(
                    AuditLog.category
                )
                .filter(
                    AuditLog.category.isnot(None)
                )
                .distinct()
                .order_by(
                    AuditLog.category.asc()
                )
                .all()
            )

            return [
                row[0]
                for row in rows
                if row[0]
            ]

        except Exception:

            logger.exception(
                "Failed to retrieve audit categories."
            )

            return []

    # ==========================================================
    # GET STATISTICS
    # ==========================================================

    @staticmethod
    def get_statistics():
        """
        Return basic audit statistics for the admin interface.
        """

        try:

            total = AuditLog.query.count()

            successful = (
                AuditLog.query
                .filter(
                    AuditLog.status == "success"
                )
                .count()
            )

            failed = (
                AuditLog.query
                .filter(
                    AuditLog.status == "failed"
                )
                .count()
            )

            return {
                "total": total,
                "successful": successful,
                "failed": failed
            }

        except Exception:

            logger.exception(
                "Failed to retrieve audit statistics."
            )

            return {
                "total": 0,
                "successful": 0,
                "failed": 0
            }