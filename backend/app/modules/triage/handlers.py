"""What `triage` does when something happens elsewhere.

Seven subscriptions, one per way the platform can fail to resolve something on
its own. None of them knows which module published: a case is a case, whether
it came from an unreadable row of the price list, from a product nobody has
ever heard of, or from a row of the invoices (004) or the purchase orders (007)
screen.

The queue never had to change shape to take any of them, which is the point of
a generic queue: a `kind`, a free-form payload, and the decision learned as a
rule.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.triage.service import (
    MISSING_PRODUCT,
    MISSING_PRODUCT_REASON,
    UNKNOWN_CATEGORY,
    UNKNOWN_CATEGORY_REASON,
    UNKNOWN_PRODUCT,
    UNKNOWN_PRODUCT_REASON,
    UNREADABLE_HISTORY,
    UNREADABLE_INVOICE_ROW,
    UNREADABLE_ORDER_ROW,
    UNREADABLE_ROW,
    TriageService,
)
from app.shared.events import (
    InvoiceRowsQuarantined,
    KnownProductsMissing,
    PriceHistoryRowsQuarantined,
    PriceRowsQuarantined,
    PurchaseOrderRowsQuarantined,
    UnknownCategoryObserved,
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


@events.subscribe(InvoiceRowsQuarantined)
async def open_unreadable_invoice_rows(
    event: InvoiceRowsQuarantined, session: AsyncSession
) -> None:
    """A row of the invoices screen could not be typed (RF-07, RF-34 of 004).

    This subscription is what makes the Artículo II true on the invoices side.
    `ingestion` published this event from the first day and **nobody listened**:
    the row went to quarantine in `staging` and stopped there, so it was not
    counted, not shown and never decided — the silence the article exists to
    forbid. Its two siblings on the price side have opened a case since 001;
    this one did not, and nothing failed loudly enough for anybody to notice.

    What a person can do about it is **see it and say they saw it**, and no
    more: an invoice is only ever born from a row the portal published, and
    typing one by hand from this queue would be loading an invoice by hand,
    which the signed spec puts out of scope. So it is the same shape as an
    unreadable history — the excerpt, and a decision that closes it.
    """
    service = TriageService(session)
    for case in event.cases:
        await service.open_case(
            kind=UNREADABLE_INVOICE_ROW,
            reason=case.reason,
            payload={
                "staging_row_id": case.staging_row_id,
                "excerpt": case.excerpt,
            },
            key=f"{case.excerpt}|{case.reason}",
            batch_id=event.batch_id,
        )
    logger.info("Unreadable invoice rows queued", extra={"cases": len(event.cases)})


@events.subscribe(PurchaseOrderRowsQuarantined)
async def open_unreadable_order_rows(
    event: PurchaseOrderRowsQuarantined, session: AsyncSession
) -> None:
    """A row of the purchase orders screen could not be typed (RF-08 of 007).

    The same subscription the invoices needed, on the screen where losing a row
    hurts most: 007 exists because *«nadie sigue los pedidos»*, and a purchase
    order that is quarantined without opening a case is a pedido nobody follows
    for the most literal reason there is — the platform never admitted it saw
    it.

    What a person can do is see it and say they saw it. An order is only ever
    born from a row the portal published, and typing one by hand here would be
    loading an order by hand, which no requirement asks for.
    """
    service = TriageService(session)
    for case in event.cases:
        await service.open_case(
            kind=UNREADABLE_ORDER_ROW,
            reason=case.reason,
            payload={
                "staging_row_id": case.staging_row_id,
                "excerpt": case.excerpt,
            },
            key=f"{case.excerpt}|{case.reason}",
            batch_id=event.batch_id,
        )
    logger.info("Unreadable order rows queued", extra={"cases": len(event.cases)})


@events.subscribe(UnknownCategoryObserved)
async def open_unknown_categories(event: UnknownCategoryObserved, session: AsyncSession) -> None:
    """A written form of a category nobody has decided about (RF-21 of 008).

    One case per written form, and the fingerprint is the text: a hundred
    products of the same batch spelled the same way ask **one** question, and
    the count of how many times it came back is what the screen shows.
    """
    service = TriageService(session)
    for case in event.cases:
        await service.open_case(
            kind=UNKNOWN_CATEGORY,
            reason=UNKNOWN_CATEGORY_REASON,
            payload={
                "category_text": case.category_text,
                "product_codes": list(case.product_codes),
                "products": len(case.product_codes),
            },
            key=case.category_text,
            batch_id=event.batch_id or None,
        )
    logger.info("Unknown categories queued", extra={"cases": len(event.cases)})
