"""What `sales` does when something happens elsewhere.

Three subscriptions, and two of them are projections: the product codes the
catalog knows, and the parameter that says when an amount is out of line. Both
arrive as events, so this module answers "does that product exist" without ever
importing the module that owns the answer (Artículo IV).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.sales.service import BROKEN_SALE, OUTLIER_KEY, REPEATED_SALE, SalesService
from app.shared.events import (
    BusinessParameterChanged,
    PendingWorkReported,
    PendingWorkRequested,
    ProductsRegistered,
    SalesNormalized,
    events,
)

logger = get_logger(__name__)


@events.subscribe(SalesNormalized)
async def register_sales(event: SalesNormalized, session: AsyncSession) -> None:
    """Bring the sales records of a batch in, counting only what may be counted."""
    await SalesService(session).register_sales(batch_id=event.batch_id, sales=event.sales)


@events.subscribe(ProductsRegistered)
async def remember_products(event: ProductsRegistered, session: AsyncSession) -> None:
    """Keep the product codes this module checks a sale against (RF-20 of 009)."""
    service = SalesService(session)
    for product in event.products:
        await service.remember_product(product.product_code)


@events.subscribe(BusinessParameterChanged)
async def remember_parameter(event: BusinessParameterChanged, session: AsyncSession) -> None:
    """Keep the threshold that says when an amount is out of line (RF-22 of 009)."""
    if event.key != OUTLIER_KEY:
        return
    await SalesService(session).remember_setting(event.key, event.value)


@events.subscribe(PendingWorkRequested)
async def report_pending_sales(event: PendingWorkRequested, session: AsyncSession) -> None:
    """Contestar qué ventas siguen esperando una decisión.

    Se contesta **siempre**, también cuando no hay ninguna: una lista vacía no
    es silencio, es la frase «de esto ya no queda nada», y es lo que cierra los
    casos de ventas que quedaron abiertos después de que alguien las resolviera.
    Callarse cuando no hay nada dejaría esos casos colgados para siempre.
    """
    await events.publish(
        PendingWorkReported(
            kinds=(REPEATED_SALE, BROKEN_SALE),
            items=await SalesService(session).pending_work(),
        ),
        session,
    )
    del event
