"""The alert that must never take anything down with it, and two guards.

`notifications` is the module with the weakest promise in the feature: it talks
to a free third-party service over the network, and RF-11 already puts the same
warning on a screen that depends on nobody. So what is pinned here is the
**failure** path — that an alert which cannot be delivered is reported, logged
and swallowed, never raised into the extraction that triggered it.

The two guards at the end are small and load-bearing: `operations` only closes
the runs of the task it owns, and the portal client never lets a browser error
carry a credential out of the module (Artículo VII).
"""

from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from playwright.async_api import Error as PlaywrightError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications import client as channel_module
from app.modules.notifications import service as notification_service
from app.modules.notifications import tasks as notification_tasks
from app.modules.notifications.client import NOT_CONFIGURED, Delivery, WhatsAppChannel
from app.modules.notifications.service import NotificationService
from app.modules.operations.models import JobStatus
from app.modules.operations.service import PRICE_UPDATE_TASK, OperationsService
from app.modules.portal.client import UNREADABLE, PortalClient
from app.shared.events import JobRunFailed, JobRunSucceeded, events
from tests.integration.features.conftest import Queued

pytestmark = [pytest.mark.integration, pytest.mark.database]

send_whatsapp = notification_tasks.send_whatsapp.run.__wrapped__

A_MESSAGE = "⚠️ Cordillera: la actualización de precios dejó de funcionar."


class Retried(Exception):
    """Raised by the stub instead of Celery's own `Retry`."""


def celery_self(*, retries: int = 0) -> Any:
    """A stand-in for the bound task, carrying only what the body reads."""
    return SimpleNamespace(
        request=SimpleNamespace(retries=retries), retry=lambda **_kwargs: Retried()
    )


def configured(channel: WhatsAppChannel, monkeypatch: pytest.MonkeyPatch) -> WhatsAppChannel:
    """A channel with somewhere to send to."""
    monkeypatch.setattr(channel, "base_url", "https://evolution.example")
    monkeypatch.setattr(channel, "instance", "cordillera")
    monkeypatch.setattr(channel, "api_key", "una-clave-de-prueba")
    monkeypatch.setattr(channel, "recipient", "5492944000000")
    return channel


def transport_answering(handler: Any, monkeypatch: pytest.MonkeyPatch) -> list[httpx.Request]:
    """Point the channel's HTTP client at a transport under the test's control.

    A real `httpx.AsyncClient` over a mock transport, not a fake client: what is
    worth testing is the request that actually goes out — its header, its body —
    and a stub of the client would only prove the stub.
    """
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    def build(**kwargs: Any) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(record), **kwargs)

    monkeypatch.setattr(
        channel_module, "httpx", SimpleNamespace(AsyncClient=build, HTTPError=httpx.HTTPError)
    )
    return seen


