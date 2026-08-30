"""Role-based access control, over HTTP.

The business has three roles — OWNER, PURCHASING, SALES — and authorisation is
enforced per resource, not by hiding links in a menu. These tests call the real
endpoints with a real token for each role.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User, UserRole
from tests.conftest import API_PREFIX, authorization_header
from tests.factories.user_factory import DEFAULT_PASSWORD, UserFactory

# No password: the owner hands out accesses, not credentials (RF-44). The phone
# is required, because that is where the invitation goes.
NEW_USER = {
    "email": "alta@example.com",
    "name": "Alta",
    "phone": "+5491144445555",
    "role": UserRole.SALES.value,
}
# A key of the catalog: since 003 the list is closed, so an invented key is
# refused before authorisation ever becomes the interesting part of the test.
PARAMETERS = {"items": [{"key": "price_update.interval_hours", "value": 24}]}


@pytest.mark.integration
@pytest.mark.database
class TestPurchasingRole:
    """What whoever handles purchasing can and cannot do."""

    async def test_cannot_create_a_user(self, purchasing_client: AsyncClient) -> None:
        """Handing out accounts and roles is the owner's decision."""
        # Act
        response = await purchasing_client.post(f"{API_PREFIX}/users", json=NEW_USER)

        # Assert
        assert response.status_code == 403

    async def test_cannot_update_the_business_parameters(
        self, purchasing_client: AsyncClient
    ) -> None:
        """These values decide how the platform behaves: owner only."""
        # Act
        response = await purchasing_client.put(
            f"{API_PREFIX}/operations/parameters", json=PARAMETERS
        )

        # Assert
        assert response.status_code == 403

    async def test_cannot_list_users(self, purchasing_client: AsyncClient) -> None:
        """RF-24: the access screens are the owner's, reading them included.

        This used to be allowed, on the argument that the team should know who
        its colleagues are. No requirement asks for it, and the list carries
        everybody's email, phone and role — so it went back behind the same
        door as the rest of the administration.
        """
        # Act
        response = await purchasing_client.get(f"{API_PREFIX}/users")

        # Assert
        assert response.status_code == 403

    async def test_can_read_the_job_history(self, purchasing_client: AsyncClient) -> None:
        """Whether last night's extraction ran is not privileged information."""
        # Act
        response = await purchasing_client.get(f"{API_PREFIX}/operations/jobs")

        # Assert
        assert response.status_code == 200

    async def test_cannot_read_the_business_parameters(
        self, purchasing_client: AsyncClient
    ) -> None:
        """Reading the rules is as restricted as writing them."""
        # Act
        response = await purchasing_client.get(f"{API_PREFIX}/operations/parameters")

        # Assert
        assert response.status_code == 403

    async def test_cannot_deactivate_a_user(
        self, purchasing_client: AsyncClient, sales_user: User
    ) -> None:
        """Disabling a colleague's account is an administrative act."""
        # Act
        response = await purchasing_client.post(f"{API_PREFIX}/users/{sales_user.id}/deactivate")

        # Assert
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.database
class TestSalesRole:
    """Sales has the same operational reach as purchasing."""

    async def test_cannot_create_a_user(self, sales_client: AsyncClient) -> None:
        """Administration is closed to the operational roles."""
        assert (await sales_client.post(f"{API_PREFIX}/users", json=NEW_USER)).status_code == 403

    async def test_can_read_its_own_account(self, sales_client: AsyncClient) -> None:
        """Every authenticated role can read itself."""
        # Act
        response = await sales_client.get(f"{API_PREFIX}/auth/me")

        # Assert
        assert response.status_code == 200
        assert response.json()["user"]["role"] == UserRole.SALES.value


