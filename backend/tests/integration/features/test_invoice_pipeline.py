"""Las tres tasks de la 004, corridas dos veces (`PY-07`, `TEST-04`).

**Por qué este archivo existe.** El `/review-feature` de la 004 encontró que
`extract_invoices`, `extract_invoice_file` y `extract_supplier_ledger` eran tres
tasks nuevas sin un solo test que las corriera dos veces. El mecanismo que las
hace idempotentes —el salto por hash de `PortalService._extract`— sí estaba
probado, pero por el camino de precios (`test_price_pipeline.py`), y el de
facturas tiene un paso más que ése no tiene: **la descarga del archivo, una por
factura**. Un reintento de Celery sobre esa task es lo más frecuente que le puede
pasar a esta feature —cien visitas a un sistema ajeno, espaciadas— y era
justamente lo que nadie ejercitaba.

Lo que se prueba es lo que `PY-07` promete: **re-ejecutar no duplica efectos.**
No que la task "no falle" dos veces.

Con el portal apagado, como toda la suite (`TEST-03`): el lector es `FakePortal`,
que contesta desde los fixtures capturados de `tests/fixtures/portal/`.
"""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ingestion.models import InvoiceFileRead, InvoiceRow
from app.modules.portal.models import PortalDocument, PortalSection
from app.modules.portal.service import PortalService
from app.modules.purchases.models import Invoice, InvoiceDocument
from tests.factories.portal_factory import FakePortal

pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.portal]

# Una factura de las cien de la pantalla, y la que tiene fixture de archivo.
AN_INVOICE = "F-8411"


async def count(session: AsyncSession, model: type) -> int:
    """How many rows of something there are right now."""
    result = await session.execute(select(func.count()).select_from(model))
    return int(result.scalar_one())


async def documents_of(session: AsyncSession, section: PortalSection) -> int:
    """How many documents of one section landed in `raw`."""
    result = await session.execute(
        select(func.count()).select_from(PortalDocument).where(PortalDocument.section == section)
    )
    return int(result.scalar_one())


@pytest.mark.asyncio
class TestRunningTheInvoiceTasksTwice:
    """`TEST-04`: la segunda corrida no agrega nada."""

    async def test_the_invoices_screen_is_read_once_however_often_it_is_asked_for(
        self, session: AsyncSession
    ) -> None:
        """La misma pantalla, dos veces: un documento en `raw` y cien filas en `staging`."""
        # Arrange
        portal = FakePortal()
        service = PortalService(session, reader_factory=portal)

        # Act
        first = await service.extract_invoices()
        second = await service.extract_invoices()

        # Assert: la segunda se saltea por hash y lo dice devolviendo None.
        assert first is not None
        assert second is None
        assert await documents_of(session, PortalSection.INVOICES) == 1
        rows = await count(session, InvoiceRow)
        invoices = await count(session, Invoice)
        assert rows > 0
        assert invoices > 0

        # Y la tercera tampoco: la idempotencia no es una propiedad del segundo
        # intento, es del enésimo.
        assert await service.extract_invoices() is None
        assert await count(session, InvoiceRow) == rows
        assert await count(session, Invoice) == invoices
        # El portal se visitó las tres veces —el hash sólo se conoce después de
        # leer—, y eso es lo correcto: lo que no se repite es el efecto.
        assert portal.invoice_visits == 3

    async def test_the_file_of_an_invoice_is_stored_once_however_often_it_is_fetched(
        self, session: AsyncSession
    ) -> None:
        """El paso que el camino de precios no tiene, y el que Celery más reintenta."""
        # Arrange: las facturas ya registradas, que es lo que encola la descarga.
        portal = FakePortal()
        service = PortalService(session, reader_factory=portal)
        await service.extract_invoices()

        # Act
        first = await service.extract_invoice_file(AN_INVOICE)
        second = await service.extract_invoice_file(AN_INVOICE)

        # Assert
        assert first is not None
        assert second is None
        assert await documents_of(session, PortalSection.INVOICE_FILE) == 1
        assert await count(session, InvoiceFileRead) == 1
        assert await count(session, InvoiceDocument) == 1

    async def test_the_supplier_register_is_read_once_however_often_it_is_asked_for(
        self, session: AsyncSession
    ) -> None:
        """El padrón no se duplica ni duplica las grafías que da de alta."""
        # Arrange
        portal = FakePortal()
        service = PortalService(session, reader_factory=portal)

        # Act
        first = await service.extract_supplier_ledger()
        second = await service.extract_supplier_ledger()

        # Assert
        assert first is not None
        assert second is None
        assert await documents_of(session, PortalSection.SUPPLIER_LEDGER) == 1
