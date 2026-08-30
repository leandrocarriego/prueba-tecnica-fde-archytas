"""Integration tests for the health endpoint."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.modules.operations import repository as repository_module
from app.modules.operations.repository import DatabaseProbe
from app.quality import Quality, get_quality
from tests.conftest import API_PREFIX


def gateway_answering(handler: Any, monkeypatch: pytest.MonkeyPatch) -> list[httpx.Request]:
    """Point the probe's HTTP client at a transport under the test's control.

    Same shape as the notifications tests: a real `httpx.AsyncClient` over a
    mock transport, because what is worth checking is the request that actually
    goes out.
    """
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    def build(**kwargs: Any) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(record), **kwargs)

    monkeypatch.setattr(
        repository_module, "httpx", SimpleNamespace(AsyncClient=build, HTTPError=httpx.HTTPError)
    )
    return seen


def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give the probe a gateway to ask about."""
    monkeypatch.setattr(settings, "EVOLUTION_API_URL", "http://evolution.interno:8099")
    monkeypatch.setattr(settings, "EVOLUTION_INSTANCE", "cordillera")
    monkeypatch.setattr(settings, "EVOLUTION_API_KEY", "una-clave-de-prueba")


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
        # No gateway configured in the suite, which is not a fault: see below.
        assert body["whatsapp"]["status"] == "off"

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


@pytest.mark.integration
@pytest.mark.database
class TestTheWhatsAppComponent:
    """The channel is reported, and deliberately does not decide the verdict.

    It is worth reporting because when the session drops, every invitation and
    every alert stops arriving and nothing says so — the channel that would
    carry the warning is the one that is down.

    It must not decide the verdict because the route answers 503 when `status`
    is not OK and Docker restarts on that. A gateway belonging to a third party
    must never be able to restart this API.
    """

    async def test_an_unconfigured_channel_is_off_and_not_a_fault(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Nobody asked for it, so nothing is broken."""
        # Arrange
        monkeypatch.setattr(settings, "EVOLUTION_API_KEY", "")

        # Act
        response = await client.get(f"{API_PREFIX}/health")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["whatsapp"]["status"] == "off"

    async def test_a_connected_session_is_ok(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The gateway says the session is open, and it is asked with the key."""
        # Arrange
        configured(monkeypatch)
        requests = gateway_answering(
            lambda _r: httpx.Response(200, json={"instance": {"state": "open"}}), monkeypatch
        )

        # Act
        response = await client.get(f"{API_PREFIX}/health")

        # Assert
        assert response.status_code == 200
        assert response.json()["whatsapp"] == {"status": "ok", "detail": None}
        assert requests[0].url.path == "/instance/connectionState/cordillera"
        assert requests[0].headers["apikey"] == "una-clave-de-prueba"

    async def test_a_gateway_that_does_not_answer_does_not_take_the_api_down(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The one that matters: 200, so Docker does not restart the API."""

        # Arrange
        def refuse(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        configured(monkeypatch)
        gateway_answering(refuse, monkeypatch)

        # Act
        response = await client.get(f"{API_PREFIX}/health")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["whatsapp"]["status"] == "down"

    async def test_an_unpaired_session_is_down_rather_than_off(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The gateway answered: the phone stopped being paired. Nobody chose that."""
        # Arrange
        configured(monkeypatch)
        gateway_answering(
            lambda _r: httpx.Response(200, json={"instance": {"state": "close"}}), monkeypatch
        )

        # Act
        response = await client.get(f"{API_PREFIX}/health")

        # Assert
        assert response.status_code == 200
        assert response.json()["whatsapp"]["status"] == "down"

    async def test_the_detail_never_leaks_the_gateway(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`/health` is public. It must not hand out the address, key or instance."""

        # Arrange
        def refuse(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused to http://evolution.interno:8099")

        configured(monkeypatch)
        gateway_answering(refuse, monkeypatch)

        # Act
        response = await client.get(f"{API_PREFIX}/health")

        # Assert
        detail = response.json()["whatsapp"]["detail"]
        assert "evolution.interno" not in detail
        assert "8099" not in detail
        assert "una-clave-de-prueba" not in detail
        assert "cordillera" not in detail
        assert "connection refused" not in detail


@pytest.mark.integration
@pytest.mark.database
class TestTheQualitySnapshot:
    """The two numbers about the code itself, and who gets to read them.

    They are a claim, so the platform can only ever repeat a measurement or say
    nothing: `scripts/quality_snapshot.py` writes it from the artefacts of a
    real run and CI fails when the committed file disagrees with the suite.
    These tests cover the half that runs in production.

    And they need a session. How well a system is tested is a fact about the
    people who build it, not something to read off the internet by anyone who
    finds the domain.
    """

    @pytest.fixture(autouse=True)
    def _fresh(self) -> Any:
        """The snapshot is cached for the process; each test gets its own."""
        get_quality.cache_clear()
        yield
        get_quality.cache_clear()

    async def test_the_public_health_says_nothing_about_it(self, client: AsyncClient) -> None:
        """The one that matters: `/health` is public and must not carry it."""
        # Act
        response = await client.get(f"{API_PREFIX}/health")

        # Assert
        assert response.status_code == 200
        assert "quality" not in response.json()

    async def test_it_reports_what_the_suite_measured(
        self, owner_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With a session, the numbers reach the page unchanged."""
        # Arrange
        monkeypatch.setattr(
            "app.modules.operations.service.get_quality",
            lambda: Quality(tests=550, coverage=94.74),
        )

        # Act
        response = await owner_client.get(f"{API_PREFIX}/operations/quality")

        # Assert
        assert response.status_code == 200
        assert response.json() == {"tests": 550, "coverage": 94.74}

    async def test_an_image_without_a_snapshot_says_nothing(
        self, owner_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Silence is the honest answer to "we do not know"."""
        # Arrange
        monkeypatch.setattr("app.modules.operations.service.get_quality", lambda: None)

        # Act
        response = await owner_client.get(f"{API_PREFIX}/operations/quality")

        # Assert
        assert response.status_code == 200
        assert response.json() is None

    async def test_a_missing_file_never_breaks_the_route(
        self, owner_client: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """The API works perfectly well without knowing its own coverage."""
        # Arrange
        monkeypatch.setattr("app.quality.SNAPSHOT", tmp_path / "no-esta.json")

        # Act
        response = await owner_client.get(f"{API_PREFIX}/operations/quality")

        # Assert
        assert response.status_code == 200
        assert response.json() is None

    async def test_a_corrupt_file_is_not_a_number_it_made_up(
        self, owner_client: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """The one thing it must never do is invent the figure."""
        # Arrange
        broken = tmp_path / "quality.json"
        broken.write_text('{"tests": "todos"}', encoding="utf-8")
        monkeypatch.setattr("app.quality.SNAPSHOT", broken)

        # Act
        response = await owner_client.get(f"{API_PREFIX}/operations/quality")

        # Assert
        assert response.status_code == 200
        assert response.json() is None
