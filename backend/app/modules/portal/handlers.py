"""What `portal` does when something happens elsewhere.

One subscription: the catalog got to know a product for the first time, so the
history that the portal already publishes for it has to be brought in (RF-38).

The handler **queues and returns**. It runs inside the transaction of whoever
published, and a hundred visits to a third party's system cannot be held open
inside a transaction that is registering products (`GEN-09`).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.logging import get_logger
from app.modules.portal.tasks import extract_product_history
from app.shared.events import ProductsRegistered, events

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
