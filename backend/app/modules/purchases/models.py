"""Purchases models: the supplier register, the invoices and everything on them.

All in `core`: only what could be interpreted reaches this schema, fed from
`staging` and never straight from `raw`.

Two decisions are worth reading twice.

**A supplier is never created by the platform.** The register comes from
`/estado-cuenta`, which is the only screen of the portal that publishes it, and
an invoice from somebody outside it is set aside rather than turned into a ninth
supplier. The client ruled that out explicitly: the register grows as a decision
of the business.

**A due date is not a column of the invoice.** It is a row of its own, because
it can be moved, and moving it has to keep where it came from. An invoice's due
date is derived from the agreed payment term of its supplier and nothing else
(RF-26 of 005) — never from a date the document happens to print.
"""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.shared.corrections import CorrectionColumns, CorrectionStatus

CORE_SCHEMA = "core"


class SupplierAliasSource(enum.StrEnum):
    """Where a way of writing a supplier's name came from."""

    # Seen in the portal and matched against the register with certainty.
    OBSERVED = "OBSERVED"
    # Somebody decided it, from the review queue.
    LEARNED = "LEARNED"


class InvoiceReviewState(enum.StrEnum):
    """Whether an invoice can be trusted as it stands.

    `PENDING` is not an error: it is an invoice waiting for a person, counted
    and visible, and the run that brought it finished fine without it.
    """

    OK = "OK"
    PENDING = "PENDING"
    RESOLVED = "RESOLVED"


class PaymentOrigin(enum.StrEnum):
    """Whether a payment came from the portal or somebody typed it (RF-20 of 005)."""

    PORTAL = "PORTAL"
    MANUAL = "MANUAL"


class PaymentState(enum.StrEnum):
    """Whether a payment is counted, waiting for a decision, or undone."""

    IMPUTED = "IMPUTED"
    PENDING = "PENDING"
    VOIDED = "VOIDED"


class DueDateOrigin(enum.StrEnum):
    """Whether a due date comes from an invoice or somebody added it (RF-14 of 006)."""

    INVOICE = "INVOICE"
    MANUAL = "MANUAL"


class OrderReviewState(enum.StrEnum):
    """Whether a purchase order could be attributed to a supplier of the register."""

    OK = "OK"
    PENDING = "PENDING"
    RESOLVED = "RESOLVED"


