"""What `ingestion` does when something happens elsewhere.

Four subscriptions, and none of them knows who published: the portal stored a
document, or `triage` recorded (or revoked) a decision a person took.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.ingestion.service import IngestionService
from app.shared.events import (
    PriceListExtracted,
    ProductHistoryExtracted,
    QuarantineCaseResolved,
    QuarantineRuleRevoked,
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
