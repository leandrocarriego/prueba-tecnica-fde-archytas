"""Integration tests for `IdentityService`.

Against a real session, because the service commits: what these tests verify is
the state the database is left in, not the calls the service made.

They pin the two properties the module was rewritten for. A failed login never
says **why** it failed — an unknown address, a wrong password, a deactivated
access and a locked one are indistinguishable from outside. And a session is a
row, so everything that should end one — a deactivation, a password change, a
reactivation, going idle — actually ends it, which is the whole reason the
signed token was dropped.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import (
    AccessEvent,
    AccessEventKind,
    CredentialToken,
    TokenPurpose,
    UserRole,
)
from app.modules.identity.schemas import UserCreate, UserUpdate
from app.modules.identity.security import hash_token, verify_password
from app.modules.identity.service import (
    MAX_ATTEMPTS_KEY,
    IdentityService,
)
from app.shared.errors import AuthenticationError, ConflictError, NotFoundError, ValidationError
from tests.factories.user_factory import DEFAULT_PASSWORD, UserFactory

NEW_PASSWORD = "una-clave-nueva-2026"


@pytest.fixture
def service(session: AsyncSession) -> IdentityService:
    """The service under test, on the test's session."""
    return IdentityService(session)


def _payload(**overrides: object) -> UserCreate:
    """A valid access, with no password: the owner never sets one."""
    data: dict[str, object] = {
        "email": "marcela@example.com",
        "name": "Marcela",
        "phone": "+5491133334444",
        "role": UserRole.PURCHASING,
    }
    data.update(overrides)
    return UserCreate(**data)  # type: ignore[arg-type]


async def _tokens_of(
    session: AsyncSession, user_id: int, purpose: TokenPurpose
) -> list[CredentialToken]:
    """Every token ever issued to a user for one purpose, newest last."""
    result = await session.execute(
        select(CredentialToken)
        .where(CredentialToken.user_id == user_id, CredentialToken.purpose == purpose)
        .order_by(CredentialToken.id)
    )
    return list(result.scalars().all())


async def _events_of(session: AsyncSession, kind: AccessEventKind) -> list[AccessEvent]:
    """Every access event of one kind."""
    result = await session.execute(select(AccessEvent).where(AccessEvent.kind == kind))
    return list(result.scalars().all())


