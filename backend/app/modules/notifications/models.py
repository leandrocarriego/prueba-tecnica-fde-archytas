"""Notifications models: who gets told what, and how to reach them.

Two small tables, and both exist because of the same boundary. An alert has to
reach a person, on their phone, according to their role — and all three of
those facts belong to `identity`, whose tables this module may not read
(Artículo IV). So it keeps its own list of recipients, fed by the events
`identity` publishes when an access is created, deactivated, reactivated or
given another role.

The consequence is the good one: RF-45 of 007 — somebody who loses access stops
receiving alerts — is not a rule anybody has to remember. It is what happens
when `UserDeactivated` arrives.
"""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

OPERATIONS_SCHEMA = "operations"


class AlertKind(enum.StrEnum):
    """The kinds of alert the owner routes separately (RF-37 of 007)."""

    PAYMENT_CLAIM = "PAYMENT_CLAIM"
    DUE_SOON = "DUE_SOON"
    DAILY_DIGEST = "DAILY_DIGEST"


class NotificationRecipient(Base):
    """One person an alert can reach, as this module knows them."""

    __tablename__ = "notification_recipient"
    __table_args__ = {"schema": OPERATIONS_SCHEMA}

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    role: Mapped[str] = mapped_column(String(20), index=True)
    phone: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(255), default="")
    # False from the moment their access is deactivated. Nothing is deleted:
    # a person who comes back gets their alerts back without being re-created.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<NotificationRecipient user_id={self.user_id} role={self.role}>"


class NotificationRoute(Base):
    """Which role receives which kind of alert (RF-37 of 007).

    A table and not a constant, because the spec says the owner defines it. The
    **starting values** are the ones that were signed — claims and due dates to
    purchasing, the daily digest to the owner — and they live in code, like
    every other starting value of the platform, so a fresh installation behaves
    like a configured one.
    """

    __tablename__ = "notification_route"
    __table_args__ = {"schema": OPERATIONS_SCHEMA}

    kind: Mapped[AlertKind] = mapped_column(String(30), primary_key=True)
    role: Mapped[str] = mapped_column(String(20))
    updated_by_user_id: Mapped[int | None] = mapped_column(Integer, default=None)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<NotificationRoute {self.kind} -> {self.role}>"


class NotificationSetting(Base):
    """The business parameters this module reads, as **its own** projection.

    The window an immediate alert may go out in, and the hour the daily digest
    leaves, are parameters of `operations`, whose table this module may not read
    (Artículo IV). Fed by the event `operations` publishes when the owner moves
    one; until that happens the router falls back to the signed starting value.
    """

    __tablename__ = "notification_setting"
    __table_args__ = {"schema": OPERATIONS_SCHEMA}

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<NotificationSetting key={self.key}>"


__all__ = [
    "OPERATIONS_SCHEMA",
    "AlertKind",
    "NotificationRecipient",
    "NotificationRoute",
    "NotificationSetting",
]
