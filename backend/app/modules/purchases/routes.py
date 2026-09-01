"""HTTP routes for the purchases module.

Sales appears in none of them, and that is a business rule and not an oversight:
RF-06 of 004 keeps the invoices and the register away from whoever handles
sales, and RF-09 and RF-46 of 007 do the same for the orders and the inbox. The
one exception is the **calendar**, which sales consults and cannot change
(RF-37, RF-38 of 006) — so it asks for a read level on its own section rather
than for a different section.

Authorisation comes from `identity.dependencies`, the one thing that crosses a
module boundary: a request has to know whether it may continue before its
handler runs, and an event cannot answer that in time.
"""

from collections.abc import AsyncIterator
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.modules.identity.dependencies import (
    ActorDirectory,
    ActorDirectoryDep,
    CurrentUser,
    Level,
    Section,
    require_section,
)
from app.modules.purchases.models import InvoiceOrder, InvoiceReviewState
from app.modules.purchases.schemas import (
    AliasPreview,
    AliasWrite,
    CalendarRead,
    DueDateEdit,
    DueDateMove,
    DueDateRead,
    DueDateWrite,
    IncidentClose,
    IncidentRead,
    InvoiceList,
    InvoiceRead,
    InvoiceReviewResolution,
    OrderResolution,
    PaymentRead,
    PaymentSplitWrite,
    PaymentWrite,
    PurchaseOrderList,
    PurchaseOrderRead,
    PurchasesDashboard,
    ReceiptRead,
    SupplierAliasRead,
    SupplierContactWrite,
    SupplierList,
    SupplierRead,
    SupplierTotalsRead,
)
from app.modules.purchases.service import PurchasesService, today_here
from app.shared.live import announce, bus

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

# Used to walk to the first day of the next month without a calendar library.
_ONE_WEEK = timedelta(days=7)
_ONE_DAY = timedelta(days=1)

Session = Annotated[AsyncSession, Depends(get_session)]


def get_purchases_service(session: Session) -> PurchasesService:
    """Provide the purchases service for a request."""
    return PurchasesService(session)


PurchasesDep = Annotated[PurchasesService, Depends(get_purchases_service)]

SkipParam = Annotated[int, Query(ge=0, description="Rows to skip")]
LimitParam = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE, description="Rows per page")]
SearchParam = Annotated[str | None, Query(max_length=255, description="Match number or supplier")]

invoices_router = APIRouter(prefix="/invoices", tags=["Invoices"])
suppliers_router = APIRouter(prefix="/suppliers", tags=["Suppliers"])
review_router = APIRouter(prefix="/invoice-review", tags=["Invoices"])
aliases_router = APIRouter(prefix="/supplier-aliases", tags=["Suppliers"])
payments_router = APIRouter(prefix="/payments", tags=["Payments"])
receipts_router = APIRouter(prefix="/receipts", tags=["Receipts"])
incidents_router = APIRouter(prefix="/receipt-incidents", tags=["Receipts"])
calendar_router = APIRouter(prefix="/calendar", tags=["Calendar"])
orders_router = APIRouter(prefix="/purchase-orders", tags=["Purchase orders"])
purchases_dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# --- The invoices (004, 005) ---------------------------------------------


