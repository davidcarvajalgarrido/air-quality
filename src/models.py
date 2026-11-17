"""Modelos SQLModel del historial."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Conversation(SQLModel, table=True):
    id: str = Field(primary_key=True, max_length=100)
    created_at: datetime = Field(default_factory=_now)


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: str = Field(foreign_key="conversation.id", index=True, max_length=100)
    role: str = Field(max_length=20)
    content: str
    created_at: datetime = Field(default_factory=_now)
