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
from app.modules.purchases.models import (
    Invoice,
    InvoiceReviewState,
    OrderReviewState,
    PurchaseOrder,
    RecordOrigin,
)
from app.modules.purchases.service import DISPUTED_BY_PORTAL, PurchasesService
from app.modules.triage.models import CaseStatus, ExceptionCase
from app.modules.triage.service import (
    DISPUTED_INVOICE,
    DISPUTED_ORDER,
    INVOICE_ORIGIN,
    ORDER_ORIGIN,
    UNREADABLE_INVOICE_ROW,
    UNREADABLE_ORDER_ROW,
    TriageService,
)
from app.shared.errors import ConflictError, NotFoundError
from app.shared.events import NormalizedInvoice, NormalizedPurchaseOrder
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


class TestTheOrderHalf:
    """Lo mismo sobre una orden de compra, que no es lo mismo en un punto.

    Una orden cargada a mano **no se puede cronometrar en su estado**: la
    plataforma no la vio llegar, así que lo único cierto es hace cuánto se
    emitió (RF-49 de 007). Fingir que el reloj arrancó cuando alguien la
    escribió sería inventar una antigüedad.
    """

    async def an_unreadable_order_row(self, session: AsyncSession) -> ExceptionCase:
        """El pendiente que abre una fila de órdenes que nadie pudo interpretar."""
        await TriageService(session).open_case(
            kind=UNREADABLE_ORDER_ROW,
            section=BusinessSection.PURCHASING,
            reason="La fila de órdenes no se pudo interpretar",
            payload={"staging_row_id": 9, "excerpt": "OC 4417  ???", "origin": ORDER_ORIGIN},
            key="9",
        )
        result = await session.execute(
            select(ExceptionCase).where(ExceptionCase.kind == UNREADABLE_ORDER_ROW)
        )
        case = result.scalars().first()
        assert case is not None
        return case

    async def stored_order(self, session: AsyncSession) -> PurchaseOrder:
        """La orden, como quedó en `core`."""
        found = (
            (await session.execute(select(PurchaseOrder).where(PurchaseOrder.number == "OC-4417")))
            .scalars()
            .first()
        )
        assert found is not None
        return found

    async def test_a_row_nobody_could_read_becomes_an_order(
        self, session: AsyncSession, owner: User
    ) -> None:
        """La persona la escribe mirando el papel, y la orden entra."""
        # Arrange
        supplier = await SupplierFactory.create(
            session, legal_name=SUPPLIER, tax_id="30-71042588-4", payment_term_days=30
        )
        case = await self.an_unreadable_order_row(session)

        # Act
        await TriageService(session).resolve(
            case.id,
            decision={
                "action": "load",
                "number": "OC-4417",
                "ordered_on": "2026-08-25",
                "supplier_id": supplier.id,
                "product_text": "Caños de 3/4",
                "quantity": 40,
                "amount": "90000",
            },
            user_id=owner.id,
            remember=False,
            visible=EVERY_AREA,
        )

        # Assert
        order = await self.stored_order(session)
        assert order.origin is RecordOrigin.MANUAL
        assert order.amount == Decimal("90000")
        assert order.review_state is OrderReviewState.RESOLVED
        # La plataforma no la vio llegar: no se le puede contar el tiempo en su
        # estado, y se dice como eso en vez de inventarlo (RF-49 de 007).
        assert order.observed_from_start is False

    async def test_the_portal_publishing_it_later_asks_which_values_stay(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Y el estado sí se actualiza: es un hecho del portal, no está en discusión."""
        # Arrange
        supplier = await SupplierFactory.create(
            session, legal_name=SUPPLIER, tax_id="30-71042588-4", payment_term_days=30
        )
        purchases = PurchasesService(session)
        await purchases.register_order_by_hand(
            number="OC-4417",
            ordered_on=date(2026, 8, 25),
            supplier_id=supplier.id,
            amount=Decimal("90000"),
            actor_user_id=owner.id,
        )

        # Act — el portal publica la fila, ya legible, con otro importe.
        await purchases.register_orders(
            batch_id=1,
            orders=(
                NormalizedPurchaseOrder(
                    staging_row_id=9,
                    number="OC-4417",
                    ordered_on=date(2026, 8, 25),
                    supplier_text=SUPPLIER,
                    product_code=None,
                    product_text="Caños de 3/4",
                    quantity=40,
                    amount=Decimal("96000"),
                    status_text="En preparación",
                ),
            ),
        )

        # Assert
        order = await self.stored_order(session)
        assert order.review_state is OrderReviewState.PENDING
        assert order.review_reason == DISPUTED_BY_PORTAL
        assert order.amount == Decimal("90000")
        assert order.status_text == "En preparación"

        result = await session.execute(
            select(ExceptionCase).where(ExceptionCase.kind == DISPUTED_ORDER)
        )
        cases = list(result.scalars().all())
        assert len(cases) == 1
        assert Decimal(cases[0].payload["published"]["importe"]) == Decimal("96000")

    async def test_keeping_the_portal_values_writes_them(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Contestada la pregunta, la orden deja de estar apartada."""
        # Arrange
        supplier = await SupplierFactory.create(
            session, legal_name=SUPPLIER, tax_id="30-71042588-4", payment_term_days=30
        )
        purchases = PurchasesService(session)
        await purchases.register_order_by_hand(
            number="OC-4417",
            ordered_on=date(2026, 8, 25),
            supplier_id=supplier.id,
            amount=Decimal("90000"),
            actor_user_id=owner.id,
        )
        await purchases.register_orders(
            batch_id=1,
            orders=(
                NormalizedPurchaseOrder(
                    staging_row_id=9,
                    number="OC-4417",
                    ordered_on=date(2026, 8, 26),
                    supplier_text=SUPPLIER,
                    product_code=None,
                    product_text="Caños de 3/4",
                    quantity=40,
                    amount=Decimal("96000"),
                    status_text="En preparación",
                ),
            ),
        )
        result = await session.execute(
            select(ExceptionCase).where(ExceptionCase.kind == DISPUTED_ORDER)
        )
        case = result.scalars().first()
        assert case is not None

        # Act
        await TriageService(session).resolve(
            case.id,
            decision={"keep": "portal"},
            user_id=owner.id,
            remember=False,
            visible=EVERY_AREA,
        )

        # Assert
        order = await self.stored_order(session)
        assert order.amount == Decimal("96000")
        assert order.ordered_on == date(2026, 8, 26)
        assert order.origin is RecordOrigin.PORTAL
        assert order.review_state is OrderReviewState.RESOLVED


class TestWhatArrivesBrokenDoesNotWriteAnything:
    """Las guardas, que son la mitad silenciosa de dejar cargar datos a mano.

    Una decisión llega del navegador, pasa por la cola y vuelve meses después:
    todo lo que trae se convierte sin confiar. Lo que no se puede convertir no
    pisa nada — escribir basura sobre un dato bueno es peor que no aplicar la
    decisión — y lo que no se puede hacer se rechaza con una frase, no con un
    error de integridad.
    """

    async def test_a_supplier_outside_the_register_is_refused(
        self, session: AsyncSession, owner: User
    ) -> None:
        """El padrón es cerrado: una factura no lo amplía (H2 y H4 de la 004)."""
        purchases = PurchasesService(session)
        with pytest.raises(NotFoundError):
            await purchases.register_invoice_by_hand(
                number=NUMBER,
                issued_on=date(2026, 8, 30),
                total=Decimal("152400"),
                supplier_id=9999,
                actor_user_id=owner.id,
            )
        with pytest.raises(NotFoundError):
            await purchases.register_order_by_hand(
                number="OC-9999",
                ordered_on=date(2026, 8, 25),
                supplier_id=9999,
                actor_user_id=owner.id,
            )

    async def test_an_order_number_already_registered_is_refused(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Con una frase, y no con el error del índice único."""
        # Arrange
        supplier = await SupplierFactory.create(
            session, legal_name=SUPPLIER, tax_id="30-71042588-4", payment_term_days=30
        )
        purchases = PurchasesService(session)
        await purchases.register_order_by_hand(
            number="OC-4417",
            ordered_on=date(2026, 8, 25),
            supplier_id=supplier.id,
            actor_user_id=owner.id,
        )

        # Act & Assert
        with pytest.raises(ConflictError):
            await purchases.register_order_by_hand(
                number="OC-4417",
                ordered_on=date(2026, 8, 25),
                supplier_id=supplier.id,
                actor_user_id=owner.id,
            )

    async def test_a_dispute_whose_record_is_gone_is_not_an_error(
        self, session: AsyncSession, owner: User
    ) -> None:
        """La decisión ya quedó guardada del lado de la cola; acá no hay a qué aplicarla."""
        await PurchasesService(session).settle_manual_dispute(
            entity="invoice",
            entity_id=9999,
            keep="portal",
            published={"fecha": "2026-08-30", "total": "160000"},
            actor_user_id=owner.id,
        )

    async def test_values_that_are_not_values_do_not_overwrite_good_ones(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Lo que no se puede convertir se deja como estaba."""
        # Arrange
        supplier = await SupplierFactory.create(
            session, legal_name=SUPPLIER, tax_id="30-71042588-4", payment_term_days=30
        )
        purchases = PurchasesService(session)
        invoice = await purchases.register_invoice_by_hand(
            number=NUMBER,
            issued_on=date(2026, 8, 30),
            total=Decimal("152400"),
            supplier_id=supplier.id,
            actor_user_id=owner.id,
        )
        order = await purchases.register_order_by_hand(
            number="OC-4417",
            ordered_on=date(2026, 8, 25),
            supplier_id=supplier.id,
            amount=Decimal("90000"),
            actor_user_id=owner.id,
        )

        # Act — «queda lo del portal», pero lo del portal llegó ilegible.
        await purchases.settle_manual_dispute(
            entity="invoice",
            entity_id=invoice.id,
            keep="portal",
            published={"fecha": "el martes", "total": "un montón"},
            actor_user_id=owner.id,
        )
        await purchases.settle_manual_dispute(
            entity="purchase_order",
            entity_id=order.id,
            keep="portal",
            published={"fecha": "2026-08-26", "importe": "ni idea"},
            actor_user_id=owner.id,
        )

        # Assert — los datos buenos siguen ahí; sólo se escribió lo convertible.
        assert (await stored(session)).total == Decimal("152400")
        assert (await stored(session)).issued_on == date(2026, 8, 30)
        moved = (
            (await session.execute(select(PurchaseOrder).where(PurchaseOrder.number == "OC-4417")))
            .scalars()
            .first()
        )
        assert moved is not None
        assert moved.ordered_on == date(2026, 8, 26)
        assert moved.amount is None

    async def test_the_portal_republishing_the_same_values_says_nothing(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Coincidir no es discutir: no se abre ningún caso."""
        # Arrange
        supplier = await SupplierFactory.create(
            session, legal_name=SUPPLIER, tax_id="30-71042588-4", payment_term_days=30
        )
        purchases = PurchasesService(session)
        await purchases.register_invoice_by_hand(
            number=NUMBER,
            issued_on=date(2026, 8, 30),
            total=Decimal("152400"),
            supplier_id=supplier.id,
            actor_user_id=owner.id,
        )

        # Act — el portal publica exactamente lo mismo que escribió la persona.
        await purchases.register_invoices(batch_id=1, invoices=(portal_row(152400),))

        # Assert
        invoice = await stored(session)
        assert invoice.review_state is InvoiceReviewState.RESOLVED
        assert await cases_of(session, DISPUTED_INVOICE) == []

    async def test_an_incomplete_load_writes_nothing(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Media factura no es una factura: sin los cuatro campos no entra nada.

        La pantalla no deja confirmar sin ellos, y por eso mismo esto no se
        puede quedar en la pantalla: la decisión viaja por un evento, y lo que
        llega incompleto no puede escribir un registro a medias.
        """
        # Arrange
        supplier = await SupplierFactory.create(
            session, legal_name=SUPPLIER, tax_id="30-71042588-4", payment_term_days=30
        )
        service = TriageService(session)
        case = await an_unreadable_row(session)

        # Act — sin total.
        await service.resolve(
            case.id,
            decision={
                "action": "load",
                "number": NUMBER,
                "issued_on": "2026-08-30",
                "supplier_id": supplier.id,
            },
            user_id=owner.id,
            remember=False,
            visible=EVERY_AREA,
        )

        # Assert — el caso se cerró con lo que la persona decidió, y no entró
        # ninguna factura a medias.
        found = (
            (await session.execute(select(Invoice).where(Invoice.number == NUMBER)))
            .scalars()
            .first()
        )
        assert found is None
