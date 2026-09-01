"""Sending, out of the way of whoever asked for it.

The send is a Celery task and not a handler body on purpose: Evolution API is a
free third-party service, and an alert that cannot be delivered must not abort
the extraction that triggered it. Its failure ends up as a failed job — visible
— instead of rolling back a price update that actually worked.
"""

from datetime import UTC, datetime
from typing import Any

from celery import Task
from celery.schedules import crontab
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionFactory
from app.logging import get_logger
from app.modules.notifications.client import NOT_CONFIGURED
from app.modules.notifications.delivery import AlertRouter
from app.modules.notifications.models import AlertKind
from app.modules.notifications.service import (
    DIGEST_TIME_KEY,
    DigestPart,
    NotificationService,
    daily_digest_message,
)
from app.shared.events import (
    AlertDeliveryFailed,
    DailyDigestContribution,
    DailyDigestRequested,
    events,
)
from app.shared.time import BUSINESS_TIME_ZONE
from app.worker.bridge import async_task
from app.worker.celery_app import celery_app

logger = get_logger(__name__)

MAX_RETRIES = 2
RETRY_COUNTDOWN_SECONDS = 60


@celery_app.task(name="notifications.send_whatsapp", bind=True, max_retries=MAX_RETRIES)
@async_task
async def send_whatsapp(self: Task, message: str) -> dict[str, Any]:
    """Deliver one message to the owner."""
    delivery = await NotificationService().notify_owner(message)
    # A channel that is not configured is not a transient failure: retrying it
    # would only fill the queue. Anything else is worth one more attempt.
    if not delivery.sent and delivery.detail != NOT_CONFIGURED:
        attempts = int(getattr(self.request, "retries", 0) or 0)
        if attempts < MAX_RETRIES:
            raise self.retry(countdown=RETRY_COUNTDOWN_SECONDS)
    return {"sent": delivery.sent, "detail": delivery.detail}


@celery_app.task(name="notifications.send_access_link", bind=True, max_retries=MAX_RETRIES)
@async_task
async def send_access_link(self: Task, phone: str, message: str) -> dict[str, Any]:
    """Deliver an invitation or a recovery link to the person it belongs to.

    Enqueued rather than sent inside the handler, like every other delivery
    here: the publisher's transaction must not stay open across a call to a
    third-party service. If this fails, the token stays valid and the owner can
    send the invitation again — nothing has to be regenerated.
    """
    delivery = await NotificationService().notify_person(phone, message)
    if not delivery.sent and delivery.detail != NOT_CONFIGURED:
        attempts = int(getattr(self.request, "retries", 0) or 0)
        if attempts < MAX_RETRIES:
            raise self.retry(countdown=RETRY_COUNTDOWN_SECONDS)
    return {"sent": delivery.sent, "detail": delivery.detail}


@celery_app.task(name="notifications.send_alert", bind=True, max_retries=MAX_RETRIES)
@async_task
async def send_alert(
    self: Task, phone: str, message: str, kind: str = "", message_id: int | None = None
) -> dict[str, Any]:
    """Deliver one alert to one person's own number (RF-44 of 007).

    The same channel as everything else here and a different name on purpose:
    an alert is not an access link, it carries no credential, and reading a log
    line should say which of the two went out.

    **A delivery that does not happen says so** (RF-38). The screen already drew
    the notice and nothing ever wrote it: the failure ended as a log line and a
    failed job, and the one place the news did not arrive — the phone — was also
    the one place nobody could tell. So the task publishes the fact and
    `messaging` records it; this module may not call that one (Artículo IV).

    **Only once the retries are spent.** Publishing on the first attempt would
    mark as failed an alert the second attempt delivers, and a screen that says
    something failed when it did not is worse than one that says nothing.
    """
    delivery = await NotificationService().notify_person(phone, message)
    if not delivery.sent and delivery.detail != NOT_CONFIGURED:
        attempts = int(getattr(self.request, "retries", 0) or 0)
        if attempts < MAX_RETRIES:
            raise self.retry(countdown=RETRY_COUNTDOWN_SECONDS)
    if not delivery.sent:
        await _report_delivery_failure(kind, delivery.detail, message_id)
    return {"sent": delivery.sent, "detail": delivery.detail}


