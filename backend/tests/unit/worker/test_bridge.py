"""Unit tests for `app.worker.bridge`.

The bridge is the only place allowed to start an event loop. These tests are
synchronous on purpose: they stand where a Celery worker stands, outside any
running loop.
"""

import asyncio
from collections.abc import Iterator

import pytest

from app.worker.bridge import async_task, run_async, shutdown_loop


@pytest.fixture(autouse=True)
def stop_worker_loop() -> Iterator[None]:
    """Leave the process without a running worker loop.

    The runner is a module-level singleton, so a test that starts it must also
    stop it or the thread outlives the suite.
    """
    yield
    shutdown_loop()


async def _echo(value: str) -> str:
    return value


async def _boom() -> None:
    raise RuntimeError("the task failed")


async def _current_loop() -> asyncio.AbstractEventLoop:
    return asyncio.get_running_loop()


@pytest.mark.unit
class TestRunAsync:
    """Synchronous code calling async code, and getting the real answer back."""

    def test_returns_the_result_of_the_coroutine(self) -> None:
        """The caller blocks until the coroutine is done."""
        assert run_async(_echo("extracted")) == "extracted"

    def test_propagates_the_exception(self) -> None:
        """A failing task must fail the Celery task, not disappear in a thread."""
        with pytest.raises(RuntimeError, match="the task failed"):
            run_async(_boom())

    def test_every_call_shares_one_event_loop(self) -> None:
        """One loop per process: asyncpg connections are bound to their loop.

        A fresh loop per call would hand a task a pooled connection that belongs
        to a loop that is already closed.
        """
        # Act
        first = run_async(_current_loop())
        second = run_async(_current_loop())

        # Assert
        assert first is second
        assert first.is_running()

    def test_the_loop_restarts_after_a_shutdown(self) -> None:
        """A worker that shut its loop down can still be used again."""
        # Arrange
        first = run_async(_current_loop())

        # Act
        shutdown_loop()
        second = run_async(_current_loop())

        # Assert
        assert first is not second
        assert run_async(_echo("still working")) == "still working"

    def test_shutdown_is_safe_without_a_loop(self) -> None:
        """Celery sends the shutdown signal whether or not any task ran."""
        shutdown_loop()
        shutdown_loop()


@pytest.mark.unit
class TestAsyncTask:
    """The decorator that lets a task body stay async."""

    def test_turns_an_async_function_into_a_sync_callable(self) -> None:
        """Celery calls it like any other function."""

        # Arrange
        @async_task
        async def extract(section: str, *, page: int = 1) -> str:
            return f"{section}:{page}"

        # Act
        result = extract("invoices", page=3)

        # Assert
        assert result == "invoices:3"

    def test_keeps_the_identity_of_the_wrapped_function(self) -> None:
        """Celery derives the default task name from `__name__`."""

        # Arrange
        @async_task
        async def extract_section() -> None:
            """Extract one section of the portal."""

        # Assert
        assert extract_section.__name__ == "extract_section"
        assert extract_section.__doc__ == "Extract one section of the portal."