@invoices_router.get(
    "",
    dependencies=[require_section(Section.PURCHASE_INVOICES, Level.READ)],
    summary="The invoices, with every filter and every order of the screen",
)
async def list_invoices(
    service: PurchasesDep,
    directory: ActorDirectoryDep,
    skip: SkipParam = 0,
    limit: LimitParam = DEFAULT_PAGE_SIZE,
    q: SearchParam = None,
    supplier_id: Annotated[int | None, Query(description="Only this supplier's")] = None,
    review_state: Annotated[InvoiceReviewState | None, Query(description="By review")] = None,
    payment_state: Annotated[str | None, Query(description="SALDADA, PARCIAL, SIN_PAGOS")] = None,
    issued_from: Annotated[date | None, Query(description="Issued from this date")] = None,
    issued_to: Annotated[date | None, Query(description="Issued up to this date")] = None,
    due_from: Annotated[date | None, Query(description="Falling due from")] = None,
    due_to: Annotated[date | None, Query(description="Falling due up to")] = None,
    with_receipt: Annotated[bool | None, Query(description="With or without receipt")] = None,
    order: Annotated[InvoiceOrder, Query(description="By date or by total")] = (
        InvoiceOrder.ISSUED_DESC
    ),
) -> InvoiceList:
    """The owner and purchasing (RF-03, RF-05, RF-39 to RF-46 of 004).

    `q` searches the invoice number, the supplier name as it arrived written,
    and —for an invoice already attributed— the tax id and the legal name of
    the register (RF-41, RF-42).
    """
    listing = await service.list_invoices(
        skip=skip,
        limit=limit,
        query=q,
        supplier_id=supplier_id,
        review_state=review_state,
        payment_state=payment_state,
        issued_from=issued_from,
        issued_to=issued_to,
        due_from=due_from,
        due_to=due_to,
        with_receipt=with_receipt,
        order=order,
    )
    await _name_whoever_resolved(listing.items, directory)
    return listing


@invoices_router.get(
    "/{invoice_id}",
    dependencies=[require_section(Section.PURCHASE_INVOICES, Level.READ)],
    summary="One invoice, with what its document said",
)
async def get_invoice(
    invoice_id: int, service: PurchasesDep, directory: ActorDirectoryDep
) -> InvoiceRead:
    """The owner and purchasing (RF-03, RF-27, RF-32, RF-39 of 004)."""
    invoice = await service.get_invoice(invoice_id)
    await _name_whoever_resolved([invoice], directory)
    return invoice


async def _name_whoever_resolved(invoices: list[InvoiceRead], directory: ActorDirectory) -> None:
    """Put a name next to the id of whoever decided about a held invoice.

    Here and not in the service, for the same reason the history of `operations`
    resolves its authors at the edge: `purchases` stores an id and holds no
    foreign key to `users`, because two modules' schemas do not get to depend on
    each other (Artículo IV). The name is a rendering concern, so it is resolved
    by the one file of `identity` another module may import (RF-32).
    """
    names = await directory.names_for(
        {invoice.resolved_by_user_id for invoice in invoices if invoice.resolved_by_user_id}
    )
    for invoice in invoices:
        if invoice.resolved_by_user_id is not None:
            invoice.resolved_by_name = names.get(invoice.resolved_by_user_id)


@invoices_router.get(
    "/{invoice_id}/payments",
    dependencies=[require_section(Section.PAYMENTS, Level.READ)],
    summary="The payments imputed to an invoice",
)
async def invoice_payments(invoice_id: int, service: PurchasesDep) -> list[PaymentRead]:
    """The owner and purchasing (RF-10, RF-20 of 005)."""
    return await service.payments_of(invoice_id)


@invoices_router.post(
    "/{invoice_id}/payments",
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_section(Section.PAYMENTS, Level.WRITE)],
    summary="Register a payment by hand",
)
async def register_payment(
    invoice_id: int, payload: PaymentWrite, current_user: CurrentUser, service: PurchasesDep
) -> PaymentRead:
    """Purchasing and the owner (RF-18, RF-19, RF-21 of 005).

    A payment over the outstanding balance comes back as a conflict the first
    time, with the balance in it: that is the warning, and it is answered by
    sending it again with `confirm_over_balance`.
    """
    return await service.register_payment(
        invoice_id,
        amount=payload.amount,
        paid_on=payload.paid_on,
        reference=payload.reference,
        actor_user_id=current_user.id,
        confirm_over_balance=payload.confirm_over_balance,
    )