class Supplier(Base):
    """One supplier of the register, as `/estado-cuenta` publishes it.

    The platform never creates one: an invoice from a name outside the register
    goes to review. The register is the padrón, and widening it is a decision of
    the business rather than a side effect of an extraction.
    """

    __tablename__ = "supplier"
    __table_args__ = (
        Index("ix_supplier_legal_name", "legal_name"),
        {"schema": CORE_SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    legal_name: Mapped[str] = mapped_column(String(255), unique=True)
    # Unique when present: two suppliers with one tax id is the portal
    # contradicting itself, not a case of the business. Nullable because the
    # detail of a supplier is only published once its row is expanded, and a
    # row the portal refuses to open leaves us knowing less rather than guessing.
    tax_id: Mapped[str | None] = mapped_column(String(20), default=None, unique=True)
    email: Mapped[str | None] = mapped_column(String(255), default=None)
    phone: Mapped[str | None] = mapped_column(String(50), default=None)
    # `45 dias` on the screen. It is what a due date is calculated from, and the
    # only thing it is calculated from (RF-26 of 005).
    payment_term_days: Mapped[int | None] = mapped_column(Integer, default=None)
    balance: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Supplier id={self.id} name={self.legal_name}>"


class SupplierAlias(Base):
    """One way a supplier's name arrives written, pointing at who it is.

    Twenty-four spellings for eight suppliers, measured. Each one is a row: an
    observed spelling that matched with certainty, or one a person assigned from
    the review queue. `rule_id` is the decision it came from, when it came from
    one, and it is what lets that decision be undone exactly (RF-52, RF-53).
    """

    __tablename__ = "supplier_alias"
    __table_args__ = {"schema": CORE_SCHEMA}

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey(f"{CORE_SCHEMA}.supplier.id", ondelete="RESTRICT"), index=True
    )
    text_normalized: Mapped[str] = mapped_column(String(255), unique=True)
    text_original: Mapped[str] = mapped_column(String(255))
    rule_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    source: Mapped[SupplierAliasSource] = mapped_column(
        Enum(SupplierAliasSource, name="supplier_alias_source", schema=CORE_SCHEMA),
        default=SupplierAliasSource.LEARNED,
        server_default=SupplierAliasSource.LEARNED.value,
    )
    created_by_user_id: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<SupplierAlias {self.text_original!r} -> {self.supplier_id}>"


class Invoice(Base):
    """A purchase invoice, as far as the platform can vouch for it.

    Three columns are `NOT NULL` and that is the promise of RF-35: an invoice
    without a number, a date or an amount does not enter — it stays in
    quarantine as a row nobody could read. The supplier is **not** among them:
    an invoice whose supplier could not be resolved is a registered invoice
    waiting for a person, not a discarded one.
    """

    __tablename__ = "invoice"
    __table_args__ = (
        # The duplicate key is (supplier, number), as signed. A **partial**
        # unique index, so that while the supplier is unresolved the invoice
        # cannot be anybody's duplicate: two invoices with the same number and
        # no supplier identified are not duplicates of each other (RF-40).
        Index(
            "uq_invoice_supplier_number",
            "supplier_id",
            "number",
            unique=True,
            postgresql_where=text("supplier_id IS NOT NULL"),
        ),
        Index("ix_invoice_number", "number"),
        Index("ix_invoice_issued_on", "issued_on"),
        Index("ix_invoice_review_state", "review_state"),
        {"schema": CORE_SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(64))
    issued_on: Mapped[date] = mapped_column(Date)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{CORE_SCHEMA}.supplier.id", ondelete="RESTRICT"), default=None, index=True
    )
    # The name exactly as the portal wrote it, kept whatever happens next: it is
    # what the review screen shows, and what an assignment matches on.
    supplier_text: Mapped[str] = mapped_column(String(255), default="")
    # Derived from the supplier's agreed term (RF-26 of 005), and rewritten when
    # somebody reschedules it on the calendar before it falls due (RF-26 of 006).
    due_on: Mapped[date | None] = mapped_column(Date, default=None, index=True)
    # The date it was first due. An invoice that fell due keeps being measured
    # against this one however often it is rescheduled afterwards (RF-29 of 006).
    original_due_on: Mapped[date | None] = mapped_column(Date, default=None)
    # What the portal says about this invoice. Kept and shown, and never the one
    # that decides: the payment state comes from the payments imputed (RF-45 of
    # 005), and a disagreement between the two is flagged (RF-46).
    portal_paid: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    portal_payment_status: Mapped[str | None] = mapped_column(String(50), default=None)
    portal_receipt_issued: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    file_kind: Mapped[str | None] = mapped_column(String(50), default=None)
    product_code: Mapped[str | None] = mapped_column(String(64), default=None)
    review_state: Mapped[InvoiceReviewState] = mapped_column(
        Enum(InvoiceReviewState, name="invoice_review_state", schema=CORE_SCHEMA),
        default=InvoiceReviewState.OK,
        server_default=InvoiceReviewState.OK.value,
    )
    review_reason: Mapped[str | None] = mapped_column(String(200), default=None)
    resolved_by_user_id: Mapped[int | None] = mapped_column(Integer, default=None)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    # Which saved assignment of a spelling resolved this invoice. It is what
    # makes undoing that assignment exact: it reaches what it resolved and never
    # an invoice somebody decided one by one (RF-53).
    resolved_by_alias_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    # How many times the same invoice arrived. A second arrival with the same
    # total is counted, not stored twice (RF-38, RF-39).
    arrival_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    staging_row_id: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Invoice id={self.id} number={self.number} supplier={self.supplier_id}>"


class InvoiceDocument(Base):
    """What the document of an invoice said, and whether it agreed with the table.

    Kept in `core` and not only in `staging` because it is what the review
    screen shows a person: the excerpt of the file, next to what the table said,
    is the evidence the decision is taken on (RF-30 of 004).
    """

    __tablename__ = "invoice_document"
    __table_args__ = {"schema": CORE_SCHEMA}

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey(f"{CORE_SCHEMA}.invoice.id", ondelete="CASCADE"), unique=True
    )
    raw_document_id: Mapped[int | None] = mapped_column(Integer, default=None)
    readable: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    agrees: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    excerpt: Mapped[str | None] = mapped_column(Text, default=None)
    reason: Mapped[str | None] = mapped_column(String(200), default=None)
    read_number: Mapped[str | None] = mapped_column(String(64), default=None)
    read_issued_on: Mapped[date | None] = mapped_column(Date, default=None)
    read_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    read_supplier_text: Mapped[str | None] = mapped_column(String(255), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<InvoiceDocument invoice_id={self.invoice_id} agrees={self.agrees}>"


class Payment(Base):
    """One payment: a voucher the portal published, or one somebody typed.

    A voucher that does not say which invoice it covers is **not** distributed
    by the platform. It is registered against its supplier and waits, counted
    and visible, for a person to say how it splits (RF-12, RF-53 of 005).
    Splitting it automatically would be the system deciding where money went.
    """

    __tablename__ = "payment"
    __table_args__ = (
        # The same voucher read twice is imputed once (RF-13). The database is
        # what says so, not a check that could race with itself.
        UniqueConstraint("external_id", name="uq_payment_external_id"),
        Index("ix_payment_invoice_id", "invoice_id"),
        Index("ix_payment_state", "state"),
        {"schema": CORE_SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{CORE_SCHEMA}.supplier.id", ondelete="RESTRICT"), default=None
    )
    invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{CORE_SCHEMA}.invoice.id", ondelete="CASCADE"), default=None
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    paid_on: Mapped[date] = mapped_column(Date)
    origin: Mapped[PaymentOrigin] = mapped_column(
        Enum(PaymentOrigin, name="payment_origin", schema=CORE_SCHEMA),
        default=PaymentOrigin.PORTAL,
        server_default=PaymentOrigin.PORTAL.value,
    )
    state: Mapped[PaymentState] = mapped_column(
        Enum(PaymentState, name="payment_state", schema=CORE_SCHEMA),
        default=PaymentState.IMPUTED,
        server_default=PaymentState.IMPUTED.value,
    )
    # `Aceros Belgrano SA|REC-1084`. Null on a payment somebody typed: it has no
    # voucher of the portal behind it, and two manual payments of the same
    # amount on the same day are two payments.
    external_id: Mapped[str | None] = mapped_column(String(160), default=None)
    reference: Mapped[str | None] = mapped_column(String(255), default=None)
    supplier_text: Mapped[str | None] = mapped_column(String(255), default=None)
    review_reason: Mapped[str | None] = mapped_column(String(200), default=None)
    created_by_user_id: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    voided_by_user_id: Mapped[int | None] = mapped_column(Integer, default=None)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    def __repr__(self) -> str:
        return f"<Payment id={self.id} invoice={self.invoice_id} {self.amount}>"


class Receipt(Base):
    """The reception receipt of an invoice, with a number of this platform's own.

    Annulled, never deleted: a receipt that disappeared could not be audited,
    and RF-49 of 005 asks for who annulled it and when. The invoice can then be
    issued another one — unless it has already fallen due (RF-50, RF-51).
    """

    __tablename__ = "receipt"
    __table_args__ = (
        # One receipt in force per invoice. Partial, over the ones not annulled:
        # an invoice can have several over its life and only one that counts.
        Index(
            "uq_receipt_in_force",
            "invoice_id",
            unique=True,
            postgresql_where=text("voided_at IS NULL"),
        ),
        UniqueConstraint("number", name="uq_receipt_number"),
        {"schema": CORE_SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey(f"{CORE_SCHEMA}.invoice.id", ondelete="CASCADE"), index=True
    )
    # Correlative and unique, of this platform: the portal does not number ours
    # (RF-48).
    number: Mapped[str] = mapped_column(String(32))
    issued_by_user_id: Mapped[int] = mapped_column(Integer)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # The document a person downloads (RF-47). Plain text: it is a receipt of
    # reception, and rendering it as a PDF is a presentation choice the browser
    # can make later without the record changing.
    document: Mapped[str | None] = mapped_column(Text, default=None)
    voided_by_user_id: Mapped[int | None] = mapped_column(Integer, default=None)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    @property
    def is_in_force(self) -> bool:
        return self.voided_at is None

    def __repr__(self) -> str:
        return f"<Receipt {self.number} invoice={self.invoice_id}>"


class ReceiptIncident(Base):
    """An invoice that fell due without its receipt (RF-37 of 005).

    Closed with what was done about it, never deleted: RF-59 asks that it stop
    being counted among the pending ones and stay available to look at.
    """

    __tablename__ = "receipt_incident"
    __table_args__ = (
        Index(
            "uq_receipt_incident_open",
            "invoice_id",
            unique=True,
            postgresql_where=text("closed_at IS NULL"),
        ),
        {"schema": CORE_SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey(f"{CORE_SCHEMA}.invoice.id", ondelete="CASCADE"), index=True
    )
    opened_on: Mapped[date] = mapped_column(Date)
    closed_by_user_id: Mapped[int | None] = mapped_column(Integer, default=None)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    resolution: Mapped[str | None] = mapped_column(Text, default=None)

    def __repr__(self) -> str:
        return f"<ReceiptIncident invoice={self.invoice_id} closed={self.closed_at is not None}>"


class DueDate(Base):
    """One entry of the calendar: an invoice's due date, or one somebody added.

    A row of its own rather than a column of the invoice, because it moves and
    moving it has to keep where it came from. An entry that comes from an
    invoice cannot be deleted (RF-18 of 006): the invoice exists, and so does
    the date it is due.
    """

    __tablename__ = "due_date"
    __table_args__ = (
        Index("ix_due_date_on_date", "on_date"),
        Index(
            "uq_due_date_invoice",
            "invoice_id",
            unique=True,
            postgresql_where=text("invoice_id IS NOT NULL"),
        ),
        {"schema": CORE_SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    on_date: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(String(300))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{CORE_SCHEMA}.invoice.id", ondelete="CASCADE"), default=None
    )
    origin: Mapped[DueDateOrigin] = mapped_column(
        Enum(DueDateOrigin, name="due_date_origin", schema=CORE_SCHEMA),
        default=DueDateOrigin.MANUAL,
        server_default=DueDateOrigin.MANUAL.value,
    )
    original_date: Mapped[date] = mapped_column(Date)
    created_by_user_id: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def was_rescheduled(self) -> bool:
        """Whether it is no longer where it started (RF-24 of 006)."""
        return self.on_date != self.original_date

    def __repr__(self) -> str:
        return f"<DueDate id={self.id} on={self.on_date}>"


class DueDateChange(Base):
    """One move of an entry of the calendar, with who moved it and why.

    Every move is kept, so RF-23 can show the original date, all of its
    reschedulings and whatever reasons were written. Two people moving the same
    entry leaves the last move in force and both in the history (RF-34).
    """

    __tablename__ = "due_date_change"
    __table_args__ = {"schema": CORE_SCHEMA}

    id: Mapped[int] = mapped_column(primary_key=True)
    due_date_id: Mapped[int] = mapped_column(
        ForeignKey(f"{CORE_SCHEMA}.due_date.id", ondelete="CASCADE"), index=True
    )
    previous_date: Mapped[date] = mapped_column(Date)
    new_date: Mapped[date] = mapped_column(Date)
    # Offered, never required (RF-22 of 006).
    reason: Mapped[str | None] = mapped_column(Text, default=None)
    actor_user_id: Mapped[int] = mapped_column(Integer)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<DueDateChange {self.previous_date} -> {self.new_date}>"


class PurchaseOrder(Base):
    """One purchase order, and how long the platform has been watching it there.

    `status_since` is **the date this platform observed the state**, not a date
    the portal publishes: the portal does not say since when an order has been
    where it is, and inventing that would be answering a question the origin
    never answered (RF-05, RF-48 of 007).
    """

    __tablename__ = "purchase_order"
    __table_args__ = (
        UniqueConstraint("number", name="uq_purchase_order_number"),
        Index("ix_purchase_order_status", "status_text"),
        Index("ix_purchase_order_supplier", "supplier_id"),
        {"schema": CORE_SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(64))
    ordered_on: Mapped[date] = mapped_column(Date)
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{CORE_SCHEMA}.supplier.id", ondelete="RESTRICT"), default=None
    )
    supplier_text: Mapped[str] = mapped_column(String(255), default="")
    product_code: Mapped[str | None] = mapped_column(String(64), default=None)
    product_text: Mapped[str] = mapped_column(String(500), default="")
    quantity: Mapped[int | None] = mapped_column(Integer, default=None)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    status_text: Mapped[str] = mapped_column(String(100), default="")
    status_since: Mapped[date] = mapped_column(Date)
    # Whether the platform saw this order before it started watching. For those,
    # what can be shown is how long ago the order was placed, and it is said as
    # that rather than as time in the state (RF-49).
    observed_from_start: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    review_state: Mapped[OrderReviewState] = mapped_column(
        Enum(OrderReviewState, name="order_review_state", schema=CORE_SCHEMA),
        default=OrderReviewState.OK,
        server_default=OrderReviewState.OK.value,
    )
    # The earlier order this one repeats, when it looks like a repeat (RF-15).
    repeat_of_order_id: Mapped[int | None] = mapped_column(Integer, default=None)
    repeat_dismissed_by_user_id: Mapped[int | None] = mapped_column(Integer, default=None)
    repeat_dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<PurchaseOrder {self.number} {self.status_text}>"


class PurchaseSetting(Base):
    """The business parameters this module needs, as **its own** projection.

    The parameters belong to `operations` and this module cannot read its table
    (Artículo IV). So it keeps the handful it cares about here, fed by the event
    `operations` publishes when the owner changes one. Until that happens the
    service falls back to the starting value declared in `shared/parameters.py`,
    which is what makes a fresh installation behave like a configured one.
    """

    __tablename__ = "purchase_setting"
    __table_args__ = {"schema": CORE_SCHEMA}

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<PurchaseSetting key={self.key}>"


class PurchaseCorrection(Base, CorrectionColumns):
    """A value of this module that a person put on top of what the portal said.

    The same shape as the catalog's, from `app.shared.corrections`, in this
    module's own table — the mixin exists for exactly this, and its docstring
    names purchase invoices. Neither module learns about the other's.
    """

    __tablename__ = "purchase_correction"
    __table_args__ = (
        Index(
            "uq_purchase_correction_in_force",
            "entity_type",
            "entity_id",
            "field",
            unique=True,
            postgresql_where=text("status <> 'REVERTED'"),
        ),
        {"schema": CORE_SCHEMA},
    )

    def __repr__(self) -> str:
        return f"<PurchaseCorrection {self.entity_type}:{self.entity_id}.{self.field}>"


__all__ = [
    "CORE_SCHEMA",
    "SupplierAliasSource",
    "CorrectionStatus",
    "DueDate",
    "DueDateChange",
    "DueDateOrigin",
    "Invoice",
    "InvoiceDocument",
    "InvoiceReviewState",
    "OrderReviewState",
    "Payment",
    "PaymentOrigin",
    "PaymentState",
    "PurchaseCorrection",
    "PurchaseOrder",
    "PurchaseSetting",
    "Receipt",
    "ReceiptIncident",
    "Supplier",
    "SupplierAlias",
]
