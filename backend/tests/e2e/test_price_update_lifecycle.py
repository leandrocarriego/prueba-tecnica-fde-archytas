"""The price update, from an empty database to a decided case, over the API.

The acceptance criteria of the spec read as one story: the system brings the
list by itself, the prices show up, something cannot be resolved, a person
decides, and the platform stops asking. This walks that story.

**One thing here is not HTTP, and it cannot be.** The extraction runs in a
Celery worker against a portal, and the suite has neither: no RabbitMQ, no
browser (`TEST-03`). So where the worker would pick the job up, the test runs
the task's own body — the same code, in this process — and everything before and
after it is a real request. Faking that step instead would prove nothing about
the pipeline it triggers.
"""

from collections.abc import Callable, Iterator
from types import SimpleNamespace, TracebackType
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications import tasks as notification_tasks
from app.modules.operations import service as operations_service
from app.modules.portal import handlers as portal_handlers
from app.modules.portal import service as portal_service
from app.modules.portal import tasks as portal_tasks
from tests.conftest import API_PREFIX
from tests.factories.portal_factory import FakePortal, broken_list_bytes

pytestmark = [pytest.mark.e2e, pytest.mark.database, pytest.mark.portal]

PRICES = f"{API_PREFIX}/prices"
UPDATES = f"{API_PREFIX}/price-updates"
TRIAGE = f"{API_PREFIX}/triage"

UNKNOWN_CODE = "COR-0999"

extract_price_list = portal_tasks.extract_price_list.run.__wrapped__


