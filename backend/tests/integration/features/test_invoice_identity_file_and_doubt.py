"""Los tres requisitos firmados de la 004 que el converge encontró sin construir.

* **RF-11 — el CUIT identifica.** La tabla del portal no publica ninguno, así que
  el único lugar del que puede salir es el archivo, y el archivo llega después
  de la fila. La factura que nadie pudo atribuir por el nombre se resuelve sola
  cuando su documento trae un CUIT del padrón, sin que una persona la mire.
* **RF-04 — se abre el original.** El archivo tal como lo mandó el proveedor, con
  su tipo, y no una transcripción de lo que el lector entendió.
* **RF-31 — lo dudoso se confirma o se corrige.** Los tres datos de cabecera se
  escriben desde la revisión, con quién los escribió y qué decían antes; y dejar
  uno como está es confirmarlo, que es la respuesta más frecuente y por eso la
  que no cuesta nada.

Lo que **no** se prueba acá y sigue probándose donde estaba: la identificación
por nombre, el duplicado y la retroactividad de una grafía viven en
`test_invoices_and_suppliers.py`.
"""

from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.modules.operations.models import AuditEntry
from app.modules.purchases.models import Invoice, InvoiceReviewState
from app.modules.purchases.service import NO_INVOICE_FILE, PurchasesService
from app.modules.triage.models import CaseStatus, ExceptionCase
from app.modules.triage.service import UNREADABLE_INVOICE_ROW
from app.shared.errors import ConflictError, NotFoundError
from app.shared.events import (
    InvoiceRowsQuarantined,
    NormalizedInvoice,
    NormalizedSupplier,
    QuarantinedRow,
    events,
)
from tests.conftest import API_PREFIX
from tests.factories.purchases_factory import REGISTER

pytestmark = [pytest.mark.integration, pytest.mark.database]

# Un proveedor del padrón, y su CUIT escrito de las dos formas en que se imprime.
BELGRANO = "Aceros Belgrano SA"
BELGRANO_TAX_ID = "30-70918273-4"
BELGRANO_TAX_ID_PLAIN = "30709182734"
# El de Cordillera, el cliente: está impreso en las facturas y no es de nadie
# del padrón, que es exactamente lo que impide que identifique.
CLIENT_TAX_ID = "30-71234567-8"

A_PDF = b"%PDF-1.4 lo que mando el proveedor"
PDF_TYPE = "application/pdf"


def invoice(number: str, supplier_text: str, **kwargs: object) -> NormalizedInvoice:
    """One normalised row of the invoices screen, as `ingestion` publishes it."""
    return NormalizedInvoice(
        staging_row_id=0,
        number=number,
        supplier_text=supplier_text,
        issued_on=kwargs.pop("issued_on", None) or date(2026, 5, 3),  # type: ignore[arg-type]
        total=Decimal(str(kwargs.pop("total", 100_000))),
        **kwargs,
    )


async def register(session: AsyncSession) -> None:
    """Load the register the way `/estado-cuenta` does, through the service."""
    await PurchasesService(session).remember_suppliers(
        tuple(
            NormalizedSupplier(legal_name=name, tax_id=tax_id, payment_term_days=term)
            for name, tax_id, term in REGISTER
        )
    )


async def stored(session: AsyncSession, number: str) -> Invoice:
    """The invoice with this number, as it ended up in `core`."""
    found = (
        (await session.execute(select(Invoice).where(Invoice.number == number))).scalars().first()
    )
    assert found is not None
    return found


async def document_arrives(
    service: PurchasesService,
    number: str,
    *,
    tax_id: str | None = None,
    agrees: bool = True,
    content: bytes | None = A_PDF,
    **read: object,
) -> None:
    """The file of an invoice comes back read, the way `ingestion` publishes it."""
    await service.record_document(
        invoice_number=number,
        raw_document_id=1,
        readable=True,
        agrees=agrees,
        excerpt="FACTURA",
        reason=None,
        number=read.get("read_number"),  # type: ignore[arg-type]
        issued_on=read.get("read_issued_on"),  # type: ignore[arg-type]
        total=read.get("read_total"),  # type: ignore[arg-type]
        supplier_text=None,
        supplier_tax_id=tax_id,
        content=content,
        content_type=PDF_TYPE if content else None,
    )