@invoices_router.get(
    "/{invoice_id}/receipt",
    dependencies=[require_section(Section.RECEIPTS, Level.READ)],
    summary="The reception receipt of an invoice",
)
async def get_receipt(invoice_id: int, service: PurchasesDep) -> ReceiptRead:
    """The owner and purchasing (RF-29, RF-47 of 005)."""
    return await service.get_receipt(invoice_id)


@invoices_router.post(
    "/{invoice_id}/receipt",
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_section(Section.RECEIPTS, Level.WRITE)],
    summary="Issue the reception receipt of an invoice",
)
async def issue_receipt(
    invoice_id: int, current_user: CurrentUser, service: PurchasesDep
) -> ReceiptRead:
    """Purchasing and the owner (RF-33, RF-36, RF-47, RF-48 of 005).

    Refused with its reason when the invoice already fell due (RF-34) or already
    has a receipt in force (RF-35).
    """
    return await service.issue_receipt(invoice_id, actor_user_id=current_user.id)


# --- The register (004) --------------------------------------------------


@suppliers_router.get(
    "",
    dependencies=[require_section(Section.SUPPLIERS, Level.READ)],
    summary="The supplier register",
)
async def list_suppliers(service: PurchasesDep) -> SupplierList:
    """The owner and purchasing (RF-08, RF-24 of 004)."""
    return await service.list_suppliers()


@suppliers_router.get(
    "/{supplier_id}",
    dependencies=[require_section(Section.SUPPLIERS, Level.READ)],
    summary="One supplier, with what the portal did not publish marked",
)
async def get_supplier(supplier_id: int, service: PurchasesDep) -> SupplierRead:
    """The owner and purchasing (RF-10, RF-15, RF-20 of 004)."""
    return await service.get_supplier(supplier_id)


@suppliers_router.patch(
    "/{supplier_id}",
    dependencies=[require_section(Section.SUPPLIERS, Level.WRITE)],
    summary="Correct the contact details of a supplier",
)
async def correct_supplier(
    supplier_id: int,
    payload: SupplierContactWrite,
    current_user: CurrentUser,
    service: PurchasesDep,
) -> SupplierRead:
    """The owner and purchasing (RF-16 to RF-19 of 004).

    What the portal had said is kept, so the correction can be undone and a
    later reading that contradicts it is reported instead of overwriting it.
    """
    return await service.correct_supplier(
        supplier_id,
        values={
            "email": payload.email,
            "phone": payload.phone,
            "payment_term_days": payload.payment_term_days,
        },
        reason_code=payload.reason_code,
        reason_detail=payload.reason_detail,
        actor_user_id=current_user.id,
    )


@suppliers_router.get(
    "/{supplier_id}/invoices",
    dependencies=[require_section(Section.PURCHASE_INVOICES, Level.READ)],
    summary="The invoices of one supplier",
)
async def supplier_invoices(
    supplier_id: int,
    service: PurchasesDep,
    skip: SkipParam = 0,
    limit: LimitParam = DEFAULT_PAGE_SIZE,
) -> InvoiceList:
    """The owner and purchasing (RF-21 of 004)."""
    return await service.list_invoices(skip=skip, limit=limit, supplier_id=supplier_id)


@suppliers_router.get(
    "/{supplier_id}/totals",
    dependencies=[require_section(Section.SUPPLIERS, Level.READ)],
    summary="What a supplier was invoiced, paid and still owes",
)
async def supplier_totals(
    supplier_id: int,
    service: PurchasesDep,
    since: Annotated[date | None, Query(description="From this date")] = None,
    until: Annotated[date | None, Query(description="Up to this date")] = None,
) -> SupplierTotalsRead:
    """The owner and purchasing (RF-22, RF-23 of 004; RF-24 to RF-28 of 005).

    What it left out travels with the number, never quietly.
    """
    return await service.supplier_totals(supplier_id, since=since, until=until)


