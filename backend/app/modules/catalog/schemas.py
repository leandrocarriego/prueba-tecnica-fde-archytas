"""Catalog schemas: the HTTP contract of the prices screen and the product page."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.modules.catalog.models import PriceSource, ProductStatus


class PriceRead(BaseModel):
    """A product with the price in force, as the prices screen shows it."""

    model_config = ConfigDict(from_attributes=True)

    product_id: int
    code: str
    description: str
    status: ProductStatus
    price: Decimal | None
    currency: str
    effective_at: datetime | None
    previous_price: Decimal | None
    is_highlighted: bool
    # The product did not come in the last list: it keeps the price it had.
    is_stale: bool
    # Against the last price of the previous calendar month (RF-24). None when
    # there is no point to compare against.
    monthly_variation_pct: Decimal | None = None


class PriceList(BaseModel):
    """A page of prices."""

    items: list[PriceRead]
    total: int
    skip: int
    limit: int


class PricePointRead(BaseModel):
    """One point of a product's history."""

    model_config = ConfigDict(from_attributes=True)

    price: Decimal
    changed_at: datetime
    source: PriceSource


class PriceHistoryRead(BaseModel):
    """How the price of a product evolved (RF-23), and its monthly variation (RF-24)."""

    product_id: int
    code: str
    description: str
    price: Decimal | None
    currency: str
    monthly_variation_pct: Decimal | None
    points: list[PricePointRead]
