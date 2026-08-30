"""Identity business logic.

This is the module's only public surface: other modules never import from
here — they subscribe to the events it publishes, and authorise their routes
through `dependencies.py`.

Two decisions shape this file. A session is a **row**, not a signed token, so
that deactivating somebody, changing a password or reactivating an access can
end sessions that were already handed out, and so that going idle can be
measured at all. And the owner never sets anybody's password: an access is
created empty and its person redeems an invitation.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, NoReturn

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.identity import security
from app.modules.identity.models import (
    AccessEventKind,
    SessionRevocation,
    TokenPurpose,
    User,
    UserRole,
)
from app.modules.identity.repository import UserRepository
from app.modules.identity.schemas import (
    AccessEventRead,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.shared.errors import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.shared.events import (
    PasswordResetRequested,
    UserDeactivated,
    UserInvited,
    UserReactivated,
    UserRegistered,
    UserRoleChanged,
    events,
)
from app.shared.parameters import initial_value

logger = get_logger(__name__)

# Keys of the parameters `operations` owns and this module projects.
IDLE_MINUTES_KEY = "access.session_idle_minutes"
MAX_ATTEMPTS_KEY = "access.max_failed_attempts"
LOCKOUT_MINUTES_KEY = "access.lockout_minutes"

# The idle timeout is one of the parameters the owner sets from the settings
# panel, so its starting value is declared once, in the catalog, and read from
# there. Writing 60 here as well would be a second answer to the same question,
# and the day somebody moved one the platform would obey whichever it happened
# to read.
DEFAULT_IDLE_MINUTES = int(initial_value(IDLE_MINUTES_KEY))

# These two are deliberately **not** on the panel, so their starting value
# lives here, next to the rule that uses it.
DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_LOCKOUT_MINUTES = 15

INVITATION_TTL = timedelta(days=7)
RESET_TTL = timedelta(hours=1)

# A session's last use is only written when it is older than this. Three people
# do not need a row rewritten on every request; what must stay exact is that a
# session dies after the idle window, and this window is two orders of
# magnitude smaller than it.
TOUCH_AFTER = timedelta(seconds=60)

INVITE_NEW_ACCESS = "NEW_ACCESS"
INVITE_REACTIVATION = "REACTIVATION"

# One sentence for every way a login can fail. The caller never sees which.
REJECTED = "Invalid email or password"


class IdentityService:
    """Creates accesses, authenticates them and keeps the record of both."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    # --- settings this module projects ------------------------------------

    async def _setting(self, key: str, default: int) -> int:
        """Read a projected parameter, falling back to its initial value."""
        setting = await self.users.get_setting(key)
        if setting is None:
            return default
        try:
            return int(setting.value)
        except (TypeError, ValueError):
            # A parameter that arrived unusable must not lock everybody out.
            logger.warning("Unusable access setting", extra={"key": key})
            return default

    async def apply_setting(self, key: str, value: Any) -> None:
        """Take in a parameter change published by `operations`."""
        if key in (IDLE_MINUTES_KEY, MAX_ATTEMPTS_KEY, LOCKOUT_MINUTES_KEY):
            await self.users.set_setting(key, value)
            logger.info("Access setting updated", extra={"key": key})

    # --- accesses ---------------------------------------------------------

    async def create_user(self, payload: UserCreate, *, actor_id: int | None = None) -> UserRead:
        """Create an access and invite its person to set their own password.

        No password is accepted here on purpose: the owner hands out accesses,
        not credentials.
        """
        if await self.users.get_by_email(payload.email) is not None:
            raise ConflictError("A user with this email already exists")
        if payload.role is UserRole.OWNER and await self.users.count_owners():
            raise ConflictError("There is already an owner, and there can only be one")

        user = User(
            email=payload.email,
            name=payload.name,
            last_name=payload.last_name,
            phone=payload.phone,
            role=payload.role,
            is_active=True,
        )
        user = await self.users.add(user)
        await self.users.record_event(
            AccessEventKind.ACCESS_GRANTED,
            user_id=user.id,
            actor_user_id=actor_id,
            details={"role": user.role.value},
        )
        await events.publish(
            UserRegistered(
                user_id=user.id,
                email=user.email,
                role=user.role.value,
                phone=user.phone,
            ),
            self.session,
        )
        await self.invite(user, INVITE_NEW_ACCESS)
        await self.session.commit()
        logger.info("Access created", extra={"user_id": user.id, "role": user.role})
        return UserRead.model_validate(user)

    async def invite(self, user: User, reason: str) -> None:
        """Issue an invitation token and announce it. Never commits."""
        token = security.generate_token()
        expires_at = datetime.now(UTC) + INVITATION_TTL
        await self.users.add_token(
            user.id, security.hash_token(token), TokenPurpose.INVITATION, expires_at
        )
        user.invited_at = datetime.now(UTC)
        await events.publish(
            UserInvited(
                user_id=user.id,
                phone=user.phone,
                name=user.name,
                token=token,
                expires_at=expires_at,
                reason=reason,
            ),
            self.session,
        )

    async def get_user(self, user_id: int) -> UserRead:
        """Return an access by id."""
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found", details={"user_id": user_id})
        return UserRead.model_validate(user)

    async def list_users(
        self, *, skip: int = 0, limit: int = 100, query: str | None = None
    ) -> tuple[list[UserRead], int]:
        """Return a page of accesses and the total count."""
        if query:
            users = await self.users.search(query, skip=skip, limit=limit)
        else:
            users = await self.users.list(skip=skip, limit=limit)
        total = await self.users.count()
        return [UserRead.model_validate(user) for user in users], total

    async def update_user(
        self, user_id: int, payload: UserUpdate, *, actor_id: int | None = None
    ) -> UserRead:
        """Apply a partial update, keeping the owner unique."""
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found", details={"user_id": user_id})

        values = payload.model_dump(exclude_unset=True)
        new_role = values.get("role")
        previous_role = user.role
        if new_role is UserRole.OWNER and await self.users.count_owners(excluding=user_id):
            raise ConflictError("There is already an owner, and there can only be one")

        user = await self.users.update(user, values)
        if new_role is not None and new_role is not previous_role:
            await self.users.record_event(
                AccessEventKind.ACCESS_ROLE_CHANGED,
                user_id=user.id,
                actor_user_id=actor_id,
                details={"role": {"from": previous_role.value, "to": user.role.value}},
            )
            await events.publish(
                UserRoleChanged(
                    user_id=user.id, previous_role=previous_role.value, role=user.role.value
                ),
                self.session,
            )
        await self.session.commit()
        return UserRead.model_validate(user)

    async def deactivate_user(self, user_id: int, *, actor_id: int) -> None:
        """Deactivate an access: its history stays, its sessions do not."""
        if user_id == actor_id:
            raise ValidationError("The owner cannot deactivate their own access")
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found", details={"user_id": user_id})

        await self.users.update(user, {"is_active": False})
        closed = await self.users.revoke_sessions_of(user_id, SessionRevocation.DEACTIVATION)
        await self.users.record_event(
            AccessEventKind.ACCESS_DEACTIVATED, user_id=user_id, actor_user_id=actor_id
        )
        await events.publish(UserDeactivated(user_id=user_id), self.session)
        await self.session.commit()
        logger.info("Access deactivated", extra={"user_id": user_id, "sessions_closed": closed})

    async def reactivate_user(self, user_id: int, *, actor_id: int) -> UserRead:
        """Bring an access back: same person, new invitation, no old password."""
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found", details={"user_id": user_id})
        if user.is_active:
            raise ConflictError("That access is already active")

        await self.users.update(
            user,
            {"is_active": True, "activated_at": None, "failed_attempts": 0, "locked_until": None},
        )
        await self.users.clear_password(user_id)
        await self.users.revoke_sessions_of(user_id, SessionRevocation.REACTIVATION)
        await self.users.record_event(
            AccessEventKind.ACCESS_REACTIVATED, user_id=user_id, actor_user_id=actor_id
        )
        await events.publish(UserReactivated(user_id=user_id), self.session)
        await self.invite(user, INVITE_REACTIVATION)
        await self.session.commit()
        logger.info("Access reactivated", extra={"user_id": user_id})
        return UserRead.model_validate(user)

    # --- getting in -------------------------------------------------------

    async def authenticate(self, email: str, password: str) -> tuple[str, UserRead]:
        """Verify credentials and open a session.

        Every way this can fail raises the same error with the same message: an
        unknown address, a wrong password, an access that was deactivated and
        one that is temporarily locked. The log tells them apart; the caller
        never does.
        """
        user = await self.users.get_by_email(email)
        if user is None:
            await self._reject(None, email, "INVALID_CREDENTIALS")

        now = datetime.now(UTC)
        if user.locked_until is not None and user.locked_until > now:
            await self._reject(user, email, "LOCKED")
        if not user.is_active:
            await self._reject(user, email, "INACTIVE")

        credential = await self.users.get_password(user.id)
        if credential is None:
            # Invited and not redeemed yet: there is no password to check.
            await self._reject(user, email, "NOT_ACTIVATED")
        if not security.verify_password(password, credential.hashed_password):
            await self._count_failure(user, email)

        token = security.generate_token()
        await self.users.add_session(user.id, security.hash_token(token))
        await self.users.update(user, {"failed_attempts": 0, "locked_until": None})
        await self.users.record_event(AccessEventKind.LOGIN_SUCCEEDED, user_id=user.id)
        await self.session.commit()
        logger.info("User authenticated", extra={"user_id": user.id})
        return token, UserRead.model_validate(user)

    async def _reject(self, user: User | None, email: str, reason: str) -> NoReturn:
        """Record a refused login and fail, always the same way."""
        await self.users.record_event(
            AccessEventKind.LOGIN_REJECTED,
            user_id=user.id if user else None,
            attempted_email=email,
            reason=reason,
        )
        await self.session.commit()
        raise AuthenticationError(REJECTED)

    async def _count_failure(self, user: User, email: str) -> NoReturn:
        """Count a wrong password and lock the access if it went too far."""
        attempts = user.failed_attempts + 1
        limit = await self._setting(MAX_ATTEMPTS_KEY, DEFAULT_MAX_ATTEMPTS)
        values: dict[str, Any] = {"failed_attempts": attempts}

        if attempts >= limit:
            minutes = await self._setting(LOCKOUT_MINUTES_KEY, DEFAULT_LOCKOUT_MINUTES)
            values["locked_until"] = datetime.now(UTC) + timedelta(minutes=minutes)
            values["failed_attempts"] = 0
            await self.users.update(user, values)
            await self.users.record_event(
                AccessEventKind.ACCESS_LOCKED,
                user_id=user.id,
                attempted_email=email,
                reason="TOO_MANY_ATTEMPTS",
                details={"minutes": minutes},
            )
            await self.session.commit()
            raise AuthenticationError(REJECTED)

        await self.users.update(user, values)
        await self._reject(user, email, "INVALID_CREDENTIALS")

    async def resolve_session(self, token: str) -> User | None:
        """Return the person behind a session token, or None.

        Idleness is measured here, from the last use rather than from the
        login: somebody who kept working at hour seven is still working at
        hour nine.
        """
        session = await self.users.get_live_session(security.hash_token(token))
        if session is None:
            return None

        now = datetime.now(UTC)
        idle_minutes = await self._setting(IDLE_MINUTES_KEY, DEFAULT_IDLE_MINUTES)
        if session.last_seen_at + timedelta(minutes=idle_minutes) <= now:
            return None

        user = await self.users.get(session.user_id)
        if user is None or not user.is_active:
            return None

        if now - session.last_seen_at >= TOUCH_AFTER:
            await self.users.touch_session(session, now)
            await self.session.commit()
        return user

    async def logout(self, token: str) -> None:
        """Close the session this token belongs to."""
        session = await self.users.get_live_session(security.hash_token(token))
        if session is not None:
            await self.users.revoke_session(session, SessionRevocation.LOGOUT)
            await self.session.commit()

    # --- credentials of one's own -----------------------------------------

    async def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str,
        *,
        current_token: str | None = None,
    ) -> None:
        """Change a password, verifying the current one first.

        Every other session of the same person dies with it: a password that
        stopped being valid must not survive in a browser somewhere else.
        """
        credential = await self.users.get_password(user_id)
        if credential is None or not security.verify_password(
            current_password, credential.hashed_password
        ):
            raise AuthenticationError("Current password is incorrect")

        await self.users.set_password(user_id, security.hash_password(new_password))
        keep = None
        if current_token is not None:
            live = await self.users.get_live_session(security.hash_token(current_token))
            keep = live.id if live else None
        await self.users.revoke_sessions_of(user_id, SessionRevocation.PASSWORD_CHANGED, keep=keep)
        await self.session.commit()
        logger.info("Password changed", extra={"user_id": user_id})

    async def request_password_reset(self, email: str) -> None:
        """Announce a recovery, if the address belongs to an active access.

        Answers nothing either way: the caller must not be able to tell an
        address that exists from one that does not.
        """
        user = await self.users.get_by_email(email)
        if user is None or not user.is_active:
            return

        token = security.generate_token()
        expires_at = datetime.now(UTC) + RESET_TTL
        await self.users.add_token(
            user.id, security.hash_token(token), TokenPurpose.PASSWORD_RESET, expires_at
        )
        await events.publish(
            PasswordResetRequested(
                user_id=user.id,
                phone=user.phone,
                name=user.name,
                token=token,
                expires_at=expires_at,
            ),
            self.session,
        )
        await self.session.commit()
        logger.info("Password reset requested", extra={"user_id": user.id})

    async def redeem_token(self, token: str, purpose: TokenPurpose, new_password: str) -> None:
        """Spend a single-use token and set the password it was issued for."""
        stored = await self.users.get_usable_token(security.hash_token(token), purpose)
        if stored is None:
            raise ValidationError("El enlace no es válido o ya venció")

        user = await self.users.get(stored.user_id)
        if user is None or not user.is_active:
            raise ValidationError("El enlace no es válido o ya venció")

        await self.users.set_password(user.id, security.hash_password(new_password))
        stored.used_at = datetime.now(UTC)
        await self.users.update(
            user, {"activated_at": datetime.now(UTC), "failed_attempts": 0, "locked_until": None}
        )
        await self.users.revoke_sessions_of(user.id, SessionRevocation.PASSWORD_CHANGED)
        await self.session.commit()
        logger.info("Credential token redeemed", extra={"user_id": user.id, "purpose": purpose})

    async def token_is_usable(self, token: str, purpose: TokenPurpose) -> bool:
        """Say whether a link still works, without spending it."""
        return await self.users.get_usable_token(security.hash_token(token), purpose) is not None

    # --- the record -------------------------------------------------------

    async def record_denied_access(
        self, *, user_id: int | None, resource: str, reason: str
    ) -> None:
        """Write down that somebody was refused a resource."""
        await self.users.record_event(
            AccessEventKind.PERMISSION_DENIED,
            user_id=user_id,
            resource=resource,
            reason=reason,
        )
        await self.session.commit()

    async def list_access_events(
        self, *, skip: int = 0, limit: int = 50, kinds: list[AccessEventKind] | None = None
    ) -> tuple[list[AccessEventRead], int]:
        """Return a page of the access log."""
        rows, total = await self.users.list_events(skip=skip, limit=limit, kinds=kinds)
        return [AccessEventRead.model_validate(row) for row in rows], total
