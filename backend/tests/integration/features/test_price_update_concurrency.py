"""RF-15 with two connections, because in one it is not the same question.

Everywhere else the suite runs each test inside a transaction that is rolled
back, and two "concurrent" callers sharing one session are just two calls in a
row: they see each other's uncommitted rows, and the race the advisory lock
exists to lose never happens.

So this file opens **its own connections**, commits for real, and cleans up
after itself. It is the only place in the suite that does, and that is why it is
marked slow.

What is under test is not "two requests come back different". It is that the
decision to start an update is serialised by the database: `pg_try_advisory_xact_lock`
is taken before looking for a running run, so the check and the insert cannot
interleave — which is exactly what a `SELECT ... WHERE status = RUNNING`
followed by an `INSERT` would allow.
"""

import asyncio
from collections.abc import AsyncIterator, Callable

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.modules.operations.models import JobRun, JobStatus
from app.modules.operations.service import (
    PRICE_UPDATE_LOCK_KEY,
    PRICE_UPDATE_TASK,
    OperationsService,
)
from app.shared.errors import ConflictError

pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.slow]


class Dispatched:
    """Stands in for handing the extraction to the worker."""

    def __init__(self) -> None:
        self.job_run_ids: list[int] = []

    def __call__(self, job_run_id: int) -> None:
        self.job_run_ids.append(job_run_id)


@pytest.fixture
async def open_session() -> AsyncIterator[Callable[[], AsyncSession]]:
    """Independent sessions that really commit, and a cleanup that really deletes.

    Every run this test opens is committed, so it would outlive the test and be
    seen by the next one. The fixture remembers where the table was and removes
    exactly what the test added.
    """
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    opened: list[AsyncSession] = []

    async with factory() as bookkeeping:
        result = await bookkeeping.execute(select(func.coalesce(func.max(JobRun.id), 0)))
        watermark = int(result.scalar_one())

    def _open() -> AsyncSession:
        session = factory()
        opened.append(session)
        return session

    try:
        yield _open
    finally:
        for session in opened:
            await session.rollback()
            await session.close()
        async with factory() as cleanup:
            await cleanup.execute(delete(JobRun).where(JobRun.id > watermark))
            await cleanup.commit()
        await engine.dispose()


async def running_runs(session: AsyncSession) -> int:
    """How many price updates the database believes are in flight."""
    result = await session.execute(
        select(func.count())
        .select_from(JobRun)
        .where(JobRun.task_name == PRICE_UPDATE_TASK, JobRun.status == JobStatus.RUNNING)
    )
    return int(result.scalar_one())


class TestTwoRequestsAtTheSameTime:
    """One update at a time, whoever asks and whenever they ask (RF-15)."""

    async def test_only_one_of_two_simultaneous_requests_starts_an_update(
        self, open_session: Callable[[], AsyncSession]
    ) -> None:
        """Both callers fire together; one gets a run, the other gets told."""
        # Arrange
        first, second = open_session(), open_session()
        dispatch = Dispatched()

        # Act
        outcomes = await asyncio.gather(
            OperationsService(first).request_price_update(dispatch=dispatch),
            OperationsService(second).request_price_update(dispatch=dispatch),
            return_exceptions=True,
        )

        # Assert
        started = [outcome for outcome in outcomes if not isinstance(outcome, BaseException)]
        refused = [outcome for outcome in outcomes if isinstance(outcome, ConflictError)]
        assert len(started) == 1, f"Both requests started an update: {outcomes}"
        assert len(refused) == 1, f"Nobody was told there was one running: {outcomes}"

    async def test_the_worker_is_handed_exactly_one_extraction(
        self, open_session: Callable[[], AsyncSession]
    ) -> None:
        """The point of RF-15 is the portal, not the row: one knock on the door."""
        # Arrange
        first, second = open_session(), open_session()
        dispatch = Dispatched()

        # Act
        await asyncio.gather(
            OperationsService(first).request_price_update(dispatch=dispatch),
            OperationsService(second).request_price_update(dispatch=dispatch),
            return_exceptions=True,
        )

        # Assert
        assert len(dispatch.job_run_ids) == 1

    async def test_the_database_is_left_with_one_run_in_flight(
        self, open_session: Callable[[], AsyncSession]
    ) -> None:
        """Two rows in `RUNNING` would make every later check ambiguous."""
        # Arrange
        first, second = open_session(), open_session()

        # Act
        await asyncio.gather(
            OperationsService(first).request_price_update(dispatch=Dispatched()),
            OperationsService(second).request_price_update(dispatch=Dispatched()),
            return_exceptions=True,
        )

        # Assert
        assert await running_runs(open_session()) == 1


class TestTheLockItself:
    """The mechanism, pinned deterministically rather than by racing."""

    async def test_a_caller_is_refused_while_another_holds_the_lock(
        self, open_session: Callable[[], AsyncSession]
    ) -> None:
        """The first caller has not committed yet, so its run is invisible.

        This is the exact window a `SELECT ... WHERE status = RUNNING` would
        walk straight through: there is no row to find. The lock is what makes
        the second caller wait for an answer it can trust.
        """
        # Arrange: hold the lock in an open transaction, like a request in flight.
        holder = open_session()
        held = await OperationsService(holder).runs.try_lock(PRICE_UPDATE_LOCK_KEY)
        assert held is True
        assert await running_runs(open_session()) == 0

        # Act
        with pytest.raises(ConflictError) as refused:
            await OperationsService(open_session()).request_price_update(dispatch=Dispatched())

        # Assert
        assert "already running" in refused.value.message.lower()

    async def test_once_the_lock_is_released_the_next_caller_gets_through(
        self, open_session: Callable[[], AsyncSession]
    ) -> None:
        """A lock that is never released would turn RF-15 into "no updates ever"."""
        # Arrange
        holder = open_session()
        await OperationsService(holder).runs.try_lock(PRICE_UPDATE_LOCK_KEY)

        # Act: the holder's transaction ends, and the lock ends with it.
        await holder.rollback()
        requested = await OperationsService(open_session()).request_price_update(
            dispatch=Dispatched()
        )

        # Assert
        assert requested.status is JobStatus.RUNNING

    async def test_a_request_that_arrives_after_the_first_one_committed_is_told_which_run(
        self, open_session: Callable[[], AsyncSession]
    ) -> None:
        """Then the row *is* visible, and the answer carries its id so the screen can follow it."""
        # Arrange
        first = await OperationsService(open_session()).request_price_update(dispatch=Dispatched())

        # Act
        with pytest.raises(ConflictError) as refused:
            await OperationsService(open_session()).request_price_update(dispatch=Dispatched())

        # Assert
        assert refused.value.details["job_run_id"] == first.job_run_id
