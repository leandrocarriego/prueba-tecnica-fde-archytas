"""Los parsers de las cinco secciones nuevas, contra los fixtures fijados.

`TEST-03` es Blocker: nunca contra el portal en vivo. Lo que se afirma acá son
los números que el relevamiento midió, para que un cambio en el portal —o en un
parser— se note como un test que falla y no como un tablero que empieza a dar
distinto sin que nadie sepa por qué.
"""

from decimal import Decimal
from pathlib import Path

import pytest

from app.modules.ingestion.parsers import (
    invoice_references_in,
    parse_invoices,
    parse_messages,
    parse_purchase_orders,
    parse_sales,
    parse_supplier_ledger,
    sale_code_key,
)
from app.modules.purchases.service import RECEIVED_STATUS
from app.shared.errors import ExtractionError

pytestmark = [pytest.mark.unit, pytest.mark.portal]

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "portal"


def fixture(name: str) -> bytes:
    """The bytes of a pinned fixture."""
    return (FIXTURES / name).read_bytes()


class TestTheInvoicesScreen:
    """004: la tabla trae los cuatro datos de cabecera, completos, en las 100 filas."""

    def test_it_reads_the_hundred_rows_without_setting_any_aside(self) -> None:
        """Lo que el relevamiento afirma: ni una celda vacía en ninguna columna."""
        rows = parse_invoices(fixture("invoices-page-2026-08-29.html"))

        assert len(rows) == 100
        assert all(row.is_readable for row in rows)
        assert all(row.number and row.supplier_text for row in rows)
        assert all(row.issued_on is not None and row.total is not None for row in rows)

    def test_the_three_formats_are_the_measured_ones(self) -> None:
        """46 escaneados, 29 planillas, 25 PDF: es lo que decide qué lector prueba primero."""
        rows = parse_invoices(fixture("invoices-page-2026-08-29.html"))

        counts = {
            kind: sum(1 for row in rows if row.file_kind == kind)
            for kind in {row.file_kind for row in rows}
        }
        assert counts == {"PDF (escaneado)": 46, "Excel": 29, "PDF": 25}

    def test_it_reads_what_005_needs_from_the_same_screen(self) -> None:
        """Pagado, saldo, estado y recibo salen de esta lectura y no de una segunda."""
        rows = parse_invoices(fixture("invoices-page-2026-08-29.html"))
        first = rows[0]

        assert first.number == "F-7797"
        assert first.total == Decimal("223376")
        assert first.paid == Decimal(0)
        assert first.balance == Decimal("223376")
        assert first.portal_payment_status == "Impaga"
        assert first.receipt_issued is True

    def test_the_overdue_note_is_not_read_as_part_of_the_state(self) -> None:
        """`Impaga (88d vencida)` es el estado más cuánto lleva, y lo segundo es de hoy.

        Cuántos días lleva vencida es una pregunta que esta plataforma contesta
        sola, contra su propio reloj. Guardarla como si fuera del portal sería
        congelar el día en que se leyó la pantalla.
        """
        rows = parse_invoices(fixture("invoices-page-2026-08-29.html"))

        assert all(
            row.portal_payment_status in {"Impaga", "Pagada", "Pago parcial"} for row in rows
        )

    def test_the_product_is_crossed_by_code_and_not_by_name(self) -> None:
        """La celda arranca con el código del catálogo, y eso evita adivinar."""
        rows = parse_invoices(fixture("invoices-page-2026-08-29.html"))

        assert rows[0].product_code == "COR-0057"
        assert all(row.product_code is None or row.product_code.startswith("COR-") for row in rows)

    def test_a_page_without_a_table_is_a_technical_failure(self) -> None:
        """El portal cambió y este parser dejó de entender lo que lee."""
        with pytest.raises(ExtractionError):
            parse_invoices(b"<html><body><p>Sin tabla</p></body></html>")


