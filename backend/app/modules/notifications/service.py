"""Notifications business logic: what the owner reads on their phone.

The wording is the whole domain of this module, so it lives here rather than in
the task. It is in Spanish because it is read by a person, like every other
user-facing string (Artículo VIII).
"""

from datetime import datetime
from typing import NamedTuple
from urllib.parse import urlencode

from app.config import settings
from app.logging import get_logger
from app.modules.notifications.client import Delivery, WhatsAppChannel
from app.modules.notifications.models import AlertKind

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


# --- Dónde se mira cada cosa que un aviso nombra --------------------------
#
# La **dirección**, no el nombre de la pantalla. El dueño lee esto de noche, en
# el teléfono y lejos del sistema: «miralo en la pantalla de facturas» no es una
# manera de entrar, y `https://…/facturas/312` sí. Es la misma razón por la que
# la invitación y la recuperación llevan su enlace, y por la que
# `_where_to_look` ya lo hacía para el dato de una corrección; lo que faltaba
# era que lo llevaran los cuatro avisos que se mandan solos.
INVOICES_SCREEN = "facturas"
INBOX_SCREEN = "mensajes"
ORDERS_SCREEN = "ordenes"
PRICE_LOG_SCREEN = "precios/historial"


def _link(screen: str, entity_id: object = None, **query: str) -> str:
    """La dirección de una pantalla, o la del dato adentro de ella.

    `query` es para las pantallas que no tienen una ruta por fila y sí un filtro
    que las recorta: la bandeja del portal no direcciona un mensaje, pero
    `?proveedor=…` deja al dueño frente a los de ese proveedor y no frente a
    cuarenta. Un filtro es peor que una ruta y mucho mejor que un listado
    entero.
    """
    address = f"{settings.FRONTEND_URL}/{screen}"
    if entity_id is not None:
        address = f"{address}/{entity_id}"
    if query:
        address = f"{address}?{urlencode(query)}"
    return address


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
        "Los precios que muestra el sistema pueden estar desactualizados.\n"
        f"Mirá qué pasó en cada corrida: {_link(PRICE_LOG_SCREEN)}"
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


# --- The alerts of 005 and 007 -------------------------------------------

# Who receives each kind of alert while nobody has said otherwise. These are the
# values the client signed: the claims and the due dates go to whoever handles
# purchasing, and the daily digest to the owner.
DEFAULT_ROUTES: dict[str, str] = {
    "PAYMENT_CLAIM": "PURCHASING",
    "DUE_SOON": "PURCHASING",
    "DAILY_DIGEST": "OWNER",
}

# The window inside which an immediate alert is delivered (RF-43 of 007). What
# happens outside it is not dropped: it waits for the window to open (RF-42).
WINDOW_START_KEY = "alerts.window_start"
WINDOW_END_KEY = "alerts.window_end"
DIGEST_TIME_KEY = "daily_digest.time"

# Monday to Friday, as signed. Saturday is 5 in `weekday()`.
WORKING_DAYS = frozenset({0, 1, 2, 3, 4})


def due_soon_message(
    *,
    number: str,
    supplier: str,
    due_on: object,
    days_ahead: int,
    invoice_id: int | None = None,
) -> str:
    """The alert for an invoice that is about to fall due with no receipt (RF-38).

    El enlace lleva a **esa** factura y no a la lista: el aviso dice que todavía
    se le puede emitir el recibo, y el enlace es lo que hace que eso sea una
    acción y no una tarea que hay que ir a buscar entre cuatrocientas filas.

    `invoice_id` es opcional porque un aviso sin referencia sigue siendo un
    aviso: sin él se manda el mismo mensaje, sin la línea del enlace. Prometer
    una dirección que apunte a `/facturas/None` sería peor que no prometerla.
    """
    when = "hoy" if days_ahead == 0 else f"en {days_ahead} día{'s' if days_ahead != 1 else ''}"
    where = "" if invoice_id is None else f"\nEmitilo acá: {_link(INVOICES_SCREEN, invoice_id)}"
    return (
        "📄 Cordillera: una factura vence sin recibo de recepción.\n"
        f"Factura {number}, de {supplier}.\n"
        f"Vence {when} ({due_on}).\n"
        f"Todavía se le puede emitir el recibo.{where}"
    )


def _inbox_of(supplier: str) -> str:
    """La bandeja recortada a los mensajes de un proveedor.

    La pantalla filtra por nombre —es lo que `RF-26` de la 007 firmó—, así que
    el nombre que ya viaja en el aviso alcanza para dejar al dueño frente a los
    mensajes de ese proveedor. No hay ruta por mensaje; el día que la haya, esto
    es una línea.
    """
    return _link(INBOX_SCREEN, proveedor=supplier)


