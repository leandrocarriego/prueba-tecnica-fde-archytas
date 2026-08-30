"""The update as an operation: is it alive, ask for one now, and its two settings.

H2, H3 and H4 of the spec. `operations` is the module that watches the platform
run, so this is where "the update stopped working" becomes a row, a warning and
a line on the prices screen.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.service import CatalogService
from app.modules.identity.models import User
from app.modules.operations.models import JobRun, JobStatus
from app.modules.operations.schemas import PriceUpdateSettingsWrite
from app.modules.operations.service import PRICE_UPDATE_TASK, OperationsService
from app.shared.errors import ConflictError
from app.shared.parameters import initial_value
from tests.conftest import Queued

pytestmark = [pytest.mark.integration, pytest.mark.database]


class Dispatched:
    """Records the extraction that would have been handed to the worker."""

    def __init__(self) -> None:
        self.job_run_ids: list[int] = []

    def __call__(self, job_run_id: int) -> None:
        self.job_run_ids.append(job_run_id)


async def fail_a_run(service: OperationsService, message: str = "El portal no responde") -> int:
    """Open a run and report it failed, the way the extraction task does."""
    run = await service.runs.add(
        JobRun(task_name=PRICE_UPDATE_TASK, status=JobStatus.RUNNING, started_at=datetime.now(UTC))
    )
    await service.session.commit()
    await service.record_price_update_failure(run.id, message)
    return run.id


async def succeed_a_run(service: OperationsService) -> int:
    """Open a run and report it finished well."""
    run = await service.runs.add(
        JobRun(task_name=PRICE_UPDATE_TASK, status=JobStatus.RUNNING, started_at=datetime.now(UTC))
    )
    await service.session.commit()
    await service.record_price_update_success(run.id)
    return run.id


class TestAskingForAnUpdate:
    """H3: bring the list now, without waiting for the next scheduled query."""

    async def test_it_opens_a_run_and_hands_it_to_the_worker(
        self, session: AsyncSession, purchasing_user: User
    ) -> None:
        """RF-14: the request is a run somebody can follow, not a fire and forget."""
        # Arrange
        dispatch = Dispatched()

        # Act
        requested = await OperationsService(session).request_price_update(
            requested_by_user_id=purchasing_user.id, dispatch=dispatch
        )

        # Assert
        assert requested.status is JobStatus.RUNNING
        assert dispatch.job_run_ids == [requested.job_run_id]

    async def test_it_records_who_asked(self, session: AsyncSession, purchasing_user: User) -> None:
        """RF-17: knocking on a third party's door is not anonymous."""
        # Arrange
        service = OperationsService(session)

        # Act
        requested = await service.request_price_update(
            requested_by_user_id=purchasing_user.id, dispatch=Dispatched()
        )

        # Assert
        run = await service.get_run(requested.job_run_id)
        assert run.payload == {"requested_by_user_id": purchasing_user.id}
        assert run.started_at is not None

    async def test_a_second_request_is_refused_while_one_runs(
        self, session: AsyncSession, purchasing_user: User
    ) -> None:
        """RF-15: the system says there is one in flight instead of starting another."""
        # Arrange
        service = OperationsService(session)
        first = await service.request_price_update(
            requested_by_user_id=purchasing_user.id, dispatch=Dispatched()
        )

        # Act / Assert
        with pytest.raises(ConflictError) as refused:
            await service.request_price_update(
                requested_by_user_id=purchasing_user.id, dispatch=Dispatched()
            )
        assert refused.value.details["job_run_id"] == first.job_run_id

    async def test_the_result_of_that_run_can_be_read_even_if_it_failed(
        self, session: AsyncSession, purchasing_user: User
    ) -> None:
        """RF-16: `/status` only knows about successes, so a failure needs its own route."""
        # Arrange
        service = OperationsService(session)
        requested = await service.request_price_update(
            requested_by_user_id=purchasing_user.id, dispatch=Dispatched()
        )

        # Act
        await service.record_price_update_failure(requested.job_run_id, "El portal no responde")

        # Assert
        run = await service.get_run(requested.job_run_id)
        assert run.status is JobStatus.FAILED
        assert run.error == "El portal no responde"


