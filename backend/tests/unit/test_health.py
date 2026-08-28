"""The health report, without a database.

The happy path is covered against a real one in
`tests/integration/test_health.py`. What is worth isolating here is the failure:
it is the branch nobody exercises by accident, and the one that has to hold when
everything else is broken.
"""

from typing import Any

import pytest
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.health import DATABASE_UNAVAILABLE, HealthState, check_health

pytestmark = pytest.mark.unit


class FailingSession:
    """A session whose every query fails, like one pointed at a dead database."""

    def __init__(self, error: Exception) -> None:
        self.error = error

    async def execute(self, *_args: Any, **_kwargs: Any) -> Any:
        raise self.error


class TestCheckHealth:
    """`check_health` answers instead of raising, whatever the database does."""

    @pytest.mark.parametrize(
        "error",
        [
            OperationalError("select 1", {}, Exception("connection refused")),
            OSError("network is unreachable"),
        ],
        ids=["sqlalchemy", "os"],
    )
    async def test_reports_the_database_as_down_instead_of_raising(self, error: Exception) -> None:
        report = await check_health(FailingSession(error))  # type: ignore[arg-type]

        assert report.status is HealthState.DOWN
        assert report.database.status is HealthState.DOWN

    async def test_the_detail_says_nothing_about_the_underlying_failure(self) -> None:
        """The endpoint is public: it must not leak the host, driver or credentials."""
        error = OperationalError(
            "select 1", {}, Exception("could not connect to server at 10.0.0.7:5432")
        )

        report = await check_health(FailingSession(error))  # type: ignore[arg-type]

        assert report.database.detail == DATABASE_UNAVAILABLE
        assert "10.0.0.7" not in str(report.model_dump())

    async def test_still_identifies_the_service_when_the_database_is_down(self) -> None:
        """The status page has to say *which* service is failing, not just that one is."""
        report = await check_health(FailingSession(OSError()))  # type: ignore[arg-type]

        assert report.service == settings.PROJECT_NAME
        assert report.environment == settings.ENVIRONMENT
