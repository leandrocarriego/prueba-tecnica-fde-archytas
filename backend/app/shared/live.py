"""The live channel: telling the browsers of other people that something moved.

**Why this exists and why it is here.** A screen that two people keep open for
hours, deciding on it, has to be the same screen for both of them. Everything
else in this platform answers a request; this is the one thing the server has
to say without being asked.

It lives in `shared/` because it carries no domain: it moves opaque strings
between processes. What travels and what it means belongs to the module that
publishes it, and `shared/` never imports a module (`GEN-03`).

**Two processes, not one.** The deployment runs `uvicorn --workers 2`, so a
person watching is attached to one worker and whoever moves something may be
talking to the other. An in-memory list of subscribers works perfectly on a
developer's machine and fails half the time in production, which is the worst
way to fail. The bus between the workers is Postgres itself — `LISTEN` and
`NOTIFY` — and not the task broker: the queue of the workers and the channel of
a screen have different lifetimes, and one being down should not take the other
with it. It also adds no dependency: the database is already there.

**Why `NOTIFY` and not a push from the handler.** A domain handler runs inside
the transaction of whoever published (`GEN-09`), so writing to a socket from
there would make one person's dropped WiFi able to abort another person's
change. `NOTIFY` cannot do that: it is transactional — Postgres delivers it
**on commit**, and a transaction that aborts notifies nobody — and it does no
network I/O of its own. Delivery is best effort: whoever is listening gets it,
whoever is not does not. That is the right trade here, because a screen that
reconnects re-reads what it shows, and a channel that promises to lose nothing
needs persistence nobody asked for.
"""

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from typing import Any

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.logging import get_logger

logger = get_logger(__name__)

# One channel for the whole platform. What kind of change it is travels inside
# the message, so a second screen that needs live updates does not need a second
# listener — and Postgres channel names are a global namespace, which is exactly
# the kind of thing that is cheap to keep small.
CHANNEL = "cordillera_live"

# A slow reader does not get to hold the process. If a browser stops draining
# its queue, its messages are dropped and it will catch up when it re-reads.
QUEUE_LIMIT = 100


async def announce(session: AsyncSession, topic: str, payload: dict[str, Any]) -> None:
    """Say something on the channel, inside the caller's transaction.

    Nothing is delivered until that transaction commits, which is what makes
    this safe to call from a domain handler.
    """
    message = json.dumps({"topic": topic, "data": payload}, default=str)
    await session.execute(
        text("SELECT pg_notify(:channel, :message)"), {"channel": CHANNEL, "message": message}
    )


class LiveBus:
    """Every browser attached to *this* worker, and the one connection that feeds them."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._connection: asyncpg.Connection | None = None
        self._started = False

    async def start(self) -> None:
        """Open the dedicated connection that listens. Never fatal.

        A platform whose calendar does not update live is worse than one that
        does; a platform that refuses to boot because of it is worse than both.
        """
        if self._started:
            return
        try:
            self._connection = await asyncpg.connect(dsn=_dsn())
            await self._connection.add_listener(CHANNEL, self._on_message)
            self._started = True
            logger.info("Live channel listening", extra={"channel": CHANNEL})
        except Exception as error:  # noqa: BLE001 - se informa y la app sigue
            logger.warning("Live channel unavailable: %s", error)

    async def stop(self) -> None:
        """Let the connection go, and every reader with it."""
        if self._connection is not None:
            with contextlib.suppress(Exception):
                await self._connection.remove_listener(CHANNEL, self._on_message)
                await self._connection.close()
        self._connection = None
        self._started = False
        self._subscribers.clear()

    def _on_message(self, _connection: object, _pid: int, _channel: str, payload: str) -> None:
        """Hand what arrived to every reader of this worker, dropping the slow ones."""
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning("A live reader fell behind and lost a message")

    async def read(self) -> AsyncIterator[str]:
        """One reader: the messages, as they come."""
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=QUEUE_LIMIT)
        self._subscribers.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)

    @property
    def readers(self) -> int:
        """How many browsers this worker is feeding. For the health of the thing."""
        return len(self._subscribers)


def _dsn() -> str:
    """The URL asyncpg wants, which is the SQLAlchemy one without its driver."""
    return settings.database_url.replace("postgresql+asyncpg://", "postgresql://")


# One per process, like the engine.
bus = LiveBus()
