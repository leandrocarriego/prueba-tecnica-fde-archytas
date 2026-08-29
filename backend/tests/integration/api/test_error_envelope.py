"""One error shape for the whole API.

`app.main` maps the domain errors of `app.shared.errors` to status codes and
wraps every failure — its own and FastAPI's — in the same envelope:

    {"error": {"type": ..., "message": ..., "details": ...}}

The frontend reads exactly this, so the shape is part of the contract and not
an implementation detail.
"""

import pytest
from httpx import AsyncClient, Response

from app.modules.identity.models import User, UserRole
from tests.conftest import API_PREFIX


def envelope(response: Response) -> dict[str, object]:
    """Return the error body, having checked it has the agreed shape."""
    body = response.json()
    assert set(body) == {"error"}, f"Unexpected error body: {body}"
    error = body["error"]
    assert set(error) == {"type", "message", "details"}, f"Unexpected error body: {body}"
    assert isinstance(error["message"], str) and error["message"]
    return error


@pytest.mark.integration
@pytest.mark.database
class TestDomainErrors:
    """Errors raised by the services, mapped by the composition root."""

    async def test_not_found_is_404_and_carries_the_id(self, owner_client: AsyncClient) -> None:
        """`NotFoundError` becomes a 404, with the details the service attached."""
        # Act
        response = await owner_client.get(f"{API_PREFIX}/users/999999")

        # Assert
        assert response.status_code == 404
        error = envelope(response)
        assert error["type"] == "NotFoundError"
        assert error["details"] == {"user_id": 999999}

    async def test_conflict_is_409(self, owner_client: AsyncClient, sales_user: User) -> None:
        """`ConflictError` becomes a 409."""
        # Act
        response = await owner_client.post(
            f"{API_PREFIX}/users",
            json={
                "email": sales_user.email,
                "name": "Repetido",
                "phone": "+5491155556666",
            },
        )

        # Assert
        assert response.status_code == 409
        assert envelope(response)["type"] == "ConflictError"

    async def test_authentication_error_is_401(self, client: AsyncClient, owner: User) -> None:
        """`AuthenticationError` becomes a 401."""
        # Act
        response = await client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": owner.email, "password": "clave-incorrecta"},
        )

        # Assert
        assert response.status_code == 401
        error = envelope(response)
        assert error["type"] == "AuthenticationError"
        # The message must not say which half of the credentials was wrong.
        assert error["message"] == "Invalid email or password"

    async def test_validation_error_is_422(self, client: AsyncClient) -> None:
        """`ValidationError` becomes a 422: the payload is well-formed but unusable."""
        # Act
        response = await client.post(
            f"{API_PREFIX}/auth/password-reset/confirm",
            json={"token": "un-token-inventado", "new_password": "una-clave-nueva-2026"},
        )

        # Assert
        assert response.status_code == 422
        assert envelope(response)["type"] == "ValidationError"


@pytest.mark.integration
@pytest.mark.database
class TestFrameworkErrors:
    """FastAPI's own failures wear the same envelope."""

    async def test_a_missing_token_is_401_in_the_same_shape(self, client: AsyncClient) -> None:
        """The auth dependencies raise `HTTPException`; clients still see one shape."""
        # Act
        response = await client.get(f"{API_PREFIX}/auth/me")

        # Assert
        assert response.status_code == 401
        error = envelope(response)
        assert error["type"] == "Unauthorized"
        assert error["details"] == {}
        # The header a client needs to know what to do next survives the wrapping.
        assert response.headers["WWW-Authenticate"] == "Bearer"

    async def test_a_forbidden_role_is_403_in_the_same_shape(
        self, purchasing_client: AsyncClient
    ) -> None:
        """A role check failure is wrapped like everything else."""
        # Act
        response = await purchasing_client.get(f"{API_PREFIX}/operations/parameters")

        # Assert
        assert response.status_code == 403
        assert envelope(response)["type"] == "Forbidden"

    async def test_an_unknown_path_is_404_in_the_same_shape(self, client: AsyncClient) -> None:
        """Even a route that does not exist answers in the agreed shape."""
        # Act
        response = await client.get(f"{API_PREFIX}/no-existe")

        # Assert
        assert response.status_code == 404
        assert envelope(response)["type"] == "Not Found"

    async def test_a_malformed_payload_is_422_with_the_field_errors(
        self, owner_client: AsyncClient
    ) -> None:
        """A request that does not validate reports which fields failed."""
        # Act
        response = await owner_client.post(
            f"{API_PREFIX}/users", json={"email": "no-es-un-email", "name": ""}
        )

        # Assert
        assert response.status_code == 422
        error = envelope(response)
        assert error["type"] == "RequestValidationError"
        details = error["details"]
        assert isinstance(details, dict)
        # The details are JSON-encodable: a validation error can carry exotic
        # values, and the envelope encodes them rather than crashing on them.
        assert [item["loc"] for item in details["errors"]]

    async def test_an_unsupported_method_is_405_in_the_same_shape(
        self, owner_client: AsyncClient
    ) -> None:
        """Starlette's own 405 is wrapped too."""
        # Act
        response = await owner_client.delete(f"{API_PREFIX}/operations/parameters")

        # Assert
        assert response.status_code == 405
        assert envelope(response)["type"] == "Method Not Allowed"


@pytest.mark.integration
@pytest.mark.database
class TestSuccessfulResponsesAreNotWrapped:
    """The envelope is for failures only."""

    async def test_a_successful_response_carries_the_resource(
        self, owner_client: AsyncClient, owner: User
    ) -> None:
        """A 200 body is the resource itself, with no wrapper around it."""
        # Act
        response = await owner_client.get(f"{API_PREFIX}/auth/me")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert "error" not in body
        # `/auth/me` answers with who is working *and* what they may reach, so
        # the menu is drawn from what the backend enforces.
        assert body["user"]["email"] == owner.email
        assert body["user"]["role"] == UserRole.OWNER.value
        assert body["permissions"]