class TestTheSupplierRegister:
    """004: el padrón son ocho filas, y la ficha está sólo en el detalle expandido."""

    def test_it_reads_the_eight_suppliers(self) -> None:
        """Las ocho razones sociales contra las que se resuelven las grafías."""
        suppliers, _ = parse_supplier_ledger(fixture("suppliers-ledger-page-2026-08-29.html"))

        assert len(suppliers) == 8
        assert all(supplier.legal_name for supplier in suppliers)

    def test_the_card_of_an_expanded_supplier_is_read_by_label(self) -> None:
        """CUIT, correo, teléfono y plazo salen del detalle, no de la fila."""
        suppliers, _ = parse_supplier_ledger(fixture("suppliers-ledger-page-2026-08-29.html"))
        expanded = next(item for item in suppliers if item.legal_name == "Aceros Belgrano SA")

        assert expanded.tax_id == "30-70918273-4"
        assert expanded.email == "cobranzas@acerosbelgrano.com.ar"
        assert expanded.payment_term_days == 45
        assert expanded.balance == Decimal("4307338")

    def test_a_supplier_the_portal_did_not_expand_keeps_what_it_did_publish(self) -> None:
        """Saber menos no es lo mismo que inventar el resto."""
        suppliers, _ = parse_supplier_ledger(fixture("suppliers-ledger-page-2026-08-29.html"))
        collapsed = next(item for item in suppliers if item.legal_name != "Aceros Belgrano SA")

        assert collapsed.balance is not None
        assert collapsed.tax_id is None
        assert collapsed.payment_term_days is None

    def test_only_the_payments_of_the_ledger_are_read(self) -> None:
        """Los movimientos `Factura` no son pagos y no se leen como tales."""
        _, payments = parse_supplier_ledger(fixture("suppliers-ledger-page-2026-08-29.html"))

        assert payments
        assert all(payment.amount and payment.amount > 0 for payment in payments)
        assert all(payment.supplier_text == "Aceros Belgrano SA" for payment in payments)

    def test_a_voucher_that_names_its_own_receipt_names_no_invoice(self) -> None:
        """El hallazgo de 005: `REC-1084` no dice a qué factura corresponde.

        Es lo que hace que la mayoría de los comprobantes queden esperando a una
        persona en vez de imputarse solos, y es un dato del origen, no una
        limitación de la implementación.
        """
        _, payments = parse_supplier_ledger(fixture("suppliers-ledger-page-2026-08-29.html"))

        assert all(invoice_references_in(payment.reference or "") == [] for payment in payments)
        assert invoice_references_in("Pago de F-8291 y F-6707") == ["F-8291", "F-6707"]


class TestThePurchaseOrders:
    """007: 40 órdenes, cuatro estados, y una sola fecha por orden."""

    def test_it_reads_the_forty_orders_with_their_states(self) -> None:
        """Los conteos por estado son los que midió el relevamiento."""
        orders = parse_purchase_orders(fixture("purchase-orders-page-2026-08-29.html"))

        assert len(orders) == 40
        assert all(order.is_readable for order in orders)
        counts = {
            state: sum(1 for order in orders if order.status_text == state)
            for state in {order.status_text for order in orders}
        }
        assert counts == {
            "Pendiente de envio": 14,
            "Enviada al proveedor": 5,
            "Confirmada por proveedor": 10,
            "Recibida": 11,
        }

    def test_the_state_that_means_arrived_is_the_one_the_portal_writes(self) -> None:
        """D-4: `RECEIVED_STATUS` contra la grafía real, y no contra la recordada.

        `_is_stalled` decide con una comparación de texto exacta: una orden cuyo
        `status_text` es `RECEIVED_STATUS` está terminada y nunca se señala. Si
        el portal cambiara esa grafía —«Recibido», «Recibida ✓», un espacio de
        más—, la constante dejaría de coincidir **en silencio** y las once
        órdenes ya recibidas empezarían a estancarse todas juntas.

        Es la dependencia más frágil de la 007 y no la delata ningún nombre. El
        test la ata al fixture: si la grafía se mueve, rompe acá y no en un
        teléfono a las ocho de la mañana.
        """
        orders = parse_purchase_orders(fixture("purchase-orders-page-2026-08-29.html"))

        arrived = [order for order in orders if order.status_text == RECEIVED_STATUS]

        assert len(arrived) == 11, (
            f"{RECEIVED_STATUS!r} ya no es lo que el portal escribe: "
            f"los estados de la captura son {sorted({o.status_text for o in orders})}"
        )

    def test_an_order_is_one_product_of_the_catalog(self) -> None:
        """Se cruza con el catálogo por código, no por nombre."""
        orders = parse_purchase_orders(fixture("purchase-orders-page-2026-08-29.html"))

        assert all(order.product_code and order.product_code.startswith("COR-") for order in orders)
        assert len({order.number for order in orders}) == 40


