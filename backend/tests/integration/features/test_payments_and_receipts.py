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
from app.shared.events import NormalizedPayment
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
