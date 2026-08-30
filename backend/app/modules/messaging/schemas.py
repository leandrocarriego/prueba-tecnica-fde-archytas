"""Messaging schemas: the inbox as the screen that finally reads it shows it."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.messaging.models import MessageKind, MessageState

NOTE_MAX = 2000


class MessageRead(BaseModel):
    """One message of the inbox (RF-22 to RF-32 of 007)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    received_at: datetime
    sender_text: str
    supplier_name: str | None
    kind: MessageKind
    kind_text: str | None
    subject: str
    body: str | None
    state: MessageState
    assignee_user_id: int | None
    note: str | None
    resolved_by_user_id: int | None
    resolved_at: datetime | None
    alert_failure: str | None
    # True when the sender did not resolve to the register with certainty. The
    # message is shown all the same, saying so (RF-24).
    sender_unidentified: bool = False


class MessageList(BaseModel):
    """A page of the inbox, with what is still pending beside it (RF-31)."""

    items: list[MessageRead]
    total: int
    pending: int
    skip: int
    limit: int


class MessageNote(BaseModel):
    """A note somebody writes on a message (RF-32 of 007)."""

    note: str = Field(min_length=1, max_length=NOTE_MAX)


class MessageAssignment(BaseModel):
    """Who is responsible for a message (RF-30 of 007)."""

    assignee_user_id: int | None = None
