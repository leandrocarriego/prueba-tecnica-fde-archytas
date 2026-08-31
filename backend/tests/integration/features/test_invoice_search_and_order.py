"""H8 de la 004: encontrar una factura sin recorrer la lista.

La historia entera en un archivo, porque las seis preguntas que hace son la
misma pregunta —¿qué queda en la lista?— con distinta condición encima, y
verlas juntas es lo que muestra que ninguna se pisa con las otras.

Cuatro de los seis requisitos no existían cuando este archivo se escribió, y se
construyeron con él: buscar por **CUIT** (RF-41), buscar por **razón social**
—no por la grafía con que llegó escrito el nombre— (RF-42), filtrar por
**rango de fechas de emisión** (RF-43) y **ordenar por fecha y por total**
(RF-45). Los otros dos —filtrar por proveedor (RF-44) y por estado de revisión
(RF-46)— estaban construidos y sin un solo test: un filtro que nadie prueba se
rompe en silencio la próxima vez que alguien toca la consulta.

El padrón de estos tests son dos proveedores con CUIT distinto, y la trampa
está puesta a propósito: **una de las facturas llegó con el nombre mal escrito**
y fue asignada igual. Buscarla por la razón social del padrón es lo único que
distingue RF-42 de la búsqueda por texto que ya existía.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.purchases.models import InvoiceOrder, InvoiceReviewState
from app.modules.purchases.service import PurchasesService
from tests.factories.purchases_factory import InvoiceFactory, SupplierFactory

pytestmark = [pytest.mark.integration, pytest.mark.database]

BELGRANO = "Aceros Belgrano SA"
BELGRANO_TAX_ID = "30-70918273-4"
CUYO = "Herramientas Cuyo SRL"
CUYO_TAX_ID = "30-75263748-9"

# La grafía con que llegó una de las facturas de Belgrano. No es la razón
# social, y ese es el punto: RF-42 pide buscar por la del padrón.
MISSPELLED = "ACEROS BELGANO S.A."


class Register:
    """Las facturas contra las que se hace cada pregunta de H8."""

    def __init__(self) -> None:
        self.belgrano_id = 0
        self.cuyo_id = 0
        self.numbers: dict[str, str] = {}


@pytest.fixture
async def listing(session: AsyncSession) -> Register:
    """Dos proveedores, cinco facturas, tres fechas y cuatro montos distintos."""
    belgrano = await SupplierFactory.create(
        session, legal_name=BELGRANO, tax_id=BELGRANO_TAX_ID, payment_term_days=45
    )
    cuyo = await SupplierFactory.create(
        session, legal_name=CUYO, tax_id=CUYO_TAX_ID, payment_term_days=30
    )

    await InvoiceFactory.create(
        session, supplier=belgrano, number="F-1001", issued_on=date(2026, 3, 5), total=50_000
    )
    # La que llegó con el nombre mal escrito y se asignó igual.
    await InvoiceFactory.create(
        session,
        supplier=belgrano,
        number="F-1002",
        issued_on=date(2026, 5, 20),
        total=300_000,
        supplier_text=MISSPELLED,
    )
    await InvoiceFactory.create(
        session, supplier=cuyo, number="F-2001", issued_on=date(2026, 5, 2), total=120_000
    )
    await InvoiceFactory.create(
        session, supplier=cuyo, number="F-2002", issued_on=date(2026, 7, 11), total=80_000
    )
    # Una apartada, sin proveedor identificado.
    await InvoiceFactory.create(
        session,
        number="F-3001",
        issued_on=date(2026, 5, 9),
        total=999_000,
        review_state=InvoiceReviewState.PENDING,
    )
    await session.commit()

    register = Register()
    register.belgrano_id = belgrano.id
    register.cuyo_id = cuyo.id
    return register


async def numbers(session: AsyncSession, **filters: object) -> list[str]:
    """Los números de las facturas que quedan, en el orden en que quedan."""
    result = await PurchasesService(session).list_invoices(limit=100, **filters)  # type: ignore[arg-type]
    return [item.number for item in result.items]


class TestSearchingBySupplier:
    """RF-41 y RF-42: el CUIT y la razón social, que son lo que hay a mano."""

    async def test_the_tax_id_finds_every_invoice_of_that_supplier(
        self, session: AsyncSession, listing: Register
    ) -> None:
        """RF-41: se escribe el CUIT y quedan sus facturas."""
        # Act
        found = await numbers(session, query=BELGRANO_TAX_ID)

        # Assert
        assert sorted(found) == ["F-1001", "F-1002"]

    async def test_the_tax_id_is_found_without_its_dashes(
        self, session: AsyncSession, listing: Register
    ) -> None:
        """Un CUIT copiado sin puntuación es el mismo número."""
        # Act
        found = await numbers(session, query="30709182734")

        # Assert
        assert sorted(found) == ["F-1001", "F-1002"]

    async def test_the_legal_name_finds_an_invoice_that_arrived_misspelled(
        self, session: AsyncSession, listing: Register
    ) -> None:
        """RF-42: la razón social del padrón, no la grafía de esa factura.

        Es la mitad de RF-42 que la búsqueda por texto no cubría: `F-1002`
        llegó como «ACEROS BELGANO S.A.» y nadie la va a buscar así.
        """
        # Act
        found = await numbers(session, query="Belgrano")

        # Assert
        assert "F-1002" in found

    async def test_the_number_still_finds_an_invoice_nobody_could_attribute(
        self, session: AsyncSession, listing: Register
    ) -> None:
        """El join es izquierdo: una factura apartada sigue apareciendo por su número."""
        # Act
        found = await numbers(session, query="F-3001")

        # Assert
        assert found == ["F-3001"]

    async def test_a_tax_id_of_nobody_finds_nothing(
        self, session: AsyncSession, listing: Register
    ) -> None:
        """Un CUIT que no es de nadie no puede traer facturas de todos."""
        # Act
        found = await numbers(session, query="30-99999999-9")

        # Assert
        assert found == []


class TestFilteringByIssueDate:
    """RF-43: el rango de fechas es el de emisión, no el de vencimiento."""

    async def test_a_range_keeps_only_what_was_issued_inside_it(
        self, session: AsyncSession, listing: Register
    ) -> None:
        """RF-43: mayo de 2026 son tres facturas y no las cinco."""
        # Act
        found = await numbers(session, issued_from=date(2026, 5, 1), issued_to=date(2026, 5, 31))

        # Assert
        assert sorted(found) == ["F-1002", "F-2001", "F-3001"]

    async def test_both_ends_are_included(self, session: AsyncSession, listing: Register) -> None:
        """Un rango de un día trae la factura de ese día."""
        # Act
        found = await numbers(session, issued_from=date(2026, 3, 5), issued_to=date(2026, 3, 5))

        # Assert
        assert found == ["F-1001"]

    async def test_it_is_not_the_due_date(self, session: AsyncSession, listing: Register) -> None:
        """`F-1001` se emitió en marzo y vence en abril: son dos preguntas.

        Sin esta diferencia, «las facturas de marzo» significaría una cosa
        para quien mira la lista y otra para quien mira el calendario.
        """
        # Act
        by_issue = await numbers(session, issued_from=date(2026, 3, 1), issued_to=date(2026, 3, 31))
        by_due = await numbers(session, due_from=date(2026, 3, 1), due_to=date(2026, 3, 31))

        # Assert
        assert by_issue == ["F-1001"]
        assert by_due == []


class TestOrdering:
    """RF-45: por fecha y por total, en los dos sentidos."""

    async def test_by_default_the_newest_comes_first(
        self, session: AsyncSession, listing: Register
    ) -> None:
        """El orden de siempre no cambia porque ahora se pueda pedir otro."""
        # Act
        found = await numbers(session)

        # Assert
        assert found == ["F-2002", "F-1002", "F-3001", "F-2001", "F-1001"]

    async def test_by_issue_date_ascending(self, session: AsyncSession, listing: Register) -> None:
        """RF-45: la más vieja primero."""
        # Act
        found = await numbers(session, order=InvoiceOrder.ISSUED_ASC)

        # Assert
        assert found == ["F-1001", "F-2001", "F-3001", "F-1002", "F-2002"]

    async def test_by_total_descending(self, session: AsyncSession, listing: Register) -> None:
        """RF-45: la más cara primero."""
        # Act
        found = await numbers(session, order=InvoiceOrder.TOTAL_DESC)

        # Assert
        assert found == ["F-3001", "F-1002", "F-2001", "F-2002", "F-1001"]

    async def test_by_total_ascending(self, session: AsyncSession, listing: Register) -> None:
        """RF-45: y la más barata."""
        # Act
        found = await numbers(session, order=InvoiceOrder.TOTAL_ASC)

        # Assert
        assert found == ["F-1001", "F-2002", "F-2001", "F-1002", "F-3001"]

    async def test_the_order_survives_a_filter(
        self, session: AsyncSession, listing: Register
    ) -> None:
        """Ordenar y filtrar son dos cosas, y tienen que poder pasar juntas."""
        # Act
        found = await numbers(
            session, supplier_id=listing.belgrano_id, order=InvoiceOrder.TOTAL_ASC
        )

        # Assert
        assert found == ["F-1001", "F-1002"]

    async def test_two_invoices_of_the_same_day_do_not_move_between_pages(
        self, session: AsyncSession, listing: Register
    ) -> None:
        """El id desempata: sin eso, la página dos repite una fila de la uno."""
        # Arrange — dos facturas del mismo día y del mismo monto
        supplier = await SupplierFactory.create(session, legal_name="Empate SA", tax_id=None)
        for number in ("F-4001", "F-4002"):
            await InvoiceFactory.create(
                session,
                supplier=supplier,
                number=number,
                issued_on=date(2026, 9, 1),
                total=Decimal("1000"),
            )
        await session.commit()
        service = PurchasesService(session)

        # Act
        first = await service.list_invoices(limit=1, supplier_id=supplier.id)
        second = await service.list_invoices(skip=1, limit=1, supplier_id=supplier.id)

        # Assert
        assert first.items[0].number != second.items[0].number


class TestTheFiltersThatWereNeverTested:
    """RF-44 y RF-46: construidos desde el primer día, verificados recién ahora."""

    async def test_by_supplier(self, session: AsyncSession, listing: Register) -> None:
        """RF-44: quedan las de ese proveedor y ninguna más."""
        # Act
        found = await numbers(session, supplier_id=listing.cuyo_id)

        # Assert
        assert sorted(found) == ["F-2001", "F-2002"]

    async def test_by_review_state(self, session: AsyncSession, listing: Register) -> None:
        """RF-46: las que están esperando a una persona."""
        # Act
        found = await numbers(session, review_state=InvoiceReviewState.PENDING)

        # Assert
        assert found == ["F-3001"]

    async def test_the_count_matches_the_filtered_page(
        self, session: AsyncSession, listing: Register
    ) -> None:
        """El total que informa la pantalla es el de lo filtrado, no el del padrón.

        Un contador que ignora el filtro dice «120 facturas» debajo de una
        lista de dos, y quien lo lee deja de creerle a los dos números.
        """
        # Act
        result = await PurchasesService(session).list_invoices(supplier_id=listing.belgrano_id)

        # Assert
        assert result.total == 2
        assert len(result.items) == 2
