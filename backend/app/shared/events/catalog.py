"""The shared vocabulary of domain events.

Events live here, not inside the module that publishes them, and the reason is
the boundary rule itself: if `billing` had to import `purchasing.events` to
subscribe to one of its events, the two modules would be coupled again — by the
import that the rule forbids. A shared catalog is the price of modules that
genuinely do not know about each other.

The consequence to accept: this file is a public vocabulary. Adding an event is
a decision about the language of the business, and it belongs in `plan.md`.

Rules for an event:
- **Past tense.** An event reports something that already happened and cannot be
  refused. `InvoiceRegistered`, not `RegisterInvoice`.
- **Immutable.** Frozen dataclasses: a handler never rewrites what it received.
- **Identifiers, not entities.** An event carries ids and plain values, never a
  SQLAlchemy model — models are private to their module.
"""

import enum
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.shared.sections import BusinessSection


class AuditAction(enum.StrEnum):
    """What a manual change did to the datum it touched.

    One vocabulary rather than four events. Four — created, updated, corrected,
    correction reverted — would be four handlers writing into the same table,
    and the log would have four doors instead of one. The distinction survives
    as a field, typed, in `shared/` so both the event and the row that stores it
    read it from the same place.
    """

    CREATED = "CREATED"
    UPDATED = "UPDATED"
    CORRECTED = "CORRECTED"
    CORRECTION_REVERTED = "CORRECTION_REVERTED"


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Base class for every event that crosses a module boundary."""

    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC), kw_only=True)


# ── identity ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class UserRegistered(DomainEvent):
    """A user account was created.

    It carries the phone because that is where an alert is delivered (RF-44 of
    007), and whoever delivers one cannot ask `identity` for it without
    importing it. Like `UserInvited`, this is an in-process event that is never
    persisted; unlike it, it carries no credential.
    """

    user_id: int
    email: str
    role: str
    phone: str = ""


@dataclass(frozen=True, slots=True)
class UserDeactivated(DomainEvent):
    """A user account was disabled and can no longer authenticate."""

    user_id: int


@dataclass(frozen=True, slots=True)
class UserReactivated(DomainEvent):
    """A user account was enabled again and was invited to set a new password."""

    user_id: int


@dataclass(frozen=True, slots=True)
class UserRoleChanged(DomainEvent):
    """A user's role changed, so what they may reach changed with it.

    And with it, which alerts are theirs: the routing of 007 is by role, so
    whoever keeps a list of recipients has to hear about this.
    """

    user_id: int
    previous_role: str
    role: str


@dataclass(frozen=True, slots=True)
class UserInvited(DomainEvent):
    """A person was invited to set the password of their own access.

    Carries the token because a message without it is useless, and the module
    that delivers it cannot ask identity for it without importing it. The bus
    is in-process and the event is never persisted: **it must never be
    logged**, whole or in part.
    """

    user_id: int
    phone: str
    name: str
    token: str
    expires_at: datetime
    # NEW_ACCESS or REACTIVATION: the same mechanism, a different sentence.
    reason: str


@dataclass(frozen=True, slots=True)
class PasswordResetRequested(DomainEvent):
    """Somebody asked to recover their access. Carries the token, like `UserInvited`."""

    user_id: int
    phone: str
    name: str
    token: str
    expires_at: datetime


# ── operations ───────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class JobRunFailed(DomainEvent):
    """A background job finished in failure."""

    job_run_id: int
    job_name: str
    message: str


@dataclass(frozen=True, slots=True)
class JobRunSucceeded(DomainEvent):
    """A background job finished successfully.

    Symmetric to `JobRunFailed`, and published by the module that owns the work
    rather than by `operations`: the extraction task is the only one that knows
    it got to the end, and it cannot call `operations` to say so.
    """

    job_run_id: int
    job_name: str


# ── the price update pipeline ────────────────────────────────────────────────
#
# Five modules that do not know each other, chained by the events below:
#
#   portal ──PriceListExtracted──► ingestion ──PriceListNormalized──► catalog
#      ▲                               │                                │
#      │                    PriceRowsQuarantined              UnknownProductsObserved
#      │                               ▼                      KnownProductsMissing
#   ProductsRegistered ◄── catalog     triage ◄────────────────────────┘
#
# Every payload is flat: identifiers, strings, numbers and frozen tuples of
# small dataclasses. Never a SQLAlchemy model (`GEN-08`).


@dataclass(frozen=True, slots=True)
class NormalizedPriceRow:
    """One row of the daily list that could be interpreted.

    The last three fields carry what the list has always said and nobody read
    yet: the category the supplier wrote, its subcategory, and the stock of the
    day. They arrive with a default so every caller that already builds this
    event keeps compiling — the price update of `001` never mentions them.
    """

    staging_row_id: int
    product_code: str
    description: str
    price: Decimal
    currency: str
    # Exactly as the supplier wrote them. Interpreting them is `008`, and the
    # catalog does it against a table of equivalences, never by guessing.
    category_raw: str | None = None
    subcategory_raw: str | None = None
    # The photograph of the day, which is what the stock cut of `009` compares
    # between the start and the end of a period.
    stock: int | None = None


@dataclass(frozen=True, slots=True)
class QuarantinedRow:
    """One row that could not be interpreted, with what a person needs to read it."""

    staging_row_id: int
    reason: str
    excerpt: str
    product_code: str | None = None


@dataclass(frozen=True, slots=True)
class UnknownProduct:
    """A product the catalog does not know, held back instead of created."""

    staging_row_id: int
    product_code: str
    description: str
    price: Decimal


@dataclass(frozen=True, slots=True)
class MissingProduct:
    """A known product that stopped appearing in the list."""

    product_id: int
    product_code: str
    description: str


@dataclass(frozen=True, slots=True)
class RegisteredProduct:
    """A product the catalog just started to know."""

    product_id: int
    product_code: str


@dataclass(frozen=True, slots=True)
class NormalizedHistoryPoint:
    """One point of the history the portal already publishes for a product."""

    staging_row_id: int
    price: Decimal
    changed_at: datetime


# ── portal ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PriceListExtracted(DomainEvent):
    """The daily price list was downloaded and stored verbatim in `raw`.

    It carries the bytes as well as the identifier. `ingestion` normalises them
    and cannot read `raw.portal_document`, which belongs to `portal`: the row is
    the audit trail (Artículo III), the payload is how the next step gets its
    input without crossing the boundary.
    """

    raw_document_id: int
    content_hash: str
    content: bytes
    content_type: str
    fetched_at: datetime
    job_run_id: int | None = None


@dataclass(frozen=True, slots=True)
class ProductHistoryExtracted(DomainEvent):
    """The history screen of one product was read and stored verbatim in `raw`."""

    raw_document_id: int
    product_code: str
    content_hash: str
    content: bytes


# ── ingestion ────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PriceListNormalized(DomainEvent):
    """The rows of a list that could be typed, as one batch.

    One event per batch, not one per row: a hundred publications inside the same
    transaction would be a hundred handler dispatches for no benefit.
    """

    batch_id: int
    raw_document_id: int
    rows: tuple[NormalizedPriceRow, ...]
    # Every product code the file carried, the quarantined rows included. A row
    # that could not be read is **not** a product that stopped coming, and
    # without this the catalog could not tell the two apart (RF-28).
    seen_codes: tuple[str, ...] = ()
    quarantined: int = 0
    job_run_id: int | None = None


@dataclass(frozen=True, slots=True)
class PriceRowsQuarantined(DomainEvent):
    """Rows of a list that could not be interpreted, set aside for a person."""

    batch_id: int
    cases: tuple[QuarantinedRow, ...]


@dataclass(frozen=True, slots=True)
class PriceHistoryNormalized(DomainEvent):
    """The points of a product's published history that could be typed."""

    product_code: str
    points: tuple[NormalizedHistoryPoint, ...]


