"""Data access for the identity module. Private to this module."""

from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import CursorResult, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import (
    AccessEvent,
    AccessEventKind,
    AccessSetting,
    CredentialToken,
    Session,
    SessionRevocation,
    TokenPurpose,
    User,
    UserPassword,
)
from app.shared.repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Reads and writes users, credentials, sessions and the access log."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    # --- users -----------------------------------------------------------

    async def get_by_email(self, email: str) -> User | None:
        """Return the user with this email address, or None."""
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def search(self, query: str, *, skip: int = 0, limit: int = 100) -> list[User]:
        """Return users whose name or email match the query."""
        pattern = f"%{query}%"
        result = await self.session.execute(
            select(User)
            .where(or_(User.name.ilike(pattern), User.email.ilike(pattern)))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_owners(self, *, excluding: int | None = None) -> int:
        """Return how many accounts hold the owner role.

        Used to keep it at one: the spec says there is a single owner, and the
        check has to see the database rather than trust the caller.
        """
        statement = select(User).where(User.role == "OWNER")
        if excluding is not None:
            statement = statement.where(User.id != excluding)
        result = await self.session.execute(statement)
        return len(list(result.scalars().all()))

    # --- credentials -----------------------------------------------------

    async def get_password(self, user_id: int) -> UserPassword | None:
        """Return the stored credential for a user, or None."""
        result = await self.session.execute(
            select(UserPassword).where(UserPassword.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def set_password(self, user_id: int, hashed_password: str) -> UserPassword:
        """Create or replace a user's credential."""
        credential = await self.get_password(user_id)
        if credential is None:
            credential = UserPassword(user_id=user_id, hashed_password=hashed_password)
            self.session.add(credential)
        else:
            credential.hashed_password = hashed_password
        await self.session.flush()
        return credential

    async def clear_password(self, user_id: int) -> None:
        """Delete a user's credential.

        Reactivating an access does not invalidate the old password: it removes
        it. The person comes back through an invitation, like the first time.
        """
        credential = await self.get_password(user_id)
        if credential is not None:
            await self.session.delete(credential)
            await self.session.flush()

    # --- single-use tokens ------------------------------------------------

    async def add_token(
        self, user_id: int, token_hash: str, purpose: TokenPurpose, expires_at: datetime
    ) -> CredentialToken:
        """Store a token and invalidate any earlier one of the same purpose.

        Asking twice leaves one live link, the last: otherwise the first
        message would keep working for as long as its expiry allowed.
        """
        await self.session.execute(
            update(CredentialToken)
            .where(
                CredentialToken.user_id == user_id,
                CredentialToken.purpose == purpose,
                CredentialToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(UTC))
        )
        token = CredentialToken(
            user_id=user_id, token_hash=token_hash, purpose=purpose, expires_at=expires_at
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_usable_token(
        self, token_hash: str, purpose: TokenPurpose
    ) -> CredentialToken | None:
        """Return the token if it exists, is unused and has not expired."""
        result = await self.session.execute(
            select(CredentialToken).where(
                CredentialToken.token_hash == token_hash,
                CredentialToken.purpose == purpose,
                CredentialToken.used_at.is_(None),
                CredentialToken.expires_at > datetime.now(UTC),
            )
        )
        return result.scalar_one_or_none()

    # --- sessions ---------------------------------------------------------

    async def add_session(self, user_id: int, token_hash: str) -> Session:
        """Open a session for a user."""
        session = Session(user_id=user_id, token_hash=token_hash, last_seen_at=datetime.now(UTC))
        self.session.add(session)
        await self.session.flush()
        return session

    async def get_live_session(self, token_hash: str) -> Session | None:
        """Return the session for this token if it has not been revoked."""
        result = await self.session.execute(
            select(Session).where(
                Session.token_hash == token_hash,
                Session.revoked_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def touch_session(self, session: Session, moment: datetime) -> None:
        """Record that the session was used."""
        session.last_seen_at = moment
        await self.session.flush()

    async def revoke_session(self, session: Session, reason: SessionRevocation) -> None:
        """Close one session."""
        session.revoked_at = datetime.now(UTC)
        session.revoked_reason = reason
        await self.session.flush()

    async def revoke_sessions_of(
        self, user_id: int, reason: SessionRevocation, *, keep: int | None = None
    ) -> int:
        """Close every open session of a user, optionally sparing one.

        `keep` is what lets somebody change their own password without logging
        themselves out of the browser they are typing in.
        """
        statement = (
            update(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC), revoked_reason=reason)
        )
        if keep is not None:
            statement = statement.where(Session.id != keep)
        result = await self.session.execute(statement)
        await self.session.flush()
        return int(cast("CursorResult[Any]", result).rowcount or 0)

    # --- the access log ---------------------------------------------------

    async def record_event(
        self,
        kind: AccessEventKind,
        *,
        user_id: int | None = None,
        actor_user_id: int | None = None,
        attempted_email: str | None = None,
        resource: str | None = None,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AccessEvent:
        """Write one line of the access log."""
        event = AccessEvent(
            kind=kind,
            user_id=user_id,
            actor_user_id=actor_user_id,
            attempted_email=attempted_email,
            resource=resource,
            reason=reason,
            details=details,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_events(
        self, *, skip: int = 0, limit: int = 50, kinds: list[AccessEventKind] | None = None
    ) -> tuple[list[AccessEvent], int]:
        """Return a page of the access log, newest first, and the total."""
        statement = select(AccessEvent)
        if kinds:
            statement = statement.where(AccessEvent.kind.in_(kinds))
        total = len(list((await self.session.execute(statement)).scalars().all()))
        result = await self.session.execute(
            statement.order_by(AccessEvent.occurred_at.desc(), AccessEvent.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    # --- the projection of somebody else's parameters ---------------------

    async def get_setting(self, key: str) -> AccessSetting | None:
        """Return one projected setting."""
        result = await self.session.execute(select(AccessSetting).where(AccessSetting.key == key))
        return result.scalar_one_or_none()

    async def set_setting(self, key: str, value: Any) -> AccessSetting:
        """Create or update a projected setting."""
        setting = await self.get_setting(key)
        if setting is None:
            setting = AccessSetting(key=key, value=value)
            self.session.add(setting)
        else:
            setting.value = value
        await self.session.flush()
        return setting