class Recorder:
    """Anything that would reach the broker, written down instead."""

    def __init__(self) -> None:
        self.calls: list[Any] = []

    def apply_async(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)

    def delay(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(args)

    def __call__(self, *args: Any) -> None:
        self.calls.append(args)


class _Handle:
    """Lends the test's session to a task and never closes it."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


@pytest.fixture
def worker(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Callable[[int | None, bytes | None], Any]]:
    """The worker, standing where RabbitMQ and Playwright would be.

    It runs the extraction task's body against the pinned fixtures, on the
    session this test rolls back, and records everything the platform tried to
    queue while it ran.
    """
    dispatched: list[int] = []
    monkeypatch.setattr(portal_tasks, "SessionFactory", lambda: _Handle(session))
    monkeypatch.setattr(
        operations_service,
        "dispatch_price_extraction",
        lambda job_run_id: dispatched.append(job_run_id),
    )
    monkeypatch.setattr(portal_handlers, "extract_product_history", Recorder())
    monkeypatch.setattr(notification_tasks, "send_whatsapp", Recorder())

    async def run(job_run_id: int | None = None, price_list: bytes | None = None) -> Any:
        monkeypatch.setattr(portal_service, "PortalClient", FakePortal(price_list=price_list))
        return await extract_price_list(
            SimpleNamespace(request=SimpleNamespace(retries=0), retry=lambda **_: Exception()),
            job_run_id=job_run_id,
        )

    run.dispatched = dispatched  # type: ignore[attr-defined]
    yield run


@pytest.mark.slow
class TestThePriceUpdateLifecycle:
    """From nothing to a decision that the platform remembers."""

    async def test_the_whole_story(
        self,
        owner_client: AsyncClient,
        purchasing_client: AsyncClient,
        sales_client: AsyncClient,
        worker: Callable[..., Any],
    ) -> None:
        """Every step is what the spec says a person does, in the order they do it."""
        # --- Nothing has happened yet -------------------------------------
        empty = await sales_client.get(PRICES)
        assert empty.status_code == 200
        assert empty.json()["total"] == 0

        status = (await sales_client.get(f"{UPDATES}/status")).json()
        assert status["last_success_at"] is None
        assert status["is_stalled"] is False
        # RF-20: the values the platform starts with, before anybody configures.
        assert status["interval_hours"] == 12
        assert status["highlight_threshold_pct"] == "10"

        # --- Marcela asks for the list now (RF-14) ------------------------
        requested = await purchasing_client.post(UPDATES)
        assert requested.status_code == 202
        job_run_id = requested.json()["job_run_id"]

        # A second request while that one runs is told, not started (RF-15).
        assert (await purchasing_client.post(UPDATES)).status_code == 409

        # --- The worker does its job --------------------------------------
        await worker(job_run_id)

        # RF-16: whoever asked finds out how it ended.
        finished = (await purchasing_client.get(f"{UPDATES}/{job_run_id}")).json()
        assert finished["status"] == "SUCCEEDED"
        assert finished["result"]["updated"] == 100

        # --- The prices are there (RF-02, RF-03, RF-04) -------------------
        listing = (await sales_client.get(PRICES)).json()
        assert listing["total"] == 100
        first = next(item for item in listing["items"] if item["code"] == "COR-0001")
        assert first["price"] == "48210.0000"
        assert first["description"] == "Adhesivos - Articulo 1"

        # RF-09: and the screen says when that happened.
        status = (await sales_client.get(f"{UPDATES}/status")).json()
        assert status["last_success_at"] is not None
        assert status["is_stalled"] is False

        # --- The next list brings trouble (RF-06, RF-07) ------------------
        second = await purchasing_client.post(UPDATES)
        assert second.status_code == 202
        await worker(second.json()["job_run_id"], broken_list_bytes())

        # The rest of the prices were updated all the same.
        assert (await sales_client.get(PRICES)).json()["total"] == 100

        # RF-26, RF-27: what was set aside is visible, with its reason.
        queue = (await purchasing_client.get(f"{TRIAGE}/cases")).json()
        assert queue["total"] == 9
        assert all(item["reason"] for item in queue["items"])
        unknown = next(item for item in queue["items"] if item["kind"] == "unknown_product")
        assert unknown["payload"]["product_code"] == UNKNOWN_CODE

        # Sales reaches the screen and none of this is on it. Until 011 the
        # door was shut on Julián, and it had to open — the queue holds his own
        # sales rows now — so what says the queue is Marcela's is no longer the
        # door but what comes back through it.
        his = await sales_client.get(f"{TRIAGE}/cases")
        assert his.status_code == 200
        assert his.json()["total"] == 0
        # And he cannot decide about one either, id in hand.
        refused = await sales_client.post(
            f"{TRIAGE}/cases/{unknown['id']}/resolution",
            json={"decision": {"action": "incorporate"}},
        )
        assert refused.status_code == 403

        # --- Marcela decides (RF-30, RF-32, RF-33) ------------------------
        resolved = await purchasing_client.post(
            f"{TRIAGE}/cases/{unknown['id']}/resolution",
            json={"decision": {"action": "incorporate"}},
        )
        assert resolved.status_code == 200
        assert resolved.json()["resolved_by_user_id"] is not None
        assert (await purchasing_client.get(f"{TRIAGE}/cases")).json()["total"] == 8

        # The product is in the list now.
        after = (await sales_client.get(PRICES, params={"q": UNKNOWN_CODE})).json()
        assert after["total"] == 1

        # --- And the platform remembers why (RF-36) -----------------------
        #
        # Filtered by kind rather than counted: the platform ships with the
        # table of category equivalences the client signed already seeded (008),
        # so the queue is not empty before this story begins. What this asserts
        # is that *this* decision became exactly one rule of its own.
        rules = (await purchasing_client.get(f"{TRIAGE}/rules")).json()
        learned = [rule for rule in rules if rule["kind"] == "unknown_product"]
        assert len(learned) == 1

        # --- Until somebody says otherwise (RF-37) ------------------------
        assert (
            await purchasing_client.delete(f"{TRIAGE}/rules/{learned[0]['id']}")
        ).status_code == 204
        assert (await sales_client.get(PRICES, params={"q": UNKNOWN_CODE})).json()["total"] == 0

        # --- The owner changes the rules of the game (RF-18, RF-19) -------
        saved = await owner_client.put(
            f"{UPDATES}/settings", json={"interval_hours": 6, "highlight_threshold_pct": 20}
        )
        assert saved.status_code == 200
        # Purchasing may ask for updates, but not decide how the platform behaves.
        assert (
            await purchasing_client.put(
                f"{UPDATES}/settings", json={"interval_hours": 1, "highlight_threshold_pct": 1}
            )
        ).status_code == 403

        status = (await sales_client.get(f"{UPDATES}/status")).json()
        assert status["interval_hours"] == 6
        assert status["highlight_threshold_pct"] == "20"
