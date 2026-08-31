"""Messaging business logic: read the inbox, say who wrote and who owes an answer.

Two things are decided here and nowhere else.

**What a message is about.** The portal writes the kind in words, and those
words are mapped to the three kinds the business recognises. A wording nobody
mapped is **not** discarded and not guessed at: the message is shown as
unclassified (RF-25), which is Artículo II at its smallest.

**Who wrote it.** The sender is compared against the register of suppliers,
through this module's own projection of it. A sender that does not resolve with
certainty leaves the message visible and marked as unidentified (RF-24) — never
attributed to the nearest name.
"""

from datetime import UTC, datetime

from rapidfuzz import fuzz, process
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.messaging.models import (
    MessageKind,
    MessageState,
    SupplierMessage,
)
from app.modules.messaging.repository import MessagingRepository
from app.modules.messaging.schemas import MessageList, MessageRead
from app.shared.errors import ConflictError, NotFoundError
from app.shared.events import NormalizedMessage, NormalizedSupplier, SupplierMessageReceived, events
from app.shared.text import normalize, normalize_entity_name

logger = get_logger(__name__)

# What the portal writes in its `Tipo` column, mapped to what the business
# calls it. Matched on the normalised text, so accents and case do not matter;
# anything not here stays unclassified rather than being forced into a bucket.
KINDS: dict[str, MessageKind] = {
    "reclamo de pago": MessageKind.PAYMENT_CLAIM,
    "reclamo": MessageKind.PAYMENT_CLAIM,
    "vencimiento proximo": MessageKind.DUE_SOON,
    "vencimiento": MessageKind.DUE_SOON,
    "stock bajo": MessageKind.LOW_STOCK,
    "stock": MessageKind.LOW_STOCK,
}

# The kinds somebody is woken up for the moment they arrive (RF-33, RF-34).
URGENT = frozenset({MessageKind.PAYMENT_CLAIM, MessageKind.DUE_SOON})

# How close a sender's name has to be to a supplier of the register before it
# counts as identified. High on purpose: a message attributed to the wrong
# supplier is worse than one that says plainly it could not be attributed.
SENDER_THRESHOLD = 88

NO_SUCH_MESSAGE = "No encontramos ese mensaje"
ALREADY_RESOLVED = "El mensaje ya está resuelto"


