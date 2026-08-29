"""Ingestion business logic: type what arrived, set aside what cannot be typed.

The rule that governs every line of this file is Artículo II — nothing is
discarded. A row that cannot be interpreted does not raise, does not stop the
batch and does not disappear: it is stored with its reason and reported as a
case for a person.

The second rule is Artículo IV. This module needs to know whether a person has
already decided about a row like this one, and it cannot ask `triage`. So it
reads its **own** projection of the rules, fed by the events `triage` publishes.
"""

from decimal import Decimal, InvalidOperation

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.ingestion.models import PriceHistoryRow, PriceRow, RowStatus
from app.modules.ingestion.parsers import (
    DEFAULT_CURRENCY,
    ParsedPriceRow,
    parse_price_list,
    parse_product_history,
)
from app.modules.ingestion.repository import StagingRepository
from app.shared.events import (
    NormalizedHistoryPoint,
    NormalizedPriceRow,
    PriceHistoryNormalized,
    PriceHistoryRowsQuarantined,
    PriceListNormalized,
    PriceRowsQuarantined,
    QuarantinedRow,
    events,
)

logger = get_logger(__name__)

# The three kinds of case a person can decide about. They are strings and not an
# enum shared with `triage` on purpose: the queue is generic, and P2 will put
# invoices in it without migrating anything.
UNREADABLE_ROW = "unreadable_row"
UNKNOWN_PRODUCT = "unknown_product"
MISSING_PRODUCT = "missing_product"

LEFT_OUT_BY_RULE = "Dejado fuera de la lista por una decisión anterior"


