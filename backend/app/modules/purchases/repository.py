"""Data access for the purchases module. Private to this module."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.purchases.models import (
    DueDate,
    DueDateChange,
    Invoice,
    InvoiceDocument,
    InvoiceReviewState,
    Payment,
    PaymentOrigin,
    PaymentState,
    PurchaseCorrection,
    PurchaseOrder,
    PurchaseSetting,
    Receipt,
    ReceiptIncident,
    Supplier,
    SupplierAlias,
    SupplierAliasSource,
)
from app.shared.corrections import CorrectionStatus


class PurchasesRepository:
    """Reads and writes the register, the invoices and everything hanging off them."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- The register ----------------------------------------------------

    async def suppliers(self) -> list[Supplier]:
        """Every supplier of the register, by name."""
        result = await self.session.execute(select(Supplier).order_by(Supplier.legal_name))
        return list(result.scalars().all())

    async def supplier(self, supplier_id: int) -> Supplier | None:
        """Return a supplier by id, or None."""
        return await self.session.get(Supplier, supplier_id)

    async def supplier_named(self, legal_name: str) -> Supplier | None:
        """The supplier with this exact legal name, or None."""
        result = await self.session.execute(
            select(Supplier).where(Supplier.legal_name == legal_name)
        )
        return result.scalars().first()

    async def supplier_with_tax_id(self, tax_id: str) -> Supplier | None:
        """The supplier with this tax id, or None."""
        result = await self.session.execute(select(Supplier).where(Supplier.tax_id == tax_id))
        return result.scalars().first()

    async def put_supplier(
        self,
        *,
        legal_name: str,
        tax_id: str | None,
        email: str | None,
        phone: str | None,
        payment_term_days: int | None,
        balance: Decimal | None,
    ) -> Supplier:
        """Record what the register publishes about a supplier, or refresh it.

        A field the register did not publish this time is **left alone** rather
        than blanked: a row the portal did not expand tells us nothing new about
        that supplier, and nothing is not the same as empty.
        """
        supplier = await self.supplier_named(legal_name)
        if supplier is None:
            supplier = Supplier(legal_name=legal_name)
            self.session.add(supplier)
        for field, value in (
            ("tax_id", tax_id),
            ("email", email),
            ("phone", phone),
            ("payment_term_days", payment_term_days),
            ("balance", balance),
        ):
            if value is not None:
                setattr(supplier, field, value)
        await self.session.flush()
        return supplier

    # --- The spellings of a supplier's name ------------------------------

    async def aliases(self) -> list[SupplierAlias]:
        """Every spelling in force, oldest first."""
        result = await self.session.execute(select(SupplierAlias).order_by(SupplierAlias.id))
        return list(result.scalars().all())

    async def alias_for(self, text_normalized: str) -> SupplierAlias | None:
        """The spelling that resolves this text, or None."""
        result = await self.session.execute(
            select(SupplierAlias).where(SupplierAlias.text_normalized == text_normalized)
        )
        return result.scalars().first()

    async def alias_by_id(self, alias_id: int) -> SupplierAlias | None:
        """Return a spelling by id, or None."""
        return await self.session.get(SupplierAlias, alias_id)

    async def put_alias(
        self,
        *,
        text_normalized: str,
        text_original: str,
        supplier_id: int,
        rule_id: int | None = None,
        source: SupplierAliasSource = SupplierAliasSource.LEARNED,
        created_by_user_id: int | None = None,
    ) -> SupplierAlias:
        """Record (or re-point) a spelling of a supplier's name."""
        alias = await self.alias_for(text_normalized)
        if alias is None:
            alias = SupplierAlias(
                text_normalized=text_normalized,
                text_original=text_original,
                supplier_id=supplier_id,
                rule_id=rule_id,
                source=source,
                created_by_user_id=created_by_user_id,
            )
            self.session.add(alias)
        else:
            alias.supplier_id = supplier_id
            alias.rule_id = rule_id
            alias.text_original = text_original
        await self.session.flush()
        return alias

    async def drop_alias(self, alias: SupplierAlias) -> None:
        """Remove a spelling. What it resolved goes back to review."""
        await self.session.delete(alias)
        await self.session.flush()

    # --- The invoices ----------------------------------------------------

    async def invoice(self, invoice_id: int) -> Invoice | None:
        """Return an invoice by id, or None."""
        return await self.session.get(Invoice, invoice_id)

    async def invoice_of(
        self, *, supplier_id: int | None, number: str, supplier_text: str = ""
    ) -> Invoice | None:
        """The invoice that is the same invoice as this one, or None.

        With a supplier resolved, the identity is *(supplier, number)*, as
        signed. **Without one it is *(the name as written, number)***, and that
        distinction is RF-40: two invoices with the same number whose suppliers
        are both unresolved are not duplicates of each other — nobody knows yet
        whether they are from the same company. Comparing them by number alone
        would merge two different invoices and lose one of them.

        The written name still makes the second reading of the same screen
        idempotent: the same held invoice arriving again is recognised.
        """
        statement = select(Invoice).where(Invoice.number == number)
        if supplier_id is not None:
            statement = statement.where(Invoice.supplier_id == supplier_id)
        else:
            statement = statement.where(
                Invoice.supplier_id.is_(None), Invoice.supplier_text == supplier_text
            )
        result = await self.session.execute(statement.order_by(Invoice.id).limit(1))
        return result.scalars().first()

    async def invoices_numbered(self, number: str) -> list[Invoice]:
        """Every invoice carrying this number, whoever it belongs to."""
        result = await self.session.execute(select(Invoice).where(Invoice.number == number))
        return list(result.scalars().all())

    async def add_invoice(self, invoice: Invoice) -> Invoice:
        """Store an invoice and give it its id."""
        self.session.add(invoice)
        await self.session.flush()
        return invoice

    async def pending_invoices(self) -> list[Invoice]:
        """Every invoice still waiting for a person.

        The service filters them by the normalised spelling of their supplier,
        in Python: the normalisation drops legal forms and connecting words, and
        teaching that to SQL would be a second copy of a rule that already
        exists once in `shared/text.py`.

        It is what makes an assignment retroactive, and what lets the screen say
        how many invoices it will resolve **before** it is saved (RF-48).
        """
        result = await self.session.execute(
            select(Invoice).where(
                Invoice.supplier_id.is_(None),
                Invoice.review_state == InvoiceReviewState.PENDING,
            )
        )
        return list(result.scalars().all())

    async def invoices_resolved_by_alias(self, alias_id: int) -> list[Invoice]:
        """The invoices one saved assignment resolved, and nothing else (RF-53).

        Exactly like the categories of 008: the scope of undoing a decision is
        what that decision did, never what somebody decided one by one.
        """
        result = await self.session.execute(
            select(Invoice).where(Invoice.resolved_by_alias_id == alias_id)
        )
        return list(result.scalars().all())

    async def list_invoices(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        supplier_id: int | None = None,
        query: str | None = None,
        review_state: InvoiceReviewState | None = None,
        due_from: date | None = None,
        due_to: date | None = None,
        with_receipt: bool | None = None,
    ) -> list[Invoice]:
        """A page of invoices, newest first."""
        statement = self._invoices_query(
            select(Invoice), supplier_id, query, review_state, due_from, due_to, with_receipt
        )
        result = await self.session.execute(
            statement.order_by(Invoice.issued_on.desc(), Invoice.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_invoices(
        self,
        *,
        supplier_id: int | None = None,
        query: str | None = None,
        review_state: InvoiceReviewState | None = None,
        due_from: date | None = None,
        due_to: date | None = None,
        with_receipt: bool | None = None,
    ) -> int:
        """How many invoices match the same filters as the listing."""
        statement = self._invoices_query(
            select(func.count()).select_from(Invoice),
            supplier_id,
            query,
            review_state,
            due_from,
            due_to,
            with_receipt,
        )
        result = await self.session.execute(statement)
        return int(result.scalar_one())

    def _invoices_query(
        self,
        statement: Select[Any],
        supplier_id: int | None,
        query: str | None,
        review_state: InvoiceReviewState | None,
        due_from: date | None,
        due_to: date | None,
        with_receipt: bool | None,
    ) -> Select[Any]:
        """The filters the listing and its count share."""
        if supplier_id is not None:
            statement = statement.where(Invoice.supplier_id == supplier_id)
        if review_state is not None:
            statement = statement.where(Invoice.review_state == review_state)
        if due_from is not None:
            statement = statement.where(Invoice.due_on >= due_from)
        if due_to is not None:
            statement = statement.where(Invoice.due_on <= due_to)
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                or_(Invoice.number.ilike(pattern), Invoice.supplier_text.ilike(pattern))
            )
        if with_receipt is not None:
            issued = select(Receipt.invoice_id).where(Receipt.voided_at.is_(None))
            statement = statement.where(
                Invoice.id.in_(issued) if with_receipt else Invoice.id.not_in(issued)
            )
        return statement

    async def overdue_without_receipt(self, today: date) -> list[Invoice]:
        """Invoices past their due date with no receipt in force (RF-37 of 005)."""
        issued = select(Receipt.invoice_id).where(Receipt.voided_at.is_(None))
        result = await self.session.execute(
            select(Invoice).where(
                Invoice.due_on.is_not(None), Invoice.due_on < today, Invoice.id.not_in(issued)
            )
        )
        return list(result.scalars().all())

    async def due_between(self, start: date, end: date) -> list[Invoice]:
        """Invoices falling due in a window, whatever their state."""
        result = await self.session.execute(
            select(Invoice).where(Invoice.due_on.is_not(None), Invoice.due_on.between(start, end))
        )
        return list(result.scalars().all())

    # --- The document of an invoice --------------------------------------

    async def put_document(self, document: InvoiceDocument) -> InvoiceDocument:
        """Record the reading of an invoice's document, or refresh it."""
        existing = await self.document_of(document.invoice_id)
        if existing is None:
            self.session.add(document)
            await self.session.flush()
            return document
        for field in (
            "raw_document_id",
            "readable",
            "agrees",
            "excerpt",
            "reason",
            "read_number",
            "read_issued_on",
            "read_total",
            "read_supplier_text",
        ):
            setattr(existing, field, getattr(document, field))
        await self.session.flush()
        return existing

    async def document_of(self, invoice_id: int) -> InvoiceDocument | None:
        """The reading of an invoice's document, or None."""
        result = await self.session.execute(
            select(InvoiceDocument).where(InvoiceDocument.invoice_id == invoice_id)
        )
        return result.scalars().first()

    # --- The payments ----------------------------------------------------

    async def payment(self, payment_id: int) -> Payment | None:
        """Return a payment by id, or None."""
        return await self.session.get(Payment, payment_id)

    async def payment_with_external_id(self, external_id: str) -> Payment | None:
        """The voucher of the portal already registered under this id, or None."""
        result = await self.session.execute(
            select(Payment).where(Payment.external_id == external_id)
        )
        return result.scalars().first()

    async def add_payment(self, payment: Payment) -> Payment:
        """Store a payment and give it its id."""
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def payments_of(self, invoice_id: int) -> list[Payment]:
        """Every payment ever imputed to an invoice, undone ones included."""
        result = await self.session.execute(
            select(Payment)
            .where(Payment.invoice_id == invoice_id)
            .order_by(Payment.paid_on, Payment.id)
        )
        return list(result.scalars().all())

    async def imputed_totals(self) -> dict[int, Decimal]:
        """What has been paid on each invoice, from the payments that count."""
        result = await self.session.execute(
            select(Payment.invoice_id, func.sum(Payment.amount))
            .where(Payment.invoice_id.is_not(None), Payment.state == PaymentState.IMPUTED)
            .group_by(Payment.invoice_id)
        )
        return {int(row[0]): Decimal(row[1]) for row in result.all()}

    async def imputed_total_of(self, invoice_id: int) -> Decimal:
        """What has been paid on one invoice."""
        result = await self.session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.invoice_id == invoice_id, Payment.state == PaymentState.IMPUTED
            )
        )
        return Decimal(result.scalar_one())

    async def pending_payments(self, *, supplier_id: int | None = None) -> list[Payment]:
        """The vouchers waiting for somebody to say what they cover."""
        statement = select(Payment).where(Payment.state == PaymentState.PENDING)
        if supplier_id is not None:
            statement = statement.where(Payment.supplier_id == supplier_id)
        result = await self.session.execute(statement.order_by(Payment.paid_on, Payment.id))
        return list(result.scalars().all())

    async def similar_manual_payment(self, *, invoice_id: int, amount: Decimal) -> Payment | None:
        """A payment somebody typed that looks like this voucher (RF-42 of 005)."""
        result = await self.session.execute(
            select(Payment).where(
                Payment.invoice_id == invoice_id,
                Payment.amount == amount,
                Payment.origin == PaymentOrigin.MANUAL,
                Payment.state == PaymentState.IMPUTED,
            )
        )
        return result.scalars().first()

    # --- The receipts and their incidents --------------------------------

    async def receipt_of(self, invoice_id: int) -> Receipt | None:
        """The receipt in force of an invoice, or None."""
        result = await self.session.execute(
            select(Receipt).where(Receipt.invoice_id == invoice_id, Receipt.voided_at.is_(None))
        )
        return result.scalars().first()

    async def receipt(self, receipt_id: int) -> Receipt | None:
        """Return a receipt by id, or None."""
        return await self.session.get(Receipt, receipt_id)

    async def receipts_in_force(self) -> set[int]:
        """The invoices that have a receipt right now."""
        result = await self.session.execute(
            select(Receipt.invoice_id).where(Receipt.voided_at.is_(None))
        )
        return {int(value) for value in result.scalars().all()}

    async def add_receipt(self, receipt: Receipt) -> Receipt:
        """Store a receipt and give it its id."""
        self.session.add(receipt)
        await self.session.flush()
        return receipt

    async def next_receipt_number(self) -> int:
        """The next number of the correlative series (RF-48 of 005)."""
        result = await self.session.execute(select(func.count()).select_from(Receipt))
        return int(result.scalar_one()) + 1

    async def open_incident(self, invoice_id: int, opened_on: date) -> ReceiptIncident | None:
        """Open the incident of an overdue invoice, unless it is already open."""
        existing = await self.incident_of(invoice_id)
        if existing is not None:
            return None
        incident = ReceiptIncident(invoice_id=invoice_id, opened_on=opened_on)
        self.session.add(incident)
        await self.session.flush()
        return incident

    async def incident_of(self, invoice_id: int) -> ReceiptIncident | None:
        """The open incident of an invoice, or None."""
        result = await self.session.execute(
            select(ReceiptIncident).where(
                ReceiptIncident.invoice_id == invoice_id, ReceiptIncident.closed_at.is_(None)
            )
        )
        return result.scalars().first()

    async def incident(self, incident_id: int) -> ReceiptIncident | None:
        """Return an incident by id, or None."""
        return await self.session.get(ReceiptIncident, incident_id)

    async def incidents(self, *, only_open: bool = True) -> list[ReceiptIncident]:
        """The incidents, the open ones by default (RF-59)."""
        statement = select(ReceiptIncident)
        if only_open:
            statement = statement.where(ReceiptIncident.closed_at.is_(None))
        result = await self.session.execute(statement.order_by(ReceiptIncident.opened_on))
        return list(result.scalars().all())

    # --- The calendar ----------------------------------------------------

    async def due_date(self, due_date_id: int) -> DueDate | None:
        """Return an entry of the calendar by id, or None."""
        return await self.session.get(DueDate, due_date_id)

    async def due_date_of_invoice(self, invoice_id: int) -> DueDate | None:
        """The entry that stands for an invoice, or None."""
        result = await self.session.execute(select(DueDate).where(DueDate.invoice_id == invoice_id))
        return result.scalars().first()

    async def add_due_date(self, entry: DueDate) -> DueDate:
        """Store an entry of the calendar and give it its id."""
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def drop_due_date(self, entry: DueDate) -> None:
        """Remove an entry. The service refuses first if it comes from an invoice."""
        await self.session.delete(entry)
        await self.session.flush()

    async def due_dates_between(self, start: date, end: date) -> list[DueDate]:
        """Every entry of the calendar in a window, in date order."""
        result = await self.session.execute(
            select(DueDate).where(DueDate.on_date.between(start, end)).order_by(DueDate.on_date)
        )
        return list(result.scalars().all())

    async def add_due_date_change(self, change: DueDateChange) -> DueDateChange:
        """Record one move of an entry."""
        self.session.add(change)
        await self.session.flush()
        return change

    async def changes_of(self, due_date_id: int) -> list[DueDateChange]:
        """Every move of an entry, oldest first (RF-23 of 006)."""
        result = await self.session.execute(
            select(DueDateChange)
            .where(DueDateChange.due_date_id == due_date_id)
            .order_by(DueDateChange.changed_at)
        )
        return list(result.scalars().all())

    # --- The purchase orders ---------------------------------------------

    async def order(self, order_id: int) -> PurchaseOrder | None:
        """Return an order by id, or None."""
        return await self.session.get(PurchaseOrder, order_id)

    async def order_numbered(self, number: str) -> PurchaseOrder | None:
        """The order with this number, or None."""
        result = await self.session.execute(
            select(PurchaseOrder).where(PurchaseOrder.number == number)
        )
        return result.scalars().first()

    async def add_order(self, order: PurchaseOrder) -> PurchaseOrder:
        """Store an order and give it its id."""
        self.session.add(order)
        await self.session.flush()
        return order

    async def orders(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        status_text: str | None = None,
        supplier_id: int | None = None,
    ) -> list[PurchaseOrder]:
        """A page of orders, newest first."""
        statement = select(PurchaseOrder)
        if status_text is not None:
            statement = statement.where(PurchaseOrder.status_text == status_text)
        if supplier_id is not None:
            statement = statement.where(PurchaseOrder.supplier_id == supplier_id)
        result = await self.session.execute(
            statement.order_by(PurchaseOrder.ordered_on.desc(), PurchaseOrder.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def orders_per_status(self) -> dict[str, int]:
        """How many orders are in each state (RF-07 of 007)."""
        result = await self.session.execute(
            select(PurchaseOrder.status_text, func.count()).group_by(PurchaseOrder.status_text)
        )
        return {str(row[0]): int(row[1]) for row in result.all()}

    async def earlier_order_for(
        self, *, supplier_id: int | None, product_code: str | None, since: date, before: date
    ) -> PurchaseOrder | None:
        """An earlier order of the same product to the same supplier, inside the window."""
        if supplier_id is None or product_code is None:
            return None
        result = await self.session.execute(
            select(PurchaseOrder)
            .where(
                PurchaseOrder.supplier_id == supplier_id,
                PurchaseOrder.product_code == product_code,
                PurchaseOrder.ordered_on >= since,
                PurchaseOrder.ordered_on <= before,
            )
            .order_by(PurchaseOrder.ordered_on.desc())
            .limit(1)
        )
        return result.scalars().first()

    # --- Corrections by hand ---------------------------------------------

    async def correction(self, correction_id: int) -> PurchaseCorrection | None:
        """Return a correction by id, or None."""
        return await self.session.get(PurchaseCorrection, correction_id)

    async def correction_in_force(
        self, *, entity_type: str, entity_id: str, field: str
    ) -> PurchaseCorrection | None:
        """The correction standing over one field of one row, or None."""
        result = await self.session.execute(
            select(PurchaseCorrection).where(
                PurchaseCorrection.entity_type == entity_type,
                PurchaseCorrection.entity_id == entity_id,
                PurchaseCorrection.field == field,
                PurchaseCorrection.status != CorrectionStatus.REVERTED,
            )
        )
        return result.scalars().first()

    async def corrections_in_force(self, entity_ids: Sequence[str]) -> list[PurchaseCorrection]:
        """Every correction standing over a set of rows."""
        if not entity_ids:
            return []
        result = await self.session.execute(
            select(PurchaseCorrection).where(
                PurchaseCorrection.entity_id.in_(list(entity_ids)),
                PurchaseCorrection.status != CorrectionStatus.REVERTED,
            )
        )
        return list(result.scalars().all())

    async def add_correction(self, correction: PurchaseCorrection) -> PurchaseCorrection:
        """Store a correction and give it its id."""
        self.session.add(correction)
        await self.session.flush()
        return correction

    # --- The parameters this module reads --------------------------------

    async def setting(self, key: str) -> Any | None:
        """The value of a parameter as this module last heard it, or None."""
        row = await self.session.get(PurchaseSetting, key)
        return None if row is None else row.value

    async def put_setting(self, key: str, value: Any) -> None:
        """Record the value of a parameter the owner changed."""
        row = await self.session.get(PurchaseSetting, key)
        if row is None:
            self.session.add(PurchaseSetting(key=key, value=value))
        else:
            row.value = value
        await self.session.flush()
