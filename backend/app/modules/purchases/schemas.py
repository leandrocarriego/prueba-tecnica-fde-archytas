"""Purchases schemas: the HTTP contract of the invoices, the register and the calendar."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.purchases.models import (
    DueDateOrigin,
    InvoiceReviewState,
    OrderReviewState,
    PaymentOrigin,
    PaymentState,
    RecordOrigin,
    SupplierAliasSource,
)
from app.shared.corrections import CorrectionStatus

DETAIL_MAX = 1000


class SupplierAliasRead(BaseModel):
    """One way a supplier's name arrives written (RF-10, RF-51 of 004)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_id: int
    text_original: str
    text_normalized: str
    source: SupplierAliasSource
    rule_id: int | None
    created_by_user_id: int | None
    # Resuelto por la ruta, no por el servicio: `purchases` no puede nombrar a
    # nadie sin importar `identity` (RF-51).
    created_by_name: str | None = None
    created_at: datetime


class SupplierCorrectionMark(BaseModel):
    """A field of a supplier's card that a person corrected by hand.

    The same shape the catalog gives a corrected price, because it answers the
    same two questions on the screen: which value is a person's rather than the
    portal's, and what the portal said underneath it (RF-18, RF-19 of 004).

    `conflict_value` is what the portal came back with **after** the correction
    and was not allowed to write. The screen shows it beside the corrected
    value as a difference to look at, never as the value in force.
    """

    correction_id: int
    field: str
    portal_value: Any
    corrected_value: Any
    status: CorrectionStatus
    conflict_value: Any | None = None


class SupplierRead(BaseModel):
    """A supplier of the register, with what is missing marked as missing.

    `missing` is the list of fields the portal has not published for them, and
    it is shown rather than filled in: RF-15 and RF-20 ask the screen to say
    *falta*, and a blank looks like a value nobody bothered to read.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    legal_name: str
    tax_id: str | None
    email: str | None
    phone: str | None
    payment_term_days: int | None
    balance: Decimal | None
    missing: list[str] = Field(default_factory=list)
    aliases: list[SupplierAliasRead] = Field(default_factory=list)
    invoice_count: int = 0
    # The contact fields somebody corrected by hand, and the ones the portal
    # later contradicted (RF-18, RF-19 of 004). An empty list is a card exactly
    # as `/estado-cuenta` published it.
    corrections: list[SupplierCorrectionMark] = Field(default_factory=list)


class SupplierList(BaseModel):
    """The register (RF-08, RF-24 of 004)."""

    items: list[SupplierRead]
    total: int


class SupplierContactWrite(BaseModel):
    """The contact details of a supplier, corrected by hand (RF-16 of 004)."""

    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    payment_term_days: int | None = Field(default=None, ge=0, le=365)
    reason_code: str
    reason_detail: str | None = Field(default=None, max_length=DETAIL_MAX)


class AgingBucket(BaseModel):
    """One band of a supplier's debt by age (RF-25 of 005)."""

    label: str
    amount: Decimal
    invoices: int


class SupplierTotalsRead(BaseModel):
    """What a supplier was invoiced, what was paid, and what is still owed.

    What was **left out** is not a footnote, and it is not one number either.
    RF-23 asks for one thing in particular — how many invoices the total leaves
    out **because they are in review** — and adding to it the ones that fall
    outside the chosen period made that number mean something else as soon as
    somebody chose a period: «quedaron afuera 12» over a supplier with 3 held
    invoices and 9 from last year is true about nothing anybody asked.

    So the three reasons are counted apart and `excluded` stays as their sum,
    which is what a screen shows when nobody picked a period.
    """

    supplier_id: int
    invoiced: Decimal
    paid: Decimal
    owed: Decimal
    invoices: int
    excluded: int
    # In review, waiting for a person: the number RF-23 names.
    excluded_in_review: int = 0
    # Paid more than they are worth: RF-28 of 005, a different question.
    excluded_inconsistent: int = 0
    # Simply not in the period asked for. Not a problem with the invoice.
    excluded_out_of_period: int = 0
    aging: list[AgingBucket]
    average_delay_days: Decimal | None
    since: date | None = None
    until: date | None = None


