"""El corte de compras del tablero: qué debo, qué vence y qué no llegó.

Las cuatro tarjetas que la guía visual dibuja en `3b` —deuda a proveedores,
vence en 7 días, OC sin recibir y próximos vencimientos— y la regla que las
cruza a todas: **una factura que esta plataforma no puede avalar no suma**. Una
en revisión tiene un total que nadie confirmó y una pagada de más está
inconsistente, así que ninguna de las dos entra en la deuda —y cuántas hay se
informa, en vez de desaparecer (Artículo II, RF-23 de la 004, RF-16 y RF-28 de
la 005).

Y la otra mitad de esa regla, que es la que se olvida: **una suma y un aviso no
son la misma pregunta**. La factura que nadie pudo atribuir no entra en la
deuda, pero sí en los vencimientos: la fecha llega igual, y esconderla hasta que
alguien resuelva el proveedor sería decidir no avisar.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.modules.purchases.models import InvoiceReviewState
from app.modules.purchases.service import PurchasesService, today_here
from app.shared.events import NormalizedPurchaseOrder
from tests.factories.purchases_factory import InvoiceFactory, PaymentFactory, SupplierFactory

pytestmark = [pytest.mark.integration, pytest.mark.database]


def order(
    number: str,
    *,
    status: str = "Pendiente de envio",
    ordered_on: date | None = None,
) -> NormalizedPurchaseOrder:
    """One normalised row of the purchase orders screen."""
    return NormalizedPurchaseOrder(
        staging_row_id=0,
        number=number,
        ordered_on=ordered_on or today_here(),
        supplier_text="Herramientas Cuyo SRL",
        product_code="COR-0078",
        product_text="COR-0078 - Articulo",
        quantity=10,
        amount=None,
        status_text=status,
    )


class TestWhatIsOwed:
    """La deuda es lo que queda sin pagar de las facturas que se pueden avalar."""

    async def test_it_adds_up_what_is_left_on_each_invoice(self, session: AsyncSession) -> None:
        """Una saldada no es una deuda de cero pesos: no es una deuda."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        await InvoiceFactory.create(session, supplier=supplier, total=100_000)
        half = await InvoiceFactory.create(session, supplier=supplier, total=80_000)
        await PaymentFactory.create(session, invoice=half, amount=30_000)
        settled = await InvoiceFactory.create(session, supplier=supplier, total=50_000)
        await PaymentFactory.create(session, invoice=settled, amount=50_000)

        # Act
        cut = await PurchasesService(session).dashboard()

        # Assert — 100.000 enteros más los 50.000 que le faltan a la segunda.
        assert cut.owed == Decimal(150_000)
        assert cut.open_invoices == 2

    async def test_an_invoice_in_review_does_not_add_and_is_reported(
        self, session: AsyncSession
    ) -> None:
        """RF-23 de la 004: su total no lo confirmó nadie, y el número lo dice."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Cañerias del Litoral SA")
        await InvoiceFactory.create(session, supplier=supplier, total=100_000)
        await InvoiceFactory.create(
            session,
            supplier=supplier,
            total=999_000,
            review_state=InvoiceReviewState.PENDING,
        )

        # Act
        cut = await PurchasesService(session).dashboard()

        # Assert
        assert cut.owed == Decimal(100_000)
        assert cut.open_invoices == 1
        assert cut.excluded_in_review == 1

    async def test_one_paid_beyond_its_total_is_reported_apart(self, session: AsyncSession) -> None:
        """RF-28 de la 005: pagada de más no es saldada, es inconsistente."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Herramientas Cuyo SRL")
        broken = await InvoiceFactory.create(session, supplier=supplier, total=10_000)
        await PaymentFactory.create(session, invoice=broken, amount=15_000)

        # Act
        cut = await PurchasesService(session).dashboard()

        # Assert
        assert cut.owed == Decimal(0)
        assert cut.excluded_inconsistent == 1
        assert cut.excluded_in_review == 0


