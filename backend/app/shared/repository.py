"""Generic async repository.

Repositories are private to their module, like everything else in it: a module
never imports another module. What another module needs to know arrives as a
domain event (`app.shared.events`), not as a call.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base


class BaseRepository[ModelT: Base]:
    """CRUD primitives shared by every repository."""

    def __init__(self, model: type[ModelT], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get(self, entity_id: int) -> ModelT | None:
        """Return an entity by primary key, or None."""
        return await self.session.get(self.model, entity_id)

    async def list(self, *, skip: int = 0, limit: int = 100) -> list[ModelT]:
        """Return a page of entities."""
        result = await self.session.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def count(self) -> int:
        """Return the total number of entities."""
        result = await self.session.execute(select(func.count()).select_from(self.model))
        return int(result.scalar_one())

    async def add(self, entity: ModelT) -> ModelT:
        """Persist a new entity and return it with server-side defaults applied."""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: ModelT, values: dict[str, Any]) -> ModelT:
        """Apply the given values to an entity and flush."""
        for field, value in values.items():
            setattr(entity, field, value)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        """Remove an entity."""
        await self.session.delete(entity)
        await self.session.flush()