# --- The review of what could not be decided alone (004) -----------------


@review_router.get(
    "",
    dependencies=[require_section(Section.PURCHASE_INVOICES, Level.WRITE)],
    summary="The invoices waiting for a person",
)
async def review_queue(
    service: PurchasesDep,
    directory: ActorDirectoryDep,
    skip: SkipParam = 0,
    limit: LimitParam = DEFAULT_PAGE_SIZE,
) -> InvoiceList:
    """The owner and purchasing (RF-30, RF-34, RF-46 of 004)."""
    queue = await service.review_queue(skip=skip, limit=limit)
    await _name_whoever_resolved(queue.items, directory)
    return queue


@review_router.post(
    "/{invoice_id}/resolve",
    dependencies=[require_section(Section.PURCHASE_INVOICES, Level.WRITE)],
    summary="Decide about an invoice held for review",
)
async def resolve_invoice(
    invoice_id: int,
    payload: InvoiceReviewResolution,
    current_user: CurrentUser,
    service: PurchasesDep,
) -> InvoiceRead:
    """The owner and purchasing (RF-31, RF-32, RF-33, RF-36 of 004).

    Who decided comes from the token, never from the body.
    """
    return await service.resolve_invoice(
        invoice_id,
        supplier_id=payload.supplier_id,
        remember=payload.remember,
        actor_user_id=current_user.id,
        number=payload.number,
        issued_on=payload.issued_on,
        total=payload.total,
    )


# --- The spellings of a supplier's name (004) ----------------------------


@aliases_router.get(
    "",
    dependencies=[require_section(Section.SUPPLIERS, Level.READ)],
    summary="The spellings assigned to a supplier",
)
async def list_aliases(
    service: PurchasesDep, directory: ActorDirectoryDep
) -> list[SupplierAliasRead]:
    """The owner and purchasing (RF-51 of 004).

    The name of whoever decided each spelling is resolved here, not in the
    service: the criterion asks for «quién y cuándo», and `purchases` can say
    the id but not the person (Artículo IV).
    """
    aliases = await service.list_aliases()
    names = await directory.names_for(
        {alias.created_by_user_id for alias in aliases if alias.created_by_user_id}
    )
    for alias in aliases:
        if alias.created_by_user_id is not None:
            alias.created_by_name = names.get(alias.created_by_user_id)
    return aliases


@aliases_router.post(
    "/preview",
    dependencies=[require_section(Section.SUPPLIERS, Level.WRITE)],
    summary="How many invoices this assignment would resolve",
)
async def preview_alias(payload: AliasWrite, service: PurchasesDep) -> AliasPreview:
    """The owner and purchasing (RF-48 of 004).

    Counted with the query that will resolve them, so the number promised here
    is the number that happens.
    """
    return await service.preview_alias(text=payload.text, supplier_id=payload.supplier_id)


@aliases_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_section(Section.SUPPLIERS, Level.WRITE)],
    summary="Assign a spelling to a supplier",
)
async def save_alias(
    payload: AliasWrite, current_user: CurrentUser, service: PurchasesDep
) -> AliasPreview:
    """The owner and purchasing (RF-47, RF-49, RF-50 of 004)."""
    return await service.save_alias(
        text=payload.text, supplier_id=payload.supplier_id, actor_user_id=current_user.id
    )


@aliases_router.delete(
    "/{alias_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_section(Section.SUPPLIERS, Level.WRITE)],
    summary="Leave an assignment without effect",
)
async def drop_alias(alias_id: int, service: PurchasesDep) -> None:
    """The owner and purchasing (RF-52, RF-53 of 004).

    What that assignment resolved goes back to the queue. What somebody decided
    one by one does not.
    """
    await service.drop_alias(alias_id)


# --- The payments held for a decision (005) ------------------------------


