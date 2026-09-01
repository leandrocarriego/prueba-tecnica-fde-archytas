"""Background extraction of SIGProv.

One task per section of the portal, every one of them idempotent by the content
hash of what it brings back, and every one reporting the outcome of its run as a
domain event: `operations` owns `JobRun` and this module cannot call it
(Artículo IV), so the run is closed by whoever is listening to
`JobRunSucceeded` and `JobRunFailed`.

Two of them are not scheduled and have no run of their own — the history of a
product and the document of an invoice. They are consequences of something
being registered rather than work somebody asked for, so a failure is logged
and costs the row nothing.
"""

from typing import Any

from celery import Task

from app.database import SessionFactory
from app.logging import get_logger
from app.modules.portal.service import PortalService
from app.shared.errors import ExtractionError, PortalShapeError
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


# --- The sections of 004, 007 and 009 ------------------------------------
#
# Five tasks with the same body: read one section, close the run either way.
# `_run_section` is that body, so adding a section is a name and a method and
# never a sixth copy of the retry-and-report dance.

INVOICES_TASK = "extract_invoices"
SUPPLIER_LEDGER_TASK = "extract_supplier_ledger"
PURCHASE_ORDERS_TASK = "extract_purchase_orders"
MESSAGES_TASK = "extract_messages"
SALES_TASK = "extract_sales"
INVOICE_FILE_TASK = "extract_invoice_file"


async def _run_section(
    task: Task, method: str, task_name: str, job_run_id: int | None
) -> dict[str, Any]:
    """Read one section of the portal and report how the run ended.

    Retries are few and spaced for the same reason as the price list: the
    portal account is shared with the client's own staff and its session drops,
    so a failed extraction is very often just bad timing. The failure is only
    recorded once the retries run out.
    """
    logger.info("Section extraction started", extra={"section": task_name})
    try:
        async with SessionFactory() as session:
            service = PortalService(session)
            document_id = await getattr(service, method)(job_run_id=job_run_id)
    except PortalShapeError as error:
        # The page does not have the columns this platform reads. That is not
        # bad timing and it will not be different in five minutes, so it is
        # recorded now with the reason. Retrying it kept the run `RUNNING` for
        # the length of the retries — which is what the owner saw as a «Traer
        # ahora» that stayed disabled — and, when the worker was replaced by a
        # deploy in between, the retry chain was lost and the run was swept away
        # with «its worker never came back»: a sentence that names the symptom
        # and buries the cause.
        await _report_failure(job_run_id, task_name, error.message)
        raise
    except ExtractionError as error:
        attempts = int(getattr(task.request, "retries", 0) or 0)
        if attempts < MAX_RETRIES:
            logger.warning(
                "Section extraction failed, retrying",
                extra={"section": task_name, "attempt": attempts + 1},
            )
            raise task.retry(exc=error, countdown=RETRY_COUNTDOWN_SECONDS) from error
        await _report_failure(job_run_id, task_name, error.message)
        raise
    except Exception as error:
        # Anything that is not the portal refusing: a parser that broke, a
        # column the migration never created, a bug. It is not retried —
        # retrying a defect just repeats it — but it **is** recorded, because a
        # run that dies without saying so stays `RUNNING` for ever, and
        # `request_sync` skips a section that has one of those open. Five
        # sections of this platform were wedged that way for twelve hours,
        # silently, which is exactly what the Artículo II forbids.
        await _report_failure(job_run_id, task_name, f"{type(error).__name__}: {error}")
        raise

    await _report_success(job_run_id, task_name)
    return {"raw_document_id": document_id, "reprocessed": document_id is not None}


@celery_app.task(name="portal.extract_invoices", bind=True, max_retries=MAX_RETRIES)
@async_task
async def extract_invoices(self: Task, job_run_id: int | None = None) -> dict[str, Any]:
    """Read the invoices screen and hand it to the pipeline (RF-01 of 004)."""
    return await _run_section(self, "extract_invoices", INVOICES_TASK, job_run_id)


@celery_app.task(name="portal.extract_supplier_ledger", bind=True, max_retries=MAX_RETRIES)
@async_task
async def extract_supplier_ledger(self: Task, job_run_id: int | None = None) -> dict[str, Any]:
    """Read the supplier register, expanding each row (RF-08 of 004)."""
    return await _run_section(self, "extract_supplier_ledger", SUPPLIER_LEDGER_TASK, job_run_id)


@celery_app.task(name="portal.extract_purchase_orders", bind=True, max_retries=MAX_RETRIES)
@async_task
async def extract_purchase_orders(self: Task, job_run_id: int | None = None) -> dict[str, Any]:
    """Read the purchase orders screen (RF-01 of 007)."""
    return await _run_section(self, "extract_purchase_orders", PURCHASE_ORDERS_TASK, job_run_id)


@celery_app.task(name="portal.extract_messages", bind=True, max_retries=MAX_RETRIES)
@async_task
async def extract_messages(self: Task, job_run_id: int | None = None) -> dict[str, Any]:
    """Read the inbox of the portal (RF-21 of 007)."""
    return await _run_section(self, "extract_messages", MESSAGES_TASK, job_run_id)


@celery_app.task(name="portal.extract_sales", bind=True, max_retries=MAX_RETRIES)
@async_task
async def extract_sales(self: Task, job_run_id: int | None = None) -> dict[str, Any]:
    """Read the sales screen (RF-01 of 009)."""
    return await _run_section(self, "extract_sales", SALES_TASK, job_run_id)


@celery_app.task(name="portal.extract_invoice_file", bind=True, max_retries=MAX_RETRIES)
@async_task
async def extract_invoice_file(
    self: Task, invoice_number: str, file_kind: str = ""
) -> dict[str, Any]:
    """Download the document of one invoice (RF-02, RF-25 of 004).

    Queued once per invoice, the first time it is registered, and spaced out by
    the handler that queues them: a hundred invoices on day one are a hundred
    visits to somebody else's system.

    No `JobRun` of its own: this is a consequence of an invoice being
    registered, not a run somebody asked for. A failure is logged and the
    invoice stays registered without its document — losing the file must not
    cost it that, and the review shows it as a document that could not be read.
    """
    logger.info("Invoice file extraction started", extra={"invoice_number": invoice_number})
    try:
        async with SessionFactory() as session:
            document_id = await PortalService(session).extract_invoice_file(
                invoice_number, file_kind=file_kind
            )
    except ExtractionError as error:
        attempts = int(getattr(self.request, "retries", 0) or 0)
        if attempts < MAX_RETRIES:
            raise self.retry(exc=error, countdown=RETRY_COUNTDOWN_SECONDS) from error
        logger.error(
            "Invoice file could not be downloaded",
            extra={"invoice_number": invoice_number, "reason": error.message},
        )
        raise

    return {"raw_document_id": document_id, "invoice_number": invoice_number}
