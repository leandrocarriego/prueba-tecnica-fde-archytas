"""HTTP routes for the catalog module.

Both routes are readable by every operational role: these are the supplier's
prices, not the company's margins, so purchasing and sales can both look at them
(a business rule of the spec, not a technical detail).

Authorisation comes from `identity.dependencies`, which is the one thing that
crosses a module boundary — a request has to know whether it may continue
before its handler runs, and an event cannot answer that in time.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.modules.catalog.schemas import PriceHistoryRead, PriceList
from app.modules.catalog.service import CatalogService
from app.modules.identity.dependencies import get_current_user

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
