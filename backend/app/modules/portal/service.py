"""Portal business logic: read a section, store it verbatim, say what happened.

This is the module's whole public behaviour, and it is deliberately small. It
downloads, hashes, appends to `raw` and publishes a domain event. It does not
interpret a single cell: interpreting is `ingestion`'s job, and it happens later
over bytes that are already stored — which is what makes the pipeline
reproducible without asking the portal anything again (Artículo III).
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.portal.client import DownloadedDocument, PortalClient, PortalReader
from app.modules.portal.models import PortalDocument, PortalSection
from app.modules.portal.repository import RawDocumentRepository
from app.shared.events import (
    DomainEvent,
    InvoiceFileExtracted,
    InvoiceListExtracted,
    PriceListExtracted,
    ProductHistoryExtracted,
    PurchaseOrdersExtracted,
    SalesExtracted,
    SupplierLedgerExtracted,
    SupplierMessagesExtracted,
    events,
)

logger = get_logger(__name__)


class PortalService:
    """Extracts a section of SIGProv into `raw`, and reports it as a fact."""

    def __init__(
        self,
        session: AsyncSession,
        reader_factory: Callable[[], PortalReader] | None = None,
    ) -> None:
        self.session = session
        self.documents = RawDocumentRepository(session)
        # Injected so the suite can run with the portal switched off (`TEST-03`):
        # the tests hand in a reader backed by the fixtures, and no browser starts.
        self._reader_factory: Callable[[], PortalReader] = reader_factory or PortalClient

    async def extract_price_list(self, *, job_run_id: int | None = None) -> int | None:
        """Bring the file of the day and store it. Returns None if it is not new.

        Idempotent by content hash: the same file downloaded twice is stored
        once and reported once, so re-running the task reprocesses nothing
        (`PY-07`).
        """
        async with self._reader_factory() as reader:
            document = await reader.download_price_list()

        digest = sha256(document.content).hexdigest()
        existing = await self.documents.get_by_hash(digest)
        if existing is not None and existing.normalized_at is not None:
            logger.info("Price list already stored and read, nothing to reprocess")
            return None

        stored = existing or await self.documents.insert(
            section=PortalSection.PRICES,
            content=document.content,
            content_hash=digest,
            content_type=document.content_type,
            job_run_id=job_run_id,
        )
        # The evidence is committed **before** anything tries to interpret it.
        # The day the portal changes its format, the file will fail to parse —
        # and that is precisely the day somebody needs the file to find out
        # why. Keeping the two in one transaction meant every failure of
        # interpretation destroyed its own evidence (Artículo III).
        await self.session.commit()

        await events.publish(
            PriceListExtracted(
                raw_document_id=stored.id,
                content_hash=digest,
                content=document.content,
                content_type=document.content_type,
                fetched_at=stored.fetched_at,
                job_run_id=job_run_id,
            ),
            self.session,
        )
        await self.documents.mark_normalized(stored, datetime.now(UTC))
        await self.session.commit()
        logger.info(
            "Price list extracted",
            extra={"raw_document_id": stored.id, "bytes": len(document.content)},
        )
        return stored.id

    async def extract_product_history(self, product_code: str) -> int | None:
        """Read the history screen the portal publishes for one product.

        Same path as the list, on purpose: `raw` first, then `staging`, then
        `core`. An unreadable history has to have somewhere to be set aside
        (RF-39), and without a row in `staging` there would be no such place.
        """
        async with self._reader_factory() as reader:
            document = await reader.fetch_product_history(product_code)

        digest = sha256(document.content).hexdigest()
        existing = await self.documents.get_by_hash(digest)
        if existing is not None and existing.normalized_at is not None:
            logger.info("Product history already stored", extra={"product_code": product_code})
            return None

        stored = existing or await self.documents.insert(
            section=PortalSection.PRICE_HISTORY,
            content=document.content,
            content_hash=digest,
            content_type=document.content_type,
        )
        # Same order as the list, and for the same reason: what the portal
        # published is kept whether or not we manage to read it.
        await self.session.commit()

        await events.publish(
            ProductHistoryExtracted(
                raw_document_id=stored.id,
                product_code=product_code,
                content_hash=digest,
                content=document.content,
            ),
            self.session,
        )
        await self.documents.mark_normalized(stored, datetime.now(UTC))
        await self.session.commit()
        logger.info(
            "Product history extracted",
            extra={"raw_document_id": stored.id, "product_code": product_code},
        )
        return stored.id

    # --- The sections of 004, 007 and 009 --------------------------------

    async def extract_invoices(self, *, job_run_id: int | None = None) -> int | None:
        """Read the invoices screen and store it. Returns None if it is not new."""

        async def read(reader: PortalReader) -> DownloadedDocument:
            return await reader.fetch_invoices()

        def event(document: PortalDocument) -> DomainEvent:
            return InvoiceListExtracted(
                raw_document_id=document.id,
                content=document.content,
                fetched_at=document.fetched_at,
                job_run_id=job_run_id,
            )

        return await self._extract(
            PortalSection.INVOICES, read, event, job_run_id=job_run_id, label="invoices"
        )

    async def extract_supplier_ledger(self, *, job_run_id: int | None = None) -> int | None:
        """Read the supplier register, every row already expanded."""

        async def read(reader: PortalReader) -> DownloadedDocument:
            return await reader.fetch_supplier_ledger()

        def event(document: PortalDocument) -> DomainEvent:
            return SupplierLedgerExtracted(
                raw_document_id=document.id, content=document.content, job_run_id=job_run_id
            )

        return await self._extract(
            PortalSection.SUPPLIER_LEDGER,
            read,
            event,
            job_run_id=job_run_id,
            label="supplier-ledger",
        )

    async def extract_purchase_orders(self, *, job_run_id: int | None = None) -> int | None:
        """Read the purchase orders screen."""

        async def read(reader: PortalReader) -> DownloadedDocument:
            return await reader.fetch_purchase_orders()

        def event(document: PortalDocument) -> DomainEvent:
            return PurchaseOrdersExtracted(
                raw_document_id=document.id,
                content=document.content,
                fetched_at=document.fetched_at,
                job_run_id=job_run_id,
            )

        return await self._extract(
            PortalSection.PURCHASE_ORDERS,
            read,
            event,
            job_run_id=job_run_id,
            label="purchase-orders",
        )

    async def extract_messages(self, *, job_run_id: int | None = None) -> int | None:
        """Read the inbox of the portal."""

        async def read(reader: PortalReader) -> DownloadedDocument:
            return await reader.fetch_messages()

        def event(document: PortalDocument) -> DomainEvent:
            return SupplierMessagesExtracted(
                raw_document_id=document.id,
                content=document.content,
                fetched_at=document.fetched_at,
                job_run_id=job_run_id,
            )

        return await self._extract(
            PortalSection.MESSAGES, read, event, job_run_id=job_run_id, label="messages"
        )

    async def extract_sales(self, *, job_run_id: int | None = None) -> int | None:
        """Read the sales screen."""

        async def read(reader: PortalReader) -> DownloadedDocument:
            return await reader.fetch_sales()

        def event(document: PortalDocument) -> DomainEvent:
            return SalesExtracted(
                raw_document_id=document.id,
                content=document.content,
                fetched_at=document.fetched_at,
                job_run_id=job_run_id,
            )

        return await self._extract(
            PortalSection.SALES, read, event, job_run_id=job_run_id, label="sales"
        )

    async def extract_invoice_file(self, invoice_number: str, *, file_kind: str = "") -> int | None:
        """Download the document of one invoice and store it verbatim (RF-02, RF-25).

        One visit per invoice, queued by whoever registered it: a hundred
        invoices on day one are a hundred visits to somebody else's system, and
        they are spaced out rather than fired at once.
        """

        async def read(reader: PortalReader) -> DownloadedDocument:
            return await reader.download_invoice_file(invoice_number)

        def event(document: PortalDocument) -> DomainEvent:
            return InvoiceFileExtracted(
                raw_document_id=document.id,
                invoice_number=invoice_number,
                content=document.content,
                content_type=document.content_type,
                file_kind=file_kind,
            )

        return await self._extract(
            PortalSection.INVOICE_FILE, read, event, label=f"invoice-file:{invoice_number}"
        )

    async def _extract(
        self,
        section: PortalSection,
        read: Callable[[PortalReader], Awaitable[DownloadedDocument]],
        build_event: Callable[[PortalDocument], DomainEvent],
        *,
        job_run_id: int | None = None,
        label: str,
    ) -> int | None:
        """Bring one document, store it, and report it as a fact. Once.

        The shape the price list established, factored out rather than copied
        six times: hash, skip what was already read, **commit the evidence
        before anything tries to interpret it**, publish, and only then record
        that the pipeline got through it.

        That order is the part worth keeping: the day the portal changes its
        format the document will fail to parse, and that is exactly the day
        somebody needs the document to find out why (Artículo III).
        """
        async with self._reader_factory() as reader:
            document = await read(reader)

        digest = sha256(document.content).hexdigest()
        existing = await self.documents.get_by_hash(digest)
        if existing is not None and existing.normalized_at is not None:
            logger.info("Section already stored and read", extra={"section": label})
            return None

        stored = existing or await self.documents.insert(
            section=section,
            content=document.content,
            content_hash=digest,
            content_type=document.content_type,
            job_run_id=job_run_id,
        )
        await self.session.commit()

        await events.publish(build_event(stored), self.session)
        await self.documents.mark_normalized(stored, datetime.now(UTC))
        await self.session.commit()
        logger.info(
            "Section extracted",
            extra={"section": label, "raw_document_id": stored.id, "bytes": len(document.content)},
        )
        return stored.id