@payments_router.get(
    "/pending",
    dependencies=[require_section(Section.PAYMENTS, Level.WRITE)],
    summary="The vouchers waiting to be distributed",
)
async def pending_payments(service: PurchasesDep) -> list[PaymentRead]:
    """The owner and purchasing (RF-11, RF-12, RF-54 of 005)."""
    return await service.pending_payments()


@payments_router.post(
    "/{payment_id}/split",
    dependencies=[require_section(Section.PAYMENTS, Level.WRITE)],
    summary="Distribute a voucher between the invoices it covers",
)
async def split_payment(
    payment_id: int,
    payload: PaymentSplitWrite,
    current_user: CurrentUser,
    service: PurchasesDep,
) -> list[PaymentRead]:
    """The owner and purchasing (RF-53, RF-55, RF-56 of 005)."""
    return await service.split_payment(
        payment_id,
        parts=[(part.invoice_id, part.amount) for part in payload.parts],
        actor_user_id=current_user.id,
    )


@payments_router.delete(
    "/{payment_id}",
    dependencies=[require_section(Section.PAYMENTS, Level.WRITE)],
    summary="Leave a payment loaded by hand without effect",
)
async def void_payment(
    payment_id: int, current_user: CurrentUser, service: PurchasesDep
) -> PaymentRead:
    """The owner and purchasing (RF-22 of 005). A voucher of the portal is refused (RF-23)."""
    return await service.void_payment(payment_id, actor_user_id=current_user.id)


# --- The receipts and their incidents (005) ------------------------------


@receipts_router.delete(
    "/{receipt_id}",
    dependencies=[require_section(Section.RECEIPTS, Level.WRITE)],
    summary="Annul a receipt already issued",
)
async def void_receipt(
    receipt_id: int, current_user: CurrentUser, service: PurchasesDep
) -> ReceiptRead:
    """The owner and purchasing (RF-49, RF-50, RF-51 of 005)."""
    return await service.void_receipt(receipt_id, actor_user_id=current_user.id)


@incidents_router.get(
    "",
    dependencies=[require_section(Section.RECEIPTS, Level.READ)],
    summary="The invoices that fell due without their receipt",
)
async def list_incidents(
    service: PurchasesDep,
    include_closed: Annotated[bool, Query(description="Also the ones already closed")] = False,
) -> list[IncidentRead]:
    """The owner and purchasing (RF-37, RF-59 of 005)."""
    return await service.list_incidents(only_open=not include_closed)


@incidents_router.post(
    "/{incident_id}/close",
    dependencies=[require_section(Section.RECEIPTS, Level.WRITE)],
    summary="Close an incident, saying what was done",
)
async def close_incident(
    incident_id: int,
    payload: IncidentClose,
    current_user: CurrentUser,
    service: PurchasesDep,
) -> IncidentRead:
    """The owner and purchasing (RF-57, RF-58, RF-59 of 005)."""
    return await service.close_incident(
        incident_id, resolution=payload.resolution, actor_user_id=current_user.id
    )


# --- The calendar (006) --------------------------------------------------


@calendar_router.get(
    "",
    dependencies=[require_section(Section.CALENDAR, Level.READ)],
    summary="One window of the calendar of due dates",
)
async def read_calendar(
    service: PurchasesDep,
    directory: ActorDirectoryDep,
    since: Annotated[date | None, Query(description="First day shown")] = None,
    until: Annotated[date | None, Query(description="Last day shown")] = None,
    without_receipt: Annotated[bool, Query(description="Only what has no receipt")] = False,
    hide_settled: Annotated[bool, Query(description="Hide what is already settled")] = False,
) -> CalendarRead:
    """All three roles: sales consults the calendar and cannot change it (RF-37).

    With no window given it opens on the current month, which is RF-04.
    """
    start, end = _month_of(since, until)
    read = await service.calendar(
        since=start, until=end, without_receipt=without_receipt, hide_settled=hide_settled
    )
    await _name_whoever_touched_the_calendar(read.items, directory)
    return read


