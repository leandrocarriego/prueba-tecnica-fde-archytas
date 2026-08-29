"""Notifications business logic: what the owner reads on their phone.

The wording is the whole domain of this module, so it lives here rather than in
the task. It is in Spanish because it is read by a person, like every other
user-facing string (Artículo VIII).
"""

from datetime import datetime

from app.logging import get_logger
from app.modules.notifications.client import Delivery, WhatsAppChannel

logger = get_logger(__name__)

NEVER = "todavía no hubo ninguna"


def _moment(value: datetime | None) -> str:
    """Say when something happened, in words the owner reads."""
    return NEVER if value is None else value.strftime("%d/%m/%Y %H:%M")


def invitation_message(*, name: str, link: str, reason: str) -> str:
    """The message that lets somebody set the password of their own access."""
    if reason == "REACTIVATION":
        opening = f"Hola {name}, tu acceso a Cordillera volvió a quedar activo."
    else:
        opening = f"Hola {name}, te damos acceso al sistema de Cordillera."
    return (
        f"{opening}\n\n"
        f"Entrá acá para poner tu clave: {link}\n\n"
        "El enlace sirve una sola vez y vence en 7 días. "
        "Nadie más que vos conoce tu clave."
    )


def recovery_message(*, name: str, link: str) -> str:
    """The message that lets somebody set a new password after forgetting theirs."""
    return (
        f"Hola {name}, pediste recuperar tu acceso a Cordillera.\n\n"
        f"Entrá acá para poner una clave nueva: {link}\n\n"
        "El enlace sirve una sola vez y vence en 1 hora. "
        "Si no lo pediste vos, avisale al dueño."
    )


def stalled_message(*, consecutive_failures: int, last_success_at: datetime | None) -> str:
    """The alert for an interrupted price update (RF-12)."""
    return (
        "⚠️ Cordillera: la actualización de precios dejó de funcionar.\n"
        f"Intentos fallidos seguidos: {consecutive_failures}.\n"
        f"Última actualización exitosa: {_moment(last_success_at)}.\n"
        "Los precios que muestra el sistema pueden estar desactualizados."
    )


def recovered_message(*, recovered_at: datetime) -> str:
    """The all-clear, so the owner does not have to ask."""
    return (
        "✅ Cordillera: la actualización de precios volvió a funcionar.\n"
        f"Se actualizó correctamente el {_moment(recovered_at)}."
    )


class NotificationService:
    """Delivers a message through the only channel there is."""

    def __init__(self, channel: WhatsAppChannel | None = None) -> None:
        self.channel = channel or WhatsAppChannel()

    async def notify_person(self, phone: str, message: str) -> Delivery:
        """Deliver one message to a given number.

        Same channel as the alerts, another recipient: an invitation and a
        recovery link go to the person they belong to, not to the owner.
        """
        return await self.channel.send(message, to=phone)

    async def notify_owner(self, message: str) -> Delivery:
        """Send the owner a message. A failure is reported, never raised here."""
        return await self.channel.send(message)
