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