@dataclass(frozen=True, slots=True)
class PriceHistoryRowsQuarantined(DomainEvent):
    """Points of a published history that could not be interpreted."""

    product_code: str
    cases: tuple[QuarantinedRow, ...]


# ── catalog ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ProductPricesUpdated(DomainEvent):
    """A batch of prices was applied to the products the catalog knows."""

    batch_id: int
    updated: int
    unchanged: int
    highlighted: int
    quarantined: int = 0
    job_run_id: int | None = None


@dataclass(frozen=True, slots=True)
class UnknownProductsObserved(DomainEvent):
    """The list brought products the catalog does not know. None was created."""

    batch_id: int
    cases: tuple[UnknownProduct, ...]


@dataclass(frozen=True, slots=True)
class KnownProductsMissing(DomainEvent):
    """Known products that did not come in this list. Their last price is kept."""

    batch_id: int
    products: tuple[MissingProduct, ...]


@dataclass(frozen=True, slots=True)
class ProductsRegistered(DomainEvent):
    """Products the catalog started to know, for the first time."""

    batch_id: int
    products: tuple[RegisteredProduct, ...]


# ── triage ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class QuarantineCaseResolved(DomainEvent):
    """A person decided what to do with a case, and the decision became a rule."""

    case_id: int
    kind: str
    decision: dict[str, Any]
    payload: dict[str, Any]
    rule_id: int | None
    matcher: dict[str, Any]
    decided_by_user_id: int
    decided_at: datetime


