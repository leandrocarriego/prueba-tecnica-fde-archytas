"""Cross-module communication.

`from app.shared.events import events, UserRegistered` is the only way one
module reaches another. See `bus.py` for the mechanics and `catalog.py` for the
vocabulary.
"""

from app.shared.events.bus import EventBus, Handler, discover_handlers, events
from app.shared.events.catalog import (
    DomainEvent,
    JobRunFailed,
    UserDeactivated,
    UserRegistered,
)

__all__ = [
    "DomainEvent",
    "EventBus",
    "Handler",
    "JobRunFailed",
    "UserDeactivated",
    "UserRegistered",
    "discover_handlers",
    "events",
]
