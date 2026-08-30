"""Integration tests for `OperationsService`.

`operations` is the system operating on itself: the job history is what explains a
failed overnight extraction the next morning, and the parameters are the rules
the business changes without a deploy. Both are exercised against a real
session, since both are about what ends up stored.
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operations.models import JobStatus
from app.modules.operations.schemas import HealthState, ParameterWrite
from app.modules.operations.service import OperationsService
from app.shared.errors import NotFoundError, ValidationError
from app.shared.parameters import PARAMETERS
from app.shared.sections import BusinessSection

TASK = "portal.extract_invoices"

INTERVAL = "price_update.interval_hours"
THRESHOLD = "price_update.highlight_threshold_pct"
# Who is making the change. The log needs somebody, and these tests are about
# what gets stored, not about who may store it — that is `test_rbac.py`.
ACTOR = 1


@pytest.fixture
def service(session: AsyncSession) -> OperationsService:
    """The service under test, on the test's session."""
    return OperationsService(session)


@pytest.mark.integration
@pytest.mark.database
class TestJobRunLifecycle:
    """A run goes from started to finished, one way or the other."""

    async def test_start_run_records_the_run(self, service: OperationsService) -> None:
        """A started run is RUNNING, timestamped, and counts as one attempt."""
        # Act
        run = await service.start_run(TASK, payload={"section": "invoices"})

        # Assert
        assert run.id is not None
        assert run.task_name == TASK
        assert run.status is JobStatus.RUNNING
        assert run.started_at is not None
        assert run.finished_at is None
        assert run.payload == {"section": "invoices"}
        assert run.attempts == 1

    async def test_start_then_complete(self, service: OperationsService) -> None:
        """A successful run ends SUCCEEDED, with its result and no error."""
        # Arrange
        run = await service.start_run(TASK)

        # Act
        finished = await service.complete_run(run.id, result={"rows": 128})

        # Assert
        assert finished.id == run.id
        assert finished.status is JobStatus.SUCCEEDED
        assert finished.finished_at is not None
        assert finished.result == {"rows": 128}
        assert finished.error is None

    async def test_start_then_fail(self, service: OperationsService) -> None:
        """A failed run keeps the reason next to the row, not only in the log."""
        # Arrange
        run = await service.start_run(TASK)

        # Act
        failed = await service.fail_run(run.id, "The portal changed its table layout")

        # Assert
        assert failed.status is JobStatus.FAILED
        assert failed.finished_at is not None
        assert failed.error == "The portal changed its table layout"

    async def test_a_retry_reuses_the_run_and_counts_the_attempt(
        self, service: OperationsService
    ) -> None:
        """Tasks are idempotent, so a retry is the same run attempted again.

        Opening a second row per retry would make the history unreadable: the
        question is how often *this* run was attempted.
        """
        # Arrange
        run = await service.start_run(TASK)
        await service.fail_run(run.id, "Timeout")

        # Act
        retried = await service.start_run(TASK, run_id=run.id)

        # Assert
        assert retried.id == run.id
        assert retried.attempts == 2
        assert retried.status is JobStatus.RUNNING
        # The previous failure must not survive into the new attempt.
        assert retried.error is None
        assert retried.finished_at is None

    async def test_a_retry_that_succeeds_leaves_one_run(self, service: OperationsService) -> None:
        """Two attempts, one row, and the final state is the one that counts."""
        # Arrange
        run = await service.start_run(TASK)
        await service.fail_run(run.id, "Timeout")
        await service.start_run(TASK, run_id=run.id)

        # Act
        finished = await service.complete_run(run.id, result={"rows": 3})
        _, total = await service.list_runs()

        # Assert
        assert total == 1
        assert finished.status is JobStatus.SUCCEEDED
        assert finished.attempts == 2

    @pytest.mark.parametrize("action", ["complete", "fail", "retry", "get"])
    async def test_operating_on_a_missing_run_is_a_domain_error(
        self, service: OperationsService, action: str
    ) -> None:
        """Every writer fails the same way on a run that does not exist."""
        # Act / Assert
        with pytest.raises(NotFoundError) as raised:
            if action == "complete":
                await service.complete_run(999999)
            elif action == "fail":
                await service.fail_run(999999, "boom")
            elif action == "retry":
                await service.start_run(TASK, run_id=999999)
            else:
                await service.get_run(999999)

        assert raised.value.details == {"run_id": 999999}


@pytest.mark.integration
@pytest.mark.database
class TestJobRunListing:
    """Reading the history."""

    async def test_list_runs_returns_the_newest_first(self, service: OperationsService) -> None:
        """The console shows the latest run at the top."""
        # Arrange
        first = await service.start_run("portal.extract_invoices")
        second = await service.start_run("portal.extract_orders")

        # Act
        runs, total = await service.list_runs()

        # Assert
        assert [run.id for run in runs] == [second.id, first.id]
        assert total == 2

    async def test_list_runs_filters_by_task(self, service: OperationsService) -> None:
        """Filtering by task narrows both the page and the total."""
        # Arrange
        await service.start_run("portal.extract_invoices")
        await service.start_run("portal.extract_orders")

        # Act
        runs, total = await service.list_runs(task_name="portal.extract_orders")

        # Assert
        assert [run.task_name for run in runs] == ["portal.extract_orders"]
        assert total == 1

    async def test_list_runs_filters_by_status(self, service: OperationsService) -> None:
        """Asking what failed last night is one filter, not a scan of the history."""
        # Arrange
        failed = await service.start_run(TASK)
        await service.fail_run(failed.id, "Timeout")
        await service.start_run(TASK)

        # Act
        runs, total = await service.list_runs(status=JobStatus.FAILED)

        # Assert
        assert [run.id for run in runs] == [failed.id]
        assert total == 1

    async def test_list_runs_paginates(self, service: OperationsService) -> None:
        """The total ignores the page bounds."""
        # Arrange
        for _ in range(3):
            await service.start_run(TASK)

        # Act
        runs, total = await service.list_runs(skip=1, limit=1)

        # Assert
        assert len(runs) == 1
        assert total == 3


