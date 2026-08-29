"""What `notifications` does when something happens elsewhere.

Two subscriptions, and both of them **queue and return**. A handler runs inside
the transaction of whoever published, and a call to a third-party HTTP service
has no business being inside the transaction that just recorded a failed
extraction (`GEN-09`).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.logging import get_logger
from app.modules.notifications import tasks
from app.modules.notifications.service import (
    invitation_message,
    recovered_message,
    recovery_message,
    stalled_message,
)
from app.shared.events import (
    PasswordResetRequested,
    PriceUpdateRecovered,
    PriceUpdateStalled,
    UserInvited,
    events,
)

logger = get_logger(__name__)


@events.subscribe(PriceUpdateStalled)
async def warn_the_owner(event: PriceUpdateStalled, _session: AsyncSession) -> None:
    """Two scheduled runs in a row went by without a successful update (RF-12)."""
    tasks.send_whatsapp.delay(
        stalled_message(
            consecutive_failures=event.consecutive_failures,
            last_success_at=event.last_success_at,
        )
    )
    logger.info("Stall alert queued", extra={"failures": event.consecutive_failures})


@events.subscribe(PriceUpdateRecovered)
async def tell_the_owner_it_is_back(event: PriceUpdateRecovered, _session: AsyncSession) -> None:
    """The update started working again."""
    tasks.send_whatsapp.delay(recovered_message(recovered_at=event.recovered_at))
    logger.info("Recovery notice queued")


@events.subscribe(UserInvited)
async def deliver_invitation(event: UserInvited, _session: AsyncSession) -> None:
    """Send somebody the link that lets them set their own password (RF-42, RF-52).

    Queues and returns, like every delivery here: the invitation travels to a
    third-party service, and the transaction that created the access cannot
    stay open waiting for it. A failure here is a visible failed job and the
    token stays valid, so the owner can send it again without regenerating
    anything.
    """
    link = f"{settings.FRONTEND_URL}/invitacion/{event.token}"
    tasks.send_access_link.delay(
        event.phone, invitation_message(name=event.name, link=link, reason=event.reason)
    )
    logger.info("Invitation queued", extra={"user_id": event.user_id, "reason": event.reason})


@events.subscribe(PasswordResetRequested)
async def deliver_recovery(event: PasswordResetRequested, _session: AsyncSession) -> None:
    """Send somebody the link that lets them set a new password (RF-38)."""
    link = f"{settings.FRONTEND_URL}/recuperar/{event.token}"
    tasks.send_access_link.delay(event.phone, recovery_message(name=event.name, link=link))
    logger.info("Recovery link queued", extra={"user_id": event.user_id})
