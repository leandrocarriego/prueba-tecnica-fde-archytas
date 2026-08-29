"""HTTP routes for the operations module.

Two routers, because they have different audiences. `health_router` is
infrastructure: it is public, unauthenticated, and `app.main` mounts it both
under the API prefix and at the root so Docker can reach it without knowing the
API version. `router` is the operations console — job history and business
parameters — and every route on it declares who may call it.

Authorisation comes from `identity.dependencies`, which is identity's HTTP
composition surface over `IdentityService`. Note what is *not* imported: no
repository and no model. In particular the `UserRole` enum stays inside
identity, so owner-only routes are written as `require_roles()` with no
operational role, which is exactly what that helper documents.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.modules.identity.dependencies import (
    CurrentUser,
    Level,
    Section,
    get_current_user,
    require_section,
)
from app.modules.operations.models import JobStatus
from app.modules.operations.schemas import (
    HealthRead,
    HealthState,
    JobRunList,
    JobRunRead,
    ParameterRead,
    ParameterUpdateRequest,
    PriceUpdateRequested,
    PriceUpdateSettingsRead,
    PriceUpdateSettingsWrite,
    PriceUpdateStatusRead,
)
from app.modules.operations.service import OperationsService

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

Session = Annotated[AsyncSession, Depends(get_session)]


def get_operations_service(session: Session) -> OperationsService:
    """Provide the operations service for a request."""
    return OperationsService(session)


OperationsDep = Annotated[OperationsService, Depends(get_operations_service)]

SkipParam = Annotated[int, Query(ge=0, description="Rows to skip")]
LimitParam = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE, description="Rows per page")]
TaskNameParam = Annotated[str | None, Query(max_length=255, description="Filter by task")]
StatusParam = Annotated[JobStatus | None, Query(description="Filter by run status")]

health_router = APIRouter(tags=["Health"])
router = APIRouter(prefix="/operations", tags=["Operations"])
price_updates_router = APIRouter(prefix="/price-updates", tags=["Price updates"])


@health_router.get(
    "/health",
    summary="Service and database health",
    responses={http_status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "A dependency is down"}},
)
async def health(response: Response, service: OperationsDep) -> HealthRead:
    """Public and unauthenticated: Docker's healthcheck calls it before anyone logs in.

    It answers 503 rather than 200 when a dependency is down, because an
    orchestrator restarts on the status code, not on the body.
    """
    report = await service.health()
    if report.status is not HealthState.OK:
        response.status_code = http_status.HTTP_503_SERVICE_UNAVAILABLE
    return report


@router.get(
    "/jobs",
    dependencies=[Depends(get_current_user)],
    summary="Recent background runs",
)
async def list_jobs(
    service: OperationsDep,
    skip: SkipParam = 0,
    limit: LimitParam = DEFAULT_PAGE_SIZE,
    task_name: TaskNameParam = None,
    status: StatusParam = None,
) -> JobRunList:
    """Every authenticated role.

    Whoever handles purchasing needs to know whether last night's extraction
    ran, without having to ask the owner.
    """
    items, total = await service.list_runs(
        skip=skip, limit=limit, task_name=task_name, status=status
    )
    return JobRunList(items=items, total=total, skip=skip, limit=limit)


@router.get(
    "/parameters",
    dependencies=[require_section(Section.SYSTEM_PARAMETERS)],
    summary="Read the business parameters",
)
async def list_parameters(service: OperationsDep) -> list[ParameterRead]:
    """Owner only: these values decide how the platform behaves."""
    return await service.list_parameters()


@router.put(
    "/parameters",
    dependencies=[require_section(Section.SYSTEM_PARAMETERS, Level.WRITE)],
    summary="Update the business parameters",
)
async def update_parameters(
    payload: ParameterUpdateRequest, service: OperationsDep
) -> list[ParameterRead]:
    """Owner only.

    The whole set is written in one transaction, so the platform never runs on
    half of the old rules and half of the new ones.
    """
    return await service.set_parameters(payload.items)


# --- The price update ----------------------------------------------------
#
# Four routes about the update itself rather than about the prices it brings, so
# they live here and not in `catalog`: what ran, asking for a run, and the two
# parameters the owner decides.


@price_updates_router.get(
    "/status",
    dependencies=[Depends(get_current_user)],
    summary="The state of the price update",
)
async def price_update_status(service: OperationsDep) -> PriceUpdateStatusRead:
    """Every authenticated role.

    It answers the last **successful** update (RF-09) and whether the update is
    interrupted (RF-11), which is what the prices screen shows at the top.
    """
    return await service.price_update_status()


@price_updates_router.post(
    "",
    status_code=http_status.HTTP_202_ACCEPTED,
    dependencies=[require_section(Section.PRICES, Level.WRITE)],
    summary="Bring the list now",
)
async def request_price_update(
    current_user: CurrentUser, service: OperationsDep
) -> PriceUpdateRequested:
    """The owner and purchasing, and nobody else.

    Asking for the list by hand is knocking on a third party's door, so it is
    not a read that any role can do. Who asked is taken from the token and
    recorded with the run (RF-17); a second request while one is running is
    answered with a 409 rather than starting another (RF-15).
    """
    return await service.request_price_update(requested_by_user_id=current_user.id)


@price_updates_router.get(
    "/settings",
    dependencies=[require_section(Section.SYSTEM_PARAMETERS)],
    summary="The two parameters of the price update",
)
async def read_price_update_settings(service: OperationsDep) -> PriceUpdateSettingsRead:
    """Owner only: these values decide how the platform behaves."""
    return await service.price_update_settings()


@price_updates_router.put(
    "/settings",
    dependencies=[require_section(Section.SYSTEM_PARAMETERS, Level.WRITE)],
    summary="Change how often and what counts as a big rise",
)
async def write_price_update_settings(
    payload: PriceUpdateSettingsWrite, service: OperationsDep
) -> PriceUpdateSettingsRead:
    """Owner only (RF-18, RF-19). The new frequency applies from the next query."""
    return await service.set_price_update_settings(payload)


@price_updates_router.get(
    "/{job_run_id}",
    dependencies=[require_section(Section.PRICES, Level.WRITE)],
    summary="How one update ended",
)
async def read_price_update(job_run_id: int, service: OperationsDep) -> JobRunRead:
    """The owner and purchasing.

    Deliberately a different route from `/status`: that one reports the last
    **successful** update, so a run that failed would never show up there and
    whoever asked for it would never learn that it failed (RF-16).
    """
    return await service.get_run(job_run_id)