@pytest.mark.integration
@pytest.mark.database
class TestParameters:
    """Business rules that change without a deploy, and only within their range.

    The table stopped being the list of parameters when 003 landed: it holds the
    values the owner changed, and everything else — that a parameter exists, what
    it starts at, how far it may move — is declared in `app.shared.parameters`.
    These tests are about that seam.
    """

    async def test_the_whole_catalog_is_listed_before_anybody_changes_anything(
        self, service: OperationsService
    ) -> None:
        """RF-01 and RF-04 together: every parameter, each with a value."""
        # Act
        listed = await service.list_parameters()

        # Assert
        assert {parameter.key for parameter in listed} == {spec.key for spec in PARAMETERS}
        assert all(parameter.changed_at is None for parameter in listed)
        assert all(parameter.value == parameter.initial for parameter in listed)

    async def test_a_parameter_nobody_touched_reports_its_starting_value(
        self, service: OperationsService
    ) -> None:
        """RF-04: the platform behaves on day one without a row anywhere."""
        # Assert
        assert await service.get_parameter_value(INTERVAL) == 12

    async def test_setting_a_parameter_puts_the_new_value_in_force(
        self, service: OperationsService
    ) -> None:
        """RF-02, and RF-07: nothing else has to happen for it to take effect."""
        # Act
        written = await service.set_parameters(
            [ParameterWrite(key=INTERVAL, value=24)], actor_user_id=ACTOR
        )

        # Assert
        assert written[0].value == 24
        assert written[0].changed_at is not None
        assert await service.get_parameter_value(INTERVAL) == 24

    async def test_setting_it_twice_overwrites_instead_of_duplicating(
        self, service: OperationsService
    ) -> None:
        """One key, one row: the second decision replaces the first."""
        # Arrange
        await service.set_parameters([ParameterWrite(key=INTERVAL, value=24)], actor_user_id=ACTOR)

        # Act
        await service.set_parameters([ParameterWrite(key=INTERVAL, value=6)], actor_user_id=ACTOR)

        # Assert
        assert await service.get_parameter_value(INTERVAL) == 6
        assert len(await service.list_parameters()) == len(PARAMETERS)

    async def test_a_key_outside_the_catalog_is_refused(self, service: OperationsService) -> None:
        """The list is closed (RF-06), which is also what keeps a secret out of it."""
        # Act / Assert
        with pytest.raises(ValidationError):
            await service.set_parameters(
                [ParameterWrite(key="portal.password", value="hunter2")], actor_user_id=ACTOR
            )

    async def test_a_value_outside_the_range_is_refused_with_the_range(
        self, service: OperationsService
    ) -> None:
        """RF-06 with its own example: a frequency of zero is not a frequency."""
        # Act / Assert
        with pytest.raises(ValidationError) as refusal:
            await service.set_parameters(
                [ParameterWrite(key=INTERVAL, value=0)], actor_user_id=ACTOR
            )

        assert "1" in refusal.value.message
        assert "168" in refusal.value.message

    async def test_nothing_is_written_when_one_value_of_the_set_is_refused(
        self, service: OperationsService
    ) -> None:
        """Half-applied settings would leave the business on a mix of rules."""
        # Act
        with pytest.raises(ValidationError):
            await service.set_parameters(
                [
                    ParameterWrite(key=INTERVAL, value=24),
                    ParameterWrite(key=THRESHOLD, value=-1),
                ],
                actor_user_id=ACTOR,
            )

        # Assert — the legal one did not sneak through
        assert await service.get_parameter_value(INTERVAL) == 12

    async def test_a_change_leaves_its_line_in_the_log(self, service: OperationsService) -> None:
        """RF-08: the old value, the new one, who changed it and when."""
        # Arrange
        await service.set_parameters([ParameterWrite(key=INTERVAL, value=24)], actor_user_id=ACTOR)

        # Act
        history = await service.list_audit(sections=None)

        # Assert
        assert history.total == 1
        entry = history.items[0]
        assert entry.entity_id == INTERVAL
        assert entry.old_value == 12
        assert entry.new_value == 24
        assert entry.actor_user_id == ACTOR
        assert entry.section is BusinessSection.SYSTEM
        assert entry.occurred_at is not None

    async def test_a_decimal_keeps_its_cents_through_jsonb(
        self, service: OperationsService
    ) -> None:
        """Stored as text so a percentage does not come back as a float."""
        # Act
        await service.set_parameters(
            [ParameterWrite(key=THRESHOLD, value="12.50")], actor_user_id=ACTOR
        )

        # Assert
        assert await service.get_parameter_value(THRESHOLD) == "12.50"
        assert await service.highlight_threshold() == Decimal("12.50")

    async def test_asking_for_a_key_that_is_not_a_parameter(
        self, service: OperationsService
    ) -> None:
        """Not "missing": there is no such parameter, and there never was."""
        # Act / Assert
        with pytest.raises(ValidationError) as refused:
            await service.get_parameter("nope")

        assert refused.value.details["key"] == "nope"


@pytest.mark.integration
@pytest.mark.database
class TestHealth:
    """The report behind `/health`."""

    async def test_health_is_ok_against_a_live_database(self, service: OperationsService) -> None:
        """Every component answering means the service is ok."""
        # Act
        report = await service.health()

        # Assert
        assert report.status is HealthState.OK
        assert report.database.status is HealthState.OK
        assert report.database.detail is None
