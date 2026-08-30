"""Facturas y proveedores: identificar sin adivinar, y decidir una vez.

Las tres cosas que el plan de la 004 marca como las que se rompen de verdad:

* **la identificación del proveedor** — una grafía ya asignada entra directo,
  dos que se parecen entre sí van a revisión, y el CUIT impreso no identifica a
  nadie porque es el del cliente;
* **la retroactividad de una asignación** — el número que la pantalla informa
  antes de guardar es el que después se resuelve, y dejarla sin efecto los
  devuelve;
* **el duplicado** — mismo número y proveedor conserva una sola, con otro monto
  va a revisión, y dos sin proveedor identificado **no** son duplicadas.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.modules.purchases.models import Invoice, InvoiceReviewState
from app.modules.purchases.service import PurchasesService
from app.shared.events import NormalizedInvoice, NormalizedSupplier
from tests.factories.purchases_factory import REGISTER, InvoiceFactory, SupplierFactory

pytestmark = [pytest.mark.integration, pytest.mark.database]


def invoice(
    number: str,
    supplier_text: str,
    *,
    total: int = 100_000,
    issued_on: date | None = None,
    **kwargs: object,
) -> NormalizedInvoice:
    """One normalised row of the invoices screen, as `ingestion` publishes it."""
    return NormalizedInvoice(
        staging_row_id=0,
        number=number,
        supplier_text=supplier_text,
        issued_on=issued_on or date(2026, 5, 3),
        total=Decimal(total),
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


class TestTheRegisterIsClosed:
    """H2 y H4: el padrón viene del portal, y no lo amplía una extracción."""

    async def test_it_records_what_the_register_publishes(self, session: AsyncSession) -> None:
        """RF-08: las ocho fichas, con su CUIT y su plazo pactado."""
        # Act
        await register(session)

        # Assert
        listing = await PurchasesService(session).list_suppliers()
        assert listing.total == 8
        first = next(item for item in listing.items if item.legal_name == "Aceros Belgrano SA")
        assert first.tax_id == "30-70918273-4"
        assert first.payment_term_days == 45
        # The register publishes the email and the phone only in the expanded
        # detail; this fixture loads the card without them, and the screen says
        # so instead of showing a blank (RF-15, RF-20).
        assert first.missing == ["email", "phone"]

    async def test_what_the_portal_did_not_publish_is_said_out_loud(
        self, session: AsyncSession
    ) -> None:
        """RF-15, RF-20: lo que falta se marca como falta, no se deja en blanco."""
        # Arrange
        supplier = await SupplierFactory.create(
            session, legal_name="Sin Ficha SA", tax_id=None, payment_term_days=None
        )

        # Act
        read = await PurchasesService(session).get_supplier(supplier.id)

        # Assert
        assert set(read.missing) == {"tax_id", "email", "phone", "payment_term_days"}

    async def test_an_invoice_from_outside_the_register_does_not_create_a_supplier(
        self, session: AsyncSession
    ) -> None:
        """RF-14: se aparta con su motivo, y el padrón sigue teniendo ocho."""
        # Arrange
        await register(session)

        # Act
        await PurchasesService(session).register_invoices(
            batch_id=1, invoices=(invoice("F-0001", "Metalurgica Que No Existe SA"),)
        )

        # Assert
        held = await stored(session, "F-0001")
        assert held.supplier_id is None
        assert held.review_state is InvoiceReviewState.PENDING
        assert (await PurchasesService(session).list_suppliers()).total == 8


class TestIdentifyingTheSupplier:
    """H3: el nombre contra el padrón, y en la duda una persona."""

    async def test_a_spelling_of_the_register_enters_straight(self, session: AsyncSession) -> None:
        """RF-11, RF-12: escrito como el padrón lo escribe, no pregunta nada."""
        # Arrange
        await register(session)

        # Act
        await PurchasesService(session).register_invoices(
            batch_id=1, invoices=(invoice("F-0100", "Aceros Belgrano SA"),)
        )

        # Assert
        resolved = await stored(session, "F-0100")
        assert resolved.supplier_id is not None
        assert resolved.review_state is InvoiceReviewState.OK

    async def test_a_variant_close_enough_is_identified_and_remembered(
        self, session: AsyncSession
    ) -> None:
        """`Aceros Belgano SA` —un error de tipeo— es la misma empresa, y queda aprendida.

        La grafía nueva se guarda como observada, así la próxima factura escrita
        igual no cuesta ni una comparación. Una que sólo difiere en la forma
        legal —`ACEROS BELGRANO S.A.`— ni siquiera llega hasta acá: la
        normalización de nombres de empresa saca `S.A.` y `SRL`, y entra por la
        grafía que el padrón sembró.
        """
        # Arrange
        await register(session)
        service = PurchasesService(session)

        # Act
        await service.register_invoices(
            batch_id=1, invoices=(invoice("F-0101", "Aceros Belgano SA"),)
        )

        # Assert
        assert (await stored(session, "F-0101")).supplier_id is not None
        assert any(
            alias.text_original == "Aceros Belgano SA" for alias in await service.list_aliases()
        )

    async def test_a_name_that_is_nearly_two_suppliers_goes_to_a_person(
        self, session: AsyncSession
    ) -> None:
        """RF-13: parecerse a dos no es identificar, es una moneda al aire.

        Es el riesgo que el plan marca como alto: un proveedor mal resuelto
        rompe la deuda y los totales, y no se nota desde afuera.
        """
        # Arrange — dos razones sociales igual de parecidas al nombre que llega.
        # Las dos superan el umbral: lo que decide que nadie gana es que ninguna
        # está lo bastante por delante de la otra.
        await SupplierFactory.create(session, legal_name="Pinturerias Reunidas Sur SA")
        await SupplierFactory.create(session, legal_name="Pinturerias Reunidas Sud SA")

        # Act
        supplier, reason = await PurchasesService(session).resolve_supplier(
            "Pinturerias Reunidas Su SA"
        )

        # Assert
        assert supplier is None
        assert reason


class TestAssigningASpelling:
    """H8: una decisión sobre una grafía alcanza a todo lo que estaba esperando."""

    async def test_the_preview_promises_the_number_that_then_happens(
        self, session: AsyncSession
    ) -> None:
        """RF-48: contado con la misma consulta que después las resuelve."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(
            batch_id=1,
            invoices=(
                invoice("F-0200", "Metalurgica Rosario"),
                invoice("F-0201", "Metalurgica Rosario"),
                invoice("F-0202", "Otra Cosa SRL"),
            ),
        )
        target = (await service.list_suppliers()).items[0]

        # Act
        preview = await service.preview_alias(text="Metalurgica Rosario", supplier_id=target.id)
        saved = await service.save_alias(
            text="Metalurgica Rosario", supplier_id=target.id, actor_user_id=1
        )

        # Assert
        assert preview.invoices == 2
        assert saved.invoices == preview.invoices
        assert sorted(saved.numbers) == ["F-0200", "F-0201"]

    async def test_dropping_it_gives_back_exactly_what_it_resolved(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-52, RF-53: y no toca lo que alguien decidió una por una."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(
            batch_id=1,
            invoices=(invoice("F-0300", "Metalurgica Rosario"), invoice("F-0301", "Otra Cosa")),
        )
        target = (await service.list_suppliers()).items[0]
        await service.save_alias(
            text="Metalurgica Rosario", supplier_id=target.id, actor_user_id=owner.id
        )
        by_hand = await stored(session, "F-0301")
        await service.resolve_invoice(
            by_hand.id, supplier_id=target.id, remember=False, actor_user_id=owner.id
        )
        alias = next(
            item
            for item in await service.list_aliases()
            if item.text_original == "Metalurgica Rosario"
        )

        # Act
        returned = await service.drop_alias(alias.id)

        # Assert
        assert returned == 1
        assert (await stored(session, "F-0300")).review_state is InvoiceReviewState.PENDING
        assert (await stored(session, "F-0301")).supplier_id == target.id


