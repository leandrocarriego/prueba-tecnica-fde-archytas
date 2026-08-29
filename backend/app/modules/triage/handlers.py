"""What `triage` does when something happens elsewhere.

Four subscriptions, one per way this feature can fail to resolve something on
its own. None of them knows which module published: a case is a case, whether
it came from an unreadable row or from a product nobody has ever heard of.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.triage.service import (
    MISSING_PRODUCT,
    MISSING_PRODUCT_REASON,
    UNKNOWN_PRODUCT,
    UNKNOWN_PRODUCT_REASON,
    UNREADABLE_HISTORY,
    UNREADABLE_ROW,
    TriageService,
)
from app.shared.events import (
    KnownProductsMissing,
    PriceHistoryRowsQuarantined,
    PriceRowsQuarantined,
    UnknownProductsObserved,
    events,
)

logger = get_logger(__name__)


@events.subscribe(PriceRowsQuarantined)
async def open_unreadable_rows(event: PriceRowsQuarantined, session: AsyncSession) -> None:
    """A row of the list could not be interpreted (RF-06)."""
    service = TriageService(session)
    for case in event.cases:
        await service.open_case(
            kind=UNREADABLE_ROW,
            reason=case.reason,
            payload={
                "staging_row_id": case.staging_row_id,
                "product_code": case.product_code,
                "excerpt": case.excerpt,
            },
            key=f"{case.product_code or case.excerpt}|{case.reason}",
            batch_id=event.batch_id,
        )
    logger.info("Unreadable rows queued", extra={"cases": len(event.cases)})


@events.subscribe(UnknownProductsObserved)
async def open_unknown_products(event: UnknownProductsObserved, session: AsyncSession) -> None:
    """The list brought a product the catalog does not know (RF-07)."""
    service = TriageService(session)
    for case in event.cases:
        await service.open_case(
            kind=UNKNOWN_PRODUCT,
            reason=UNKNOWN_PRODUCT_REASON,
            payload={
                "staging_row_id": case.staging_row_id,
                "product_code": case.product_code,
                "description": case.description,
                "price": str(case.price),
            },
            key=case.product_code,
            batch_id=event.batch_id,
        )
    logger.info("Unknown products queued", extra={"cases": len(event.cases)})


@events.subscribe(KnownProductsMissing)
async def open_missing_products(event: KnownProductsMissing, session: AsyncSession) -> None:
    """A known product stopped coming in the list (RF-28)."""
    service = TriageService(session)
    for product in event.products:
        await service.open_case(
            kind=MISSING_PRODUCT,
            reason=MISSING_PRODUCT_REASON,
            payload={
                "product_id": product.product_id,
                "product_code": product.product_code,
                "description": product.description,
            },
            key=str(product.product_id),
            batch_id=event.batch_id,
        )
    logger.info("Missing products queued", extra={"cases": len(event.products)})


@events.subscribe(PriceHistoryRowsQuarantined)
async def open_unreadable_history(
    event: PriceHistoryRowsQuarantined, session: AsyncSession
) -> None:
    """The published history of a product could not be read (RF-39).

    The product keeps its current price: nothing in this path touches it.
    """
    service = TriageService(session)
    for case in event.cases:
        await service.open_case(
            kind=UNREADABLE_HISTORY,
            reason=case.reason,
            payload={
                "staging_row_id": case.staging_row_id,
                "product_code": event.product_code,
                "excerpt": case.excerpt,
            },
            key=f"{event.product_code}|{case.excerpt}",
        )
    logger.info(
        "Unreadable history queued",
        extra={"product_code": event.product_code, "cases": len(event.cases)},
    )
