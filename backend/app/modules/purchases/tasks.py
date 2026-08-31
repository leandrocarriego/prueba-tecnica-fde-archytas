"""The scheduled work of purchases: what falls due, and what fell due already.

Both of these are about the **receipt** and not about the money: an invoice
about to fall due with no receipt is announced, and one that already fell due
without one becomes an incident. An invoice that has its receipt is neither.
"""

from datetime import timedelta
from typing import Any

from app.database import SessionFactory
from app.logging import get_logger
from app.modules.purchases.service import PurchasesService
from app.shared.events import InvoiceDueSoon, events
from app.worker.bridge import async_task
from app.worker.celery_app import celery_app

logger = get_logger(__name__)

# Once a day is enough for both: a due date moves in days, not in minutes, and
# waking up more often would only mean announcing the same invoice again.
TICK_HOURS = 24


@celery_app.task(name="purchases.watch_due_dates")
@async_task
async def watch_due_dates() -> dict[str, Any]:
    """Announce what is about to fall due and open what already did.

    **Announced once per due date** (RF-39 of 005): the announcement is
    published as a fact and it is `notifications` that decides whether it has
    already told somebody, exactly as it does for the interrupted price update.
    An invoice that has its receipt is never announced at all (RF-40).
    """
    announced = 0
    async with SessionFactory() as session:
        service = PurchasesService(session)
        suppliers = {
            supplier.id: supplier.legal_name for supplier in await service.purchases.suppliers()
        }
        for invoice, days_ahead in await service.invoices_due_soon():
            if invoice.due_on is None:  # pragma: no cover - filtered by the query
                continue
            await events.publish(
                InvoiceDueSoon(
                    invoice_id=invoice.id,
                    number=invoice.number,
                    supplier_name=suppliers.get(invoice.supplier_id or 0, invoice.supplier_text),
                    due_on=invoice.due_on,
                    days_ahead=days_ahead,
                    total=invoice.total,
                ),
                session,
            )
            announced += 1
        await session.commit()
        opened = await service.open_incidents_for_overdue()

    logger.info("Due dates watched", extra={"announced": announced, "incidents": opened})
    return {"announced": announced, "incidents": opened}


celery_app.conf.beat_schedule["purchases-due-dates"] = {
    "task": "purchases.watch_due_dates",
    "schedule": timedelta(hours=TICK_HOURS),
}