class PaymentRead(BaseModel):
    """One payment of an invoice, with where it came from (RF-10, RF-20 of 005)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int | None
    supplier_id: int | None
    amount: Decimal
    paid_on: date
    origin: PaymentOrigin
    state: PaymentState
    reference: str | None
    supplier_text: str | None
    review_reason: str | None
    created_by_user_id: int | None
    created_at: datetime
    voided_by_user_id: int | None
    voided_at: datetime | None


class PaymentWrite(BaseModel):
    """A payment somebody registers by hand (RF-18 of 005)."""

    amount: Decimal = Field(gt=0)
    paid_on: date
    reference: str | None = Field(default=None, max_length=255)
    # RF-21: a payment over the outstanding balance is warned about before it is
    # registered. The warning is the refusal; this is how the caller says they
    # read it and meant it.
    confirm_over_balance: bool = False


class ReceiptRead(BaseModel):
    """The reception receipt of an invoice (RF-29, RF-36, RF-47 of 005)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    number: str
    issued_by_user_id: int
    issued_at: datetime
    voided_by_user_id: int | None
    voided_at: datetime | None
    document: str | None = None


class InvoiceDocumentRead(BaseModel):
    """What the document of the invoice said, next to what the table said."""

    model_config = ConfigDict(from_attributes=True)

    readable: bool
    agrees: bool
    excerpt: str | None
    reason: str | None
    read_number: str | None
    read_issued_on: date | None
    read_total: Decimal | None
    read_supplier_text: str | None
    # The issuer's tax id, when the document printed one that is not the
    # client's. It is what identified the supplier without anybody deciding
    # (RF-11), so the screen can say that is what happened.
    read_supplier_tax_id: str | None = None


class InvoiceRead(BaseModel):
    """An invoice as every screen of the feature shows it.

    The payment state is **computed** from the payments imputed and never taken
    from what the portal reports (RF-45 of 005). What the portal says travels
    beside it, and when the two disagree the invoice says so (RF-46).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    issued_on: date
    total: Decimal
    supplier_id: int | None
    supplier_text: str
    supplier_name: str | None = None
    due_on: date | None
    original_due_on: date | None
    review_state: InvoiceReviewState
    review_reason: str | None
    # De dónde salió: del portal, o de una persona que la escribió sobre una
    # fila que el portal publicó ilegible. Viaja hasta la pantalla porque el
    # Artículo I lo pide: un dato que escribió alguien no se muestra como algo
    # que publicó el origen.
    origin: RecordOrigin = RecordOrigin.PORTAL
    arrival_count: int
    file_kind: str | None
    product_code: str | None
    # Computed, in the order a screen reads them.
    paid: Decimal = Decimal(0)
    balance: Decimal = Decimal(0)
    paid_pct: int = 0
    payment_state: str = "SIN_PAGOS"
    portal_payment_status: str | None = None
    payment_state_disagrees: bool = False
    is_inconsistent: bool = False
    receipt_issued: bool = False
    receipt_number: str | None = None
    is_overdue_without_receipt: bool = False
    # Quién decidió sobre la factura apartada y cuándo (RF-32). Se guardaban en
    # `core.invoice` y no salían de ahí, así que ninguna pantalla podía decir lo
    # que el criterio firmado pide que se lea. El nombre lo resuelve la ruta con
    # `ActorDirectory`: este módulo sabe el id y se detiene ahí.
    resolved_by_user_id: int | None = None
    resolved_by_name: str | None = None
    resolved_at: datetime | None = None
    document: InvoiceDocumentRead | None = None


class InvoiceList(BaseModel):
    """A page of invoices, with what it left out of its own counting."""

    items: list[InvoiceRead]
    total: int
    skip: int
    limit: int


class InvoiceReviewResolution(BaseModel):
    """What a person decided about an invoice held for review.

    Two decisions travel in the same shape because a person takes them in the
    same breath, looking at the same excerpt:

    - **Who it is.** `supplier_id` says which supplier, and `remember` turns
      that into a saved spelling so the next invoice written the same way does
      not ask again (RF-47, RF-49).
    - **What it says.** `number`, `issued_on` and `total` are the header fields
      the document put in doubt. Sending one **corrects** it; leaving it out
      **confirms** what the table published, which is the commoner answer and so
      is the one that costs nothing to give (RF-31).

    Nothing here is a suggestion the platform filled in: an empty field is a
    person saying «what is there is right», never the system deciding for them.
    """

    supplier_id: int | None = None
    remember: bool = True
    number: str | None = Field(default=None, max_length=64)
    issued_on: date | None = None
    total: Decimal | None = Field(default=None, gt=0)


class AliasPreview(BaseModel):
    """How many invoices an assignment would resolve, before it is saved (RF-48)."""

    text_original: str
    supplier_id: int
    invoices: int
    numbers: list[str]


class AliasWrite(BaseModel):
    """A spelling somebody assigns to a supplier (RF-47 of 004)."""

    text: str = Field(min_length=1, max_length=255)
    supplier_id: int


class DueDateChangeRead(BaseModel):
    """One move of an entry of the calendar (RF-23 of 006)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    previous_date: date
    new_date: date
    reason: str | None
    actor_user_id: int
    actor_name: str | None = None
    changed_at: datetime


