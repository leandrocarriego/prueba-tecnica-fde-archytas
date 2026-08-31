"""El calendario: mover un vencimiento, y qué cambia cuando ya venció.

La distinción más fina de la 006 es la que separa RF-26/RF-27 de RF-28/RF-30:
reprogramar **antes** del vencimiento mueve el plazo para emitir el recibo y la
medición del atraso; reprogramar **después** no mueve ninguna de las dos. Es lo
que se fija acá, más las reglas de qué se puede tocar y qué no.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.modules.purchases.models import DueDateOrigin
from app.modules.purchases.service import PurchasesService, today_here
from app.shared.events import DueDateChanged, events
from app.shared.errors import ConflictError
from tests.factories.purchases_factory import InvoiceFactory, SupplierFactory

pytestmark = [pytest.mark.integration, pytest.mark.database]

# A window around today rather than a month written down. A calendar test that
# pins a month starts failing the day that month is in the past — and half of
# what these tests assert is precisely about "before" and "after" today.
WINDOW = timedelta(days=90)


def soon(days: int) -> date:
    """A date relative to today, on the clock the business runs on."""
    return today_here() + timedelta(days=days)


async def calendar(session: AsyncSession, **filters: bool) -> list:
    """The entries around today, which is where these tests work."""
    read = await PurchasesService(session).calendar(
        since=today_here() - WINDOW, until=today_here() + WINDOW, **filters
    )
    return read.items


class TestWhatIsOnTheCalendar:
    """H1 y H2: cada factura registrada aparece en su fecha, con lo que muestra el día."""

    async def test_an_invoice_puts_itself_on_the_calendar(self, session: AsyncSession) -> None:
        """RF-03: y con su descripción, su monto y su proveedor (RF-02)."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        stored = await InvoiceFactory.create(
            session, supplier=supplier, due_on=soon(18), total=223_376
        )
        await PurchasesService(session)._sync_due_date(stored)  # noqa: SLF001

        # Act
        entries = await calendar(session)

        # Assert
        entry = next(item for item in entries if item.invoice_id == stored.id)
        assert entry.on_date == soon(18)
        assert entry.origin is DueDateOrigin.INVOICE
        assert entry.amount == Decimal(223_376)
        assert stored.number in entry.description

    async def test_it_can_show_only_what_has_no_receipt(self, session: AsyncSession) -> None:
        """RF-10, y RF-40 para esconder las saldadas."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        service = PurchasesService(session)
        stored = await InvoiceFactory.create(session, supplier=supplier, due_on=soon(20))
        await service._sync_due_date(stored)  # noqa: SLF001

        # Act
        without_receipt = await calendar(session, without_receipt=True)

        # Assert
        assert any(item.invoice_id == stored.id for item in without_receipt)


class TestAddingAndRemovingByHand:
    """H3: lo que se carga a mano se corrige y se borra; lo de una factura no."""

    async def test_a_hand_made_entry_is_added_corrected_and_removed(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-12 a RF-17."""
        # Arrange
        service = PurchasesService(session)

        # Act
        added = await service.add_due_date(
            on_date=soon(10),
            description="Pago de alquiler",
            amount=Decimal(500_000),
            actor_user_id=owner.id,
        )
        corrected = await service.edit_due_date(
            added.id, description="Alquiler del depósito", amount=None, actor_user_id=owner.id
        )
        await service.remove_due_date(added.id, actor_user_id=owner.id)

        # Assert
        assert added.origin is DueDateOrigin.MANUAL
        assert corrected.description == "Alquiler del depósito"
        assert not any(item.id == added.id for item in await calendar(session))

    async def test_an_entry_that_comes_from_an_invoice_is_not_removed(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-18: la factura existe, y el día en que vence también."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        service = PurchasesService(session)
        stored = await InvoiceFactory.create(session, supplier=supplier, due_on=soon(12))
        await service._sync_due_date(stored)  # noqa: SLF001
        entry = next(item for item in await calendar(session) if item.invoice_id == stored.id)

        # Act / Assert
        with pytest.raises(ConflictError):
            await service.remove_due_date(entry.id, actor_user_id=owner.id)


class TestMovingAVencimiento:
    """H4: mover conserva de dónde venía, y decide distinto según si ya venció."""

    async def test_it_keeps_where_it_was_and_who_moved_it(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-20 a RF-24."""
        # Arrange
        service = PurchasesService(session)
        added = await service.add_due_date(
            on_date=soon(10), description="Seguro", amount=None, actor_user_id=owner.id
        )

        # Act
        moved = await service.move_due_date(
            added.id,
            on_date=soon(24),
            reason="El proveedor pidió correrlo",
            actor_user_id=owner.id,
        )

        # Assert
        assert moved.on_date == soon(24)
        assert moved.original_date == soon(10)
        entry = next(item for item in await calendar(session) if item.id == added.id)
        assert entry.was_rescheduled is True
        assert entry.changes[0].previous_date == soon(10)
        assert entry.changes[0].reason == "El proveedor pidió correrlo"
        assert entry.changes[0].actor_user_id == owner.id

    async def test_moving_it_into_the_past_asks_first(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-25: el pedido de confirmación es el rechazo, y se contesta confirmando."""
        # Arrange
        service = PurchasesService(session)
        added = await service.add_due_date(
            on_date=today_here() + timedelta(days=5),
            description="Impuesto",
            amount=None,
            actor_user_id=owner.id,
        )
        yesterday = today_here() - timedelta(days=1)

        # Act / Assert
        with pytest.raises(ConflictError):
            await service.move_due_date(
                added.id, on_date=yesterday, reason=None, actor_user_id=owner.id
            )

        moved = await service.move_due_date(
            added.id,
            on_date=yesterday,
            reason=None,
            actor_user_id=owner.id,
            confirm_past=True,
        )
        assert moved.on_date == yesterday

    async def test_rescheduling_before_it_falls_due_moves_the_receipt_deadline(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-26: la fecha nueva pasa a ser el plazo para emitir el recibo."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        service = PurchasesService(session)
        stored = await InvoiceFactory.create(
            session, supplier=supplier, due_on=today_here() + timedelta(days=2)
        )
        await service._sync_due_date(stored)  # noqa: SLF001
        entry = await service.purchases.due_date_of_invoice(stored.id)
        assert entry is not None
        later = today_here() + timedelta(days=20)

        # Act
        await service.move_due_date(entry.id, on_date=later, reason=None, actor_user_id=owner.id)

        # Assert
        assert (await service.get_invoice(stored.id)).due_on == later

    async def test_rescheduling_one_that_already_fell_due_changes_none_of_that(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-28, RF-29, RF-30: sigue vencida, sigue sin recibo y se mide contra la original.

        Es la confusión más fácil de la feature: si mover una vencida habilitara
        el recibo, RF-34 de 005 dejaría de valer con sólo arrastrar una tarjeta.
        """
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        service = PurchasesService(session)
        original_due = today_here() - timedelta(days=5)
        stored = await InvoiceFactory.create(session, supplier=supplier, due_on=original_due)
        await service._sync_due_date(stored)  # noqa: SLF001
        entry = await service.purchases.due_date_of_invoice(stored.id)
        assert entry is not None

        # Act
        await service.move_due_date(
            entry.id,
            on_date=today_here() + timedelta(days=15),
            reason=None,
            actor_user_id=owner.id,
        )

        # Assert
        read = await service.get_invoice(stored.id)
        assert read.due_on == original_due
        assert read.is_overdue_without_receipt is True
        with pytest.raises(ConflictError):
            await service.issue_receipt(stored.id, actor_user_id=owner.id)


class TestAnOverdueOneMovedToAnotherMonth:
    """La tarjeta se muestra donde está, con lo que la factura dice de sí misma."""

    async def test_it_keeps_everything_it_says_about_the_invoice(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-30, y de refilón RF-02, RF-09 y RF-39.

        El cruce entre la entrada y su factura se hacía **por fecha** —las
        facturas que vencen en la ventana pedida— y no por la factura que la
        entrada nombra. Una vencida reprogramada a otro mes tiene la tarjeta en
        una ventana y su `due_on` en otra, así que volvía sin proveedor, sin
        estado de pago y **sin la marca de vencida sin recibo**, que es
        exactamente lo que RF-30 promete que se sigue viendo.

        El ejemplo del criterio firmado —vence el 10, se reprograma el 12 para
        el 20— cae entero dentro de un mes y por eso pasaba igual. Este test
        cruza el borde a propósito.
        """
        # Arrange — vencida hace cinco días, reprogramada a 40 días de hoy.
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        service = PurchasesService(session)
        stored = await InvoiceFactory.create(
            session, supplier=supplier, due_on=today_here() - timedelta(days=5), total=10_000
        )
        await service._sync_due_date(stored)  # noqa: SLF001
        entry = await service.purchases.due_date_of_invoice(stored.id)
        assert entry is not None
        moved_to = soon(40)
        await service.move_due_date(entry.id, on_date=moved_to, reason=None, actor_user_id=owner.id)

        # Act — la ventana donde ahora está la tarjeta, y no donde vence la factura.
        read = await service.calendar(
            since=moved_to - timedelta(days=2), until=moved_to + timedelta(days=2)
        )

        # Assert
        card = next(item for item in read.items if item.invoice_id == stored.id)
        assert card.supplier_name == "Aceros Belgrano SA"
        assert card.payment_state == "SIN_PAGOS"
        assert card.receipt_issued is False
        assert card.is_overdue_without_receipt is True


class TestTheLiveChannel:
    """H5: lo que una persona hace llega a la pantalla de la otra."""

    async def test_a_change_that_commits_is_announced_with_who_made_it(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-31, RF-33: el evento sale, con el nombre de quien lo hizo.

        Se verifica sobre el evento de dominio y no sobre el socket: lo que la
        feature promete es que el cambio **se anuncia**, y por dónde viaja es
        una decisión del plan que puede cambiar sin que la promesa cambie.
        """
        # Arrange
        service = PurchasesService(session)
        anunciados: list[tuple[str, str]] = []

        async def escuchar(event: DueDateChanged, _session: AsyncSession) -> None:
            anunciados.append((event.action, event.actor_name))

        events.subscribe(DueDateChanged)(escuchar)
        try:
            # Act — los cuatro verbos, que es lo que RF-31 nombra.
            entry = await service.add_due_date(
                on_date=soon(5),
                description="Alquiler",
                amount=Decimal(1000),
                actor_user_id=owner.id,
                actor_name="Marcela",
            )
            await service.edit_due_date(
                entry.id,
                description="Alquiler del depósito",
                amount=None,
                actor_user_id=owner.id,
                actor_name="Marcela",
            )
            await service.move_due_date(
                entry.id,
                on_date=soon(9),
                reason=None,
                actor_user_id=owner.id,
                actor_name="Marcela",
            )
            await service.remove_due_date(
                entry.id, actor_user_id=owner.id, actor_name="Marcela"
            )
        finally:
            events.unsubscribe(DueDateChanged, escuchar)

        # Assert — los cuatro, y ninguno anónimo.
        assert [action for action, _ in anunciados] == ["added", "edited", "moved", "removed"]
        assert {name for _, name in anunciados} == {"Marcela"}

    async def test_a_refused_move_announces_nothing(
        self, session: AsyncSession, owner: User
    ) -> None:
        """`GEN-09`: lo que no llegó a pasar no se anuncia.

        Es el test que sostiene la decisión de transporte del plan. Se anuncia
        con `NOTIFY`, que Postgres entrega **al commitear**, justamente para que
        una caída del canal de una persona no pueda abortar el cambio de otra.
        Si alguna vez esto se cambia por un empujón a un socket dentro de la
        transacción, este test sigue pasando y el acoplamiento vuelve — así que
        lo que se fija acá es lo observable: un movimiento rechazado no le
        cuenta nada a nadie.
        """
        # Arrange
        service = PurchasesService(session)
        entry = await service.add_due_date(
            on_date=soon(5), description="Seguro", amount=None, actor_user_id=owner.id
        )
        anunciados: list[str] = []

        async def escuchar(event: DueDateChanged, _session: AsyncSession) -> None:
            anunciados.append(event.action)

        events.subscribe(DueDateChanged)(escuchar)
        try:
            # Act — mover al pasado sin confirmar se rechaza (RF-25).
            with pytest.raises(ConflictError):
                await service.move_due_date(
                    entry.id,
                    on_date=today_here() - timedelta(days=1),
                    reason=None,
                    actor_user_id=owner.id,
                )
        finally:
            events.unsubscribe(DueDateChanged, escuchar)

        # Assert
        assert anunciados == []

    async def test_two_people_moving_the_same_entry_keep_both_moves(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-34: vale el último y los dos quedan en el historial.

        Está cumplido **sin** canal en vivo —lo resuelve la tabla de
        movimientos— y por eso no se va con la H5 si algún día se difiere.
        """
        # Arrange
        service = PurchasesService(session)
        entry = await service.add_due_date(
            on_date=soon(5), description="Impuestos", amount=None, actor_user_id=owner.id
        )

        # Act — dos movimientos seguidos sobre la misma entrada.
        await service.move_due_date(
            entry.id, on_date=soon(10), reason="Lo pidió el proveedor", actor_user_id=owner.id
        )
        await service.move_due_date(
            entry.id, on_date=soon(20), reason="Se acordó otra fecha", actor_user_id=owner.id
        )

        # Assert
        cards = await calendar(session)
        card = next(item for item in cards if item.id == entry.id)
        assert card.on_date == soon(20)
        assert [change.previous_date for change in card.changes] == [soon(5), soon(10)]
