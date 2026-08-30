"""What `notifications` does when something happens elsewhere.

Every subscription that delivers something **queues and returns**. A handler runs inside the
transaction of whoever published, and a call to a third-party HTTP service has
no business inside the transaction that just recorded a failed extraction, or
the one applying a price list (`GEN-09`).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.logging import get_logger
from app.modules.notifications import tasks
from app.modules.notifications.delivery import AlertRouter
from app.modules.notifications.models import AlertKind
from app.modules.notifications.repository import NotificationsRepository
from app.modules.notifications.service import (
    DIGEST_TIME_KEY,
    WINDOW_END_KEY,
    WINDOW_START_KEY,
    conflict_message,
    due_soon_message,
    invitation_message,
    message_due_message,
    payment_claim_message,
    recovered_message,
    recovery_message,
    stalled_message,
)
from app.shared.events import (
    BusinessParameterChanged,
    CorrectionConflicted,
    InvoiceDueSoon,
    PasswordResetRequested,
    PriceUpdateRecovered,
    PriceUpdateStalled,
    SupplierMessageReceived,
    UserDeactivated,
    UserInvited,
    UserReactivated,
    UserRegistered,
    UserRoleChanged,
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


@events.subscribe(CorrectionConflicted)
async def warn_about_a_contradicted_correction(
    event: CorrectionConflicted, _session: AsyncSession
) -> None:
    """The portal came back with something else on a corrected value (RF-29).

    Queued, like every delivery here, and for a sharper reason than usual: this
    fires while a price list is being applied. A gateway that is not answering
    must not roll back an update that worked — the conflict is already recorded
    on the correction itself, so the flag survives even if the message does not.
    """
    tasks.send_whatsapp.delay(
        conflict_message(
            field=event.field,
            original=event.original_value,
            corrected=event.corrected_value,
            incoming=event.incoming_value,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
        )
    )
    logger.info(
        "Correction conflict alert queued",
        extra={"correction_id": event.correction_id, "entity_id": event.entity_id},
    )


# --- The alerts of 005 and 007 -------------------------------------------
#
# Four more subscriptions, and the same rule as above: queue and return. What
# is different here is **when** they go out — an immediate alert whose cause
# happens outside the window the owner allows is delayed until the window
# opens, never dropped (RF-42 of 007).


@events.subscribe(UserRegistered)
async def remember_recipient(event: UserRegistered, session: AsyncSession) -> None:
    """Keep somebody an alert can reach (RF-44 of 007)."""
    await NotificationsRepository(session).put_recipient(
        user_id=event.user_id, role=event.role, phone=event.phone
    )


@events.subscribe(UserDeactivated)
async def stop_alerting(event: UserDeactivated, session: AsyncSession) -> None:
    """Somebody lost their access, so their alerts stop (RF-45 of 007)."""
    await NotificationsRepository(session).set_active(event.user_id, active=False)


@events.subscribe(UserReactivated)
async def resume_alerting(event: UserReactivated, session: AsyncSession) -> None:
    """Their access came back, and so do their alerts."""
    await NotificationsRepository(session).set_active(event.user_id, active=True)


@events.subscribe(UserRoleChanged)
async def follow_the_role(event: UserRoleChanged, session: AsyncSession) -> None:
    """Which alerts are theirs changed with their role."""
    await NotificationsRepository(session).set_role(event.user_id, event.role)


@events.subscribe(BusinessParameterChanged)
async def remember_window(event: BusinessParameterChanged, session: AsyncSession) -> None:
    """Keep the window and the digest hour this module obeys (RF-36, RF-43)."""
    if event.key not in {WINDOW_START_KEY, WINDOW_END_KEY, DIGEST_TIME_KEY}:
        return
    await AlertRouter(session).remember(event.key, event.value)


@events.subscribe(InvoiceDueSoon)
async def warn_about_a_due_invoice(event: InvoiceDueSoon, session: AsyncSession) -> None:
    """An invoice is about to fall due with no receipt (RF-38 of 005)."""
    await _deliver(
        session,
        AlertKind.DUE_SOON,
        due_soon_message(
            number=event.number,
            supplier=event.supplier_name,
            due_on=event.due_on.isoformat(),
            days_ahead=event.days_ahead,
        ),
    )


@events.subscribe(SupplierMessageReceived)
async def warn_about_a_message(event: SupplierMessageReceived, session: AsyncSession) -> None:
    """A claim or a due-date notice landed in the inbox (RF-33, RF-34 of 007)."""
    kind = AlertKind.PAYMENT_CLAIM if event.kind == "PAYMENT_CLAIM" else AlertKind.DUE_SOON
    build = payment_claim_message if kind is AlertKind.PAYMENT_CLAIM else message_due_message
    await _deliver(
        session,
        kind,
        build(supplier=event.supplier_name, subject=event.subject, body=event.body),
    )


async def _deliver(session: AsyncSession, kind: AlertKind, message: str) -> None:
    """Queue one alert per recipient, waiting for the window if it is closed.

    The delay is what RF-42 asks for and it is applied by the broker rather than
    by a process holding the message: something that has to go out at eight in
    the morning must not depend on a worker being alive at midnight.
    """
    router = AlertRouter(session)
    countdown = await router.delay_until_window()
    phones = await router.phones_for(kind)
    for phone in phones:
        tasks.send_alert.apply_async(args=[phone, message], countdown=countdown)
    logger.info(
        "Alert queued",
        extra={"kind": kind.value, "recipients": len(phones), "countdown": countdown},
    )
