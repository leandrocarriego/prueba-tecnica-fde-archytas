"""The event bus: the only channel between modules.

These tests pin the three properties the boundary rule depends on. If any of
them stops holding, "modules communicate through events" stops being true even
though `test_module_boundaries.py` still passes: no import is needed to lose an
event, only a swallowed exception.
"""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from app.shared.events import DomainEvent, EventBus, UserRegistered, discover_handlers


@pytest.fixture
def bus() -> EventBus:
    """A bus of its own, so a test never sees another test's subscriptions."""
    return EventBus()


@pytest.fixture
def event() -> UserRegistered:
    return UserRegistered(user_id=7, email="duenio@cordillera.com.ar", role="OWNER")


@pytest.mark.unit
class TestPublishing:
    """What happens to an event once a module lets it go."""

    async def test_a_subscribed_handler_receives_the_event_and_the_session(
        self, bus: EventBus, event: UserRegistered
    ) -> None:
        """The handler gets the publisher's session so both commit together."""
        # Arrange
        seen: list[tuple[UserRegistered, object]] = []
        session = object()

        @bus.subscribe(UserRegistered)
        async def record(received: UserRegistered, received_session) -> None:  # noqa: ANN001
            seen.append((received, received_session))

        # Act
        await bus.publish(event, session)  # type: ignore[arg-type]

        # Assert
        assert seen == [(event, session)]

    async def test_an_event_with_no_subscribers_is_not_an_error(
        self, bus: EventBus, event: UserRegistered
    ) -> None:
        """A module reports a fact; it does not require an audience."""
        await bus.publish(event, None)  # type: ignore[arg-type]

    async def test_handlers_run_in_registration_order(
        self, bus: EventBus, event: UserRegistered
    ) -> None:
        """Order is deterministic, so a failure is reproducible."""
        # Arrange
        order: list[str] = []

        @bus.subscribe(UserRegistered)
        async def first(_event: UserRegistered, _session) -> None:  # noqa: ANN001
            order.append("first")

        @bus.subscribe(UserRegistered)
        async def second(_event: UserRegistered, _session) -> None:  # noqa: ANN001
            order.append("second")

        # Act
        await bus.publish(event, None)  # type: ignore[arg-type]

        # Assert
        assert order == ["first", "second"]

    async def test_a_failing_handler_aborts_the_publisher(
        self, bus: EventBus, event: UserRegistered
    ) -> None:
        """Artículo II: nothing is lost in silence.

        The publisher's transaction must roll back with the handler, otherwise
        the system commits a fact whose consequences never happened — exactly
        the silent partial state the constitution forbids.
        """

        # Arrange
        @bus.subscribe(UserRegistered)
        async def explode(_event: UserRegistered, _session) -> None:  # noqa: ANN001
            raise RuntimeError("handler failed")

        # Act / Assert
        with pytest.raises(RuntimeError, match="handler failed"):
            await bus.publish(event, None)  # type: ignore[arg-type]

    async def test_a_handler_is_only_called_for_its_own_event_type(self, bus: EventBus) -> None:
        """Dispatch is by exact type, never by inheritance from DomainEvent."""
        # Arrange
        calls: list[str] = []

        @bus.subscribe(UserRegistered)
        async def only_user_registered(_event, _session) -> None:  # noqa: ANN001
            calls.append("called")

        # Act
        await bus.publish(DomainEvent(), None)  # type: ignore[arg-type]

        # Assert
        assert calls == []


@pytest.mark.unit
class TestEventShape:
    """The guarantees the catalog promises about an event."""

    def test_an_event_cannot_be_mutated_by_a_handler(self, event: UserRegistered) -> None:
        """A handler never rewrites what it received."""
        with pytest.raises(FrozenInstanceError):
            event.user_id = 99  # type: ignore[misc]

    def test_an_event_is_stamped_with_an_aware_utc_timestamp(self, event: UserRegistered) -> None:
        """A naive timestamp makes two events from two processes uncomparable."""
        assert event.occurred_at.tzinfo is not None
        assert event.occurred_at.tzinfo.utcoffset(event.occurred_at) == UTC.utcoffset(None)
        assert event.occurred_at <= datetime.now(UTC)


@pytest.mark.unit
class TestRegistry:
    """Registration and discovery."""

    def test_subscribe_returns_the_handler_so_it_stays_callable(self, bus: EventBus) -> None:
        """The decorator must not replace the function it decorates."""

        # Arrange / Act
        @bus.subscribe(UserRegistered)
        async def handler(_event, _session) -> None:  # noqa: ANN001
            return None

        # Assert
        assert bus.handlers_for(UserRegistered) == (handler,)

    def test_clear_drops_every_registration(self, bus: EventBus) -> None:
        """Test isolation depends on this."""

        # Arrange
        @bus.subscribe(UserRegistered)
        async def handler(_event, _session) -> None:  # noqa: ANN001
            return None

        # Act
        bus.clear()

        # Assert
        assert bus.handlers_for(UserRegistered) == ()

    def test_discovery_tolerates_a_module_without_handlers(self) -> None:
        """Not every module reacts to something; a missing handlers.py is legal."""
        assert discover_handlers() == []
