"""What `purchases` does when something happens elsewhere.

It never asks anybody anything. The register was read, a batch of invoices was
typed, the document of one of them was read, a voucher arrived, the owner moved
a parameter: each of those is a fact this module reacts to, in the transaction
of whoever published it.
"""

from collections.abc import Mapping
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.purchases.service import (
    INVOICE_ENTITY,
    KEEP_MANUAL,
    KEEP_PORTAL,
    MATCH_THRESHOLD_KEY,
    ORDER_ENTITY,
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
    QuarantineCaseResolved,
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


# --- Lo que una persona decidió en «Para decidir» ------------------------
#
# Las cuatro clases de caso que terminan en una escritura de este módulo. Los
# strings se escriben acá y no se importan de `triage`: un módulo no importa
# otro (Artículo IV), y son justamente vocabulario compartido para que las dos
# puntas se entiendan sin conocerse.
UNREADABLE_INVOICE_ROW = "unreadable_invoice_row"
UNREADABLE_ORDER_ROW = "unreadable_order_row"
DISPUTED_INVOICE = "disputed_invoice"
DISPUTED_ORDER = "disputed_order"

# La decisión de cargar la fila a mano, frente a la de sólo darla por revisada.
LOAD = "load"


def _text(values: Mapping[str, Any], key: str) -> str:
    """Un string de la decisión, o vacío. Nada se convierte confiando."""
    value = values.get(key)
    return str(value).strip() if isinstance(value, str | int | float) else ""


def _date_of(values: Mapping[str, Any], key: str) -> date | None:
    """Una fecha ISO de la decisión, o `None` si no es una fecha."""
    raw = _text(values, key)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        logger.warning("A decision carried a date that is not one", extra={"field": key})
        return None


def _money_of(values: Mapping[str, Any], key: str) -> Decimal | None:
    """Un importe de la decisión, con las mismas puertas cerradas que en `catalog`.

    `Decimal` construye `nan`, `snan` e `Infinity` sin quejarse, y esto escribe
    sobre una columna de plata que después se compara y se suma. Un `NaN` que
    pasara por acá no se quedaría quieto: haría fallar el próximo total.
    """
    raw = _text(values, key)
    if not raw:
        return None
    try:
        amount = Decimal(raw)
    except (InvalidOperation, ArithmeticError):
        logger.warning("A decision carried an amount that is not a number", extra={"field": key})
        return None
    if not amount.is_finite() or amount < 0:
        logger.warning("A decision carried an amount that is not one", extra={"field": key})
        return None
    return amount


def _int_of(values: Mapping[str, Any], key: str) -> int | None:
    """Un entero de la decisión, o `None`."""
    value = values.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


@events.subscribe(QuarantineCaseResolved)
async def apply_purchases_decision(event: QuarantineCaseResolved, session: AsyncSession) -> None:
    """Escribir lo que una persona decidió sobre una fila de compras.

    Son dos decisiones distintas y las dos existen por lo mismo. **Cargarla a
    mano** es la otra mitad del Artículo II: hasta la 011 una fila que el portal
    publicaba rota sólo se podía dar por revisada, así que la factura no entraba
    a ningún total ni al calendario, y avisar sin dejar arreglar es la mitad de
    una promesa. **Elegir quién gana** es lo que pasa cuando el portal publica,
    meses después, esa misma fila ya legible y distinta.

    Una decisión que no es ninguna de las dos —darla por revisada— no escribe
    nada acá, y eso no es un caso que falte: es la respuesta que el origen de
    sólo lectura admite cuando el papel no está a mano.

    Corre en la transacción de quien resolvió el caso: si esto falla, la
    resolución falla con él y el caso sigue pendiente, que es exactamente lo que
    tiene que pasar cuando el número ya estaba registrado (`GEN-09`).
    """
    decision = event.decision
    service = PurchasesService(session)

    if event.kind == UNREADABLE_INVOICE_ROW and _text(decision, "action") == LOAD:
        issued_on = _date_of(decision, "issued_on")
        total = _money_of(decision, "total")
        supplier_id = _int_of(decision, "supplier_id")
        number = _text(decision, "number")
        if issued_on is None or total is None or supplier_id is None or not number:
            logger.warning("An invoice to load by hand arrived incomplete")
            return
        await service.register_invoice_by_hand(
            number=number,
            issued_on=issued_on,
            total=total,
            supplier_id=supplier_id,
            actor_user_id=event.decided_by_user_id,
            occurred_at=event.decided_at,
        )
        return

    if event.kind == UNREADABLE_ORDER_ROW and _text(decision, "action") == LOAD:
        ordered_on = _date_of(decision, "ordered_on")
        supplier_id = _int_of(decision, "supplier_id")
        number = _text(decision, "number")
        if ordered_on is None or supplier_id is None or not number:
            logger.warning("An order to load by hand arrived incomplete")
            return
        await service.register_order_by_hand(
            number=number,
            ordered_on=ordered_on,
            supplier_id=supplier_id,
            product_text=_text(decision, "product_text"),
            quantity=_int_of(decision, "quantity"),
            amount=_money_of(decision, "amount"),
            actor_user_id=event.decided_by_user_id,
            occurred_at=event.decided_at,
        )
        return

    if event.kind in {DISPUTED_INVOICE, DISPUTED_ORDER}:
        keep = _text(decision, "keep")
        if keep not in {KEEP_PORTAL, KEEP_MANUAL}:
            logger.warning("A settled dispute did not say which values stay")
            return
        entity_id = _int_of(event.payload, "entity_id")
        if entity_id is None:
            logger.warning("A settled dispute did not say which record it was about")
            return
        # Lo que el portal publicó viaja en el caso, que es donde quedó cuando
        # se abrió la discusión: el evento que la abrió ya no existe, y volver a
        # leer el portal para preguntárselo sería contestar con otra cosa.
        stored = event.payload.get("published")
        published = (
            {str(key): str(value) for key, value in stored.items()}
            if isinstance(stored, dict)
            else {}
        )
        await service.settle_manual_dispute(
            entity=INVOICE_ENTITY if event.kind == DISPUTED_INVOICE else ORDER_ENTITY,
            entity_id=entity_id,
            keep=keep,
            published=published,
            actor_user_id=event.decided_by_user_id,
            occurred_at=event.decided_at,
        )
