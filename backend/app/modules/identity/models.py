"""Identity models.

These tables are owned by the application itself, so they live in the default
schema — unlike the portal data, which is partitioned across `raw`, `staging`,
`core` and `operations`.

Two things here are deliberately not columns. A session is not a signed token:
it is a row, because four requirements need it revoked or touched after it was
issued. And the state of an access — invited, active, locked, deactivated — is
derived from `is_active`, `activated_at` and `locked_until` rather than stored,
so there is no second copy of the truth to disagree with them.
"""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(enum.StrEnum):
    """The three roles the business actually has.

    Taken from the client's own words: the owner, whoever handles purchasing,
    and whoever handles sales. Authorisation is enforced per resource, not by
    hiding links in a menu.
    """

    OWNER = "OWNER"
    PURCHASING = "PURCHASING"
    SALES = "SALES"


class SessionRevocation(enum.StrEnum):
    """Why a session stopped being valid before it went idle."""

    LOGOUT = "LOGOUT"
    DEACTIVATION = "DEACTIVATION"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    REACTIVATION = "REACTIVATION"


class TokenPurpose(enum.StrEnum):
    """What a single-use credential token lets someone do."""

    INVITATION = "INVITATION"
    PASSWORD_RESET = "PASSWORD_RESET"


class AccessEventKind(enum.StrEnum):
    """What happened, in the vocabulary the owner reads on screen.

    The first four are about getting in; the last four are the owner acting on
    somebody else's access. They share a table because they answer the same
    question — who did what to which access, and when — and the owner reads
    them in a single list.
    """

    LOGIN_SUCCEEDED = "LOGIN_SUCCEEDED"
    LOGIN_REJECTED = "LOGIN_REJECTED"
    ACCESS_LOCKED = "ACCESS_LOCKED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    ACCESS_GRANTED = "ACCESS_GRANTED"
    ACCESS_ROLE_CHANGED = "ACCESS_ROLE_CHANGED"
    ACCESS_DEACTIVATED = "ACCESS_DEACTIVATED"
    ACCESS_REACTIVATED = "ACCESS_REACTIVATED"


class User(Base):
    """A person who can log into the platform."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255), default=None)
    # Not nullable: the invitation and the recovery link travel by WhatsApp, so
    # an access without a phone is an access nobody can ever use.
    phone: Mapped[str] = mapped_column(String(20))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), server_default=UserRole.SALES.value
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # Null until the person redeems their invitation and sets a password of
    # their own. Reactivating clears it again: coming back means being invited.
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    invited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"


class UserPassword(Base):
    """A user's password hash, kept apart from the user record itself."""

    __tablename__ = "user_passwords"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(backref="password_info")

    def __repr__(self) -> str:
        return f"<UserPassword user_id={self.user_id}>"


class Session(Base):
    """One open session, and the only thing that can be revoked.

    What travels to the browser is an opaque random string; what is stored is
    its SHA-256. The table is therefore not enough to get in. `last_seen_at` is
    what makes idleness measurable, which a signed token cannot do: its expiry
    is fixed when it is issued and never learns that somebody kept working.
    """

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    revoked_reason: Mapped[SessionRevocation | None] = mapped_column(
        Enum(SessionRevocation, name="session_revocation"), default=None
    )

    user: Mapped[User] = relationship(backref="sessions")

    def __repr__(self) -> str:
        return f"<Session id={self.id} user_id={self.user_id}>"


class CredentialToken(Base):
    """A single-use token that lets a person set a password.

    Invitation and recovery are the same mechanism with a different reason, so
    they are the same table with a `purpose`. Stored hashed, like a session: a
    token in the clear in the database is a password in the database.
    """

    __tablename__ = "credential_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    purpose: Mapped[TokenPurpose] = mapped_column(Enum(TokenPurpose, name="token_purpose"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(backref="credential_tokens")

    def __repr__(self) -> str:
        return f"<CredentialToken user_id={self.user_id} purpose={self.purpose}>"


class AccessEvent(Base):
    """Who got in, who was turned away, and what the owner changed.

    Nothing is discarded: a rejected attempt is business information, which is
    why this is a table of the product and not a log line that rotates away.
    `user_id` is who it happened to and `actor_user_id` is who did it — the
    same person when someone logs in, two different people when the owner
    deactivates an access.
    """

    __tablename__ = "access_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    kind: Mapped[AccessEventKind] = mapped_column(
        Enum(AccessEventKind, name="access_event_kind"), index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None, index=True
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    # Kept even when it matches no account: an attempt against an address that
    # does not exist is exactly what the owner wants to see.
    attempted_email: Mapped[str | None] = mapped_column(String(255), default=None)
    resource: Mapped[str | None] = mapped_column(String(255), default=None)
    reason: Mapped[str | None] = mapped_column(String(100), default=None)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)

    def __repr__(self) -> str:
        return f"<AccessEvent id={self.id} kind={self.kind}>"


class AccessSetting(Base):
    """This module's own copy of the parameters the owner can change.

    `operations` owns them; identity keeps a projection fed by
    `BusinessParameterChanged` instead of reading somebody else's table. Seeded
    with the initial values, so the system knows how long a session lasts
    before any event has ever been published.
    """

    __tablename__ = "access_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<AccessSetting key={self.key}>"
