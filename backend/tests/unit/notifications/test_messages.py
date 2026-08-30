"""What the owner actually reads on their phone, and when nothing is sent.

The wording is the whole domain of `notifications`, so it is tested like domain
logic: in Spanish, because a person reads it, and without a network anywhere
near it.
"""

from datetime import UTC, datetime

import pytest

from app.modules.notifications.client import NOT_CONFIGURED, WhatsAppChannel
from app.modules.notifications.service import (
    NEVER,
    NotificationService,
    conflict_message,
    recovered_message,
    stalled_message,
)

pytestmark = pytest.mark.unit

A_MOMENT = datetime(2026, 8, 29, 7, 30, tzinfo=UTC)


class TestTheWording:
    """It has to be readable by somebody who is not looking at a screen."""

    def test_the_alert_says_what_broke_and_since_when(self) -> None:
        """RF-12: an alert that does not say when it last worked is not useful."""
        # Act
        message = stalled_message(consecutive_failures=2, last_success_at=A_MOMENT)

        # Assert
        assert "actualización de precios" in message
        assert "2" in message
        assert "29/08/2026 07:30" in message

    def test_it_says_so_when_there_never_was_a_successful_update(self) -> None:
        """A blank where the date goes reads like a bug."""
        # Act
        message = stalled_message(consecutive_failures=2, last_success_at=None)

        # Assert
        assert NEVER in message

    def test_the_all_clear_says_it_is_working_again(self) -> None:
        """So the owner does not have to open the screen to check."""
        # Act
        message = recovered_message(recovered_at=A_MOMENT)

        # Assert
        assert "volvió a funcionar" in message
        assert "29/08/2026 07:30" in message


class TestAChannelThatIsNotConfigured:
    """An alert that cannot be delivered is logged, and never raises."""

    async def test_it_reports_that_nothing_was_sent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The extraction that triggered it must not fail because of this."""
        # Arrange
        channel = WhatsAppChannel()
        monkeypatch.setattr(channel, "base_url", "")

        # Act
        delivery = await NotificationService(channel).notify_owner("hola")

        # Assert
        assert delivery.sent is False
        assert delivery.detail == NOT_CONFIGURED

    def test_it_knows_it_is_not_configured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Four settings, and all four are needed to reach anybody."""
        # Arrange
        channel = WhatsAppChannel()

        # Act
        monkeypatch.setattr(channel, "recipient", "")

        # Assert
        assert channel.is_configured is False


@pytest.mark.unit
class TestTheConflictAlert:
    """RF-29: the owner finds out without having to be looking at the screen."""

    def test_it_carries_the_three_values(self) -> None:
        """What the portal said, what a person corrected it to, and what it says now."""
        # Act
        message = conflict_message(
            field="price", original="1000", corrected="1200", incoming="1500"
        )

        # Assert
        assert "1000" in message
        assert "1200" in message
        assert "1500" in message

    def test_it_says_the_correction_still_stands(self) -> None:
        """The system flags and waits: it never picks one of the two (RF-28)."""
        # Act
        message = conflict_message(field="price", original="1", corrected="2", incoming="3")

        # Assert
        assert "sigue en pie" in message

    def test_the_field_is_named_in_spanish(self) -> None:
        """It travels as another module's code and is read by a person."""
        # Assert
        assert "precio" in conflict_message(
            field="price", original="1", corrected="2", incoming="3"
        )

    def test_a_field_nobody_translated_still_names_itself(self) -> None:
        """A message missing a word still says what happened."""
        # Assert
        assert "invoice_number" in conflict_message(
            field="invoice_number", original="1", corrected="2", incoming="3"
        )

    def test_it_names_the_datum_the_conflict_is_about(self) -> None:
        """Two conflicts in one nightly run carry the same field and can carry
        the same numbers: the datum is the only thing that tells them apart."""
        # Act
        message = conflict_message(
            field="price",
            original="1",
            corrected="2",
            incoming="3",
            entity_type="catalog.product_price",
            entity_id="12",
        )

        # Assert
        assert "Producto #12" in message

    def test_it_gives_a_way_to_reach_that_screen(self) -> None:
        """RF-29: the alert is read at night, on a phone, away from the system.

        The id is internal — no screen shows it — so knowing which product
        disagrees is worth nothing without the address of its screen.
        """
        # Act
        message = conflict_message(
            field="price",
            original="1",
            corrected="2",
            incoming="3",
            entity_type="catalog.product_price",
            entity_id="12",
        )

        # Assert
        assert "/precios/12" in message

    def test_an_entity_nobody_named_never_reaches_the_owner_as_code(self) -> None:
        """A namespace with a dot in it is not something a person reads."""
        # Act
        message = conflict_message(
            field="price",
            original="1",
            corrected="2",
            incoming="3",
            entity_type="catalog.invoice",
            entity_id="7",
        )

        # Assert
        assert "catalog.invoice" not in message
        assert "Dato #7" in message

    def test_without_a_reference_it_does_not_invent_one(self) -> None:
        """Naming one datum «#None» reads like a bug and says less than silence."""
        # Act
        message = conflict_message(field="price", original="1", corrected="2", incoming="3")

        # Assert
        assert "#" not in message
        assert "Revisala en la pantalla del dato." in message