@calendar_router.post(
    "/presence",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_section(Section.CALENDAR, Level.WRITE)],
    summary="Decir que se está mirando el calendario",
)
async def announce_presence(current_user: CurrentUser, session: Session) -> None:
    """Contar en el canal que esta persona tiene el calendario abierto (H5 de 006).

    La otra mitad de «se actualiza en vivo». Hasta acá la pantalla decía qué
    cambió y quién lo cambió, y no decía **quién más está mirando**, que es el
    dato que cambia cómo se trabaja: mover un vencimiento sabiendo que del otro
    lado hay alguien mirando la misma pantalla no es lo mismo que moverlo a
    ciegas.

    **Pide `WRITE` y no `READ`, y eso deja afuera a ventas: se anuncia quien
    puede cambiar algo.** Nació pidiendo `READ` —anunciarse no escribe ningún
    dato del negocio— y `tests/architecture/test_route_authorization.py` lo
    frenó: un `POST` tiene que exigir el nivel que cambia, porque la alternativa
    es que la regla dependa de que cada caso se juzgue a ojo. Debilitar el test
    para dejar pasar éste habría sido cambiar una regla verificada por una
    opinión (Artículo VI).

    Y la consecuencia resulta ser la correcta: la presencia existe para que dos
    personas no se pisen editando lo mismo, y quien tiene el calendario en sólo
    lectura no puede pisar a nadie. Ventas ve quién está —el canal es de lectura
    para los tres roles— y no aparece en la lista de los demás. La asimetría no
    esconde ningún riesgo: nada de lo que ventas haga acá puede sorprender a
    quien está moviendo un vencimiento.

    **No hay registro de presencias en ninguna parte, y es deliberado.** Cada
    navegador anuncia que está, cada tanto, y los demás lo escuchan; el que se
    va deja de anunciarse y desaparece solo de las demás pantallas cuando se le
    vence el turno. Una tabla de «quién está conectado» habría que limpiarla
    cuando alguien cierra el navegador de golpe, que es justo el caso en que
    nadie avisa — y una lista que se ensucia dice que hay gente mirando que no
    está.

    Viaja el nombre y el id, nada más: es lo que se dibuja. No es un registro de
    auditoría —eso es el historial— y por eso no se guarda.
    """
    await announce(
        session,
        "presence",
        {
            "screen": "calendar",
            "user_id": current_user.id,
            "name": f"{current_user.name} {current_user.last_name or ''}".strip(),
        },
    )
    await session.commit()


async def _name_whoever_touched_the_calendar(
    entries: list[DueDateRead], directory: ActorDirectory
) -> None:
    """Put names next to the ids the calendar carries (RF-13, RF-21).

    Same reason as the invoices: `purchases` stores an id and holds no foreign
    key to `users`, so the name is resolved at the edge by the one file of
    `identity` another module may import.

    Without this the two requirements cannot be met at all: «figura con el
    nombre de Marcela» is not something a screen can render from a number.
    """
    ids = {entry.created_by_user_id for entry in entries if entry.created_by_user_id}
    ids |= {change.actor_user_id for entry in entries for change in entry.changes}
    names = await directory.names_for(ids)
    for entry in entries:
        if entry.created_by_user_id is not None:
            entry.created_by_name = names.get(entry.created_by_user_id)
        for change in entry.changes:
            change.actor_name = names.get(change.actor_user_id)


@calendar_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_section(Section.CALENDAR, Level.WRITE)],
    summary="Add a due date by hand",
)
async def add_due_date(
    payload: DueDateWrite, current_user: CurrentUser, service: PurchasesDep
) -> DueDateRead:
    """The owner and purchasing (RF-12, RF-13, RF-14 of 006). Sales is refused (RF-38)."""
    return await service.add_due_date(
        on_date=payload.on_date,
        description=payload.description,
        amount=payload.amount,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
    )


