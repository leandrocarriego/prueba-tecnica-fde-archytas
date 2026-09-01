"""Cargar a mano lo que el portal publicó roto, y qué pasa cuando lo publica bien.

La 011 cerró la primera mitad del Artículo II: una fila que el portal publica
ilegible ya no se pierde en silencio, se aparta y se muestra. Faltaba la otra —
**dejar arreglarla**. Hasta acá lo único que se podía hacer con esa fila era
darla por revisada: la factura no entraba a ningún total, no aparecía en el
calendario de vencimientos, y avisar sin dejar arreglar es la mitad de una
promesa.

Lo que se agrega tiene una consecuencia que no es evidente y que es la mayor
parte de este archivo: **el portal puede publicar más adelante esa misma fila,
ya legible y distinta**. Ninguno de los dos gana solo. Pisar lo cargado a mano
tira trabajo hecho sin avisar; dejarlo ganar deja la plataforma discrepando del
origen sin que nadie se entere. Así que el registro se aparta —fuera de todos
los totales, como cualquier dato dudoso— y la diferencia se pregunta con los dos
valores al lado. Decisión del dueño, 2026-09-01.

Y una vuelta más, que es la que se rompe sin ruido: contestada la pregunta a
favor de lo cargado a mano, **el portal sigue publicando su fila cada doce
horas**. Sin memoria de lo rechazado, la misma pregunta ya contestada volvería
con cada lectura hasta que alguien se rinda.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.modules.purchases.models import Invoice, InvoiceReviewState, RecordOrigin
from app.modules.purchases.service import DISPUTED_BY_PORTAL, PurchasesService
from app.modules.triage.models import CaseStatus, ExceptionCase
from app.modules.triage.service import (
    DISPUTED_INVOICE,
    INVOICE_ORIGIN,
    UNREADABLE_INVOICE_ROW,
    TriageService,
)
from app.shared.errors import ConflictError
from app.shared.events import NormalizedInvoice
from app.shared.sections import BusinessSection
from tests.factories.purchases_factory import SupplierFactory

pytestmark = [pytest.mark.integration, pytest.mark.database]

EVERY_AREA = frozenset(BusinessSection)

# La fila de la captura: el número se lee, el total y la fecha no.
EXCERPT = "FC A 0001-00099999   ???   $ --"
NUMBER = "0001-00099999"
SUPPLIER = "Ferrum Andina SA"


async def cases_of(session: AsyncSession, kind: str) -> list[ExceptionCase]:
    """Los casos de una clase, en el orden en que se abrieron."""
    result = await session.execute(
        select(ExceptionCase).where(ExceptionCase.kind == kind).order_by(ExceptionCase.id)
    )
    return list(result.scalars().all())


async def an_unreadable_row(session: AsyncSession) -> ExceptionCase:
    """El pendiente que abre una fila de facturas que nadie pudo interpretar."""
    await TriageService(session).open_case(
        kind=UNREADABLE_INVOICE_ROW,
        section=BusinessSection.PURCHASING,
        reason="La fila de facturas no se pudo interpretar",
        payload={"staging_row_id": 7, "excerpt": EXCERPT, "origin": INVOICE_ORIGIN},
        key="7",
    )
    return (await cases_of(session, UNREADABLE_INVOICE_ROW))[0]


def portal_row(total: int, *, issued_on: date | None = None) -> NormalizedInvoice:
    """La misma factura, como la publica el portal el día que se puede leer."""
    return NormalizedInvoice(
        staging_row_id=7,
        number=NUMBER,
        supplier_text=SUPPLIER,
        issued_on=issued_on or date(2026, 8, 30),
        total=Decimal(total),
    )


async def stored(session: AsyncSession) -> Invoice:
    """La factura, como quedó en `core`."""
    found = (
        (await session.execute(select(Invoice).where(Invoice.number == NUMBER))).scalars().first()
    )
    assert found is not None
    return found


class TestLoadingByHandWhatCouldNotBeRead:
    """La otra mitad del Artículo II: el sistema avisa **y** deja arreglarlo."""

    async def test_a_row_nobody_could_read_becomes_an_invoice(
        self, session: AsyncSession, owner: User
    ) -> None:
        """La persona mira el papel, la escribe, y la factura entra."""
        # Arrange
        supplier = await SupplierFactory.create(
            session, legal_name=SUPPLIER, tax_id="30-71042588-4", payment_term_days=30
        )
        case = await an_unreadable_row(session)

        # Act
        await TriageService(session).resolve(
            case.id,
            decision={
                "action": "load",
                "number": NUMBER,
                "issued_on": "2026-08-30",
                "total": "152400",
                "supplier_id": supplier.id,
            },
            user_id=owner.id,
            user_name=owner.name,
            remember=False,
            visible=EVERY_AREA,
        )

        # Assert — entró, y entró diciendo que la escribió una persona.
        invoice = await stored(session)
        assert invoice.total == Decimal("152400")
        assert invoice.origin is RecordOrigin.MANUAL
        assert invoice.review_state is InvoiceReviewState.RESOLVED
        assert invoice.resolved_by_user_id == owner.id
        # El vencimiento no se escribió: sale del plazo pactado, como el de
        # cualquier otra (RF-26 de 005).
        assert invoice.due_on == date(2026, 9, 29)

    async def test_a_number_already_registered_leaves_the_case_pending(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Y el caso no se cierra: el handler corre en la transacción del que resolvió.

        Es `GEN-09` puesto a prueba con el caso que de verdad pasa: dos personas
        mirando la misma cola, y la segunda cargando lo que la primera ya cargó.
        Si la escritura se rechaza y el caso igual se cerrara, el pendiente
        desaparecería sin que nada haya entrado.
        """
        # Arrange — la factura ya está (la cargó otro), y llega el mismo pendiente.
        supplier = await SupplierFactory.create(
            session, legal_name=SUPPLIER, tax_id="30-71042588-4", payment_term_days=30
        )
        await PurchasesService(session).register_invoice_by_hand(
            number=NUMBER,
            issued_on=date(2026, 8, 30),
            total=Decimal("152400"),
            supplier_id=supplier.id,
            actor_user_id=owner.id,
        )
        case = await an_unreadable_row(session)
        await session.commit()

        # Act
        with pytest.raises(ConflictError):
            await TriageService(session).resolve(
                case.id,
                decision={
                    "action": "load",
                    "number": NUMBER,
                    "issued_on": "2026-08-30",
                    "total": "152400",
                    "supplier_id": supplier.id,
                },
                user_id=owner.id,
                remember=False,
                visible=EVERY_AREA,
            )

        # Assert — el pendiente sigue ahí, porque no entró nada.
        await session.rollback()
        assert (await cases_of(session, UNREADABLE_INVOICE_ROW))[0].status is CaseStatus.PENDING


