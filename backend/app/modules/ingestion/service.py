"""Ingestion business logic: type what arrived, set aside what cannot be typed.

The rule that governs every line of this file is Artículo II — nothing is
discarded. A row that cannot be interpreted does not raise, does not stop the
batch and does not disappear: it is stored with its reason and reported as a
case for a person.

The second rule is Artículo IV. This module needs to know whether a person has
already decided about a row like this one, and it cannot ask `triage`. So it
reads its **own** projection of the rules, fed by the events `triage` publishes.
"""

from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.ingestion.documents import read_invoice_document
from app.modules.ingestion.models import (
    InvoiceFileRead,
    InvoiceRow,
    MessageRow,
    PaymentRow,
    PriceHistoryRow,
    PriceRow,
    PurchaseOrderRow,
    RowStatus,
    SaleRow,
    SupplierRow,
)
from app.modules.ingestion.parsers import (
    DEFAULT_CURRENCY,
    ParsedPriceRow,
    invoice_references_in,
    parse_invoices,
    parse_messages,
    parse_price_list,
    parse_product_history,
    parse_purchase_orders,
    parse_sales,
    parse_supplier_ledger,
)
from app.modules.ingestion.repository import StagingRepository

# The event and the `staging` row that records the same reading share a name.
# The row keeps the plain one because it is a table, and the event is aliased
# here rather than renamed in the shared catalog: a name in the vocabulary of
# the business should not have to dodge a table of one module.
from app.shared.events import InvoiceFileRead as InvoiceFileRead_
from app.shared.events import (
    InvoiceRowsQuarantined,
    InvoicesNormalized,
    NormalizedHistoryPoint,
    NormalizedInvoice,
    NormalizedMessage,
    NormalizedPayment,
    NormalizedPriceRow,
    NormalizedPurchaseOrder,
    NormalizedSale,
    NormalizedSupplier,
    PaymentsNormalized,
    PriceHistoryNormalized,
    PriceHistoryRowsQuarantined,
    PriceListNormalized,
    PriceRowsQuarantined,
    PurchaseOrderRowsQuarantined,
    PurchaseOrdersNormalized,
    QuarantinedRow,
    SaleRowsQuarantined,
    SalesNormalized,
    SupplierMessagesNormalized,
    SuppliersNormalized,
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
                        # Read since `001` and never carried anywhere: the
                        # catalog resolves the category against its table of
                        # equivalences (008) and keeps the photograph of the
                        # stock (009). This module still interprets neither.
                        category_raw=stored.category_raw,
                        subcategory_raw=stored.subcategory_raw,
                        stock=stored.stock,
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
            stock=parsed.stock,
            resolved_by_rule_id=resolved_by_rule_id,
        )

    # --- The other sections of the portal (004, 007, 009) ----------------
    #
    # Six more pipelines, one per section, all shaped like the price list:
    # parse, write every row into `staging` marked valid or quarantined, then
    # publish what could be typed and what could not. Nothing is discarded and
    # nothing is completed by assumption (Artículo II).

    async def normalize_invoices(
        self, *, raw_document_id: int, content: bytes, job_run_id: int | None = None
    ) -> int:
        """Type the invoices screen into `staging` and report the batch."""
        parsed = parse_invoices(content)
        batch_id = await self.staging.next_document_batch_id()

        rows = [
            InvoiceRow(
                raw_document_id=raw_document_id,
                batch_id=batch_id,
                line_number=row.line_number,
                number=row.number,
                supplier_text=row.supplier_text,
                issued_on=row.issued_on,
                due_on=row.due_on,
                total=row.total,
                paid=row.paid,
                balance=row.balance,
                receipt_issued=row.receipt_issued,
                portal_payment_status=row.portal_payment_status,
                file_kind=row.file_kind,
                product_code=row.product_code,
                status=RowStatus.VALID if row.is_readable else RowStatus.QUARANTINED,
                reason=row.reason,
                excerpt=row.excerpt,
            )
            for row in parsed
        ]
        await self.staging.add_all(rows)

        normalized = tuple(
            NormalizedInvoice(
                staging_row_id=row.id,
                number=row.number or "",
                supplier_text=row.supplier_text or "",
                issued_on=row.issued_on,
                total=row.total,
                due_on=row.due_on,
                receipt_issued=row.receipt_issued,
                paid=row.paid or Decimal(0),
                balance=row.balance,
                portal_payment_status=row.portal_payment_status,
                file_kind=row.file_kind,
                product_code=row.product_code,
            )
            for row in rows
            if row.status is RowStatus.VALID
            and row.number
            and row.issued_on is not None
            and row.total is not None
        )
        quarantined = self._quarantined_of(rows)

        await events.publish(
            InvoicesNormalized(
                batch_id=batch_id,
                raw_document_id=raw_document_id,
                invoices=normalized,
                quarantined=len(quarantined),
                job_run_id=job_run_id,
            ),
            self.session,
        )
        if quarantined:
            await events.publish(
                InvoiceRowsQuarantined(batch_id=batch_id, cases=quarantined), self.session
            )
        logger.info(
            "Invoices normalized",
            extra={"batch_id": batch_id, "valid": len(normalized), "quarantined": len(quarantined)},
        )
        return batch_id

    async def normalize_invoice_file(
        self,
        *,
        raw_document_id: int,
        invoice_number: str,
        content: bytes,
        content_type: str,
        file_kind: str,
    ) -> None:
        """Read the document of an invoice and compare it with the table.

        This is the comparison the whole feature rests on. It is **not** a
        confidence score: the table already published the four header fields,
        so the question is whether the document says the same thing. When it
        does, the invoice is certainty and nobody is bothered; when it does not,
        or when the document could not be read at all, it goes to a person with
        the excerpt in view.
        """
        reading = read_invoice_document(content, content_type=content_type, file_kind=file_kind)
        table_row = await self.staging.invoice_row_for(invoice_number)
        agrees = reading.agrees_with(
            number=table_row.number if table_row else None,
            issued_on=table_row.issued_on if table_row else None,
            total=table_row.total if table_row else None,
        )

        stored = InvoiceFileRead(
            raw_document_id=raw_document_id,
            invoice_number=invoice_number,
            readable=reading.readable and reading.reason is None,
            agrees=agrees,
            number=reading.number,
            issued_on=reading.issued_on,
            total=reading.total,
            supplier_text=reading.supplier_text,
            supplier_tax_id=reading.supplier_tax_id,
            reason=reading.reason,
            excerpt=reading.excerpt,
        )
        await self.staging.add_all([stored])

        await events.publish(
            InvoiceFileRead_(
                invoice_number=invoice_number,
                raw_document_id=raw_document_id,
                readable=stored.readable,
                agrees=agrees,
                excerpt=reading.excerpt,
                reason=reading.reason,
                number=reading.number,
                issued_on=reading.issued_on,
                total=reading.total,
                supplier_text=reading.supplier_text,
                supplier_tax_id=reading.supplier_tax_id,
                content=content,
                content_type=content_type,
            ),
            self.session,
        )
        logger.info(
            "Invoice document read",
            extra={"invoice_number": invoice_number, "readable": stored.readable, "agrees": agrees},
        )

    async def normalize_supplier_ledger(self, *, raw_document_id: int, content: bytes) -> None:
        """Type the supplier register and the payments of every expanded account."""
        suppliers, payments = parse_supplier_ledger(content)
        batch_id = await self.staging.next_document_batch_id()

        supplier_rows = [
            SupplierRow(
                raw_document_id=raw_document_id,
                line_number=row.line_number,
                legal_name=row.legal_name,
                tax_id=row.tax_id,
                email=row.email,
                phone=row.phone,
                payment_term_days=row.payment_term_days,
                balance=row.balance,
                status=RowStatus.VALID if row.is_readable else RowStatus.QUARANTINED,
                reason=row.reason,
                excerpt=row.excerpt,
            )
            for row in suppliers
        ]
        payment_rows = [
            PaymentRow(
                raw_document_id=raw_document_id,
                batch_id=batch_id,
                line_number=row.line_number,
                supplier_text=row.supplier_text,
                reference=row.reference,
                paid_on=row.paid_on,
                amount=row.amount,
                external_id=row.external_id,
                status=RowStatus.VALID if row.is_readable else RowStatus.QUARANTINED,
                reason=row.reason,
                excerpt=row.excerpt,
            )
            for row in payments
        ]
        await self.staging.add_all([*supplier_rows, *payment_rows])

        await events.publish(
            SuppliersNormalized(
                raw_document_id=raw_document_id,
                suppliers=tuple(
                    NormalizedSupplier(
                        legal_name=row.legal_name or "",
                        tax_id=row.tax_id,
                        email=row.email,
                        phone=row.phone,
                        payment_term_days=row.payment_term_days,
                        balance=row.balance,
                    )
                    for row in supplier_rows
                    if row.status is RowStatus.VALID and row.legal_name
                ),
            ),
            self.session,
        )
        imputable = tuple(
            NormalizedPayment(
                staging_row_id=row.id,
                supplier_text=row.supplier_text or "",
                references=tuple(invoice_references_in(row.reference or "")),
                paid_on=row.paid_on,
                amount=row.amount,
                external_id=row.external_id or "",
            )
            for row in payment_rows
            if row.status is RowStatus.VALID and row.paid_on is not None and row.amount is not None
        )
        if imputable:
            await events.publish(
                PaymentsNormalized(
                    batch_id=batch_id,
                    raw_document_id=raw_document_id,
                    payments=imputable,
                    quarantined=len(payment_rows) - len(imputable),
                ),
                self.session,
            )
        logger.info(
            "Supplier ledger normalized",
            extra={"suppliers": len(supplier_rows), "payments": len(payment_rows)},
        )

    async def normalize_purchase_orders(
        self, *, raw_document_id: int, content: bytes, job_run_id: int | None = None
    ) -> int:
        """Type the purchase orders screen into `staging` and report the batch."""
        parsed = parse_purchase_orders(content)
        batch_id = await self.staging.next_document_batch_id()

        rows = [
            PurchaseOrderRow(
                raw_document_id=raw_document_id,
                batch_id=batch_id,
                line_number=row.line_number,
                number=row.number,
                ordered_on=row.ordered_on,
                supplier_text=row.supplier_text,
                product_code=row.product_code,
                product_text=row.product_text,
                quantity=row.quantity,
                amount=row.amount,
                status_text=row.status_text,
                status=RowStatus.VALID if row.is_readable else RowStatus.QUARANTINED,
                reason=row.reason,
                excerpt=row.excerpt,
            )
            for row in parsed
        ]
        await self.staging.add_all(rows)
        quarantined = self._quarantined_of(rows)

        await events.publish(
            PurchaseOrdersNormalized(
                batch_id=batch_id,
                raw_document_id=raw_document_id,
                orders=tuple(
                    NormalizedPurchaseOrder(
                        staging_row_id=row.id,
                        number=row.number or "",
                        ordered_on=row.ordered_on,
                        supplier_text=row.supplier_text or "",
                        product_code=row.product_code,
                        product_text=row.product_text or "",
                        quantity=row.quantity,
                        amount=row.amount,
                        status_text=row.status_text or "",
                    )
                    for row in rows
                    if row.status is RowStatus.VALID and row.number and row.ordered_on is not None
                ),
                quarantined=len(quarantined),
                job_run_id=job_run_id,
            ),
            self.session,
        )
        if quarantined:
            await events.publish(
                PurchaseOrderRowsQuarantined(batch_id=batch_id, cases=quarantined), self.session
            )
        logger.info("Purchase orders normalized", extra={"batch_id": batch_id, "rows": len(rows)})
        return batch_id

    async def normalize_messages(
        self, *, raw_document_id: int, content: bytes, job_run_id: int | None = None
    ) -> int:
        """Type the inbox, keeping only what this pipeline has not seen before.

        The inbox is read whole every time and most of it was already read, so
        what is published is the **new** messages. Whether anybody is woken up
        for them is not decided here: the first reading of all says so with
        `first_run`, and everything the inbox already held at start-up is
        registered as pending without a single alert (RF-47 of 007).
        """
        parsed = parse_messages(content)
        batch_id = await self.staging.next_document_batch_id()
        first_run = not await self.staging.has_typed_messages()
        known = await self.staging.known_message_ids()

        rows = [
            MessageRow(
                raw_document_id=raw_document_id,
                batch_id=batch_id,
                line_number=row.line_number,
                external_id=row.external_id,
                received_at=row.received_at,
                sender_text=row.sender_text,
                kind_text=row.kind_text,
                subject=row.subject,
                body=row.body,
                already_read=row.already_read,
                status=RowStatus.VALID if row.is_readable else RowStatus.QUARANTINED,
                reason=row.reason,
                excerpt=row.excerpt,
            )
            for row in parsed
            if row.external_id not in known
        ]
        await self.staging.add_all(rows)

        fresh = tuple(
            NormalizedMessage(
                staging_row_id=row.id,
                external_id=row.external_id or "",
                received_at=row.received_at,
                sender_text=row.sender_text or "",
                kind_text=row.kind_text or "",
                subject=row.subject or "",
                body=row.body or "",
                already_read=row.already_read,
            )
            for row in rows
            if row.status is RowStatus.VALID and row.external_id and row.received_at is not None
        )
        if fresh:
            await events.publish(
                SupplierMessagesNormalized(
                    batch_id=batch_id,
                    raw_document_id=raw_document_id,
                    messages=fresh,
                    first_run=first_run,
                ),
                self.session,
            )
        logger.info(
            "Inbox normalized",
            extra={"batch_id": batch_id, "new": len(fresh), "first_run": first_run},
        )
        del job_run_id
        return batch_id

    async def normalize_sales(
        self, *, raw_document_id: int, content: bytes, job_run_id: int | None = None
    ) -> int:
        """Type the sales screen into `staging` and report the batch."""
        parsed = parse_sales(content)
        batch_id = await self.staging.next_document_batch_id()

        rows = [
            SaleRow(
                raw_document_id=raw_document_id,
                batch_id=batch_id,
                line_number=row.line_number,
                code=row.code,
                code_key=row.code_key,
                sold_on=row.sold_on,
                product_code=row.product_code,
                quantity=row.quantity,
                total=row.total,
                status=RowStatus.VALID if row.is_readable else RowStatus.QUARANTINED,
                reason=row.reason,
                excerpt=row.excerpt,
            )
            for row in parsed
        ]
        await self.staging.add_all(rows)
        quarantined = self._quarantined_of(rows)

        # **Every row travels, quarantined ones included.** This used to publish
        # only the rows that read whole, and the twelve records the survey
        # measured as broken — no date, a date that does not exist, no total, a
        # negative quantity — stayed in `staging` where no screen reaches them:
        # they were not shown, not counted among what an indicator left out, and
        # not correctable. That is RF-16 to RF-19 of 009, and holding them is
        # what the signed spec asks for (Artículo II).
        #
        # `SaleRowsQuarantined` is still published below and still has no
        # subscriber, and that is deliberate: the row already has a human
        # surface in the sales review queue, and opening a `triage` case as well
        # would show the same record on two screens belonging to two different
        # people.
        await events.publish(
            SalesNormalized(
                batch_id=batch_id,
                raw_document_id=raw_document_id,
                sales=tuple(
                    NormalizedSale(
                        staging_row_id=row.id,
                        code=row.code or "",
                        code_key=row.code_key or "",
                        sold_on=row.sold_on,
                        product_code=row.product_code,
                        quantity=row.quantity,
                        total=row.total,
                        reason=row.reason,
                    )
                    for row in rows
                ),
                quarantined=len(quarantined),
                job_run_id=job_run_id,
            ),
            self.session,
        )
        if quarantined:
            await events.publish(
                SaleRowsQuarantined(batch_id=batch_id, cases=quarantined), self.session
            )
        logger.info("Sales normalized", extra={"batch_id": batch_id, "rows": len(rows)})
        return batch_id

    @staticmethod
    def _quarantined_of(rows: Sequence[Any]) -> tuple[QuarantinedRow, ...]:
        """The rows a person has to look at, in the shape the review queue reads.

        One helper for four pipelines: what a quarantined row is — its id, why
        it was set aside and what it actually said — does not depend on which
        screen it came from, and neither does the queue that shows it.
        """
        return tuple(
            QuarantinedRow(
                staging_row_id=row.id,
                reason=row.reason or "",
                excerpt=row.excerpt or "",
                product_code=getattr(row, "number", None),
            )
            for row in rows
            if row.status is RowStatus.QUARANTINED
        )
