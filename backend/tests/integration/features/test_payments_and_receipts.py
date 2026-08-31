"""Pagos y recibos: el estado sale de los pagos, no de lo que informe el portal.

Las reglas que más fácil se rompen de la 005, y que por eso se fijan acá:

* el estado de pago **se calcula** con lo imputado (RF-45), y cuando no coincide
  con el del portal se señalan los dos (RF-46);
* una factura con más pagos que total no está saldada: está inconsistente, se
  informa y **queda afuera** de los totales (RF-14 a RF-17, RF-16);
* un comprobante traído del portal no se deja sin efecto (RF-23), y uno que no
  dice a qué factura corresponde no se reparte solo (RF-12, RF-54);
* el recibo se niega después del vencimiento (RF-34) y no se emite dos veces
  (RF-35), y anularlo sobre una vencida abre un incidente (RF-51).
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.modules.purchases.models import PaymentOrigin, PaymentState
from app.modules.purchases.service import PurchasesService, today_here
from app.shared.errors import ConflictError, ValidationError
from app.shared.events import NormalizedInvoice, NormalizedPayment, NormalizedSupplier
from tests.factories.purchases_factory import InvoiceFactory, PaymentFactory, SupplierFactory

pytestmark = [pytest.mark.integration, pytest.mark.database]


class TestThePaymentStateComesFromThePayments:
    """H1 y H3: lo imputado manda, y lo que dice el portal se muestra al lado."""

    async def test_an_invoice_with_no_payments_is_unpaid(self, session: AsyncSession) -> None:
        """RF-01."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        stored = await InvoiceFactory.create(session, supplier=supplier, total=100_000)

        # Act
        read = await PurchasesService(session).get_invoice(stored.id)

        # Assert
        assert read.payment_state == "SIN_PAGOS"
        assert read.paid == 0
        assert read.balance == Decimal(100_000)

    async def test_a_partial_payment_reports_how_much_of_it_is_paid(
        self, session: AsyncSession
    ) -> None:
        """RF-02, RF-03."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Cañerias del Litoral SA")
        stored = await InvoiceFactory.create(session, supplier=supplier, total=100_000)
        await PaymentFactory.create(session, invoice=stored, amount=25_000)

        # Act
        read = await PurchasesService(session).get_invoice(stored.id)

        # Assert
        assert read.payment_state == "PARCIAL"
        assert read.paid == Decimal(25_000)
        assert read.paid_pct == 25

    async def test_it_disagrees_out_loud_with_the_portal(self, session: AsyncSession) -> None:
        """RF-46: no gana ninguno de los dos, se muestran los dos."""
        # Arrange — el portal dice `Pagada`, y no hay un solo pago imputado.
        supplier = await SupplierFactory.create(session, legal_name="Herramientas Cuyo SRL")
        stored = await InvoiceFactory.create(
            session, supplier=supplier, total=100_000, portal_payment_status="Pagada"
        )

        # Act
        read = await PurchasesService(session).get_invoice(stored.id)

        # Assert
        assert read.payment_state == "SIN_PAGOS"
        assert read.portal_payment_status == "Pagada"
        assert read.payment_state_disagrees is True

    async def test_a_wording_the_platform_does_not_know_is_not_a_contradiction(
        self, session: AsyncSession
    ) -> None:
        """Si no, el día que el portal agregue una palabra se señalan las cien."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Sanitarios SA")
        stored = await InvoiceFactory.create(
            session, supplier=supplier, total=100_000, portal_payment_status="En gestion"
        )

        # Act
        read = await PurchasesService(session).get_invoice(stored.id)

        # Assert
        assert read.payment_state_disagrees is False