class TestKnowingItIsAlive:
    """H2: the last successful update, and the alert when there is none."""

    async def test_a_fresh_installation_has_nothing_to_report(self, session: AsyncSession) -> None:
        """No runs yet is not an interruption."""
        # Act
        status = await OperationsService(session).price_update_status()

        # Assert
        assert status.last_success_at is None
        assert status.is_stalled is False

    async def test_it_reports_the_last_successful_update(self, session: AsyncSession) -> None:
        """RF-09: the date and time on top of the prices screen."""
        # Arrange
        service = OperationsService(session)
        run_id = await succeed_a_run(service)

        # Act
        status = await service.price_update_status()

        # Assert
        assert status.last_run_id == run_id
        assert status.last_success_at is not None

    async def test_it_reports_how_many_rows_the_update_set_aside(
        self, session: AsyncSession
    ) -> None:
        """RF-27: the tally of an update is on the screen, not only in the run.

        The number the prices screen shows comes typed out of the run, so a
        rename of the key inside `result` fails here instead of quietly showing
        nothing.
        """
        # Arrange
        service = OperationsService(session)
        run_id = await succeed_a_run(service)
        await service.record_price_update_result(
            run_id, {"updated": 94, "unchanged": 0, "highlighted": 2, "quarantined": 6}
        )

        # Act
        status = await service.price_update_status()

        # Assert
        assert status.last_quarantined == 6

    async def test_an_update_with_nothing_to_report_says_zero_and_not_nothing(
        self, session: AsyncSession
    ) -> None:
        """A clean update set aside zero rows; no update at all reports nothing."""
        # Arrange
        service = OperationsService(session)
        assert (await service.price_update_status()).last_quarantined is None

        # Act
        run_id = await succeed_a_run(service)
        await service.record_price_update_result(run_id, {"updated": 100, "quarantined": 0})

        # Assert
        assert (await service.price_update_status()).last_quarantined == 0

    async def test_a_failure_is_recorded_with_its_reason(self, session: AsyncSession) -> None:
        """RF-10: tomorrow morning, the reason has to be next to the run."""
        # Arrange
        service = OperationsService(session)

        # Act
        run_id = await fail_a_run(service, "El portal no responde")

        # Assert
        run = await service.get_run(run_id)
        assert run.status is JobStatus.FAILED
        assert run.error == "El portal no responde"

    async def test_two_failures_in_a_row_are_an_interruption(
        self, session: AsyncSession, queued_alerts: Queued
    ) -> None:
        """RF-11 and RF-12: the screen says so, and the owner is warned."""
        # Arrange
        service = OperationsService(session)

        # Act
        await fail_a_run(service)
        await fail_a_run(service)

        # Assert
        status = await service.price_update_status()
        assert status.consecutive_failures == 2
        assert status.is_stalled is True
        assert queued_alerts.count == 1

    async def test_the_same_interruption_warns_once(
        self, session: AsyncSession, queued_alerts: Queued
    ) -> None:
        """RF-13: days down is one message, not one per attempt."""
        # Arrange
        service = OperationsService(session)

        # Act
        for _ in range(5):
            await fail_a_run(service)

        # Assert
        assert queued_alerts.count == 1

    async def test_coming_back_is_reported_too(
        self, session: AsyncSession, queued_alerts: Queued
    ) -> None:
        """RF-44: the owner should not have to open the screen to find out it works again.

        Two messages in total and not three: the one that said it stopped, and
        the one that says it came back. From there on a successful update is
        just an ordinary day and says nothing.
        """
        # Arrange
        service = OperationsService(session)
        await fail_a_run(service)
        await fail_a_run(service)

        # Act
        await succeed_a_run(service)

        # Assert
        assert queued_alerts.count == 2
        status = await service.price_update_status()
        assert status.is_stalled is False

        # And the next one is silent.
        await succeed_a_run(service)
        assert queued_alerts.count == 2

    async def test_the_alert_does_not_depend_on_whatsapp_working(
        self, session: AsyncSession, queued_alerts: Queued
    ) -> None:
        """RF-11 is a property of the screen, not of the message."""
        # Arrange
        service = OperationsService(session)
        await fail_a_run(service)
        await fail_a_run(service)

        # Act
        status = await service.price_update_status()

        # Assert
        assert status.is_stalled is True


class TestTheTwoSettings:
    """H4: the owner decides how often, and what a big rise is."""

    async def test_the_starting_values_are_in_force_until_somebody_changes_them(
        self, session: AsyncSession
    ) -> None:
        """RF-20: twelve hours and 10%, out of the box.

        Read from the catalog of business parameters rather than from a
        constant here: since 003 that catalog is where a starting value is
        declared, and a copy in the test would keep passing after somebody
        changed the real one.
        """
        # Act
        settings = await OperationsService(session).price_update_settings()

        # Assert
        assert settings.interval_hours == initial_value("price_update.interval_hours")
        assert settings.highlight_threshold_pct == initial_value(
            "price_update.highlight_threshold_pct"
        )

    async def test_the_owner_can_change_them(self, session: AsyncSession) -> None:
        """RF-18 and RF-19, and the change is what is read afterwards."""
        # Arrange
        service = OperationsService(session)

        # Act
        saved = await service.set_price_update_settings(
            PriceUpdateSettingsWrite(interval_hours=6, highlight_threshold_pct=15), actor_user_id=1
        )

        # Assert
        assert saved.interval_hours == 6
        assert (await service.price_update_settings()).highlight_threshold_pct == 15

    async def test_the_threshold_reaches_the_module_that_applies_it(
        self, session: AsyncSession
    ) -> None:
        """`catalog` keeps its own copy: it cannot read another module's table."""
        # Arrange
        service = OperationsService(session)

        # Act
        await service.set_price_update_settings(
            PriceUpdateSettingsWrite(interval_hours=12, highlight_threshold_pct=25), actor_user_id=1
        )

        # Assert
        assert await CatalogService(session).highlight_threshold() == 25

    async def test_a_new_frequency_applies_from_the_next_query(self, session: AsyncSession) -> None:
        """RF-21: not from a redeploy, and not to the query already gone."""
        # Arrange
        service = OperationsService(session)
        run = await service.runs.add(
            JobRun(
                task_name=PRICE_UPDATE_TASK,
                status=JobStatus.SUCCEEDED,
                started_at=datetime.now(UTC) - timedelta(hours=7),
                finished_at=datetime.now(UTC) - timedelta(hours=7),
            )
        )
        await session.commit()
        assert run.id

        # Act / Assert: at twelve hours it is not due yet…
        assert await service.due_for_update() is False

        # …and the owner moving it to six makes the next query due now.
        await service.set_price_update_settings(
            PriceUpdateSettingsWrite(interval_hours=6, highlight_threshold_pct=10), actor_user_id=1
        )
        assert await service.due_for_update() is True

    async def test_a_scheduled_query_never_overlaps_a_running_one(
        self, session: AsyncSession
    ) -> None:
        """One update at a time, whoever asked for it (RF-15)."""
        # Arrange
        service = OperationsService(session)
        await service.request_price_update(dispatch=Dispatched())

        # Act / Assert
        assert await service.due_for_update() is False
