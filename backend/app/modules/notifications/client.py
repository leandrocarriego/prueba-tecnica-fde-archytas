"""The WhatsApp channel, through Evolution API.

Evolution API is a free third-party service, so the rule around it is that a
message that cannot be sent is never allowed to take anything else down with
it: the caller is a Celery task, the failure is logged and the run is what
records it. The prices screen says the same thing without asking anybody
(RF-11), which is why the alert is allowed to be best-effort.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.config import settings
from app.logging import get_logger

logger = get_logger(__name__)

NOT_CONFIGURED = "WhatsApp is not configured; the alert was only logged"


@dataclass(frozen=True, slots=True)
class Delivery:
    """What happened to one message."""

    sent: bool
    detail: str


class WhatsAppChannel:
    """Sends a plain text message to one number."""

    def __init__(self) -> None:
        self.base_url = settings.EVOLUTION_API_URL.rstrip("/")
        self.instance = settings.EVOLUTION_INSTANCE
        self.api_key = settings.EVOLUTION_API_KEY
        self.recipient = settings.NOTIFICATIONS_WHATSAPP_TO

    @property
    def is_configured(self) -> bool:
        """Whether there is anywhere to send to."""
        return bool(self.base_url and self.instance and self.api_key and self.recipient)

    async def send(self, message: str, *, to: str | None = None) -> Delivery:
        """Deliver one message, or write it down instead.

        The disk emitter is not a stub for tests: it is what a development
        machine uses so that trying the invitation flow does not send a real
        WhatsApp to a real person. It is on by default, and turning it off is
        an explicit decision made in the environment.
        """
        if settings.NOTIFICATIONS_TO_DISK:
            return self._write_to_disk(to or self.recipient, message)
        return await self._deliver(message, to=to)

    def _write_to_disk(self, recipient: str, message: str) -> Delivery:
        """Append the message to the outbox, and say it was delivered."""
        outbox = Path(settings.NOTIFICATIONS_OUTBOX_DIR)
        outbox.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        path = outbox / f"{stamp}-{recipient.strip('+') or 'sin-destino'}.txt"
        path.write_text(f"Para: {recipient}\n\n{message}\n", encoding="utf-8")
        logger.info("Message written to the outbox", extra={"path": str(path)})
        return Delivery(sent=True, detail=f"escrito en {path}")

    async def _deliver(self, message: str, *, to: str | None = None) -> Delivery:
        """Send a message, and say plainly whether it left."""
        if not self.is_configured:
            logger.warning(NOT_CONFIGURED)
            return Delivery(sent=False, detail=NOT_CONFIGURED)

        url = f"{self.base_url}/message/sendText/{self.instance}"
        try:
            async with httpx.AsyncClient(timeout=settings.EVOLUTION_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    url,
                    headers={"apikey": self.api_key, "Content-Type": "application/json"},
                    json={"number": to or self.recipient, "text": message},
                )
                response.raise_for_status()
        except httpx.HTTPError as error:
            # The exception is logged here and not propagated with its detail:
            # it quotes the URL, and the URL carries the instance.
            logger.exception("WhatsApp message could not be sent")
            return Delivery(sent=False, detail=type(error).__name__)

        logger.info("WhatsApp message sent")
        return Delivery(sent=True, detail="ok")