class TestAnInconsistentInvoice:
    """H3: más pagos que total no es estar saldada."""

    async def test_it_is_flagged_and_never_settled(self, session: AsyncSession) -> None:
        """RF-14, RF-15, RF-17."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Instrumental SA")
        stored = await InvoiceFactory.create(session, supplier=supplier, total=100_000)
        await PaymentFactory.create(session, invoice=stored, amount=120_000)

        # Act
        read = await PurchasesService(session).get_invoice(stored.id)

        # Assert
        assert read.is_inconsistent is True
        assert read.payment_state != "SALDADA"
        assert read.total == Decimal(100_000)
        assert read.paid == Decimal(120_000)

    async def test_it_is_left_out_of_the_totals_and_the_exclusion_is_reported(
        self, session: AsyncSession
    ) -> None:
        """RF-16, y RF-28: cuántas quedaron afuera viaja con el número."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Electrical Supply SA")
        good = await InvoiceFactory.create(session, supplier=supplier, total=50_000)
        broken = await InvoiceFactory.create(session, supplier=supplier, total=100_000)
        await PaymentFactory.create(session, invoice=good, amount=20_000)
        await PaymentFactory.create(session, invoice=broken, amount=150_000)

        # Act
        totals = await PurchasesService(session).supplier_totals(supplier.id)

        # Assert
        assert totals.invoiced == Decimal(50_000)
        assert totals.paid == Decimal(20_000)
        assert totals.owed == Decimal(30_000)
        assert totals.excluded == 1


class TestRegisteringAPaymentByHand:
    """H4: cargar un pago, y no poder deshacer el del portal."""

    async def test_it_warns_before_registering_more_than_the_balance(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-21: el aviso es el rechazo, y se contesta confirmando."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Insumos Bahia SA")
        stored = await InvoiceFactory.create(session, supplier=supplier, total=10_000)
        service = PurchasesService(session)

        # Act / Assert — primero avisa…
        with pytest.raises(ConflictError) as warned:
            await service.register_payment(
                stored.id,
                amount=Decimal(15_000),
                paid_on=date(2026, 3, 1),
                reference=None,
                actor_user_id=owner.id,
            )
        assert Decimal(warned.value.details["balance"]) == Decimal(10_000)

        # …y después, dicho que sí, lo registra.
        registered = await service.register_payment(
            stored.id,
            amount=Decimal(15_000),
            paid_on=date(2026, 3, 1),
            reference=None,
            actor_user_id=owner.id,
            confirm_over_balance=True,
        )
        assert registered.origin is PaymentOrigin.MANUAL
        assert registered.created_by_user_id == owner.id

    async def test_a_payment_from_the_portal_is_not_undone(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-23: es lo que informó el origen, y no se borra el registro de otro."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Pinturerias SA")
        stored = await InvoiceFactory.create(session, supplier=supplier)
        payment = await PaymentFactory.create(session, invoice=stored, origin=PaymentOrigin.PORTAL)

        # Act / Assert
        with pytest.raises(ConflictError):
            await PurchasesService(session).void_payment(payment.id, actor_user_id=owner.id)

    async def test_one_loaded_by_hand_is_undone_and_stops_counting(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-22, y el estado se recalcula solo porque nunca estuvo guardado."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Ferreteria SA")
        stored = await InvoiceFactory.create(session, supplier=supplier, total=10_000)
        payment = await PaymentFactory.create(session, invoice=stored, amount=10_000)
        service = PurchasesService(session)
        assert (await service.get_invoice(stored.id)).payment_state == "SALDADA"

        # Act
        await service.void_payment(payment.id, actor_user_id=owner.id)

        # Assert
        assert (await service.get_invoice(stored.id)).payment_state == "SIN_PAGOS"