class IngestionService:
    """Turns a stored document into typed rows, valid or quarantined."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.staging = StagingRepository(session)

    async def normalize_price_list(
        self,
        *,
        raw_document_id: int,
        content: bytes,
        job_run_id: int | None = None,
    ) -> int:
        """Type the daily list into `staging` and report the batch. Returns its id."""
        parsed = parse_price_list(content)
        batch_id = await self.staging.next_batch_id()
        rules = await self._rules_by_code()

        rows: list[PriceRow] = []
        # Kept parallel to `rows`: after the flush each `PriceRow` has an id, and
        # the events carry that id so a case can point at the exact line.
        decisions: list[tuple[ParsedPriceRow, int | None]] = []

        for row in parsed:
            rule = rules.get((UNKNOWN_PRODUCT, row.product_code or ""))
            if rule is not None and rule[1].get("action") == "ignore":
                rows.append(
                    self._row_of(
                        row,
                        raw_document_id=raw_document_id,
                        batch_id=batch_id,
                        status=RowStatus.QUARANTINED,
                        reason=LEFT_OUT_BY_RULE,
                        resolved_by_rule_id=rule[0],
                    )
                )
                decisions.append((row, None))
                continue

            price, resolved_by = row.price, None
            if not row.is_readable:
                price, resolved_by = self._apply_unreadable_rule(row, rules)

            readable = price is not None
            rows.append(
                self._row_of(
                    row,
                    raw_document_id=raw_document_id,
                    batch_id=batch_id,
                    status=RowStatus.VALID if readable else RowStatus.QUARANTINED,
                    reason=None if readable else row.reason,
                    price=price,
                    resolved_by_rule_id=resolved_by,
                )
            )
            decisions.append((row, resolved_by))

        await self.staging.add_rows(rows)

        normalized: list[NormalizedPriceRow] = []
        quarantined: list[QuarantinedRow] = []
        for stored, (parsed_row, _) in zip(rows, decisions, strict=True):
            if (
                stored.status is RowStatus.VALID
                and stored.product_code
                and stored.price is not None
            ):
                normalized.append(
                    NormalizedPriceRow(
                        staging_row_id=stored.id,
                        product_code=stored.product_code,
                        description=stored.description or "",
                        price=stored.price,
                        currency=stored.currency,
                    )
                )
            elif stored.resolved_by_rule_id is None:
                # Set aside by a rule is not set aside for a person: only what
                # nobody has decided about yet becomes a case.
                quarantined.append(
                    QuarantinedRow(
                        staging_row_id=stored.id,
                        reason=stored.reason or parsed_row.reason or "",
                        excerpt=stored.excerpt or "",
                        product_code=stored.product_code,
                    )
                )

        await events.publish(
            PriceListNormalized(
                batch_id=batch_id,
                raw_document_id=raw_document_id,
                rows=tuple(normalized),
                seen_codes=tuple(
                    {row.product_code for row in rows if row.product_code is not None}
                ),
                quarantined=len(quarantined),
                job_run_id=job_run_id,
            ),
            self.session,
        )
        if quarantined:
            await events.publish(
                PriceRowsQuarantined(batch_id=batch_id, cases=tuple(quarantined)), self.session
            )

        logger.info(
            "Price list normalized",
            extra={
                "batch_id": batch_id,
                "valid": len(normalized),
                "quarantined": len(quarantined),
                "rows": len(rows),
            },
        )
        return batch_id

    async def normalize_product_history(
        self, *, raw_document_id: int, product_code: str, content: bytes
    ) -> None:
        """Type the history screen of a product into `staging`.

        The same path as the list, so that an unreadable history has somewhere
        to be set aside instead of vanishing (RF-39). A product whose history
        cannot be read keeps its current price: nothing here touches it.
        """
        points = parse_product_history(content)
        rows = [
            PriceHistoryRow(
                raw_document_id=raw_document_id,
                product_code=product_code,
                line_number=point.line_number,
                price=point.price,
                changed_at=point.changed_at,
                status=RowStatus.VALID if point.is_readable else RowStatus.QUARANTINED,
                reason=point.reason,
                excerpt=point.excerpt,
            )
            for point in points
        ]
        await self.staging.add_history_rows(rows)

        normalized = tuple(
            NormalizedHistoryPoint(
                staging_row_id=row.id, price=row.price, changed_at=row.changed_at
            )
            for row in rows
            if row.status is RowStatus.VALID
            and row.price is not None
            and row.changed_at is not None
        )
        quarantined = tuple(
            QuarantinedRow(
                staging_row_id=row.id,
                reason=row.reason or "",
                excerpt=row.excerpt or "",
                product_code=product_code,
            )
            for row in rows
            if row.status is RowStatus.QUARANTINED
        )

        if normalized:
            await events.publish(
                PriceHistoryNormalized(product_code=product_code, points=normalized), self.session
            )
        if quarantined:
            await events.publish(
                PriceHistoryRowsQuarantined(product_code=product_code, cases=quarantined),
                self.session,
            )

        logger.info(
            "Product history normalized",
            extra={
                "product_code": product_code,
                "valid": len(normalized),
                "quarantined": len(quarantined),
            },
        )

    # --- The learned rules -----------------------------------------------

    async def learn_rule(
        self,
        *,
        rule_id: int,
        kind: str,
        matcher: dict[str, object],
        decision: dict[str, object],
    ) -> None:
        """Copy a decision taken in `triage` into the projection this module reads."""
        await self.staging.save_rule(rule_id=rule_id, kind=kind, matcher=matcher, decision=decision)
        logger.info("Resolution rule learned", extra={"rule_id": rule_id, "kind": kind})

    async def forget_rule(self, rule_id: int) -> None:
        """Drop a rule that was left without effect, so its cases come back (RF-37)."""
        await self.staging.drop_rule(rule_id)
        logger.info("Resolution rule forgotten", extra={"rule_id": rule_id})

    # --- Internals -------------------------------------------------------

    async def _rules_by_code(self) -> dict[tuple[str, str], tuple[int, dict[str, object]]]:
        """Index the rules by kind and product code, which is what a row matches on."""
        indexed: dict[tuple[str, str], tuple[int, dict[str, object]]] = {}
        for rule in await self.staging.rules():
            code = str(rule.matcher.get("product_code", ""))
            if code:
                indexed[(rule.kind, code)] = (rule.rule_id, dict(rule.decision))
        return indexed

    @staticmethod
    def _apply_unreadable_rule(
        row: ParsedPriceRow, rules: dict[tuple[str, str], tuple[int, dict[str, object]]]
    ) -> tuple[Decimal | None, int | None]:
        """Reapply what a person already decided about a row like this one (RF-34)."""
        rule = rules.get((UNREADABLE_ROW, row.product_code or ""))
        if rule is None:
            return None, None
        try:
            price = Decimal(str(rule[1]["price"]))
        except (KeyError, InvalidOperation, ArithmeticError):
            logger.warning("Resolution rule has no usable price", extra={"rule_id": rule[0]})
            return None, None
        return price, rule[0]

    @staticmethod
    def _row_of(
        parsed: ParsedPriceRow,
        *,
        raw_document_id: int,
        batch_id: int,
        status: RowStatus,
        reason: str | None,
        price: Decimal | None = None,
        resolved_by_rule_id: int | None = None,
    ) -> PriceRow:
        """Build the staging row for a parsed line."""
        return PriceRow(
            raw_document_id=raw_document_id,
            batch_id=batch_id,
            line_number=parsed.line_number,
            product_code=parsed.product_code,
            description=parsed.description,
            price=price,
            currency=DEFAULT_CURRENCY,
            status=status,
            reason=reason,
            excerpt=parsed.excerpt,
            category_raw=parsed.category_raw,
            subcategory_raw=parsed.subcategory_raw,
            resolved_by_rule_id=resolved_by_rule_id,
        )