class DueDateRead(BaseModel):
    """One entry of the calendar, with everything the day shows about it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    on_date: date
    description: str
    amount: Decimal | None
    invoice_id: int | None
    origin: DueDateOrigin
    original_date: date
    was_rescheduled: bool = False
    is_past: bool = False
    supplier_name: str | None = None
    receipt_issued: bool = False
    is_overdue_without_receipt: bool = False
    payment_state: str | None = None
    # Quién lo cargó y cuándo (RF-13). Se guardaban desde el primer día y no
    # salían del backend, así que el criterio firmado —«figura con el nombre de
    # Marcela y la fecha en que lo cargó»— no se podía verificar en pantalla.
    created_by_user_id: int | None = None
    created_by_name: str | None = None
    created_at: datetime | None = None
    changes: list[DueDateChangeRead] = Field(default_factory=list)


class CalendarRead(BaseModel):
    """One month of the calendar (RF-01 to RF-05 of 006)."""

    since: date
    until: date
    items: list[DueDateRead]


class DueDateWrite(BaseModel):
    """An entry somebody adds by hand (RF-12 of 006)."""

    on_date: date
    description: str = Field(min_length=1, max_length=300)
    amount: Decimal | None = None


class DueDateEdit(BaseModel):
    """The description and the amount of a hand-made entry (RF-15 of 006)."""

    description: str | None = Field(default=None, min_length=1, max_length=300)
    amount: Decimal | None = None


class DueDateMove(BaseModel):
    """A move of an entry to another date (RF-19, RF-22, RF-25, RF-42 of 006)."""

    on_date: date
    reason: str | None = Field(default=None, max_length=DETAIL_MAX)
    # Moving something into the past is confirmed before it is applied (RF-25).
    confirm_past: bool = False


class PurchaseOrderRead(BaseModel):
    """One purchase order, with how long it has been watched where it is."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    ordered_on: date
    supplier_id: int | None
    supplier_text: str
    supplier_name: str | None = None
    product_code: str | None
    product_text: str
    quantity: int | None
    amount: Decimal | None
    status_text: str
    status_since: date
    observed_from_start: bool
    # Whether the order could be attributed to a supplier of the register, and
    # why not when it could not (RF-08, RF-50, RF-55). `review_reason` is null
    # for the orders held before the reason was kept: it was never stored, and
    # writing an invented one is what Artículo II forbids.
    review_state: OrderReviewState
    review_reason: str | None = None
    resolved_by_user_id: int | None = None
    resolved_at: datetime | None = None
    days_in_status: int = 0
    days_since_ordered: int = 0
    is_stalled: bool = False
    repeat_of_order_id: int | None = None
    repeat_of_number: str | None = None
    repeat_dismissed_at: datetime | None = None


class OrderResolution(BaseModel):
    """Which supplier of the register a held order is from (RF-54, RF-61 of 007).

    `remember` is what turns the decision into a saved spelling, and it defaults
    to true because that is what the signed spec asks for: the same way of
    writing a name is decided **once** and serves every order and invoice that
    was waiting on it.
    """

    supplier_id: int
    remember: bool = True


