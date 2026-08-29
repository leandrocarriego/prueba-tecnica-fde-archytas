"""Unit tests for the command that creates the first access.

It is the one account nobody can be invited into, so it is worth pinning what
it refuses to do: create a second owner, and run without knowing who the owner
is.
"""

import pytest

from app.modules.identity.bootstrap import MISSING_SETTINGS, create_first_owner
from app.modules.identity.models import UserRole
from tests.factories.user_factory import UserFactory


@pytest.mark.integration
@pytest.mark.database
class TestFirstOwner:
    """Installing the platform, once."""

    @pytest.fixture(autouse=True)
    def _owner_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The three values an installer would put in the environment."""
        from app.config import settings

        monkeypatch.setattr(settings, "OWNER_EMAIL", "dueno@example.com")
        monkeypatch.setattr(settings, "OWNER_NAME", "Dueño")
        monkeypatch.setattr(settings, "OWNER_PHONE", "+5491100001111")

    @pytest.fixture(autouse=True)
    def _same_session(self, session: object, monkeypatch: pytest.MonkeyPatch) -> None:
        """Run the command on the test's session, like the middleware does."""
        from contextlib import asynccontextmanager

        from app.modules.identity import bootstrap

        @asynccontextmanager
        async def _factory():  # type: ignore[no-untyped-def]
            yield session

        monkeypatch.setattr(bootstrap, "SessionFactory", _factory)

    async def test_it_creates_the_owner_and_invites_him(self, session: object) -> None:
        """He gets the same invitation as everybody else: nobody types his password."""
        # Act
        message = await create_first_owner()

        # Assert
        assert "Dueño creado" in message
        from app.modules.identity.repository import UserRepository

        created = await UserRepository(session).get_by_email("dueno@example.com")  # type: ignore[arg-type]
        assert created is not None
        assert created.role is UserRole.OWNER
        assert created.activated_at is None

    async def test_running_it_twice_leaves_one_owner(self, session: object) -> None:
        """Idempotent: an installer that reruns the step does not split the role."""
        # Act
        await create_first_owner()
        second = await create_first_owner()

        # Assert
        assert "Ya hay un dueño" in second

    async def test_it_refuses_when_there_is_already_an_owner(self, session: object) -> None:
        """RF-50 holds here too, and this is the path that bypasses the service."""
        # Arrange
        await UserFactory.create(session, role=UserRole.OWNER)  # type: ignore[arg-type]

        # Act / Assert
        assert "Ya hay un dueño" in await create_first_owner()

    async def test_it_says_what_is_missing_instead_of_guessing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An installer with an empty environment gets a sentence, not a traceback."""
        # Arrange
        from app.config import settings

        monkeypatch.setattr(settings, "OWNER_EMAIL", "")

        # Act / Assert
        assert await create_first_owner() == MISSING_SETTINGS
