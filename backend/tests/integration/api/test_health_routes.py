"""Integration tests for the health endpoint."""

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.modules.operations.repository import DatabaseProbe
from tests.conftest import API_PREFIX


@pytest.mark.integration
@pytest.mark.database
class TestHealthRoutes:
    """`/health`: public, and honest about the database."""

    async def test_health_reports_ok(self, client: AsyncClient) -> None:
        """A reachable database answers 200 with every component ok."""
        # Act
        response = await client.get(f"{API_PREFIX}/health")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["service"] == settings.PROJECT_NAME
        assert body["environment"] == settings.ENVIRONMENT
        assert body["database"] == {"status": "ok", "detail": None}

    async def test_health_is_public(self, client: AsyncClient) -> None:
        """No credentials: Docker's healthcheck runs before anyone logs in."""
        # Act
        response = await client.get(f"{API_PREFIX}/health")

        # Assert
        assert "authorization" not in client.headers
        assert response.status_code == 200

    async def test_health_answers_at_the_root_too(self, client: AsyncClient) -> None:
        """The same endpoint is mounted without the API prefix for the container."""
        # Act
        response = await client.get("/health")

        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    async def test_health_reports_503_when_the_database_is_down(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An orchestrator restarts on the status code, not on the body."""

        # Arrange
        async def _fail(self: DatabaseProbe) -> None:
            raise OperationalError("select 1", {}, Exception("connection refused"))

        monkeypatch.setattr(DatabaseProbe, "ping", _fail)

        # Act
        response = await client.get(f"{API_PREFIX}/health")

        # Assert
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "down"
        assert body["database"]["status"] == "down"
        # The reason stays in the log: `/health` is public and must not leak
        # hostnames or drivers.
        assert "connection refused" not in body["database"]["detail"]