class TestDuplicates:
    """H7: la misma factura dos veces, y la que repite número con otro monto."""

    async def test_the_same_invoice_twice_is_kept_once_and_counted(
        self, session: AsyncSession
    ) -> None:
        """RF-38, RF-39."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        row = invoice("F-0400", "Aceros Belgrano SA", total=50_000)

        # Act
        await service.register_invoices(batch_id=1, invoices=(row,))
        await service.register_invoices(batch_id=2, invoices=(row,))

        # Assert
        found = (
            (await session.execute(select(Invoice).where(Invoice.number == "F-0400")))
            .scalars()
            .all()
        )
        assert len(found) == 1
        assert found[0].arrival_count == 2

    async def test_the_same_number_with_another_total_goes_to_a_person(
        self, session: AsyncSession
    ) -> None:
        """RF-37: no es la misma factura, y no es una decisión de la plataforma."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(
            batch_id=1, invoices=(invoice("F-0500", "Aceros Belgrano SA", total=50_000),)
        )

        # Act
        await service.register_invoices(
            batch_id=2, invoices=(invoice("F-0500", "Aceros Belgrano SA", total=51_000),)
        )

        # Assert
        held = await stored(session, "F-0500")
        assert held.review_state is InvoiceReviewState.PENDING
        assert held.review_reason

    async def test_two_without_a_supplier_are_not_duplicates_of_each_other(
        self, session: AsyncSession
    ) -> None:
        """RF-40: mientras el proveedor no está resuelto, no es duplicada de nadie."""
        # Arrange
        await register(session)

        # Act
        await PurchasesService(session).register_invoices(
            batch_id=1,
            invoices=(
                invoice("F-0600", "Uno Que No Esta SA"),
                invoice("F-0600", "Otro Que Tampoco SRL"),
            ),
        )

        # Assert
        found = (
            (await session.execute(select(Invoice).where(Invoice.number == "F-0600")))
            .scalars()
            .all()
        )
        assert len(found) == 2
        assert all(item.supplier_id is None for item in found)