class TestTheTaxIdIdentifies:
    """RF-11: cuando la factura trae el CUIT del proveedor, no lo decide nadie."""

    async def test_a_held_invoice_is_resolved_by_the_tax_id_its_document_printed(
        self, session: AsyncSession
    ) -> None:
        """Y sin pasar por una persona: nadie la mira y sale de la cola."""
        # Arrange — un nombre que no se parece a ninguno de los ocho.
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(
            batch_id=1, invoices=(invoice("F-1100", "Sociedad Anonima Sin Nombre Parecido"),)
        )
        held = await stored(session, "F-1100")
        assert held.review_state is InvoiceReviewState.PENDING

        # Act
        await document_arrives(service, "F-1100", tax_id=BELGRANO_TAX_ID)

        # Assert
        resolved = await stored(session, "F-1100")
        supplier = await service.purchases.supplier(resolved.supplier_id or 0)
        assert supplier is not None and supplier.legal_name == BELGRANO
        assert resolved.review_state is InvoiceReviewState.OK
        assert resolved.review_reason is None
        # Nadie lo decidió: lo decidió un número que no admite interpretación.
        assert resolved.resolved_by_user_id is None

    async def test_the_tax_id_is_matched_without_its_punctuation(
        self, session: AsyncSession
    ) -> None:
        """`30-70918273-4` y `30709182734` son el mismo número."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(
            batch_id=1, invoices=(invoice("F-1101", "Sociedad Anonima Sin Nombre Parecido"),)
        )

        # Act
        await document_arrives(service, "F-1101", tax_id=BELGRANO_TAX_ID_PLAIN)

        # Assert
        assert (await stored(session, "F-1101")).review_state is InvoiceReviewState.OK

    async def test_the_tax_id_of_the_client_identifies_nobody(self, session: AsyncSession) -> None:
        """La trampa que el relevamiento midió, cerrada por el padrón.

        Aunque el número se colara hasta acá, Cordillera **no está en el padrón**,
        así que no coincide con nadie y la factura sigue esperando a una persona.
        Es la segunda barrera, y no una repetición de la primera: la del lector
        depende de cómo esté escrito el documento, y ésta no depende de nada.
        """
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(
            batch_id=1, invoices=(invoice("F-1102", "Sociedad Anonima Sin Nombre Parecido"),)
        )

        # Act
        await document_arrives(service, "F-1102", tax_id=CLIENT_TAX_ID)

        # Assert
        still_held = await stored(session, "F-1102")
        assert still_held.review_state is InvoiceReviewState.PENDING
        assert still_held.supplier_id is None

    async def test_it_does_not_touch_an_invoice_held_over_a_number(
        self, session: AsyncSession
    ) -> None:
        """Un CUIT contesta de quién es la factura, no cuánto dice."""
        # Arrange — se resuelve sola por el nombre, y después el archivo discrepa.
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(batch_id=1, invoices=(invoice("F-1103", BELGRANO),))
        await document_arrives(service, "F-1103", agrees=False)
        assert (await stored(session, "F-1103")).review_state is InvoiceReviewState.PENDING

        # Act — llega otra lectura, ahora con un CUIT del padrón.
        await document_arrives(service, "F-1103", tax_id=BELGRANO_TAX_ID, agrees=False)

        # Assert — sigue esperando: la duda era sobre el monto, no sobre el dueño.
        assert (await stored(session, "F-1103")).review_state is InvoiceReviewState.PENDING

    async def test_the_due_date_is_recalculated_from_the_term_of_that_supplier(
        self, session: AsyncSession
    ) -> None:
        """Hasta acá no había plazo con el que calcularlo (RF-26 de 005)."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(
            batch_id=1,
            invoices=(
                invoice(
                    "F-1104",
                    "Sociedad Anonima Sin Nombre Parecido",
                    issued_on=date(2026, 5, 3),
                ),
            ),
        )

        # Act
        await document_arrives(service, "F-1104", tax_id=BELGRANO_TAX_ID)

        # Assert — 45 días, que es el plazo pactado de Belgrano en el padrón.
        assert (await stored(session, "F-1104")).due_on == date(2026, 6, 17)


