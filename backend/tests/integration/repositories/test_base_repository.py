"""Integration tests for `app.shared.repository.BaseRepository`.

Every repository in the platform inherits these five primitives, so they are
exercised against a real PostgreSQL session rather than a mock.

The model under test is `operations.Parameter`, an existing table. Declaring a
throwaway model here would register a table that the schema — created once, at
the start of the run — does not have.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operations.models import Parameter
from app.shared.repository import BaseRepository


@pytest.mark.integration
@pytest.mark.database
class TestBaseRepository:
    """CRUD primitives against the database."""

    @pytest.fixture
    def repository(self, session: AsyncSession) -> BaseRepository[Parameter]:
        """A repository over an existing table."""
        return BaseRepository(Parameter, session)

    async def test_add_returns_the_entity_with_its_defaults(
        self, repository: BaseRepository[Parameter]
    ) -> None:
        """`add` flushes and refreshes, so server-side defaults are already there."""
        # Arrange
        parameter = Parameter(key="extraction.hour", value=3, description="Nightly extraction")

        # Act
        stored = await repository.add(parameter)

        # Assert
        assert stored.id is not None
        assert stored.key == "extraction.hour"
        # `updated_at` has a server default: it can only be known after the flush.
        assert stored.updated_at is not None

    async def test_get_returns_the_entity(self, repository: BaseRepository[Parameter]) -> None:
        """A stored row comes back by primary key."""
        # Arrange
        stored = await repository.add(Parameter(key="tolerance.days", value=5))

        # Act
        found = await repository.get(stored.id)

        # Assert
        assert found is not None
        assert found.id == stored.id
        assert found.value == 5

    async def test_get_returns_none_when_the_id_does_not_exist(
        self, repository: BaseRepository[Parameter]
    ) -> None:
        """A miss is None, not an exception: turning it into an error is the service's job."""
        assert await repository.get(999999) is None

    async def test_list_returns_every_entity(self, repository: BaseRepository[Parameter]) -> None:
        """Without arguments the page covers everything stored."""
        # Arrange
        for index in range(3):
            await repository.add(Parameter(key=f"key.{index}", value=index))

        # Act
        found = await repository.list()

        # Assert
        assert len(found) == 3

    async def test_list_paginates(self, repository: BaseRepository[Parameter]) -> None:
        """`skip` and `limit` bound the page."""
        # Arrange
        for index in range(5):
            await repository.add(Parameter(key=f"key.{index}", value=index))

        # Act
        page = await repository.list(skip=1, limit=2)

        # Assert
        assert len(page) == 2

    async def test_list_of_an_empty_table_is_empty(
        self, repository: BaseRepository[Parameter]
    ) -> None:
        """Nothing stored means an empty list, not None."""
        assert await repository.list() == []

    async def test_count_counts_the_rows(self, repository: BaseRepository[Parameter]) -> None:
        """`count` ignores pagination: it is the total."""
        # Arrange
        assert await repository.count() == 0
        for index in range(4):
            await repository.add(Parameter(key=f"key.{index}", value=index))

        # Act
        total = await repository.count()

        # Assert
        assert total == 4

    async def test_update_applies_the_given_values(
        self, repository: BaseRepository[Parameter]
    ) -> None:
        """Only the fields passed in change."""
        # Arrange
        stored = await repository.add(
            Parameter(key="tolerance.days", value=5, description="original")
        )

        # Act
        updated = await repository.update(stored, {"value": 9})

        # Assert
        assert updated.value == 9
        assert updated.description == "original"
        assert updated.id == stored.id

    async def test_update_is_visible_to_a_later_read(
        self, repository: BaseRepository[Parameter]
    ) -> None:
        """The change reaches the database, not just the in-memory object."""
        # Arrange
        stored = await repository.add(Parameter(key="tolerance.days", value=5))

        # Act
        await repository.update(stored, {"value": 9})
        repository.session.expunge_all()
        found = await repository.get(stored.id)

        # Assert
        assert found is not None
        assert found.value == 9

    async def test_delete_removes_the_entity(self, repository: BaseRepository[Parameter]) -> None:
        """After deleting, the row is gone and the count reflects it."""
        # Arrange
        stored = await repository.add(Parameter(key="tolerance.days", value=5))

        # Act
        await repository.delete(stored)

        # Assert
        assert await repository.get(stored.id) is None
        assert await repository.count() == 0

    async def test_rows_do_not_leak_between_tests(
        self, repository: BaseRepository[Parameter]
    ) -> None:
        """The isolation this suite depends on, asserted instead of assumed.

        Every other test in this class writes parameters. If the rollback per
        test were not happening, this one would find them.
        """
        assert await repository.count() == 0
