"""HTTP routes for the catalog module.

Two routers. `/prices` is what everybody reads: these are the supplier's
prices, not the company's margins, so purchasing and sales can both look at
them (a business rule of the spec, not a technical detail).

`/catalog` is where a person changes one by hand, and its two routes are
deliberately asymmetric:

* **correcting** asks for the section the datum belongs to — the product
  catalog, which is the owner and sales (RF-24). Who may correct depends on
  whose datum it is.
* **undoing a correction** is the owner's alone (RF-30), whatever the datum.
  That is a different question, so it asks for a different section.

Authorisation comes from `identity.dependencies`, which is the one thing that
crosses a module boundary — a request has to know whether it may continue
before its handler runs, and an event cannot answer that in time.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.modules.catalog.schemas import (
    CorrectionRead,
    CorrectionWrite,
    PriceHistoryRead,
    PriceList,
)
from app.modules.catalog.service import CatalogService
from app.modules.identity.dependencies import (
    CurrentUser,
    Level,
    Section,
    get_current_user,
    require_section,
)

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500

Session = Annotated[AsyncSession, Depends(get_session)]


def get_catalog_service(session: Session) -> CatalogService:
    """Provide the catalog service for a request."""
    return CatalogService(session)


CatalogDep = Annotated[CatalogService, Depends(get_catalog_service)]

SkipParam = Annotated[int, Query(ge=0, description="Rows to skip")]
LimitParam = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE, description="Rows per page")]
SearchParam = Annotated[str | None, Query(max_length=500, description="Match code or description")]
HighlightedParam = Annotated[bool, Query(description="Only the rises above the threshold")]

router = APIRouter(prefix="/prices", tags=["Prices"])
corrections_router = APIRouter(prefix="/catalog", tags=["Corrections"])


@router.get(
    "",
    dependencies=[Depends(get_current_user)],
    summary="The price list in force",
)
async def list_prices(
    service: CatalogDep,
    skip: SkipParam = 0,
    limit: LimitParam = DEFAULT_PAGE_SIZE,
    q: SearchParam = None,
    highlighted: HighlightedParam = False,
) -> PriceList:
    """Every authenticated role: the owner, purchasing and sales."""
    return await service.list_prices(skip=skip, limit=limit, query=q, highlighted=highlighted)


@router.get(
    "/{product_id}/history",
    dependencies=[Depends(get_current_user)],
    summary="How the price of a product evolved",
)
async def price_history(product_id: int, service: CatalogDep) -> PriceHistoryRead:
    """Every authenticated role."""
    return await service.price_history(product_id)


@corrections_router.post(
    "/products/{product_id}/corrections",
    dependencies=[require_section(Section.PRODUCT_CATALOG, Level.WRITE)],
    summary="Correct a value of a product by hand",
)
async def correct_product(
    product_id: int,
    payload: CorrectionWrite,
    current_user: CurrentUser,
    service: CatalogDep,
) -> CorrectionRead:
    """The owner and sales: the catalog and its prices are theirs (RF-24).

    Any field the portal brought, not only the amounts (RF-23), always with a
    reason picked from the list (RF-11). What the portal had said is kept
    (RF-25), and who changed it is taken from the token rather than the body.
    """
    return await service.apply_correction(
        product_id=product_id,
        field=payload.field,
        value=payload.value,
        reason_code=payload.reason_code,
        reason_detail=payload.reason_detail,
        actor_user_id=current_user.id,
    )


@corrections_router.delete(
    "/corrections/{correction_id}",
    dependencies=[require_section(Section.MANUAL_CORRECTIONS, Level.WRITE)],
    summary="Undo a manual correction",
)
async def revert_correction(
    correction_id: int, current_user: CurrentUser, service: CatalogDep
) -> CorrectionRead:
    """The owner alone (RF-30), even over a datum somebody else corrected.

    The datum goes back to the value the portal reported (RF-31) and the
    correction is marked as undone with who and when — never deleted (RF-32).
    A datum the portal never brought has no correction, so this answers 404
    rather than inventing one to undo (RF-33).
    """
    return await service.revert_correction(correction_id, actor_user_id=current_user.id)