class MessagingService:
    """Registers the messages of the inbox and keeps their state and their owner."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.messaging = MessagingRepository(session)

    async def remember_suppliers(self, suppliers: tuple[NormalizedSupplier, ...]) -> None:
        """Keep the register this module identifies senders against."""
        for card in suppliers:
            await self.messaging.put_supplier(
                legal_name=card.legal_name, name_key=normalize_entity_name(card.legal_name)
            )

    async def register_messages(
        self, *, messages: tuple[NormalizedMessage, ...], first_run: bool
    ) -> int:
        """Bring the new messages of the inbox in, pending (RF-27 of 007).

        On the **first** reading nobody is woken up: what the inbox already held
        when the platform started is registered as pending and announced to
        nobody (RF-47). Waking three people for sixty-four messages that were
        already sitting there is not an alert, it is noise.
        """
        registered = 0
        for row in messages:
            if await self.messaging.with_external_id(row.external_id) is not None:
                continue
            supplier = await self._sender_of(row.sender_text)
            message = await self.messaging.add(
                SupplierMessage(
                    external_id=row.external_id,
                    received_at=row.received_at,
                    sender_text=row.sender_text,
                    supplier_name=supplier,
                    kind=self._kind_of(row.kind_text),
                    kind_text=row.kind_text,
                    subject=row.subject,
                    body=row.body,
                    state=MessageState.PENDING,
                )
            )
            registered += 1
            if not first_run and message.kind in URGENT:
                await events.publish(
                    SupplierMessageReceived(
                        message_id=message.id,
                        kind=message.kind.value,
                        supplier_name=supplier or row.sender_text,
                        subject=message.subject,
                        body=message.body or "",
                        received_at=message.received_at,
                    ),
                    self.session,
                )
                message.alerted_at = datetime.now(UTC)
        await self.session.flush()
        logger.info("Inbox registered", extra={"messages": registered, "first_run": first_run})
        return registered

    @staticmethod
    def _kind_of(kind_text: str) -> MessageKind:
        """What the portal's wording means, or that it means nothing known."""
        return KINDS.get(normalize(kind_text or ""), MessageKind.UNCLASSIFIED)

    async def _sender_of(self, sender_text: str) -> str | None:
        """Which supplier of the register wrote this, or nothing (RF-23, RF-24)."""
        cleaned = (sender_text or "").strip()
        if not cleaned:
            return None
        register = {row.legal_name: row.name_key for row in await self.messaging.suppliers()}
        if not register:
            return None
        found = process.extractOne(
            normalize_entity_name(cleaned), register, scorer=fuzz.token_sort_ratio
        )
        if found is None or found[1] < SENDER_THRESHOLD:
            return None
        return str(found[2])

    # --- Reading -----------------------------------------------------------

    async def list_messages(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        kind: MessageKind | None = None,
        state: MessageState | None = None,
        supplier_name: str | None = None,
    ) -> MessageList:
        """The messages screen, with its filters and its pending count."""
        messages = await self.messaging.list_messages(
            skip=skip, limit=limit, kind=kind, state=state, supplier_name=supplier_name
        )
        return MessageList(
            items=[self._read(message) for message in messages],
            total=await self.messaging.count_messages(
                kind=kind, state=state, supplier_name=supplier_name
            ),
            pending=await self.messaging.count_messages(state=MessageState.PENDING),
            skip=skip,
            limit=limit,
        )

    async def senders(self) -> list[str]:
        """The suppliers a message can be filtered by (RF-26 of 007).

        This module's **own** projection of the register, not `purchases`'
        table: the screen filters by exact name and these are exactly the names
        `supplier_name` can hold, so offering any other list would offer filters
        that match nothing.
        """
        return sorted(supplier.legal_name for supplier in await self.messaging.suppliers())

    async def count_pending(self) -> int:
        """How many messages are still waiting for somebody (RF-31)."""
        return await self.messaging.count_messages(state=MessageState.PENDING)

    async def pending_messages(self) -> list[MessageRead]:
        """Everything still pending, for the daily digest (RF-35, RF-40)."""
        return [self._read(message) for message in await self.messaging.pending_messages()]

    @staticmethod
    def _read(message: SupplierMessage) -> MessageRead:
        """Render a message, saying out loud when its sender is unknown."""
        read = MessageRead.model_validate(message)
        read.sender_unidentified = message.supplier_name is None
        return read

    # --- Deciding ----------------------------------------------------------

    async def resolve(self, message_id: int, *, actor_user_id: int) -> MessageRead:
        """Mark a message as dealt with, with who and when (RF-28, RF-29)."""
        message = await self._require(message_id)
        if message.state is MessageState.RESOLVED:
            raise ConflictError(ALREADY_RESOLVED, details={"message_id": message_id})
        message.state = MessageState.RESOLVED
        message.resolved_by_user_id = actor_user_id
        message.resolved_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.commit()
        return self._read(message)

    async def assign(self, message_id: int, *, assignee_user_id: int | None) -> MessageRead:
        """Put somebody's name on a message (RF-30 of 007)."""
        message = await self._require(message_id)
        message.assignee_user_id = assignee_user_id
        await self.session.flush()
        await self.session.commit()
        return self._read(message)

    async def annotate(self, message_id: int, *, note: str) -> MessageRead:
        """Write a note on a message (RF-32 of 007)."""
        message = await self._require(message_id)
        message.note = note
        await self.session.flush()
        await self.session.commit()
        return self._read(message)

    async def record_alert_failure(self, message_id: int, reason: str) -> None:
        """Say on the screen that an alert about this message did not get through.

        RF-38: an alert that failed is not allowed to fail silently. It is the
        screen that says so, because the phone is exactly where the news did not
        arrive.
        """
        message = await self.messaging.message(message_id)
        if message is None:
            return
        message.alert_failure = reason
        await self.session.flush()

    async def _require(self, message_id: int) -> SupplierMessage:
        """Return the message, or say plainly that it is not there."""
        message = await self.messaging.message(message_id)
        if message is None:
            raise NotFoundError(NO_SUCH_MESSAGE, details={"message_id": message_id})
        return message