@pytest.mark.integration
@pytest.mark.database
class TestOwnerRole:
    """The owner is admitted everywhere."""

    async def test_can_create_a_user(self, owner_client: AsyncClient) -> None:
        """The route the operational roles are refused."""
        # Act
        response = await owner_client.post(f"{API_PREFIX}/users", json=NEW_USER)

        # Assert
        assert response.status_code == 201
        assert response.json()["email"] == NEW_USER["email"]

    async def test_can_update_the_business_parameters(self, owner_client: AsyncClient) -> None:
        """Writing the rules is the owner's."""
        # Act
        response = await owner_client.put(f"{API_PREFIX}/operations/parameters", json=PARAMETERS)

        # Assert
        assert response.status_code == 200
        assert response.json()[0]["key"] == "price_update.interval_hours"
        assert response.json()[0]["value"] == 24

    async def test_can_list_users(self, owner_client: AsyncClient) -> None:
        """The only role that reaches the list at all."""
        assert (await owner_client.get(f"{API_PREFIX}/users")).status_code == 200

    async def test_can_change_a_role(self, owner_client: AsyncClient, sales_user: User) -> None:
        """Deciding who does what is the point of the role."""
        # Act
        response = await owner_client.patch(
            f"{API_PREFIX}/users/{sales_user.id}", json={"role": UserRole.PURCHASING.value}
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["role"] == UserRole.PURCHASING.value


@pytest.mark.integration
@pytest.mark.database
class TestAnonymousCallers:
    """No credentials, no answer."""

    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("GET", f"{API_PREFIX}/users"),
            ("GET", f"{API_PREFIX}/auth/me"),
            ("GET", f"{API_PREFIX}/operations/jobs"),
            ("GET", f"{API_PREFIX}/operations/parameters"),
        ],
    )
    async def test_a_protected_route_without_a_token_is_401(
        self, client: AsyncClient, method: str, path: str
    ) -> None:
        """A missing token is not a 403: the caller was never identified."""
        # Act
        response = await client.request(method, path)

        # Assert
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"

    async def test_an_invalid_token_is_401(self, client: AsyncClient) -> None:
        """A token that cannot be verified identifies nobody."""
        # Act
        response = await client.get(
            f"{API_PREFIX}/users", headers={"Authorization": "Bearer not-a-token"}
        )

        # Assert
        assert response.status_code == 401

    async def test_the_token_of_a_deactivated_user_is_401(
        self,
        client: AsyncClient,
        owner_client: AsyncClient,
        sales_user: User,
        session: AsyncSession,
    ) -> None:
        """Deactivating an account has to close the session it is holding."""
        # Arrange
        headers = await authorization_header(session, sales_user)
        assert (await client.get(f"{API_PREFIX}/auth/me", headers=headers)).status_code == 200

        # Act
        await owner_client.post(f"{API_PREFIX}/users/{sales_user.id}/deactivate")
        response = await client.get(f"{API_PREFIX}/auth/me", headers=headers)

        # Assert
        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.database
class TestOwnAccountOnly:
    """Routes that act on the caller take the caller from the token."""

    async def test_change_password_cannot_be_pointed_at_another_account(
        self, sales_client: AsyncClient
    ) -> None:
        """The body carries passwords, never a user id.

        If the endpoint took a target user, a session would be enough to
        overwrite somebody else's credential.
        """
        # Act
        response = await sales_client.post(
            f"{API_PREFIX}/auth/password/change",
            json={
                "current_password": DEFAULT_PASSWORD,
                "new_password": "otra-clave-2026",
                # Ignored by the schema: there is no target field to abuse.
                "user_id": 1,
            },
        )

        # Assert
        assert response.status_code == 204

    async def test_a_wrong_current_password_is_401(self, sales_client: AsyncClient) -> None:
        """Holding the session is not enough to change the password."""
        # Act
        response = await sales_client.post(
            f"{API_PREFIX}/auth/password/change",
            json={"current_password": "incorrecta", "new_password": "otra-clave-2026"},
        )

        # Assert
        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.database
class TestRolesInTheDatabase:
    """The three roles the business actually has."""

    @pytest.mark.parametrize("role", list(UserRole))
    async def test_every_role_can_authenticate(
        self, client: AsyncClient, session: AsyncSession, role: UserRole
    ) -> None:
        """No role is locked out of the platform it was given."""
        # Arrange
        user = await UserFactory.create(session, role=role)

        # Act
        response = await client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": user.email, "password": DEFAULT_PASSWORD},
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["user"]["role"] == role.value