class PurchaseOrderList(BaseModel):
    """A page of orders, with the counts the screen shows beside it."""

    items: list[PurchaseOrderRead]
    total: int
    per_status: dict[str, int]
    stalled: int
    # How many are set aside waiting for a person to say whose they are (RF-51).
    held: int = 0


class IncidentRead(BaseModel):
    """An invoice that fell due without its receipt (RF-37, RF-59 of 005)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    opened_on: date
    closed_by_user_id: int | None
    closed_at: datetime | None
    resolution: str | None
    invoice_number: str | None = None
    supplier_name: str | None = None


class IncidentClose(BaseModel):
    """What was done about an incident (RF-57, RF-58 of 005)."""

    resolution: str = Field(min_length=1, max_length=DETAIL_MAX)


class PaymentSplit(BaseModel):
    """One part of a voucher that covers several invoices (RF-53 of 005)."""

    invoice_id: int
    amount: Decimal = Field(gt=0)


class PaymentSplitWrite(BaseModel):
    """How a held voucher splits between invoices.

    The parts have to add up to the voucher exactly (RF-55): a split that does
    not is not a distribution, it is a different amount.
    """

    parts: list[PaymentSplit] = Field(min_length=1)


class CorrectionRead(BaseModel):
    """A value of this module somebody corrected by hand (RF-17 of 004)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: str
    field: str
    portal_value: Any
    corrected_value: Any
    reason_code: str
    reason_detail: str | None
    corrected_by_user_id: int
    corrected_at: datetime
    status: str
    conflict_value: Any | None = None


# --- The owner's dashboard (the purchases cut) -------------------------------


class UpcomingDue(BaseModel):
    """One invoice about to fall due, as the dashboard lists it.

    The balance travels beside the total because they are different questions:
    the total is what the invoice was for, the balance is what is still owed on
    it. A calendar that shows the total of a half-paid invoice is telling
    somebody to pay it twice.
    """

    invoice_id: int
    number: str
    supplier_name: str | None
    # The name as the portal wrote it, for the invoices nobody could attribute
    # yet: they still fall due, and hiding them until somebody resolves the
    # supplier would be the platform deciding not to warn (Artículo II).
    supplier_text: str
    total: Decimal
    balance: Decimal
    due_on: date
    # Negative is already overdue. Computed here and not in the browser: the day
    # this business runs on is Buenos Aires, and a phone in another zone would
    # count a different number of days.
    days_left: int
    receipt_issued: bool
    # Todavía sin confirmar por una persona: la factura está en revisión, así
    # que su vencimiento avisa pero su importe no es una afirmación de esta
    # plataforma. La pantalla lo dibuja punteado, que es lo que el punteado
    # significa en toda la aplicación.
    in_review: bool = False


class PurchasesDashboard(BaseModel):
    """What is owed, what falls due next and what was ordered and never arrived.

    The four cuts of the owner's dashboard that are about purchases, and none of
    them takes a window: «cuánto debo» and «qué vence esta semana» are questions
    about today, and a period control over them would be a control that changes
    nothing (RF-05 gives a window to the cuts that have one).

    What is **left out** travels with the number, like everywhere else: an
    invoice in review or one paid beyond its total does not add to the debt, and
    how many there are is reported rather than buried (RF-23 of 004, RF-16 and
    RF-28 of 005).

    **A sum and a warning are not the same question**, and this cut answers both
    with different rules. `owed` is a sum, so it only adds up what the platform
    can vouch for. `due_soon`, `overdue` and `upcoming` are warnings, and they
    include the invoices in review: a due date arrives whether or not somebody
    resolved who the supplier is, and hiding it until then would be deciding not
    to warn. What travels marked is the amount (`in_review`), not the date.
    """

    # --- What is owed to suppliers
    owed: Decimal
    open_invoices: int
    excluded_in_review: int
    excluded_inconsistent: int

    # --- What falls due within the week
    due_soon_days: int
    due_soon: int
    due_soon_without_receipt: int
    overdue: int

    # --- What was ordered and has not arrived
    orders_pending: int
    orders_stalled: int
    # The parameter the owner set, so the screen can say «con más de N días»
    # instead of hard-coding a number the owner can change (RF-10 of 007).
    stalled_days: int

    # --- The next few due dates, in the order they fall
    upcoming: list[UpcomingDue]
