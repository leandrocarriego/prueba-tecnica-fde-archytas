"""The two parsers, against the files pinned in `tests/fixtures/portal/`.

`TEST-03` is a Blocker: a parser is never tested against the live portal. The
corollary is that this whole file runs with SIGProv switched off, and that is
what makes it reproducible — the portal changing tomorrow breaks a fixture on
purpose, not a test at random.

The totals asserted here come from the fixture's own README: 101 data rows in
the broken file, 95 readable (94 known products plus one the catalog will not
know) and 6 set aside, one per way a cell can be wrong.
"""

from decimal import Decimal
from pathlib import Path

import pytest

from app.modules.ingestion.parsers import (
    DUPLICATE_CODE,
    MISSING_CODE,
    MISSING_PRICE,
    NEGATIVE_PRICE,
    PRICE_AS_TEXT,
    PRICE_NOT_A_NUMBER,
    UNREADABLE_DATE,
    parse_price_list,
    parse_product_history,
)
from app.shared.errors import ExtractionError

pytestmark = [pytest.mark.unit, pytest.mark.portal]

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "portal"
PRICE_LIST = FIXTURES / "price-list-2026-08-28.xlsx"
BROKEN_LIST = FIXTURES / "price-list-broken-2026-08-28.xlsx"
HISTORY_PAGE = FIXTURES / "price-history-page-2026-08-28.html"

# Line numbers are the ones in the sheet, header included, so a person reviewing
# a case can open the file and land on the row.
EXPECTED_QUARANTINE: dict[int, str] = {
    8: PRICE_NOT_A_NUMBER,
    14: MISSING_PRICE,
    22: NEGATIVE_PRICE,
    35: PRICE_AS_TEXT,
    51: MISSING_CODE,
    67: DUPLICATE_CODE,
}


class TestPriceList:
    """The file of the day."""

    def test_reads_every_row_of_a_clean_file(self) -> None:
        """A hundred products, all of them usable."""
        # Act
        rows = parse_price_list(PRICE_LIST.read_bytes())

        # Assert
        assert len(rows) == 100
        assert all(row.is_readable for row in rows)

    def test_keeps_code_description_and_price(self) -> None:
        """The three fields the prices screen shows (RF-04)."""
        # Act
        first = parse_price_list(PRICE_LIST.read_bytes())[0]

        # Assert
        assert first.product_code == "COR-0001"
        assert first.description == "Adhesivos - Articulo 1"
        # `$48.210` on screen is 48210 in the file: the dot separates thousands.
        assert first.price == Decimal("48210")

    def test_keeps_the_categories_exactly_as_they_came(self) -> None:
        """P1 does not interpret them, it only refuses to lose them."""
        # Act
        first = parse_price_list(PRICE_LIST.read_bytes())[0]

        # Assert
        assert first.category_raw == "PINTURAS Y ADHESIVOS"
        assert first.subcategory_raw == "Adhesivos"

    def test_a_broken_row_does_not_stop_the_others(self) -> None:
        """RF-06: the rest of the list is interpreted just the same."""
        # Act
        rows = parse_price_list(BROKEN_LIST.read_bytes())

        # Assert
        assert len(rows) == 101
        assert sum(row.is_readable for row in rows) == 95
        assert sum(not row.is_readable for row in rows) == 6

    @pytest.mark.parametrize(
        ("line_number", "reason"), sorted(EXPECTED_QUARANTINE.items()), ids=str
    )
    def test_each_broken_cell_says_why(self, line_number: int, reason: str) -> None:
        """Every case is set aside for a reason a person can read (RF-26)."""
        # Arrange
        rows = {row.line_number: row for row in parse_price_list(BROKEN_LIST.read_bytes())}

        # Assert
        assert rows[line_number].reason == reason

    def test_a_price_written_as_text_is_not_guessed(self) -> None:
        """`"48.210"` could be 48210 or 48.21, and this system does not guess.

        It controls what the business is invoiced, so the row goes to a person
        instead of to a rounding decision nobody would ever see.
        """
        # Act
        rows = {row.line_number: row for row in parse_price_list(BROKEN_LIST.read_bytes())}

        # Assert
        assert rows[35].price is None
        assert rows[35].reason == PRICE_AS_TEXT

    def test_a_row_that_is_set_aside_keeps_what_the_file_said(self) -> None:
        """Without the excerpt, whoever reviews the case is guessing too."""
        # Act
        rows = {row.line_number: row for row in parse_price_list(BROKEN_LIST.read_bytes())}

        # Assert
        assert "CONSULTAR" in rows[8].excerpt

    def test_an_unknown_product_is_not_a_broken_row(self) -> None:
        """It reads perfectly. Whether the catalog knows it is not the parser's business."""
        # Act
        last = parse_price_list(BROKEN_LIST.read_bytes())[-1]

        # Assert
        assert last.product_code == "COR-0999"
        assert last.is_readable

    def test_a_file_that_is_not_a_spreadsheet_is_a_technical_failure(self) -> None:
        """A document that is not what it claims is not a data problem (`ERR-05`)."""
        # Act / Assert
        with pytest.raises(ExtractionError):
            parse_price_list(b"this is not a workbook")


class TestProductHistory:
    """The history screen the portal publishes for one product."""

    def test_reads_every_published_point(self) -> None:
        """The screen says eleven records, and eleven come back (RF-38)."""
        # Act
        points = parse_product_history(HISTORY_PAGE.read_bytes())

        # Assert
        assert len(points) == 11
        assert all(point.is_readable for point in points)

    def test_reads_the_price_as_text_with_a_thousands_separator(self) -> None:
        """Here the price *is* text — `$25.308` — unlike in the daily file."""
        # Act
        first = parse_product_history(HISTORY_PAGE.read_bytes())[0]

        # Assert
        assert first.price == Decimal("25308")
        assert first.changed_at is not None
        assert first.changed_at.date().isoformat() == "2023-01-01"

    def test_the_variation_column_is_not_read(self) -> None:
        """It is derivable from two points, and two sources for one number is one too many."""
        # Act
        points = parse_product_history(HISTORY_PAGE.read_bytes())

        # Assert
        assert not any(hasattr(point, "variation") for point in points)

    def test_an_unreadable_date_is_set_aside(self) -> None:
        """RF-39: it is quarantined, and the rest of the history still lands."""
        # Arrange
        page = (
            b'<table class="datos"><tbody>'
            b"<tr><td>ayer</td><td>$1.000</td><td>-</td></tr>"
            b"<tr><td>2026-01-06</td><td>$2.000</td><td>+10%</td></tr>"
            b"</tbody></table>"
        )

        # Act
        points = parse_product_history(page)

        # Assert
        assert points[0].reason == UNREADABLE_DATE
        assert points[1].price == Decimal("2000")

    def test_an_unreadable_price_is_set_aside(self) -> None:
        """The point is quarantined; nothing about the product's current price moves."""
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

    def test_a_screen_without_a_table_is_a_technical_failure(self) -> None:
        """The portal changed, and that has to be visible instead of silently empty."""
        # Act / Assert
        with pytest.raises(ExtractionError):
            parse_product_history(b"<html><body><p>Sin datos</p></body></html>")
