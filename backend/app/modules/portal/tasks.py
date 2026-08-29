"""Background extraction of SIGProv.

Two tasks, both idempotent by the content hash of what they bring back, and
both reporting the outcome of their run as a domain event: `operations` owns
`JobRun` and this module cannot call it (Artículo IV), so the run is closed by
whoever is listening to `JobRunSucceeded` and `JobRunFailed`.
"""

from typing import Any

from celery import Task

from app.database import SessionFactory
from app.logging import get_logger
from app.modules.portal.service import PortalService
from app.shared.errors import ExtractionError
from app.shared.events import JobRunFailed, JobRunSucceeded, events
from app.worker.bridge import async_task
from app.worker.celery_app import celery_app

logger = get_logger(__name__)

PRICE_LIST_TASK = "extract_price_list"
PRODUCT_HISTORY_TASK = "extract_product_history"

# The portal account is shared with the client's own staff and its session drops
# after eight hours of inactivity, so a failed extraction is very often just bad
# timing. Retries are few and spaced; the failure is only recorded once they run
# out, which is what keeps RF-10 from filling the history with the same run.
MAX_RETRIES = 2
RETRY_COUNTDOWN_SECONDS = 300


async def _report_failure(job_run_id: int | None, task_name: str, message: str) -> None:
    """Tell `operations` that the run failed, on a session of its own.

    The session that was doing the work is rolled back by then, so the failure
    is reported on a fresh one: a run that fails still has to leave a trace, and
    a trace inside an aborted transaction is no trace at all (RF-10).
    """
    if job_run_id is None:
        return
    async with SessionFactory() as session:
        await events.publish(
            JobRunFailed(job_run_id=job_run_id, job_name=task_name, message=message), session
        )
        await session.commit()


async def _report_success(job_run_id: int | None, task_name: str) -> None:
    """Close the run as successful. Also the path a duplicate file takes."""
    if job_run_id is None:
        return
    async with SessionFactory() as session:
        await events.publish(JobRunSucceeded(job_run_id=job_run_id, job_name=task_name), session)
        await session.commit()


@celery_app.task(name="portal.extract_price_list", bind=True, max_retries=MAX_RETRIES)
@async_task
async def extract_price_list(self: Task, job_run_id: int | None = None) -> dict[str, Any]:
    """Bring the price list of the day and hand it to the pipeline.

    Everything downstream — normalising, quarantining, updating the prices —
    happens in the handlers of the event this publishes, inside this task's
    transaction. So one run either lands whole or does not land at all.
    """
    logger.info("Price list extraction started", extra={"job_run_id": job_run_id})
    try:
        async with SessionFactory() as session:
            document_id = await PortalService(session).extract_price_list(job_run_id=job_run_id)
    except ExtractionError as error:
        attempts = int(getattr(self.request, "retries", 0) or 0)
        if attempts < MAX_RETRIES:
            logger.warning(
                "Price list extraction failed, retrying",
                extra={"job_run_id": job_run_id, "attempt": attempts + 1},
            )
            raise self.retry(exc=error, countdown=RETRY_COUNTDOWN_SECONDS) from error
        await _report_failure(job_run_id, PRICE_LIST_TASK, error.message)
        raise

    await _report_success(job_run_id, PRICE_LIST_TASK)
    return {"raw_document_id": document_id, "reprocessed": document_id is not None}


@celery_app.task(name="portal.extract_product_history", bind=True, max_retries=MAX_RETRIES)
@async_task
async def extract_product_history(self: Task, product_code: str) -> dict[str, Any]:
    """Read the history the portal already publishes for one product (RF-38).

    Queued once per product, the first time the catalog gets to know it, and
    spaced out by the handler that queues them: a hundred products on day one
    are a hundred visits to somebody else's system.
    """
    logger.info("Product history extraction started", extra={"product_code": product_code})
    try:
        async with SessionFactory() as session:
            document_id = await PortalService(session).extract_product_history(product_code)
    except ExtractionError as error:
        attempts = int(getattr(self.request, "retries", 0) or 0)
        if attempts < MAX_RETRIES:
            raise self.retry(exc=error, countdown=RETRY_COUNTDOWN_SECONDS) from error
        # No `JobRun` of its own: this task is a consequence of a product being
        # registered, not a run somebody asked for. The failure is logged and
        # the product keeps its current price — losing its published history
        # must not cost it that (RF-39).
        logger.error(
            "Product history could not be read",
            extra={"product_code": product_code, "reason": error.message},
        )
        raise

    return {"raw_document_id": document_id, "product_code": product_code}