@pytest.mark.integration
@pytest.mark.database
class TestCreateAccess:
    """Handing out an access, which is not the same as handing out a password."""

    async def test_the_access_is_created_without_a_credential(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-44: the owner never knows anybody else's password."""
        # Act
        created = await service.create_user(_payload())

        # Assert
        assert created.email == "marcela@example.com"
        assert created.activated_at is None
        assert await service.users.get_password(created.id) is None

    async def test_an_invitation_is_issued_and_stored_hashed(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-42: what reaches the person is a token; what is stored is its hash."""
        # Act
        created = await service.create_user(_payload())

        # Assert
        tokens = await _tokens_of(session, created.id, TokenPurpose.INVITATION)
        assert len(tokens) == 1
        assert len(tokens[0].token_hash) == 64
        assert tokens[0].used_at is None

    async def test_the_invitation_is_queued_to_the_person(
        self, service: IdentityService, queued_access_links: object
    ) -> None:
        """RF-42: it goes to their phone, and it leaves the transaction alone."""
        # Act
        created = await service.create_user(_payload(phone="+5491199998888"))

        # Assert
        assert queued_access_links.count == 1  # type: ignore[attr-defined]
        sent_to = queued_access_links.calls[0]["args"][0]  # type: ignore[attr-defined]
        assert sent_to == "+5491199998888"
        assert created.id

    async def test_an_invited_access_cannot_log_in_yet(self, service: IdentityService) -> None:
        """RF-43: until the invitation is redeemed, there is nothing to log in with."""
        # Arrange
        created = await service.create_user(_payload())

        # Act / Assert
        with pytest.raises(AuthenticationError):
            await service.authenticate(created.email, DEFAULT_PASSWORD)

    async def test_a_duplicate_email_conflicts(self, service: IdentityService) -> None:
        """The email is the username, so it stays unique."""
        # Arrange
        await service.create_user(_payload())

        # Act / Assert
        with pytest.raises(ConflictError):
            await service.create_user(_payload())

    async def test_a_second_owner_is_refused(self, service: IdentityService, owner: object) -> None:
        """RF-50: there is one owner, and the check reads the database."""
        # Act / Assert
        with pytest.raises(ConflictError):
            await service.create_user(_payload(role=UserRole.OWNER))

    async def test_creating_an_access_is_recorded(
        self, service: IdentityService, session: AsyncSession, owner: object
    ) -> None:
        """RF-23: who did it, to whom, and what they were given."""
        # Act
        created = await service.create_user(_payload(), actor_id=owner.id)  # type: ignore[attr-defined]

        # Assert
        events = await _events_of(session, AccessEventKind.ACCESS_GRANTED)
        assert [(event.user_id, event.actor_user_id) for event in events] == [
            (created.id, owner.id)  # type: ignore[attr-defined]
        ]
        assert events[0].details == {"role": UserRole.PURCHASING.value}


@pytest.mark.integration
@pytest.mark.database
class TestRedeemingAnInvitation:
    """The only way a password is ever set for the first time."""

    async def test_redeeming_activates_the_access_and_lets_it_in(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-42, RF-43: she sets her own password and gets in with it."""
        # Arrange
        created = await service.create_user(_payload())
        token = await self._last_invitation(service, session, created.id)

        # Act
        await service.redeem_token(token, TokenPurpose.INVITATION, NEW_PASSWORD)

        # Assert
        session_token, user = await service.authenticate(created.email, NEW_PASSWORD)
        assert session_token
        assert user.activated_at is not None

    async def test_a_token_works_once(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-40: spending it kills it."""
        # Arrange
        created = await service.create_user(_payload())
        token = await self._last_invitation(service, session, created.id)
        await service.redeem_token(token, TokenPurpose.INVITATION, NEW_PASSWORD)

        # Act / Assert
        with pytest.raises(ValidationError):
            await service.redeem_token(token, TokenPurpose.INVITATION, "otra-clave-2026")

    async def test_an_expired_token_is_refused(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-41: a link kept for later stops working."""
        # Arrange
        created = await service.create_user(_payload())
        token = await self._last_invitation(service, session, created.id)
        stored = (await _tokens_of(session, created.id, TokenPurpose.INVITATION))[-1]
        stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.flush()

        # Act / Assert
        with pytest.raises(ValidationError):
            await service.redeem_token(token, TokenPurpose.INVITATION, NEW_PASSWORD)

    async def test_issuing_a_new_one_invalidates_the_previous(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """Asking twice leaves one live link, the last."""
        # Arrange
        created = await service.create_user(_payload())
        first = await self._last_invitation(service, session, created.id)
        await service.users.add_token(
            created.id,
            hash_token("second"),
            TokenPurpose.INVITATION,
            datetime.now(UTC) + timedelta(days=1),
        )
        await session.commit()

        # Act / Assert
        assert await service.token_is_usable(first, TokenPurpose.INVITATION) is False

    @staticmethod
    async def _last_invitation(
        service: IdentityService, session: AsyncSession, user_id: int
    ) -> str:
        """Recover the token a test needs by re-issuing one it knows.

        The service hands the real token to an event, not to its caller — which
        is the point — so a test that needs to redeem one issues its own with a
        known value.
        """
        token = "invitation-under-test"
        await service.users.add_token(
            user_id,
            hash_token(token),
            TokenPurpose.INVITATION,
            datetime.now(UTC) + timedelta(days=7),
        )
        await session.commit()
        return token


@pytest.mark.integration
@pytest.mark.database
class TestAuthenticate:
    """Getting in, and the four ways of not getting in that look the same."""

    async def test_a_successful_login_opens_a_session(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-01: the token maps to a row, and the row is what can be revoked."""
        # Arrange
        user = await UserFactory.create(session)

        # Act
        token, read = await service.authenticate(user.email, DEFAULT_PASSWORD)

        # Assert
        assert read.id == user.id
        stored = await service.users.get_live_session(hash_token(token))
        assert stored is not None and stored.user_id == user.id

    async def test_every_failure_looks_the_same(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-02, RF-19, RF-46: four different reasons, one answer.

        This is the test the feature exists for. If any branch ever grows its
        own message, the login turns into a way of finding out which addresses
        have an account and which are blocked.
        """
        # Arrange
        wrong_password = await UserFactory.create(session)
        inactive = await UserFactory.create(session, is_active=False)
        locked = await UserFactory.create(session)
        locked.locked_until = datetime.now(UTC) + timedelta(minutes=15)
        await session.flush()

        messages = []

        # Act
        for email, password in (
            ("nobody@example.com", DEFAULT_PASSWORD),
            (wrong_password.email, "no-es-la-clave"),
            (inactive.email, DEFAULT_PASSWORD),
            (locked.email, DEFAULT_PASSWORD),
        ):
            with pytest.raises(AuthenticationError) as raised:
                await service.authenticate(email, password)
            messages.append(str(raised.value))

        # Assert
        assert len(set(messages)) == 1

    async def test_a_rejected_login_is_recorded_with_its_reason(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-14 and the asymmetry it needs: hidden outside, legible inside."""
        # Arrange
        user = await UserFactory.create(session, is_active=False)

        # Act
        with pytest.raises(AuthenticationError):
            await service.authenticate(user.email, DEFAULT_PASSWORD)

        # Assert
        events = await _events_of(session, AccessEventKind.LOGIN_REJECTED)
        assert [event.reason for event in events] == ["INACTIVE"]
        assert events[0].attempted_email == user.email

    async def test_an_attempt_from_an_unknown_address_is_still_recorded(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """Nothing is discarded: there is nobody to attribute it to, and it is kept."""
        # Act
        with pytest.raises(AuthenticationError):
            await service.authenticate("nobody@example.com", "x")

        # Assert
        events = await _events_of(session, AccessEventKind.LOGIN_REJECTED)
        assert events[0].user_id is None
        assert events[0].attempted_email == "nobody@example.com"

    async def test_no_password_is_ever_written_to_the_log(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """The log holds the address that was tried, never the secret."""
        # Act
        with pytest.raises(AuthenticationError):
            await service.authenticate("nobody@example.com", "clave-secreta-123")

        # Assert
        events = await _events_of(session, AccessEventKind.LOGIN_REJECTED)
        written = " ".join(
            str(value)
            for event in events
            for value in (event.attempted_email, event.reason, event.details)
        )
        assert "clave-secreta-123" not in written

    async def test_a_successful_login_is_recorded(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-29: who came in, and when."""
        # Arrange
        user = await UserFactory.create(session)

        # Act
        await service.authenticate(user.email, DEFAULT_PASSWORD)

        # Assert
        events = await _events_of(session, AccessEventKind.LOGIN_SUCCEEDED)
        assert [event.user_id for event in events] == [user.id]


@pytest.mark.integration
@pytest.mark.database
class TestLockout:
    """Trying passwords until one works is not free."""

    async def test_the_access_locks_after_the_configured_attempts(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-45, RF-49: the limit is a parameter, and this test sets it low."""
        # Arrange
        user = await UserFactory.create(session)
        await service.users.set_setting(MAX_ATTEMPTS_KEY, 2)
        await session.commit()

        # Act
        for _ in range(2):
            with pytest.raises(AuthenticationError):
                await service.authenticate(user.email, "no-es-la-clave")

        # Assert
        await session.refresh(user)
        assert user.locked_until is not None

    async def test_a_locked_access_is_refused_even_with_the_right_password(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-46: this is what makes the lock worth anything."""
        # Arrange
        user = await UserFactory.create(session)
        user.locked_until = datetime.now(UTC) + timedelta(minutes=15)
        await session.flush()

        # Act / Assert
        with pytest.raises(AuthenticationError):
            await service.authenticate(user.email, DEFAULT_PASSWORD)

    async def test_the_lock_lets_go_when_it_expires(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-48: temporary means temporary; nobody has to unlock it by hand."""
        # Arrange
        user = await UserFactory.create(session)
        user.locked_until = datetime.now(UTC) - timedelta(seconds=1)
        await session.flush()

        # Act
        token, _ = await service.authenticate(user.email, DEFAULT_PASSWORD)

        # Assert
        assert token

    async def test_locking_is_recorded_for_the_owner(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-47: the owner finds it among the rejected attempts."""
        # Arrange
        user = await UserFactory.create(session)
        await service.users.set_setting(MAX_ATTEMPTS_KEY, 1)
        await session.commit()

        # Act
        with pytest.raises(AuthenticationError):
            await service.authenticate(user.email, "no-es-la-clave")

        # Assert
        assert len(await _events_of(session, AccessEventKind.ACCESS_LOCKED)) == 1

    async def test_a_good_login_clears_the_count(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """Failures have to be *consecutive*, or a slow typist locks themselves out."""
        # Arrange
        user = await UserFactory.create(session)
        with pytest.raises(AuthenticationError):
            await service.authenticate(user.email, "no-es-la-clave")

        # Act
        await service.authenticate(user.email, DEFAULT_PASSWORD)

        # Assert
        await session.refresh(user)
        assert user.failed_attempts == 0


@pytest.mark.integration
@pytest.mark.database
class TestSessionLifetime:
    """What a signed token could not do, and this is here to prove it does."""

    async def test_a_live_session_resolves_to_its_person(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-01."""
        # Arrange
        user = await UserFactory.create(session)
        token, _ = await service.authenticate(user.email, DEFAULT_PASSWORD)

        # Assert
        resolved = await service.resolve_session(token)
        assert resolved is not None and resolved.id == user.id

    async def test_garbage_resolves_to_nobody(self, service: IdentityService) -> None:
        """RF-15."""
        assert await service.resolve_session("no-es-un-token") is None

    async def test_idleness_is_counted_from_the_last_use_not_the_login(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-05, RF-36: somebody working at hour seven is still in at hour nine.

        The one that the 60-second write window could break: if `last_seen_at`
        stopped being refreshed, this session would die on schedule from its
        login instead of from its activity.
        """
        # Arrange
        user = await UserFactory.create(session)
        token, _ = await service.authenticate(user.email, DEFAULT_PASSWORD)
        stored = await service.users.get_live_session(hash_token(token))
        assert stored is not None
        # Seven hours of work: created long ago, used a moment ago.
        stored.created_at = datetime.now(UTC) - timedelta(hours=7)
        stored.last_seen_at = datetime.now(UTC) - timedelta(minutes=1)
        await session.flush()

        # Assert
        assert await service.resolve_session(token) is not None

    async def test_a_session_left_idle_past_the_window_is_gone(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-05: eight hours untouched and the screen asks to log in again."""
        # Arrange
        user = await UserFactory.create(session)
        token, _ = await service.authenticate(user.email, DEFAULT_PASSWORD)
        stored = await service.users.get_live_session(hash_token(token))
        assert stored is not None
        stored.last_seen_at = datetime.now(UTC) - timedelta(hours=9)
        await session.flush()

        # Assert
        assert await service.resolve_session(token) is None

    async def test_logging_out_ends_that_session_only(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-04: closing one browser does not close the other."""
        # Arrange
        user = await UserFactory.create(session)
        first, _ = await service.authenticate(user.email, DEFAULT_PASSWORD)
        second, _ = await service.authenticate(user.email, DEFAULT_PASSWORD)

        # Act
        await service.logout(first)

        # Assert
        assert await service.resolve_session(first) is None
        assert await service.resolve_session(second) is not None


@pytest.mark.integration
@pytest.mark.database
class TestDeactivationAndReactivation:
    """Leaving the team, and coming back as the same person."""

    async def test_deactivating_closes_the_open_sessions(
        self, service: IdentityService, session: AsyncSession, owner: object
    ) -> None:
        """RF-20: the next request fails, not the next hour."""
        # Arrange
        user = await UserFactory.create(session)
        token, _ = await service.authenticate(user.email, DEFAULT_PASSWORD)

        # Act
        await service.deactivate_user(user.id, actor_id=owner.id)  # type: ignore[attr-defined]

        # Assert
        assert await service.resolve_session(token) is None

    async def test_the_owner_cannot_deactivate_themselves(
        self, service: IdentityService, owner: object
    ) -> None:
        """RF-22: nobody locks the only administrator out of the system."""
        with pytest.raises(ValidationError):
            await service.deactivate_user(owner.id, actor_id=owner.id)  # type: ignore[attr-defined]

    async def test_deactivating_keeps_the_person(
        self, service: IdentityService, session: AsyncSession, owner: object
    ) -> None:
        """RF-21: the row stays, so what they authored keeps a name."""
        # Arrange
        user = await UserFactory.create(session)

        # Act
        await service.deactivate_user(user.id, actor_id=owner.id)  # type: ignore[attr-defined]

        # Assert
        kept = await service.get_user(user.id)
        assert kept.name == user.name
        assert kept.is_active is False

    async def test_reactivating_removes_the_old_password(
        self, service: IdentityService, session: AsyncSession, owner: object
    ) -> None:
        """RF-53: the previous password stops existing, not just stops working."""
        # Arrange
        user = await UserFactory.create(session)
        await service.deactivate_user(user.id, actor_id=owner.id)  # type: ignore[attr-defined]

        # Act
        await service.reactivate_user(user.id, actor_id=owner.id)  # type: ignore[attr-defined]

        # Assert
        assert await service.users.get_password(user.id) is None
        with pytest.raises(AuthenticationError):
            await service.authenticate(user.email, DEFAULT_PASSWORD)

    async def test_reactivating_invites_again(
        self,
        service: IdentityService,
        session: AsyncSession,
        owner: object,
        queued_access_links: object,
    ) -> None:
        """RF-51, RF-52: coming back means being invited, not being restored."""
        # Arrange
        user = await UserFactory.create(session)
        await service.deactivate_user(user.id, actor_id=owner.id)  # type: ignore[attr-defined]

        # Act
        back = await service.reactivate_user(user.id, actor_id=owner.id)  # type: ignore[attr-defined]

        # Assert
        assert back.is_active is True
        assert back.activated_at is None
        assert len(await _tokens_of(session, user.id, TokenPurpose.INVITATION)) == 1
        assert queued_access_links.count == 1  # type: ignore[attr-defined]

    async def test_reactivating_an_active_access_conflicts(
        self, service: IdentityService, session: AsyncSession, owner: object
    ) -> None:
        """There is nothing to bring back."""
        # Arrange
        user = await UserFactory.create(session)

        # Act / Assert
        with pytest.raises(ConflictError):
            await service.reactivate_user(user.id, actor_id=owner.id)  # type: ignore[attr-defined]

    async def test_the_change_is_recorded_with_actor_and_subject(
        self, service: IdentityService, session: AsyncSession, owner: object
    ) -> None:
        """RF-23: in a login they are the same person; here they are not."""
        # Arrange
        user = await UserFactory.create(session)

        # Act
        await service.deactivate_user(user.id, actor_id=owner.id)  # type: ignore[attr-defined]

        # Assert
        events = await _events_of(session, AccessEventKind.ACCESS_DEACTIVATED)
        assert [(event.user_id, event.actor_user_id) for event in events] == [
            (user.id, owner.id)  # type: ignore[attr-defined]
        ]


@pytest.mark.integration
@pytest.mark.database
class TestRoles:
    """One owner, and a role change that is written down."""

    async def test_promoting_a_second_owner_is_refused(
        self, service: IdentityService, session: AsyncSession, owner: object
    ) -> None:
        """RF-50: not by creation, and not by promotion either."""
        # Arrange
        user = await UserFactory.create(session, role=UserRole.SALES)

        # Act / Assert
        with pytest.raises(ConflictError):
            await service.update_user(user.id, UserUpdate(role=UserRole.OWNER))

    async def test_a_role_change_is_recorded_with_what_changed(
        self, service: IdentityService, session: AsyncSession, owner: object
    ) -> None:
        """RF-23: the before and the after, not just the fact."""
        # Arrange
        user = await UserFactory.create(session, role=UserRole.SALES)

        # Act
        await service.update_user(
            user.id,
            UserUpdate(role=UserRole.PURCHASING),
            actor_id=owner.id,  # type: ignore[attr-defined]
        )

        # Assert
        events = await _events_of(session, AccessEventKind.ACCESS_ROLE_CHANGED)
        assert events[0].details == {"role": {"from": "SALES", "to": "PURCHASING"}}

    async def test_updating_an_unknown_access_is_not_found(self, service: IdentityService) -> None:
        """The negative case, which the happy path never reaches."""
        with pytest.raises(NotFoundError):
            await service.update_user(999999, UserUpdate(name="Nadie"))


@pytest.mark.integration
@pytest.mark.database
class TestOwnPassword:
    """Changing it, and losing it."""

    async def test_changing_it_replaces_the_credential(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-25, RF-26."""
        # Arrange
        user = await UserFactory.create(session)

        # Act
        await service.change_password(user.id, DEFAULT_PASSWORD, NEW_PASSWORD)

        # Assert
        credential = await service.users.get_password(user.id)
        assert credential is not None
        assert verify_password(NEW_PASSWORD, credential.hashed_password)
        assert not verify_password(DEFAULT_PASSWORD, credential.hashed_password)

    async def test_the_wrong_current_password_is_refused(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """Knowing the session is not knowing the password."""
        # Arrange
        user = await UserFactory.create(session)

        # Act / Assert
        with pytest.raises(AuthenticationError):
            await service.change_password(user.id, "no-es-la-clave", NEW_PASSWORD)

    async def test_changing_it_closes_the_other_sessions(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-26: a password that stopped being valid must not survive in another browser."""
        # Arrange
        user = await UserFactory.create(session)
        elsewhere, _ = await service.authenticate(user.email, DEFAULT_PASSWORD)
        here, _ = await service.authenticate(user.email, DEFAULT_PASSWORD)

        # Act
        await service.change_password(user.id, DEFAULT_PASSWORD, NEW_PASSWORD, current_token=here)

        # Assert
        assert await service.resolve_session(elsewhere) is None
        assert await service.resolve_session(here) is not None

    async def test_a_recovery_answers_the_same_for_an_address_that_does_not_exist(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """RF-39: the form cannot be used to find out who has an account."""
        # Act
        known = await service.request_password_reset((await UserFactory.create(session)).email)
        unknown = await service.request_password_reset("nobody@example.com")

        # Assert
        assert known is None and unknown is None

    async def test_a_recovery_issues_a_token_and_queues_the_message(
        self, service: IdentityService, session: AsyncSession, queued_access_links: object
    ) -> None:
        """RF-27, RF-38: without the owner, and out by WhatsApp."""
        # Arrange
        user = await UserFactory.create(session)

        # Act
        await service.request_password_reset(user.email)

        # Assert
        assert len(await _tokens_of(session, user.id, TokenPurpose.PASSWORD_RESET)) == 1
        assert queued_access_links.count == 1  # type: ignore[attr-defined]

    async def test_a_recovery_for_a_deactivated_access_does_nothing(
        self, service: IdentityService, session: AsyncSession, queued_access_links: object
    ) -> None:
        """A closed access does not come back through the recovery form."""
        # Arrange
        user = await UserFactory.create(session, is_active=False)

        # Act
        await service.request_password_reset(user.email)

        # Assert
        assert await _tokens_of(session, user.id, TokenPurpose.PASSWORD_RESET) == []
        assert queued_access_links.count == 0  # type: ignore[attr-defined]


@pytest.mark.integration
@pytest.mark.database
class TestProjectedSettings:
    """The three parameters this module does not own."""

    async def test_a_parameter_it_cares_about_is_taken_in(
        self, service: IdentityService, session: AsyncSession
    ) -> None:
        """The projection is what lets identity avoid reading someone else's table."""
        # Act
        await service.apply_setting(MAX_ATTEMPTS_KEY, 9)

        # Assert
        stored = await service.users.get_setting(MAX_ATTEMPTS_KEY)
        assert stored is not None and stored.value == 9

    async def test_a_parameter_of_another_module_is_ignored(self, service: IdentityService) -> None:
        """Every parameter change is published to everybody; most are not ours."""
        # Act
        await service.apply_setting("price_update.interval_hours", 6)

        # Assert
        assert await service.users.get_setting("price_update.interval_hours") is None
