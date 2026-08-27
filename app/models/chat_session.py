from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel


class ChatSession(BaseModel):

    __tablename__ = "chat_sessions"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    title = db.Column(
        db.String(255),
        nullable=False,
        default="New Chat"
    )

    summary = db.Column(
        db.Text
    )

    messages = db.relationship(
        "ChatMessage",
        backref="session",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at"
    )