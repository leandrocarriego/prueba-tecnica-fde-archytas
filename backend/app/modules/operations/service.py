"""Operations business logic.

This is the module's only public surface: other modules import
`OperationsService` and nothing else from `operations`. Celery tasks use it to
record what they did, and the rest of the platform reads its parameters through
`get_parameter_value` instead of hardcoding thresholds.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.logging import get_logger
from app.modules.operations.models import AuditEntry, JobRun, JobStatus, Parameter
from app.modules.operations.repository import (
    AuditEntryRepository,
    DatabaseProbe,
    JobRunRepository,
    ParameterRepository,
    WhatsAppProbe,
)
from app.modules.operations.schemas import (
    AuditEntryList,
    AuditEntryRead,
    ComponentHealth,
    CorrectionReasonRead,
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
from app.quality import Quality, get_quality
from app.shared.corrections import REASON_LABELS, label_for
from app.shared.errors import ConflictError, NotFoundError
from app.shared.events import (
    AuditAction,
    BusinessParameterChanged,
    ManualChangeRecorded,
    PriceUpdateRecovered,
    PriceUpdateStalled,
    events,
)
from app.shared.parameters import PARAMETERS, ParameterSpec, spec_for
from app.shared.sections import BusinessSection
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

# What the platform does on its first day is no longer written here: the
# starting value, the range and the sentence the owner reads all come from
# `app.shared.parameters`, which is the one place a parameter is declared. A
# constant beside the key would be a second answer to "what is it worth before
# anybody touched it".

# The log calls a parameter change by this name. A string in this module's own
# vocabulary, like every `entity_type`.
PARAMETER_ENTITY = "operations.parameter"

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


@dataclass(frozen=True, slots=True)
class SyncJob:
    """One extraction that runs on a schedule of its own.

    Everything that separates the six scheduled extractions of the platform is
    here — the name their runs are recorded under, the Celery task that does
    the work, the parameter that says how often, and its advisory lock — so the
    heartbeat below is one loop and not six copies of the same fifteen lines.

    `celery_task` is a **string** on purpose: the work belongs to `portal`, and
    one module never imports another (Artículo IV). A name over the broker is
    the same kind of contract an event is.
    """

    key: str
    task_name: str
    celery_task: str
    interval_key: str
    lock_key: int
    # The parameter of `message_sync` is in minutes and every other one is in
    # hours. Carrying the unit next to the key is what keeps the heartbeat from
    # having to know which is which.
    unit: str = "hours"

    def interval(self, value: int) -> timedelta:
        """How long to wait between runs, in the unit this parameter is written in."""
        return timedelta(**{self.unit: value})


# The scheduled extractions of the platform. Adding one is a line here plus the
# task that does the work — never a change to `celery_app.py`, and never a
# second schedule to keep in step with the parameters panel.
SYNC_JOBS: tuple[SyncJob, ...] = (
    SyncJob(
        key="invoices",
        task_name="extract_invoices",
        celery_task="portal.extract_invoices",
        interval_key="invoice_sync.interval_hours",
        lock_key=0x9C1D_0002,
    ),
    SyncJob(
        key="supplier_ledger",
        task_name="extract_supplier_ledger",
        celery_task="portal.extract_supplier_ledger",
        interval_key="invoice_sync.interval_hours",
        lock_key=0x9C1D_0003,
    ),
    SyncJob(
        key="purchase_orders",
        task_name="extract_purchase_orders",
        celery_task="portal.extract_purchase_orders",
        interval_key="invoice_sync.interval_hours",
        lock_key=0x9C1D_0004,
    ),
    SyncJob(
        key="messages",
        task_name="extract_messages",
        celery_task="portal.extract_messages",
        interval_key="message_sync.interval_minutes",
        lock_key=0x9C1D_0005,
        unit="minutes",
    ),
    SyncJob(
        key="sales",
        task_name="extract_sales",
        celery_task="portal.extract_sales",
        interval_key="sales_sync.interval_hours",
        lock_key=0x9C1D_0006,
    ),
)

SYNC_BY_KEY: dict[str, SyncJob] = {job.key: job for job in SYNC_JOBS}


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
        self.audit = AuditEntryRepository(session)
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
    #
    # The screen is drawn from the declaration in `app.shared.parameters`, with
    # whatever the owner changed laid on top. The table holds only the changes:
    # a parameter nobody touched has no row and still has a value (RF-04).

    async def list_parameters(self) -> list[ParameterRead]:
        """Every parameter of the system, with the value in force (RF-01)."""
        stored = {parameter.key: parameter for parameter in await self.parameters.list_all()}
        return [self._parameter_read(spec, stored.get(spec.key)) for spec in PARAMETERS]

    async def get_parameter(self, key: str) -> ParameterRead:
        """One parameter, declaration and value together."""
        spec = spec_for(key)
        return self._parameter_read(spec, await self.parameters.get_by_key(key))

    async def get_parameter_value(self, key: str) -> Any:
        """The value in force, falling back to the starting one (RF-04).

        This is what the rest of the module calls. A parameter nobody changed is
        not a configuration gap any more: the catalog says what it is worth, so
        there is nothing to warn about and nothing to guess.
        """
        parameter = await self.parameters.get_by_key(key)
        if parameter is None:
            return spec_for(key).stored_initial
        return parameter.value

    async def set_parameters(
        self, items: list[ParameterWrite], *, actor_user_id: int
    ) -> list[ParameterRead]:
        """Store what the owner decided, and say so — or refuse and say why.

        Validation happens for the whole set before anything is written, so a
        rejected value cannot leave the platform running on a mix of the old
        rules and the new ones. A key outside the catalog and a value outside
        its range are both refused, and the refusal carries the range (RF-06).

        Each change is logged here rather than published as
        `ManualChangeRecorded`: the log is this module's own table, and
        publishing an event to hear it back would be ceremony. The event exists
        for the changes that come from outside.
        """
        validated = [(spec_for(item.key), item) for item in items]
        checked = [(spec, spec.coerce(item.value)) for spec, item in validated]

        updated: list[ParameterRead] = []
        for spec, value in checked:
            previous = await self.parameters.get_by_key(spec.key)
            old_value = spec.stored_initial if previous is None else previous.value
            # The label travels into `description` so a `psql` session reading
            # the table sees the same sentence the owner does. The catalog is
            # still the source: nothing reads this column back.
            parameter = await self.parameters.upsert(spec.key, value, spec.label)
            await self.record_manual_change(
                ManualChangeRecorded(
                    entity_type=PARAMETER_ENTITY,
                    entity_id=spec.key,
                    action=AuditAction.UPDATED,
                    actor_user_id=actor_user_id,
                    section=BusinessSection.SYSTEM,
                    old_value=old_value,
                    new_value=value,
                )
            )
            # Whoever needs a parameter keeps its own copy: nobody reads this
            # table from outside the module (Artículo IV).
            await events.publish(BusinessParameterChanged(key=spec.key, value=value), self.session)
            updated.append(self._parameter_read(spec, parameter))

        await self.session.commit()
        logger.info(
            "Parameters updated",
            extra={"keys": [spec.key for spec, _ in checked], "actor_user_id": actor_user_id},
        )
        return updated

    @staticmethod
    def _parameter_read(spec: ParameterSpec, stored: Parameter | None) -> ParameterRead:
        """Put the value in force on top of what the catalog declares."""
        return ParameterRead(
            key=spec.key,
            label=spec.label,
            effect=spec.effect,
            kind=spec.kind,
            value=spec.stored_initial if stored is None else stored.value,
            initial=spec.stored_initial,
            minimum=None if spec.minimum is None else str(spec.minimum),
            maximum=None if spec.maximum is None else str(spec.maximum),
            unit=spec.unit,
            consumed_by=spec.consumed_by,
            has_effect=spec.has_effect,
            changed_at=None if stored is None else stored.updated_at,
        )

    # --- The log of manual changes ---------------------------------------
    #
    # One door in, and it is this one: `record_manual_change`. The handler of
    # `ManualChangeRecorded` calls it for what happens in other modules, and
    # `set_parameters` calls it for what happens here.

    async def record_manual_change(self, event: ManualChangeRecorded) -> None:
        """Append one line to the log. It cannot be edited afterwards.

        No exception is caught around this on purpose. It runs in the
        transaction of whoever made the change, so if the line cannot be
        written the change does not happen either (`GEN-09`): a change without
        its record is exactly the silent loss Artículo II forbids.
        """
        await self.audit.insert(
            AuditEntry(
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                field=event.field,
                action=event.action,
                old_value=event.old_value,
                new_value=event.new_value,
                reason_code=event.reason_code,
                reason_detail=event.reason_detail,
                actor_user_id=event.actor_user_id,
                section=event.section,
                occurred_at=event.occurred_at,
            )
        )
        logger.info(
            "Manual change recorded",
            extra={
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "action": event.action.value,
                "actor_user_id": event.actor_user_id,
            },
        )

    async def list_audit(
        self,
        *,
        sections: Sequence[BusinessSection] | None,
        skip: int = 0,
        limit: int = 50,
        actor_user_id: int | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> AuditEntryList:
        """The history of manual changes, newest first (RF-13, RF-14, RF-18, RF-19).

        `sections` is the caller's own reach, resolved by `identity`, and it is
        applied to the query rather than checked afterwards: the owner passes
        `None` and sees everything, everybody else sees their sections only.
        """
        entries = await self.audit.list(
            skip=skip,
            limit=limit,
            sections=sections,
            actor_user_id=actor_user_id,
            since=since,
            until=until,
        )
        total = await self.audit.count(
            sections=sections, actor_user_id=actor_user_id, since=since, until=until
        )
        return AuditEntryList(
            items=[self._audit_read(entry) for entry in entries],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def audit_for_entity(
        self, entity_type: str, entity_id: str, *, sections: Sequence[BusinessSection] | None
    ) -> list[AuditEntryRead]:
        """The history of one datum, reachable from the datum itself (RF-15)."""
        entries = await self.audit.list_for_entity(entity_type, entity_id, sections=sections)
        return [self._audit_read(entry) for entry in entries]

    @staticmethod
    def correction_reasons() -> list[CorrectionReasonRead]:
        """The list a person picks a reason from (RF-11).

        Served from here because here is where a `reason_code` is validated. A
        list kept in the browser would be a second list, and the day they
        disagree the browser offers something the API refuses.
        """
        return [
            CorrectionReasonRead(code=reason.value, label=label)
            for reason, label in REASON_LABELS.items()
        ]

    @staticmethod
    def _audit_read(entry: AuditEntry) -> AuditEntryRead:
        """One line of the history, with its reason spelled out."""
        return AuditEntryRead(
            id=entry.id,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            field=entry.field,
            action=entry.action,
            old_value=entry.old_value,
            new_value=entry.new_value,
            reason_code=entry.reason_code,
            reason_label=label_for(entry.reason_code),
            reason_detail=entry.reason_detail,
            actor_user_id=entry.actor_user_id,
            section=entry.section,
            occurred_at=entry.occurred_at,
        )

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

    async def request_sync(
        self, job: SyncJob, *, requested_by_user_id: int | None = None
    ) -> int | None:
        """Open a run for one scheduled extraction and hand it to the worker.

        Returns the run id, or `None` when one of these is already running: the
        same rule as the price update, for the same reason — the portal account
        is shared with the client's own staff, and two browsers signed in as the
        same person is not a thing to do to somebody else's system.
        """
        if not await self.runs.try_lock(job.lock_key):
            return None
        if await self.runs.running(job.task_name) is not None:
            return None

        run = await self.runs.add(
            JobRun(
                task_name=job.task_name,
                status=JobStatus.RUNNING,
                started_at=datetime.now(UTC),
                payload={"requested_by_user_id": requested_by_user_id},
                attempts=1,
            )
        )
        await self.session.commit()
        celery_app.send_task(job.celery_task, kwargs={"job_run_id": run.id})
        logger.info("Extraction requested", extra={"job": job.key, "job_run_id": run.id})
        return run.id

    async def due_for_sync(self, job: SyncJob) -> bool:
        """Whether this extraction is due, by the parameter that governs it.

        Read every time rather than cached, which is what makes a change to the
        frequency apply from the following query instead of from a redeploy.
        """
        if await self.runs.running(job.task_name) is not None:
            return False
        runs = await self.runs.latest(job.task_name, limit=1)
        if not runs or runs[0].started_at is None:
            return True
        every = job.interval(int(await self.get_parameter_value(job.interval_key)))
        return datetime.now(UTC) - runs[0].started_at >= every

    async def record_sync_success(self, job_run_id: int) -> None:
        """Close a scheduled extraction as successful."""
        await self.complete_run(job_run_id, result={})

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
        self, payload: PriceUpdateSettingsWrite, *, actor_user_id: int
    ) -> PriceUpdateSettingsRead:
        """Store what the owner decided, and tell whoever reads it (RF-18, RF-19).

        The same two keys of the catalog, through the same door as the general
        panel: the validation, the log line and the event are written once.
        """
        await self.set_parameters(
            [
                ParameterWrite(key=INTERVAL_HOURS_KEY, value=payload.interval_hours),
                ParameterWrite(
                    key=HIGHLIGHT_THRESHOLD_KEY, value=str(payload.highlight_threshold_pct)
                ),
            ],
            actor_user_id=actor_user_id,
        )
        return await self.price_update_settings()

    async def interval_hours(self) -> int:
        """How often the portal is queried."""
        spec = spec_for(INTERVAL_HOURS_KEY)
        return self._as_int(await self.get_parameter_value(INTERVAL_HOURS_KEY), spec.initial)

    async def highlight_threshold(self) -> Decimal:
        """Above which rise a product is highlighted."""
        spec = spec_for(HIGHLIGHT_THRESHOLD_KEY)
        return self._as_decimal(
            await self.get_parameter_value(HIGHLIGHT_THRESHOLD_KEY), Decimal(str(spec.initial))
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

    @staticmethod
    def quality() -> Quality | None:
        """What the suite measured for the code this image was built from.

        Not part of `/health`, which is public: how well a system is tested is
        a fact about the people who build it, and it is theirs to share rather
        than anyone's to read off the internet. It needs a session.
        """
        return get_quality()

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
