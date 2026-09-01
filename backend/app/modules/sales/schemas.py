"""Sales schemas: the records, the ones held back, and the numbers built on them."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.sales.models import SaleState


class SaleRead(BaseModel):
    """One sales record, with why it is where it is."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    code_key: str
    sold_on: date | None
    product_code: str | None
    quantity: int | None
    total: Decimal | None
    state: SaleState
    reason: str | None
    portal_values: dict[str, Any] | None
    is_estimated: bool
    duplicate_of_sale_id: int | None
    resolved_by_user_id: int | None
    resolved_at: datetime | None


class SaleList(BaseModel):
    """A page of sales records."""

    items: list[SaleRead]
    total: int
    skip: int
    limit: int


class SaleGroup(BaseModel):
    """Two or more records that share a code, side by side (RF-30 of 009).

    `differences` names the fields they disagree on, so the screen can mark them
    instead of leaving a person to compare row by row.
    """

    code_key: str
    versions: list[SaleRead]
    differences: list[str]


class ReviewQueue(BaseModel):
    """What is waiting for a person: the repeated ones, and the broken ones."""

    groups: list[SaleGroup]
    broken: list[SaleRead]
    pending_groups: int
    held: int


class ResolvedGroup(BaseModel):
    """A repeated sale somebody already decided about (RF-34, RF-35, RF-36).

    The three requirements are one screen: the discarded version stays visible
    beside the chosen one (RF-34), the case says what was decided, by whom and
    when (RF-36), and from there the decision can be undone (RF-35).

    `resolved_by_name` is filled at the edge, by the route, never here: this
    module stores an id and cannot name a person without importing `identity`
    (Artículo IV). Writing "el usuario 3" would not meet RF-36, it would
    simulate meeting it.
    """

    code_key: str
    versions: list[SaleRead]
    action: str
    kept_sale_id: int | None
    resolved_at: datetime | None
    resolved_by_user_id: int | None
    resolved_by_name: str | None = None


class SaleResolution(BaseModel):
    """What somebody decided about a repeated sale (RF-31, RF-32 of 009)."""

    # `keep` chooses which version is the valid one; `distinct` declares that
    # they are different sales that happen to share a code.
    action: str = Field(pattern="^(keep|distinct)$")
    sale_id: int | None = None


class SaleCorrection(BaseModel):
    """A value of a held record, corrected or estimated (RF-38, RF-39 of 009)."""

    sold_on: date | None = None
    product_code: str | None = Field(default=None, max_length=64)
    quantity: int | None = None
    total: Decimal | None = None
    # Says the value is what the person believes rather than what is known. Every
    # indicator built on it reports that (RF-40).
    is_estimated: bool = False


class MonthTotal(BaseModel):
    """One month of the invoicing curve (RF-03 of 009)."""

    month: date
    total: Decimal
    sales: int


class Indicator(BaseModel):
    """One number of the dashboard, with what it left out of itself.

    `excluded` is part of the number and not a footnote: RF-25 asks every
    indicator to report how many records it left out, and RF-27 that it says so
    even when it left out none.
    """

    value: Decimal
    sales: int
    excluded: int
    # How many of the excluded were unified by the platform on its own, because
    # they repeated another record with nothing different about them (RF-12).
    # The rest of `excluded` is what a person set aside or what is still waiting
    # for one, and lumping the two together answers neither question.
    merged: int = 0
    has_estimates: bool = False


class SalesDashboard(BaseModel):
    """The commercial dashboard over one window (RF-03 to RF-07, RF-25 to RF-28)."""

    since: date | None
    until: date | None
    invoiced: Indicator
    by_month: list[MonthTotal]
    held_total: int
    pending_groups: int
    # Cuántas decisiones de ventas hay realmente esperando a alguien: los grupos
    # de repetidas sin resolver **más** las apartadas sueltas.
    #
    # Existe porque `excluded` contesta otra pregunta y las dos se estaban
    # leyendo como la misma. `excluded` cuenta **registros que no suman**, y ahí
    # entran los que el sistema unificó solo y los que una persona ya descartó:
    # noventa y seis registros afuera del total podían ser trece decisiones
    # pendientes, y el tablero ofrecía «ver cuáles» sobre los noventa y seis.
    pending_decisions: int