class TestAVoucherThatDoesNotSayWhichInvoice:
    """H2 y H9: el hallazgo del relevamiento, y lo que la plataforma hace con él."""

    async def test_it_waits_for_a_person_instead_of_being_split(
        self, session: AsyncSession
    ) -> None:
        """RF-12, RF-54: repartir plata por su cuenta es lo único que no hace."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        await InvoiceFactory.create(session, supplier=supplier, number="F-7797")

        # Act
        await PurchasesService(session).impute_payments(
            (
                NormalizedPayment(
                    staging_row_id=1,
                    supplier_text="Aceros Belgrano SA",
                    references=(),
                    paid_on=date(2026, 3, 1),
                    amount=Decimal(30_000),
                    external_id="Aceros Belgrano SA|REC-1084",
                ),
            )
        )

        # Assert
        pending = await PurchasesService(session).pending_payments()
        assert len(pending) == 1
        assert pending[0].state is PaymentState.PENDING
        assert pending[0].review_reason

    async def test_the_same_voucher_read_twice_is_imputed_once(self, session: AsyncSession) -> None:
        """RF-13: lo dice la clave única, no un chequeo que puede correr carreras."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        await InvoiceFactory.create(session, supplier=supplier, number="F-1234")
        voucher = NormalizedPayment(
            staging_row_id=1,
            supplier_text="Aceros Belgrano SA",
            references=("F-1234",),
            paid_on=date(2026, 3, 1),
            amount=Decimal(30_000),
            external_id="Aceros Belgrano SA|REC-2222",
        )
        service = PurchasesService(session)

        # Act
        await service.impute_payments((voucher,))
        await service.impute_payments((voucher,))

        # Assert
        stored = await session.get(type(supplier), supplier.id)
        assert stored is not None
        invoice_id = (await service.list_invoices(supplier_id=supplier.id)).items[0].id
        assert len(await service.payments_of(invoice_id)) == 1

    async def test_a_split_has_to_add_up_exactly(self, session: AsyncSession, owner: User) -> None:
        """RF-55: un reparto que no suma no es un reparto, es otro monto."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Distribuidora Sur SA")
        first = await InvoiceFactory.create(session, supplier=supplier, total=10_000)
        second = await InvoiceFactory.create(session, supplier=supplier, total=10_000)
        voucher = await PaymentFactory.create(
            session, amount=20_000, state=PaymentState.PENDING, origin=PaymentOrigin.PORTAL
        )
        service = PurchasesService(session)

        # Act / Assert
        with pytest.raises(ValidationError):
            await service.split_payment(
                voucher.id,
                parts=[(first.id, Decimal(10_000)), (second.id, Decimal(5_000))],
                actor_user_id=owner.id,
            )

        parts = await service.split_payment(
            voucher.id,
            parts=[(first.id, Decimal(10_000)), (second.id, Decimal(10_000))],
            actor_user_id=owner.id,
        )
        assert len(parts) == 2
        assert (await service.get_invoice(first.id)).payment_state == "SALDADA"

    async def test_a_split_moves_each_balance_by_its_own_part(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-53, RF-56: cada factura baja por su parte, y queda quién repartió.

        Tres partes distintas y no tres iguales a propósito: un reparto en
        partes iguales pasaría igual si el servicio dividiera el monto entre la
        cantidad de facturas, que es exactamente lo que la spec prohíbe — el
        reparto lo decide una persona, no el sistema.
        """
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Distribuidora Sur SA")
        first = await InvoiceFactory.create(session, supplier=supplier, total=10_000)
        second = await InvoiceFactory.create(session, supplier=supplier, total=10_000)
        third = await InvoiceFactory.create(session, supplier=supplier, total=10_000)
        voucher = await PaymentFactory.create(
            session, amount=30_000, state=PaymentState.PENDING, origin=PaymentOrigin.PORTAL
        )
        service = PurchasesService(session)

        # Act
        parts = await service.split_payment(
            voucher.id,
            parts=[
                (first.id, Decimal(10_000)),
                (second.id, Decimal(5_000)),
                (third.id, Decimal(15_000)),
            ],
            actor_user_id=owner.id,
        )

        # Assert — cada una por su parte, y ninguna por el promedio.
        assert (await service.get_invoice(first.id)).balance == 0
        assert (await service.get_invoice(second.id)).balance == Decimal(5_000)
        assert (await service.get_invoice(third.id)).balance == Decimal(-5_000)
        assert (await service.get_invoice(second.id)).payment_state == "PARCIAL"
        # RF-56: quién lo repartió, en el comprobante que se dejó sin efecto.
        assert all(part.created_by_user_id == owner.id for part in parts)
        assert await service.pending_payments() == []

    async def test_a_voucher_naming_an_unknown_invoice_is_imputed_when_it_lands(
        self, session: AsyncSession
    ) -> None:
        """RF-44: cuando la factura se registra, el comprobante deja de estar suelto."""
        # Arrange — el comprobante llega antes que la factura.
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        service = PurchasesService(session)
        await service.impute_payments(
            (
                NormalizedPayment(
                    staging_row_id=1,
                    supplier_text="Aceros Belgrano SA",
                    references=("F-9999",),
                    paid_on=date(2026, 3, 1),
                    amount=Decimal(30_000),
                    external_id="Aceros Belgrano SA|REC-3333",
                ),
            )
        )
        assert len(await service.pending_payments()) == 1

        # Act
        landed = await InvoiceFactory.create(session, supplier=supplier, number="F-9999")
        await service.impute_held_payments_for(landed)

        # Assert
        assert await service.pending_payments() == []
        assert (await service.get_invoice(landed.id)).paid == Decimal(30_000)


