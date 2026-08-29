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
