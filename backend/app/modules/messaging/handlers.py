"""What `messaging` does when something happens elsewhere.

Two subscriptions, and one of them is the whole reason this module can identify
a sender without importing anybody: the register of suppliers arrives as an
event, and this module keeps its own copy of it.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.messaging.service import MessagingService
from app.shared.events import (
    AlertDeliveryFailed,
    DailyDigestContribution,
    DailyDigestRequested,
    SupplierMessagesNormalized,
    SuppliersNormalized,
    events,
)

# How many messages the digest names one by one. The rest are in the count: a
# summary that lists sixty-four lines is a screen, not a summary.
DIGEST_LINES = 5

logger = get_logger(__name__)


@events.subscribe(SuppliersNormalized)
async def remember_register(event: SuppliersNormalized, session: AsyncSession) -> None:
    """Keep the register this module compares senders against (RF-23 of 007)."""
    await MessagingService(session).remember_suppliers(event.suppliers)


@events.subscribe(SupplierMessagesNormalized)
async def register_messages(event: SupplierMessagesNormalized, session: AsyncSession) -> None:
    """Bring the new messages of the inbox in, pending and classified."""
    await MessagingService(session).register_messages(
        messages=event.messages, first_run=event.first_run
    )


@events.subscribe(DailyDigestRequested)
async def contribute_to_the_digest(event: DailyDigestRequested, session: AsyncSession) -> None:
    """Say what is still unresolved in the inbox (RF-35, RF-40 of 007).

    A message already marked as resolved is not in it: the digest is about what
    is still waiting for somebody, and repeating what was dealt with is how a
    daily message becomes one nobody reads.
    """
    service = MessagingService(session)
    pending = await service.pending_messages()
    await events.publish(
        DailyDigestContribution(
            source="messages",
            pending=len(pending),
            lines=tuple(
                f"• {message.supplier_name or message.sender_text}: {message.subject}"
                for message in pending[:DIGEST_LINES]
            ),
        ),
        session,
    )
    del event


@events.subscribe(AlertDeliveryFailed)
async def record_a_failed_alert(event: AlertDeliveryFailed, session: AsyncSession) -> None:
    """An alert about a message did not get through, so the message says so (RF-38).

    The screen is where it belongs, and the reason is almost literal: the phone
    is exactly where the news did **not** arrive, so the only place left to tell
    somebody is the one they have to open anyway.

    An alert with no message behind it — the due-date ones of 005 — is announced
    all the same and recorded nowhere: there is nothing to write it on.
    """
    if event.message_id is None:
        return
    await MessagingService(session).record_alert_failure(event.message_id, event.reason)