class TestTheReceptionReceipt:
    """H6 y H7: emitirlo a tiempo, y qué pasa cuando ya no se puede."""

    async def test_it_is_issued_with_its_own_correlative_number(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-36, RF-47, RF-48."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        stored = await InvoiceFactory.create(
            session, supplier=supplier, due_on=today_here() + timedelta(days=10)
        )

        # Act
        receipt = await PurchasesService(session).issue_receipt(stored.id, actor_user_id=owner.id)

        # Assert
        assert receipt.number.startswith("RC-")
        assert receipt.issued_by_user_id == owner.id
        assert receipt.document and stored.number in receipt.document

    async def test_it_is_refused_after_the_due_date(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-34: y el motivo se dice, no se devuelve un error genérico."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        overdue = await InvoiceFactory.create(
            session, supplier=supplier, due_on=today_here() - timedelta(days=1)
        )

        # Act / Assert
        with pytest.raises(ConflictError) as refused:
            await PurchasesService(session).issue_receipt(overdue.id, actor_user_id=owner.id)
        assert "venc" in refused.value.message

    async def test_it_is_not_issued_twice(self, session: AsyncSession, owner: User) -> None:
        """RF-35."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        stored = await InvoiceFactory.create(
            session, supplier=supplier, due_on=today_here() + timedelta(days=10)
        )
        service = PurchasesService(session)
        await service.issue_receipt(stored.id, actor_user_id=owner.id)

        # Act / Assert
        with pytest.raises(ConflictError):
            await service.issue_receipt(stored.id, actor_user_id=owner.id)

    async def test_annulling_one_lets_another_be_issued_while_it_is_not_due(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-49, RF-50."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        stored = await InvoiceFactory.create(
            session, supplier=supplier, due_on=today_here() + timedelta(days=10)
        )
        service = PurchasesService(session)
        receipt = await service.issue_receipt(stored.id, actor_user_id=owner.id)

        # Act
        voided = await service.void_receipt(receipt.id, actor_user_id=owner.id)
        again = await service.issue_receipt(stored.id, actor_user_id=owner.id)

        # Assert
        assert voided.voided_by_user_id == owner.id
        assert again.number != receipt.number

    async def test_an_overdue_invoice_without_a_receipt_becomes_an_incident(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-37, y RF-57 a RF-59 al cerrarlo."""
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        await InvoiceFactory.create(
            session, supplier=supplier, due_on=today_here() - timedelta(days=3)
        )
        service = PurchasesService(session)

        # Act
        opened = await service.open_incidents_for_overdue()
        incidents = await service.list_incidents()
        closed = await service.close_incident(
            incidents[0].id, resolution="Se habló con el proveedor", actor_user_id=owner.id
        )

        # Assert
        assert opened == 1
        assert incidents[0].invoice_number
        assert closed.closed_by_user_id == owner.id
        assert await service.list_incidents() == []
        assert len(await service.list_incidents(only_open=False)) == 1

    async def test_closing_an_incident_does_not_reopen_the_receipt(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-57, RF-58 y el borde duro del negocio que los rodea.

        Cerrar el incidente registra **qué se hizo**, no deshace la fecha: el
        recibo se emite hasta el vencimiento y no después, y nada lo reabre —
        ni cerrar el incidente, ni reprogramar más tarde. Sin este test, la
        forma más natural de "resolver" un incidente sería emitir el recibo que
        faltaba, y RF-34 dejaría de valer por la puerta de atrás.
        """
        # Arrange
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        stored = await InvoiceFactory.create(
            session, supplier=supplier, due_on=today_here() - timedelta(days=3)
        )
        service = PurchasesService(session)
        await service.open_incidents_for_overdue()
        incident = (await service.list_incidents())[0]

        # Act
        closed = await service.close_incident(
            incident.id, resolution="Se acordó pagarla con la próxima", actor_user_id=owner.id
        )

        # Assert — el motivo queda, y la emisión sigue negada.
        assert closed.resolution == "Se acordó pagarla con la próxima"
        assert closed.closed_at is not None
        with pytest.raises(ConflictError):
            await service.issue_receipt(stored.id, actor_user_id=owner.id)


class TestTheListingAnswersAboutTheListing:
    """H1 y H6: un filtro filtra el listado, no la página que se leyó."""

    async def test_filtering_by_payment_state_does_not_filter_only_the_page(
        self, session: AsyncSession
    ) -> None:
        """RF-04: la página vuelve completa y el total cuenta lo mismo que la página.

        Con el filtro aplicado después de paginar, pedir las parciales sobre un
        conjunto más grande que la página devolvía **lo parcial que hubiera
        entrado en esa página** y un total que contaba todo: dos números que se
        contradicen en la misma pantalla.
        """
        # Arrange — nueve facturas, tres de cada estado, entremezcladas.
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        for index in range(9):
            invoice = await InvoiceFactory.create(
                session, supplier=supplier, total=10_000, number=f"F-{9000 + index}"
            )
            if index % 3 == 1:
                await PaymentFactory.create(session, invoice=invoice, amount=4_000)
            elif index % 3 == 2:
                await PaymentFactory.create(session, invoice=invoice, amount=10_000)
        service = PurchasesService(session)

        # Act — una página de dos sobre las tres parciales.
        page = await service.list_invoices(payment_state="PARCIAL", limit=2)
        everything = await service.list_invoices(payment_state="PARCIAL", limit=100)

        # Assert
        assert page.total == 3
        assert len(page.items) == 2
        assert len(everything.items) == 3
        assert {item.payment_state for item in everything.items} == {"PARCIAL"}

    async def test_the_four_states_agree_between_the_query_and_the_reader(
        self, session: AsyncSession
    ) -> None:
        """El filtro en SQL y el estado calculado en Python dicen lo mismo.

        La regla vive en dos lados a propósito —una vez en `_payment_state` y
        otra en el `WHERE`— y este test es lo que impide que se separen: si
        alguien cambia una y no la otra, el listado miente sobre su propia
        cuenta.
        """
        # Arrange — una factura de cada estado, incluida la inconsistente.
        supplier = await SupplierFactory.create(session, legal_name="Cañerias del Litoral SA")
        unpaid = await InvoiceFactory.create(session, supplier=supplier, total=10_000)
        partial = await InvoiceFactory.create(session, supplier=supplier, total=10_000)
        settled = await InvoiceFactory.create(session, supplier=supplier, total=10_000)
        over = await InvoiceFactory.create(session, supplier=supplier, total=10_000)
        await PaymentFactory.create(session, invoice=partial, amount=3_000)
        await PaymentFactory.create(session, invoice=settled, amount=10_000)
        await PaymentFactory.create(session, invoice=over, amount=13_000)
        service = PurchasesService(session)

        # Act / Assert
        expected = {
            "SIN_PAGOS": unpaid.id,
            "PARCIAL": partial.id,
            "SALDADA": settled.id,
            "INCONSISTENTE": over.id,
        }
        for state, invoice_id in expected.items():
            listing = await service.list_invoices(
                supplier_id=supplier.id, payment_state=state, limit=100
            )
            assert [item.id for item in listing.items] == [invoice_id], state
            assert listing.total == 1, state

    async def test_an_invoice_can_be_wrong_in_two_ways_at_once(self, session: AsyncSession) -> None:
        """RF-15, RF-46: los dos señalamientos viajan juntos, no por precedencia."""
        # Arrange — más pagos que total, y el portal diciendo que está paga.
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        stored = await InvoiceFactory.create(
            session, supplier=supplier, total=10_000, portal_payment_status="Impaga"
        )
        await PaymentFactory.create(session, invoice=stored, amount=13_000)

        # Act
        read = await PurchasesService(session).get_invoice(stored.id)

        # Assert — la inconsistencia no tapa la contradicción.
        assert read.is_inconsistent is True
        assert read.payment_state_disagrees is True
        assert read.total == Decimal(10_000)
        assert read.paid == Decimal(13_000)


class TestTheReceiptThePortalAlreadyIssued:
    """RF-29 a RF-31, RF-35, RF-37: uno del portal cuenta como uno emitido."""

    async def test_it_counts_everywhere_a_receipt_counts(
        self, session: AsyncSession, owner: User
    ) -> None:
        """Se guardaba y no se leía: figuraba «Falta», admitía otro y abría incidente."""
        # Arrange — vencida hace tres días, con su recibo ya emitido en el portal.
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        stored = await InvoiceFactory.create(
            session,
            supplier=supplier,
            due_on=today_here() - timedelta(days=3),
            portal_receipt_issued=True,
        )
        service = PurchasesService(session)

        # Act
        read = await service.get_invoice(stored.id)
        with_receipt = await service.list_invoices(with_receipt=True, limit=100)
        without = await service.list_invoices(with_receipt=False, limit=100)
        opened = await service.open_incidents_for_overdue()

        # Assert
        assert read.receipt_issued is True
        assert read.receipt_number is None  # el número es del portal y no lo conocemos
        assert read.is_overdue_without_receipt is False
        assert stored.id in {item.id for item in with_receipt.items}
        assert stored.id not in {item.id for item in without.items}
        assert opened == 0
        with pytest.raises(ConflictError):
            await service.issue_receipt(stored.id, actor_user_id=owner.id)

    async def test_annulling_ours_wins_over_what_the_portal_says(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-50: una decisión de una persona no la deshace una lectura del portal."""
        # Arrange — el orden es el que pasa de verdad: emitimos el nuestro, y
        # **después** una lectura del portal informa que también tiene el suyo.
        supplier = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        stored = await InvoiceFactory.create(
            session, supplier=supplier, due_on=today_here() + timedelta(days=10)
        )
        service = PurchasesService(session)
        receipt = await service.issue_receipt(stored.id, actor_user_id=owner.id)
        stored.portal_receipt_issued = True
        await session.flush()

        # Act
        await service.void_receipt(receipt.id, actor_user_id=owner.id)

        # Assert — anulado el nuestro, se puede emitir otro aunque el portal insista.
        again = await service.issue_receipt(stored.id, actor_user_id=owner.id)
        assert again.number != receipt.number


class TestTheDueDateComesFromTheAgreedTerm:
    """H5: de `issued_on + plazo`, y de ninguna otra fecha (RF-26)."""

    async def test_the_term_of_the_supplier_decides_and_not_the_document(
        self, session: AsyncSession
    ) -> None:
        """RF-26: 1 de marzo + 45 días vence el 15 de abril, diga lo que diga el papel."""
        # Arrange
        supplier = await SupplierFactory.create(
            session, legal_name="Distribuidora Sur SA", payment_term_days=45
        )
        service = PurchasesService(session)

        # Act — el portal publica otra fecha de vencimiento en su columna.
        await service.register_invoices(
            batch_id=1,
            invoices=(
                NormalizedInvoice(
                    staging_row_id=1,
                    number="F-7001",
                    issued_on=date(2026, 3, 1),
                    due_on=date(2026, 3, 31),
                    total=Decimal(10_000),
                    supplier_text="Distribuidora Sur SA",
                ),
            ),
        )

        # Assert
        listing = await service.list_invoices(supplier_id=supplier.id, limit=10)
        assert listing.items[0].due_on == date(2026, 4, 15)

    async def test_the_due_date_is_recomputed_when_the_term_finally_appears(
        self, session: AsyncSession
    ) -> None:
        """RF-26: la fecha del portal era un suplente, y se corrige el día que se sabe el plazo.

        El plazo aparece cuando el padrón por fin expande esa fila. Hasta ahora
        nada rehacía la cuenta, así que la factura se quedaba con la fecha del
        portal para siempre — y de esa fecha cuelgan el plazo del recibo, los
        tramos de antigüedad y el atraso promedio.
        """
        # Arrange — un proveedor sin plazo conocido, y una factura suya.
        supplier = await SupplierFactory.create(
            session, legal_name="Aceros Belgrano SA", payment_term_days=None
        )
        service = PurchasesService(session)
        await service.register_invoices(
            batch_id=1,
            invoices=(
                NormalizedInvoice(
                    staging_row_id=2,
                    number="F-7002",
                    issued_on=date(2026, 3, 1),
                    due_on=date(2026, 3, 31),
                    total=Decimal(10_000),
                    supplier_text="Aceros Belgrano SA",
                ),
            ),
        )
        before = (await service.list_invoices(supplier_id=supplier.id, limit=10)).items[0]
        assert before.due_on == date(2026, 3, 31)

        # Act — el padrón trae el plazo pactado.
        await service.remember_suppliers(
            (
                NormalizedSupplier(
                    legal_name="Aceros Belgrano SA",
                    tax_id=None,
                    email=None,
                    phone=None,
                    payment_term_days=30,
                    balance=None,
                ),
            )
        )

        # Assert
        after = (await service.list_invoices(supplier_id=supplier.id, limit=10)).items[0]
        assert after.due_on == date(2026, 3, 31)  # 1 de marzo + 30 días
        assert after.due_on == before.issued_on + timedelta(days=30)


class TestAVoucherBelongsToOneSupplier:
    """El supuesto firmado: un comprobante cubre facturas de un solo proveedor."""

    async def test_it_is_not_split_across_two_suppliers(
        self, session: AsyncSession, owner: User
    ) -> None:
        """RF-53 y el supuesto de la spec.

        Repartir plata de un proveedor sobre la factura de otro equivoca a los
        dos a la vez: a uno se le debe menos de lo que el sistema dice y al otro
        más, y de esos números salen la antigüedad y el atraso promedio de
        ambos. El comprobante se queda apartado, que es lo que «pregunta»
        significa acá.
        """
        # Arrange
        first = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        second = await SupplierFactory.create(session, legal_name="Distribuidora Sur SA")
        mine = await InvoiceFactory.create(session, supplier=first, total=10_000)
        theirs = await InvoiceFactory.create(session, supplier=second, total=10_000)
        voucher = await PaymentFactory.create(
            session, amount=20_000, state=PaymentState.PENDING, origin=PaymentOrigin.PORTAL
        )
        voucher.supplier_id = first.id
        await session.flush()
        service = PurchasesService(session)

        # Act / Assert
        with pytest.raises(ValidationError):
            await service.split_payment(
                voucher.id,
                parts=[(mine.id, Decimal(10_000)), (theirs.id, Decimal(10_000))],
                actor_user_id=owner.id,
            )
        # Y sigue apartado, esperando: nada se movió.
        assert [item.id for item in await service.pending_payments()] == [voucher.id]

    async def test_it_is_not_imputed_to_the_invoices_of_another_supplier(
        self, session: AsyncSession, owner: User
    ) -> None:
        """El caso más silencioso: un solo proveedor, pero el que no pagó."""
        # Arrange
        payer = await SupplierFactory.create(session, legal_name="Aceros Belgrano SA")
        other = await SupplierFactory.create(session, legal_name="Distribuidora Sur SA")
        theirs = await InvoiceFactory.create(session, supplier=other, total=10_000)
        voucher = await PaymentFactory.create(
            session, amount=10_000, state=PaymentState.PENDING, origin=PaymentOrigin.PORTAL
        )
        voucher.supplier_id = payer.id
        await session.flush()
        service = PurchasesService(session)

        # Act / Assert
        with pytest.raises(ValidationError):
            await service.split_payment(
                voucher.id, parts=[(theirs.id, Decimal(10_000))], actor_user_id=owner.id
            )


class TestWhatIsOwedAndHowLate:
    """H5: la deuda por antigüedad y el atraso promedio, contra la cuenta a mano."""

    async def test_the_debt_is_split_by_how_long_it_has_been_overdue(
        self, session: AsyncSession
    ) -> None:
        """RF-25: los tramos se cuentan desde el vencimiento, no desde la fecha."""
        # Arrange — cuatro impagas, una en cada tramo.
        supplier = await SupplierFactory.create(
            session, legal_name="Aceros Belgrano SA", payment_term_days=30
        )
        for days, amount in ((10, 1_000), (45, 2_000), (75, 4_000), (200, 8_000)):
            await InvoiceFactory.create(
                session,
                supplier=supplier,
                total=amount,
                due_on=today_here() - timedelta(days=days),
            )

        # Act
        totals = await PurchasesService(session).supplier_totals(supplier.id)

        # Assert — cada peso en un solo tramo, y la suma es la deuda entera.
        by_label = {bucket.label: bucket for bucket in totals.aging}
        assert sum(bucket.amount for bucket in totals.aging) == Decimal(15_000)
        assert sum(bucket.invoices for bucket in totals.aging) == 4
        assert all(bucket.invoices == 1 for bucket in by_label.values() if bucket.amount > 0)

    async def test_the_average_delay_counts_the_unpaid_ones_too(
        self, session: AsyncSession
    ) -> None:
        """RF-27: y esa es la parte que se olvida.

        Dejar afuera lo que se debe y ya se pasó de fecha bajaría el número
        justo cuando peor se está cumpliendo. Una pagada diez días tarde y una
        impaga vencida hace veinte dan quince de promedio; sólo la pagada daría
        diez.
        """
        # Arrange
        supplier = await SupplierFactory.create(
            session, legal_name="Cañerias del Litoral SA", payment_term_days=30
        )
        paid_late = await InvoiceFactory.create(
            session, supplier=supplier, total=10_000, due_on=today_here() - timedelta(days=40)
        )
        await PaymentFactory.create(
            session,
            invoice=paid_late,
            amount=10_000,
            paid_on=today_here() - timedelta(days=30),  # diez días tarde
        )
        await InvoiceFactory.create(
            session, supplier=supplier, total=5_000, due_on=today_here() - timedelta(days=20)
        )

        # Act
        totals = await PurchasesService(session).supplier_totals(supplier.id)

        # Assert — (10 + 20) / 2, y no 10.
        assert totals.average_delay_days == Decimal("15.0")
