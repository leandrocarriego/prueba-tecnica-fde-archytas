"""Catalog schemas: the HTTP contract of the prices screen and the product page."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.catalog.models import CorrectionStatus, PriceSource, ProductStatus

REASON_DETAIL_MAX = 1000


class CorrectionMark(BaseModel):
    """A field of this row that a person corrected by hand.

    It is what makes a corrected value tell itself apart at a glance (RF-26)
    and show what the portal had said right next to it (RF-27). A row with an
    empty list is a row exactly as the portal delivered it.
    """

    correction_id: int
    field: str
    portal_value: Any
    corrected_value: Any
    status: CorrectionStatus
    # What the portal came back with, when it contradicted the correction. The
    # screen shows it as a question to answer, not as a value it applied.
    conflict_value: Any | None = None


class CorrectionWrite(BaseModel):
    """What somebody has to say to correct a value (RF-11, RF-23).

    The reason is required by the schema and not only by the service: a
    correction without a reason is a number that appeared, and counting how
    many corrections happened for the same reason is the point of asking.
    """

    field: str = Field(min_length=1, max_length=100)
    value: Any
    reason_code: str = Field(min_length=1, max_length=50)
    reason_detail: str | None = Field(default=None, max_length=REASON_DETAIL_MAX)


class CorrectionRead(BaseModel):
    """What a correction did, as the screen that asked for it gets it back.

    `correction_id` is null when the datum was never brought from the portal:
    the change is recorded in the history all the same (RF-09), but there is no
    original value to keep and nothing to give back (RF-33).
    """

    correction_id: int | None
    product_id: int
    entity_type: str
    field: str
    portal_value: Any | None
    value: Any
    status: CorrectionStatus | None


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
    # The fields of this row somebody corrected by hand (RF-26, RF-27, RF-28).
    corrections: list[CorrectionMark] = []


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
    # Shown on the datum's own screen, which is where a conflict is resolved:
    # the spec is explicit that there is no separate queue for them (RF-28).
    corrections: list[CorrectionMark] = []
