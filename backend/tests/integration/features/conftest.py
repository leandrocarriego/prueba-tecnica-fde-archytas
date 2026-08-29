"""Fixtures shared by the feature tests.

The one thing they all need is a platform that does not reach for the broker.
A handler that queues work returns immediately by design (`GEN-09`), and in a
test the queue is exactly the part that must not be exercised: the suite runs
with RabbitMQ down, like it runs with the portal down.
"""

from collections.abc import Iterator
from typing import Any

import pytest

from app.modules.notifications import tasks as notification_tasks
from app.modules.portal import handlers as portal_handlers


class Queued:
    """Records what would have been queued, instead of queueing it."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def apply_async(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)

    def delay(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append({"args": args, "kwargs": kwargs})

    @property
    def count(self) -> int:
        return len(self.calls)


@pytest.fixture
def queued_history(monkeypatch: pytest.MonkeyPatch) -> Iterator[Queued]:
    """The history visits a registered product would trigger (RF-38)."""
    recorder = Queued()
    monkeypatch.setattr(portal_handlers, "extract_product_history", recorder)
    yield recorder


@pytest.fixture
def queued_alerts(monkeypatch: pytest.MonkeyPatch) -> Iterator[Queued]:
    """The WhatsApp messages an interruption would send (RF-12)."""
    recorder = Queued()
    monkeypatch.setattr(notification_tasks, "send_whatsapp", recorder)
    yield recorder


@pytest.fixture
def queued_access_links(monkeypatch: pytest.MonkeyPatch) -> Iterator[Queued]:
    """The invitations and recovery links an access change would send.

    Recorded rather than sent, and the recording is the assertion: what a test
    checks is that the platform *decided* to send one, which is what the
    handler is responsible for. Whether Evolution API accepted it is the
    task's problem and the channel's test.
    """
    recorder = Queued()
    monkeypatch.setattr(notification_tasks, "send_access_link", recorder)
    yield recorder


@pytest.fixture(autouse=True)
def no_broker(queued_history: Queued, queued_alerts: Queued, queued_access_links: Queued) -> None:
    """No test in this package ever reaches RabbitMQ."""
    return None
