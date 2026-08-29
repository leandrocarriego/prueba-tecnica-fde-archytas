"""Sending, out of the way of whoever asked for it.

The send is a Celery task and not a handler body on purpose: Evolution API is a
free third-party service, and an alert that cannot be delivered must not abort
the extraction that triggered it. Its failure ends up as a failed job — visible
— instead of rolling back a price update that actually worked.
"""

from typing import Any

from celery import Task

from app.logging import get_logger
from app.modules.notifications.client import NOT_CONFIGURED
from app.modules.notifications.service import NotificationService
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
