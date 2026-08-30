"""HTTP routes for the sales module.

Purchasing reaches none of them: RF-08 of 009 keeps the commercial dashboard and
the sales records to whoever sells — and to the owner, who is admitted
everywhere. Resolving a held record is sales' and the owner's alone (RF-29).
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.modules.identity.dependencies import CurrentUser, Level, Section, require_section
from app.modules.sales.models import SaleState
from app.modules.sales.schemas import (
    ReviewQueue,
    SaleCorrection,
    SaleList,
    SaleRead,
    SaleResolution,
    SalesDashboard,
)
from app.modules.sales.service import SalesService

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

Session = Annotated[AsyncSession, Depends(get_session)]


def get_sales_service(session: Session) -> SalesService:
    """Provide the sales service for a request."""
    return SalesService(session)


SalesDep = Annotated[SalesService, Depends(get_sales_service)]

router = APIRouter(prefix="/sales", tags=["Sales"])
dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "",
    dependencies=[require_section(Section.SALES, Level.READ)],
    summary="The sales records",
)
async def list_sales(
    service: SalesDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    state: Annotated[SaleState | None, Query(description="By state")] = None,
    since: Annotated[date | None, Query(description="From this date")] = None,
    until: Annotated[date | None, Query(description="Up to this date")] = None,
) -> SaleList:
    """The owner and sales. Purchasing is refused (RF-08 of 009)."""
    return await service.list_sales(skip=skip, limit=limit, state=state, since=since, until=until)


@router.get(
    "/review",
    dependencies=[require_section(Section.SALES, Level.WRITE)],
    summary="The sales waiting for a decision",
)
async def review_queue(service: SalesDep) -> ReviewQueue:
    """The owner and sales (RF-13, RF-14, RF-23, RF-26, RF-28, RF-30 of 009)."""
    return await service.review_queue()


@router.post(
    "/groups/{code_key}/resolution",
    dependencies=[require_section(Section.SALES, Level.WRITE)],
    summary="Decide about a repeated sale",
)
async def resolve_group(
    code_key: str, payload: SaleResolution, current_user: CurrentUser, service: SalesDep
) -> list[SaleRead]:
    """The owner and sales, and nobody else (RF-29, RF-31 to RF-34, RF-36)."""
    return await service.resolve_group(
        code_key,
        action=payload.action,
        sale_id=payload.sale_id,
        actor_user_id=current_user.id,
    )


@router.delete(
    "/groups/{code_key}/resolution",
    dependencies=[require_section(Section.SALES, Level.WRITE)],
    summary="Undo the decision about a repeated sale",
)
async def undo_resolution(code_key: str, service: SalesDep) -> list[SaleRead]:
    """The owner and sales (RF-35 of 009). The indicators recalculate with it."""
    return await service.undo_resolution(code_key)


@router.patch(
    "/{sale_id}",
    dependencies=[require_section(Section.SALES, Level.WRITE)],
    summary="Correct a held sale, or estimate what cannot be known",
)
async def correct_sale(
    sale_id: int, payload: SaleCorrection, current_user: CurrentUser, service: SalesDep
) -> SaleRead:
    """The owner and sales (RF-38, RF-39, RF-41 of 009).

    What the portal reported is kept whatever is corrected, and a value the
    person estimated is marked as such wherever it is added up.
    """
    return await service.correct_sale(
        sale_id,
        values={
            "sold_on": payload.sold_on,
            "product_code": payload.product_code,
            "quantity": payload.quantity,
            "total": payload.total,
        },
        is_estimated=payload.is_estimated,
        actor_user_id=current_user.id,
    )


@dashboard_router.get(
    "/sales",
    dependencies=[require_section(Section.DASHBOARD, Level.READ)],
    summary="What the business invoiced, and what was left out of the number",
)
async def sales_dashboard(
    service: SalesDep,
    since: Annotated[date | None, Query(description="From this date")] = None,
    until: Annotated[date | None, Query(description="Up to this date")] = None,
) -> SalesDashboard:
    """The owner and sales (RF-03 to RF-07, RF-25 to RF-28 of 009).

    Each cut takes its own window, which is RF-05: choosing a period here
    changes this number and no other.
    """
    return await service.dashboard(since=since, until=until)
