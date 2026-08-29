"""The two parsers of the price update. Pure functions, and nothing else.

They receive bytes and return typed rows. They never touch the database, never
touch the network, and never raise over a bad cell: a value that cannot be
interpreted comes back marked with the reason it could not, and quarantining it
is the service's job (`ERR-05`).

The only thing they do raise is `ExtractionError`, and only when the *document*
is not what it claims to be — a missing sheet, missing columns, no table. That
is a technical failure of the extraction, not a data problem, and it has to be
visible in `operations` instead of quietly producing zero rows.

Both are tested against the files pinned in `tests/fixtures/portal/`, never
against the live portal (`TEST-03`).
"""

import io
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser

from openpyxl import load_workbook

from app.shared.errors import ExtractionError

# --- The daily file ------------------------------------------------------

SHEET_NAME = "Precios"
# The header the portal writes, in the order it writes it. Surveyed on
# 2026-08-29 and pinned as a fixture: `Codigo`, `Descripcion`, `Categoria`,
# `Subcategoria`, `Precio`, `Stock`.
REQUIRED_COLUMNS = ("Codigo", "Descripcion", "Precio")

# What a person reads next to the row in the review screen, so it is written in
# Spanish like everything else the user sees.
MISSING_CODE = "La fila no trae código de producto"
DUPLICATE_CODE = "El código está repetido en el archivo"
MISSING_PRICE = "La fila no trae precio"
PRICE_NOT_A_NUMBER = "El precio no es un número"
PRICE_AS_TEXT = "El precio vino como texto y no como número"
NEGATIVE_PRICE = "El precio no puede ser negativo"
UNREADABLE_DATE = "La fecha no se pudo interpretar"

DEFAULT_CURRENCY = "ARS"


@dataclass(frozen=True, slots=True)
class ParsedPriceRow:
    """One line of the daily file, as far as it could be read.

    `reason` is what says whether it could: `None` means the row is usable, and
    anything else is the sentence a person will read next to it.
    """

    line_number: int
    excerpt: str
    product_code: str | None = None
    description: str | None = None
    price: Decimal | None = None
    category_raw: str | None = None
    subcategory_raw: str | None = None
    reason: str | None = None

    @property
    def is_readable(self) -> bool:
        return self.reason is None


@dataclass(frozen=True, slots=True)
class ParsedHistoryPoint:
    """One row of the history screen of a product."""

    line_number: int
    excerpt: str
    price: Decimal | None = None
    changed_at: datetime | None = None
    reason: str | None = None

    @property
    def is_readable(self) -> bool:
        return self.reason is None


def _cell_text(value: object) -> str:
    """Render a cell for the excerpt, without inventing anything."""
    return "" if value is None else str(value)