@dataclass(frozen=True, slots=True)
class QuarantineRuleRevoked(DomainEvent):
    """A learned rule was left without effect, so its cases come back."""

    rule_id: int
    kind: str
    matcher: dict[str, Any]
    decision: dict[str, Any]


# ── operations ───────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PriceUpdateStalled(DomainEvent):
    """Two scheduled runs in a row went by without a successful update.

    Published once per interruption: whoever holds the history of `JobRun` is
    the only one that can tell a new interruption from the same one.
    """

    consecutive_failures: int
    last_success_at: datetime | None
    reason: str


@dataclass(frozen=True, slots=True)
class PriceUpdateRecovered(DomainEvent):
    """The price update started working again after an interruption."""

    recovered_at: datetime


@dataclass(frozen=True, slots=True)
class BusinessParameterChanged(DomainEvent):
    """The owner changed a business parameter.

    The parameters live in `operations`, and a module that needs one keeps its
    own projection fed by this event rather than reading somebody else's table.
    """

    key: str
    value: Any


# ── manual changes, in any module ────────────────────────────────────────────
#
# The two events of the platform operating on itself. Neither belongs to a
# module: whoever edits a datum by hand publishes the first, and whoever owns a
# datum the portal contradicted publishes the second.


@dataclass(frozen=True, slots=True)
class ManualChangeRecorded(DomainEvent):
    """Somebody changed a datum by hand, and the log has to say so.

    Published by the module that owns the datum, consumed by `operations`,
    which turns it into a row. The publisher never learns that a log exists,
    and `operations` never learns whose datum it was — the boundary used in
    favour instead of worked around.

    The handler runs in the publisher's transaction, so a change without its
    record does not exist: if writing the row fails, the edit fails with it
    (`GEN-09`).

    Values travel as plain JSON — a price, a date and a description have to fit
    the same two columns, and an event never carries a model (`GEN-08`).
    """

    entity_type: str
    entity_id: str
    action: AuditAction
    actor_user_id: int
    section: BusinessSection
    field: str | None = None
    old_value: Any = None
    new_value: Any = None
    reason_code: str | None = None
    reason_detail: str | None = None


@dataclass(frozen=True, slots=True)
class CorrectionConflicted(DomainEvent):
    """The portal came back with something other than what it had said.

    The correction is **not** overwritten (RF-28): the module that owns the
    datum marks the conflict and says so here, and the owner is told without
    having to be looking at that screen (RF-29).
    """

    entity_type: str
    entity_id: str
    field: str
    correction_id: int
    original_value: Any
    corrected_value: Any
    incoming_value: Any


