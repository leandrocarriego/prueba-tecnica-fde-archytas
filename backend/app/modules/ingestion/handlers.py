"""What `ingestion` does when something happens elsewhere.

One subscription per section the portal stores, plus the two that keep the
projection of what a person already decided. None of them knows who published:
the portal stored a document, or `triage` recorded (or revoked) a decision.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.ingestion.service import IngestionService
from app.shared.events import (
    InvoiceFileExtracted,
    InvoiceListExtracted,
    PriceListExtracted,
    ProductHistoryExtracted,
    PurchaseOrdersExtracted,
    QuarantineCaseResolved,
    QuarantineRuleRevoked,
    SalesExtracted,
    SupplierLedgerExtracted,
    SupplierMessagesExtracted,
    events,
)

logger = get_logger(__name__)


@events.subscribe(PriceListExtracted)
async def normalize_extracted_list(event: PriceListExtracted, session: AsyncSession) -> None:
    """Type the file that was just stored, row by row."""
    await IngestionService(session).normalize_price_list(
        raw_document_id=event.raw_document_id,
        content=event.content,
        job_run_id=event.job_run_id,
    )


@events.subscribe(ProductHistoryExtracted)
async def normalize_extracted_history(
    event: ProductHistoryExtracted, session: AsyncSession
) -> None:
    """Type the history screen that was just stored."""
    await IngestionService(session).normalize_product_history(
        raw_document_id=event.raw_document_id,
        product_code=event.product_code,
        content=event.content,
    )


@events.subscribe(QuarantineCaseResolved)
async def remember_decision(event: QuarantineCaseResolved, session: AsyncSession) -> None:
    """Keep the decision so the same case is not asked about twice (RF-34)."""
    if event.rule_id is None:
        # The person decided about this one case only. There is nothing to
        # reapply, so nothing to remember here.
        return
    await IngestionService(session).learn_rule(
        rule_id=event.rule_id,
        kind=event.kind,
        matcher=event.matcher,
        decision=event.decision,
    )


@events.subscribe(QuarantineRuleRevoked)
async def forget_decision(event: QuarantineRuleRevoked, session: AsyncSession) -> None:
    """Stop applying a rule that was left without effect (RF-37)."""
    await IngestionService(session).forget_rule(event.rule_id)


@events.subscribe(InvoiceListExtracted)
async def normalize_extracted_invoices(event: InvoiceListExtracted, session: AsyncSession) -> None:
    """Type the invoices screen that was just stored, row by row."""
    await IngestionService(session).normalize_invoices(
        raw_document_id=event.raw_document_id,
        content=event.content,
        job_run_id=event.job_run_id,
    )


@events.subscribe(InvoiceFileExtracted)
async def normalize_extracted_invoice_file(
    event: InvoiceFileExtracted, session: AsyncSession
) -> None:
    """Read the document of an invoice and compare it against the table."""
    await IngestionService(session).normalize_invoice_file(
        raw_document_id=event.raw_document_id,
        invoice_number=event.invoice_number,
        content=event.content,
        content_type=event.content_type,
        file_kind=event.file_kind,
    )


@events.subscribe(SupplierLedgerExtracted)
async def normalize_extracted_ledger(event: SupplierLedgerExtracted, session: AsyncSession) -> None:
    """Type the supplier register and the payments of every expanded account."""
    await IngestionService(session).normalize_supplier_ledger(
        raw_document_id=event.raw_document_id, content=event.content
    )


@events.subscribe(PurchaseOrdersExtracted)
async def normalize_extracted_orders(event: PurchaseOrdersExtracted, session: AsyncSession) -> None:
    """Type the purchase orders screen that was just stored."""
    await IngestionService(session).normalize_purchase_orders(
        raw_document_id=event.raw_document_id,
        content=event.content,
        job_run_id=event.job_run_id,
    )


@events.subscribe(SupplierMessagesExtracted)
async def normalize_extracted_messages(
    event: SupplierMessagesExtracted, session: AsyncSession
) -> None:
    """Type the inbox that was just stored, keeping what is new."""
    await IngestionService(session).normalize_messages(
        raw_document_id=event.raw_document_id,
        content=event.content,
        job_run_id=event.job_run_id,
    )


@events.subscribe(SalesExtracted)
async def normalize_extracted_sales(event: SalesExtracted, session: AsyncSession) -> None:
    """Type the sales screen that was just stored."""
    await IngestionService(session).normalize_sales(
        raw_document_id=event.raw_document_id,
        content=event.content,
        job_run_id=event.job_run_id,
    )
