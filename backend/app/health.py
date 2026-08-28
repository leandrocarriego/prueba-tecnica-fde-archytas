"""Liveness of the service and of the database it needs.

Infrastructure, not a domain capability. It answers "is this process up, and can
it reach its database" — a question about the deployment, not about the
business — so it lives next to `database.py` and `main.py` rather than inside a
module. That is also why it needs no model, no table and no migration: its whole
database question is `select 1`.

Public and unauthenticated on purpose. The container's healthcheck calls it
before anyone logs in, and the public status page calls it precisely when nobody
can log in at all.
"""

import enum
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi import status as http_status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.logging import get_logger

logger = get_logger(__name__)

# `/health` is public: the caller learns that the database is not answering,
# never why. The exception itself goes to the log.
DATABASE_UNAVAILABLE = "The database is not answering"


class HealthState(enum.StrEnum):
    """How a component is answering right now."""

    OK = "ok"
    DOWN = "down"


class ComponentHealth(BaseModel):
    """The state of one dependency.

    `detail` is deliberately generic: this endpoint is public, so it must not
    leak hostnames, drivers or credentials out of the underlying exception. The
    real exception goes to the log.
    """

    status: HealthState
    detail: str | None = None


class HealthRead(BaseModel):
    """The answer of `/health`: the service plus every dependency it needs."""

    status: HealthState
    service: str
    environment: str
    database: ComponentHealth


async def check_health(session: AsyncSession) -> HealthRead:
    """Report whether the service and its database are answering.

    This never raises. A health check that fails with a 500 tells the
    orchestrator nothing about *what* is broken, which is the only thing it was
    asked.
    """
    database = ComponentHealth(status=HealthState.OK)
    try:
        await session.execute(text("select 1"))
    except (SQLAlchemyError, OSError):
        # Logged in full here, reported generically to the caller.
        logger.exception("Database health check failed")
        database = ComponentHealth(status=HealthState.DOWN, detail=DATABASE_UNAVAILABLE)

    return HealthRead(
        status=database.status,
        service=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
        database=database,
    )


router = APIRouter(tags=["Health"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/health",
    summary="Service and database health",
    responses={http_status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "A dependency is down"}},
)
async def health(response: Response, session: Session) -> HealthRead:
    """Answer 503 rather than 200 when a dependency is down.

    An orchestrator restarts on the status code, not on the body — while a
    person reading the status page needs the body to know *which* dependency
    failed. Both get what they need out of the same reply.
    """
    report = await check_health(session)
    if report.status is not HealthState.OK:
        response.status_code = http_status.HTTP_503_SERVICE_UNAVAILABLE
    return report
