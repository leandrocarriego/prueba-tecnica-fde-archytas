"""The record the owner reads: who got in, and who was turned away.

`identity` is the only module that writes here, so these tests go through the
API: what matters is not that a row exists but that the right person can read
it and the other two cannot.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.modules.identity.service import MAX_ATTEMPTS_KEY, IdentityService
from tests.conftest import API_PREFIX
from tests.factories.user_factory import DEFAULT_PASSWORD


@pytest.mark.integration
@pytest.mark.database
class TestWhoMayReadTheLog:
    """RF-30 and RF-31: it is the owner's, and only the owner's."""

    async def test_the_owner_reads_it(self, owner_client: AsyncClient) -> None:
        """RF-30."""
        # Act
        response = await owner_client.get(f"{API_PREFIX}/access-log")

        # Assert
        assert response.status_code == 200
        assert "items" in response.json()

    async def test_purchasing_cannot(self, purchasing_client: AsyncClient) -> None:
        """RF-31: nobody sees other people's activity."""
        assert (await purchasing_client.get(f"{API_PREFIX}/access-log")).status_code == 403

    async def test_sales_cannot(self, sales_client: AsyncClient) -> None:
        """RF-31."""
        assert (await sales_client.get(f"{API_PREFIX}/access-log")).status_code == 403

    async def test_an_anonymous_caller_cannot(self, client: AsyncClient) -> None:
        """RF-15: no session, no answer."""
        assert (await client.get(f"{API_PREFIX}/access-log")).status_code == 401


@pytest.mark.integration
@pytest.mark.database
class TestWhatTheLogShows:
    """The three things that have to end up in front of the owner."""

    async def test_a_login_appears_with_its_person_and_its_moment(
        self, owner_client: AsyncClient, client: AsyncClient, sales_user: User
    ) -> None:
        """RF-29."""
        # Arrange
        await client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": sales_user.email, "password": DEFAULT_PASSWORD},
        )

        # Act
        body = (await owner_client.get(f"{API_PREFIX}/access-log")).json()

        # Assert
        logins = [row for row in body["items"] if row["kind"] == "LOGIN_SUCCEEDED"]
        assert any(row["user_id"] == sales_user.id for row in logins)
        assert all(row["occurred_at"] for row in logins)

    async def test_a_rejected_attempt_appears_with_the_address_that_was_tried(
        self, owner_client: AsyncClient, client: AsyncClient
    ) -> None:
        """RF-02 kept the reason from the caller; the owner still gets to see it."""
        # Arrange
        await client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": "intruso@example.com", "password": "probando"},
        )

        # Act
        body = (await owner_client.get(f"{API_PREFIX}/access-log")).json()

        # Assert
        rejected = [row for row in body["items"] if row["kind"] == "LOGIN_REJECTED"]
        assert [row["attempted_email"] for row in rejected] == ["intruso@example.com"]
        # The password that was tried is nowhere in the record.
        assert "probando" not in str(body)

    async def test_a_lockout_appears_among_the_rejected_attempts(
        self,
        owner_client: AsyncClient,
        client: AsyncClient,
        sales_user: User,
        session: AsyncSession,
    ) -> None:
        """RF-47: it is how the owner finds out somebody is trying passwords."""
        # Arrange
        await IdentityService(session).users.set_setting(MAX_ATTEMPTS_KEY, 1)
        await session.commit()
        await client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": sales_user.email, "password": "no-es-la-clave"},
        )

        # Act
        body = (await owner_client.get(f"{API_PREFIX}/access-log")).json()

        # Assert
        assert any(row["kind"] == "ACCESS_LOCKED" for row in body["items"])

    async def test_the_log_can_be_filtered_by_kind(
        self, owner_client: AsyncClient, client: AsyncClient, sales_user: User
    ) -> None:
        """A list nobody can narrow is a list nobody reads."""
        # Arrange
        await client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": sales_user.email, "password": DEFAULT_PASSWORD},
        )

        # Act
        response = await owner_client.get(
            f"{API_PREFIX}/access-log", params={"kind": "LOGIN_SUCCEEDED"}
        )

        # Assert
        assert response.status_code == 200
        assert {row["kind"] for row in response.json()["items"]} <= {"LOGIN_SUCCEEDED"}


@pytest.mark.integration
@pytest.mark.database
class TestRefusalsAreRecorded:
    """RF-14: knowing that somebody tried to reach where they should not.

    The row is written by a middleware and not by the route, because the 403
    comes out of a dependency and takes the request's transaction down with it.
    That is why this is an integration test and could never be a unit one:
    what is being verified is that the write survives the rollback.
    """

    async def test_being_refused_a_section_is_recorded(
        self, owner_client: AsyncClient, sales_client: AsyncClient
    ) -> None:
        """The owner has to see that Julián tried to open the suppliers screen."""
        # Arrange — sales reaches for a section that is not theirs
        refused = await sales_client.get(f"{API_PREFIX}/users")
        assert refused.status_code == 403

        # Act
        body = (await owner_client.get(f"{API_PREFIX}/access-log")).json()

        # Assert
        denials = [row for row in body["items"] if row["kind"] == "PERMISSION_DENIED"]
        assert denials, "the refusal left no trace"
        assert denials[0]["resource"]

    async def test_the_refusal_says_what_was_reached_for(
        self, owner_client: AsyncClient, sales_client: AsyncClient
    ) -> None:
        """RF-14: *"qué quiso ver"*, in the owner's words."""
        # Arrange
        await sales_client.get(f"{API_PREFIX}/access-log")

        # Act
        body = (await owner_client.get(f"{API_PREFIX}/access-log")).json()

        # Assert
        denials = [row for row in body["items"] if row["kind"] == "PERMISSION_DENIED"]
        assert any("/access-log" in (row["resource"] or "") for row in denials)
        assert any(row["reason"] == "SECTION_FORBIDDEN" for row in denials)