class TestWhatTheDocumentSaid:
    """H6: la comparación entre el archivo y la tabla es la señal de la feature."""

    async def test_a_document_that_agrees_leaves_the_invoice_alone(
        self, session: AsyncSession
    ) -> None:
        """RF-27: coincide, entra sin molestar a nadie."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(
            batch_id=1, invoices=(invoice("F-0700", "Aceros Belgrano SA"),)
        )

        # Act
        await service.record_document(
            invoice_number="F-0700",
            raw_document_id=1,
            readable=True,
            agrees=True,
            excerpt="FACTURA F-0700",
            reason=None,
            number="F-0700",
            issued_on=date(2026, 5, 3),
            total=Decimal(100_000),
            supplier_text="Aceros Belgrano SA",
        )

        # Assert
        assert (await stored(session, "F-0700")).review_state is InvoiceReviewState.OK

    async def test_a_document_that_disagrees_holds_it_with_the_excerpt(
        self, session: AsyncSession
    ) -> None:
        """RF-29, RF-30: y el recorte queda a la vista de quien decide."""
        # Arrange
        await register(session)
        service = PurchasesService(session)
        await service.register_invoices(
            batch_id=1, invoices=(invoice("F-0800", "Aceros Belgrano SA"),)
        )

        # Act
        await service.record_document(
            invoice_number="F-0800",
            raw_document_id=1,
            readable=True,
            agrees=False,
            excerpt="Monto total: $999.999",
            reason=None,
            number="F-0800",
            issued_on=date(2026, 5, 3),
            total=Decimal(999_999),
            supplier_text="Aceros Belgrano SA",
        )

        # Assert
        held = await service.get_invoice((await stored(session, "F-0800")).id)
        assert held.review_state is InvoiceReviewState.PENDING
        assert held.document is not None
        assert held.document.excerpt == "Monto total: $999.999"


class TestTheDueDateComesFromTheAgreedTerm:
    """H5 de 005 mirado desde acá: la fecha sale del plazo y de nada más."""

    async def test_it_is_the_invoice_date_plus_the_agreed_term(self, session: AsyncSession) -> None:
        """RF-26 de 005: `Aceros Belgrano SA` pactó 45 días."""
        # Arrange
        await register(session)

        # Act
        await PurchasesService(session).register_invoices(
            batch_id=1,
            invoices=(invoice("F-0900", "Aceros Belgrano SA", issued_on=date(2026, 5, 3)),),
        )

        # Assert
        assert (await stored(session, "F-0900")).due_on == date(2026, 6, 17)

    async def test_without_an_agreed_term_the_date_the_table_published_stands_in(
        self, session: AsyncSession
    ) -> None:
        """Una fecha que existe vale más que ninguna, y se corrige al leer el plazo."""
        # Arrange
        supplier = await SupplierFactory.create(
            session, legal_name="Sin Plazo SA", payment_term_days=None
        )

        # Act
        held = await InvoiceFactory.create(
            session, supplier=supplier, due_on=date(2026, 7, 1), number="F-1000"
        )

        # Assert
        assert held.due_on == date(2026, 7, 1)