# ── the categories of the catalog (008) ──────────────────────────────────────
#
# The written form of a category is resolved against a table of equivalences,
# never by a normaliser that guesses. What is not in the table is a case for a
# person, and that is the whole feature.


@dataclass(frozen=True, slots=True)
class UnknownCategory:
    """A written form of a category no equivalence resolves.

    It carries the products it affects and not one product: a hundred rows of
    the same list written the same way are **one** question, and asking it a
    hundred times would be the queue failing at its own job.
    """

    category_text: str
    product_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UnknownCategoryObserved(DomainEvent):
    """The list brought written forms of a category the catalog cannot resolve.

    Symmetric to `UnknownProductsObserved`: the catalog says what it could not
    place, and whoever runs the review queue decides whether to open a case.
    """

    batch_id: int
    cases: tuple[UnknownCategory, ...]


@dataclass(frozen=True, slots=True)
class QuarantineRuleRedecided(DomainEvent):
    """A rule in force was pointed at a different decision, and stays in force.

    It is **not** a revocation: nothing goes back to the queue. Whoever
    projected the rule re-points what it had resolved (RF-28, RF-29 of 008),
    and the record keeps both who created it and who corrected it.
    """

    rule_id: int
    kind: str
    matcher: dict[str, Any]
    decision: dict[str, Any]
    previous_decision: dict[str, Any]
    decided_by_user_id: int


# ── purchases: invoices and the supplier register (004) ──────────────────────
#
# The same one-way pipeline as the price list, with two more sections of the
# portal plugged into it:
#
#   portal ──InvoiceListExtracted──► ingestion ──InvoicesNormalized──► purchases
#      │                                  │                                │
#      ├──InvoiceFileExtracted────────────┤                    InvoicesNeedingReview
#      └──SupplierLedgerExtracted─────────┴──SuppliersNormalized──────────►│
#                                                                         ▼
#                                                                      triage


@dataclass(frozen=True, slots=True)
class InvoiceListExtracted(DomainEvent):
    """The invoices screen was read and stored verbatim in `raw`."""

    raw_document_id: int
    content: bytes
    fetched_at: datetime
    job_run_id: int | None = None


@dataclass(frozen=True, slots=True)
class InvoiceFileExtracted(DomainEvent):
    """One invoice document was downloaded and stored verbatim in `raw`.

    `file_kind` is what the table said it is — `PDF`, `PDF (escaneado)`,
    `Excel` — and it decides which reader gets to try first. It travels because
    the reader cannot ask the portal a second time (Artículo I).
    """

    raw_document_id: int
    invoice_number: str
    content: bytes
    content_type: str
    file_kind: str


@dataclass(frozen=True, slots=True)
class SupplierLedgerExtracted(DomainEvent):
    """The current-account screen was read, with every supplier already expanded.

    It is the only screen of the portal that publishes the register: eight rows,
    and behind each one the tax id, the email, the phone and the payment term.
    """

    raw_document_id: int
    content: bytes
    job_run_id: int | None = None


@dataclass(frozen=True, slots=True)
class NormalizedSupplier:
    """One card of the supplier register, as far as it could be read."""

    legal_name: str
    tax_id: str | None = None
    email: str | None = None
    phone: str | None = None
    # `45 dias` on the screen. It is what the due date of an invoice is
    # calculated from (RF-26 of 005), and never a date the document carries.
    payment_term_days: int | None = None
    balance: Decimal | None = None


@dataclass(frozen=True, slots=True)
class SuppliersNormalized(DomainEvent):
    """The supplier register, typed. It is the padrón: nothing outside it exists."""

    suppliers: tuple[NormalizedSupplier, ...]
    raw_document_id: int | None = None


