"""What the parsers do when the document is not the happy one.

The pinned fixtures cover the file as the portal publishes it. This covers the
edges `add_tests` asks for and the fixtures cannot contain: a listing with no
rows, a document whose structure changed, a sheet that is not where it should
be. All of it still against bytes built here — never against SIGProv (`TEST-03`).

The line these tests draw is the one `ERR-05` draws: a **cell** that cannot be
interpreted is quarantined and never raises, while a **document** that is not
what it claims to be is a technical failure of the extraction and has to be
visible in `operations` instead of quietly producing zero rows.
"""

import io

import pytest
from openpyxl import Workbook

from app.modules.ingestion.parsers import (
    MISSING_PRICE,
    PRICE_NOT_A_NUMBER,
    UNREADABLE_DATE,
    parse_price_list,
    parse_product_history,
)
from app.shared.errors import ExtractionError

pytestmark = [pytest.mark.unit, pytest.mark.portal]

HEADER = ("Codigo", "Descripcion", "Categoria", "Subcategoria", "Precio", "Stock")


def workbook_of(rows: list[tuple[object, ...]], *, sheet_name: str = "Precios") -> bytes:
    """Build a daily file with these rows, in the shape the portal publishes."""
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = sheet_name
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


class TestAListingWithNothingInIt:
    """An empty listing is a consultation that went wrong (RF-41, RF-42)."""

    def test_a_file_with_only_its_header_is_a_failed_consultation(self) -> None:
        """Zero rows would mean the hundred products stopped being listed at once."""
        # Arrange
        content = workbook_of([HEADER])

        # Act / Assert
        with pytest.raises(ExtractionError) as failure:
            parse_price_list(content)
        assert "no data rows" in failure.value.message

    def test_a_file_of_nothing_but_blank_rows_is_a_failed_consultation(self) -> None:
        """The blank rows a spreadsheet drags are not a listing either."""
        # Arrange
        content = workbook_of([HEADER, (None,) * 6, (None,) * 6])

        # Act / Assert
        with pytest.raises(ExtractionError):
            parse_price_list(content)

    def test_trailing_empty_rows_are_not_quarantined(self) -> None:
        """A spreadsheet drags blank rows behind it; they are the end of the sheet."""
        # Arrange
        content = workbook_of(
            [HEADER, ("COR-0001", "Un producto", "RUBRO", "Sub", 1000, 5), (None,) * 6]
        )

        # Act
        rows = parse_price_list(content)

        # Assert
        assert len(rows) == 1
        assert rows[0].is_readable


class TestADocumentThatIsNotWhatItClaims:
    """The portal changed, and that has to be loud."""

    def test_a_file_without_the_expected_columns_is_a_technical_failure(self) -> None:
        """Silently reading zero products would look exactly like a quiet Sunday."""
        # Arrange
        content = workbook_of([("Producto", "Valor"), ("COR-0001", 1000)])

        # Act / Assert
        with pytest.raises(ExtractionError) as failure:
            parse_price_list(content)
        assert "Codigo" in str(failure.value.details["missing"])

    def test_a_file_missing_only_the_price_column_is_a_technical_failure(self) -> None:
        """Every row would be quarantined for the same reason: that is not data, it is format."""
        # Arrange
        content = workbook_of([("Codigo", "Descripcion"), ("COR-0001", "Un producto")])

        # Act / Assert
        with pytest.raises(ExtractionError):
            parse_price_list(content)

    def test_an_empty_file_is_a_technical_failure(self) -> None:
        """Not even a header: there is nothing to decide about."""
        # Arrange
        content = workbook_of([])

        # Act / Assert
        with pytest.raises(ExtractionError):
            parse_price_list(content)

    def test_a_renamed_sheet_is_still_read(self) -> None:
        """The columns are the contract, not the tab they sit on."""
        # Arrange
        content = workbook_of(
            [HEADER, ("COR-0001", "Un producto", "RUBRO", "Sub", 1000, 5)],
            sheet_name="Hoja1",
        )

        # Act
        rows = parse_price_list(content)

        # Assert
        assert len(rows) == 1
        assert rows[0].product_code == "COR-0001"


