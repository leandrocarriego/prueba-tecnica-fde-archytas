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

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.modules.identity.dependencies import CurrentUser, Level, Section, require_section
from app.modules.purchases.models import InvoiceReviewState
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
    PaymentRead,
    PaymentSplitWrite,
    PaymentWrite,
    PurchaseOrderList,
    PurchaseOrderRead,
    ReceiptRead,
    SupplierAliasRead,
    SupplierContactWrite,
    SupplierList,
    SupplierRead,
    SupplierTotalsRead,
)
from app.modules.purchases.service import PurchasesService, today_here

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


# --- The invoices (004, 005) ---------------------------------------------


@invoices_router.get(
    "",
    dependencies=[require_section(Section.PURCHASE_INVOICES, Level.READ)],
    summary="The invoices, with every filter of the screen",
)
async def list_invoices(
    service: PurchasesDep,
    skip: SkipParam = 0,
    limit: LimitParam = DEFAULT_PAGE_SIZE,
    q: SearchParam = None,
    supplier_id: Annotated[int | None, Query(description="Only this supplier's")] = None,
    review_state: Annotated[InvoiceReviewState | None, Query(description="By review")] = None,
    payment_state: Annotated[str | None, Query(description="SALDADA, PARCIAL, SIN_PAGOS")] = None,
    due_from: Annotated[date | None, Query(description="Falling due from")] = None,
    due_to: Annotated[date | None, Query(description="Falling due up to")] = None,
    with_receipt: Annotated[bool | None, Query(description="With or without receipt")] = None,
) -> InvoiceList:
    """The owner and purchasing (RF-03, RF-05, RF-39 to RF-46 of 004)."""
    return await service.list_invoices(
        skip=skip,
        limit=limit,
        query=q,
        supplier_id=supplier_id,
        review_state=review_state,
        payment_state=payment_state,
        due_from=due_from,
        due_to=due_to,
        with_receipt=with_receipt,
    )


@invoices_router.get(
    "/{invoice_id}",
    dependencies=[require_section(Section.PURCHASE_INVOICES, Level.READ)],
    summary="One invoice, with what its document said",
)
async def get_invoice(invoice_id: int, service: PurchasesDep) -> InvoiceRead:
    """The owner and purchasing (RF-03, RF-27, RF-39 of 004)."""
    return await service.get_invoice(invoice_id)


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
    service: PurchasesDep, skip: SkipParam = 0, limit: LimitParam = DEFAULT_PAGE_SIZE
) -> InvoiceList:
    """The owner and purchasing (RF-30, RF-34, RF-46 of 004)."""
    return await service.review_queue(skip=skip, limit=limit)


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
    )


# --- The spellings of a supplier's name (004) ----------------------------


@aliases_router.get(
    "",
    dependencies=[require_section(Section.SUPPLIERS, Level.READ)],
    summary="The spellings assigned to a supplier",
)
async def list_aliases(service: PurchasesDep) -> list[SupplierAliasRead]:
    """The owner and purchasing (RF-51 of 004)."""
    return await service.list_aliases()


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
    since: Annotated[date | None, Query(description="First day shown")] = None,
    until: Annotated[date | None, Query(description="Last day shown")] = None,
    without_receipt: Annotated[bool, Query(description="Only what has no receipt")] = False,
    hide_settled: Annotated[bool, Query(description="Hide what is already settled")] = False,
) -> CalendarRead:
    """All three roles: sales consults the calendar and cannot change it (RF-37).

    With no window given it opens on the current month, which is RF-04.
    """
    start, end = _month_of(since, until)
    return await service.calendar(
        since=start, until=end, without_receipt=without_receipt, hide_settled=hide_settled
    )


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
    await service.remove_due_date(due_date_id, actor_user_id=current_user.id)


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
) -> PurchaseOrderList:
    """The owner and purchasing. Sales is refused (RF-09 of 007)."""
    return await service.list_orders(
        skip=skip,
        limit=limit,
        status_text=status_text,
        supplier_id=supplier_id,
        only_stalled=only_stalled,
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

    The **excerpt** of the document, as plain text, and not the bytes the portal
    delivered: `raw` is evidence and is never served to a browser, and what a
    person reviewing needs is what the file said next to what the table said.
    """
    invoice = await service.get_invoice(invoice_id)
    body = "" if invoice.document is None else (invoice.document.excerpt or "")
    return Response(content=body, media_type="text/plain; charset=utf-8")
