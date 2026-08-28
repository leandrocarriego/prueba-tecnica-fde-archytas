"""The single bridge between Celery's synchronous workers and our async code.

Celery executes tasks in synchronous worker processes, while every service and
repository in this application is async. Naively calling `asyncio.run()` inside
each task would create a fresh event loop per call, and asyncpg connections are
bound to the loop that opened them — the shared engine pool would hand a task a
connection belonging to a dead loop.

So each worker process owns exactly **one** event loop, running on a background
thread for the life of the process, and tasks submit coroutines to it. This is
the only place in the codebase allowed to start an event loop.
"""

import asyncio
import threading
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any

from app.logging import get_logger

logger = get_logger(__name__)


class _LoopRunner:
    """Owns one event loop per process and runs coroutines on it."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        """Start the loop thread on first use."""
        if self._loop is not None:
            return self._loop
        with self._lock:
            if self._loop is not None:
                return self._loop
            loop = asyncio.new_event_loop()
            thread = threading.Thread(
                target=loop.run_forever,
                name="cordillera-worker-loop",
                daemon=True,
            )
            thread.start()
            self._loop, self._thread = loop, thread
            logger.debug("Worker event loop started")
            return loop

    def run[R](self, coro: Coroutine[Any, Any, R]) -> R:
        """Run a coroutine on the worker loop and block until it finishes."""
        future = asyncio.run_coroutine_threadsafe(coro, self._ensure_loop())
        return future.result()

    def shutdown(self) -> None:
        """Stop the loop thread. Called on worker shutdown."""
        if self._loop is None:
            return
        with self._lock:
            loop, thread, self._loop, self._thread = self._loop, self._thread, None, None
        loop.call_soon_threadsafe(loop.stop)
        if thread is not None:
            thread.join(timeout=5)
        loop.close()
        logger.debug("Worker event loop stopped")


_runner = _LoopRunner()


def run_async[R](coro: Coroutine[Any, Any, R]) -> R:
    """Run an async call from synchronous Celery code."""
    return _runner.run(coro)


def shutdown_loop() -> None:
    """Tear down the worker loop. Wired to Celery's shutdown signal."""
    _runner.shutdown()


def async_task[**P, R](func: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, R]:
    """Turn an async function into a synchronous callable for Celery.

    Use it under the task decorator so the task body stays async:

        @celery_app.task(name="portal.extract_section")
        @async_task
        async def extract_section(section: str) -> None: ...
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return run_async(func(*args, **kwargs))

    return wrapper
