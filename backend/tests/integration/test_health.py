"""`/health` against a real database.

This is the endpoint the container's healthcheck and the public status page both
call, and the only route the API answers today. Its two mountings are part of
the contract, not an implementation detail: the orchestrator asks at the root
because it has no reason to know the API version, the browser asks under the
prefix because that is what the generated client knows.
"""

import pytest
from httpx import AsyncClient

from app.config import settings

pytestmark = [pytest.mark.integration, pytest.mark.database]

API_PREFIX = f"/api/{settings.API_VERSION}"


class TestHealth:
    """With the database up, the report says so on both paths."""

    @pytest.mark.parametrize("path", [f"{API_PREFIX}/health", "/health"], ids=["prefixed", "root"])
    async def test_answers_ok_on_both_mountings(self, client: AsyncClient, path: str) -> None:
        response = await client.get(path)

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    async def test_reports_the_database_and_identifies_the_service(
        self, client: AsyncClient
    ) -> None:
        body = (await client.get(f"{API_PREFIX}/health")).json()

        assert body["database"] == {"status": "ok", "detail": None}
        assert body["service"] == settings.PROJECT_NAME
        assert body["environment"] == settings.ENVIRONMENT

    async def test_needs_no_credentials(self, client: AsyncClient) -> None:
        """The status page is opened by people who cannot log in."""
        assert (await client.get(f"{API_PREFIX}/health")).status_code == 200

    async def test_is_published_in_the_schema_once(self, client: AsyncClient) -> None:
        """Mounted twice, documented once: two entries would collide on operation ids."""
        paths = (await client.get("/openapi.json")).json()["paths"]

        assert f"{API_PREFIX}/health" in paths
        assert "/health" not in paths
