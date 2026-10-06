from datetime import UTC, datetime

from sqlalchemy import or_

from app.extensions import db
from app.models.feedback import Feedback


class FeedbackService:
    """
    Authoritative business logic for FOCOST feedback.

    Routes and templates should not implement feedback persistence or
    administrative workflow independently.
    """

    STATUSES = (
        "new",
        "under_review",
        "planned",
        "in_progress",
        "resolved",
        "closed",
    )

    PRIORITIES = (
        "low",
        "normal",
        "high",
        "urgent",
    )

    @staticmethod
    def create(
        *,
        submitted_by_id=None,
        submitted_name=None,
        submitted_email=None,
        category="general",
        subject,
        message,
        rating=None,
    ):
        feedback = Feedback(
            submitted_by_id=submitted_by_id,
            submitted_name=(submitted_name or "").strip() or None,
            submitted_email=(submitted_email or "").strip().lower() or None,
            category=category,
            subject=subject.strip(),
            message=message.strip(),
            rating=rating,
            status="new",
            priority="normal",
        )

        db.session.add(feedback)
        db.session.commit()

        return feedback

    @staticmethod
    def get(public_id):
        return Feedback.query.filter_by(
            public_id=public_id,
            is_active=True,
        ).first()

    @staticmethod
    def list(
        *,
        page=1,
        per_page=25,
        search="",
        category="",
        status="",
        priority="",
    ):
        page = max(int(page or 1), 1)
        per_page = min(max(int(per_page or 25), 10), 100)

        query = Feedback.query.filter_by(is_active=True)

        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    Feedback.subject.ilike(term),
                    Feedback.message.ilike(term),
                    Feedback.submitted_name.ilike(term),
                    Feedback.submitted_email.ilike(term),
                )
            )

        if category:
            query = query.filter(Feedback.category == category)

        if status:
            query = query.filter(Feedback.status == status)

        if priority:
            query = query.filter(Feedback.priority == priority)

        return query.order_by(
            Feedback.created_at.desc()
        ).paginate(
            page=page,
            per_page=per_page,
            error_out=False,
        )

    @staticmethod
    def statistics():
        rows = (
            db.session.query(
                Feedback.status,
                db.func.count(Feedback.id),
            )
            .filter(Feedback.is_active.is_(True))
            .group_by(Feedback.status)
            .all()
        )

        counts = {
            status: int(count)
            for status, count in rows
        }

        average_rating = (
            db.session.query(db.func.avg(Feedback.rating))
            .filter(Feedback.is_active.is_(True), Feedback.rating.isnot(None))
            .scalar()
        )
        return {
            "total": sum(counts.values()),
            "new": counts.get("new", 0),
            "under_review": counts.get("under_review", 0),
            "planned": counts.get("planned", 0),
            "in_progress": counts.get("in_progress", 0),
            "resolved": counts.get("resolved", 0),
            "closed": counts.get("closed", 0),
            "average_rating": round(float(average_rating), 2) if average_rating is not None else None,
            "rated_count": (
                Feedback.query.filter(
                    Feedback.is_active.is_(True),
                    Feedback.rating.isnot(None)
                ).count()
            ),
        }

    @staticmethod
    def update_review(
        feedback,
        *,
        status,
        priority,
        admin_notes,
        reviewed_by_id,
    ):
        if status not in FeedbackService.STATUSES:
            raise ValueError("Invalid feedback status.")

        if priority not in FeedbackService.PRIORITIES:
            raise ValueError("Invalid feedback priority.")

        feedback.status = status
        feedback.priority = priority
        feedback.admin_notes = (
            admin_notes.strip()
            if admin_notes
            else None
        )
        feedback.reviewed_by_id = reviewed_by_id
        feedback.reviewed_at = datetime.now(UTC)

        db.session.commit()

        return feedback
