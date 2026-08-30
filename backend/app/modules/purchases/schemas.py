"""Purchases schemas: the HTTP contract of the invoices, the register and the calendar."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.purchases.models import (
    DueDateOrigin,
    InvoiceReviewState,
    PaymentOrigin,
    PaymentState,
    SupplierAliasSource,
)

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
    created_at: datetime


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

    `excluded` is not a footnote: an invoice in review or flagged as
    inconsistent is **left out** of the totals, and how many were left out
    travels beside the number (RF-22, RF-23 of 004; RF-28 of 005).
    """

    supplier_id: int
    invoiced: Decimal
    paid: Decimal
    owed: Decimal
    invoices: int
    excluded: int
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
    document: InvoiceDocumentRead | None = None


class InvoiceList(BaseModel):
    """A page of invoices, with what it left out of its own counting."""

    items: list[InvoiceRead]
    total: int
    skip: int
    limit: int


class InvoiceReviewResolution(BaseModel):
    """What a person decided about an invoice held for review.

    `supplier_id` says who it is. `remember` is what turns that decision into a
    saved spelling, so the next invoice written the same way does not ask again
    (RF-31, RF-47 of 004).
    """

    supplier_id: int | None = None
    remember: bool = True
    # Used when the decision is about a duplicate rather than about a supplier.
    action: str | None = None


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
    days_in_status: int = 0
    days_since_ordered: int = 0
    is_stalled: bool = False
    repeat_of_order_id: int | None = None
    repeat_of_number: str | None = None
    repeat_dismissed_at: datetime | None = None


class PurchaseOrderList(BaseModel):
    """A page of orders, with the counts the screen shows beside it."""

    items: list[PurchaseOrderRead]
    total: int
    per_status: dict[str, int]
    stalled: int


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