class TestCellsAtTheirEdges:
    """One bad cell is a case for a person, never an exception."""

    def test_a_price_of_zero_is_read_as_a_price(self) -> None:
        """Zero is a number. Whether the business likes it is not the parser's call."""
        # Arrange
        content = workbook_of([HEADER, ("COR-0001", "Un producto", "R", "S", 0, 5)])

        # Act
        rows = parse_price_list(content)

        # Assert
        assert rows[0].is_readable
        assert rows[0].price == 0

    def test_a_row_with_no_price_column_value_is_quarantined(self) -> None:
        """The row exists, the price does not: a person decides what it was."""
        # Arrange
        content = workbook_of([HEADER, ("COR-0001", "Un producto", "R", "S", None, 5)])

        # Act
        rows = parse_price_list(content)

        # Assert
        assert rows[0].reason == MISSING_PRICE

    def test_a_row_without_categories_is_still_readable(self) -> None:
        """Some products come with no rubro at all, and P1 does not interpret rubros."""
        # Arrange
        content = workbook_of([HEADER, ("COR-0001", "Un producto", None, None, 1000, 5)])

        # Act
        rows = parse_price_list(content)

        # Assert
        assert rows[0].is_readable
        assert rows[0].category_raw is None


class TestTheHistoryScreenAtItsEdges:
    """The screen where the price arrives as text."""

    def test_a_page_without_a_table_is_a_technical_failure(self) -> None:
        """A product page that lost its table is the portal changing, not a datum."""
        # Act / Assert
        with pytest.raises(ExtractionError):
            parse_product_history(b"<html><body><h1>COR-0001</h1></body></html>")

    def test_a_table_that_publishes_no_price_is_not_a_failure(self) -> None:
        """A product with no history yet is a fact, not a technical failure (RF-43)."""
        # Arrange
        page = (
            b'<table class="datos">'
            b"<thead><tr><th>Fecha</th><th>Precio</th><th>Variacion</th></tr></thead>"
            b"<tbody></tbody></table>"
        )

        # Act
        points = parse_product_history(page)

        # Assert
        assert points == []

    def test_the_header_row_is_not_read_as_a_point(self) -> None:
        """`Fecha | Precio | Variacion` is not a price of anything."""
        # Arrange
        page = (
            b'<table class="datos">'
            b"<thead><tr><th>Fecha</th><th>Precio</th><th>Variacion</th></tr></thead>"
            b"<tbody><tr><td>2026-01-06</td><td>$1.000</td><td>-</td></tr></tbody>"
            b"</table>"
        )

        # Act
        points = parse_product_history(page)

        # Assert
        assert len(points) == 1
        assert points[0].is_readable

    def test_a_price_with_cents_is_read(self) -> None:
        """The hundred products have none, but the format admits them."""
        # Arrange
        page = (
            b'<table class="datos"><tbody>'
            b"<tr><td>2026-01-06</td><td>$1.234,50</td><td>-</td></tr>"
            b"</tbody></table>"
        )

        # Act
        points = parse_product_history(page)

        # Assert
        assert str(points[0].price) == "1234.50"

    def test_a_row_with_a_single_cell_is_quarantined(self) -> None:
        """Half a row is not a point, and it is not a reason to lose the rest."""
        # Arrange
        page = (
            b'<table class="datos"><tbody>'
            b"<tr><td>2026-01-06</td></tr>"
            b"<tr><td>2026-02-06</td><td>$2.000</td><td>-</td></tr>"
            b"</tbody></table>"
        )

        # Act
        points = parse_product_history(page)

        # Assert
        assert points[0].reason == UNREADABLE_DATE
        assert points[1].is_readable

    def test_a_negative_price_in_the_history_is_quarantined(self) -> None:
        """A price below zero is not a price, on either screen."""
        # Arrange
        page = (
            b'<table class="datos"><tbody>'
            b"<tr><td>2026-01-06</td><td>$-500</td><td>-</td></tr>"
            b"</tbody></table>"
        )

        # Act
        points = parse_product_history(page)

        # Assert
        assert points[0].reason is not None
        assert points[0].price is None

    def test_only_the_first_table_of_the_page_is_read(self) -> None:
        """The screen also carries navigation and notes; the prices are the first table."""
        # Arrange
        page = (
            b'<table class="datos"><tbody>'
            b"<tr><td>2026-01-06</td><td>$1.000</td><td>-</td></tr>"
            b"</tbody></table>"
            b'<table class="datos"><tbody>'
            b"<tr><td>otra cosa</td><td>que no es un precio</td></tr>"
            b"</tbody></table>"
        )

        # Act
        points = parse_product_history(page)

        # Assert
        assert len(points) == 1

    def test_a_price_that_is_not_a_number_is_quarantined(self) -> None:
        """`ERR-05`: it goes to a person, it does not stop the import."""
        # Arrange
        page = (
            b'<table class="datos"><tbody>'
            b"<tr><td>2026-01-06</td><td>a convenir</td><td>-</td></tr>"
            b"</tbody></table>"
        )

        # Act
        points = parse_product_history(page)

        # Assert
        assert points[0].reason == PRICE_NOT_A_NUMBER
