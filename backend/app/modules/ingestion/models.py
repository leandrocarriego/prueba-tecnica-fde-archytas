"""Ingestion models: what could be interpreted, and what could not.

Everything here lives in `staging`, the middle of the one-way pipeline. It is
reproducible by definition: any of these rows can be rebuilt from `raw` without
asking the portal for anything again.
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
    Index,
    Integer,
    Numeric,
    Sequence,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

STAGING_SCHEMA = "staging"

# One batch per run of the pipeline. It is what travels in the events and what
# groups a run's rows, and it comes from the database so two concurrent runs can
# never be handed the same number.
price_batch_sequence = Sequence("price_batch_seq", schema=STAGING_SCHEMA, metadata=Base.metadata)


class RowStatus(enum.StrEnum):
    """Whether a row could be interpreted.

    `QUARANTINED` is not an error state: it is a row waiting for a person, and
    it is the whole point of Artículo II — nothing is discarded.
    """

    VALID = "VALID"
    QUARANTINED = "QUARANTINED"


class PriceRow(Base):
    """One line of the daily list, typed.

    A row that cannot be read keeps its `excerpt`, so whoever reviews it can see
    what the file actually said instead of guessing.
    """

    __tablename__ = "price_row"
    __table_args__ = (
        # Counting what a run set aside (RF-27).
        Index("ix_price_row_batch_status", "batch_id", "status"),
        Index("ix_price_row_product_code", "product_code"),
        {"schema": STAGING_SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_document_id: Mapped[int] = mapped_column(Integer, index=True)
    batch_id: Mapped[int] = mapped_column(Integer)
    line_number: Mapped[int] = mapped_column(Integer)
    product_code: Mapped[str | None] = mapped_column(String(64), default=None)
    description: Mapped[str | None] = mapped_column(String(500), default=None)
    # Money is never a float.
    price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    currency: Mapped[str] = mapped_column(String(3), default="ARS", server_default="ARS")
    status: Mapped[RowStatus] = mapped_column(
        Enum(RowStatus, name="row_status", schema=STAGING_SCHEMA),
        default=RowStatus.VALID,
        server_default=RowStatus.VALID.value,
    )
    reason: Mapped[str | None] = mapped_column(String(200), default=None)
    excerpt: Mapped[str | None] = mapped_column(Text, default=None)
    # Kept exactly as the portal wrote them and read by nobody in this feature:
    # the supplier spells the same category four ways, and unifying them is P7.
    # Storing them now saves P7 from parsing every file again.
    category_raw: Mapped[str | None] = mapped_column(String(200), default=None)
    subcategory_raw: Mapped[str | None] = mapped_column(String(200), default=None)
    # The stock of the day, kept for the same reason as the two above: the file
    # publishes it, reading it later would mean parsing every file again, and
    # the stock cut of the dashboard compares one day against another (009).
    stock: Mapped[int | None] = mapped_column(Integer, default=None)
    resolved_by_rule_id: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<PriceRow id={self.id} code={self.product_code} status={self.status}>"


class PriceHistoryRow(Base):
    """One point of the history screen of a product, typed.

    Mirror of `PriceRow`: same cycle, same states, same quarantine. On this
    screen the price arrives as text (`$25.308`), so this is the parser that
    sets most rows aside.
    """

    __tablename__ = "price_history_row"
    __table_args__ = (
        Index("ix_price_history_row_product_code", "product_code"),
        {"schema": STAGING_SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_document_id: Mapped[int] = mapped_column(Integer, index=True)
    product_code: Mapped[str] = mapped_column(String(64))
    line_number: Mapped[int] = mapped_column(Integer)
    price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    status: Mapped[RowStatus] = mapped_column(
        Enum(RowStatus, name="row_status", schema=STAGING_SCHEMA),
        default=RowStatus.VALID,
        server_default=RowStatus.VALID.value,
    )
    reason: Mapped[str | None] = mapped_column(String(200), default=None)
    excerpt: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<PriceHistoryRow id={self.id} code={self.product_code} status={self.status}>"


class ResolutionRuleProjection(Base):
    """The decisions a person already took, as this module needs to read them.

    A **projection**, not a source: the rules belong to `triage`, and this
    module cannot import it (Artículo IV). It is fed by the two events `triage`
    publishes, and it is never written from the service — only from
    `handlers.py`. If that ever feels restrictive, the boundary is in the wrong
    place.
    """

    __tablename__ = "resolution_rule"
    __table_args__ = {"schema": STAGING_SCHEMA}

    # Not a primary key of its own: it is the id the rule has in `triage`.
    rule_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    kind: Mapped[str] = mapped_column(String(50), index=True)
    matcher: Mapped[dict[str, Any]] = mapped_column(JSONB)
    decision: Mapped[dict[str, Any]] = mapped_column(JSONB)
    learned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<ResolutionRuleProjection rule_id={self.rule_id} kind={self.kind}>"


# --- What the other sections of the portal said (004, 007, 009) ----------
#
# Same shape as `PriceRow` and for the same reason: every row that arrives is
# typed here first, valid or quarantined, and `core` is only ever fed from the
# valid ones. A row that cannot be read keeps its `excerpt`, so whoever reviews
# it sees what the portal actually said instead of guessing.

# The batch number of every pipeline that is not the price list. One sequence
# rather than one per section: a batch id only has to be unique, and two runs
# that overlap must never be handed the same number.
batch_sequence = Sequence("document_batch_seq", schema=STAGING_SCHEMA, metadata=Base.metadata)


class InvoiceRow(Base):
    """One row of the invoices screen, typed.

    It carries everything the table publishes, including what `005` reads —
    what was paid, the balance, the payment state the portal reports and
    whether the receipt was issued. The screen is read once; interpreting it
    twice would be two truths about the same row.
    """

    __tablename__ = "invoice_row"
    __table_args__ = (
        Index("ix_invoice_row_batch_status", "batch_id", "status"),
        Index("ix_invoice_row_number", "number"),
        {"schema": STAGING_SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_document_id: Mapped[int] = mapped_column(Integer, index=True)
    batch_id: Mapped[int] = mapped_column(Integer)
    line_number: Mapped[int] = mapped_column(Integer)
    number: Mapped[str | None] = mapped_column(String(64), default=None)
    supplier_text: Mapped[str | None] = mapped_column(String(255), default=None)
    issued_on: Mapped[date | None] = mapped_column(Date, default=None)
    due_on: Mapped[date | None] = mapped_column(Date, default=None)
    total: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    paid: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    balance: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    receipt_issued: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    portal_payment_status: Mapped[str | None] = mapped_column(String(50), default=None)
    file_kind: Mapped[str | None] = mapped_column(String(50), default=None)
    product_code: Mapped[str | None] = mapped_column(String(64), default=None)
    status: Mapped[RowStatus] = mapped_column(
        Enum(RowStatus, name="row_status", schema=STAGING_SCHEMA),
        default=RowStatus.VALID,
        server_default=RowStatus.VALID.value,
    )
    reason: Mapped[str | None] = mapped_column(String(200), default=None)
    excerpt: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<InvoiceRow id={self.id} number={self.number} status={self.status}>"


class InvoiceFileRead(Base):
    """What the **document** of an invoice said, next to what the table said.

    The two are read and compared, and `agrees` is the signal the whole feature
    rests on: when they say the same thing the invoice is certainty and nobody
    is bothered; when they disagree — or the document could not be read — it
    goes to a person with the excerpt in view.

    It saves having to invent a confidence threshold for the OCR as the only
    thing separating a good number from a made-up one.
    """

    __tablename__ = "invoice_file_read"
    __table_args__ = (
        Index("ix_invoice_file_read_number", "invoice_number"),
        {"schema": STAGING_SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_document_id: Mapped[int] = mapped_column(Integer, index=True)
    invoice_number: Mapped[str] = mapped_column(String(64))
    readable: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    agrees: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    number: Mapped[str | None] = mapped_column(String(64), default=None)
    issued_on: Mapped[date | None] = mapped_column(Date, default=None)
    total: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    supplier_text: Mapped[str | None] = mapped_column(String(255), default=None)
    reason: Mapped[str | None] = mapped_column(String(200), default=None)
    excerpt: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<InvoiceFileRead invoice={self.invoice_number} agrees={self.agrees}>"


class SupplierRow(Base):
    """One card of the supplier register, typed."""

    __tablename__ = "supplier_row"
    __table_args__ = {"schema": STAGING_SCHEMA}

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_document_id: Mapped[int] = mapped_column(Integer, index=True)
    line_number: Mapped[int] = mapped_column(Integer)
    legal_name: Mapped[str | None] = mapped_column(String(255), default=None)
    tax_id: Mapped[str | None] = mapped_column(String(20), default=None)
    email: Mapped[str | None] = mapped_column(String(255), default=None)
    phone: Mapped[str | None] = mapped_column(String(50), default=None)
    payment_term_days: Mapped[int | None] = mapped_column(Integer, default=None)
    balance: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    status: Mapped[RowStatus] = mapped_column(
        Enum(RowStatus, name="row_status", schema=STAGING_SCHEMA),
        default=RowStatus.VALID,
        server_default=RowStatus.VALID.value,
    )
    reason: Mapped[str | None] = mapped_column(String(200), default=None)
    excerpt: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<SupplierRow id={self.id} name={self.legal_name}>"


class PaymentRow(Base):
    """One movement of the current account that is a payment, typed.

    `reference` is kept as the portal wrote it, whole: a voucher that names two
    invoices is exactly the case the platform refuses to split on its own, and
    splitting the text here would be making that decision in the parser.
    """

    __tablename__ = "payment_row"
    __table_args__ = (
        Index("ix_payment_row_batch_status", "batch_id", "status"),
        {"schema": STAGING_SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_document_id: Mapped[int] = mapped_column(Integer, index=True)
    batch_id: Mapped[int] = mapped_column(Integer)
    line_number: Mapped[int] = mapped_column(Integer)
    supplier_text: Mapped[str | None] = mapped_column(String(255), default=None)
    reference: Mapped[str | None] = mapped_column(String(255), default=None)
    paid_on: Mapped[date | None] = mapped_column(Date, default=None)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    # What makes the same voucher the same voucher across runs (RF-13 of 005).
    external_id: Mapped[str | None] = mapped_column(String(128), default=None, index=True)
    status: Mapped[RowStatus] = mapped_column(
        Enum(RowStatus, name="row_status", schema=STAGING_SCHEMA),
        default=RowStatus.VALID,
        server_default=RowStatus.VALID.value,
    )
    reason: Mapped[str | None] = mapped_column(String(200), default=None)
    excerpt: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<PaymentRow id={self.id} reference={self.reference}>"


class PurchaseOrderRow(Base):
    """One row of the purchase orders screen, typed."""

    __tablename__ = "purchase_order_row"
    __table_args__ = (
        Index("ix_purchase_order_row_batch_status", "batch_id", "status"),
        {"schema": STAGING_SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_document_id: Mapped[int] = mapped_column(Integer, index=True)
    batch_id: Mapped[int] = mapped_column(Integer)
    line_number: Mapped[int] = mapped_column(Integer)
    number: Mapped[str | None] = mapped_column(String(64), default=None)
    ordered_on: Mapped[date | None] = mapped_column(Date, default=None)
    supplier_text: Mapped[str | None] = mapped_column(String(255), default=None)
    product_code: Mapped[str | None] = mapped_column(String(64), default=None)
    product_text: Mapped[str | None] = mapped_column(String(500), default=None)
    quantity: Mapped[int | None] = mapped_column(Integer, default=None)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    status_text: Mapped[str | None] = mapped_column(String(100), default=None)
    status: Mapped[RowStatus] = mapped_column(
        Enum(RowStatus, name="row_status", schema=STAGING_SCHEMA),
        default=RowStatus.VALID,
        server_default=RowStatus.VALID.value,
    )
    reason: Mapped[str | None] = mapped_column(String(200), default=None)
    excerpt: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<PurchaseOrderRow id={self.id} number={self.number}>"


class MessageRow(Base):
    """One message of the portal inbox, typed."""

    __tablename__ = "message_row"
    __table_args__ = (
        Index("ix_message_row_batch_status", "batch_id", "status"),
        {"schema": STAGING_SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_document_id: Mapped[int] = mapped_column(Integer, index=True)
    batch_id: Mapped[int] = mapped_column(Integer)
    line_number: Mapped[int] = mapped_column(Integer)
    external_id: Mapped[str | None] = mapped_column(String(128), default=None, index=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    sender_text: Mapped[str | None] = mapped_column(String(255), default=None)
    kind_text: Mapped[str | None] = mapped_column(String(100), default=None)
    subject: Mapped[str | None] = mapped_column(String(500), default=None)
    body: Mapped[str | None] = mapped_column(Text, default=None)
    already_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    status: Mapped[RowStatus] = mapped_column(
        Enum(RowStatus, name="row_status", schema=STAGING_SCHEMA),
        default=RowStatus.VALID,
        server_default=RowStatus.VALID.value,
    )
    reason: Mapped[str | None] = mapped_column(String(200), default=None)
    excerpt: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<MessageRow id={self.id} external_id={self.external_id}>"


class SaleRow(Base):
    """One sales record, typed.

    `code_key` is the sale code with the differences of spelling removed, and it
    is what says two records are the same sale (RF-09, RF-10 of 009). It is
    stored rather than derived on the way out so the grouping is a plain index
    lookup and always means what it meant when the row landed.
    """

    __tablename__ = "sale_row"
    __table_args__ = (
        Index("ix_sale_row_batch_status", "batch_id", "status"),
        Index("ix_sale_row_code_key", "code_key"),
        {"schema": STAGING_SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_document_id: Mapped[int] = mapped_column(Integer, index=True)
    batch_id: Mapped[int] = mapped_column(Integer)
    line_number: Mapped[int] = mapped_column(Integer)
    code: Mapped[str | None] = mapped_column(String(64), default=None)
    code_key: Mapped[str | None] = mapped_column(String(64), default=None)
    sold_on: Mapped[date | None] = mapped_column(Date, default=None)
    product_code: Mapped[str | None] = mapped_column(String(64), default=None)
    quantity: Mapped[int | None] = mapped_column(Integer, default=None)
    total: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    status: Mapped[RowStatus] = mapped_column(
        Enum(RowStatus, name="row_status", schema=STAGING_SCHEMA),
        default=RowStatus.VALID,
        server_default=RowStatus.VALID.value,
    )
    reason: Mapped[str | None] = mapped_column(String(200), default=None)
    excerpt: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<SaleRow id={self.id} code={self.code} status={self.status}>"
