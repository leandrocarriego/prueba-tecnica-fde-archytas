"""A date somebody typed means that date on the shop's clock.

The instants the API stores carry their offset and are unambiguous. A filter
does not: `desde 2026-08-30` typed in Buenos Aires and read as UTC starts three
hours into the previous day and ends three hours short of the one asked for.
It is the same bug `frontend/lib/time.ts` was written for, at the other end of
the request.
"""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.shared.time import BUSINESS_TIME_ZONE, as_business_time

pytestmark = pytest.mark.unit


class TestAsBusinessTime:
    """What a naive instant becomes, and what an aware one does not."""

    def test_a_naive_moment_is_read_on_the_shops_clock(self) -> None:
        # Act
        moment = as_business_time(datetime(2026, 8, 30, 0, 0, 0))

        # Assert
        assert moment is not None
        assert moment.tzinfo is not None
        assert moment.utcoffset() == timedelta(hours=-3)

    def test_the_start_of_a_day_is_not_the_start_of_the_utc_day(self) -> None:
        """The whole point: the two are three hours apart, on different days."""
        # Act
        moment = as_business_time(datetime(2026, 8, 30, 0, 0, 0))

        # Assert
        assert moment is not None
        assert moment.astimezone(UTC) == datetime(2026, 8, 30, 3, 0, 0, tzinfo=UTC)

    def test_an_instant_that_already_said_its_offset_is_left_alone(self) -> None:
        """The caller said what they meant; reinterpreting it invents a moment."""
        # Arrange
        stated = datetime(2026, 8, 30, 0, 0, 0, tzinfo=timezone(timedelta(hours=2)))

        # Act / Assert
        assert as_business_time(stated) is stated

    def test_no_filter_stays_no_filter(self) -> None:
        """`None` is "nobody asked", not "midnight"."""
        # Assert
        assert as_business_time(None) is None

    def test_the_zone_is_the_one_the_business_runs_on(self) -> None:
        # Assert
        assert str(BUSINESS_TIME_ZONE) == "America/Argentina/Buenos_Aires"
