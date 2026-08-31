"""What `purchases` does when something happens elsewhere.

It never asks anybody anything. The register was read, a batch of invoices was
typed, the document of one of them was read, a voucher arrived, the owner moved
a parameter: each of those is a fact this module reacts to, in the transaction
of whoever published it.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.purchases.service import (
    MATCH_THRESHOLD_KEY,
    RECEIPT_NOTICE_KEY,
    REPEAT_WINDOW_KEY,
    STALLED_DAYS_KEY,
    PurchasesService,
)
from app.shared.events import (
    BusinessParameterChanged,
    DailyDigestContribution,
    DailyDigestRequested,
    DueDateChanged,
    InvoiceFileRead,
    InvoicesNormalized,
    InvoicesRegistered,
    PaymentsNormalized,
    PurchaseOrdersNormalized,
    SuppliersNormalized,
    events,
)
from app.shared.live import announce

logger = get_logger(__name__)

# The parameters this module keeps a projection of. A key that is not here is
# not this module's business, and the handler says nothing about it.
WATCHED_PARAMETERS = frozenset(
    {MATCH_THRESHOLD_KEY, RECEIPT_NOTICE_KEY, STALLED_DAYS_KEY, REPEAT_WINDOW_KEY}
)

# How many orders the digest names one by one. The rest are in the count.
DIGEST_LINES = 5


@events.subscribe(SuppliersNormalized)
async def remember_register(event: SuppliersNormalized, session: AsyncSession) -> None:
    """Record the supplier register as `/estado-cuenta` publishes it (RF-08)."""
    await PurchasesService(session).remember_suppliers(event.suppliers)


@events.subscribe(InvoicesNormalized)
async def register_invoices(event: InvoicesNormalized, session: AsyncSession) -> None:
    """Bring the invoices of a batch into the business model."""
    await PurchasesService(session).register_invoices(
        batch_id=event.batch_id, invoices=event.invoices
    )


@events.subscribe(InvoiceFileRead)
async def record_document(event: InvoiceFileRead, session: AsyncSession) -> None:
    """Keep what the document said, and hold the invoice when it disagrees."""
    await PurchasesService(session).record_document(
        invoice_number=event.invoice_number,
        raw_document_id=event.raw_document_id,
        readable=event.readable,
        agrees=event.agrees,
        excerpt=event.excerpt,
        reason=event.reason,
        number=event.number,
        issued_on=event.issued_on,
        total=event.total,
        supplier_text=event.supplier_text,
        supplier_tax_id=event.supplier_tax_id,
        content=event.content,
        content_type=event.content_type,
    )


@events.subscribe(PaymentsNormalized)
async def impute_payments(event: PaymentsNormalized, session: AsyncSession) -> None:
    """Register the vouchers the current account published."""
    await PurchasesService(session).impute_payments(event.payments)


@events.subscribe(InvoicesRegistered)
async def impute_what_was_waiting(event: InvoicesRegistered, session: AsyncSession) -> None:
    """Impute the vouchers that named an invoice nobody had registered (RF-44).

    Subscribed to this module's **own** event on purpose. It is the same fact
    the rest of the platform hears — an invoice entered the business model — and
    reacting to it here keeps the imputation from being a step somebody has to
    remember to call after every path that registers one.
    """
    service = PurchasesService(session)
    for registered in event.invoices:
        invoice = await service.purchases.invoice(registered.invoice_id)
        if invoice is not None:
            await service.impute_held_payments_for(invoice)


@events.subscribe(PurchaseOrdersNormalized)
async def register_orders(event: PurchaseOrdersNormalized, session: AsyncSession) -> None:
    """Bring the purchase orders of a batch in, and start watching them."""
    await PurchasesService(session).register_orders(batch_id=event.batch_id, orders=event.orders)


@events.subscribe(BusinessParameterChanged)
async def remember_parameter(event: BusinessParameterChanged, session: AsyncSession) -> None:
    """Keep the parameters this module reads while it works (RF-11, RF-17, RF-41)."""
    if event.key not in WATCHED_PARAMETERS:
        return
    await PurchasesService(session).remember_setting(event.key, event.value)


@events.subscribe(DailyDigestRequested)
async def contribute_to_the_digest(event: DailyDigestRequested, session: AsyncSession) -> None:
    """Say which orders have not moved (RF-35, RF-41 of 007).

    Once a day at most, which is what RF-41 asks: an order that stays stalled
    appears in one digest per day and not in every alert of the day.
    """
    stalled = await PurchasesService(session).stalled_orders()
    await events.publish(
        DailyDigestContribution(
            source="purchase_orders",
            pending=len(stalled),
            lines=tuple(
                f"• {order.number} — {order.supplier_name or order.supplier_text}: "
                f"{order.status_text} hace {order.days_in_status} días"
                for order in stalled[:DIGEST_LINES]
            ),
        ),
        session,
    )
    del event


@events.subscribe(DueDateChanged)
async def push_the_calendar_change(event: DueDateChanged, session: AsyncSession) -> None:
    """Tell the screens of the other people looking at the calendar (RF-31 to RF-33).

    It runs in the transaction of whoever moved the entry, and that is fine here
    precisely because of *how* it says it: `pg_notify` is transactional, so a
    move that ends up rolled back announces nothing, and nothing is written to a
    socket from inside the transaction. Sending an HTTP push from here instead
    would make one person's dropped connection able to abort another person's
    change, which is what `GEN-09` is about.
    """
    await announce(
        session,
        topic="calendar",
        payload={
            "due_date_id": event.due_date_id,
            "action": event.action,
            "actor_name": event.actor_name,
            "on_date": event.on_date,
            "invoice_id": event.invoice_id,
        },
    )
