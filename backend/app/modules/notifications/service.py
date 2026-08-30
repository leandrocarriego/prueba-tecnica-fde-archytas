"""Notifications business logic: what the owner reads on their phone.

The wording is the whole domain of this module, so it lives here rather than in
the task. It is in Spanish because it is read by a person, like every other
user-facing string (Artículo VIII).
"""

from datetime import datetime
from typing import NamedTuple

from app.config import settings
from app.logging import get_logger
from app.modules.notifications.client import Delivery, WhatsAppChannel

logger = get_logger(__name__)

NEVER = "todavía no hubo ninguna"

# The field names travel as code — they are another module's vocabulary — and
# the owner reads Spanish. An unknown field falls back to its own name rather
# than to nothing: a message missing a word still says what happened.
FIELD_NAMES: dict[str, str] = {
    "price": "precio",
    "currency": "moneda",
    "description": "descripción",
}

UNNAMED = "Dato"


class Entity(NamedTuple):
    """How the owner names a datum, and the screen where they look at it."""

    name: str
    screen: str


# What the owner calls the thing a correction lives on, and where they go to
# see it. The entity type travels as code — it is how the rest of the platform
# refers to a row, not how a person does — so name and screen are kept in one
# table: an entity named but with nowhere to go, or the reverse, is the kind of
# gap that only shows up once the alert is already on somebody's phone.
#
# Both catalog entities are the same product to whoever reads the alert: nobody
# outside the system thinks of a price row as a thing of its own.
ENTITIES: dict[str, Entity] = {
    "catalog.product_price": Entity("Producto", "precios"),
    "catalog.product": Entity("Producto", "precios"),
}


def _moment(value: datetime | None) -> str:
    """Say when something happened, in words the owner reads."""
    return NEVER if value is None else value.strftime("%d/%m/%Y %H:%M")


def _entity(entity_type: str | None, entity_id: str | None) -> Entity | None:
    """The entity an alert is about, or nothing when there is no reference."""
    return ENTITIES.get(entity_type or "") if entity_id else None


def _datum(entity_type: str | None, entity_id: str | None) -> str:
    """Name the datum an alert is about, as its own line, or say nothing.

    Nothing when there is no reference to give: naming one datum «#None» reads
    like a bug and tells the owner less than staying quiet. An entity type
    nobody named falls back to a word and never to its own code: a namespace
    with a dot in it is not something a person reads (`GEN-07`).
    """
    if not entity_id:
        return ""
    entity = _entity(entity_type, entity_id)
    return f"{entity.name if entity else UNNAMED} #{entity_id}.\n"


def _where_to_look(entity_type: str | None, entity_id: str | None) -> str:
    """Point at the screen that shows the datum, with a link when there is one.

    The owner reads this at night, on a phone, away from the system, and the id
    the alert carries is internal — no screen displays it. Naming «the screen
    of the datum» is not a way in; the address of that screen is. It is built
    here, out of the entity type, the same way the invitation and the recovery
    messages carry the link that makes them actionable.
    """
    entity = _entity(entity_type, entity_id)
    if entity is None:
        return "Revisala en la pantalla del dato."
    return f"Revisala acá: {settings.FRONTEND_URL}/{entity.screen}/{entity_id}"


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


def conflict_message(
    *,
    field: str,
    original: object,
    corrected: object,
    incoming: object,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> str:
    """The alert when the portal contradicts a correction somebody made (RF-29).

    It says which datum disagrees, what the three values are, and stops there.
    The system does not pick one — the spec is explicit that it flags, warns,
    and waits for a person.

    The datum is named first because the owner reads this at night, away from
    any screen: two conflicts in the same nightly run carry the same field and
    can carry the same numbers, and an alert nobody can tell apart from the
    previous one is an alert nobody can act on. The last line closes the same
    gap from the other end — knowing which datum disagrees is worth little at
    3 AM without a way to reach it.
    """
    return (
        "⚠️ Cordillera: el portal informó algo distinto sobre un dato corregido a mano.\n"
        f"{_datum(entity_type, entity_id)}"
        f"Campo: {FIELD_NAMES.get(field, field)}.\n"
        f"El portal había informado: {original}.\n"
        f"Quedó corregido a mano en: {corrected}.\n"
        f"Ahora el portal informa: {incoming}.\n"
        "La corrección sigue en pie.\n"
        f"{_where_to_look(entity_type, entity_id)}"
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