@dataclass(frozen=True, slots=True)
class NormalizedInvoice:
    """One row of the invoices screen, typed.

    Everything the table publishes travels, including what `005` reads —
    `paid`, `balance`, `portal_payment_status`, `receipt_issued` — because the
    screen is read once and interpreting it twice would be two truths.
    """

    staging_row_id: int
    number: str
    supplier_text: str
    issued_on: date
    total: Decimal
    due_on: date | None = None
    receipt_issued: bool = False
    paid: Decimal = Decimal(0)
    balance: Decimal | None = None
    # What the portal *says* the payment state is. It is kept and shown, and it
    # never decides: the state comes from the payments imputed (RF-45 of 005).
    portal_payment_status: str | None = None
    file_kind: str | None = None
    product_code: str | None = None


@dataclass(frozen=True, slots=True)
class InvoicesNormalized(DomainEvent):
    """The rows of the invoices screen that could be typed, as one batch."""

    batch_id: int
    raw_document_id: int
    invoices: tuple[NormalizedInvoice, ...]
    quarantined: int = 0
    job_run_id: int | None = None


@dataclass(frozen=True, slots=True)
class InvoiceRowsQuarantined(DomainEvent):
    """Rows of the invoices screen that could not be typed."""

    batch_id: int
    cases: tuple[QuarantinedRow, ...]


@dataclass(frozen=True, slots=True)
class InvoiceFileRead(DomainEvent):
    """What the document itself said, field by field, next to what the table said.

    `agrees` is the signal the whole feature rests on: when the document and the
    table say the same thing the invoice is certainty, and when they disagree —
    or the document could not be read at all — it goes to a person with the
    excerpt in view (RF-27, RF-29, RF-30 of 004).
    """

    invoice_number: str
    raw_document_id: int
    readable: bool
    agrees: bool
    excerpt: str
    reason: str | None = None
    number: str | None = None
    issued_on: date | None = None
    total: Decimal | None = None
    supplier_text: str | None = None
    # The issuer's tax id when the document printed one that is not the
    # client's. `purchases` identifies with it against the register (RF-11).
    supplier_tax_id: str | None = None
    # The document itself. It travels so `purchases` can keep its own copy and
    # serve it back to whoever opens the invoice (RF-04): the module cannot read
    # `raw`, which belongs to `portal`, and a projection fed by an event is what
    # the Artículo IV prescribes for exactly this.
    content: bytes | None = None
    content_type: str | None = None


@dataclass(frozen=True, slots=True)
class InvoiceReviewCase:
    """An invoice held back because nobody can responsibly decide it alone."""

    invoice_id: int
    number: str
    reason: str
    supplier_text: str
    excerpt: str = ""
    # What the resolution has to match on, when the decision is about a way of
    # writing a supplier's name rather than about this one invoice.
    supplier_key: str | None = None
    # Whether this invoice has just been registered and its file has not been
    # fetched yet. A held invoice needs its document more than a resolved one
    # does — it is the evidence the person deciding looks at (RF-30), and the
    # only place a supplier tax id can come from (RF-11) — and an invoice that
    # merely arrived again already has it.
    needs_document: bool = False


@dataclass(frozen=True, slots=True)
class InvoicesNeedingReview(DomainEvent):
    """Invoices whose supplier is ambiguous, outside the register, or duplicated."""

    cases: tuple[InvoiceReviewCase, ...]
    batch_id: int | None = None


@dataclass(frozen=True, slots=True)
class RegisteredInvoice:
    """An invoice the platform started to know, with its supplier resolved."""

    invoice_id: int
    supplier_id: int
    number: str
    issued_on: date
    total: Decimal
    due_on: date | None = None


@dataclass(frozen=True, slots=True)
class InvoicesRegistered(DomainEvent):
    """Invoices that entered the business model with a supplier of the register."""

    invoices: tuple[RegisteredInvoice, ...]
    batch_id: int | None = None


# ── payments and receipts (005) ──────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class NormalizedPayment:
    """One movement of the current account that is a payment, typed.

    `references` is a tuple because one voucher can name more than one invoice,
    and that is precisely the case the system refuses to split on its own
    (RF-12 of 005).
    """

    staging_row_id: int
    supplier_text: str
    references: tuple[str, ...]
    paid_on: date
    amount: Decimal
    external_id: str