def _read_price(value: object) -> tuple[Decimal | None, str | None]:
    """Interpret the price cell of the daily file.

    In this file the price is an integer — `$48.210` on screen is `48210` here,
    and the dot is a thousands separator, not a decimal point. A price that
    arrives as text is therefore **not** interpreted: `"48.210"` could be forty
    eight thousand or forty eight, and guessing between them in a system that
    controls what the business is invoiced is not a shortcut worth taking. It
    goes to a person.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, MISSING_PRICE
    if isinstance(value, bool) or not isinstance(value, int | float | Decimal):
        text = str(value).strip()
        try:
            Decimal(text.replace(".", "").replace(",", "."))
        except (InvalidOperation, ArithmeticError):
            return None, PRICE_NOT_A_NUMBER
        return None, PRICE_AS_TEXT
    price = Decimal(str(value))
    if price < 0:
        return None, NEGATIVE_PRICE
    return price, None


def parse_price_list(content: bytes) -> list[ParsedPriceRow]:
    """Read the file of the day into rows, marking the ones that cannot be read.

    One bad cell never stops the rest: that is RF-06, and it is why this returns
    a list instead of raising.
    """
    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as error:  # openpyxl raises a zoo of exceptions on bad input
        raise ExtractionError(
            "The daily file could not be opened", details={"reason": type(error).__name__}
        ) from error

    try:
        sheet = (
            workbook[SHEET_NAME] if SHEET_NAME in workbook.sheetnames else workbook.worksheets[0]
        )
        rows = list(sheet.iter_rows(values_only=True))
    finally:
        workbook.close()

    if not rows:
        raise ExtractionError("The daily file has no rows")

    header = [_cell_text(cell).strip() for cell in rows[0]]
    missing = [column for column in REQUIRED_COLUMNS if column not in header]
    if missing:
        raise ExtractionError(
            "The daily file does not have the expected columns",
            details={"missing": missing, "found": header},
        )

    index = {name: position for position, name in enumerate(header)}

    def column(row: tuple[object, ...], name: str) -> object:
        position = index.get(name)
        return None if position is None or position >= len(row) else row[position]

    parsed: list[ParsedPriceRow] = []
    seen_codes: set[str] = set()

    for offset, row in enumerate(rows[1:], start=2):
        excerpt = " | ".join(_cell_text(cell) for cell in row)
        code = _cell_text(column(row, "Codigo")).strip()
        description = _cell_text(column(row, "Descripcion")).strip()
        category = _cell_text(column(row, "Categoria")).strip() or None
        subcategory = _cell_text(column(row, "Subcategoria")).strip() or None

        if not code and not description and not excerpt.strip(" |"):
            # A trailing empty row is not a data problem, it is the end of the
            # sheet. Nothing to set aside.
            continue

        def row_of(
            *,
            product_code: str | None = None,
            price: Decimal | None = None,
            reason: str | None = None,
            line_number: int = offset,
            excerpt: str = excerpt,
            description: str | None = description or None,
            category_raw: str | None = category,
            subcategory_raw: str | None = subcategory,
        ) -> ParsedPriceRow:
            """Build the row of this line, whatever could be read of it."""
            return ParsedPriceRow(
                line_number=line_number,
                excerpt=excerpt,
                product_code=product_code,
                description=description,
                price=price,
                category_raw=category_raw,
                subcategory_raw=subcategory_raw,
                reason=reason,
            )

        if not code:
            parsed.append(row_of(reason=MISSING_CODE))
            continue
        if code in seen_codes:
            parsed.append(row_of(product_code=code, reason=DUPLICATE_CODE))
            continue
        seen_codes.add(code)

        price, reason = _read_price(column(row, "Precio"))
        parsed.append(row_of(product_code=code, price=price, reason=reason))

    if not parsed:
        # Headers and nothing else. Letting this through would mean telling
        # `catalog` that every known product stopped being listed, which floods
        # the review queue with a hundred cases nobody caused and still closes
        # the run as successful (RF-41, RF-42). An empty list is a consultation
        # that went wrong, and it takes the same path as any other failure.
        raise ExtractionError("The daily file has no data rows")

    return parsed


# --- The published history of one product --------------------------------

# `$25.308` on the history screen: the dot separates thousands, and there are no
# cents anywhere in the hundred products the portal publishes.
MONEY = re.compile(r"^\$?\s*(-?[\d.]+)(?:,(\d{1,2}))?$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class _TableRows(HTMLParser):
    """Collects the body rows of the first `table.datos` of a page.

    A hand-written collector rather than a dependency: the portal serves one
    plain table per screen, and a parser this small does not justify pulling an
    HTML library into the build.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self.found = False
        self._in_table = False
        self._done = False
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._is_header = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "table" and not self._done:
            self._in_table = "datos" in (attributes.get("class") or "")
            self.found = self.found or self._in_table
        elif self._in_table and tag == "tr":
            self._row = []
            self._is_header = False
        elif self._in_table and tag in {"td", "th"}:
            self._cell = []
            self._is_header = self._is_header or tag == "th"

    def handle_endtag(self, tag: str) -> None:
        if not self._in_table:
            return
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if not self._is_header:
                self.rows.append(self._row)
            self._row = None
        elif tag == "table":
            self._in_table = False
            self._done = bool(self.rows)

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def _read_history_price(text: str) -> tuple[Decimal | None, str | None]:
    """Interpret `$25.308` — thousands separated by dots, cents after a comma."""
    match = MONEY.match(text.strip())
    if match is None:
        return None, PRICE_NOT_A_NUMBER
    whole = match.group(1).replace(".", "")
    cents = match.group(2) or "0"
    try:
        price = Decimal(f"{whole}.{cents}")
    except (InvalidOperation, ArithmeticError):
        return None, PRICE_NOT_A_NUMBER
    if price < 0:
        return None, NEGATIVE_PRICE
    return price, None


def parse_product_history(content: bytes) -> list[ParsedHistoryPoint]:
    """Read the history screen of a product into points.

    The *Variacion vs. anterior* column the portal shows is not read: it is
    derivable from two consecutive points, and storing it would mean having two
    sources for the same number.
    """
    parser = _TableRows()
    parser.feed(content.decode("utf-8", errors="replace"))
    parser.close()

    if not parser.found:
        # No table at all: the portal changed and this parser stopped
        # understanding what it reads. That is a technical failure.
        raise ExtractionError("The history screen has no table of prices")

    if not parser.rows:
        # The table is there and publishes no price: the product has no history
        # yet. A fact, not a failure — it ends without points and without noise,
        # and the current price of the product is left alone (RF-43).
        return []

    points: list[ParsedHistoryPoint] = []
    for offset, cells in enumerate(parser.rows, start=1):
        excerpt = " | ".join(cells)
        if len(cells) < 2:
            points.append(
                ParsedHistoryPoint(line_number=offset, excerpt=excerpt, reason=UNREADABLE_DATE)
            )
            continue

        raw_date, raw_price = cells[0].strip(), cells[1].strip()
        if not ISO_DATE.match(raw_date):
            points.append(
                ParsedHistoryPoint(line_number=offset, excerpt=excerpt, reason=UNREADABLE_DATE)
            )
            continue
        try:
            changed_at = datetime.strptime(raw_date, "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError:
            points.append(
                ParsedHistoryPoint(line_number=offset, excerpt=excerpt, reason=UNREADABLE_DATE)
            )
            continue

        price, reason = _read_history_price(raw_price)
        points.append(
            ParsedHistoryPoint(
                line_number=offset,
                excerpt=excerpt,
                price=price,
                changed_at=changed_at,
                reason=reason,
            )
        )

    return points
