"""Data access for the messaging module. Private to this module."""

from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.messaging.models import (
    MessageKind,
    MessageState,
    SupplierMessage,
    SupplierProjection,
)


class MessagingRepository:
    """Reads and writes the inbox, and the register it identifies senders against."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def message(self, message_id: int) -> SupplierMessage | None:
        """Return a message by id, or None."""
        return await self.session.get(SupplierMessage, message_id)

    async def with_external_id(self, external_id: str) -> SupplierMessage | None:
        """The message already registered under this id, or None."""
        result = await self.session.execute(
            select(SupplierMessage).where(SupplierMessage.external_id == external_id)
        )
        return result.scalars().first()

    async def add(self, message: SupplierMessage) -> SupplierMessage:
        """Store a message and give it its id."""
        self.session.add(message)
        await self.session.flush()
        return message

    async def list_messages(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        kind: MessageKind | None = None,
        state: MessageState | None = None,
        supplier_name: str | None = None,
    ) -> list[SupplierMessage]:
        """A page of messages, newest first."""
        statement = self._filtered(select(SupplierMessage), kind, state, supplier_name)
        result = await self.session.execute(
            statement.order_by(SupplierMessage.received_at.desc(), SupplierMessage.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_messages(
        self,
        *,
        kind: MessageKind | None = None,
        state: MessageState | None = None,
        supplier_name: str | None = None,
    ) -> int:
        """How many messages match the same filters as the listing."""
        statement = self._filtered(
            select(func.count()).select_from(SupplierMessage), kind, state, supplier_name
        )
        result = await self.session.execute(statement)
        return int(result.scalar_one())

    @staticmethod
    def _filtered(
        statement: Select[Any],
        kind: MessageKind | None,
        state: MessageState | None,
        supplier_name: str | None,
    ) -> Select[Any]:
        """The filters the listing and its count share (RF-26 of 007)."""
        if kind is not None:
            statement = statement.where(SupplierMessage.kind == kind)
        if state is not None:
            statement = statement.where(SupplierMessage.state == state)
        if supplier_name is not None:
            statement = statement.where(SupplierMessage.supplier_name == supplier_name)
        return statement

    async def pending_messages(self) -> list[SupplierMessage]:
        """Everything still waiting, for the count and the daily digest."""
        result = await self.session.execute(
            select(SupplierMessage)
            .where(SupplierMessage.state == MessageState.PENDING)
            .order_by(SupplierMessage.received_at)
        )
        return list(result.scalars().all())

    async def suppliers(self) -> list[SupplierProjection]:
        """The register, as this module keeps it."""
        result = await self.session.execute(select(SupplierProjection))
        return list(result.scalars().all())

    async def put_supplier(self, *, legal_name: str, name_key: str) -> None:
        """Record a supplier of the register in this module's projection."""
        row = await self.session.get(SupplierProjection, legal_name)
        if row is None:
            self.session.add(SupplierProjection(legal_name=legal_name, name_key=name_key))
        else:
            row.name_key = name_key
        await self.session.flush()
