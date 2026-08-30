"""HTTP routes for the notifications module.

The owner's alone: deciding who gets told what is a decision about the team, and
`SYSTEM_PARAMETERS` is the section that already means "the settings of the
platform itself".
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.modules.identity.dependencies import CurrentUser, Level, Section, require_section
from app.modules.notifications.models import AlertKind
from app.modules.notifications.repository import NotificationsRepository
from app.modules.notifications.schemas import RouteRead, RouteWrite
from app.modules.notifications.service import DEFAULT_ROUTES

Session = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get(
    "/routes",
    dependencies=[require_section(Section.SYSTEM_PARAMETERS, Level.READ)],
    summary="Who receives each kind of alert",
)
async def list_routes(session: Session) -> list[RouteRead]:
    """The owner (RF-37 of 007).

    Every kind is listed, including the ones nobody has configured: those show
    the value that was signed, which is what the platform is actually obeying.
    """
    repository = NotificationsRepository(session)
    stored = await repository.routes()
    return [
        RouteRead(
            kind=kind,
            role=stored.get(kind, DEFAULT_ROUTES[kind.value]),
            recipients=len(
                await repository.active_with_role(stored.get(kind, DEFAULT_ROUTES[kind.value]))
            ),
        )
        for kind in AlertKind
    ]


@router.put(
    "/routes/{kind}",
    dependencies=[require_section(Section.SYSTEM_PARAMETERS, Level.WRITE)],
    summary="Say who receives one kind of alert",
)
async def set_route(
    kind: AlertKind, payload: RouteWrite, current_user: CurrentUser, session: Session
) -> RouteRead:
    """The owner (RF-37 of 007)."""
    repository = NotificationsRepository(session)
    await repository.put_route(kind, payload.role, actor_user_id=current_user.id)
    await session.commit()
    return RouteRead(
        kind=kind,
        role=payload.role,
        updated_by_user_id=current_user.id,
        recipients=len(await repository.active_with_role(payload.role)),
    )
