"""A portal that answers from the fixtures instead of from the network.

`TEST-03` is a Blocker: the suite never opens a browser and never reaches
SIGProv. `PortalService` takes its reader as a dependency precisely so this can
be handed in, and the whole pipeline — download, hash, `raw`, `staging`, `core`
— can be exercised with the portal switched off.
"""

import io
from pathlib import Path
from types import TracebackType
from typing import Self

from openpyxl import load_workbook

from app.modules.portal.client import (
    HTML_CONTENT_TYPE,
    PDF_CONTENT_TYPE,
    XLSX_CONTENT_TYPE,
    DownloadedDocument,
)
from app.shared.errors import ExtractionError

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "portal"
PRICE_LIST = FIXTURES / "price-list-2026-08-28.xlsx"
BROKEN_LIST = FIXTURES / "price-list-broken-2026-08-28.xlsx"
HISTORY_PAGE = FIXTURES / "price-history-page-2026-08-28.html"
INVOICES_PAGE = FIXTURES / "invoices-page-2026-08-29.html"
INVOICE_FILE = FIXTURES / "invoice-F-8411-text.pdf"
SUPPLIER_LEDGER = FIXTURES / "suppliers-ledger-page-2026-08-29.html"

PRICE_COLUMN = 5
CODE_COLUMN = 1
FIRST_DATA_ROW = 2


def price_list_bytes() -> bytes:
    """The daily file exactly as the portal published it."""
    return PRICE_LIST.read_bytes()


def broken_list_bytes() -> bytes:
    """The same file with one cell broken per row, derived by hand."""
    return BROKEN_LIST.read_bytes()


def history_page_bytes() -> bytes:
    """The history screen of `COR-0001`, as rendered."""
    return HISTORY_PAGE.read_bytes()


def invoices_page_bytes() -> bytes:
    """The invoices screen, captured from the portal with its hundred rows."""
    return INVOICES_PAGE.read_bytes()


def invoice_file_bytes() -> bytes:
    """The document of one invoice, as the supplier sent it: a PDF with a text layer."""
    return INVOICE_FILE.read_bytes()


def supplier_ledger_bytes() -> bytes:
    """The supplier register, with its eight rows already expanded."""
    return SUPPLIER_LEDGER.read_bytes()


def price_list_with(
    *, prices: dict[str, int] | None = None, without: set[str] | None = None
) -> bytes:
    """Derive a daily file from the pinned one: change prices, drop products.

    Deriving instead of writing a spreadsheet from scratch keeps every test
    honest about the real shape of the file — six columns, a header row, prices
    as integers.
    """
    workbook = load_workbook(io.BytesIO(price_list_bytes()))
    sheet = workbook.active
    if sheet is None:  # pragma: no cover - the fixture always has a sheet
        raise ExtractionError("The fixture has no sheet")

    dropped = []
    for row in range(FIRST_DATA_ROW, sheet.max_row + 1):
        code = sheet.cell(row=row, column=CODE_COLUMN).value
        if without and code in without:
            dropped.append(row)
            continue
        if prices and code in prices:
            sheet.cell(row=row, column=PRICE_COLUMN).value = prices[code]

    for row in reversed(dropped):
        sheet.delete_rows(row)

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


class FakePortal:
    """A `PortalReader` that answers from bytes handed to it."""

    def __init__(
        self,
        *,
        price_list: bytes | None = None,
        history: bytes | None = None,
        invoices: bytes | None = None,
        invoice_file: bytes | None = None,
        ledger: bytes | None = None,
        fails_with: ExtractionError | None = None,
    ) -> None:
        self.price_list = price_list if price_list is not None else price_list_bytes()
        self.history = history if history is not None else history_page_bytes()
        self.invoices = invoices if invoices is not None else invoices_page_bytes()
        self.invoice_file = invoice_file if invoice_file is not None else invoice_file_bytes()
        self.supplier_ledger = ledger if ledger is not None else supplier_ledger_bytes()
        self.fails_with = fails_with
        self.downloads = 0
        self.history_visits: list[str] = []
        self.invoice_visits = 0
        self.invoice_file_visits: list[str] = []
        self.ledger_visits = 0

    def __call__(self) -> Self:
        """Usable as the `reader_factory` the service expects."""
        return self

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def download_price_list(self) -> DownloadedDocument:
        """Hand back the file, or fail the way the portal fails."""
        if self.fails_with is not None:
            raise self.fails_with
        self.downloads += 1
        return DownloadedDocument(
            content=self.price_list,
            content_type=XLSX_CONTENT_TYPE,
            filename="Lista_Precios_Cordillera.xlsx",
        )

    async def fetch_product_history(self, product_code: str) -> DownloadedDocument:
        """Hand back the history screen of a product."""
        if self.fails_with is not None:
            raise self.fails_with
        self.history_visits.append(product_code)
        return DownloadedDocument(
            content=self.history,
            content_type=HTML_CONTENT_TYPE,
            filename=f"{product_code}.html",
        )

    async def fetch_invoices(self) -> DownloadedDocument:
        """Hand back the invoices screen, rendered."""
        if self.fails_with is not None:
            raise self.fails_with
        self.invoice_visits += 1
        return DownloadedDocument(
            content=self.invoices,
            content_type=HTML_CONTENT_TYPE,
            filename="facturas.html",
        )

    async def download_invoice_file(self, invoice_number: str) -> DownloadedDocument:
        """Hand back the document of one invoice.

        The visits are counted because the portal is somebody else's system with
        a shared account: a task that asks twice for a file it already has is a
        cost this side cannot see and the other side can.
        """
        if self.fails_with is not None:
            raise self.fails_with
        self.invoice_file_visits.append(invoice_number)
        return DownloadedDocument(
            content=self.invoice_file,
            content_type=PDF_CONTENT_TYPE,
            filename=f"{invoice_number}.pdf",
        )

    async def fetch_supplier_ledger(self) -> DownloadedDocument:
        """Hand back the supplier register, every row expanded."""
        if self.fails_with is not None:
            raise self.fails_with
        self.ledger_visits += 1
        return DownloadedDocument(
            content=self.supplier_ledger,
            content_type=HTML_CONTENT_TYPE,
            filename="estado-cuenta.html",
        )
