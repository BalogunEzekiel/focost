from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel


class ChatSession(BaseModel):

    __tablename__ = "chat_sessions"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    title = db.Column(
        db.String(255),
        default="New Chat"
    )

    messages = db.relationship(
        "ChatMessage",
        backref="session",
        lazy=True,
        cascade="all, delete"
    )


class ChatMessage(BaseModel):

    __tablename__ = "chat_messages"

    session_id = db.Column(
        db.Integer,
        db.ForeignKey("chat_sessions.id"),
        nullable=False
    )

    role = db.Column(
        db.String(20)
    )

    content = db.Column(
        db.Text
    )

