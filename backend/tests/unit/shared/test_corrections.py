"""The vocabulary of a correction, without a database in sight.

What can go wrong here is a list that says one thing and a validator that
accepts another: the reason a person picks is validated against the same enum
the screen renders, so the two cannot drift. These tests are what says so.
"""

import pytest

from app.shared.corrections import (
    REASON_LABELS,
    CorrectionReason,
    CorrectionStatus,
    label_for,
)


@pytest.mark.unit
class TestTheReasons:
    """A short list, in the words a person picks by (RF-11)."""

    def test_every_reason_has_words(self) -> None:
        """A code with no label would reach the screen as a code."""
        # Assert
        assert set(REASON_LABELS) == set(CorrectionReason)
        assert all(label.strip() for label in REASON_LABELS.values())

    def test_the_list_is_short_enough_to_count(self) -> None:
        """The point of a list is being able to count what happened for the same reason.

        A list long enough to cover every case is a list where everybody picks
        a different entry, and counting it says nothing. The written detail is
        what carries the odd one out.
        """
        # Assert
        assert len(CorrectionReason) <= 6

    def test_a_code_reads_as_its_words(self) -> None:
        # Assert
        assert label_for(CorrectionReason.PORTAL_WAS_WRONG.value) == "El portal lo informó mal"

    def test_no_code_reads_as_nothing(self) -> None:
        """A change with no reason — undoing a correction — has none to show."""
        # Assert
        assert label_for(None) is None

    def test_a_code_that_is_no_longer_on_the_list_still_reads(self) -> None:
        """The log is append-only, so a reason that was legal stays readable."""
        # Assert
        assert label_for("A_REASON_FROM_LAST_YEAR") == "A_REASON_FROM_LAST_YEAR"


@pytest.mark.unit
class TestTheStates:
    """Where a correction can stand."""

    def test_undoing_is_a_state_and_not_a_deletion(self) -> None:
        """RF-32: who undid it and when are part of the record."""
        # Assert
        assert CorrectionStatus.REVERTED in set(CorrectionStatus)