def payment_claim_message(*, supplier: str, subject: str, body: str) -> str:
    """The alert for a supplier claiming a payment (RF-33 of 007)."""
    return (
        f"📣 Cordillera: un proveedor reclama un pago.\n"
        f"{supplier}: {subject}\n"
        f"{body[:280]}\n"
        f"Miralo en la bandeja: {_inbox_of(supplier)}"
    ).strip()


def message_due_message(*, supplier: str, subject: str, body: str) -> str:
    """The alert for a message announcing something about to fall due (RF-34)."""
    return (
        "⏰ Cordillera: aviso de vencimiento en la bandeja del portal.\n"
        f"{supplier}: {subject}\n"
        f"{body[:280]}\n"
        f"Miralo en la bandeja: {_inbox_of(supplier)}"
    ).strip()


def daily_digest_message(*, pending_messages: int, stalled_orders: int, lines: list[str]) -> str:
    """The summary of what is still open, once a day (RF-35 of 007).

    A summary of nothing is still worth sending: it is the difference between
    "there is nothing pending" and "the digest stopped working", and only one of
    those is good news.
    """
    header = (
        "🗒️ Cordillera — resumen del día\n"
        f"Mensajes sin resolver: {pending_messages}.\n"
        f"Órdenes estancadas: {stalled_orders}."
    )
    if not lines and pending_messages == 0 and stalled_orders == 0:
        # Sin enlace, y a propósito: un día sin nada pendiente no tiene adónde
        # mandar a nadie. Un enlace acá enseñaría que el enlace no significa
        # «hay algo para hacer», que es exactamente lo que significa en los
        # otros tres avisos.
        return f"{header}\nNo hay nada pendiente."
    # Una dirección por cuenta, y sólo la de las cuentas que no dan cero: el
    # resumen cuenta dos cosas que se resuelven en dos pantallas distintas, y
    # un enlace único tendría que apuntar a una de las dos o a ninguna.
    where = [
        line
        for line, pending in (
            (f"Mensajes: {_link(INBOX_SCREEN)}", pending_messages),
            (f"Órdenes: {_link(ORDERS_SCREEN)}", stalled_orders),
        )
        if pending
    ]
    return "\n".join([header, "", *lines[:10], *(["", *where] if where else [])])


# --- Probar un aviso antes de que haga falta ------------------------------

# La franja que encabeza un envío de prueba.
#
# Va **adentro del mensaje** y no en un metadato: lo que llega al teléfono es un
# WhatsApp suelto, sin pantalla alrededor que lo califique, y un aviso de prueba
# que se lee igual que uno de verdad hace que alguien salga a resolver una
# factura que no existe. Es la primera línea porque en la notificación del
# celular se ve el principio y no el final.
TEST_BANNER = "🧪 PRUEBA — la pidió alguien desde Configuración. No hay nada que resolver."

# Los datos con los que se arma cada ejemplo. Inventados y visiblemente
# inventados: un número de factura que no puede existir y un proveedor que se
# llama como lo que es.
SAMPLE_SUPPLIER = "Proveedor de Prueba S.A."
SAMPLE_INVOICE = "FC-0000-PRUEBA"


def test_message(kind: str) -> str:
    """Un ejemplo de un aviso, dicho con las mismas palabras que el de verdad.

    **Reusa el redactor real de cada aviso en vez de escribir un texto aparte.**
    Es lo único que hace que la prueba pruebe algo: si el ejemplo tuviera su
    propia redacción, llegaría bien el día que el aviso verdadero llega roto, y
    el botón estaría certificando su propio texto.

    Lo que sí es propio es la franja de arriba y la ausencia de enlaces a datos
    concretos — no hay una factura #0 a la que mandar a nadie.
    """
    if kind == AlertKind.PAYMENT_CLAIM:
        body = payment_claim_message(
            supplier=SAMPLE_SUPPLIER,
            subject="Reclamo de pago (ejemplo)",
            body="Este es el aspecto que tiene un reclamo del portal cuando llega de verdad.",
        )
    elif kind == AlertKind.DUE_SOON:
        body = due_soon_message(
            number=SAMPLE_INVOICE,
            supplier=SAMPLE_SUPPLIER,
            due_on="—",
            days_ahead=2,
        )
    elif kind == AlertKind.DAILY_DIGEST:
        body = daily_digest_message(pending_messages=0, stalled_orders=0, lines=[])
    else:
        # Un tipo de aviso que existe en el enum y todavía no tiene redactor. Se
        # manda igual, diciendo lo único cierto: que la ruta hasta el teléfono
        # funciona. Callarse dejaría el botón sin contestar nada.
        body = f"Cordillera: aviso de tipo {kind}."
    return f"{TEST_BANNER}\n\n{body}"
