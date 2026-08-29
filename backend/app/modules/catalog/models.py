"""Catalog models: the canonical model of the business, in `core`.

Only rows that could be interpreted reach this schema. Everything here is fed
from `staging`, never straight from `raw`.
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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

CORE_SCHEMA = "core"


class ProductStatus(enum.StrEnum):
    """Whether the business still buys this product."""

    ACTIVE = "ACTIVE"
    DISCONTINUED = "DISCONTINUED"


class PriceSource(enum.StrEnum):
    """Where a point of the history came from."""

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
