"""Catalog models: the canonical model of the business, in `core`.

Only rows that could be interpreted reach this schema. Everything here is fed
from `staging`, never straight from `raw`.

`Correction` is the exception to that sentence and the reason it is worth
reading twice: it is what a **person** put on top of what the portal said, and
it lives here, in the module that owns the datum, rather than in a central
table somewhere. That is not a preference. While a new price is being applied,
this module has to know whether the datum carries a correction and what the
portal had originally reported (RF-28), and asking another module for that
would be reading its table — the import Artículo IV forbids.
"""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.shared.corrections import CorrectionColumns, CorrectionStatus

CORE_SCHEMA = "core"


class ProductStatus(enum.StrEnum):
    """Whether the business still buys this product."""

    ACTIVE = "ACTIVE"
    DISCONTINUED = "DISCONTINUED"


class PriceSource(enum.StrEnum):
    """Where a value came from: a list the portal published, or this platform.

    It answers the question RF-33 rests on — whether there is a value the
    portal reported underneath this one — so it marks the rows that hold a
    value, not only the points of the history.
    """

    PORTAL = "PORTAL"
    SYSTEM = "SYSTEM"


class Product(Base):
    """A product the catalog knows.

    Seeded by the first list (RF-02) and after that it only grows by a human
    decision (RF-30), never by an automatic run (RF-07).
    """

    __tablename__ = "product"
    __table_args__ = {"schema": CORE_SCHEMA}

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(500))
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status", schema=CORE_SCHEMA),
        default=ProductStatus.ACTIVE,
        server_default=ProductStatus.ACTIVE.value,
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # What tells apart the product that stopped coming in the list (RF-28).
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Which learned rule brought it in, when a person decided to incorporate it.
    # It is what lets revoking that rule undo exactly what it did (RF-37).
    registered_by_rule_id: Mapped[int | None] = mapped_column(Integer, default=None)
    # Whether the portal reported this product or a person typed it into the
    # review queue. It is a different question from the one above — a product
    # that came in the daily list has no rule either — and RF-33 needs this one:
    # a value nobody reported offers no way back to "what the portal said".
    source: Mapped[PriceSource] = mapped_column(
        Enum(PriceSource, name="price_source", schema=CORE_SCHEMA),
        default=PriceSource.PORTAL,
        server_default=PriceSource.PORTAL.value,
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id} code={self.code} status={self.status}>"


class ProductPrice(Base):
    """The price in force for a product: one row per product, rewritten each time.

    `previous_price` is denormalised on purpose. RF-25 compares against *the
    previous update*, not against the previous point of the history, and they
    are not the same thing: if the price did not change the history gains no
    point (RF-22), but the update did happen.
    """

    __tablename__ = "product_price"
    __table_args__ = {"schema": CORE_SCHEMA}

    product_id: Mapped[int] = mapped_column(
        ForeignKey(f"{CORE_SCHEMA}.product.id", ondelete="CASCADE"), primary_key=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    currency: Mapped[str] = mapped_column(String(3), default="ARS", server_default="ARS")
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    previous_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    # Derived, but materialised: the prices screen filters on it.
    is_highlighted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # The product did not come in the last list and keeps its last price (RF-08).
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # Who last wrote this row. One flag for the whole row because the row is
    # written whole: whoever reports an amount reports the unit beside it.
    #
    # It belongs here and not on the product on purpose. The next daily list
    # re-prices a product a person loaded by hand, and from that morning on the
    # amount *is* the portal's even though the product never was — so RF-33 has
    # to be answered per value, not per product.
    source: Mapped[PriceSource] = mapped_column(
        Enum(PriceSource, name="price_source", schema=CORE_SCHEMA),
        default=PriceSource.PORTAL,
        server_default=PriceSource.PORTAL.value,
    )

    def __repr__(self) -> str:
        return f"<ProductPrice product_id={self.product_id} price={self.price}>"


class PricePoint(Base):
    """One point of a product's history: one per **change**, not per query.

    Fed from two sources: what the portal already published when the product was
    registered (RF-38), and what the system has seen since (RF-22).
    """

    __tablename__ = "price_point"
    __table_args__ = (
        # The database is what enforces RF-40: importing a published history
        # twice collides here and leaves one point, instead of relying on the
        # code remembering to check. `source` is deliberately out of the key —
        # the same price on the same date is the same point, whoever saw it.
        UniqueConstraint("product_id", "changed_at", name="uq_price_point_product_changed"),
        Index("ix_price_point_product_changed", "product_id", "changed_at"),
        {"schema": CORE_SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey(f"{CORE_SCHEMA}.product.id", ondelete="CASCADE"), index=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Which run produced it. Null on the points imported from the portal.
    batch_id: Mapped[int | None] = mapped_column(Integer, default=None)
    source: Mapped[PriceSource] = mapped_column(
        Enum(PriceSource, name="price_source", schema=CORE_SCHEMA),
        default=PriceSource.SYSTEM,
        server_default=PriceSource.SYSTEM.value,
    )

    def __repr__(self) -> str:
        return f"<PricePoint product_id={self.product_id} at={self.changed_at} {self.price}>"


class CatalogSetting(Base):
    """The business parameters this module needs, as **its own** projection.

    The parameters belong to `operations` and this module cannot read its table
    (Artículo IV). So it keeps the handful it cares about here, fed by the event
    `operations` publishes when the owner changes one. Until that happens the
    service falls back to the starting value, which is exactly what RF-20 asks
    for.
    """

    __tablename__ = "catalog_setting"
    __table_args__ = {"schema": CORE_SCHEMA}

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<CatalogSetting key={self.key}>"


class Correction(Base, CorrectionColumns):
    """A value a person put on top of what the portal reported, for this module.

    The columns come from `app.shared.corrections`: when purchase invoices are
    built they get a table of their own with the same shape, in their own
    schema, and neither module learns about the other.

    A datum has **at most one correction in force**, and the database is what
    says so: the partial unique index below covers every row that is not
    `REVERTED`. Undone corrections stay — nothing is deleted here either, and a
    log entry that pointed at a row somebody removed would explain nothing
    (Artículo II).
    """

    __tablename__ = "correction"
    __table_args__ = (
        Index(
            "uq_correction_in_force",
            "entity_type",
            "entity_id",
            "field",
            unique=True,
            postgresql_where=text("status <> 'REVERTED'"),
        ),
        {"schema": CORE_SCHEMA},
    )

    def __repr__(self) -> str:
        return f"<Correction {self.entity_type}:{self.entity_id}.{self.field} {self.status}>"


# Re-exported so the rest of the module names the status without reaching past
# `models.py` for it.
__all__ = [
    "CORE_SCHEMA",
    "CatalogSetting",
    "Correction",
    "CorrectionStatus",
    "PricePoint",
    "PriceSource",
    "Product",
    "ProductPrice",
    "ProductStatus",
]