@dataclass(frozen=True, slots=True)
class PaymentsNormalized(DomainEvent):
    """The payment vouchers the current account publishes, typed."""

    batch_id: int
    raw_document_id: int
    payments: tuple[NormalizedPayment, ...]
    quarantined: int = 0


@dataclass(frozen=True, slots=True)
class PaymentReviewCase:
    """A voucher that cannot be imputed without somebody deciding first."""

    payment_id: int
    reason: str
    reference: str
    supplier_text: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class PaymentsNeedingReview(DomainEvent):
    """Vouchers held back: unknown invoice, several invoices, or a possible twin."""

    cases: tuple[PaymentReviewCase, ...]


@dataclass(frozen=True, slots=True)
class ReceiptIssued(DomainEvent):
    """A reception receipt was issued for an invoice, with its own number."""

    receipt_id: int
    invoice_id: int
    number: str
    issued_by_user_id: int
    issued_at: datetime


@dataclass(frozen=True, slots=True)
class ReceiptVoided(DomainEvent):
    """A reception receipt was annulled, and the invoice is without one again."""

    receipt_id: int
    invoice_id: int
    voided_by_user_id: int


@dataclass(frozen=True, slots=True)
class InvoiceDueSoon(DomainEvent):
    """An invoice with no receipt is about to reach its due date (RF-38 of 005).

    Published once per due date: whoever holds the invoice is the only one that
    can tell a new deadline from the same one already announced (RF-39).
    """

    invoice_id: int
    number: str
    supplier_name: str
    due_on: date
    days_ahead: int
    total: Decimal


# ── the calendar of due dates (006) ──────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class DueDateChanged(DomainEvent):
    """Something on the calendar changed, and other screens are looking at it.

    One event for the four verbs — added, moved, corrected, removed — because
    what the screens do about it is the same: refresh the day it touched, and
    say who did it (RF-31, RF-33 of 006).
    """

    due_date_id: int
    action: str
    actor_user_id: int
    actor_name: str
    on_date: date | None = None
    previous_date: date | None = None
    invoice_id: int | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class InvoiceDueDateRescheduled(DomainEvent):
    """The due date of an invoice moved, and the deadline to issue its receipt with it.

    Only when it moved **before** falling due: an invoice already overdue keeps
    its original date for everything that matters — the receipt stays refused
    and the supplier's delay is still measured against it (RF-28, RF-29 of 006).
    """

    invoice_id: int
    previous_due_on: date | None
    due_on: date
    was_overdue: bool
    actor_user_id: int


# ── purchase orders and the supplier inbox (007) ─────────────────────────────


@dataclass(frozen=True, slots=True)
class PurchaseOrdersExtracted(DomainEvent):
    """The purchase orders screen was read and stored verbatim in `raw`."""

    raw_document_id: int
    content: bytes
    fetched_at: datetime
    job_run_id: int | None = None


@dataclass(frozen=True, slots=True)
class NormalizedPurchaseOrder:
    """One row of the purchase orders screen, typed."""

    staging_row_id: int
    number: str
    ordered_on: date
    supplier_text: str
    product_code: str | None
    product_text: str
    quantity: int | None
    amount: Decimal | None
    status_text: str


@dataclass(frozen=True, slots=True)
class PurchaseOrdersNormalized(DomainEvent):
    """The purchase orders that could be typed, as one batch."""

    batch_id: int
    raw_document_id: int
    orders: tuple[NormalizedPurchaseOrder, ...]
    quarantined: int = 0
    job_run_id: int | None = None


@dataclass(frozen=True, slots=True)
class PurchaseOrderRowsQuarantined(DomainEvent):
    """Rows of the purchase orders screen that could not be typed."""

    batch_id: int
    cases: tuple[QuarantinedRow, ...]


@dataclass(frozen=True, slots=True)
class SupplierMessagesExtracted(DomainEvent):
    """The portal inbox was read and stored verbatim in `raw`."""

    raw_document_id: int
    content: bytes
    fetched_at: datetime
    job_run_id: int | None = None


