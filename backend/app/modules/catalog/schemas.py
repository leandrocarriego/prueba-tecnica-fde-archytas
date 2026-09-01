"""Catalog schemas: the HTTP contract of the prices screen and the product page."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.catalog.models import AliasSource, CorrectionStatus, PriceSource, ProductStatus

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


class CorrectionInForceRead(CorrectionMark):
    """A standing correction, said in the words a screen away from the datum needs.

    `CorrectionMark` is enough on the product's own page: the page already knows
    which datum it is about. The change log does not — it shows the corrections
    of many data at once — so which datum a correction stands on travels with
    it, in the same vocabulary the log writes (`catalog.product_price`, the
    product id as text). That is what lets the log offer the undo beside the row
    that reported the correction (RF-30) instead of only linking away to it.
    """

    entity_type: str
    entity_id: str


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


# --- The rubros of the catalog (008) --------------------------------------


class CategoryAliasRead(BaseModel):
    """One written form pointing at a rubro, as the screens show it (RF-03, RF-27)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    text_original: str
    text_normalized: str
    rule_id: int | None
    source: AliasSource
    created_at: datetime


class CategoryRead(BaseModel):
    """A rubro with what the screen shows next to it: its count and its forms."""

    id: int
    name: str
    product_count: int
    aliases: list[CategoryAliasRead]


class CategoryList(BaseModel):
    """The rubros, plus «sin rubro» as one more group (RF-09, RF-10, RF-11)."""

    items: list[CategoryRead]
    # Not a row of `core.category`: null is «sin rubro», and it is reported
    # beside the list so every cut adds up to the total (RF-10).
    unclassified_count: int
    # How many of those are waiting on a decision about their written form,
    # which is not the same number: a product that arrived with no category
    # at all is «sin rubro» and has nothing under review (RF-26).
    pending_review_count: int
    total_products: int


class CategoryWrite(BaseModel):
    """The name of a rubro, on the way in (RF-05, RF-06)."""

    name: str = Field(min_length=1, max_length=100)


class UnclassifiedProduct(BaseModel):
    """A product with no rubro, with the proposal the system derived — or none.

    `proposed_category_id` is computed on the way out and stored nowhere: while
    nobody confirms it the product **is** «sin rubro», it counts as such and it
    stays in this queue (RF-16).
    """

    product_id: int
    code: str
    description: str
    category_raw: str | None
    subcategory_raw: str | None
    proposed_category_id: int | None = None
    proposed_category_name: str | None = None


class UnclassifiedList(BaseModel):
    """A page of the queue of products waiting for a rubro (RF-11, RF-12)."""

    items: list[UnclassifiedProduct]
    total: int
    skip: int
    limit: int


class ProductCategoryWrite(BaseModel):
    """The rubro somebody chose for a product.

    Confirming the proposal and correcting it are the same write, and the only
    difference is which rubro travels: the system has no reason to tell them
    apart, and does not (RF-15).
    """

    category_id: int


# --- The cuts of the dashboard that come from the catalog (009) -----------


class PriceCurvePoint(BaseModel):
    """One month of the curve of what the supplier charges (RF-42 of 009)."""

    month: date
    average_price: Decimal
    changes: int


class StockCut(BaseModel):
    """What one product had at the start and at the end of the window (RF-43)."""

    product_id: int
    code: str
    description: str
    opening: int | None
    closing: int | None
    ran_out: bool = False


class NewProductRead(BaseModel):
    """A product the catalog started to know inside the window (RF-45)."""

    product_id: int
    code: str
    description: str
    first_seen_at: datetime


class CatalogDashboard(BaseModel):
    """The three cuts of the dashboard that are about the catalog.

    `excluded` travels with each of them, and is reported even when it is zero:
    RF-46 asks each cut to say how many records it left out, and RF-27 that it
    say so when it left out none.
    """

    since: date | None
    until: date | None
    price_curve: list[PriceCurvePoint]
    price_curve_excluded: int
    stock: list[StockCut]
    stock_excluded: int
    new_products: list[NewProductRead]
    new_products_excluded: int = 0