@calendar_router.patch(
    "/{due_date_id}",
    dependencies=[require_section(Section.CALENDAR, Level.WRITE)],
    summary="Correct a due date loaded by hand",
)
async def edit_due_date(
    due_date_id: int, payload: DueDateEdit, current_user: CurrentUser, service: PurchasesDep
) -> DueDateRead:
    """The owner and purchasing (RF-15, RF-16 of 006)."""
    return await service.edit_due_date(
        due_date_id,
        description=payload.description,
        amount=payload.amount,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
    )


@calendar_router.put(
    "/{due_date_id}/date",
    dependencies=[require_section(Section.CALENDAR, Level.WRITE)],
    summary="Move a due date to another day",
)
async def move_due_date(
    due_date_id: int, payload: DueDateMove, current_user: CurrentUser, service: PurchasesDep
) -> DueDateRead:
    """The owner and purchasing (RF-19 to RF-30, RF-42 of 006).

    Dragging it and picking a date are the same call: the browser decides how
    the person says it, and the platform has no reason to tell them apart.
    """
    return await service.move_due_date(
        due_date_id,
        on_date=payload.on_date,
        reason=payload.reason,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
        confirm_past=payload.confirm_past,
    )


@calendar_router.delete(
    "/{due_date_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_section(Section.CALENDAR, Level.WRITE)],
    summary="Remove a due date loaded by hand",
)
async def remove_due_date(
    due_date_id: int, current_user: CurrentUser, service: PurchasesDep
) -> None:
    """The owner and purchasing (RF-17 of 006). One from an invoice is refused (RF-18)."""
    await service.remove_due_date(
        due_date_id, actor_user_id=current_user.id, actor_name=current_user.name
    )