class TestWhenThePortalFinallyPublishesIt:
    """Ninguno de los dos gana solo, y la pregunta se hace una sola vez."""

    async def loaded_by_hand(self, session: AsyncSession, owner: User) -> Invoice:
        """Una factura que una persona reconstruyó, con total 152.400."""
        supplier = await SupplierFactory.create(
            session, legal_name=SUPPLIER, tax_id="30-71042588-4", payment_term_days=30
        )
        return await PurchasesService(session).register_invoice_by_hand(
            number=NUMBER,
            issued_on=date(2026, 8, 30),
            total=Decimal("152400"),
            supplier_id=supplier.id,
            actor_user_id=owner.id,
        )

    async def test_a_different_total_asks_which_one_stays(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Se aparta sin pisar nada, y el caso lleva los dos valores."""
        # Arrange
        await self.loaded_by_hand(session, owner)

        # Act — el portal publica la fila, ya legible, con otro total.
        await PurchasesService(session).register_invoices(
            batch_id=1, invoices=(portal_row(160000),)
        )

        # Assert — apartada, sin haber pisado el total que escribió la persona.
        invoice = await stored(session)
        assert invoice.review_state is InvoiceReviewState.PENDING
        assert invoice.review_reason == DISPUTED_BY_PORTAL
        assert invoice.total == Decimal("152400")

        # Y la pregunta, con los dos valores al lado.
        cases = await cases_of(session, DISPUTED_INVOICE)
        assert len(cases) == 1
        # Comparados como plata y no como texto: los dos lados se guardan con la
        # escala de la columna, y lo que la prueba mira es el importe.
        assert Decimal(cases[0].payload["typed"]["total"]) == Decimal("152400")
        assert Decimal(cases[0].payload["published"]["total"]) == Decimal("160000")

    async def test_keeping_the_portal_values_writes_them(
        self, session: AsyncSession, owner: User
    ) -> None:
        """«Queda lo del portal» escribe lo del portal, y el origen pasa a serlo."""
        # Arrange
        await self.loaded_by_hand(session, owner)
        await PurchasesService(session).register_invoices(
            batch_id=1, invoices=(portal_row(160000),)
        )
        case = (await cases_of(session, DISPUTED_INVOICE))[0]

        # Act
        await TriageService(session).resolve(
            case.id,
            decision={"keep": "portal"},
            user_id=owner.id,
            remember=False,
            visible=EVERY_AREA,
        )

        # Assert
        invoice = await stored(session)
        assert invoice.total == Decimal("160000")
        assert invoice.origin is RecordOrigin.PORTAL
        assert invoice.review_state is InvoiceReviewState.RESOLVED

    async def test_keeping_what_was_typed_does_not_ask_again(
        self, session: AsyncSession, owner: User
    ) -> None:
        """La lectura de mañana no reabre la discusión que se contestó hoy.

        El portal republica su fila cada doce horas. Sin memoria de lo
        rechazado, la misma pregunta volvería con cada lectura, y una pregunta
        que vuelve después de contestada enseña a ignorar la cola.
        """
        # Arrange
        await self.loaded_by_hand(session, owner)
        purchases = PurchasesService(session)
        await purchases.register_invoices(batch_id=1, invoices=(portal_row(160000),))
        case = (await cases_of(session, DISPUTED_INVOICE))[0]
        await TriageService(session).resolve(
            case.id,
            decision={"keep": "manual"},
            user_id=owner.id,
            remember=False,
            visible=EVERY_AREA,
        )

        # Act — el portal vuelve a publicar exactamente lo mismo.
        await purchases.register_invoices(batch_id=2, invoices=(portal_row(160000),))

        # Assert — sigue lo que escribió la persona, y no hay pregunta nueva.
        invoice = await stored(session)
        assert invoice.total == Decimal("152400")
        assert invoice.origin is RecordOrigin.MANUAL
        assert invoice.review_state is InvoiceReviewState.RESOLVED
        assert len(await cases_of(session, DISPUTED_INVOICE)) == 1

    async def test_the_portal_changing_its_mind_again_does_ask(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Lo que se rechazó fue **un** valor, no toda discusión futura."""
        # Arrange
        await self.loaded_by_hand(session, owner)
        purchases = PurchasesService(session)
        await purchases.register_invoices(batch_id=1, invoices=(portal_row(160000),))
        case = (await cases_of(session, DISPUTED_INVOICE))[0]
        await TriageService(session).resolve(
            case.id,
            decision={"keep": "manual"},
            user_id=owner.id,
            remember=False,
            visible=EVERY_AREA,
        )

        # Act — ahora el portal dice otra cosa distinta.
        await purchases.register_invoices(batch_id=2, invoices=(portal_row(171000),))

        # Assert
        cases = await cases_of(session, DISPUTED_INVOICE)
        assert len(cases) == 2
        assert Decimal(cases[-1].payload["published"]["total"]) == Decimal("171000")
