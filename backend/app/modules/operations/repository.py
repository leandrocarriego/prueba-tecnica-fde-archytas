"""Where the operations module reaches outside itself. Private to this module.

Mostly its own tables, and at the end the two probes: this is the module that
watches the platform operate, so it is the one that asks a dependency whether
it is answering. Both live here for the same reason `DatabaseProbe` gives —
nothing else in the module opens a connection of its own.
"""

from typing import Any

import httpx
from sqlalchemy import Select, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.operations.models import JobRun, JobStatus, Parameter
from app.shared.repository import BaseRepository


class JobRunRepository(BaseRepository[JobRun]):
    """Reads and writes the history of background runs."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(JobRun, session)

    @staticmethod
    def _filtered(
        statement: Select[Any], task_name: str | None, status: JobStatus | None
    ) -> Select[Any]:
        """Apply the optional filters shared by the listing and its count."""
        if task_name is not None:
            statement = statement.where(JobRun.task_name == task_name)
        if status is not None:
            statement = statement.where(JobRun.status == status)
        return statement

    async def list_recent(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        task_name: str | None = None,
        status: JobStatus | None = None,
    ) -> list[JobRun]:
        """Return a page of runs, newest first."""
        # Ordered by `id` rather than `started_at`: the identifier is monotonic
        # and always set, while `started_at` is null on a run that has not begun.
        statement = self._filtered(select(JobRun), task_name, status)
        result = await self.session.execute(
            statement.order_by(JobRun.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def last_successful(self, task_name: str) -> JobRun | None:
        """The most recent run of a task that finished well (RF-09)."""
        result = await self.session.execute(
            select(JobRun)
            .where(JobRun.task_name == task_name, JobRun.status == JobStatus.SUCCEEDED)
            .order_by(JobRun.id.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def running(self, task_name: str) -> JobRun | None:
        """The run of a task that is executing right now, if there is one."""
        result = await self.session.execute(
            select(JobRun)
            .where(JobRun.task_name == task_name, JobRun.status == JobStatus.RUNNING)
            .order_by(JobRun.id.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def latest(self, task_name: str, *, limit: int = 20) -> list[JobRun]:
        """The last runs of a task, newest first."""
        result = await self.session.execute(
            select(JobRun)
            .where(JobRun.task_name == task_name)
            .order_by(JobRun.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def try_lock(self, key: int) -> bool:
        """Take a transaction-scoped advisory lock, or say it is taken.

        It is what makes "one update at a time" true (RF-15) without the race a
        `SELECT ... WHERE status = RUNNING` followed by an `INSERT` would have.
        The lock is released when the transaction ends, whatever ends it.
        """
        result = await self.session.execute(select(func.pg_try_advisory_xact_lock(key)))
        return bool(result.scalar_one())

    async def count_matching(
        self, *, task_name: str | None = None, status: JobStatus | None = None
    ) -> int:
        """Return how many runs match the same filters as `list_recent`."""
        statement = self._filtered(select(func.count()).select_from(JobRun), task_name, status)
        result = await self.session.execute(statement)
        return int(result.scalar_one())


class ParameterRepository(BaseRepository[Parameter]):
    """Reads and writes the configurable business parameters."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Parameter, session)

    async def get_by_key(self, key: str) -> Parameter | None:
        """Return the parameter stored under this key, or None."""
        result = await self.session.execute(select(Parameter).where(Parameter.key == key))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Parameter]:
        """Return every parameter, ordered by key.

        There are a handful of these and the settings screen shows all of them,
        so they are not paginated.
        """
        result = await self.session.execute(select(Parameter).order_by(Parameter.key))
        return list(result.scalars().all())

    async def upsert(self, key: str, value: Any, description: str | None) -> Parameter:
        """Create the parameter or overwrite its value.

        A `None` description leaves the stored text untouched: callers that only
        change a value should not have to resend it.
        """
        parameter = await self.get_by_key(key)
        if parameter is None:
            parameter = Parameter(key=key, value=value, description=description)
            self.session.add(parameter)
        else:
            parameter.value = value
            if description is not None:
                parameter.description = description
        await self.session.flush()
        await self.session.refresh(parameter)
        return parameter


class DatabaseProbe:
    """Asks the database the cheapest question there is.

    It lives in the repository layer because it is data access, even though it
    reads no table: nothing else in the module opens a connection of its own.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ping(self) -> None:
        """Run a trivial query. Raises if the database is unreachable."""
        await self.session.execute(text("select 1"))


class WhatsAppProbe:
    """Asks the gateway whether its WhatsApp session is still open.

    It reads the settings and talks HTTP; it does **not** import
    `notifications`. A module never imports another module (Artículo IV), and
    it does not need to: this is the same shape as pinging the database, which
    `operations` also does without importing whoever owns it.

    The duplication is one URL, and the alternative was worse. A projection fed
    by events would only learn the channel is down when something tried to send
    — which is the moment the answer is least useful, and says nothing at all
    on a quiet day.
    """

    # Short on purpose: this runs inside `/health`, which Docker calls every
    # fifteen seconds with a five second timeout. A slow gateway must not make
    # the API look unhealthy.
    TIMEOUT_SECONDS = 2.0

    @property
    def is_configured(self) -> bool:
        """Whether there is a gateway to ask about at all."""
        return bool(
            settings.EVOLUTION_API_URL
            and settings.EVOLUTION_INSTANCE
            and settings.EVOLUTION_API_KEY
        )

    async def is_connected(self) -> bool:
        """Whether the session is paired and open. Raises if the gateway is not answering."""
        url = (
            f"{settings.EVOLUTION_API_URL.rstrip('/')}"
            f"/instance/connectionState/{settings.EVOLUTION_INSTANCE}"
        )
        async with httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers={"apikey": settings.EVOLUTION_API_KEY})
            response.raise_for_status()
            body = response.json()
        state = body.get("instance", {}).get("state") if isinstance(body, dict) else None
        return state == "open"
