"""Integration tests for `OperationsService`.

`operations` is the system operating on itself: the job history is what explains a
failed overnight extraction the next morning, and the parameters are the rules
the business changes without a deploy. Both are exercised against a real
session, since both are about what ends up stored.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operations.models import JobStatus
from app.modules.operations.schemas import HealthState, ParameterWrite
from app.modules.operations.service import OperationsService
from app.shared.errors import NotFoundError

TASK = "portal.extract_invoices"


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
    """Business rules that change without a deploy."""

    async def test_set_parameters_creates_the_batch(self, service: OperationsService) -> None:
        """The whole set is written at once, so the platform never runs on half of it."""
        # Arrange
        items = [
            ParameterWrite(key="extraction.hour", value=3, description="Nightly extraction"),
            ParameterWrite(key="matching.threshold", value=0.87, description="Fuzzy matching"),
        ]

        # Act
        written = await service.set_parameters(items)

        # Assert
        assert {parameter.key for parameter in written} == {
            "extraction.hour",
            "matching.threshold",
        }
        assert await service.get_parameter_value("extraction.hour") == 3

    async def test_set_parameters_overwrites_by_key(self, service: OperationsService) -> None:
        """A second write updates the row instead of adding a duplicate key."""
        # Arrange
        await service.set_parameters([ParameterWrite(key="extraction.hour", value=3)])

        # Act
        await service.set_parameters([ParameterWrite(key="extraction.hour", value=5)])
        stored = await service.list_parameters()

        # Assert
        assert len(stored) == 1
        assert stored[0].value == 5

    async def test_omitting_the_description_keeps_the_stored_one(
        self, service: OperationsService
    ) -> None:
        """A caller changing only a value should not have to resend the label."""
        # Arrange
        await service.set_parameters(
            [ParameterWrite(key="extraction.hour", value=3, description="Nightly extraction")]
        )

        # Act
        await service.set_parameters([ParameterWrite(key="extraction.hour", value=5)])
        parameter = await service.get_parameter("extraction.hour")

        # Assert
        assert parameter.value == 5
        assert parameter.description == "Nightly extraction"

    async def test_a_value_can_be_any_json(self, service: OperationsService) -> None:
        """JSONB, so a parameter can be a number, a flag or a small structure."""
        # Arrange
        items = [
            ParameterWrite(key="alerts.enabled", value=True),
            ParameterWrite(key="portal.sections", value=["invoices", "orders"]),
            ParameterWrite(key="limits", value={"per_page": 50}),
        ]

        # Act
        await service.set_parameters(items)

        # Assert
        assert await service.get_parameter_value("alerts.enabled") is True
        assert await service.get_parameter_value("portal.sections") == ["invoices", "orders"]
        assert await service.get_parameter_value("limits") == {"per_page": 50}

    async def test_list_parameters_is_ordered_by_key(self, service: OperationsService) -> None:
        """The settings screen shows them in a stable order."""
        # Arrange
        await service.set_parameters(
            [
                ParameterWrite(key="zeta", value=1),
                ParameterWrite(key="alfa", value=2),
            ]
        )

        # Act
        stored = await service.list_parameters()

        # Assert
        assert [parameter.key for parameter in stored] == ["alfa", "zeta"]

    async def test_get_parameter_not_found(self, service: OperationsService) -> None:
        """Asking for a parameter by key is an explicit read: a miss is an error."""
        # Act / Assert
        with pytest.raises(NotFoundError) as raised:
            await service.get_parameter("nope")

        assert raised.value.details == {"key": "nope"}

    async def test_get_parameter_value_falls_back_to_the_default(
        self, service: OperationsService
    ) -> None:
        """Other modules read parameters this way.

        A parameter nobody configured is a gap in the configuration, not a
        reason to interrupt a purchase or an extraction.
        """
        assert await service.get_parameter_value("nope", default=7) == 7


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