@dataclass(frozen=True, slots=True)
class NormalizedMessage:
    """One message of the portal inbox, typed."""

    staging_row_id: int
    external_id: str
    received_at: datetime
    sender_text: str
    kind_text: str
    subject: str
    body: str
    already_read: bool = False


@dataclass(frozen=True, slots=True)
class SupplierMessagesNormalized(DomainEvent):
    """The messages of the inbox that could be typed, as one batch."""

    batch_id: int
    raw_document_id: int
    messages: tuple[NormalizedMessage, ...]
    # True on the run that finds the inbox already full at start-up: those
    # messages are registered as pending and nobody is woken up for them
    # (RF-47 of 007).
    first_run: bool = False


@dataclass(frozen=True, slots=True)
class AlertDeliveryFailed(DomainEvent):
    """An alert could not be delivered, and somebody has to be able to see it.

    RF-38 of 007 asks the failure to be recorded **and shown on the messages
    screen**, and the screen already draws it — what was missing was anything
    writing it. The delivery fails inside a Celery task in the worker, which
    knows a phone and a text and nothing else, and `notifications` may not call
    `messaging` (Artículo IV). So the fact travels as what it is: a fact.

    `message_id` is nullable because the same task also delivers the due-date
    alerts of 005, which have no inbox message behind them. Those publish too
    and nobody records them — 005 has no RF-38 of its own, and the event is
    ready for the day it does.
    """

    kind: str
    reason: str
    message_id: int | None = None


@dataclass(frozen=True, slots=True)
class SupplierMessageReceived(DomainEvent):
    """A message worth waking somebody up for just arrived (RF-33, RF-34 of 007)."""

    message_id: int
    kind: str
    supplier_name: str
    subject: str
    body: str
    received_at: datetime


# ── sales, and the numbers the owner reads (009) ─────────────────────────────


@dataclass(frozen=True, slots=True)
class SalesExtracted(DomainEvent):
    """The sales screen was read and stored verbatim in `raw`."""

    raw_document_id: int
    content: bytes
    fetched_at: datetime
    job_run_id: int | None = None


@dataclass(frozen=True, slots=True)
class NormalizedSale:
    """One sales record, as far as it could be read.

    **A record the parser could not read whole travels too**, with the reason it
    could not, and that is what RF-16 to RF-19 of 009 ask for: a sale without a
    date, with a date that does not exist, without a total or with a negative
    quantity is *held*, not dropped. Leaving it in `staging` would keep it out
    of every screen and out of every «this is what I left out» count, which is
    the one thing the feature exists to prevent.

    So `sold_on` and `total` are nullable here, exactly as they are in the table
    this ends up in. `reason` is `None` for a record that reads whole.
    """

    staging_row_id: int
    code: str
    # The code with its spelling differences removed, which is what says two
    # records are the same sale (RF-10 of 009). Empty when the record arrived
    # without a code: there is nothing to group it by, and it is held on its own.
    code_key: str
    sold_on: date | None
    product_code: str | None
    quantity: int | None
    total: Decimal | None
    # Why the parser could not read it whole, in the words a person reads
    # (RF-23). `None` means it read whole.
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class SalesNormalized(DomainEvent):
    """The sales records that could be typed, as one batch."""

    batch_id: int
    raw_document_id: int
    sales: tuple[NormalizedSale, ...]
    quarantined: int = 0
    job_run_id: int | None = None


@dataclass(frozen=True, slots=True)
class SaleRowsQuarantined(DomainEvent):
    """Sales records that could not be typed, or that no indicator may add up."""

    batch_id: int
    cases: tuple[QuarantinedRow, ...]


# ── the daily digest, assembled across modules (007) ─────────────────────────
#
# The digest is one message about two modules' business — the messages still
# open and the orders that have not moved — and neither of them may read the
# other, nor may whoever sends it read either.
#
# So it is assembled the way everything else here is: whoever is going to send
# it **asks**, in public, and whoever has something to say answers. The bus is
# in-process and synchronous, so by the time `publish` returns, every module
# that had a line has contributed one.