class TestDeliveringAnAlert:
    """What actually goes out, and what happens when it does not."""

    async def test_a_delivered_message_reaches_the_configured_number(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The recipient and the key travel in the request, never in the answer."""
        # Arrange
        channel = configured(WhatsAppChannel(), monkeypatch)
        requests = transport_answering(
            lambda _r: httpx.Response(200, json={"ok": True}), monkeypatch
        )

        # Act
        delivery = await NotificationService(channel).notify_owner(A_MESSAGE)

        # Assert
        assert delivery.sent is True
        assert requests[0].headers["apikey"] == "una-clave-de-prueba"
        assert b"5492944000000" in requests[0].content

    async def test_a_rejected_message_is_reported_and_not_raised(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Evolution API answering 500 must not abort an extraction that worked."""
        # Arrange
        channel = configured(WhatsAppChannel(), monkeypatch)
        transport_answering(lambda _r: httpx.Response(500, text="boom"), monkeypatch)

        # Act
        delivery = await NotificationService(channel).notify_owner(A_MESSAGE)

        # Assert
        assert delivery.sent is False
        assert delivery.detail == "HTTPStatusError"

    async def test_a_service_that_is_not_answering_is_reported_and_not_raised(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A free third-party service is down sometimes; that is not our outage."""

        # Arrange
        def refuse(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        channel = configured(WhatsAppChannel(), monkeypatch)
        transport_answering(refuse, monkeypatch)

        # Act
        delivery = await NotificationService(channel).notify_owner(A_MESSAGE)

        # Assert
        assert delivery.sent is False
        assert delivery.detail == "ConnectError"

    async def test_the_failure_never_names_the_instance_or_the_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The URL carries the instance, and the header carries the key."""
        # Arrange
        channel = configured(WhatsAppChannel(), monkeypatch)
        transport_answering(lambda _r: httpx.Response(401, text="unauthorized"), monkeypatch)

        # Act
        delivery = await NotificationService(channel).notify_owner(A_MESSAGE)

        # Assert
        assert "cordillera" not in delivery.detail
        assert "una-clave-de-prueba" not in delivery.detail


class TestTheSendingTask:
    """`notifications.send_whatsapp`: queued so its failure is its own."""

    async def test_an_unconfigured_channel_ends_the_task_quietly(self) -> None:
        """No retries, no exception: there is nowhere to send, and that is not transient."""
        # Act
        result = await send_whatsapp(celery_self(), A_MESSAGE)

        # Assert
        assert result == {"sent": False, "detail": NOT_CONFIGURED}

    async def test_a_delivery_that_failed_is_retried(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A service that is down now may be up in a minute."""

        # Arrange
        class Refusing:
            async def send(self, _message: str) -> Delivery:
                return Delivery(sent=False, detail="ConnectError")

        monkeypatch.setattr(notification_service, "WhatsAppChannel", Refusing)

        # Act / Assert
        with pytest.raises(Retried):
            await send_whatsapp(celery_self(retries=0), A_MESSAGE)

    async def test_once_the_retries_run_out_the_task_gives_up_quietly(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The alert is lost, the update is not. RF-11 is on the screen for this reason."""

        # Arrange
        class Refusing:
            async def send(self, _message: str) -> Delivery:
                return Delivery(sent=False, detail="ConnectError")

        monkeypatch.setattr(notification_service, "WhatsAppChannel", Refusing)

        # Act
        result = await send_whatsapp(celery_self(retries=notification_tasks.MAX_RETRIES), A_MESSAGE)

        # Assert
        assert result["sent"] is False

    async def test_a_stall_queues_exactly_one_message(
        self, session: AsyncSession, queued_alerts: Queued
    ) -> None:
        """RF-12 and RF-13, from the event to the queue."""
        # Arrange
        service = OperationsService(session)
        first = await service.request_price_update(dispatch=lambda _id: None)
        await service.record_price_update_failure(first.job_run_id, "El portal no responde")
        second = await service.request_price_update(dispatch=lambda _id: None)

        # Act
        await service.record_price_update_failure(second.job_run_id, "El portal no responde")

        # Assert
        assert queued_alerts.count == 1
        assert "actualización de precios" in queued_alerts.calls[0]["args"][0]


class TestOperationsOnlyClosesItsOwnRuns:
    """A module that reacts to every job run would close other people's work."""

    async def test_a_success_of_another_task_is_ignored(self, session: AsyncSession) -> None:
        """`JobRunSucceeded` is shared vocabulary: P2 will publish it too."""
        # Arrange
        service = OperationsService(session)
        requested = await service.request_price_update(dispatch=lambda _id: None)

        # Act
        await events.publish(
            JobRunSucceeded(job_run_id=requested.job_run_id, job_name="extract_invoices"), session
        )

        # Assert
        run = await service.get_run(requested.job_run_id)
        assert run.status is JobStatus.RUNNING

    async def test_a_failure_of_another_task_is_ignored(self, session: AsyncSession) -> None:
        """Ídem: someone else's failure is not this feature's interruption."""
        # Arrange
        service = OperationsService(session)
        requested = await service.request_price_update(dispatch=lambda _id: None)

        # Act
        await events.publish(
            JobRunFailed(
                job_run_id=requested.job_run_id, job_name="extract_invoices", message="boom"
            ),
            session,
        )

        # Assert
        run = await service.get_run(requested.job_run_id)
        assert run.status is JobStatus.RUNNING

    async def test_a_success_reported_for_a_run_that_does_not_exist_is_survivable(
        self, session: AsyncSession
    ) -> None:
        """A worker reporting about a deleted run must not take the transaction down."""
        # Act
        await events.publish(
            JobRunSucceeded(job_run_id=999_999, job_name=PRICE_UPDATE_TASK), session
        )

        # Assert: nothing raised, and nothing invented.
        assert (await OperationsService(session).price_update_status()).last_run_id is None


@pytest.mark.unit
class TestThePortalNeverLeaksItsCredentials:
    """Artículo VII: the account is a third party's, and it stays in the environment."""

    def test_a_navigation_error_is_wrapped_before_it_leaves_the_module(self) -> None:
        """Playwright quotes the URL it was on, and a login URL carries the account."""
        # Arrange
        leaky = PlaywrightError(
            "Timeout 15000ms exceeded.\n"
            "navigating to https://portal.example/login?usuario=proveedor&clave=secreta"
        )

        # Act
        wrapped = PortalClient._unreadable("prices", leaky)

        # Assert
        assert wrapped.message == UNREADABLE
        assert wrapped.details == {"section": "prices"}

    def test_nothing_of_the_original_message_survives_into_the_error(self) -> None:
        """What reaches `operations` and the screen is the section, and only that."""
        # Arrange
        leaky = PlaywrightError("page.fill: #clave with 'secreta' failed")

        # Act
        wrapped = PortalClient._unreadable("price-history", leaky)

        # Assert
        rendered = f"{wrapped.message} {wrapped.details}"
        assert "secreta" not in rendered
        assert "clave" not in rendered
