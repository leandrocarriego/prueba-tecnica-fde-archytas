"""The Celery tasks of the price update, without a worker in the way.

Each task is tested through its **async body**, which is what
`agents/skills/add_celery_task.md` prescribes: the bridge in `app/worker/` runs
that body on the worker's own event loop, and borrowing that loop here would
hand the test's asyncpg connections to a loop they were not opened on.

Two things are pinned for every task, because they are what a task is for:

* **Idempotency** (`PY-07`, `TEST-04`). Running it twice does what running it
  once did. For the extraction that is the content hash of `raw`, and the point
  is that it does not depend on anybody remembering to check.
* **The run is closed either way.** `operations` owns `JobRun` and the task
  cannot call it, so the outcome travels as an event. A run left `RUNNING`
  forever would make the prices screen lie (RF-09) and the interruption
  detection blind (RF-11).
"""

from collections.abc import Callable
from types import SimpleNamespace, TracebackType
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Product
from app.modules.operations import service as operations_service
from app.modules.operations import tasks as operations_tasks
from app.modules.operations.models import JobRun, JobStatus
from app.modules.operations.service import PRICE_UPDATE_TASK, OperationsService
from app.modules.portal import service as portal_service
from app.modules.portal import tasks as portal_tasks
from app.modules.portal.models import PortalDocument
from app.shared.errors import ExtractionError
from tests.factories.portal_factory import FakePortal

pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.portal]

# The bodies under test, reached past the bridge that would otherwise run them
# on the worker's loop.
extract_price_list = portal_tasks.extract_price_list.run.__wrapped__
extract_product_history = portal_tasks.extract_product_history.run.__wrapped__
tick_price_update = operations_tasks.tick_price_update.run.__wrapped__

UNREADABLE = ExtractionError("The portal could not be read", details={"section": "prices"})


class Retried(Exception):
    """Raised by the stub instead of Celery's own `Retry`."""


def celery_self(*, retries: int = 0) -> Any:
    """A stand-in for the bound task.

    It carries the two things the body actually reads: how many attempts have
    already gone by, and a `retry()` to call when it is worth another one.
    """

    def retry(*_args: object, **_kwargs: object) -> Retried:
        return Retried()

    return SimpleNamespace(request=SimpleNamespace(retries=retries), retry=retry)


