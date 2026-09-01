"""HTTP routes for the operations module.

Two routers, because they have different audiences. `health_router` is
infrastructure: it is public, unauthenticated, and `app.main` mounts it both
under the API prefix and at the root so Docker can reach it without knowing the
API version. `router` is the operations console — job history, the business
parameters and the log of manual changes — and every route on it declares who
may call it.

Authorisation comes from `identity.dependencies`, which is identity's HTTP
composition surface over `IdentityService`. Note what is *not* imported: no
repository and no model. The `UserRole` enum stays inside identity, so a route
asks for a section and a level (`require_section`) and never names a role.

The log is the one place where the answer is not a yes or a no: `/audit` admits
every session and narrows *what it returns* to the sections the caller reaches,
because RF-19 asks for a smaller list rather than a closed door.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.modules.identity.dependencies import (
    ActorDirectoryDep,
    CurrentUser,
    Level,
    Section,
    VisibleSections,
    get_current_user,
    require_section,
)
from app.modules.operations.models import JobStatus
from app.modules.operations.schemas import (
    AuditEntryList,
    AuditEntryRead,
    CorrectionReasonRead,
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
    SyncRequested,
    SyncSourceRead,
)
from app.modules.operations.service import OperationsService
from app.quality import Quality
from app.shared.time import as_business_time

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
ActorParam = Annotated[int | None, Query(ge=1, description="Filter by who made the change")]
# A moment with no offset is read on the shop's clock, not on UTC: a filter
# typed as a date means that day in Buenos Aires, and three hours of the wrong
# day at each end is exactly the bug `frontend/lib/time.ts` exists to prevent.
SinceParam = Annotated[datetime | None, Query(description="Changes from this moment on")]
UntilParam = Annotated[datetime | None, Query(description="Changes up to this moment")]
EntityTypeParam = Annotated[str, Path(max_length=100, description="The kind of datum")]
EntityIdParam = Annotated[str, Path(max_length=100, description="Its identifier in its module")]

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
    "/quality",
    dependencies=[Depends(get_current_user)],
    summary="Tests and coverage of the build this image came from",
)
async def read_quality(service: OperationsDep) -> Quality | None:
    """Every authenticated role, and nobody else.

    `/health` is public and deliberately says nothing about this: how well the
    system is tested is a fact about the people who build it, not something to
    be read off the internet by anyone who finds the domain.

    `None` when the image carries no snapshot. Saying nothing is the honest
    answer to "we do not know"; a number nobody measured would not be.
    """
    return service.quality()


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
    payload: ParameterUpdateRequest, current_user: CurrentUser, service: OperationsDep
) -> list[ParameterRead]:
    """Owner only (RF-02, RF-03).

    The whole set is written in one transaction, so the platform never runs on
    half of the old rules and half of the new ones. A key outside the catalog
    or a value outside its range is refused with the range in the message
    (RF-06), and who changed what is taken from the token, never from the body
    (RF-08).
    """
    return await service.set_parameters(payload.items, actor_user_id=current_user.id)


# --- The log of manual changes -------------------------------------------
#
# Deliberately **not** owner-only. RF-19 says everybody else reads the changes
# of the sections they reach, so the route admits any session and the filter is
# applied inside the query, from what `identity` answers about the caller.


@router.get(
    "/audit",
    dependencies=[Depends(get_current_user)],
    summary="The history of manual changes",
)
async def list_audit(
    sections: VisibleSections,
    directory: ActorDirectoryDep,
    service: OperationsDep,
    skip: SkipParam = 0,
    limit: LimitParam = DEFAULT_PAGE_SIZE,
    actor_user_id: ActorParam = None,
    since: SinceParam = None,
    until: UntilParam = None,
) -> AuditEntryList:
    """Every authenticated role, each seeing their own sections.

    The owner reaches all three and therefore sees everybody (RF-18); anybody
    else sees the sections they reach and nothing else (RF-19). Newest first
    (RF-13), filterable by person and by date range (RF-14).
    """
    page = await service.list_audit(
        sections=sorted(sections),
        skip=skip,
        limit=limit,
        actor_user_id=actor_user_id,
        since=as_business_time(since),
        until=as_business_time(until),
    )
    await _name_the_authors(page.items, directory)
    return page


@router.get(
    "/audit/{entity_type}/{entity_id}",
    dependencies=[Depends(get_current_user)],
    summary="The history of one datum",
)
async def audit_for_entity(
    entity_type: EntityTypeParam,
    entity_id: EntityIdParam,
    sections: VisibleSections,
    directory: ActorDirectoryDep,
    service: OperationsDep,
) -> list[AuditEntryRead]:
    """Every authenticated role, filtered by section like the listing.

    It exists so a corrected datum leads to its own history without anybody
    having to go looking for it on another screen (RF-15).
    """
    entries = await service.audit_for_entity(entity_type, entity_id, sections=sorted(sections))
    await _name_the_authors(entries, directory)
    return entries


async def _name_the_authors(entries: list[AuditEntryRead], directory: ActorDirectoryDep) -> None:
    """Put a name next to each id, here and not in the service.

    `operations` stores who made a change as an id and deliberately holds no
    foreign key to `users`: two modules' schemas do not get to depend on each
    other. The name is a rendering concern, so it is resolved at the edge, by
    the one file of `identity` another module may import.
    """
    names = await directory.names_for({entry.actor_user_id for entry in entries})
    for entry in entries:
        entry.actor_name = names.get(entry.actor_user_id)


@router.get(
    "/corrections/reasons",
    dependencies=[Depends(get_current_user)],
    summary="The reasons a correction may be given",
)
async def correction_reasons(service: OperationsDep) -> list[CorrectionReasonRead]:
    """Every authenticated role.

    Served by the API because the API is what validates the code (RF-11): the
    list and the rule that checks it come from the same place.
    """
    return service.correction_reasons()


# --- Las seis fuentes, juntas --------------------------------------------
#
# Todo lo que la plataforma sabe lo trajo del portal, y hasta acá cada
# extracción se administraba por su cuenta: cuatro parámetros de frecuencia
# repartidos entre dieciséis tarjetas y un solo botón de «traerlo ahora», el de
# la lista de precios, porque fue la primera que se construyó. Estas dos rutas
# son el panel que las mira juntas.
#
# Van en `router` —el prefijo `/operations`— y bajo `SYSTEM_PARAMETERS`, que es
# la sección de la pantalla donde viven: es el dueño el que decide cada cuánto
# se le golpea la puerta a un sistema ajeno. La lista de precios conserva además
# su propio botón en `/precios`, bajo `PRICES`, para que compras la siga
# pudiendo pedir sin entrar a la configuración.


@router.get(
    "/syncs",
    dependencies=[require_section(Section.SYSTEM_PARAMETERS)],
    summary="En qué anda cada fuente de datos",
)
async def list_syncs(service: OperationsDep) -> list[SyncSourceRead]:
    """Owner only: es la pantalla donde se decide cada cuánto se consulta."""
    return await service.update_sources()


@router.post(
    "/syncs/{key}",
    status_code=http_status.HTTP_202_ACCEPTED,
    dependencies=[require_section(Section.SYSTEM_PARAMETERS, Level.WRITE)],
    summary="Traer una fuente ahora",
)
async def request_sync(
    key: Annotated[str, Path(description="Cuál de las seis fuentes")],
    current_user: CurrentUser,
    service: OperationsDep,
) -> SyncRequested:
    """Owner only.

    Pedir una extracción a mano es golpear la puerta de un tercero, así que no
    es una lectura que cualquier rol pueda hacer. Quién la pidió sale del token
    y queda con la corrida; una segunda mientras hay una corriendo se contesta
    con 409 en vez de abrir otra.
    """
    return await service.request_manual_sync(key, requested_by_user_id=current_user.id)


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
    payload: PriceUpdateSettingsWrite, current_user: CurrentUser, service: OperationsDep
) -> PriceUpdateSettingsRead:
    """Owner only (RF-18, RF-19). The new frequency applies from the next query.

    The two keys it writes are the same ones the general parameters panel
    writes, so a change here is validated, logged and published exactly like
    one made there.
    """
    return await service.set_price_update_settings(payload, actor_user_id=current_user.id)


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
