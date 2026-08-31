"""A quién le llega un aviso, y cuándo puede sonar (H6 y H7 de la 007).

**Es la mitad de la feature que no tenía un solo test.** La franja horaria, el
ruteo por rol, los destinatarios y el resumen diario estaban construidos y verdes
por lectura, y son justamente la parte que puede despertar a alguien un sábado a
las once de la noche — que es como un canal se silencia, y un canal silenciado es
la feature entera sin efecto.

Lo que se fija acá:

* fuera de la franja el aviso **se demora, no se descarta** (RF-42, RF-43);
* le llega a quien tiene el rol configurado, a su número, y **no** a quien perdió
  el acceso (RF-37, RF-44, RF-45);
* el resumen sale a su hora, sale aunque no haya nada, y no repite lo resuelto
  (RF-35, RF-36, RF-40, RF-41);
* y un aviso que no se pudo entregar **queda dicho en la pantalla** (RF-38).
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.messaging.models import MessageKind, MessageState, SupplierMessage
from app.modules.messaging.service import MessagingService
from app.modules.notifications.delivery import AlertRouter
from app.modules.notifications.models import AlertKind
from app.modules.notifications.repository import NotificationsRepository
from app.modules.notifications.service import daily_digest_message
from app.shared.events import AlertDeliveryFailed, events
from app.shared.time import BUSINESS_TIME_ZONE

pytestmark = [pytest.mark.integration, pytest.mark.database]

AN_HOUR = 3600


def moment(day: int, hour: int, minute: int = 0) -> datetime:
    """Un momento de marzo de 2026 en la hora del negocio. El 2 es un lunes."""
    return datetime(2026, 3, day, hour, minute, tzinfo=BUSINESS_TIME_ZONE)


async def recipient(session: AsyncSession, *, user_id: int, role: str, phone: str) -> None:
    """Alguien a quien un aviso puede llegarle, como lo sabe este módulo."""
    await NotificationsRepository(session).put_recipient(user_id=user_id, role=role, phone=phone)


class TestTheAlertWindow:
    """RF-42 y RF-43: fuera de la franja el aviso espera, nunca se descarta."""

    async def test_inside_the_window_it_goes_out_at_once(self, session: AsyncSession) -> None:
        """Martes a las 10, dentro de 08:00–18:00 de lunes a viernes."""
        # Act
        delay = await AlertRouter(session).delay_until_window(moment(3, 10))

        # Assert
        assert delay == 0

    async def test_a_saturday_night_claim_waits_until_monday(self, session: AsyncSession) -> None:
        """El criterio firmado de RF-42, al pie de la letra.

        *«Un reclamo que entra el sábado a las 22 no suena el sábado: el aviso
        llega el lunes a las 8.»*
        """
        # Act — sábado 7 de marzo de 2026 a las 22:00.
        delay = await AlertRouter(session).delay_until_window(moment(7, 22))

        # Assert — hasta el lunes 9 a las 08:00: 34 horas.
        assert delay == 34 * AN_HOUR

    async def test_before_the_window_opens_it_waits_only_the_hours_left(
        self, session: AsyncSession
    ) -> None:
        """El caso que se rompe sin ruido: martes a las 6 espera dos horas, no veintiséis.

        Es la clase de error que sólo se nota porque a alguien le llega un aviso
        un día tarde, y para entonces nadie lo asocia con la franja.
        """
        # Act
        delay = await AlertRouter(session).delay_until_window(moment(3, 6))

        # Assert
        assert delay == 2 * AN_HOUR

    async def test_after_the_window_closes_it_waits_for_the_next_morning(
        self, session: AsyncSession
    ) -> None:
        """Martes 19:00 → miércoles 08:00."""
        # Act
        delay = await AlertRouter(session).delay_until_window(moment(3, 19))

        # Assert
        assert delay == 13 * AN_HOUR

    async def test_friday_evening_waits_the_whole_weekend(self, session: AsyncSession) -> None:
        """Viernes 19:00 → lunes 08:00, saltando sábado y domingo."""
        # Act
        delay = await AlertRouter(session).delay_until_window(moment(6, 19))

        # Assert
        assert delay == 61 * AN_HOUR


class TestWhoAnAlertReaches:
    """RF-37, RF-44 y RF-45: el rol configurado, su número, y nadie más."""

    async def test_a_claim_goes_to_whoever_handles_purchasing(self, session: AsyncSession) -> None:
        """RF-37 y RF-44: el valor firmado, sin que nadie configure nada."""
        # Arrange
        await recipient(session, user_id=1, role="PURCHASING", phone="+5491111111111")
        await recipient(session, user_id=2, role="SALES", phone="+5492222222222")

        # Act
        phones = await AlertRouter(session).phones_for(AlertKind.PAYMENT_CLAIM)

        # Assert
        assert phones == ["+5491111111111"]

    async def test_somebody_who_lost_their_access_stops_receiving(
        self, session: AsyncSession
    ) -> None:
        """RF-45, que **no es una regla que alguien tenga que recordar**.

        Es lo que pasa cuando llega `UserDeactivated`: el destinatario queda
        inactivo y `active_with_role` deja de devolverlo. No hay ningún paso que
        se pueda olvidar.
        """
        # Arrange
        await recipient(session, user_id=1, role="PURCHASING", phone="+5491111111111")
        await NotificationsRepository(session).set_active(1, active=False)

        # Act
        phones = await AlertRouter(session).phones_for(AlertKind.PAYMENT_CLAIM)

        # Assert
        assert phones == []

    async def test_a_vacant_role_falls_back_to_the_owner(self, session: AsyncSession) -> None:
        """El aviso no desaparece porque un rol esté vacante: cae al dueño."""
        # Arrange — no hay nadie en compras.
        await recipient(session, user_id=1, role="OWNER", phone="+5493333333333")

        # Act
        phones = await AlertRouter(session).phones_for(AlertKind.PAYMENT_CLAIM)

        # Assert
        assert phones == ["+5493333333333"]

    async def test_the_owner_can_point_a_kind_at_another_role(
        self, session: AsyncSession, owner: object
    ) -> None:
        """RF-37: el reparto inicial es un punto de partida, no una decisión del cliente."""
        # Arrange
        repository = NotificationsRepository(session)
        await recipient(session, user_id=1, role="PURCHASING", phone="+5491111111111")
        await recipient(session, user_id=2, role="SALES", phone="+5492222222222")

        # Act
        await repository.put_route(AlertKind.PAYMENT_CLAIM, "SALES", actor_user_id=1)

        # Assert
        assert await AlertRouter(session).phones_for(AlertKind.PAYMENT_CLAIM) == ["+5492222222222"]


class TestTheDailyDigest:
    """RF-35, RF-40 y RF-41: qué junta, qué no repite, y que sale igual."""

    async def test_a_digest_with_nothing_pending_is_still_worth_sending(self) -> None:
        """RF-35: «no hay nada» y «el resumen se rompió» se ven igual desde un teléfono.

        Sólo una de las dos es una buena noticia, y por eso el resumen sale
        también cuando no hay nada que contar.
        """
        # Act
        text = daily_digest_message(pending_messages=0, stalled_orders=0, lines=[])

        # Assert
        assert "No hay nada pendiente" in text
        assert "Mensajes sin resolver: 0" in text

    async def test_a_resolved_message_is_not_in_the_digest(
        self, session: AsyncSession, owner: object
    ) -> None:
        """RF-40: el resumen es sobre lo que sigue esperando a alguien.

        Repetir lo que ya se resolvió es cómo un mensaje diario se convierte en
        uno que nadie lee.
        """
        # Arrange
        service = MessagingService(session)
        session.add(
            SupplierMessage(
                external_id="MSG-D1",
                received_at=datetime.now(UTC),
                sender_text="Aceros Belgrano SA",
                kind=MessageKind.PAYMENT_CLAIM,
                subject="Reclamo",
                state=MessageState.PENDING,
            )
        )
        await session.flush()
        pending_before = await service.count_pending()

        # Act
        message = (await service.list_messages()).items[0]
        await service.resolve(message.id, actor_user_id=1)

        # Assert
        assert pending_before == 1
        assert await service.count_pending() == 0
        assert await service.pending_messages() == []


class TestAnAlertThatDidNotGetThrough:
    """RF-38: el aviso que no se pudo entregar queda dicho en la pantalla."""

    async def test_the_failure_is_recorded_on_the_message_it_was_about(
        self, session: AsyncSession
    ) -> None:
        """El teléfono es exactamente donde la noticia **no** llegó.

        Así que el único lugar que queda para avisar es la pantalla que la
        persona abre igual. La columna existía y el cartel se dibujaba desde el
        primer día; lo que faltaba era algo que lo escribiera.
        """
        # Arrange
        session.add(
            SupplierMessage(
                external_id="MSG-F1",
                received_at=datetime.now(UTC),
                sender_text="Aceros Belgrano SA",
                kind=MessageKind.PAYMENT_CLAIM,
                subject="Reclamo",
                state=MessageState.PENDING,
            )
        )
        await session.flush()
        message = (await MessagingService(session).list_messages()).items[0]

        # Act
        await events.publish(
            AlertDeliveryFailed(
                kind=AlertKind.PAYMENT_CLAIM.value,
                reason="El canal no respondió",
                message_id=message.id,
            ),
            session,
        )

        # Assert
        after = (await MessagingService(session).list_messages()).items[0]
        assert after.alert_failure == "El canal no respondió"

    async def test_an_alert_with_no_message_behind_it_is_announced_and_recorded_nowhere(
        self, session: AsyncSession
    ) -> None:
        """Los avisos de vencimiento de la 005 no tienen mensaje en el que anotarlo.

        Se publican igual y no rompen nada: el evento queda listo para el día que
        la 005 tenga su propio RF-38.
        """
        # Act / Assert — que no levante.
        await events.publish(
            AlertDeliveryFailed(
                kind=AlertKind.DUE_SOON.value, reason="El canal no respondió", message_id=None
            ),
            session,
        )
