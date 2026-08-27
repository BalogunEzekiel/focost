from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel

class ChatMessage(BaseModel):

    __tablename__ = "chat_messages"

    session_id = db.Column(
        db.Integer,
        db.ForeignKey("chat_sessions.id"),
        nullable=False,
        index=True
    )

    role = db.Column(
        db.String(20),
        nullable=False
    )

    content = db.Column(
        db.Text,
        nullable=False
    )

    tokens = db.Column(
        db.Integer
    )

    model = db.Column(
        db.String(100)
    )

    def to_dict(self):

        return {

            "role": self.role,

            "content": self.content

        }