@dataclass(frozen=True, slots=True)
class DailyDigestRequested(DomainEvent):
    """Somebody is about to send the daily digest and is asking what to put in it."""

    on_date: date


@dataclass(frozen=True, slots=True)
class DailyDigestContribution(DomainEvent):
    """What one module has to say in the digest of the day.

    `pending` is the number that goes in the header, and `lines` are the few
    sentences under it. A module with nothing to report answers with zero and no
    lines — which is a fact worth sending, and different from not answering.
    """

    source: str
    pending: int
    lines: tuple[str, ...] = ()


# ── what the platform sets aside and nobody heard about (011) ────────────────
#
# Three of the four events below fill the same hole in three different places:
# `ingestion` quarantined a row in `staging` and told nobody, so nothing counted
# it, nothing showed it and nobody ever decided about it. That is the one thing
# the Artículo II forbids — setting a datum aside in silence is discarding it
# with extra steps — and it is what the whole 011 exists to close.
#
# They are the same shape as the four quarantine events that already work, and
# deliberately so: `tuple[QuarantinedRow, ...]`, built by the same
# `_quarantined_of` helper, consumed by the same generic queue. A feature that
# had to invent a shape here would be a feature that had misunderstood the one
# that came before.


@dataclass(frozen=True, slots=True)
class SupplierRowsQuarantined(DomainEvent):
    """Rows of the supplier register that could not be typed."""

    raw_document_id: int
    cases: tuple[QuarantinedRow, ...]


@dataclass(frozen=True, slots=True)
class PaymentRowsQuarantined(DomainEvent):
    """Payment records that could not be typed."""

    batch_id: int
    raw_document_id: int
    cases: tuple[QuarantinedRow, ...]


@dataclass(frozen=True, slots=True)
class MessageRowsQuarantined(DomainEvent):
    """Messages of the portal inbox that could not be typed."""

    batch_id: int
    raw_document_id: int
    cases: tuple[QuarantinedRow, ...]


@dataclass(frozen=True, slots=True)
class QuarantinedSourceResolved(DomainEvent):
    """What opened a case got resolved on the screen it belongs to (RF-20).

    The fourth is not about opening a case but about **closing one honestly**.
    A payment held in review and a sale nobody could add up both have their own
    screen, and the work usually gets done there. Asking the person to close the
    triage case afterwards is the same work twice, and the day they forget, the
    list of pending things is lying.

    So whoever resolves it says so out loud, and `triage` listens. It carries
    identifiers and a label and never the entity (`GEN-08`), and the publisher
    does not know who is listening — which is what keeps `purchases` and `sales`
    from ever having to import `triage` (Artículo IV).

    `resolved_where` is for the person reading the closed case later: it says on
    which screen the work happened. **No name of a person travels**, and that is
    the decision the spec took: the record of who did the work belongs to the
    screen where it was done, and copying it here would create a second version
    of it that can drift.
    """

    # The `kind` of the case to close, and the same key its fingerprint was
    # built from — not a reconstruction: a key rebuilt loosely would close a
    # case nobody resolved.
    kind: str
    key: str
    resolved_where: str


@dataclass(frozen=True, slots=True)
class QuarantinedSourceReopened(DomainEvent):
    """The work that had closed a case got undone on its own screen (RF-24).

    The mirror of `QuarantinedSourceResolved`, and the reason it exists is that
    a rule the client signed only holds in both directions: *hay una sola
    verdad sobre si algo sigue pendiente*. A queue that knows how to close
    itself and not how to reopen tells the truth exactly until somebody changes
    their mind — and the sales screen lets them, because 009 promised it
    (RF-35).

    Same shape and same discipline as its sibling: identifiers and nothing
    else, the publisher does not know who listens, and the key is the one the
    case was opened with rather than a reconstruction.
    """

    kind: str
    key: str
    reopened_where: str