class TestTheOriginalFile:
    """RF-04: el archivo como lo mandó el proveedor, no una transcripción."""

    async def test_it_gives_back_the_bytes_the_portal_delivered(
        self, session: AsyncSession
    ) -> None:
        """Con su tipo y con un nombre que se puede buscar en una carpeta."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(batch_id=1, invoices=(invoice("F-1200", BELGRANO),))
        await document_arrives(service, "F-1200")
        registered = await stored(session, "F-1200")

        # Act
        served = await service.invoice_file(registered.id)

        # Assert
        assert served.content == A_PDF
        assert served.content_type == PDF_TYPE
        assert served.filename == "Factura F-1200.pdf"

    async def test_an_invoice_whose_file_never_arrived_says_so(self, session: AsyncSession) -> None:
        """Y no devuelve cero bytes con un `200`, que un navegador lee como roto."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(batch_id=1, invoices=(invoice("F-1201", BELGRANO),))
        registered = await stored(session, "F-1201")

        # Act / Assert
        with pytest.raises(NotFoundError) as raised:
            await service.invoice_file(registered.id)
        assert NO_INVOICE_FILE in str(raised.value)

    async def test_over_http_it_comes_back_as_a_file_and_not_as_text(
        self, session: AsyncSession, purchasing_client: AsyncClient
    ) -> None:
        """Con su tipo y su `Content-Disposition`: es lo que hace que se abra.

        Sobre HTTP y no sólo sobre el servicio porque lo que RF-04 promete es
        *abrir* el archivo, y eso lo decide la respuesta, no el valor que
        devuelve una función.
        """
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(batch_id=1, invoices=(invoice("F-1202", BELGRANO),))
        await document_arrives(service, "F-1202")
        await session.commit()
        registered = await stored(session, "F-1202")

        # Act
        response = await purchasing_client.get(f"{API_PREFIX}/invoices/{registered.id}/file")

        # Assert
        assert response.status_code == 200
        assert response.content == A_PDF
        assert response.headers["content-type"].startswith(PDF_TYPE)
        assert "Factura F-1202.pdf" in response.headers["content-disposition"]

    async def test_sales_does_not_reach_the_file_of_a_purchase_invoice(
        self, session: AsyncSession, sales_client: AsyncClient
    ) -> None:
        """RF-06: la matriz lo frena, y el archivo no es una puerta de atrás."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(batch_id=1, invoices=(invoice("F-1203", BELGRANO),))
        await document_arrives(service, "F-1203")
        await session.commit()
        registered = await stored(session, "F-1203")

        # Act
        response = await sales_client.get(f"{API_PREFIX}/invoices/{registered.id}/file")

        # Assert
        assert response.status_code == 403


class TestConfirmingOrCorrectingWhatIsInDoubt:
    """RF-31: el dato en duda lo escribe una persona, y queda dicho quién."""

    async def test_the_corrected_total_is_the_total_of_the_invoice(
        self, session: AsyncSession, owner: User
    ) -> None:
        """El criterio firmado: confirmado el total, la factura muestra ese total."""
        # Arrange — el archivo dice otra cosa que la tabla, así que va a revisión.
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(
            batch_id=1, invoices=(invoice("F-1300", BELGRANO, total=100_000),)
        )
        await document_arrives(service, "F-1300", agrees=False, read_total=Decimal("442965"))
        held = await stored(session, "F-1300")

        # Act
        read = await service.resolve_invoice(
            held.id,
            supplier_id=None,
            remember=False,
            actor_user_id=owner.id,
            total=Decimal("442965"),
        )

        # Assert
        assert read.total == Decimal("442965")
        assert (await stored(session, "F-1300")).total == Decimal("442965")
        assert read.review_state is InvoiceReviewState.RESOLVED

    async def test_it_records_who_corrected_it_and_what_it_said_before(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-18 y RF-32, por el mismo camino que una corrección de proveedor."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(
            batch_id=1, invoices=(invoice("F-1301", BELGRANO, total=100_000),)
        )
        await document_arrives(service, "F-1301", agrees=False)
        held = await stored(session, "F-1301")

        # Act
        await service.resolve_invoice(
            held.id,
            supplier_id=None,
            remember=False,
            actor_user_id=owner.id,
            total=Decimal("442965"),
        )

        # Assert
        entries = (
            (await session.execute(select(AuditEntry).where(AuditEntry.entity_id == str(held.id))))
            .scalars()
            .all()
        )
        written = [entry for entry in entries if entry.field == "total"]
        assert len(written) == 1
        assert written[0].actor_user_id == owner.id
        assert written[0].old_value == "100000.0000"
        assert written[0].new_value == "442965"

    async def test_leaving_a_field_alone_confirms_it_and_records_nothing(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Confirmar es la respuesta más frecuente y por eso no cuesta nada.

        Y no escribe en la bitácora: nadie corrigió nada, y una bitácora que
        registra el acuerdo con el portal deja de servir para encontrar en qué
        se lo contradijo.
        """
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(
            batch_id=1, invoices=(invoice("F-1302", BELGRANO, total=100_000),)
        )
        await document_arrives(service, "F-1302", agrees=False)
        held = await stored(session, "F-1302")

        # Act — se manda el mismo total que ya tenía.
        await service.resolve_invoice(
            held.id,
            supplier_id=None,
            remember=False,
            actor_user_id=owner.id,
            total=Decimal("100000"),
        )

        # Assert
        assert (await stored(session, "F-1302")).total == Decimal("100000")
        entries = (
            (await session.execute(select(AuditEntry).where(AuditEntry.entity_id == str(held.id))))
            .scalars()
            .all()
        )
        assert entries == []

    async def test_correcting_the_date_moves_the_due_date_and_the_calendar(
        self, session: AsyncSession, owner: User
    ) -> None:
        """El vencimiento sale de la fecha de la factura y del plazo pactado."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(
            batch_id=1, invoices=(invoice("F-1303", BELGRANO, issued_on=date(2026, 5, 3)),)
        )
        await document_arrives(service, "F-1303", agrees=False)
        held = await stored(session, "F-1303")

        # Act — era el 3 de mayo y en realidad decía el 3 de enero.
        await service.resolve_invoice(
            held.id,
            supplier_id=None,
            remember=False,
            actor_user_id=owner.id,
            issued_on=date(2026, 1, 3),
        )

        # Assert — 45 días desde la fecha nueva, y el vencimiento del calendario
        # con ella.
        corrected = await stored(session, "F-1303")
        assert corrected.issued_on == date(2026, 1, 3)
        assert corrected.due_on == date(2026, 2, 17)
        entry = await service.purchases.due_date_of_invoice(corrected.id)
        assert entry is not None and entry.on_date == date(2026, 2, 17)

    async def test_a_number_that_belongs_to_another_invoice_is_refused(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Con una frase, y no con un error de integridad de la base."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(
            batch_id=1,
            invoices=(invoice("F-1304", BELGRANO), invoice("F-1305", BELGRANO)),
        )
        await document_arrives(service, "F-1305", agrees=False)
        held = await stored(session, "F-1305")

        # Act / Assert
        with pytest.raises(ConflictError):
            await service.resolve_invoice(
                held.id,
                supplier_id=None,
                remember=False,
                actor_user_id=owner.id,
                number="F-1304",
            )

    async def test_the_correction_and_the_supplier_travel_together(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Quien decide mira una sola vez el recorte y contesta las dos preguntas."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(
            batch_id=1, invoices=(invoice("F-1306", "Metalurgica Rosario", total=100_000),)
        )
        held = await stored(session, "F-1306")
        assert held.review_state is InvoiceReviewState.PENDING
        target = next(item for item in (await service.list_suppliers()).items)

        # Act
        read = await service.resolve_invoice(
            held.id,
            supplier_id=target.id,
            remember=True,
            actor_user_id=owner.id,
            total=Decimal("442965"),
        )

        # Assert
        assert read.total == Decimal("442965")
        assert read.supplier_id == target.id
        assert read.review_state is InvoiceReviewState.RESOLVED
        # Y la grafía quedó guardada, que es lo que hace que no se vuelva a preguntar.
        assert any(
            alias.text_original == "Metalurgica Rosario" for alias in await service.list_aliases()
        )


class TestARowNobodyCouldInterpret:
    """RF-07, RF-34 y el Artículo II sobre la fila que no se pudo tipar."""

    async def test_it_opens_a_case_instead_of_stopping_in_quarantine(
        self, session: AsyncSession
    ) -> None:
        """El agujero que el converge encontró: se publicaba y nadie escuchaba.

        La fila quedaba en cuarentena en `staging` y ahí terminaba: no se
        contaba, no se veía y nadie la decidía — el silencio que el artículo
        existe para prohibir. Sus dos hermanas del lado de los precios abren caso
        desde la 001.
        """
        # Act
        await events.publish(
            InvoiceRowsQuarantined(
                batch_id=7,
                cases=(
                    QuarantinedRow(
                        staging_row_id=99,
                        reason="La fila no tiene monto",
                        excerpt="Aceros Belgrano SA;F-9000;;;",
                    ),
                ),
            ),
            session,
        )

        # Assert
        opened = (
            (
                await session.execute(
                    select(ExceptionCase).where(ExceptionCase.kind == UNREADABLE_INVOICE_ROW)
                )
            )
            .scalars()
            .all()
        )
        assert len(opened) == 1
        assert opened[0].status is CaseStatus.PENDING
        assert opened[0].reason == "La fila no tiene monto"
        assert opened[0].payload["excerpt"] == "Aceros Belgrano SA;F-9000;;;"


class TestWhatTheTotalsLeaveOut:
    """RF-23: cuántas quedaron afuera **por estar en revisión**, y no en total."""

    async def test_the_three_reasons_are_counted_apart(self, session: AsyncSession) -> None:
        """Sumarlas hacía que el número dejara de contestar lo que RF-23 pregunta.

        Con período elegido, «quedaron afuera 3» sobre un proveedor con una
        factura en revisión y dos del año pasado es verdad sobre nada que nadie
        haya preguntado.
        """
        # Arrange — una en revisión, una vieja, una dentro del período.
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(
            batch_id=1,
            invoices=(
                invoice("F-1400", BELGRANO, issued_on=date(2026, 5, 3)),
                invoice("F-1401", BELGRANO, issued_on=date(2024, 5, 3)),
                invoice("F-1402", "Nombre Que No Se Parece A Nadie SA", issued_on=date(2026, 5, 3)),
            ),
        )
        target = next(
            item for item in (await service.list_suppliers()).items if item.legal_name == BELGRANO
        )
        held = await stored(session, "F-1402")
        held.supplier_id = target.id
        await session.flush()

        # Act
        totals = await service.supplier_totals(
            target.id, since=date(2026, 1, 1), until=date(2026, 12, 31)
        )

        # Assert
        assert totals.invoices == 1
        assert totals.excluded_in_review == 1
        assert totals.excluded_out_of_period == 1
        assert totals.excluded_inconsistent == 0
        assert totals.excluded == 2


class TestNamingWhoDecided:
    """RF-32 y RF-51: el id se guarda acá y el nombre lo pone `identity`."""

    async def test_the_invoice_says_who_resolved_it_and_when(
        self, session: AsyncSession, owner: User, purchasing_client: AsyncClient
    ) -> None:
        """Se guardaba desde el primer día y no salía en la respuesta."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(
            batch_id=1, invoices=(invoice("F-1500", "Nombre Que No Se Parece A Nadie SA"),)
        )
        held = await stored(session, "F-1500")
        target = next(item for item in (await service.list_suppliers()).items)
        await service.resolve_invoice(
            held.id, supplier_id=target.id, remember=False, actor_user_id=owner.id
        )
        await session.commit()

        # Act
        response = await purchasing_client.get(f"{API_PREFIX}/invoices/{held.id}")

        # Assert
        body = response.json()
        assert body["resolved_by_user_id"] == owner.id
        assert body["resolved_by_name"]
        assert body["resolved_at"]

    async def test_the_spelling_says_who_assigned_it(
        self, session: AsyncSession, owner: User, purchasing_client: AsyncClient
    ) -> None:
        """RF-51 pide «quién y cuándo», y la pantalla sólo podía decir cuándo."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        target = next(item for item in (await service.list_suppliers()).items)
        await service.save_alias(
            text="Metalurgica Rosario", supplier_id=target.id, actor_user_id=owner.id
        )
        await session.commit()

        # Act
        response = await purchasing_client.get(f"{API_PREFIX}/supplier-aliases")

        # Assert
        assigned = [
            alias for alias in response.json() if alias["text_original"] == "Metalurgica Rosario"
        ]
        assert len(assigned) == 1
        assert assigned[0]["created_by_user_id"] == owner.id
        assert assigned[0]["created_by_name"]