@calendar_router.get(
    "/stream",
    dependencies=[require_section(Section.CALENDAR, Level.READ)],
    summary="The live channel of the calendar",
)
async def calendar_stream() -> StreamingResponse:
    """All three roles, `READ`: sales watches the calendar live too (RF-37).

    Server-sent events, and not a WebSocket: everything the screen needs travels
    in one direction — what somebody else did — and what this screen does
    already has four routes of its own. A bidirectional protocol would bring its
    own handshake, its own keepalive and its own class of bugs to solve a
    problem that is not there.

    The browser does not call this route: the token lives in a cookie only the
    server reads, and `EventSource` cannot send headers. The Next route handler
    reads the cookie and proxies the stream, which is also why no token ever
    ends up in a query string.
    """

    async def events_of() -> AsyncIterator[str]:
        # An immediate comment so the reader knows it is connected rather than
        # waiting on a proxy that has not flushed anything yet.
        yield ": conectado\n\n"
        async for message in bus.read():
            yield f"data: {message}\n\n"

    return StreamingResponse(
        events_of(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _month_of(since: date | None, until: date | None) -> tuple[date, date]:
    """The window to show: what was asked for, or the current month (RF-04)."""
    if since is not None and until is not None:
        return since, until
    today = today_here()
    first = today.replace(day=1)
    next_month = (first.replace(day=28) + _ONE_WEEK).replace(day=1)
    return first, next_month - _ONE_DAY


# --- The purchase orders (007) -------------------------------------------


@orders_router.get(
    "",
    dependencies=[require_section(Section.PURCHASE_ORDERS, Level.READ)],
    summary="The purchase orders, with their counts",
)
async def list_orders(
    service: PurchasesDep,
    skip: SkipParam = 0,
    limit: LimitParam = MAX_PAGE_SIZE,
    status_text: Annotated[str | None, Query(description="Only this state")] = None,
    supplier_id: Annotated[int | None, Query(description="Only this supplier's")] = None,
    only_stalled: Annotated[bool, Query(description="Only the stalled ones")] = False,
    only_in_review: Annotated[bool, Query(description="Only the ones held for review")] = False,
) -> PurchaseOrderList:
    """The owner and purchasing. Sales is refused (RF-09 of 007).

    `only_in_review` is RF-52, and it is a filter of this same listing rather
    than a screen of its own: the spec decides it that way and gives the reason
    — a queue that costs time is a queue that gets abandoned.
    """
    return await service.list_orders(
        skip=skip,
        limit=limit,
        status_text=status_text,
        supplier_id=supplier_id,
        only_stalled=only_stalled,
        only_in_review=only_in_review,
    )


@orders_router.post(
    "/{order_id}/resolution",
    dependencies=[require_section(Section.PURCHASE_ORDERS, Level.WRITE)],
    summary="Say which supplier a held order is from",
)
async def resolve_order(
    order_id: int,
    payload: OrderResolution,
    current_user: CurrentUser,
    service: PurchasesDep,
) -> PurchaseOrderRead:
    """The owner and purchasing; sales is refused (RF-53 of 007).

    Who resolved it comes from the token, never from the body. With `remember`
    —the default— the spelling is saved as a criterion and **every other order
    and invoice written the same way is resolved with it** (RF-61, RF-62).

    There is no way to create a supplier from here, and that is the point of
    RF-55: the register is the portal's eight, and adding one is a decision of
    the business taken somewhere else.
    """
    return await service.resolve_order(
        order_id,
        supplier_id=payload.supplier_id,
        remember=payload.remember,
        actor_user_id=current_user.id,
    )


@orders_router.delete(
    "/{order_id}/repeat-flag",
    dependencies=[require_section(Section.PURCHASE_ORDERS, Level.WRITE)],
    summary="Drop the repeated-order flag",
)
async def dismiss_repeat(
    order_id: int, current_user: CurrentUser, service: PurchasesDep
) -> PurchaseOrderRead:
    """The owner and purchasing (RF-18, RF-19 of 007)."""
    return await service.dismiss_repeat(order_id, actor_user_id=current_user.id)


@invoices_router.get(
    "/{invoice_id}/file",
    dependencies=[require_section(Section.PURCHASE_INVOICES, Level.READ)],
    summary="What the document of the invoice said",
    response_class=Response,
)
async def invoice_file(invoice_id: int, service: PurchasesDep) -> Response:
    """The owner and purchasing (RF-04 of 004).

    The file **as the portal delivered it** — the PDF or the spreadsheet, with
    its own content type — and not a transcription of it. What a person disputes
    is a number, and the answer to «where does that number come from» is the
    paper it was printed on.

    It is served from this module's own copy (`core.invoice_document.content`),
    never by reading `raw`: that belongs to `portal`. `raw` stays the evidence
    and stays untouched (Artículo III).
    """
    document = await service.invoice_file(invoice_id)
    return Response(
        content=document.content,
        media_type=document.content_type,
        headers={"Content-Disposition": f'inline; filename="{document.filename}"'},
    )


# --- The purchases cut of the owner's dashboard (013) --------------------


@purchases_dashboard_router.get(
    "/purchases",
    dependencies=[
        require_section(Section.DASHBOARD, Level.READ),
        require_section(Section.PURCHASE_INVOICES, Level.READ),
    ],
    summary="What is owed, what falls due next and what never arrived",
)
async def purchases_dashboard(service: PurchasesDep) -> PurchasesDashboard:
    """The owner, and only the owner.

    **Two sections and not one**, which is the whole authorisation decision of
    this endpoint. `DASHBOARD` keeps purchasing out of the tablero (RF-08 of
    009) and `PURCHASE_INVOICES` keeps sales out of the invoices (RF-10 of 002):
    asking for either alone would hand one of the two a screen its role was
    written to exclude. Whoever passes both is the owner, which is exactly whose
    dashboard the guía visual draws in `3b`.

    No window: the four numbers are questions about today, and the cut says so
    (`PurchasesDashboard`).
    """
    return await service.dashboard()
