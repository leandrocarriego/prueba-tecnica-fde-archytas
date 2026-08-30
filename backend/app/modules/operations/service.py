"""Operations business logic.

This is the module's only public surface: other modules import
`OperationsService` and nothing else from `operations`. Celery tasks use it to
record what they did, and the rest of the platform reads its parameters through
`get_parameter_value` instead of hardcoding thresholds.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.logging import get_logger
from app.modules.operations.models import JobRun, JobStatus
from app.modules.operations.repository import (
    DatabaseProbe,
    JobRunRepository,
    ParameterRepository,
    WhatsAppProbe,
)
from app.modules.operations.schemas import (
    ComponentHealth,
    HealthRead,
    HealthState,
    JobRunRead,
    ParameterRead,
    ParameterWrite,
    PriceUpdateRequested,
    PriceUpdateSettingsRead,
    PriceUpdateSettingsWrite,
    PriceUpdateStatusRead,
)
from app.shared.errors import ConflictError, NotFoundError
from app.shared.events import (
    BusinessParameterChanged,
    PriceUpdateRecovered,
    PriceUpdateStalled,
    events,
)
from app.worker.celery_app import celery_app

logger = get_logger(__name__)

# `/health` is public: the caller learns that the database is not answering,
# never why. The exception itself goes to the log.
DATABASE_UNAVAILABLE = "The database is not answering"
# Deliberately generic, like the database's: `/health` is public, so a detail
# must not name the gateway, its instance or its address. The real exception
# goes to the log.
WHATSAPP_UNREACHABLE = "The WhatsApp gateway is not answering"
WHATSAPP_DISCONNECTED = "The WhatsApp session is not connected"
WHATSAPP_NOT_CONFIGURED = "The WhatsApp channel is not configured"

# --- The price update ----------------------------------------------------

PRICE_UPDATE_TASK = "extract_price_list"
EXTRACTION_TASK_NAME = "portal.extract_price_list"

INTERVAL_HOURS_KEY = "price_update.interval_hours"
HIGHLIGHT_THRESHOLD_KEY = "price_update.highlight_threshold_pct"

# What the platform does on its first day, before the owner touches anything
# (RF-20). Twelve hours because the supplier publishes twice a day: asking more
# often brings no new price and knocks on a third party's door for nothing.
DEFAULT_INTERVAL_HOURS = 12
DEFAULT_HIGHLIGHT_THRESHOLD = Decimal("10")

# One key for the whole platform: the advisory lock that serialises the decision
# to start an update. Arbitrary, stable, and documented so nobody reuses it.
PRICE_UPDATE_LOCK_KEY = 0x9C1D_0001

# An update is interrupted once two scheduled runs in a row have gone by without
# a successful one (RF-11, RF-12). The warning goes out at exactly that
# transition, which is what makes it happen once per interruption (RF-13).
STALL_THRESHOLD = 2

ALREADY_RUNNING = "A price update is already running"

# A run that is still RUNNING long past the point where its task could still be
# alive did not get slow: its worker is gone — a redeploy, an OOM, a reboot.
# Nobody will ever close it, and while it is open `due_for_update` says no and
# `request_price_update` raises: the feature stops for good, quietly, which is
# the one thing it is not allowed to do (Artículo II).
#
# The bound is Celery's own hard time limit, because that is what actually
# bounds a live task, plus a margin so a task killed *at* the limit still gets
# to record its own failure instead of being reaped first.
ABANDONED_AFTER = timedelta(seconds=celery_app.conf.task_time_limit or 1800) + timedelta(minutes=15)
ABANDONED = "The run was interrupted: its worker never came back"


def dispatch_price_extraction(job_run_id: int) -> None:
    """Hand the extraction to the worker that owns it.

    By task **name**, not by import: the extraction belongs to `portal`, and one
    module never imports another (Artículo IV). A string over the broker is the
    same kind of contract an event is.
    """
    celery_app.send_task(EXTRACTION_TASK_NAME, kwargs={"job_run_id": job_run_id})


class OperationsService:
    """Records background runs, serves business parameters and reports health."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.runs = JobRunRepository(session)
        self.parameters = ParameterRepository(session)
        self.database = DatabaseProbe(session)
        self.whatsapp = WhatsAppProbe()

    # --- Job runs --------------------------------------------------------

    async def start_run(
        self,
        task_name: str,
        *,
        payload: dict[str, Any] | None = None,
        run_id: int | None = None,
    ) -> JobRunRead:
        """Record that a task started, and return the run to report back on.

        Passing an existing `run_id` records a retry of that run instead of
        opening a second one: tasks are idempotent, so a retried extraction is
        the same run attempted again, and `attempts` is what says how often.
        """
        started_at = datetime.now(UTC)
        if run_id is None:
            run = await self.runs.add(
                JobRun(
                    task_name=task_name,
                    status=JobStatus.RUNNING,
                    started_at=started_at,
                    payload=payload,
                    attempts=1,
                )
            )
        else:
            run = await self._require_run(run_id)
            run = await self.runs.update(
                run,
                {
                    "status": JobStatus.RUNNING,
                    "started_at": started_at,
                    "finished_at": None,
                    "error": None,
                    "attempts": run.attempts + 1,
                },
            )
        await self.session.commit()
        logger.info(
            "Job run started",
            extra={"run_id": run.id, "task_name": run.task_name, "attempts": run.attempts},
        )
        return JobRunRead.model_validate(run)

    async def complete_run(
        self, run_id: int, *, result: dict[str, Any] | None = None
    ) -> JobRunRead:
        """Record that a run finished successfully."""
        run = await self._require_run(run_id)
        run = await self.runs.update(
            run,
            {
                "status": JobStatus.SUCCEEDED,
                "finished_at": datetime.now(UTC),
                "result": result,
                "error": None,
            },
        )
        await self.session.commit()
        logger.info("Job run succeeded", extra={"run_id": run.id, "task_name": run.task_name})
        return JobRunRead.model_validate(run)

    async def fail_run(self, run_id: int, error: str) -> JobRunRead:
        """Record that a run failed, keeping the reason with the row.

        The message is stored rather than only logged: whoever looks at the job
        history tomorrow will not have the worker's stdout in front of them.
        """
        run = await self._require_run(run_id)
        run = await self.runs.update(
            run,
            {
                "status": JobStatus.FAILED,
                "finished_at": datetime.now(UTC),
                "error": error,
            },
        )
        await self.session.commit()
        logger.error(
            "Job run failed",
            extra={"run_id": run.id, "task_name": run.task_name, "error": error},
        )
        return JobRunRead.model_validate(run)

    async def list_runs(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        task_name: str | None = None,
        status: JobStatus | None = None,
    ) -> tuple[list[JobRunRead], int]:
        """Return a page of runs, newest first, and how many match the filters."""
        runs = await self.runs.list_recent(
            skip=skip, limit=limit, task_name=task_name, status=status
        )
        total = await self.runs.count_matching(task_name=task_name, status=status)
        return [JobRunRead.model_validate(run) for run in runs], total

    async def get_run(self, run_id: int) -> JobRunRead:
        """Return a single run by id."""
        return JobRunRead.model_validate(await self._require_run(run_id))

    async def _require_run(self, run_id: int) -> JobRun:
        """Return the run or raise, so every writer fails the same way."""
        run = await self.runs.get(run_id)
        if run is None:
            raise NotFoundError("Job run not found", details={"run_id": run_id})
        return run

    # --- Parameters ------------------------------------------------------

    async def list_parameters(self) -> list[ParameterRead]:
        """Return every business parameter, ordered by key."""
        return [ParameterRead.model_validate(item) for item in await self.parameters.list_all()]

    async def get_parameter(self, key: str) -> ParameterRead:
        """Return one parameter by key."""
        parameter = await self.parameters.get_by_key(key)
        if parameter is None:
            raise NotFoundError("Parameter not found", details={"key": key})
        return ParameterRead.model_validate(parameter)

    async def get_parameter_value(self, key: str, default: Any = None) -> Any:
        """Return the value of a parameter, or `default` if it is not set.

        This is what other modules call: a missing parameter is a configuration
        gap, not an error worth interrupting a purchase or an extraction over.
        """
        parameter = await self.parameters.get_by_key(key)
        if parameter is None:
            logger.warning("Parameter not configured, falling back", extra={"key": key})
            return default
        return parameter.value

    async def set_parameters(self, items: list[ParameterWrite]) -> list[ParameterRead]:
        """Create or overwrite a set of parameters in a single transaction.

        All of them land or none of them do: half-applied settings would leave
        the business running on a mix of old and new rules.
        """
        updated = [
            await self.parameters.upsert(item.key, item.value, item.description) for item in items
        ]
        for item in items:
            # Whoever needs a parameter keeps its own copy: nobody reads this
            # table from outside the module (Artículo IV).
            await events.publish(
                BusinessParameterChanged(key=item.key, value=item.value), self.session
            )
        await self.session.commit()
        logger.info("Parameters updated", extra={"keys": [item.key for item in items]})
        return [ParameterRead.model_validate(parameter) for parameter in updated]

    # --- The price update -------------------------------------------------

    async def request_price_update(
        self,
        *,
        requested_by_user_id: int | None = None,
        dispatch: Callable[[int], None] | None = None,
    ) -> PriceUpdateRequested:
        """Ask the portal for the list now, unless one is already being asked for.

        The advisory lock is what makes RF-15 true. Checking for a running run
        and inserting a new one are two statements, and between them two callers
        can both find nothing; under the lock only one gets to look.
        """
        if not await self.runs.try_lock(PRICE_UPDATE_LOCK_KEY):
            running = await self.runs.running(PRICE_UPDATE_TASK)
            raise ConflictError(
                ALREADY_RUNNING, details={"job_run_id": None if running is None else running.id}
            )

        running = await self.runs.running(PRICE_UPDATE_TASK)
        if running is not None:
            raise ConflictError(ALREADY_RUNNING, details={"job_run_id": running.id})

        run = await self.runs.add(
            JobRun(
                task_name=PRICE_UPDATE_TASK,
                status=JobStatus.RUNNING,
                started_at=datetime.now(UTC),
                # Who asked and when: the run itself is the record (RF-17).
                payload={"requested_by_user_id": requested_by_user_id},
                attempts=1,
            )
        )
        await self.session.commit()

        (dispatch or dispatch_price_extraction)(run.id)
        logger.info(
            "Price update requested",
            extra={"job_run_id": run.id, "requested_by_user_id": requested_by_user_id},
        )
        return PriceUpdateRequested(job_run_id=run.id, status=run.status)

    async def price_update_status(self) -> PriceUpdateStatusRead:
        """When the last successful update was, and whether it is interrupted."""
        runs = await self.runs.latest(PRICE_UPDATE_TASK)
        last_success = await self.runs.last_successful(PRICE_UPDATE_TASK)
        failures = self._consecutive_failures(runs)
        latest = runs[0] if runs else None
        return PriceUpdateStatusRead(
            last_success_at=None if last_success is None else last_success.finished_at,
            last_run_id=None if latest is None else latest.id,
            last_run_status=None if latest is None else latest.status,
            last_result=None if last_success is None else last_success.result,
            last_quarantined=self._quarantined_of(last_success),
            consecutive_failures=failures,
            is_stalled=failures >= STALL_THRESHOLD,
            interval_hours=await self.interval_hours(),
            highlight_threshold_pct=await self.highlight_threshold(),
        )

    async def record_price_update_success(self, job_run_id: int) -> None:
        """Close a run that finished well, and say so if it was interrupted."""
        run = await self.runs.get(job_run_id)
        if run is None:
            logger.warning("Success reported for an unknown run", extra={"run_id": job_run_id})
            return
        was_stalled = self._consecutive_failures(await self.runs.latest(PRICE_UPDATE_TASK))
        await self.runs.update(
            run,
            {"status": JobStatus.SUCCEEDED, "finished_at": datetime.now(UTC), "error": None},
        )
        if was_stalled >= STALL_THRESHOLD:
            await events.publish(PriceUpdateRecovered(recovered_at=datetime.now(UTC)), self.session)
        logger.info("Price update finished", extra={"run_id": run.id})

    async def record_price_update_failure(self, job_run_id: int, message: str) -> None:
        """Record a failed run with its reason (RF-10), and warn once (RF-12, RF-13)."""
        run = await self.runs.get(job_run_id)
        if run is None:
            logger.warning("Failure reported for an unknown run", extra={"run_id": job_run_id})
            return
        await self.runs.update(
            run,
            {"status": JobStatus.FAILED, "finished_at": datetime.now(UTC), "error": message},
        )
        failures = self._consecutive_failures(await self.runs.latest(PRICE_UPDATE_TASK))
        if failures == STALL_THRESHOLD:
            # Exactly at the transition, so the same interruption warns once
            # however many runs it goes on to fail (RF-13).
            last_success = await self.runs.last_successful(PRICE_UPDATE_TASK)
            await events.publish(
                PriceUpdateStalled(
                    consecutive_failures=failures,
                    last_success_at=None if last_success is None else last_success.finished_at,
                    reason=message,
                ),
                self.session,
            )
        logger.error(
            "Price update failed",
            extra={"run_id": run.id, "consecutive_failures": failures},
        )

    async def record_price_update_result(self, job_run_id: int, result: dict[str, Any]) -> None:
        """Keep the tally of a run: what changed, what was set aside (RF-27)."""
        run = await self.runs.get(job_run_id)
        if run is None:
            return
        await self.runs.update(run, {"result": result})

    async def close_abandoned_price_update(self) -> int | None:
        """Fail a run whose worker never came back, and say so like any failure.

        Called by the heartbeat before it decides anything, because this is the
        only thing that can be waiting on the other side of that decision. It
        goes through the same path a real failure takes, so the run keeps its
        reason (RF-10), the screen stops claiming an update is in progress
        (RF-11) and the owner is warned on the same terms (RF-12, RF-13): from
        outside, a worker that died mid-run and a portal that would not answer
        are the same event — the update did not happen.
        """
        running = await self.runs.running(PRICE_UPDATE_TASK)
        if running is None or running.started_at is None:
            return None
        if datetime.now(UTC) - running.started_at < ABANDONED_AFTER:
            return None

        run_id = running.id
        logger.warning(
            "Abandoned price update closed",
            extra={"run_id": run_id, "started_at": running.started_at.isoformat()},
        )
        await self.record_price_update_failure(run_id, ABANDONED)
        await self.session.commit()
        return run_id

    async def due_for_update(self) -> bool:
        """Whether the next scheduled query is due.

        Read from the parameter every time, which is what makes a change apply
        from the following query and not from a redeploy (RF-21).
        """
        if await self.runs.running(PRICE_UPDATE_TASK) is not None:
            return False
        runs = await self.runs.latest(PRICE_UPDATE_TASK, limit=1)
        if not runs or runs[0].started_at is None:
            return True
        interval = timedelta(hours=await self.interval_hours())
        return datetime.now(UTC) - runs[0].started_at >= interval

    # --- The two parameters of the feature --------------------------------

    async def price_update_settings(self) -> PriceUpdateSettingsRead:
        """The values in force, falling back to the starting ones (RF-20)."""
        return PriceUpdateSettingsRead(
            interval_hours=await self.interval_hours(),
            highlight_threshold_pct=await self.highlight_threshold(),
        )

    async def set_price_update_settings(
        self, payload: PriceUpdateSettingsWrite
    ) -> PriceUpdateSettingsRead:
        """Store what the owner decided, and tell whoever reads it (RF-18, RF-19)."""
        await self.set_parameters(
            [
                ParameterWrite(
                    key=INTERVAL_HOURS_KEY,
                    value=payload.interval_hours,
                    description="Cada cuántas horas se consulta el portal",
                ),
                ParameterWrite(
                    key=HIGHLIGHT_THRESHOLD_KEY,
                    value=str(payload.highlight_threshold_pct),
                    description="Porcentaje de suba a partir del cual un producto se destaca",
                ),
            ]
        )
        return await self.price_update_settings()

    async def interval_hours(self) -> int:
        """How often the portal is queried."""
        return self._as_int(
            await self.get_parameter_value(INTERVAL_HOURS_KEY), DEFAULT_INTERVAL_HOURS
        )

    async def highlight_threshold(self) -> Decimal:
        """Above which rise a product is highlighted."""
        return self._as_decimal(
            await self.get_parameter_value(HIGHLIGHT_THRESHOLD_KEY), DEFAULT_HIGHLIGHT_THRESHOLD
        )

    @staticmethod
    def _quarantined_of(run: JobRun | None) -> int | None:
        """How many rows the last successful update set aside (RF-27).

        `None` means there is no update to report on yet, which is not the same
        as an update that set aside nothing.
        """
        if run is None or not isinstance(run.result, dict):
            return None
        value = run.result.get("quarantined")
        return value if isinstance(value, int) else None

    @staticmethod
    def _consecutive_failures(runs: list[JobRun]) -> int:
        """How many runs have failed in a row, newest first."""
        failures = 0
        for run in runs:
            if run.status is JobStatus.FAILED:
                failures += 1
                continue
            if run.status is JobStatus.SUCCEEDED:
                break
        return failures

    @staticmethod
    def _as_int(value: Any, fallback: int) -> int:
        """Read a parameter as a whole number, or fall back to the starting value."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _as_decimal(value: Any, fallback: Decimal) -> Decimal:
        """Read a parameter as a decimal, or fall back to the starting value."""
        try:
            return Decimal(str(value))
        except (TypeError, InvalidOperation, ArithmeticError):
            return fallback

    # --- Health ----------------------------------------------------------

    async def health(self) -> HealthRead:
        """Report whether the service and its database are answering.

        This never raises: a health check that fails with a 500 tells the
        orchestrator nothing about *what* is broken.
        """
        database = ComponentHealth(status=HealthState.OK)
        try:
            await self.database.ping()
        except (SQLAlchemyError, OSError):
            # Logged in full here, reported generically to the caller.
            logger.exception("Database health check failed")
            database = ComponentHealth(status=HealthState.DOWN, detail=DATABASE_UNAVAILABLE)

        return HealthRead(
            # Only the database decides this. See `HealthRead`: the route
            # answers 503 when it is not OK and Docker restarts on that, so a
            # WhatsApp outage counting here would restart the API every fifteen
            # seconds because somebody else's gateway is down.
            status=database.status,
            service=settings.PROJECT_NAME,
            environment=settings.ENVIRONMENT,
            database=database,
            whatsapp=await self._whatsapp_health(),
        )

    async def _whatsapp_health(self) -> ComponentHealth:
        """Report the channel the owner is reached through. Never raises.

        Worth reporting even though it changes nothing about serving requests:
        when the session drops, every invitation and every alert stops arriving
        and **nothing says so** — the one channel that could carry the warning
        is the channel that is down. So it is written where somebody can look.
        """
        if not self.whatsapp.is_configured:
            return ComponentHealth(status=HealthState.OFF, detail=WHATSAPP_NOT_CONFIGURED)
        try:
            connected = await self.whatsapp.is_connected()
        except (httpx.HTTPError, OSError):
            logger.exception("WhatsApp health check failed")
            return ComponentHealth(status=HealthState.DOWN, detail=WHATSAPP_UNREACHABLE)
        if not connected:
            # The gateway answered, and what it said is that the phone is no
            # longer paired. That is down, not off: nobody turned it off.
            return ComponentHealth(status=HealthState.DOWN, detail=WHATSAPP_DISCONNECTED)
        return ComponentHealth(status=HealthState.OK)
