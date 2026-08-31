"""Sales models: one row per sales record, and what the platform decided about it.

The columns that matter most are the ones holding **what the portal said**. A
person can correct a date, a total, a quantity or a product, and can mark a
value as estimated when the right one cannot be known — and in every one of
those cases the value the portal reported is kept beside it (RF-39, RF-41).
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
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

CORE_SCHEMA = "core"


class SaleState(enum.StrEnum):
    """Whether a sales record may be added up.

    `HELD` is not an error state: it is a record waiting for a person, counted
    and visible. `DISCARDED` is the copy of a record that was counted once —
    kept, never deleted, and shown next to the one that was chosen (RF-34).
    """

    COUNTED = "COUNTED"
    HELD = "HELD"
    DISCARDED = "DISCARDED"


class Sale(Base):
    """One sales record, as far as the platform can vouch for it."""

    __tablename__ = "sale"
    __table_args__ = (
        Index("ix_sale_code_key", "code_key"),
        Index("ix_sale_state", "state"),
        Index("ix_sale_sold_on", "sold_on"),
        {"schema": CORE_SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64))
    # The code with the differences of spelling removed. It is what says two
    # records are the same sale, and it is stored so the grouping is an index
    # lookup rather than a rule applied differently in two places (RF-10).
    code_key: Mapped[str] = mapped_column(String(64))
    sold_on: Mapped[date | None] = mapped_column(Date, default=None)
    product_code: Mapped[str | None] = mapped_column(String(64), default=None)
    quantity: Mapped[int | None] = mapped_column(Integer, default=None)
    total: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    state: Mapped[SaleState] = mapped_column(
        Enum(SaleState, name="sale_state", schema=CORE_SCHEMA),
        default=SaleState.COUNTED,
        server_default=SaleState.COUNTED.value,
    )
    # Why it is held, in the words the review screen shows (RF-23).
    reason: Mapped[str | None] = mapped_column(String(200), default=None)
    # What the portal reported, kept whatever anybody corrects afterwards. It is
    # the evidence, and it is what makes a correction reversible (RF-41).
    portal_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    # A value somebody estimated because the right one cannot be known. Every
    # indicator built on it says so (RF-39, RF-40).
    is_estimated: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # The record this one was found to duplicate, when it was.
    duplicate_of_sale_id: Mapped[int | None] = mapped_column(Integer, default=None)
    decision: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    resolved_by_user_id: Mapped[int | None] = mapped_column(Integer, default=None)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    staging_row_id: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Sale id={self.id} code={self.code} state={self.state}>"


class SalesProduct(Base):
    """The product codes the catalog knows, as this module needs to read them.

    A projection, fed by the event the catalog publishes when it starts knowing
    a product. It is what lets RF-20 — a sale pointing at a product that does
    not exist — be answered without importing the catalog (Artículo IV).
    """

    __tablename__ = "sales_product"
    __table_args__ = {"schema": CORE_SCHEMA}

    product_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    known_since: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<SalesProduct {self.product_code}>"


class SalesSetting(Base):
    """The business parameters this module reads, as its own projection."""

    __tablename__ = "sales_setting"
    __table_args__ = {"schema": CORE_SCHEMA}

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<SalesSetting key={self.key}>"


__all__ = ["CORE_SCHEMA", "Sale", "SaleState", "SalesProduct", "SalesSetting"]