class TestWhatFallsDue:
    """«Vence en 7 días» mira la semana, y avisa cuáles no tienen recibo."""

    async def test_it_counts_the_week_and_not_what_comes_after(self, session: AsyncSession) -> None:
        """La tarjeta dice siete días, así que cuenta siete días."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Ferrum Andina SA")
        today = today_here()
        await InvoiceFactory.create(
            session, supplier=supplier, total=100_000, due_on=today + timedelta(days=2)
        )
        await InvoiceFactory.create(
            session, supplier=supplier, total=100_000, due_on=today + timedelta(days=30)
        )

        # Act
        cut = await PurchasesService(session).dashboard()

        # Assert
        assert cut.due_soon_days == 7
        assert cut.due_soon == 1
        assert cut.due_soon_without_receipt == 1

    async def test_a_settled_invoice_is_not_falling_due(self, session: AsyncSession) -> None:
        """Lo que ya se pagó no vence: no hay nada que hacer con eso."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Insumos del Valle SRL")
        paid = await InvoiceFactory.create(
            session,
            supplier=supplier,
            total=100_000,
            due_on=today_here() + timedelta(days=3),
        )
        await PaymentFactory.create(session, invoice=paid, amount=100_000)

        # Act
        cut = await PurchasesService(session).dashboard()

        # Assert
        assert cut.due_soon == 0

    async def test_what_already_fell_due_is_counted_apart(self, session: AsyncSession) -> None:
        """Lo vencido no es «lo que viene»: es otra pregunta y va en otro número."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Tornillería Sur")
        await InvoiceFactory.create(
            session, supplier=supplier, total=100_000, due_on=today_here() - timedelta(days=5)
        )

        # Act
        cut = await PurchasesService(session).dashboard()

        # Assert
        assert cut.overdue == 1
        assert cut.due_soon == 0


class TestTheNextDueDates:
    """La lista que la guía dibuja: en el orden en que se pagan."""

    async def test_they_come_in_the_order_they_fall(self, session: AsyncSession) -> None:
        """Y cada una con lo que **falta**, no con lo que la factura decía."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Ferrum Andina SA")
        today = today_here()
        await InvoiceFactory.create(
            session,
            supplier=supplier,
            number="FC-1060",
            total=200_000,
            due_on=today + timedelta(days=6),
        )
        near = await InvoiceFactory.create(
            session,
            supplier=supplier,
            number="FC-1051",
            total=500_000,
            due_on=today + timedelta(days=2),
        )
        await PaymentFactory.create(session, invoice=near, amount=100_000)

        # Act
        cut = await PurchasesService(session).dashboard()

        # Assert
        assert [item.number for item in cut.upcoming] == ["FC-1051", "FC-1060"]
        first = cut.upcoming[0]
        assert first.days_left == 2
        assert first.balance == Decimal(400_000)
        assert first.supplier_name == "Ferrum Andina SA"
        assert first.receipt_issued is False

    async def test_an_invoice_nobody_could_attribute_still_falls_due(
        self, session: AsyncSession
    ) -> None:
        """Esconderla hasta que alguien resuelva el proveedor sería no avisar."""
        # Arrange
        await InvoiceFactory.create(
            session,
            supplier=None,
            supplier_text="FERRUM ANDINA",
            total=100_000,
            due_on=today_here() + timedelta(days=1),
        )

        # Act
        cut = await PurchasesService(session).dashboard()

        # Assert — avisa, y dice que el importe todavía no lo confirmó nadie.
        assert len(cut.upcoming) == 1
        assert cut.upcoming[0].supplier_name is None
        assert cut.upcoming[0].supplier_text == "FERRUM ANDINA"
        assert cut.upcoming[0].in_review is True
        assert cut.due_soon == 1
        # Y no suma: la deuda sólo agrega lo que esta plataforma puede avalar.
        assert cut.owed == Decimal(0)
        assert cut.excluded_in_review == 1


class TestWhatWasOrderedAndNeverArrived:
    """«OC sin recibir»: todo lo que todavía no llegó, y hace cuánto."""

    async def test_a_received_order_is_not_pending(self, session: AsyncSession) -> None:
        """Una orden recibida está terminada, por mucho que haya tardado."""
        # Arrange
        service = PurchasesService(session)
        await service.register_orders(
            batch_id=1, orders=(order("OC-0001"), order("OC-0002", status="Recibida"))
        )

        # Act
        cut = await service.dashboard()

        # Assert
        assert cut.orders_pending == 1
        assert cut.orders_stalled == 0

    async def test_one_that_sat_too_long_is_counted_as_stalled(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Con el límite que el dueño configuró, que viaja para poder decirlo."""
        # Arrange
        service = PurchasesService(session)
        await service.register_orders(batch_id=1, orders=(order("OC-0003"),))
        stored = await service.purchases.order_numbered("OC-0003")
        assert stored is not None
        stored.status_since = today_here() - timedelta(days=90)
        await session.flush()

        # Act
        cut = await service.dashboard()

        # Assert
        assert cut.orders_pending == 1
        assert cut.orders_stalled == 1
        assert cut.stalled_days > 0


class TestAnEmptyLedger:
    """Sin nada cargado, el corte contesta ceros: es una respuesta, no un vacío."""

    async def test_it_answers_zero_rather_than_nothing(self, session: AsyncSession) -> None:
        """RF-27 de la 009, dicho para compras: cero es un dato."""
        # Act
        cut = await PurchasesService(session).dashboard()

        # Assert
        assert cut.owed == Decimal(0)
        assert cut.open_invoices == 0
        assert cut.due_soon == 0
        assert cut.orders_pending == 0
        assert cut.upcoming == []
