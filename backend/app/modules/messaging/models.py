"""Messaging models: the messages of the portal inbox, and who they came from.

`SupplierProjection` is the part worth reading twice. Identifying the sender of
a message means comparing it against the register of suppliers, and the register
belongs to `purchases`, whose tables this module may not read (Artículo IV). So
it keeps its own copy, fed by the same `SuppliersNormalized` event `purchases`
listens to — neither module learns that the other exists, and both are right
about who the suppliers are.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

CORE_SCHEMA = "core"


class MessageKind(enum.StrEnum):
    """What a message is about.

    `UNCLASSIFIED` is a value like any other and not an error: a message whose
    kind cannot be determined is **shown** as unclassified rather than discarded
    (RF-25 of 007), which is Artículo II in the smallest possible place.
    """

    PAYMENT_CLAIM = "PAYMENT_CLAIM"
    DUE_SOON = "DUE_SOON"
    LOW_STOCK = "LOW_STOCK"
    UNCLASSIFIED = "UNCLASSIFIED"


class MessageState(enum.StrEnum):
    """Whether somebody has dealt with a message yet (RF-27, RF-28 of 007)."""

    PENDING = "PENDING"
    RESOLVED = "RESOLVED"


class SupplierMessage(Base):
    """One message of the portal inbox, with a state and an owner of its own."""

    __tablename__ = "supplier_message"
    __table_args__ = (
        Index("ix_supplier_message_state_kind", "state", "kind"),
        Index("ix_supplier_message_received_at", "received_at"),
        {"schema": CORE_SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # What makes the same message the same message between two readings of the
    # inbox: it is read whole every time, and most of it was already read.
    external_id: Mapped[str] = mapped_column(String(160), unique=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sender_text: Mapped[str] = mapped_column(String(255), default="")
    # Null when the sender does not resolve to the register with certainty. The
    # message is shown all the same, saying the sender was not identified
    # (RF-24) — never hidden, and never attributed to a guess.
    # The supplier this message was attributed to, by name: it is how the
    # register identifies one, and this module never sees anybody's ids.
    supplier_name: Mapped[str | None] = mapped_column(String(255), default=None, index=True)
    kind: Mapped[MessageKind] = mapped_column(
        Enum(MessageKind, name="message_kind", schema=CORE_SCHEMA),
        default=MessageKind.UNCLASSIFIED,
        server_default=MessageKind.UNCLASSIFIED.value,
    )
    kind_text: Mapped[str | None] = mapped_column(String(100), default=None)
    subject: Mapped[str] = mapped_column(String(500), default="")
    body: Mapped[str | None] = mapped_column(Text, default=None)
    state: Mapped[MessageState] = mapped_column(
        Enum(MessageState, name="message_state", schema=CORE_SCHEMA),
        default=MessageState.PENDING,
        server_default=MessageState.PENDING.value,
    )
    assignee_user_id: Mapped[int | None] = mapped_column(Integer, default=None)
    note: Mapped[str | None] = mapped_column(Text, default=None)
    resolved_by_user_id: Mapped[int | None] = mapped_column(Integer, default=None)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    # When somebody was told about this message, so nobody is told twice while
    # it is still the same message (RF-39).
    alerted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    # Why an alert could not be delivered, shown on the messages screen (RF-38).
    alert_failure: Mapped[str | None] = mapped_column(String(200), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<SupplierMessage id={self.id} kind={self.kind} state={self.state}>"


class SupplierProjection(Base):
    """The register of suppliers, as this module needs to read it.

    A **projection**, not a source: the register belongs to `purchases`, and
    this module cannot import it. It is fed from `handlers.py` by the same event
    that feeds `purchases`, and it is never written from the service.
    """

    __tablename__ = "messaging_supplier"
    __table_args__ = {"schema": CORE_SCHEMA}

    # Keyed by the legal name and not by an id, because the event that feeds
    # this carries the register as the portal publishes it — before any module
    # has given those names an id of its own. The name **is** the identity of a
    # supplier in that register: it is what `/estado-cuenta` groups by.
    legal_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    # The name reduced to its identifying tokens, which is what a sender's name
    # is compared against.
    name_key: Mapped[str] = mapped_column(String(255), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<SupplierProjection {self.legal_name}>"


__all__ = ["CORE_SCHEMA", "MessageKind", "MessageState", "SupplierMessage", "SupplierProjection"]
