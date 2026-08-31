"""Purchases factories: a register, an invoice, a payment.

Written through the models rather than through `PurchasesService`, so a test can
build the exact state it needs — an invoice already held, a supplier with no
agreed term — without going through the pipeline it is about to exercise.
"""

import itertools
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.purchases.models import (
    Invoice,
    InvoiceReviewState,
    Payment,
    PaymentOrigin,
    PaymentState,
    Supplier,
    SupplierAlias,
    SupplierAliasSource,
)
from app.shared.text import normalize_entity_name

# Numbers are unique per process: two tests must never collide on
# `(supplier, number)`, which the database enforces.
_sequence = itertools.count(1)

# The eight legal names of the register, as `/estado-cuenta` publishes them.
REGISTER: tuple[tuple[str, str, int], ...] = (
    ("Aceros Belgrano SA", "30-70918273-4", 45),
    ("Cañerias del Litoral SA", "30-71829304-5", 30),
    ("Distribuidora Metalica Sur", "30-72930415-6", 60),
    ("Electrical Supply Argentina", "30-73041526-7", 30),
    ("Ferretera del Norte SRL", "30-74152637-8", 45),
    ("Herramientas Cuyo SRL", "30-75263748-9", 30),
    ("Insumos Industriales Bahia", "30-76374859-0", 60),
    ("Pinturerias Reunidas SA", "30-77485960-1", 45),
)


class SupplierFactory:
    """Builds the register, or one supplier of it."""

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        legal_name: str,
        tax_id: str | None = None,
        payment_term_days: int | None = 30,
        **kwargs: Any,
    ) -> Supplier:
        """Create one supplier, and the spelling of its own name."""
        supplier = Supplier(
            legal_name=legal_name,
            tax_id=tax_id,
            payment_term_days=payment_term_days,
            **kwargs,
        )
        session.add(supplier)
        await session.flush()
        # The spelling is unique, and two legal names can reduce to the same key
        # — `Ferretera del Norte SRL` and `Ferretera del Norte SA` both come down
        # to `ferretera norte`. The first one to claim it keeps it, which is what
        # the database says too; a test that wants that ambiguity builds it on
        # purpose rather than tripping over a constraint here.
        key = normalize_entity_name(legal_name)
        taken = (
            (
                await session.execute(
                    select(SupplierAlias).where(SupplierAlias.text_normalized == key)
                )
            )
            .scalars()
            .first()
        )
        if taken is None:
            session.add(
                SupplierAlias(
                    supplier_id=supplier.id,
                    text_normalized=key,
                    text_original=legal_name,
                    source=SupplierAliasSource.OBSERVED,
                )
            )
            await session.flush()
        return supplier

    @staticmethod
    async def register(session: AsyncSession) -> list[Supplier]:
        """The whole register, as the portal publishes it."""
        return [
            await SupplierFactory.create(
                session, legal_name=name, tax_id=tax_id, payment_term_days=term
            )
            for name, tax_id, term in REGISTER
        ]


class InvoiceFactory:
    """Builds invoices, resolved or held."""

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        supplier: Supplier | None = None,
        number: str | None = None,
        supplier_text: str | None = None,
        issued_on: date | None = None,
        total: Decimal | int = 100_000,
        due_on: date | None = None,
        review_state: InvoiceReviewState | None = None,
        **kwargs: Any,
    ) -> Invoice:
        """Create an invoice, with its due date derived from the agreed term."""
        index = next(_sequence)
        issued = issued_on or date(2026, 1, 10)
        due = due_on
        if due is None and supplier is not None and supplier.payment_term_days is not None:
            due = issued + timedelta(days=supplier.payment_term_days)
        invoice = Invoice(
            number=number or f"F-{index:05d}",
            issued_on=issued,
            total=Decimal(str(total)),
            supplier_id=supplier.id if supplier else None,
            # How the name arrived written. Defaults to the register's spelling,
            # and is worth overriding: an invoice attributed to a supplier
            # despite arriving misspelled is a real state of this table, and the
            # only one where searching by legal name differs from searching by
            # text (RF-42 of 004).
            supplier_text=supplier_text
            or (supplier.legal_name if supplier else "Proveedor Sin Padron"),
            due_on=due,
            original_due_on=due,
            review_state=review_state
            or (InvoiceReviewState.OK if supplier else InvoiceReviewState.PENDING),
            **kwargs,
        )
        session.add(invoice)
        await session.flush()
        return invoice


class PaymentFactory:
    """Builds payments, from the portal or typed by somebody."""

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        invoice: Invoice | None = None,
        amount: Decimal | int = 10_000,
        paid_on: date | None = None,
        origin: PaymentOrigin = PaymentOrigin.MANUAL,
        state: PaymentState = PaymentState.IMPUTED,
        **kwargs: Any,
    ) -> Payment:
        """Create a payment, imputed to an invoice or waiting for a decision."""
        payment = Payment(
            invoice_id=invoice.id if invoice else None,
            supplier_id=invoice.supplier_id if invoice else None,
            amount=Decimal(str(amount)),
            paid_on=paid_on or date(2026, 2, 1),
            origin=origin,
            state=state,
            created_at=datetime.now(UTC),
            **kwargs,
        )
        session.add(payment)
        await session.flush()
        return payment
