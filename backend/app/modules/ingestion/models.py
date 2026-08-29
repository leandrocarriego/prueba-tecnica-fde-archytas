"""Ingestion models: what could be interpreted, and what could not.

Everything here lives in `staging`, the middle of the one-way pipeline. It is
reproducible by definition: any of these rows can be rebuilt from `raw` without
asking the portal for anything again.
"""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Enum, Index, Integer, Numeric, Sequence, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

STAGING_SCHEMA = "staging"

# One batch per run of the pipeline. It is what travels in the events and what
# groups a run's rows, and it comes from the database so two concurrent runs can
# never be handed the same number.
batch_sequence = Sequence("price_batch_seq", schema=STAGING_SCHEMA, metadata=Base.metadata)


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