async def _report_delivery_failure(kind: str, reason: str | None, message_id: int | None) -> None:
    """Announce that an alert did not get through (RF-38 of 007).

    A session of its own, like `daily_digest` opens one: this runs in the worker
    and there is no request behind it.
    """
    async with SessionFactory() as session:
        await events.publish(
            AlertDeliveryFailed(
                kind=kind, reason=reason or "No se pudo entregar", message_id=message_id
            ),
            session,
        )
        await session.commit()
    logger.warning(
        "Alert delivery failed", extra={"kind": kind, "message_id": message_id, "reason": reason}
    )


@celery_app.task(name="notifications.daily_digest")
@async_task
async def daily_digest() -> dict[str, Any]:
    """Send the summary of what is still open, once a day (RF-35, RF-36 of 007).

    **The digest is assembled by asking.** This task publishes one question —
    "what goes in today's digest?" — and every module that has something to say
    answers with its own count and its own lines. Neither `messaging` nor
    `purchases` is imported here, and neither of them knows a digest exists: it
    is the same mechanism the rest of the platform uses to cross a boundary.

    It goes out even when there is nothing pending: "nothing is waiting" and
    "the digest stopped working" look identical from a phone otherwise.

    Beat wakes this every hour and the task decides whether this is the hour the
    owner chose (RF-36). Reading the parameter here rather than writing it into
    the schedule is what makes a change to it apply from the next day instead of
    from a redeploy.
    """
    collected: list[DailyDigestContribution] = []

    async def collect(event: DailyDigestContribution, _session: AsyncSession) -> None:
        collected.append(event)

    # Subscribed for the length of this run rather than at import time: the
    # accumulator is this task's, and a module-level handler would be shared by
    # every digest the process ever sends.
    events.subscribe(DailyDigestContribution)(collect)
    try:
        async with SessionFactory() as session:
            if not await _is_the_hour(session):
                return {"sent": False, "reason": "not the configured hour"}
            await events.publish(DailyDigestRequested(on_date=datetime.now(UTC).date()), session)
            # Cada contribución se pasa entera, con su `source`: quién la
            # contó es lo que deja escribirla bajo su propio título y con el
            # enlace de su pantalla. Antes se sumaban dos `source` por nombre y
            # las líneas de todos se mezclaban en una sola lista, así que el
            # resumen no podía decir de qué era cada renglón — y un módulo que
            # contribuyera algo nuevo se perdía sin que nada lo notara.
            parts = [DigestPart(part.source, part.pending, part.lines) for part in collected]
            phones = await AlertRouter(session).phones_for(AlertKind.DAILY_DIGEST)
            await session.commit()
    finally:
        events.unsubscribe(DailyDigestContribution, collect)

    message = daily_digest_message(parts)
    for phone in phones:
        send_alert.delay(phone, message)

    counts = {part.source: part.total for part in parts}
    logger.info("Daily digest sent", extra={"counts": counts, "recipients": len(phones)})
    return {"counts": counts, "recipients": len(phones)}


async def _is_the_hour(session: AsyncSession) -> bool:
    """Whether now is the hour the owner set for the digest (RF-36 of 007)."""
    router = AlertRouter(session)
    configured = str(await router.setting(DIGEST_TIME_KEY))
    now = datetime.now(UTC).astimezone(BUSINESS_TIME_ZONE)
    return now.strftime("%H") == configured.partition(":")[0].zfill(2)


celery_app.conf.beat_schedule["daily-digest"] = {
    "task": "notifications.daily_digest",
    # Every hour, and the task itself decides whether this is the hour the owner
    # chose: reading the parameter here is what makes a change to it apply from
    # the next day instead of from a redeploy, exactly like the price update.
    "schedule": crontab(minute=0),
}