class _Handle:
    """An async context manager that lends the test's session and never closes it."""

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
def on_the_test_session(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> Callable[[], _Handle]:
    """Make the tasks open the session this test will roll back.

    A task opens its own session with `SessionFactory` — that is right in
    production and wrong here, where it would commit outside the transaction
    that keeps the suite isolated.
    """

    def factory() -> _Handle:
        return _Handle(session)

    monkeypatch.setattr(portal_tasks, "SessionFactory", factory)
    monkeypatch.setattr(operations_tasks, "SessionFactory", factory)
    return factory


@pytest.fixture
def a_portal(monkeypatch: pytest.MonkeyPatch) -> Callable[..., FakePortal]:
    """Let a test decide what the portal answers, for the whole task."""

    def install(**kwargs: Any) -> FakePortal:
        portal = FakePortal(**kwargs)
        monkeypatch.setattr(portal_service, "PortalClient", portal)
        return portal

    return install


async def open_run(session: AsyncSession) -> JobRun:
    """A run in flight, the way `POST /price-updates` leaves one."""
    service = OperationsService(session)
    requested = await service.request_price_update(dispatch=lambda _id: None)
    run = await service.runs.get(requested.job_run_id)
    assert run is not None
    return run


async def count(session: AsyncSession, model: type) -> int:
    """How many rows of something there are right now."""
    result = await session.execute(select(func.count()).select_from(model))
    return int(result.scalar_one())


@pytest.mark.usefixtures("on_the_test_session")
class TestExtractingThePriceList:
    """`portal.extract_price_list`, the task the whole feature hangs from."""

    async def test_it_brings_the_list_and_the_catalog_ends_up_loaded(
        self, session: AsyncSession, a_portal: Callable[..., FakePortal]
    ) -> None:
        """One run, and the pipeline behind it, from `raw` to `core`."""
        # Arrange
        a_portal()

        # Act
        result = await extract_price_list(celery_self())

        # Assert
        assert result["reprocessed"] is True
        assert await count(session, PortalDocument) == 1
        assert await count(session, Product) == 100

    async def test_running_it_twice_stores_one_document(
        self, session: AsyncSession, a_portal: Callable[..., FakePortal]
    ) -> None:
        """`TEST-04`: the second run finds the same bytes and reprocesses nothing.

        The unique index on `content_hash` is the mechanism; this is the proof
        that the task actually leans on it.
        """
        # Arrange
        a_portal()

        # Act
        first = await extract_price_list(celery_self())
        second = await extract_price_list(celery_self())

        # Assert
        assert first["reprocessed"] is True
        assert second["reprocessed"] is False
        assert await count(session, PortalDocument) == 1
        assert await count(session, Product) == 100

    async def test_a_successful_run_is_closed_as_succeeded(
        self, session: AsyncSession, a_portal: Callable[..., FakePortal]
    ) -> None:
        """RF-16: whoever asked for it finds out that it worked."""
        # Arrange
        a_portal()
        run = await open_run(session)

        # Act
        await extract_price_list(celery_self(), job_run_id=run.id)

        # Assert
        closed = await OperationsService(session).get_run(run.id)
        assert closed.status is JobStatus.SUCCEEDED
        assert closed.finished_at is not None

    async def test_a_run_that_brought_nothing_new_is_closed_too(
        self, session: AsyncSession, a_portal: Callable[..., FakePortal]
    ) -> None:
        """The portal published the same file: nothing to reprocess, still a finished run.

        This is the path that would leave a run `RUNNING` forever if the task
        only reported success when it had something to hand downstream.
        """
        # Arrange
        a_portal()
        await extract_price_list(celery_self())
        run = await open_run(session)

        # Act
        result = await extract_price_list(celery_self(), job_run_id=run.id)

        # Assert
        assert result["reprocessed"] is False
        closed = await OperationsService(session).get_run(run.id)
        assert closed.status is JobStatus.SUCCEEDED

    async def test_a_failure_is_retried_before_it_is_reported(
        self, session: AsyncSession, a_portal: Callable[..., FakePortal]
    ) -> None:
        """The portal account is shared and its session drops: most failures are timing."""
        # Arrange
        a_portal(fails_with=UNREADABLE)
        run = await open_run(session)

        # Act / Assert
        with pytest.raises(Retried):
            await extract_price_list(celery_self(retries=0), job_run_id=run.id)

        # …and the run is not written off while there are attempts left.
        still_open = await OperationsService(session).get_run(run.id)
        assert still_open.status is JobStatus.RUNNING

    async def test_once_the_retries_run_out_the_failure_is_recorded_with_its_reason(
        self, session: AsyncSession, a_portal: Callable[..., FakePortal]
    ) -> None:
        """RF-10: tomorrow morning the reason has to be next to the run."""
        # Arrange
        a_portal(fails_with=UNREADABLE)
        run = await open_run(session)

        # Act
        with pytest.raises(ExtractionError):
            await extract_price_list(
                celery_self(retries=portal_tasks.MAX_RETRIES), job_run_id=run.id
            )

        # Assert
        failed = await OperationsService(session).get_run(run.id)
        assert failed.status is JobStatus.FAILED
        assert failed.error == UNREADABLE.message

    async def test_the_reason_never_carries_a_credential(
        self, session: AsyncSession, a_portal: Callable[..., FakePortal]
    ) -> None:
        """Artículo VII: the portal account is a third party's, and it stays in the environment."""
        # Arrange
        a_portal(fails_with=UNREADABLE)
        run = await open_run(session)

        # Act
        with pytest.raises(ExtractionError):
            await extract_price_list(
                celery_self(retries=portal_tasks.MAX_RETRIES), job_run_id=run.id
            )

        # Assert
        failed = await OperationsService(session).get_run(run.id)
        assert failed.error is not None
        assert "clave" not in failed.error.lower()
        assert "password" not in failed.error.lower()

    async def test_a_scheduled_run_without_an_id_still_works(
        self, session: AsyncSession, a_portal: Callable[..., FakePortal]
    ) -> None:
        """Nothing in the extraction depends on somebody having asked for it."""
        # Arrange
        a_portal()

        # Act
        result = await extract_price_list(celery_self(), job_run_id=None)

        # Assert
        assert result["reprocessed"] is True


@pytest.mark.usefixtures("on_the_test_session")
class TestExtractingAProductHistory:
    """`portal.extract_product_history`, one visit per product, once."""

    async def test_it_stores_the_screen_and_the_points_land(
        self, session: AsyncSession, a_portal: Callable[..., FakePortal]
    ) -> None:
        """RF-38: the history the portal already publishes becomes the product's."""
        # Arrange
        portal = a_portal()
        await extract_price_list(celery_self())

        # Act
        result = await extract_product_history(celery_self(), product_code="COR-0001")

        # Assert
        assert result["product_code"] == "COR-0001"
        assert portal.history_visits == ["COR-0001"]
        assert await count(session, PortalDocument) == 2

    async def test_visiting_the_same_history_twice_stores_one_document(
        self, session: AsyncSession, a_portal: Callable[..., FakePortal]
    ) -> None:
        """`TEST-04` again: resuming after a crash must not repeat the work."""
        # Arrange
        a_portal()
        await extract_price_list(celery_self())

        # Act
        await extract_product_history(celery_self(), product_code="COR-0001")
        await extract_product_history(celery_self(), product_code="COR-0001")

        # Assert
        assert await count(session, PortalDocument) == 2

    async def test_a_history_that_cannot_be_read_is_retried_and_then_given_up(
        self, session: AsyncSession, a_portal: Callable[..., FakePortal]
    ) -> None:
        """RF-39: and the price of the product is not touched on the way out."""
        # Arrange
        portal = a_portal()
        await extract_price_list(celery_self())
        before = await count(session, Product)
        portal.fails_with = UNREADABLE

        # Act / Assert
        with pytest.raises(Retried):
            await extract_product_history(celery_self(), product_code="COR-0001")
        with pytest.raises(ExtractionError):
            await extract_product_history(
                celery_self(retries=portal_tasks.MAX_RETRIES), product_code="COR-0001"
            )

        assert await count(session, Product) == before


@pytest.mark.usefixtures("on_the_test_session")
class TestTheScheduledHeartbeat:
    """`operations.tick_price_update`, which is how RF-01 and RF-21 hold together."""

    @pytest.fixture(autouse=True)
    def no_dispatch(self, monkeypatch: pytest.MonkeyPatch) -> list[int]:
        """The extraction is handed over by name; here it is only recorded."""
        handed: list[int] = []
        monkeypatch.setattr(
            operations_service,
            "dispatch_price_extraction",
            lambda job_run_id: handed.append(job_run_id),
        )
        return handed

    async def test_a_fresh_installation_asks_for_the_list(self, no_dispatch: list[int]) -> None:
        """RF-01: nobody has to press anything for the first list to arrive."""
        # Act
        result = await tick_price_update()

        # Assert
        assert result["requested"] is True
        assert len(no_dispatch) == 1

    async def test_it_does_not_ask_again_before_the_interval_has_gone_by(
        self, session: AsyncSession, no_dispatch: list[int]
    ) -> None:
        """RF-21: the frequency is a business parameter, not a redeploy."""
        # Arrange
        await tick_price_update()
        run = await OperationsService(session).runs.running(PRICE_UPDATE_TASK)
        assert run is not None
        await OperationsService(session).record_price_update_success(run.id)

        # Act
        result = await tick_price_update()

        # Assert
        assert result["requested"] is False
        assert len(no_dispatch) == 1

    async def test_it_gives_way_to_an_update_already_running(
        self, session: AsyncSession, no_dispatch: list[int]
    ) -> None:
        """RF-15 applies to the scheduler too: one update at a time."""
        # Arrange
        await open_run(session)

        # Act
        result = await tick_price_update()

        # Assert
        assert result["requested"] is False
        assert no_dispatch == []
