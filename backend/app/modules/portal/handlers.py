"""What `portal` does when something happens elsewhere.

Two subscriptions, and the same shape: something was registered for the first
time, so the document the portal already publishes about it has to be brought
in — the price history of a product (RF-38 of 001), the file of an invoice
(RF-02 of 004).

Both handlers **queue and return**. They run inside the transaction of whoever
published, and a hundred visits to a third party's system cannot be held open
inside a transaction that is registering rows (`GEN-09`).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.logging import get_logger
from app.modules.portal.tasks import extract_invoice_file, extract_product_history
from app.shared.events import InvoicesRegistered, ProductsRegistered, events

logger = get_logger(__name__)


@events.subscribe(ProductsRegistered)
async def bring_published_history(event: ProductsRegistered, _session: AsyncSession) -> None:
    """Queue one history visit per product, spaced out, never in a burst."""
    for position, product in enumerate(event.products):
        extract_product_history.apply_async(
            kwargs={"product_code": product.product_code},
            countdown=position * settings.PORTAL_HISTORY_SPACING_SECONDS,
        )

    logger.info(
        "Published history queued",
        extra={"products": len(event.products), "batch_id": event.batch_id},
    )


@events.subscribe(InvoicesRegistered)
async def bring_invoice_files(event: InvoicesRegistered, _session: AsyncSession) -> None:
    """Queue one download per invoice, spaced out, never in a burst (RF-02, RF-25).

    A hundred invoices land on the first day and each one is a visit to
    somebody else's system with a shared account. They go out at the same pace
    the price histories do, and the invoices list is usable from the first
    moment: the document is evidence for the review, not a condition for the
    invoice to exist.
    """
    for position, invoice in enumerate(event.invoices):
        extract_invoice_file.apply_async(
            kwargs={"invoice_number": invoice.number},
            countdown=position * settings.PORTAL_HISTORY_SPACING_SECONDS,
        )

    logger.info("Invoice files queued", extra={"invoices": len(event.invoices)})
