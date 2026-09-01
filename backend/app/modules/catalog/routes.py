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

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.modules.catalog.schemas import (
    CatalogDashboard,
    CategoryAliasRead,
    CategoryList,
    CategoryRead,
    CategoryWrite,
    CorrectionInForceRead,
    CorrectionRead,
    CorrectionWrite,
    PriceHistoryRead,
    PriceList,
    PriceSummary,
    ProductCategoryWrite,
    UnclassifiedList,
    UnclassifiedProduct,
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
# How many products one question about standing corrections may name. A page
# of the change log is fifty rows, so this is room to spare and still a bound.
MAX_ENTITIES = 200

Session = Annotated[AsyncSession, Depends(get_session)]


def get_catalog_service(session: Session) -> CatalogService:
    """Provide the catalog service for a request."""
    return CatalogService(session)


CatalogDep = Annotated[CatalogService, Depends(get_catalog_service)]

SkipParam = Annotated[int, Query(ge=0, description="Rows to skip")]
LimitParam = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE, description="Rows per page")]
SearchParam = Annotated[str | None, Query(max_length=500, description="Match code or description")]
HighlightedParam = Annotated[bool, Query(description="Only the rises above the threshold")]
ChangedParam = Annotated[bool, Query(description="Only rows whose price moved from the last one")]
CategoryParam = Annotated[int | None, Query(description="Only products under this rubro")]

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
    changed: ChangedParam = False,
    category_id: CategoryParam = None,
) -> PriceList:
    """Every authenticated role: the owner, purchasing and sales."""
    return await service.list_prices(
        skip=skip,
        limit=limit,
        query=q,
        highlighted=highlighted,
        changed=changed,
        category_id=category_id,
    )


# A literal segment, declared before `/{product_id}/history` so it is never read
# as a product id.
@router.get(
    "/summary",
    dependencies=[Depends(get_current_user)],
    summary="The four counts on top of the price list",
)
async def price_summary(service: CatalogDep) -> PriceSummary:
    """The whole-catalog movement of the last sync: rose, fell, new without a
    rubro, and stopped coming. Every authenticated role."""
    return await service.price_summary()


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


@corrections_router.get(
    "/corrections",
    dependencies=[require_section(Section.MANUAL_CORRECTIONS)],
    summary="The corrections still standing on a set of products",
)
async def corrections_in_force(
    product_id: Annotated[list[int], Query(min_length=1, max_length=MAX_ENTITIES)],
    service: CatalogDep,
) -> list[CorrectionInForceRead]:
    """The owner alone, and for the same reason the undo below is.

    It is asked by the change log, which lists corrections of many products at
    once and offers the undo beside each row (RF-30): without it the screen
    would know that something was corrected and not which correction to undo.
    Whoever cannot undo never gets here, so the ids are not handed to a screen
    that has no use for them.

    The products come as repeated `product_id`, bounded like a page of the log:
    one query for the page instead of one request per row.
    """
    return await service.corrections_in_force(product_id)


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


# --- The rubros of the catalog (008, amended by 010) -----------------------
#
# **Writing is the owner's and purchasing's**, and reading is for the three
# roles. That is the correction the 010 makes to the 008: a rubro is the
# category something is bought under, so whoever sees the goods arrive is who
# decides it. Sales keeps the consultation and loses the change (RF-10, RF-11).
#
# None of the `require_section` below changed when that moved: they already ask
# for `PRODUCT_CATEGORIES`, and **who reaches it is decided in one place**, the
# matrix of `identity`. A feature that had to edit nine routes to move a
# permission would be a matrix that is not doing its job.
#
# The literal paths are declared **before** `/{category_id}` so `/unclassified`
# is never read as an id.

categories_router = APIRouter(prefix="/categories", tags=["Categories"])
products_router = APIRouter(prefix="/products", tags=["Categories"])


@categories_router.get(
    "",
    dependencies=[require_section(Section.PRODUCT_CATEGORIES, Level.READ)],
    summary="The rubros, with their count and their written forms",
)
async def list_categories(service: CatalogDep) -> CategoryList:
    """The three roles, sales included (RF-10 of 010)."""
    return await service.list_categories()


@categories_router.get(
    "/unclassified",
    dependencies=[require_section(Section.PRODUCT_CATEGORIES, Level.READ)],
    summary="The products waiting for a rubro",
)
async def list_unclassified(
    service: CatalogDep, skip: SkipParam = 0, limit: LimitParam = DEFAULT_PAGE_SIZE
) -> UnclassifiedList:
    """The three roles. Each product carries its proposal, or none (RF-13 of 010)."""
    return await service.unclassified(skip=skip, limit=limit)


@categories_router.get(
    "/aliases",
    dependencies=[require_section(Section.PRODUCT_CATEGORIES, Level.READ)],
    summary="The equivalences in force",
)
async def list_aliases(service: CatalogDep) -> list[CategoryAliasRead]:
    """The three roles (RF-27 of 008, RF-10 of 010)."""
    return await service.list_aliases()


@categories_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_section(Section.PRODUCT_CATEGORIES, Level.WRITE)],
    summary="Add a rubro",
)
async def create_category(
    payload: CategoryWrite, current_user: CurrentUser, service: CatalogDep
) -> CategoryRead:
    """The owner and purchasing (RF-01 of 010, which replaces RF-05 of 008)."""
    return await service.create_category(name=payload.name, actor_user_id=current_user.id)


@categories_router.patch(
    "/{category_id}",
    dependencies=[require_section(Section.PRODUCT_CATEGORIES, Level.WRITE)],
    summary="Change the name of a rubro",
)
async def rename_category(
    category_id: int, payload: CategoryWrite, current_user: CurrentUser, service: CatalogDep
) -> CategoryRead:
    """The owner and purchasing (RF-02 of 010, which replaces RF-06 of 008)."""
    return await service.rename_category(
        category_id, name=payload.name, actor_user_id=current_user.id
    )


@categories_router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_section(Section.PRODUCT_CATEGORIES, Level.WRITE)],
    summary="Remove a rubro",
)
async def delete_category(category_id: int, current_user: CurrentUser, service: CatalogDep) -> None:
    """The owner and purchasing. Refused, with the reason, if anything points at it (RF-03)."""
    await service.delete_category(category_id, actor_user_id=current_user.id)


@products_router.put(
    "/{product_id}/category",
    dependencies=[require_section(Section.PRODUCT_CATEGORIES, Level.WRITE)],
    summary="Give a product its rubro",
)
async def set_product_category(
    product_id: int,
    payload: ProductCategoryWrite,
    current_user: CurrentUser,
    service: CatalogDep,
) -> UnclassifiedProduct:
    """The owner and purchasing (RF-04, RF-05 and RF-13 of 010).

    Confirming the proposal and correcting it are this same call. Who decided
    comes from the token, never from the body (RF-18 of 008).
    """
    return await service.set_product_category(
        product_id, category_id=payload.category_id, actor_user_id=current_user.id
    )


catalog_dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@catalog_dashboard_router.get(
    "/catalog",
    dependencies=[require_section(Section.DASHBOARD, Level.READ)],
    summary="What the supplier charged, what the stock did, and what is new",
)
async def catalog_dashboard(
    service: CatalogDep,
    since: Annotated[date | None, Query(description="From this date")] = None,
    until: Annotated[date | None, Query(description="Up to this date")] = None,
) -> CatalogDashboard:
    """The owner and sales (RF-42 to RF-46 of 009).

    Its own window, independent of the other cuts of the dashboard (RF-05).
    """
    return await service.dashboard(since=since, until=until)
