"""What `operations` does when something happens elsewhere.

It is the module that watches the platform operate, so it listens to how the
work of other modules ended, and to every change a person made by hand. It
never learns who did it or what the datum was: another module reports a fact,
and this is where that becomes a row somebody can read tomorrow morning.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.operations.service import PRICE_UPDATE_TASK, OperationsService
from app.shared.events import (
    JobRunFailed,
    JobRunSucceeded,
    ManualChangeRecorded,
    ProductPricesUpdated,
    events,
)

logger = get_logger(__name__)


@events.subscribe(JobRunSucceeded)
async def close_successful_run(event: JobRunSucceeded, session: AsyncSession) -> None:
    """Record that a run finished well, and notice if it had been interrupted."""
    if event.job_name != PRICE_UPDATE_TASK:
        return
    await OperationsService(session).record_price_update_success(event.job_run_id)


@events.subscribe(JobRunFailed)
async def close_failed_run(event: JobRunFailed, session: AsyncSession) -> None:
    """Record a failed run with its reason (RF-10), and warn once (RF-12, RF-13)."""
    if event.job_name != PRICE_UPDATE_TASK:
        return
    await OperationsService(session).record_price_update_failure(event.job_run_id, event.message)


@events.subscribe(ProductPricesUpdated)
async def record_run_result(event: ProductPricesUpdated, session: AsyncSession) -> None:
    """Keep what the run did, so `GET /price-updates/{id}` can report it (RF-27)."""
    if event.job_run_id is None:
        return
    await OperationsService(session).record_price_update_result(
        event.job_run_id,
        {
            "batch_id": event.batch_id,
            "updated": event.updated,
            "unchanged": event.unchanged,
            "highlighted": event.highlighted,
            "quarantined": event.quarantined,
        },
    )


@events.subscribe(ManualChangeRecorded)
async def write_the_log(event: ManualChangeRecorded, session: AsyncSession) -> None:
    """Turn a manual change made anywhere into a line of the log (RF-09, RF-10, RF-12).

    Nothing is caught here, deliberately. This runs in the transaction of
    whoever made the change, so a log line that cannot be written takes the
    change down with it (`GEN-09`). That is the behaviour the feature promises:
    the alternative is a corrected value nobody can explain, which is the one
    outcome Artículo II rules out.
    """
    await OperationsService(session).record_manual_change(event)
