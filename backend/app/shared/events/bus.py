"""The bus modules talk through.

A module never imports another module. When something happens that another part
of the business cares about, the owning module publishes a domain event and
forgets about it; whoever cares subscribes. Nobody holds a reference to anyone.

Handlers run **in the publisher's session and transaction**. That is deliberate:
the reaction to an event either commits with the fact that caused it or neither
does. A handler that raises aborts the publisher — events are not a place where
work disappears quietly (`CONSTITUTION.md`, Artículo II).

Work that must not block the publisher, or that must survive a crash, does not
belong in a handler body: the handler enqueues a Celery task and returns.
"""

import logging
import pkgutil
from collections import defaultdict
from collections.abc import Awaitable, Callable
from importlib import import_module

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.events.catalog import DomainEvent

logger = logging.getLogger(__name__)

type Handler[EventT: DomainEvent] = Callable[[EventT, AsyncSession], Awaitable[None]]


class EventBus:
    """An in-process registry of handlers, keyed by event type.

    In-process is not a limitation to route around: the product is one
    deployable, and a handler sharing the publisher's transaction is the only
    way an event can be atomic with the fact it reports.
    """

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[Handler]] = defaultdict(list)

    def subscribe[EventT: DomainEvent](
        self, event_type: type[EventT]
    ) -> Callable[[Handler[EventT]], Handler[EventT]]:
        """Register a coroutine as a handler for one event type.

        Used as a decorator in a module's `handlers.py`:

            @events.subscribe(InvoiceRegistered)
            async def open_receivable(event: InvoiceRegistered, session: AsyncSession) -> None:
                ...
        """

        def register(handler: Handler[EventT]) -> Handler[EventT]:
            self._handlers[event_type].append(handler)
            return handler

        return register

    async def publish(self, event: DomainEvent, session: AsyncSession) -> None:
        """Run every handler subscribed to this event, in registration order.

        Publishing an event nobody listens to is legal and does nothing — a
        module states that something happened; it does not require an audience.
        """
        handlers = self._handlers[type(event)]
        if not handlers:
            logger.debug("event %s published with no subscribers", type(event).__name__)
            return

        for handler in handlers:
            await handler(event, session)

    def handlers_for(self, event_type: type[DomainEvent]) -> tuple[Handler, ...]:
        """Return the handlers registered for an event type. For tests."""
        return tuple(self._handlers[event_type])

    def clear(self) -> None:
        """Drop every registration. For tests only."""
        self._handlers.clear()


events = EventBus()
"""The bus. One per process, imported by every module that publishes or subscribes."""


def discover_handlers() -> list[str]:
    """Import every module's `handlers.py` so its subscriptions register.

    Called once by `app.main`. Discovery is automatic on purpose: a handler that
    is never imported is a subscription that silently does not exist, and a
    composition root with eleven hand-written imports is one `git merge` away
    from missing one.
    """
    package = import_module("app.modules")
    imported: list[str] = []

    for info in pkgutil.iter_modules(package.__path__):
        name = f"app.modules.{info.name}.handlers"
        try:
            import_module(name)
        except ModuleNotFoundError as exc:
            # The module has no handlers.py — legitimate. But a real import
            # error *inside* handlers.py also raises this, so only a missing
            # `handlers` module itself is tolerated.
            if exc.name != name:
                raise
            continue
        imported.append(name)

    return imported
