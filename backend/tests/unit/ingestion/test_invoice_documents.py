"""Los tres lectores del archivo de una factura, contra los cuatro fijados.

Lo que se prueba acá no es "el OCR anda": es que **lo que dice el archivo se
puede comparar con lo que dice la tabla**, que es la señal sobre la que se apoya
toda la 004. Un archivo que coincide entra sin molestar a nadie; uno que no
coincide, o que no se pudo leer, va a revisión con el recorte a la vista.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.modules.ingestion.documents import read_invoice_document

pytestmark = [pytest.mark.unit, pytest.mark.portal]

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "portal"

# Los cuatro datos que la tabla publica para cada una de estas tres facturas.
# Están escritos acá y no leídos del fixture a propósito: el test compara dos
# lecturas independientes, y leer las dos del mismo lugar no compararía nada.
FROM_THE_TABLE = {
    "invoice-F-8411-text.pdf": ("PDF", "F-8411", date(2025, 1, 3), Decimal("581230")),
    "invoice-F-9936-scanned.pdf": (
        "PDF (escaneado)",
        "F-9936",
        date(2024, 8, 7),
        Decimal("442965"),
    ),
    "invoice-F-7797.xlsx": ("Excel", "F-7797", date(2026, 5, 3), Decimal("223376")),
}


@pytest.mark.parametrize("name", sorted(FROM_THE_TABLE))
def test_the_three_formats_are_read_and_agree_with_the_table(name: str) -> None:
    """Los tres formatos se leen, y los tres dicen lo mismo que la tabla."""
    kind, number, issued_on, total = FROM_THE_TABLE[name]

    reading = read_invoice_document((FIXTURES / name).read_bytes(), file_kind=kind)

    assert reading.readable
    assert reading.number == number
    assert reading.issued_on == issued_on
    assert reading.total == total
    assert reading.agrees_with(number=number, issued_on=issued_on, total=total)


def test_the_date_inside_the_document_is_day_first() -> None:
    """`03/05/2026` es el 3 de mayo, no el 5 de marzo.

    Es la trampa más barata de pisar y la más silenciosa: al revés, el archivo
    discrepa con la tabla en las cien facturas y todas van a revisión.
    """
    reading = read_invoice_document(
        (FIXTURES / "invoice-F-7797.xlsx").read_bytes(), file_kind="Excel"
    )

    assert reading.issued_on == date(2026, 5, 3)


def test_no_tax_id_is_read_from_the_document() -> None:
    """El único CUIT impreso es el de Cordillera, el cliente, no el del emisor.

    Un lector que se quedara con el primero que encuentra le asignaría el mismo
    proveedor a las cien facturas. Por eso acá no se lee ninguno: el proveedor
    viaja como el nombre que el documento imprime, y resolverlo es de
    `purchases`, contra el padrón.
    """
    reading = read_invoice_document(
        (FIXTURES / "invoice-F-8411-text.pdf").read_bytes(), file_kind="PDF"
    )

    assert reading.supplier_text == "Ferretera del Norte S.R.L."
    assert not hasattr(reading, "tax_id")


def test_the_spreadsheet_is_read_by_label_and_not_by_position() -> None:
    """El encabezado está corrido a `A2`, con filas vacías y un `TOTAL` al pie."""
    reading = read_invoice_document(
        (FIXTURES / "invoice-F-7797.xlsx").read_bytes(), file_kind="Excel"
    )

    assert reading.number == "F-7797"
    assert reading.total == Decimal("223376")


def test_a_file_that_cannot_be_read_says_so_instead_of_raising() -> None:
    """Un archivo ilegible es una factura que va a una persona, no una excepción."""
    reading = read_invoice_document(b"esto no es un documento", file_kind="PDF")

    assert reading.readable is False
    assert reading.reason
    assert reading.agrees_with(number="F-1", issued_on=date(2026, 1, 1), total=Decimal(1)) is False


def test_a_reading_that_confirms_nothing_is_not_agreement() -> None:
    """Un archivo que se leyó y no dice nada reconocible no confirma la tabla."""
    reading = read_invoice_document(b"", file_kind="PDF")

    assert reading.agrees_with(number="F-1", issued_on=None, total=None) is False


def test_a_document_that_says_something_else_disagrees() -> None:
    """Y eso es exactamente lo que manda la factura a revisión (RF-29, RF-30)."""
    reading = read_invoice_document(
        (FIXTURES / "invoice-F-8411-text.pdf").read_bytes(), file_kind="PDF"
    )

    assert (
        reading.agrees_with(number="F-8411", issued_on=date(2025, 1, 3), total=Decimal("999999"))
        is False
    )


def test_a_field_the_document_does_not_carry_is_not_a_disagreement() -> None:
    """Es una confirmación menos, no una contradicción."""
    reading = read_invoice_document(
        (FIXTURES / "invoice-F-8411-text.pdf").read_bytes(), file_kind="PDF"
    )

    assert reading.agrees_with(number="F-8411", issued_on=None, total=None) is True