class TestTheInbox:
    """007: la bandeja, contra el fixture **capturado del portal real** (2026-08-31).

    Hasta esta captura los tests de esta sección corrían contra un fixture
    **derivado**: el relevamiento contó qué había y no guardó el DOM, así que las
    columnas eran una deducción. Pasaban, y no decían nada sobre la realidad.

    Lo que la captura destapó, en orden de gravedad:

    * la sección **no está en `/mensajes`** sino en `/mensajes-internos`, así que
      la lectura nocturna fallaba siempre;
    * **no hay columna `Tipo`**. El tipo está en el asunto, y leerlo de una
      columna inexistente dejaba los sesenta y siete mensajes sin clasificar —
      con lo que RF-33 y RF-34 no podían dispararse nunca.
    """

    def test_it_reads_the_whole_inbox(self) -> None:
        """Sesenta y siete mensajes y treinta y tres sin leer, al 2026-08-31.

        El relevamiento había medido 64 y 30. La diferencia no es un error de
        nadie: la bandeja recibe mensajes todos los días, y por eso el fixture
        lleva la fecha de su captura en el nombre.
        """
        messages = parse_messages(fixture("messages-page-2026-08-31.html"))

        assert len(messages) == 67
        assert sum(1 for message in messages if not message.already_read) == 33

    def test_the_kind_is_read_from_where_the_portal_writes_it(self) -> None:
        """RF-22: los tres tipos que la spec nombra, tomados del asunto.

        Este test es el que hoy fallaría con el parser anterior: sin columna
        `Tipo` devolvía `None` sesenta y siete veces.
        """
        messages = parse_messages(fixture("messages-page-2026-08-31.html"))

        counts = {
            kind: sum(1 for message in messages if message.kind_text == kind)
            for kind in {message.kind_text for message in messages}
        }
        assert counts == {"Vencimiento proximo": 27, "Reclamo de pago": 24, "Stock bajo": 16}

    def test_every_message_can_be_told_apart_from_the_next_reading(self) -> None:
        """Sin eso, cada lectura de la bandeja registraría los sesenta y siete otra vez.

        La pantalla real **no publica un id**, así que la identidad se arma con
        la fecha, el remitente y el asunto — y que los sesenta y siete sean
        distintos entre sí es lo que hace que eso alcance.
        """
        messages = parse_messages(fixture("messages-page-2026-08-31.html"))

        assert len({message.external_id for message in messages}) == 67


class TestTheSalesScreen:
    """009: 588 registros, y las anomalías que la spec enumera una por una."""

    def test_it_reads_the_five_hundred_and_eighty_eight_records(self) -> None:
        """El total medido, ni uno más ni uno menos."""
        sales = parse_sales(fixture("sales-page-2026-08-29.html"))

        assert len(sales) == 588

    def test_each_broken_record_says_why(self) -> None:
        """RF-16 a RF-19: cada motivo por separado, para poder afirmarlo."""
        sales = parse_sales(fixture("sales-page-2026-08-29.html"))
        reasons = [sale.reason for sale in sales if not sale.is_readable]

        assert len(reasons) == 12
        assert reasons.count("La fila no trae fecha") == 3
        assert reasons.count("La fecha no corresponde a un día que exista") == 3
        assert reasons.count("La fila no trae monto") == 3
        assert reasons.count("La cantidad no puede ser negativa") == 3

    def test_a_date_that_does_not_exist_is_not_rolled_into_the_next_month(self) -> None:
        """`2025-02-31` se aparta. Interpretarlo como el 3 de marzo sería inventar."""
        sales = parse_sales(fixture("sales-page-2026-08-29.html"))
        impossible = [sale for sale in sales if sale.excerpt.count("2025-02-31")]

        assert impossible
        assert all(sale.sold_on is None for sale in impossible)

    def test_normalising_the_code_finds_the_repetitions_the_raw_code_hides(self) -> None:
        """17 grupos mirando el código tal cual, 27 normalizándolo: es RF-10 entero."""
        sales = parse_sales(fixture("sales-page-2026-08-29.html"))
        raw = [sale.code for sale in sales if sale.code]
        keys = [sale.code_key for sale in sales if sale.code_key]

        assert len(raw) - len(set(raw)) == 17
        assert len(keys) - len(set(keys)) == 27

    def test_the_normalisation_only_drops_the_spelling(self) -> None:
        """Un código que difiere en un dígito es otra venta, y ninguna regla lo tapa."""
        assert sale_code_key(" v-00001 ") == sale_code_key("V-00001")
        assert sale_code_key("V-00001") != sale_code_key("V-00002")
