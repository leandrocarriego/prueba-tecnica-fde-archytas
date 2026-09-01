"""Purchases business logic: who invoiced us, how much, and what is still owed.

Four rules govern every line of this file, and all four come from the signed
specs rather than from taste.

* **The register is closed.** An invoice from a name that does not resolve to a
  supplier of `/estado-cuenta` is set aside, never turned into a new supplier.
  The client ruled that out explicitly in the `/clarify`: the register widens as
  a decision of the business.
* **Nothing is guessed.** A supplier that does not match with certainty, a
  voucher that does not say which invoice it covers, a duplicate that arrives
  with a different total: each of them waits for a person, counted and visible.
* **The payment state comes from the payments imputed**, never from what the
  portal reports. The portal's own state is kept and shown, and when the two
  disagree the invoice says so instead of one of them winning quietly.
* **A due date is derived from the agreed payment term**, and from nothing else
  — not from a date the document happens to print.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from rapidfuzz import fuzz, process
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.purchases.models import (
    INCONSISTENT,
    PARTIAL,
    SETTLED,
    UNPAID,
    DueDate,
    DueDateChange,
    DueDateOrigin,
    Invoice,
    InvoiceDocument,
    InvoiceOrder,
    InvoiceReviewState,
    OrderReviewState,
    Payment,
    PaymentOrigin,
    PaymentState,
    PurchaseCorrection,
    PurchaseOrder,
    Receipt,
    RecordOrigin,
    Supplier,
    SupplierAliasSource,
)
from app.modules.purchases.repository import PurchasesRepository
from app.modules.purchases.schemas import (
    AgingBucket,
    AliasPreview,
    CalendarRead,
    DueDateChangeRead,
    DueDateRead,
    IncidentRead,
    InvoiceDocumentRead,
    InvoiceList,
    InvoiceRead,
    PaymentRead,
    PurchaseOrderList,
    PurchaseOrderRead,
    ReceiptRead,
    SupplierAliasRead,
    SupplierCorrectionMark,
    SupplierList,
    SupplierRead,
    SupplierTotalsRead,
)
from app.shared.corrections import CorrectionStatus
from app.shared.errors import ConflictError, NotFoundError, ValidationError
from app.shared.events import (
    AuditAction,
    CorrectionConflicted,
    DueDateChanged,
    InvoiceDueDateRescheduled,
    InvoiceReviewCase,
    InvoicesNeedingReview,
    InvoicesRegistered,
    ManualChangeRecorded,
    ManualEntryDisputed,
    NormalizedInvoice,
    NormalizedPayment,
    NormalizedPurchaseOrder,
    NormalizedSupplier,
    PaymentReviewCase,
    PaymentsNeedingReview,
    QuarantinedSourceResolved,
    ReceiptIssued,
    ReceiptVoided,
    RegisteredInvoice,
    events,
)
from app.shared.parameters import initial_value
from app.shared.sections import BusinessSection
from app.shared.text import normalize_entity_name, only_digits
from app.shared.time import BUSINESS_TIME_ZONE

logger = get_logger(__name__)

# --- The kinds of case this module opens ---------------------------------

SUPPLIER_UNRESOLVED = "invoice_supplier_unresolved"
SUPPLIER_NOT_IN_REGISTER = "invoice_supplier_not_in_register"
DUPLICATE_INVOICE = "invoice_duplicate"
PAYMENT_UNASSIGNED = "payment_unassigned"

# How this module names its own rows in the one log of the platform, and which
# part of the business they belong to.
DUE_DATE_ENTITY = "purchases.due_date"
SUPPLIER_ENTITY = "purchases.supplier"
INVOICE_ENTITY = "purchases.invoice"
PURCHASING_SECTION = BusinessSection.PURCHASING

# The fields of a supplier's card a person may correct (RF-16 of 004). The legal
# name and the tax id are deliberately not among them (RF-17), and neither is
# the balance: it is the portal's arithmetic, not a contact detail.
#
# The tuple is here and not beside the endpoint because it governs two places
# that have to agree — what a correction may be written over, and what a later
# reading of the register is not allowed to overwrite (RF-19).
CORRECTABLE_SUPPLIER_FIELDS: tuple[str, ...] = ("email", "phone", "payment_term_days")

# What a person reads next to a held row. In Spanish, like every user-facing
# string of the platform.
AMBIGUOUS_SUPPLIER = "No pudimos identificar con certeza al proveedor"
OUTSIDE_REGISTER = "El proveedor no está en el padrón"
DUPLICATE_WITH_ANOTHER_TOTAL = "Ya había una factura con ese número y otro monto"
FILE_DISAGREES = "El archivo de la factura no coincide con lo que informa el portal"
FILE_UNREADABLE = "No se pudo leer el archivo de la factura"
# What 011 needs said out loud when a voucher that was waiting stops waiting.
# The kind is `triage`'s word for the case an unreadable payment row opens, and
# the key is the `staging` row it was opened with.
#
# **Today this closes nothing, and that is worth writing down rather than
# discovering.** A voucher the parser could not type never becomes a `Payment`
# at all — it stays quarantined in `staging`, which is exactly the silence 011
# closes by opening a case for it — so the vouchers that move through the two
# screens below are the *readable* ones, which never had a case. The
# announcement is still made: it costs nothing, it is the true statement that a
# reading was dealt with, and the handler on the other side treats "no case
# found" as the ordinary outcome. The day a held voucher opens a case of its
# own, this already says so.
UNREADABLE_PAYMENT_ROW = "unreadable_payment_row"
RESOLVED_IN_PAYMENTS = "la pantalla de comprobantes"

# --- Lo que carga una persona (2026-09-01) -------------------------------
#
# Cómo se nombran las dos cosas que se pueden cargar a mano cuando el portal
# publica una fila que nadie puede leer. Viajan como string en el evento, así
# que `triage` las nombra igual sin importar nada de este módulo (Artículo IV).
INVOICE_ENTITY = "invoice"
ORDER_ENTITY = "purchase_order"

# Las dos respuestas posibles cuando el portal publica, ya legible, una fila que
# alguien había reconstruido a mano y no coinciden.
KEEP_PORTAL = "portal"
KEEP_MANUAL = "manual"

DISPUTED_BY_PORTAL = "La cargó una persona y el portal la publicó distinta"

# La clase de caso que abre esa discusión y la pantalla que también puede
# cerrarla. Escritas acá por la misma razón que `UNREADABLE_PAYMENT_ROW` más
# arriba: son vocabulario que viaja en un evento, no un import de `triage`.
#
# Existe porque la factura apartada aparece en **dos** lugares —la cola de
# facturas, porque quedó `PENDING`, y «Para decidir», porque la discusión se
# pregunta ahí— y quien la resuelva primero tiene que llevarse el caso puesto.
# Un pendiente que sigue en la lista después de resuelto es la lista mintiendo
# (RF-20, RF-21 de 011).
DISPUTED_INVOICE_CASE = "disputed_invoice"
RESOLVED_IN_INVOICES = "la pantalla de facturas"

ALREADY_REGISTERED = "Esa factura ya está registrada"
ORDER_ALREADY_REGISTERED = "Esa orden ya está registrada"
SUPPLIER_NOT_IN_REGISTER = "Ese proveedor no está en el padrón"

VOUCHER_WITHOUT_INVOICE = "El comprobante no dice a qué factura corresponde"
VOUCHER_UNKNOWN_INVOICE = "El comprobante menciona una factura que no tenemos registrada"
VOUCHER_SEVERAL_INVOICES = "El comprobante cubre más de una factura"
VOUCHER_LOOKS_MANUAL = "Coincide con un pago cargado a mano"

NO_SUCH_INVOICE = "No encontramos esa factura"
NO_SUCH_ORDER = "No encontramos esa orden"
ORDER_NOT_HELD = "Esa orden no está apartada para revisión"
NO_INVOICE_FILE = "Todavía no tenemos el archivo de esa factura"
INVOICE_NUMBER_TAKEN = "Ese número ya es de otra factura de este proveedor"
# Why a header field of an invoice changed. Every correction of RF-31 comes
# from the same place — somebody looking at the excerpt of the document in the
# review queue — so the log says that once instead of asking for it every time.
INVOICE_RESOLVED_BY_HAND = "Corregido al resolver la factura en revisión"
NO_SUCH_SUPPLIER = "No encontramos ese proveedor"
NO_SUCH_PAYMENT = "No encontramos ese pago"
NO_SUCH_DUE_DATE = "No encontramos ese vencimiento"
NO_SUCH_INCIDENT = "No encontramos ese incidente"

RECEIPT_ALREADY_ISSUED = "La factura ya tiene su recibo emitido"
RECEIPT_TOO_LATE = "La factura ya venció y por eso no se le puede emitir el recibo"
RECEIPT_ALREADY_VOIDED = "El recibo ya está anulado"
PORTAL_PAYMENT_IS_NOT_UNDONE = "Un pago traído del portal no se puede dejar sin efecto"
PAYMENT_OVER_BALANCE = "El pago supera el saldo de la factura"
SPLIT_DOES_NOT_ADD_UP = "Las partes no suman el monto del comprobante"
SPLIT_CROSSES_SUPPLIERS = "Un comprobante no se reparte entre facturas de dos proveedores"
SPLIT_IS_ANOTHER_SUPPLIER = "Esas facturas son de otro proveedor, no del que pagó"
INVOICE_FROM_A_LIST_IS_NOT_REMOVED = "Un vencimiento que viene de una factura no se elimina"
MOVING_INTO_THE_PAST = "La fecha nueva ya pasó"

# The refusal above is the only one the screen has to *recognise* rather than
# just show: it is what RF-25 turns into a question instead of an error. It
# travels as a code in `details` because the alternative — matching the Spanish
# text on the other side — makes the wording of a message a contract nobody
# declared, and rewording it would kill the confirmation in silence.
MOVING_INTO_THE_PAST_CODE = "DUE_DATE_MOVING_INTO_THE_PAST"

# What the portal calls the same three, so the two can be compared (RF-46).
PORTAL_STATES: dict[str, str] = {
    "Pagada": SETTLED,
    "Pago parcial": PARTIAL,
    "Impaga": UNPAID,
}

# The parameters this module reads, through its own projection.
MATCH_THRESHOLD_KEY = "supplier_match.threshold_pct"
RECEIPT_NOTICE_KEY = "receipt.notice_days"
STALLED_DAYS_KEY = "purchase_order.stalled_days"
REPEAT_WINDOW_KEY = "purchase_order.repeat_window_days"

# What an invoice document is served as when the portal did not say. A browser
# handed an unknown type offers to save the file, which is the harmless end of
# guessing wrong.
DEFAULT_FILE_TYPE = "application/octet-stream"
# The extension each content type gets when the file is handed over, so what
# lands in Descargas opens by double-clicking it.
FILE_EXTENSIONS: tuple[tuple[str, str], ...] = (
    ("pdf", ".pdf"),
    ("spreadsheet", ".xlsx"),
    ("excel", ".xlsx"),
    ("csv", ".csv"),
)

# How far ahead of the runner-up a match has to be before it counts as certain.
# Two suppliers of this register read alike — `Ferretera del Norte SRL` and
# `Ferreteria del Norte S.R.L.` — and a name that is nearly as close to two of
# them is not an identification, it is a coin toss. In the doubt it goes to a
# person (RF-13 of 004).
MATCH_MARGIN = 6

# The bands the debt of a supplier is split into, counted from the due date.
AGING_BANDS: tuple[tuple[str, int | None], ...] = (
    ("Por vencer", 0),
    ("1 a 30 días", 30),
    ("31 a 60 días", 60),
    ("61 a 90 días", 90),
    ("Más de 90 días", None),
)

# The states of a purchase order that are before it arrives. An order that was
# received is finished, and a finished order is not stalled however long it sat
# (RF-10 of 007).
RECEIVED_STATUS = "Recibida"

HUNDRED = Decimal(100)


def _money_text(value: Decimal | None) -> str:
    """Un importe como texto, con la **misma** forma salga de donde salga.

    Los dos lados de una discusión se comparan como strings —es lo que queda
    guardado de lo que alguien rechazó— y el mismo número llega escrito
    distinto según de dónde venga: de la base sale con la escala de la columna
    (`152400.0000`) y de una fila recién normalizada, sin ella (`152400`).
    Compararlos así diría que difieren dos importes iguales, y volvería a
    preguntar una discusión ya contestada.
    """
    if value is None:
        return "—"
    return format(value.quantize(Decimal("0.0001")), "f")


def _amount_of(value: str) -> Decimal | None:
    """Un importe que volvió de la cola, convertido sin confiar en él.

    `Decimal` construye `nan` e `Infinity` sin quejarse, y esto escribe sobre
    una columna de plata: la misma puerta que `CatalogService._as_number` y
    `_price_of` ya cierran del lado del catálogo. Lo que no se puede convertir
    vuelve `None`, que en una orden es un importe que no se conoce — no cero.
    """
    if value in {"", "—"}:
        return None
    try:
        amount = Decimal(value)
    except (InvalidOperation, ArithmeticError):
        logger.warning("A settled dispute carried an amount that is not a number")
        return None
    if not amount.is_finite() or amount < 0:
        logger.warning("A settled dispute carried an amount that is not one")
        return None
    return amount


def today_here() -> date:
    """Today, on the clock this business runs on.

    Buenos Aires and not UTC: a due date is a day somebody stands in the shop
    and reads, and three hours of the wrong day at each end is the whole
    difference between an invoice being due today and being overdue.
    """
    return datetime.now(UTC).astimezone(BUSINESS_TIME_ZONE).date()


@dataclass(frozen=True, slots=True)
class InvoiceFile:
    """The document of an invoice, ready to be handed to a browser (RF-04)."""

    content: bytes
    content_type: str
    filename: str


def _filename_for(number: str, content_type: str | None) -> str:
    """What the file is called once it leaves the platform.

    `Factura F-8411.pdf` and not the opaque name the portal used: whoever opens
    it is going to have it sitting in a folder afterwards, and the invoice
    number is the only thing they will search that folder by.
    """
    kind = (content_type or "").lower()
    extension = next((suffix for token, suffix in FILE_EXTENSIONS if token in kind), "")
    return f"Factura {number}{extension}"


class PurchasesService:
    """Registers invoices, resolves who they are from, and answers what is owed."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.purchases = PurchasesRepository(session)

    # --- The register ----------------------------------------------------

    async def remember_suppliers(self, suppliers: tuple[NormalizedSupplier, ...]) -> None:
        """Record the register exactly as `/estado-cuenta` publishes it (RF-08).

        Every legal name of the register also becomes a spelling of itself, so
        an invoice that arrives written exactly as the register writes it
        resolves without anybody being asked.

        «Exactly as it publishes it» stops at a field somebody corrected by
        hand: a correction in force holds, and a reading that contradicts it is
        reported instead of applied (RF-19). It is the same mechanism 003 built
        for a price, reused here rather than rebuilt — the correction lives in
        this module's own table precisely so these lines can ask it without
        asking another module anything.
        """
        moment = datetime.now(UTC)
        for card in suppliers:
            held = await self._corrections_holding(card, moment=moment)
            supplier = await self.purchases.put_supplier(
                legal_name=card.legal_name,
                tax_id=card.tax_id,
                email=None if "email" in held else card.email,
                phone=None if "phone" in held else card.phone,
                payment_term_days=(None if "payment_term_days" in held else card.payment_term_days),
                balance=card.balance,
            )
            await self.purchases.put_alias(
                text_normalized=normalize_entity_name(card.legal_name),
                text_original=card.legal_name,
                supplier_id=supplier.id,
                source=SupplierAliasSource.OBSERVED,
            )
            # El plazo puede haber aparecido recién ahora, y de él sale el
            # vencimiento de todas sus facturas (RF-26).
            await self._refresh_due_dates(supplier)
        logger.info("Supplier register updated", extra={"suppliers": len(suppliers)})

    async def _refresh_due_dates(self, supplier: Supplier) -> None:
        """Recompute the due dates of a supplier's invoices from its term (RF-26).

        The due date of an invoice **is** `issued_on + payment_term_days`, and
        the column the portal publishes only stands in while the term is not
        known. So the day the term appears — the register finally expands that
        row, or somebody corrects it by hand — every invoice of that supplier
        that was carrying the stand-in is still carrying it, and nothing was
        putting it right: the recomputation only ever happened when a held
        invoice was resolved.

        That is not a cosmetic gap. The due date is what the receipt deadline
        (RF-34), the ageing buckets (RF-25) and the average delay (RF-27) are
        all measured against, so one wrong date quietly wrongs three numbers
        the owner reads to decide whether they are keeping their word.

        **A date a person rescheduled is not touched**, the same rule the
        calendar and the register already follow: a decision somebody took is
        not undone by a later reading.
        """
        if supplier.payment_term_days is None:
            return
        moved = 0
        for invoice in await self.purchases.invoices_of_supplier(supplier.id):
            expected = invoice.issued_on + timedelta(days=supplier.payment_term_days)
            if invoice.due_on == expected:
                continue
            entry = await self.purchases.due_date_of_invoice(invoice.id)
            if entry is not None and entry.was_rescheduled:
                continue
            invoice.due_on = expected
            if invoice.original_due_on is None:
                invoice.original_due_on = expected
            await self.session.flush()
            await self._sync_due_date(invoice)
            moved += 1
        if moved:
            logger.info(
                "Due dates recomputed from the agreed term",
                extra={"supplier_id": supplier.id, "invoices": moved},
            )

    async def _corrections_holding(
        self, card: NormalizedSupplier, *, moment: datetime
    ) -> frozenset[str]:
        """The fields of this card the portal is not allowed to write (RF-19).

        A supplier the register publishes for the first time has nothing
        standing on it, and neither has one nobody ever corrected: the common
        morning costs one lookup and writes exactly what it wrote before.

        A field the register did **not** publish this time is not a
        contradiction — it is silence, and silence disagrees with nobody
        (`put_supplier` already leaves those alone).
        """
        supplier = await self.purchases.supplier_named(card.legal_name)
        if supplier is None:
            return frozenset()

        held: set[str] = set()
        for correction in await self.purchases.corrections_in_force([str(supplier.id)]):
            if (
                correction.entity_type != SUPPLIER_ENTITY
                or correction.field not in CORRECTABLE_SUPPLIER_FIELDS
            ):
                continue
            held.add(correction.field)
            incoming = getattr(card, correction.field, None)
            if incoming is not None:
                await self._check_supplier_conflict(correction, incoming=incoming, moment=moment)
        return frozenset(held)

    async def _check_supplier_conflict(
        self, correction: PurchaseCorrection, *, incoming: Any, moment: datetime
    ) -> None:
        """Compare what the register brings against what it used to say (RF-19).

        Three outcomes, and none of them touches the corrected value:

        * the register repeats what it had said — nothing happened;
        * it says something else — the correction is flagged and the owner is
          told, through `CorrectionConflicted` like every other module;
        * it says the same something else again — already flagged, so no second
          warning about the same difference.

        The comparison is against `portal_value` and not against the corrected
        value, and that is the whole point of the rule. Somebody corrects a
        phone **because** the register has it wrong, and the register goes on
        publishing the wrong one every morning: measured against the corrected
        value the owner would be told about the same difference every single
        day, and would stop reading it long before the day the register really
        changed its mind.
        """
        if self._same_detail(incoming, correction.portal_value):
            return
        if (
            correction.status is CorrectionStatus.CONFLICTED
            and correction.conflict_value is not None
            and self._same_detail(incoming, correction.conflict_value)
        ):
            return

        correction.status = CorrectionStatus.CONFLICTED
        correction.conflict_value = incoming
        correction.conflict_detected_at = moment
        await self.session.flush()
        await events.publish(
            CorrectionConflicted(
                entity_type=correction.entity_type,
                entity_id=correction.entity_id,
                field=correction.field,
                correction_id=correction.id,
                original_value=correction.portal_value,
                corrected_value=correction.corrected_value,
                incoming_value=incoming,
            ),
            self.session,
        )
        logger.warning(
            "The register contradicted a correction",
            extra={
                "correction_id": correction.id,
                "entity_id": correction.entity_id,
                "field": correction.field,
            },
        )

    @staticmethod
    def _same_detail(left: Any, right: Any) -> bool:
        """Whether two readings of a contact detail are the same reading.

        Compared as text on purpose: `payment_term_days` comes back from JSONB
        as an `int` and arrives from the register as an `int`, but a card that
        was stored when the column held a string would otherwise read as a
        change that never happened.
        """
        return str(left) == str(right)

    async def list_suppliers(self) -> SupplierList:
        """The register, with what the portal did not publish marked as missing."""
        suppliers = await self.purchases.suppliers()
        aliases: dict[int, list[SupplierAliasRead]] = defaultdict(list)
        for alias in await self.purchases.aliases():
            aliases[alias.supplier_id].append(SupplierAliasRead.model_validate(alias))
        marks = await self._supplier_marks([supplier.id for supplier in suppliers])
        items = [
            SupplierRead(
                id=supplier.id,
                legal_name=supplier.legal_name,
                tax_id=supplier.tax_id,
                email=supplier.email,
                phone=supplier.phone,
                payment_term_days=supplier.payment_term_days,
                balance=supplier.balance,
                missing=self._missing_of(supplier),
                aliases=aliases.get(supplier.id, []),
                invoice_count=await self.purchases.count_invoices(supplier_id=supplier.id),
                corrections=marks.get(supplier.id, []),
            )
            for supplier in suppliers
        ]
        return SupplierList(items=items, total=len(items))

    async def get_supplier(self, supplier_id: int) -> SupplierRead:
        """One supplier of the register (RF-10, RF-15, RF-20)."""
        supplier = await self._require_supplier(supplier_id)
        return SupplierRead(
            id=supplier.id,
            legal_name=supplier.legal_name,
            tax_id=supplier.tax_id,
            email=supplier.email,
            phone=supplier.phone,
            payment_term_days=supplier.payment_term_days,
            balance=supplier.balance,
            missing=self._missing_of(supplier),
            aliases=[
                SupplierAliasRead.model_validate(alias)
                for alias in await self.purchases.aliases()
                if alias.supplier_id == supplier.id
            ],
            invoice_count=await self.purchases.count_invoices(supplier_id=supplier.id),
            corrections=(await self._supplier_marks([supplier.id])).get(supplier.id, []),
        )

    async def _supplier_marks(
        self, supplier_ids: list[int]
    ) -> dict[int, list[SupplierCorrectionMark]]:
        """What each card's corrections look like on a screen (RF-18, RF-19).

        One query for the whole register rather than one per supplier: the
        padrón screen walks this once for every card it lists.
        """
        marks: dict[int, list[SupplierCorrectionMark]] = defaultdict(list)
        for correction in await self.purchases.corrections_in_force(
            [str(supplier_id) for supplier_id in supplier_ids]
        ):
            if correction.entity_type != SUPPLIER_ENTITY:
                continue
            marks[int(correction.entity_id)].append(
                SupplierCorrectionMark(
                    correction_id=correction.id,
                    field=correction.field,
                    portal_value=correction.portal_value,
                    corrected_value=correction.corrected_value,
                    status=correction.status,
                    conflict_value=correction.conflict_value,
                )
            )
        return marks

    @staticmethod
    def _missing_of(supplier: Supplier) -> list[str]:
        """The fields the portal has not published about this supplier.

        Said out loud rather than left blank: a screen that shows an empty cell
        for a phone nobody published looks exactly like one for a phone somebody
        forgot to read (RF-15, RF-20).
        """
        return [
            name
            for name, value in (
                ("tax_id", supplier.tax_id),
                ("email", supplier.email),
                ("phone", supplier.phone),
                ("payment_term_days", supplier.payment_term_days),
            )
            if value is None
        ]

    async def _require_supplier(self, supplier_id: int) -> Supplier:
        """Return the supplier, or say plainly that it is not in the register."""
        supplier = await self.purchases.supplier(supplier_id)
        if supplier is None:
            raise NotFoundError(NO_SUCH_SUPPLIER, details={"supplier_id": supplier_id})
        return supplier

    # --- Resolving who an invoice is from --------------------------------

    async def resolve_supplier(self, supplier_text: str) -> tuple[Supplier | None, str | None]:
        """Say which supplier a written name is, or why it cannot be said.

        Two paths **here**, in this order and no other: an exact spelling already
        known, and then a comparison against the register. There is no tax id
        path in this function on purpose, and the reason is not the trap — it is
        the timing. The invoices table publishes no tax id column, so the only
        place a tax id can come from is the file, and the file arrives after the
        row. RF-11 is therefore answered where the tax id exists, in
        `_identify_by_tax_id`, and not here where it never would.

        A comparison only identifies when it is both close enough and clearly
        ahead of the runner-up. Anything short of that is a case for a person:
        a supplier resolved wrongly breaks the debt and the totals, and there is
        no way to notice from the outside.
        """
        cleaned = supplier_text.strip()
        if not cleaned:
            return None, AMBIGUOUS_SUPPLIER

        key = normalize_entity_name(cleaned)
        alias = await self.purchases.alias_for(key)
        if alias is not None:
            return await self.purchases.supplier(alias.supplier_id), None

        suppliers = await self.purchases.suppliers()
        if not suppliers:
            return None, OUTSIDE_REGISTER

        threshold = int(await self._setting(MATCH_THRESHOLD_KEY))
        candidates = {
            supplier.id: normalize_entity_name(supplier.legal_name) for supplier in suppliers
        }
        ranked = process.extract(key, candidates, scorer=fuzz.token_sort_ratio, limit=2)
        if not ranked:
            return None, OUTSIDE_REGISTER

        best_score, best_id = ranked[0][1], ranked[0][2]
        runner_up = ranked[1][1] if len(ranked) > 1 else 0
        if best_score < threshold:
            return None, OUTSIDE_REGISTER
        if best_score - runner_up < MATCH_MARGIN:
            return None, AMBIGUOUS_SUPPLIER

        supplier = await self.purchases.supplier(int(best_id))
        if supplier is None:  # pragma: no cover - the register was just read
            return None, OUTSIDE_REGISTER
        # A spelling that matched with certainty is remembered as observed, so
        # the next invoice written the same way costs no comparison at all.
        await self.purchases.put_alias(
            text_normalized=key,
            text_original=cleaned,
            supplier_id=supplier.id,
            source=SupplierAliasSource.OBSERVED,
        )
        return supplier, None

    async def _supplier_with_tax_id(self, tax_id: str | None) -> Supplier | None:
        """The supplier that tax id belongs to, if it belongs to one of ours.

        Compared without punctuation, because `30-70918273-4` and `30709182734`
        are the same number and which one gets printed is the document's whim.
        A number that matches nobody in the register identifies nobody: it is
        not an error and it is not a case for a person, it is simply not an
        answer, and the name path gets its turn (RF-11).
        """
        if not tax_id:
            return None
        wanted = only_digits(tax_id)
        if not wanted:
            return None
        for supplier in await self.purchases.suppliers():
            if supplier.tax_id and only_digits(supplier.tax_id) == wanted:
                return supplier
        return None

    async def _setting(self, key: str) -> Any:
        """A business parameter, from this module's projection or its initial value."""
        stored = await self.purchases.setting(key)
        return initial_value(key) if stored is None else stored

    async def remember_setting(self, key: str, value: Any) -> None:
        """Keep a business parameter this module reads."""
        await self.purchases.put_setting(key, value)

    # --- Registering what the invoices screen brought --------------------

    async def register_invoices(
        self, *, batch_id: int, invoices: tuple[NormalizedInvoice, ...]
    ) -> None:
        """Bring a batch of invoices into the business model.

        Everything that cannot be decided without a person ends up held rather
        than resolved: an ambiguous supplier, a name outside the register, a
        number that repeats with a different total. What is held is still a
        registered invoice — it is counted, it is visible, and it is excluded
        from every total until somebody decides (RF-13, RF-14, RF-38 of 004).
        """
        registered: list[RegisteredInvoice] = []
        review: list[InvoiceReviewCase] = []

        for row in invoices:
            supplier, reason = await self.resolve_supplier(row.supplier_text)
            existing = await self.purchases.invoice_of(
                supplier_id=supplier.id if supplier else None,
                number=row.number,
                supplier_text=row.supplier_text,
            )
            if existing is not None:
                held = await self._count_arrival(existing, row, batch_id=batch_id)
                if held is not None:
                    review.append(held)
                continue

            invoice = await self._create_invoice(
                row, supplier=supplier, reason=reason, batch_id=batch_id
            )
            if invoice.review_state is InvoiceReviewState.PENDING:
                review.append(
                    InvoiceReviewCase(
                        invoice_id=invoice.id,
                        number=invoice.number,
                        reason=invoice.review_reason or AMBIGUOUS_SUPPLIER,
                        supplier_text=invoice.supplier_text,
                        supplier_key=normalize_entity_name(invoice.supplier_text),
                        needs_document=True,
                    )
                )
            elif supplier is not None:
                registered.append(
                    RegisteredInvoice(
                        invoice_id=invoice.id,
                        supplier_id=supplier.id,
                        number=invoice.number,
                        issued_on=invoice.issued_on,
                        total=invoice.total,
                        due_on=invoice.due_on,
                    )
                )

        if registered:
            await events.publish(
                InvoicesRegistered(invoices=tuple(registered), batch_id=batch_id), self.session
            )
        if review:
            await events.publish(
                InvoicesNeedingReview(cases=tuple(review), batch_id=batch_id), self.session
            )
        logger.info(
            "Invoices registered",
            extra={"batch_id": batch_id, "registered": len(registered), "held": len(review)},
        )

    async def _create_invoice(
        self,
        row: NormalizedInvoice,
        *,
        supplier: Supplier | None,
        reason: str | None,
        batch_id: int,
    ) -> Invoice:
        """Store one invoice, with its due date derived from the agreed term."""
        due_on = self._due_date_for(row, supplier)
        invoice = await self.purchases.add_invoice(
            Invoice(
                number=row.number,
                issued_on=row.issued_on,
                total=row.total,
                supplier_id=supplier.id if supplier else None,
                supplier_text=row.supplier_text,
                due_on=due_on,
                original_due_on=due_on,
                portal_paid=row.paid,
                portal_payment_status=row.portal_payment_status,
                portal_receipt_issued=row.receipt_issued,
                file_kind=row.file_kind,
                product_code=row.product_code,
                last_batch_id=batch_id,
                review_state=(
                    InvoiceReviewState.OK if supplier is not None else InvoiceReviewState.PENDING
                ),
                review_reason=reason,
                staging_row_id=row.staging_row_id,
            )
        )
        await self._sync_due_date(invoice)
        return invoice

    def _due_date_for(self, row: NormalizedInvoice, supplier: Supplier | None) -> date | None:
        """When this invoice falls due.

        From the **agreed payment term** of its supplier, counted from the date
        of the invoice, and from nothing else: RF-26 of 005 is explicit that no
        other date the document carries is used for this. Only when the term is
        not known — a supplier whose row the portal never expanded — does the
        date the table publishes stand in, because a due date that exists is
        worth more than none, and it is corrected the day the term is read.
        """
        if supplier is not None and supplier.payment_term_days is not None:
            return row.issued_on + timedelta(days=supplier.payment_term_days)
        return row.due_on

    async def _count_arrival(
        self, existing: Invoice, row: NormalizedInvoice, *, batch_id: int
    ) -> InvoiceReviewCase | None:
        """An invoice met again: counted only if it really arrived again.

        **What counts as an arrival, and why it is not «we saw it again».** The
        invoices screen is re-read on a schedule and re-normalised *whole*
        whenever its hash changes — one supplier paying one invoice rewrites
        one cell and brings the other ninety-nine rows back with it. Counting
        every meeting made `arrival_count` report how often the page had been
        read, so with the sync at twelve hours every invoice «arrived» twice a
        day for ever, and RF-39 said something true about the pipeline and false
        about the invoice.

        So an arrival is the portal publishing this invoice **twice in the same
        reading**: two rows, one page, one batch. Meeting it in a later batch is
        the same row read again and adds nothing.

        The total is compared either way. Two readings that disagree about what
        an invoice is worth is a contradiction whichever reading it came in, and
        it is not a decision this platform gets to take alone (RF-37, RF-38).
        """
        if existing.last_batch_id == batch_id:
            existing.arrival_count += 1
        existing.last_batch_id = batch_id
        existing.portal_paid = row.paid
        existing.portal_payment_status = row.portal_payment_status
        existing.portal_receipt_issued = row.receipt_issued
        await self.session.flush()

        if existing.origin is RecordOrigin.MANUAL:
            # La rama entera es de esta factura y **termina acá**. Dejarla caer
            # en la comparación de duplicados de abajo la apartaría de nuevo por
            # otro motivo, que para quien mira la pantalla es la misma pregunta
            # ya contestada, hecha otra vez con otras palabras.
            published = {"fecha": row.issued_on.isoformat(), "total": _money_text(row.total)}
            if existing.total == row.total and existing.issued_on == row.issued_on:
                return None
            if existing.rejected_portal_values == published:
                return None
            await self._dispute(existing, published)
            return None

        if existing.total == row.total:
            return None
        if existing.review_state is InvoiceReviewState.PENDING:
            return None
        existing.review_state = InvoiceReviewState.PENDING
        existing.review_reason = DUPLICATE_WITH_ANOTHER_TOTAL
        await self.session.flush()
        return InvoiceReviewCase(
            invoice_id=existing.id,
            number=existing.number,
            reason=DUPLICATE_WITH_ANOTHER_TOTAL,
            supplier_text=existing.supplier_text,
            excerpt=f"{existing.total} ≠ {row.total}",
        )

    async def _dispute(self, invoice: Invoice, published: dict[str, str]) -> None:
        """Apartar la factura y preguntar cuál de los dos valores queda.

        Se aparta **sin pisar nada**: mientras la discusión está abierta, la
        factura no suma en ningún total (que es lo que hace `PENDING`), y los dos
        juegos de valores siguen existiendo — el escrito, en la fila; el
        publicado, en el evento que abre el caso—. Escribir el del portal acá
        sería decidir la discusión antes de preguntarla.
        """
        invoice.review_state = InvoiceReviewState.PENDING
        invoice.review_reason = DISPUTED_BY_PORTAL
        await self.session.flush()
        await events.publish(
            ManualEntryDisputed(
                entity=INVOICE_ENTITY,
                entity_id=invoice.id,
                number=invoice.number,
                supplier_text=invoice.supplier_text,
                typed={
                    "fecha": invoice.issued_on.isoformat(),
                    "total": _money_text(invoice.total),
                },
                published=published,
            ),
            self.session,
        )

    async def _dispute_order(self, order: PurchaseOrder, published: dict[str, str]) -> None:
        """Apartar la orden y preguntar cuál de los dos valores queda."""
        order.review_state = OrderReviewState.PENDING
        order.review_reason = DISPUTED_BY_PORTAL
        await self.session.flush()
        await events.publish(
            ManualEntryDisputed(
                entity=ORDER_ENTITY,
                entity_id=order.id,
                number=order.number,
                supplier_text=order.supplier_text,
                typed={
                    "fecha": order.ordered_on.isoformat(),
                    "importe": _money_text(order.amount),
                },
                published=published,
            ),
            self.session,
        )

    # --- Lo que carga una persona ----------------------------------------

    async def register_invoice_by_hand(
        self,
        *,
        number: str,
        issued_on: date,
        total: Decimal,
        supplier_id: int,
        actor_user_id: int,
        occurred_at: datetime | None = None,
    ) -> Invoice:
        """Alta de la factura que el portal publicó rota y una persona reconstruyó.

        Es la otra mitad del Artículo II. Hasta acá una fila ilegible sólo se
        podía dar por revisada: quedaba contada y visible —que ya era más de lo
        que había— y el dato no entraba nunca, así que la factura no aparecía en
        ningún total ni en el calendario de vencimientos.

        Entra marcada como `MANUAL` y eso no es contabilidad interna: es la
        promesa del Artículo I de no mostrar como publicado por el portal algo
        que escribió una persona, y es lo único que permite reconocer, el día
        que el portal publique esa fila, que es la misma factura y no una
        segunda.

        El vencimiento sale del plazo acordado del proveedor, igual que el de
        cualquier otra (RF-26 de 005): no se pregunta, porque no es un dato de
        la factura sino del acuerdo con quien la emitió.
        """
        supplier = await self.purchases.supplier(supplier_id)
        if supplier is None:
            raise NotFoundError(SUPPLIER_NOT_IN_REGISTER, details={"supplier_id": supplier_id})

        existing = await self.purchases.invoice_of(
            supplier_id=supplier_id, number=number, supplier_text=supplier.legal_name
        )
        if existing is not None:
            # Ya está. Insistir sería la segunda factura que este alta existe
            # para no crear, y el índice único la rechazaría con un error que no
            # dice nada.
            raise ConflictError(
                ALREADY_REGISTERED, details={"invoice_id": existing.id, "number": number}
            )

        moment = occurred_at or datetime.now(UTC)
        due_on = (
            issued_on + timedelta(days=supplier.payment_term_days)
            if supplier.payment_term_days is not None
            else None
        )
        invoice = await self.purchases.add_invoice(
            Invoice(
                number=number,
                issued_on=issued_on,
                total=total,
                supplier_id=supplier_id,
                supplier_text=supplier.legal_name,
                origin=RecordOrigin.MANUAL,
                due_on=due_on,
                original_due_on=due_on,
                # Nadie la tiene que revisar: la revisó la persona que la
                # escribió, y quién y cuándo quedan asentados acá y en el log.
                review_state=InvoiceReviewState.RESOLVED,
                resolved_by_user_id=actor_user_id,
                resolved_at=moment,
            )
        )
        await self._sync_due_date(invoice)
        await events.publish(
            ManualChangeRecorded(
                entity_type=INVOICE_ENTITY,
                entity_id=str(invoice.id),
                action=AuditAction.CREATED,
                actor_user_id=actor_user_id,
                section=BusinessSection.PURCHASING,
                new_value={
                    "number": number,
                    "issued_on": issued_on.isoformat(),
                    "total": str(total),
                    "supplier_id": supplier_id,
                },
                reason_code="LOADED_BY_HAND",
                occurred_at=moment,
            ),
            self.session,
        )
        # Sin batch, porque no salió de ninguna lectura. Se anuncia igual: un
        # comprobante que estaba esperando esta factura se imputa solo, y esa es
        # exactamente la mitad del trabajo que la persona no tendría por qué
        # volver a hacer a mano (RF-44).
        await events.publish(
            InvoicesRegistered(
                invoices=(
                    RegisteredInvoice(
                        invoice_id=invoice.id,
                        supplier_id=supplier_id,
                        number=number,
                        issued_on=issued_on,
                        total=total,
                        due_on=due_on,
                    ),
                ),
                batch_id=None,
            ),
            self.session,
        )
        logger.info(
            "Invoice loaded by hand",
            extra={"invoice_id": invoice.id, "number": number, "actor": actor_user_id},
        )
        return invoice

    async def register_order_by_hand(
        self,
        *,
        number: str,
        ordered_on: date,
        supplier_id: int,
        product_text: str = "",
        quantity: int | None = None,
        amount: Decimal | None = None,
        actor_user_id: int,
        occurred_at: datetime | None = None,
    ) -> PurchaseOrder:
        """Alta de la orden que el portal publicó rota y una persona reconstruyó.

        Lo mismo que con la factura, con una diferencia que es del dominio: una
        orden cargada a mano **no se puede cronometrar en su estado**. La
        plataforma no la vio llegar, así que lo único cierto es hace cuánto se
        emitió, y se dice como eso (RF-49 de 007) en vez de fingir que el reloj
        de RF-05 arrancó cuando alguien la escribió.
        """
        supplier = await self.purchases.supplier(supplier_id)
        if supplier is None:
            raise NotFoundError(SUPPLIER_NOT_IN_REGISTER, details={"supplier_id": supplier_id})

        existing = await self.purchases.order_numbered(number)
        if existing is not None:
            raise ConflictError(
                ORDER_ALREADY_REGISTERED, details={"order_id": existing.id, "number": number}
            )

        moment = occurred_at or datetime.now(UTC)
        order = await self.purchases.add_order(
            PurchaseOrder(
                number=number,
                ordered_on=ordered_on,
                supplier_id=supplier_id,
                supplier_text=supplier.legal_name,
                origin=RecordOrigin.MANUAL,
                product_text=product_text,
                quantity=quantity,
                amount=amount,
                status_text="",
                status_since=today_here(),
                observed_from_start=False,
                review_state=OrderReviewState.RESOLVED,
                resolved_by_user_id=actor_user_id,
                resolved_at=moment,
            )
        )
        await events.publish(
            ManualChangeRecorded(
                entity_type=ORDER_ENTITY,
                entity_id=str(order.id),
                action=AuditAction.CREATED,
                actor_user_id=actor_user_id,
                section=BusinessSection.PURCHASING,
                new_value={
                    "number": number,
                    "ordered_on": ordered_on.isoformat(),
                    "supplier_id": supplier_id,
                },
                reason_code="LOADED_BY_HAND",
                occurred_at=moment,
            ),
            self.session,
        )
        logger.info(
            "Purchase order loaded by hand",
            extra={"order_id": order.id, "number": number, "actor": actor_user_id},
        )
        return order

    async def settle_manual_dispute(
        self,
        *,
        entity: str,
        entity_id: int,
        keep: str,
        published: dict[str, str],
        actor_user_id: int,
        occurred_at: datetime | None = None,
    ) -> None:
        """Aplicar lo que se decidió sobre una fila cargada a mano y publicada distinta.

        Las dos respuestas hacen algo. **Queda el portal**: los valores
        publicados pisan a los escritos y el registro pasa a tener el origen que
        de verdad tiene desde ahora. **Queda lo cargado a mano**: los valores no
        se tocan y el origen sigue siendo la persona, que es la verdad de ese
        dato aunque el portal diga otra cosa.

        En los dos casos el registro deja de estar apartado, porque la duda que
        lo apartaba está contestada, y en los dos queda asentado quién contestó.
        """
        moment = occurred_at or datetime.now(UTC)
        record = (
            await self.purchases.invoice(entity_id)
            if entity == INVOICE_ENTITY
            else await self.purchases.order(entity_id)
        )
        if record is None:
            # El registro se fue mientras el caso esperaba. No es un error: la
            # decisión ya quedó guardada del lado de la cola, y acá no hay a qué
            # aplicarla.
            logger.warning("A settled dispute found no record", extra={"entity_id": entity_id})
            return

        changed: dict[str, str] = {}
        if keep == KEEP_PORTAL:
            changed = self._apply_published(record, published)
            record.origin = RecordOrigin.PORTAL
            record.rejected_portal_values = None
        else:
            # Se queda lo que escribió la persona, y queda dicho **qué** rechazó:
            # el portal va a publicar esa misma fila cada doce horas, y sin esto
            # la pregunta ya contestada volvería con cada lectura.
            record.rejected_portal_values = published

        if isinstance(record, Invoice):
            record.review_state = InvoiceReviewState.RESOLVED
        else:
            record.review_state = OrderReviewState.RESOLVED
        record.review_reason = None
        record.resolved_by_user_id = actor_user_id
        record.resolved_at = moment
        await self.session.flush()

        if isinstance(record, Invoice):
            await self._sync_due_date(record)

        if changed:
            await events.publish(
                ManualChangeRecorded(
                    entity_type=entity,
                    entity_id=str(entity_id),
                    action=AuditAction.UPDATED,
                    actor_user_id=actor_user_id,
                    section=BusinessSection.PURCHASING,
                    new_value=changed,
                    reason_code="PORTAL_PUBLISHED_IT_LATER",
                    occurred_at=moment,
                ),
                self.session,
            )
        logger.info(
            "Manual dispute settled",
            extra={"entity": entity, "entity_id": entity_id, "keep": keep},
        )

    @staticmethod
    def _apply_published(
        record: Invoice | PurchaseOrder, published: dict[str, str]
    ) -> dict[str, str]:
        """Escribir sobre el registro lo que el portal publicó, y decir qué cambió.

        Cada valor se convierte acá y no se confía: lo que llega es lo que este
        módulo puso en el evento hace meses, y volvió después de dar la vuelta
        por la cola y por el navegador. Un valor que no se puede convertir se
        deja como estaba — pisar un dato bueno con basura sería peor que no
        aplicar la decisión.
        """
        changed: dict[str, str] = {}
        fecha = published.get("fecha")
        if fecha:
            try:
                parsed = date.fromisoformat(fecha)
            except ValueError:
                logger.warning("A settled dispute carried a date that is not one")
            else:
                if isinstance(record, Invoice):
                    record.issued_on = parsed
                else:
                    record.ordered_on = parsed
                changed["fecha"] = fecha

        importe = published.get("importe")
        if importe is not None and isinstance(record, PurchaseOrder):
            record.amount = _amount_of(importe)
            changed["importe"] = importe

        total = published.get("total")
        if total is not None and isinstance(record, Invoice):
            try:
                amount = Decimal(total)
            except (InvalidOperation, ArithmeticError):
                logger.warning("A settled dispute carried a total that is not a number")
            else:
                if amount.is_finite() and amount >= 0:
                    record.total = amount
                    changed["total"] = total
        return changed

    async def record_document(
        self,
        *,
        invoice_number: str,
        raw_document_id: int,
        readable: bool,
        agrees: bool,
        excerpt: str,
        reason: str | None,
        number: str | None,
        issued_on: date | None,
        total: Decimal | None,
        supplier_text: str | None,
        supplier_tax_id: str | None = None,
        content: bytes | None = None,
        content_type: str | None = None,
    ) -> None:
        """Keep what the document said, and hold the invoice when it disagrees.

        This is where the comparison becomes a decision. A document that says
        the same as the table makes the invoice certainty and nobody is
        bothered; one that says something else, or that could not be read at
        all, holds the invoice with the excerpt in view (RF-27, RF-29, RF-30).

        It is also the **only** moment a tax id can identify a supplier
        (RF-11). The invoices table publishes no tax id column — it was looked
        for and it is not there — so the number, when it exists at all, exists
        inside the file, and the file arrives after the row it belongs to. An
        invoice waiting because its name resolved to nobody is therefore
        resolved here, by its tax id, without a person having to look at it.

        An invoice already held for another reason is left as it is: it is
        already waiting for the same person, and rewriting its reason would lose
        the first one.
        """
        candidates = await self.purchases.invoices_numbered(invoice_number)
        if not candidates:
            logger.warning(
                "A document arrived for an unknown invoice", extra={"number": invoice_number}
            )
            return
        invoice = candidates[0]

        await self.purchases.put_document(
            InvoiceDocument(
                invoice_id=invoice.id,
                raw_document_id=raw_document_id,
                readable=readable,
                agrees=agrees,
                excerpt=excerpt,
                reason=reason,
                read_number=number,
                read_issued_on=issued_on,
                read_total=total,
                read_supplier_text=supplier_text,
                read_supplier_tax_id=supplier_tax_id,
                content=content,
                content_type=content_type,
            )
        )
        if await self._identify_by_tax_id(invoice, supplier_tax_id):
            return
        if not agrees and invoice.review_state is InvoiceReviewState.OK:
            invoice.review_state = InvoiceReviewState.PENDING
            invoice.review_reason = FILE_DISAGREES if readable else FILE_UNREADABLE
            await self.session.flush()
        logger.info(
            "Invoice document recorded",
            extra={"invoice_id": invoice.id, "agrees": agrees, "readable": readable},
        )

    async def _identify_by_tax_id(self, invoice: Invoice, tax_id: str | None) -> bool:
        """Give a waiting invoice its supplier when the document printed its tax id.

        Only an invoice that is waiting **because of its supplier** — nobody
        could tell whose it was, or it looked like somebody outside the register
        — is touched. An invoice held because the document disagrees about a
        number is a different question and the tax id does not answer it.

        Nothing is attributed to a person here: this is the platform reading a
        number that identifies without interpretation, which is what RF-11 asks
        for, so `resolved_by_user_id` stays empty and the invoice never reaches
        the queue.
        """
        if invoice.review_state is not InvoiceReviewState.PENDING:
            return False
        if invoice.review_reason not in (AMBIGUOUS_SUPPLIER, OUTSIDE_REGISTER):
            return False
        supplier = await self._supplier_with_tax_id(tax_id)
        if supplier is None:
            return False

        invoice.supplier_id = supplier.id
        invoice.review_state = InvoiceReviewState.OK
        invoice.review_reason = None
        if supplier.payment_term_days is not None:
            invoice.due_on = invoice.issued_on + timedelta(days=supplier.payment_term_days)
            if invoice.original_due_on is None:
                invoice.original_due_on = invoice.due_on
        await self.session.flush()
        await self._sync_due_date(invoice)
        logger.info(
            "Invoice identified by the tax id its document printed",
            extra={"invoice_id": invoice.id, "supplier_id": supplier.id},
        )
        return True

    # --- Reading the invoices --------------------------------------------

    async def list_invoices(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        supplier_id: int | None = None,
        query: str | None = None,
        review_state: InvoiceReviewState | None = None,
        payment_state: str | None = None,
        issued_from: date | None = None,
        issued_to: date | None = None,
        due_from: date | None = None,
        due_to: date | None = None,
        with_receipt: bool | None = None,
        order: InvoiceOrder = InvoiceOrder.ISSUED_DESC,
    ) -> InvoiceList:
        """The invoices screen, with the filters of RF-41 to RF-46 and RF-04 of 005.

        **Two date ranges, and they answer different questions.** `issued_from`
        and `issued_to` are the date the supplier put on the invoice — the one
        the screen shows and the one RF-43 filters by. `due_from` and `due_to`
        are the day it has to be paid, which is derived from the agreed term and
        belongs to the calendar of 005. Collapsing them into one range would
        make «las facturas de mayo» mean two different sets of invoices
        depending on who asked.

        The payment state is **not** stored — storing it would be a second
        answer to a question the payments already answer — but it is filtered
        in the query all the same, over the sum of what is imputed. Filtering it
        after reading the page filtered the page and not the listing: it came
        back short, and `total` counted rows the filter had just removed.
        """
        invoices = await self.purchases.list_invoices(
            skip=skip,
            limit=limit,
            supplier_id=supplier_id,
            query=query,
            review_state=review_state,
            issued_from=issued_from,
            issued_to=issued_to,
            due_from=due_from,
            due_to=due_to,
            with_receipt=with_receipt,
            payment_state=payment_state,
            order=order,
        )
        total = await self.purchases.count_invoices(
            supplier_id=supplier_id,
            query=query,
            review_state=review_state,
            issued_from=issued_from,
            issued_to=issued_to,
            due_from=due_from,
            due_to=due_to,
            with_receipt=with_receipt,
            payment_state=payment_state,
        )
        return InvoiceList(
            items=await self._read_invoices(invoices), total=total, skip=skip, limit=limit
        )

    async def get_invoice(self, invoice_id: int) -> InvoiceRead:
        """One invoice, with its payments, its receipt and what its document said."""
        invoice = await self._require_invoice(invoice_id)
        read = (await self._read_invoices([invoice]))[0]
        document = await self.purchases.document_of(invoice.id)
        if document is not None:
            read.document = InvoiceDocumentRead.model_validate(document)
        return read

    async def payments_of(self, invoice_id: int) -> list[PaymentRead]:
        """Every payment of an invoice, with its date and its amount (RF-10 of 005)."""
        await self._require_invoice(invoice_id)
        return [
            PaymentRead.model_validate(payment)
            for payment in await self.purchases.payments_of(invoice_id)
        ]

    async def _read_invoices(self, invoices: list[Invoice]) -> list[InvoiceRead]:
        """Render invoices with everything the screens compute rather than store."""
        if not invoices:
            return []
        paid = await self.purchases.imputed_totals()
        receipts = await self.purchases.invoices_with_receipt()
        numbers = await self.purchases.receipt_numbers()
        names = {supplier.id: supplier.legal_name for supplier in await self.purchases.suppliers()}
        today = today_here()

        items: list[InvoiceRead] = []
        for invoice in invoices:
            read = InvoiceRead.model_validate(invoice)
            read.supplier_name = names.get(invoice.supplier_id or 0)
            read.paid = paid.get(invoice.id, Decimal(0))
            read.balance = invoice.total - read.paid
            read.receipt_issued = invoice.id in receipts
            # Declarado desde el primer día y nunca asignado: viajaba `null`
            # hasta acá y hasta el tipo generado del frontend. Una factura cuyo
            # recibo lo emitió el portal se queda sin número, y eso es exacto:
            # ese número no es nuestro y no lo conocemos.
            read.receipt_number = numbers.get(invoice.id)
            read.portal_payment_status = invoice.portal_payment_status
            read.payment_state = self._payment_state(invoice.total, read.paid)
            read.is_inconsistent = read.payment_state == INCONSISTENT
            read.paid_pct = (
                0
                if invoice.total <= 0
                else int((read.paid / invoice.total * HUNDRED).quantize(Decimal(1)))
            )
            read.payment_state_disagrees = self._disagrees(
                read.payment_state, invoice.portal_payment_status
            )
            read.is_overdue_without_receipt = (
                invoice.due_on is not None and invoice.due_on < today and not read.receipt_issued
            )
            items.append(read)
        return items

    @staticmethod
    def _payment_state(total: Decimal, paid: Decimal) -> str:
        """The state of an invoice, from the payments imputed to it (RF-45 of 005).

        More paid than invoiced is **not** settled: it is inconsistent, and the
        platform says so and leaves it out of the totals rather than reporting a
        debt it cannot vouch for (RF-14, RF-16, RF-17).
        """
        if paid > total:
            return INCONSISTENT
        if paid <= 0:
            return UNPAID
        return SETTLED if paid >= total else PARTIAL

    @staticmethod
    def _disagrees(computed: str, portal_status: str | None) -> bool:
        """Whether the portal's own state contradicts the one the payments give.

        A state the portal words in a way this platform does not recognise is
        not a disagreement: it is something new to read, and calling it a
        contradiction would flag every invoice the day the portal adds a word.
        """
        if portal_status is None:
            return False
        expected = PORTAL_STATES.get(portal_status)
        return expected is not None and expected != computed

    async def invoice_file(self, invoice_id: int) -> InvoiceFile:
        """The document of an invoice, as it came (RF-04 of 004).

        A missing file is a `404` and not an empty body: an invoice whose
        document never arrived — the portal link expired, or the download is
        still queued — is a fact somebody has to be told, and a browser handed
        zero bytes with a `200` reads it as a broken file instead.
        """
        invoice = await self._require_invoice(invoice_id)
        document = await self.purchases.document_of(invoice.id)
        if document is None or not document.content:
            raise NotFoundError(NO_INVOICE_FILE, details={"invoice_id": invoice_id})
        return InvoiceFile(
            content=document.content,
            content_type=document.content_type or DEFAULT_FILE_TYPE,
            filename=_filename_for(invoice.number, document.content_type),
        )

    async def _require_invoice(self, invoice_id: int) -> Invoice:
        """Return the invoice, or say plainly that it is not there."""
        invoice = await self.purchases.invoice(invoice_id)
        if invoice is None:
            raise NotFoundError(NO_SUCH_INVOICE, details={"invoice_id": invoice_id})
        return invoice

    # --- Deciding about an invoice held for review -----------------------

    async def review_queue(self, *, skip: int = 0, limit: int = 50) -> InvoiceList:
        """What is waiting for a person, with what it says and why (RF-30, RF-34)."""
        return await self.list_invoices(
            skip=skip, limit=limit, review_state=InvoiceReviewState.PENDING
        )

    async def resolve_invoice(
        self,
        invoice_id: int,
        *,
        supplier_id: int | None,
        remember: bool,
        actor_user_id: int,
        number: str | None = None,
        issued_on: date | None = None,
        total: Decimal | None = None,
    ) -> InvoiceRead:
        """Record what a person decided about a held invoice (RF-31, RF-32, RF-33).

        A held invoice can be waiting on two different questions, and this
        answers both. **What it says**: the header fields the document put in
        doubt are corrected here, and each correction is recorded with who made
        it, when, and what the value was before (RF-31, RF-18). **Who it is
        from**: saying which supplier resolves this invoice, and asking to
        remember it turns the spelling into a rule that resolves every other
        invoice written the same way — the retroactivity of RF-49, and what the
        preview counted before the decision was taken.

        The corrections are applied **first**, on purpose: the due date and the
        calendar entry follow from the date and the total, so attaching the
        supplier afterwards computes them once, from the values a person just
        confirmed, instead of from the ones they were about to replace.
        """
        invoice = await self._require_invoice(invoice_id)
        # Antes de tocarla: si estaba apartada por una discusión con el portal,
        # resolverla acá también contesta esa discusión.
        was_disputed = invoice.review_reason == DISPUTED_BY_PORTAL
        await self._correct_invoice_fields(
            invoice,
            number=number,
            issued_on=issued_on,
            total=total,
            actor_user_id=actor_user_id,
        )
        if supplier_id is None:
            # A decision that names no supplier is a decision that this invoice
            # is fine as it stands — a duplicate somebody looked at, a document
            # that disagreed and was checked by hand.
            invoice.review_state = InvoiceReviewState.RESOLVED
            invoice.review_reason = None
            invoice.resolved_by_user_id = actor_user_id
            invoice.resolved_at = datetime.now(UTC)
            await self.session.flush()
            await self._announce_dispute_settled(invoice, was_disputed)
            await self.session.commit()
            return await self.get_invoice(invoice_id)

        supplier = await self._require_supplier(supplier_id)
        alias_id: int | None = None
        if remember:
            alias = await self.purchases.put_alias(
                text_normalized=normalize_entity_name(invoice.supplier_text),
                text_original=invoice.supplier_text,
                supplier_id=supplier.id,
                source=SupplierAliasSource.LEARNED,
                created_by_user_id=actor_user_id,
            )
            alias_id = alias.id

        await self._attach(invoice, supplier, actor_user_id=actor_user_id, alias_id=alias_id)
        if remember:
            await self._apply_alias(
                normalize_entity_name(invoice.supplier_text),
                supplier=supplier,
                alias_id=alias_id,
                actor_user_id=actor_user_id,
            )
        await self._announce_dispute_settled(invoice, was_disputed)
        await self.session.commit()
        logger.info(
            "Invoice resolved", extra={"invoice_id": invoice_id, "supplier_id": supplier.id}
        )
        return await self.get_invoice(invoice_id)

    async def _announce_dispute_settled(self, invoice: Invoice, was_disputed: bool) -> None:
        """Decir que la discusión con el portal se contestó en esta pantalla.

        Anunciado y no llamado: `purchases` no puede tocar `triage`
        (Artículo IV), así que declara un hecho —una clase y una clave— y quien
        le importe escucha. La clave es la misma con la que se abrió el caso, y
        no una parecida: un fingerprint reconstruido con generosidad cerraría un
        caso que nadie resolvió.
        """
        if not was_disputed:
            return
        await events.publish(
            QuarantinedSourceResolved(
                kind=DISPUTED_INVOICE_CASE,
                key=f"{INVOICE_ENTITY}:{invoice.id}",
                resolved_where=RESOLVED_IN_INVOICES,
            ),
            self.session,
        )

    async def _correct_invoice_fields(
        self,
        invoice: Invoice,
        *,
        number: str | None,
        issued_on: date | None,
        total: Decimal | None,
        actor_user_id: int,
    ) -> list[str]:
        """Write the header fields a person confirmed or corrected (RF-31 of 004).

        A field that arrives equal to what is stored is a **confirmation**, and
        a confirmation is not a change: it writes nothing and it records
        nothing. What gets recorded is a person disagreeing with the portal, and
        that goes out as `ManualChangeRecorded` with the previous value, so the
        log answers «who decided this number was that number» (RF-18, RF-32).

        Changing the number is the one that can collide: two invoices of the
        same supplier cannot share it, and the database index says so. It is
        checked here so the person gets a sentence instead of an integrity
        error.
        """
        changed: list[str] = []
        if number is not None and number.strip() and number.strip() != invoice.number:
            await self._require_free_number(invoice, number.strip())
            changed.append(
                await self._record_invoice_change(invoice, "number", number.strip(), actor_user_id)
            )
        if issued_on is not None and issued_on != invoice.issued_on:
            changed.append(
                await self._record_invoice_change(invoice, "issued_on", issued_on, actor_user_id)
            )
        if total is not None and total != invoice.total:
            changed.append(
                await self._record_invoice_change(invoice, "total", total, actor_user_id)
            )

        if not changed:
            return changed

        await self.session.flush()
        # The due date is derived from the date of the invoice and the agreed
        # term, and the calendar entry carries the amount. Both follow a
        # correction rather than being left describing the old numbers.
        supplier = (
            await self.purchases.supplier(invoice.supplier_id) if invoice.supplier_id else None
        )
        if supplier is not None and supplier.payment_term_days is not None:
            invoice.due_on = invoice.issued_on + timedelta(days=supplier.payment_term_days)
            await self.session.flush()
        await self._sync_due_date(invoice)
        logger.info(
            "Invoice header corrected by hand",
            extra={"invoice_id": invoice.id, "fields": changed},
        )
        return changed

    async def _require_free_number(self, invoice: Invoice, number: str) -> None:
        """Refuse a number that belongs to another invoice of the same supplier."""
        if invoice.supplier_id is None:
            return
        taken = await self.purchases.invoice_of(
            supplier_id=invoice.supplier_id,
            number=number,
            supplier_text=invoice.supplier_text,
        )
        if taken is not None and taken.id != invoice.id:
            raise ConflictError(
                INVOICE_NUMBER_TAKEN, details={"number": number, "invoice_id": taken.id}
            )

    async def _record_invoice_change(
        self, invoice: Invoice, field: str, value: Any, actor_user_id: int
    ) -> str:
        """Write one field and publish the fact that a person wrote it."""
        previous = getattr(invoice, field)
        setattr(invoice, field, value)
        await events.publish(
            ManualChangeRecorded(
                entity_type=INVOICE_ENTITY,
                entity_id=str(invoice.id),
                action=AuditAction.CORRECTED,
                actor_user_id=actor_user_id,
                section=PURCHASING_SECTION,
                field=field,
                old_value=str(previous),
                new_value=str(value),
                reason_detail=INVOICE_RESOLVED_BY_HAND,
            ),
            self.session,
        )
        return field

    async def preview_alias(self, *, text: str, supplier_id: int) -> AliasPreview:
        """How many held invoices this assignment would resolve (RF-48 of 004).

        Counted with the very query that will resolve them, so the number the
        screen promises is the number that happens.
        """
        await self._require_supplier(supplier_id)
        key = normalize_entity_name(text)
        matching = [
            invoice
            for invoice in await self.purchases.pending_invoices()
            if normalize_entity_name(invoice.supplier_text) == key
        ]
        return AliasPreview(
            text_original=text.strip(),
            supplier_id=supplier_id,
            invoices=len(matching),
            numbers=[invoice.number for invoice in matching],
        )

    async def save_alias(self, *, text: str, supplier_id: int, actor_user_id: int) -> AliasPreview:
        """Assign a spelling to a supplier and resolve what was waiting on it."""
        supplier = await self._require_supplier(supplier_id)
        key = normalize_entity_name(text)
        alias = await self.purchases.put_alias(
            text_normalized=key,
            text_original=text.strip(),
            supplier_id=supplier.id,
            source=SupplierAliasSource.LEARNED,
            created_by_user_id=actor_user_id,
        )
        resolved = await self._apply_alias(
            key, supplier=supplier, alias_id=alias.id, actor_user_id=actor_user_id
        )
        await self.session.commit()
        logger.info(
            "Supplier spelling saved",
            extra={"alias_id": alias.id, "supplier_id": supplier.id, "invoices": len(resolved)},
        )
        return AliasPreview(
            text_original=alias.text_original,
            supplier_id=supplier.id,
            invoices=len(resolved),
            numbers=resolved,
        )

    async def list_aliases(self) -> list[SupplierAliasRead]:
        """Every spelling in force, with who decided it (RF-51 of 004)."""
        return [SupplierAliasRead.model_validate(alias) for alias in await self.purchases.aliases()]

    async def drop_alias(self, alias_id: int) -> int:
        """Leave an assignment without effect and give back what it resolved (RF-53).

        The scope is exactly what that assignment resolved. An invoice somebody
        decided one by one does not depend on it and does not come back.
        """
        alias = await self.purchases.alias_by_id(alias_id)
        if alias is None:
            raise NotFoundError("No encontramos esa grafía", details={"alias_id": alias_id})

        returned = await self.purchases.invoices_resolved_by_alias(alias_id)
        for invoice in returned:
            invoice.supplier_id = None
            invoice.resolved_by_alias_id = None
            invoice.resolved_by_user_id = None
            invoice.resolved_at = None
            invoice.review_state = InvoiceReviewState.PENDING
            invoice.review_reason = AMBIGUOUS_SUPPLIER
        await self.purchases.drop_alias(alias)
        await self.session.commit()
        logger.info(
            "Supplier spelling revoked", extra={"alias_id": alias_id, "invoices": len(returned)}
        )
        return len(returned)

    async def _apply_alias(
        self, key: str, *, supplier: Supplier, alias_id: int | None, actor_user_id: int
    ) -> list[str]:
        """Attach everything held under this spelling to the supplier.

        **Invoices and purchase orders, in the same pass**, and that is signed
        scope rather than tidiness: the 007 says the criterion is one and the
        same for both — *«una decisión sobre una forma de escribir un nombre se
        toma una sola vez y sirve para todo»* — and spells out the consequence,
        that resolving an order also identifies the invoices that were waiting
        on that spelling, and the other way round.

        There is one table of spellings (`core.supplier_alias`) and therefore
        one decision. Walking only invoices here would have meant the same name
        being decided twice — and the survey measured **twenty** different ways
        of writing a supplier's name in the purchase orders alone.
        """
        resolved: list[str] = []
        for invoice in await self.purchases.pending_invoices():
            if normalize_entity_name(invoice.supplier_text) != key:
                continue
            await self._attach(invoice, supplier, actor_user_id=actor_user_id, alias_id=alias_id)
            resolved.append(invoice.number)
        for order in await self.purchases.pending_orders():
            if normalize_entity_name(order.supplier_text) != key:
                continue
            await self._attach_order(order, supplier, actor_user_id=actor_user_id)
            resolved.append(order.number)
        return resolved

    async def _attach(
        self, invoice: Invoice, supplier: Supplier, *, actor_user_id: int, alias_id: int | None
    ) -> None:
        """Give a held invoice its supplier, and everything that follows from it.

        Its due date is recalculated from the agreed term, because until now
        there was no term to calculate it from, and its entry on the calendar
        moves with it.
        """
        invoice.supplier_id = supplier.id
        invoice.review_state = InvoiceReviewState.RESOLVED
        invoice.review_reason = None
        invoice.resolved_by_user_id = actor_user_id
        invoice.resolved_at = datetime.now(UTC)
        invoice.resolved_by_alias_id = alias_id
        if supplier.payment_term_days is not None:
            invoice.due_on = invoice.issued_on + timedelta(days=supplier.payment_term_days)
            if invoice.original_due_on is None:
                invoice.original_due_on = invoice.due_on
        await self.session.flush()
        await self._sync_due_date(invoice)

    # --- The totals of a supplier ----------------------------------------

    async def supplier_totals(
        self, supplier_id: int, *, since: date | None = None, until: date | None = None
    ) -> SupplierTotalsRead:
        """What a supplier was invoiced, what was paid and what is owed.

        What is **left out** travels with the number: an invoice in review or
        one whose payments exceed its total is excluded, and how many were
        excluded is reported rather than buried (RF-22, RF-23 of 004; RF-16,
        RF-28 of 005). A total that quietly drops rows is a total the client
        will disprove the first time they check it by hand.
        """
        await self._require_supplier(supplier_id)
        invoices = await self.purchases.list_invoices(supplier_id=supplier_id, limit=100_000)
        read = await self._read_invoices(invoices)
        today = today_here()

        def in_period(item: InvoiceRead) -> bool:
            return (since is None or item.issued_on >= since) and (
                until is None or item.issued_on <= until
            )

        counted = [
            item
            for item in read
            if item.review_state is not InvoiceReviewState.PENDING
            and not item.is_inconsistent
            and in_period(item)
        ]
        # Counted apart, and in this order, because one invoice can be left out
        # for more than one reason and it has to be reported once. Being held is
        # what RF-23 asks about, so it wins; falling outside the period is the
        # weakest reason — it says nothing is wrong with the invoice.
        in_review = [item for item in read if item.review_state is InvoiceReviewState.PENDING]
        inconsistent = [
            item
            for item in read
            if item.review_state is not InvoiceReviewState.PENDING and item.is_inconsistent
        ]
        out_of_period = [
            item
            for item in read
            if item.review_state is not InvoiceReviewState.PENDING
            and not item.is_inconsistent
            and not in_period(item)
        ]
        excluded = len(read) - len(counted)

        invoiced = sum((item.total for item in counted), Decimal(0))
        paid = sum((item.paid for item in counted), Decimal(0))
        return SupplierTotalsRead(
            supplier_id=supplier_id,
            invoiced=invoiced,
            paid=paid,
            owed=invoiced - paid,
            invoices=len(counted),
            excluded=excluded,
            excluded_in_review=len(in_review),
            excluded_inconsistent=len(inconsistent),
            excluded_out_of_period=len(out_of_period),
            aging=self._aging_of(counted, today),
            average_delay_days=await self._average_delay(counted, today),
            since=since,
            until=until,
        )

    @staticmethod
    def _aging_of(invoices: list[InvoiceRead], today: date) -> list[AgingBucket]:
        """Split what is owed into bands, counted from each due date (RF-25 of 005)."""
        amounts: dict[str, Decimal] = {label: Decimal(0) for label, _ in AGING_BANDS}
        counts: dict[str, int] = {label: 0 for label, _ in AGING_BANDS}
        for invoice in invoices:
            if invoice.balance <= 0:
                continue
            overdue_days = 0 if invoice.due_on is None else (today - invoice.due_on).days
            label = next(
                (
                    name
                    for name, limit in AGING_BANDS
                    if limit is not None and overdue_days <= limit
                ),
                AGING_BANDS[-1][0],
            )
            amounts[label] += invoice.balance
            counts[label] += 1
        return [
            AgingBucket(label=label, amount=amounts[label], invoices=counts[label])
            for label, _ in AGING_BANDS
        ]

    async def _average_delay(self, invoices: list[InvoiceRead], today: date) -> Decimal | None:
        """How late this supplier's invoices run against their agreed term (RF-27).

        A settled invoice counts up to the payment that settled it; one still
        unpaid and overdue counts up to today. An invoice that is not yet due is
        not late and does not enter the average — including it as a zero would
        drag the number towards nothing every time a new invoice arrives.
        """
        delays: list[int] = []
        for invoice in invoices:
            if invoice.due_on is None:
                continue
            if invoice.payment_state == SETTLED:
                payments = await self.purchases.payments_of(invoice.id)
                settled_on = max(
                    (
                        payment.paid_on
                        for payment in payments
                        if payment.state is PaymentState.IMPUTED
                    ),
                    default=None,
                )
                if settled_on is not None and settled_on > invoice.due_on:
                    delays.append((settled_on - invoice.due_on).days)
            elif invoice.due_on < today:
                delays.append((today - invoice.due_on).days)
        if not delays:
            return None
        return (Decimal(sum(delays)) / Decimal(len(delays))).quantize(Decimal("0.1"))

    # --- The payments (005) ----------------------------------------------

    async def impute_payments(self, payments: tuple[NormalizedPayment, ...]) -> None:
        """Register the vouchers the current account publishes.

        **What the survey found, and what it costs.** The vouchers of this
        portal reference their own receipt number (`REC-1084`) and not the
        invoice they cover, so most of them cannot be imputed to an invoice
        without guessing. They are registered against their supplier and wait,
        counted and visible, for a person to say what they cover (RF-53). That
        is Artículo II working as intended, and it is a finding about the origin
        rather than a shortcoming here: the alternative is the platform deciding
        where somebody's money went.

        A voucher already registered is not registered twice (RF-13): the unique
        key on its external id is what says so.
        """
        held: list[PaymentReviewCase] = []
        for row in payments:
            if row.external_id and await self.purchases.payment_with_external_id(row.external_id):
                continue

            supplier, _ = await self.resolve_supplier(row.supplier_text)
            invoice, reason = await self._invoice_for(row)
            twin = (
                None
                if invoice is None
                else await self.purchases.similar_manual_payment(
                    invoice_id=invoice.id, amount=row.amount
                )
            )
            if twin is not None:
                # The same invoice, the same amount, and one of them was typed
                # by a person: imputing both would double the payment, and
                # deciding which to keep is not this platform's call (RF-42).
                reason, invoice = VOUCHER_LOOKS_MANUAL, None

            payment = await self.purchases.add_payment(
                Payment(
                    supplier_id=supplier.id if supplier else None,
                    invoice_id=invoice.id if invoice else None,
                    amount=row.amount,
                    paid_on=row.paid_on,
                    origin=PaymentOrigin.PORTAL,
                    state=PaymentState.IMPUTED if invoice else PaymentState.PENDING,
                    external_id=row.external_id or None,
                    reference=", ".join(row.references) or None,
                    supplier_text=row.supplier_text,
                    review_reason=reason,
                    staging_row_id=row.staging_row_id,
                )
            )
            if payment.state is PaymentState.PENDING:
                held.append(
                    PaymentReviewCase(
                        payment_id=payment.id,
                        reason=reason or VOUCHER_WITHOUT_INVOICE,
                        reference=payment.reference or "",
                        supplier_text=row.supplier_text,
                        amount=row.amount,
                    )
                )

        if held:
            await events.publish(PaymentsNeedingReview(cases=tuple(held)), self.session)
        logger.info("Payments imputed", extra={"vouchers": len(payments), "held": len(held)})

    async def _invoice_for(self, row: NormalizedPayment) -> tuple[Invoice | None, str | None]:
        """The invoice a voucher covers, or why it cannot be said.

        Three answers, and none of them is a guess: the voucher names one
        invoice this platform knows and it is imputed (RF-09); it names one
        nobody registered (RF-11); or it names several, or none at all, and a
        person distributes it (RF-12, RF-53).
        """
        if not row.references:
            return None, VOUCHER_WITHOUT_INVOICE
        if len(row.references) > 1:
            return None, VOUCHER_SEVERAL_INVOICES
        found = await self.purchases.invoices_numbered(row.references[0])
        if not found:
            return None, VOUCHER_UNKNOWN_INVOICE
        return found[0], None

    async def impute_held_payments_for(self, invoice: Invoice) -> int:
        """Impute the vouchers that were waiting for this invoice (RF-44 of 005).

        When an invoice the platform did not have is finally registered, the
        vouchers that named it stop being unknown. They are imputed and the fact
        is logged, so it is visible that they moved on their own.
        """
        imputed = 0
        moved: list[Payment] = []
        for payment in await self.purchases.pending_payments():
            if payment.review_reason != VOUCHER_UNKNOWN_INVOICE:
                continue
            if invoice.number not in (payment.reference or ""):
                continue
            payment.invoice_id = invoice.id
            payment.state = PaymentState.IMPUTED
            payment.review_reason = None
            moved.append(payment)
            imputed += 1
        if imputed:
            await self.session.flush()
            await self._announce_resolved(moved)
            logger.info(
                "Held vouchers imputed to a newly registered invoice",
                extra={"invoice_id": invoice.id, "payments": imputed},
            )
        return imputed

    async def register_payment(
        self,
        invoice_id: int,
        *,
        amount: Decimal,
        paid_on: date,
        reference: str | None,
        actor_user_id: int,
        confirm_over_balance: bool = False,
    ) -> PaymentRead:
        """Register a payment somebody made by hand (RF-18, RF-19, RF-21 of 005).

        A payment over the outstanding balance is refused **the first time** and
        accepted when the caller says they meant it: that is what "warn before
        registering" means over HTTP, and it keeps the warning from being a
        message nobody has to answer.
        """
        invoice = await self._require_invoice(invoice_id)
        already = await self.purchases.imputed_total_of(invoice_id)
        if amount > invoice.total - already and not confirm_over_balance:
            raise ConflictError(
                PAYMENT_OVER_BALANCE,
                details={
                    "invoice_id": invoice_id,
                    "balance": str(invoice.total - already),
                    "amount": str(amount),
                },
            )

        payment = await self.purchases.add_payment(
            Payment(
                supplier_id=invoice.supplier_id,
                invoice_id=invoice.id,
                amount=amount,
                paid_on=paid_on,
                origin=PaymentOrigin.MANUAL,
                state=PaymentState.IMPUTED,
                reference=reference,
                created_by_user_id=actor_user_id,
            )
        )
        await self.session.commit()
        logger.info(
            "Payment registered by hand",
            extra={"invoice_id": invoice_id, "payment_id": payment.id},
        )
        return PaymentRead.model_validate(payment)

    async def void_payment(self, payment_id: int, *, actor_user_id: int) -> PaymentRead:
        """Leave a payment somebody typed without effect (RF-22, RF-23 of 005).

        A voucher that came from the portal is refused: it is what the origin
        reported, and this platform does not get to erase somebody else's
        record. What it can do is hold it for review.
        """
        payment = await self.purchases.payment(payment_id)
        if payment is None:
            raise NotFoundError(NO_SUCH_PAYMENT, details={"payment_id": payment_id})
        if payment.origin is PaymentOrigin.PORTAL:
            raise ConflictError(PORTAL_PAYMENT_IS_NOT_UNDONE, details={"payment_id": payment_id})
        payment.state = PaymentState.VOIDED
        payment.voided_by_user_id = actor_user_id
        payment.voided_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.commit()
        return PaymentRead.model_validate(payment)

    async def pending_payments(self) -> list[PaymentRead]:
        """The vouchers waiting for somebody to say what they cover (RF-54)."""
        return [
            PaymentRead.model_validate(payment)
            for payment in await self.purchases.pending_payments()
        ]

    async def split_payment(
        self, payment_id: int, *, parts: list[tuple[int, Decimal]], actor_user_id: int
    ) -> list[PaymentRead]:
        """Distribute a held voucher between the invoices it covers (RF-53 of 005).

        The parts have to add up to the voucher **exactly** (RF-55): a
        distribution that does not add up is not a distribution, and letting it
        through would put a number in the debt that nobody can trace back to a
        payment. Until it is confirmed, nothing of the voucher is imputed
        (RF-54) — which is what the held state already is.
        """
        payment = await self.purchases.payment(payment_id)
        if payment is None:
            raise NotFoundError(NO_SUCH_PAYMENT, details={"payment_id": payment_id})
        if payment.state is not PaymentState.PENDING:
            raise ConflictError(
                "Ese comprobante ya está imputado", details={"payment_id": payment_id}
            )
        if sum((amount for _, amount in parts), Decimal(0)) != payment.amount:
            raise ValidationError(
                SPLIT_DOES_NOT_ADD_UP,
                details={"payment_id": payment_id, "amount": str(payment.amount)},
            )

        invoices = [await self._require_invoice(invoice_id) for invoice_id, _ in parts]
        await self._one_supplier_only(payment, invoices)

        created: list[Payment] = []
        for invoice, (_, amount) in zip(invoices, parts, strict=True):
            created.append(
                await self.purchases.add_payment(
                    Payment(
                        supplier_id=invoice.supplier_id or payment.supplier_id,
                        invoice_id=invoice.id,
                        amount=amount,
                        paid_on=payment.paid_on,
                        origin=payment.origin,
                        state=PaymentState.IMPUTED,
                        reference=payment.reference,
                        supplier_text=payment.supplier_text,
                        created_by_user_id=actor_user_id,
                    )
                )
            )
        # The voucher itself stops standing for money: its parts do. It is left
        # in place, voided, with who split it and when — nothing is deleted.
        payment.state = PaymentState.VOIDED
        payment.voided_by_user_id = actor_user_id
        payment.voided_at = datetime.now(UTC)
        payment.review_reason = None
        await self.session.flush()
        await self._announce_resolved([payment])
        await self.session.commit()
        logger.info("Voucher split", extra={"payment_id": payment_id, "parts": len(created)})
        return [PaymentRead.model_validate(item) for item in created]

    async def _announce_resolved(self, payments: Sequence[Payment]) -> None:
        """Say that a voucher that was waiting has been dealt with (RF-20 of 011).

        Announced and not called: `purchases` may not touch `triage`
        (Artículo IV), so this states a fact in public — identifiers and a
        label, never the record — and whoever cares listens. See
        `UNREADABLE_PAYMENT_ROW` for why nothing listening closes anything yet.

        A voucher somebody typed has no `staging_row_id` and is skipped: it came
        from a person, not from a reading, so there is no reading to declare
        resolved.
        """
        for payment in payments:
            if payment.staging_row_id is None:
                continue
            await events.publish(
                QuarantinedSourceResolved(
                    kind=UNREADABLE_PAYMENT_ROW,
                    key=str(payment.staging_row_id),
                    resolved_where=RESOLVED_IN_PAYMENTS,
                ),
                self.session,
            )

    async def _one_supplier_only(self, payment: Payment, invoices: list[Invoice]) -> None:
        """A voucher covers invoices of **one** supplier, and it is a signed assumption.

        The spec says it in as many words — *«se asume que un comprobante que
        cubre varias facturas cubre facturas de un mismo proveedor… si aparece
        uno que cruza dos proveedores, el sistema lo mantiene apartado y
        pregunta»* — and the split was letting anybody spread one voucher over
        two of them.

        That is not a tidiness rule. Money attributed to the wrong supplier
        wrongs both of them at once: one is owed less than the platform says and
        the other more, and the ageing and the average delay of the two are
        computed off those numbers. The voucher stays held, which is what "asks"
        means here.
        """
        suppliers = {invoice.supplier_id for invoice in invoices if invoice.supplier_id is not None}
        if len(suppliers) > 1:
            raise ValidationError(
                SPLIT_CROSSES_SUPPLIERS,
                details={"payment_id": payment.id, "suppliers": len(suppliers)},
            )
        if payment.supplier_id is not None and suppliers and payment.supplier_id not in suppliers:
            raise ValidationError(
                SPLIT_IS_ANOTHER_SUPPLIER,
                details={"payment_id": payment.id, "supplier_id": payment.supplier_id},
            )

    # --- The reception receipts and their incidents (005) ----------------

    async def issue_receipt(self, invoice_id: int, *, actor_user_id: int) -> ReceiptRead:
        """Issue the reception receipt of an invoice (RF-33, RF-36, RF-47, RF-48).

        Two refusals, and both are the spec's: an invoice already past its due
        date cannot have one issued (RF-34), and one that already has a receipt
        in force cannot have a second (RF-35). The number is this platform's
        own, correlative and unique — the portal does not number ours.
        """
        invoice = await self._require_invoice(invoice_id)
        # Uno del portal cuenta igual que uno nuestro: emitir un segundo sobre
        # una factura que ya tiene el suyo es duplicarlo, lo diga el registro
        # que lo diga (RF-30, RF-35).
        if await self.purchases.has_receipt(invoice_id):
            raise ConflictError(RECEIPT_ALREADY_ISSUED, details={"invoice_id": invoice_id})
        if invoice.due_on is not None and invoice.due_on < today_here():
            raise ConflictError(
                RECEIPT_TOO_LATE,
                details={"invoice_id": invoice_id, "due_on": invoice.due_on.isoformat()},
            )

        number = f"RC-{await self.purchases.next_receipt_number():06d}"
        receipt = await self.purchases.add_receipt(
            Receipt(
                invoice_id=invoice.id,
                number=number,
                issued_by_user_id=actor_user_id,
                issued_at=datetime.now(UTC),
                document=self._receipt_document(invoice, number),
            )
        )
        await events.publish(
            ReceiptIssued(
                receipt_id=receipt.id,
                invoice_id=invoice.id,
                number=number,
                issued_by_user_id=actor_user_id,
                issued_at=receipt.issued_at,
            ),
            self.session,
        )
        await self.session.commit()
        logger.info("Receipt issued", extra={"invoice_id": invoice_id, "number": number})
        return ReceiptRead.model_validate(receipt)

    def _receipt_document(self, invoice: Invoice, number: str) -> str:
        """The receipt a person downloads (RF-47).

        Plain text, in Spanish, because that is what it is: a statement that the
        invoice was received and will be paid. Turning it into a PDF is a
        presentation choice the browser can make later, and doing it here would
        put a rendering library between the record and the fact it records.
        """
        lines = [
            "RECIBO DE RECEPCIÓN",
            f"Número: {number}",
            f"Factura: {invoice.number}",
            f"Proveedor: {invoice.supplier_text}",
            f"Fecha de la factura: {invoice.issued_on:%d/%m/%Y}",
            f"Monto: ${invoice.total:,.2f}",
        ]
        if invoice.due_on is not None:
            lines.append(f"Vencimiento: {invoice.due_on:%d/%m/%Y}")
        lines.append("")
        lines.append(
            "Ferretería Industrial Cordillera SRL deja constancia de haber recibido la "
            "factura detallada, que será abonada según lo acordado."
        )
        return "\n".join(lines) + "\n"

    async def void_receipt(self, receipt_id: int, *, actor_user_id: int) -> ReceiptRead:
        """Annul a receipt, keeping who annulled it and when (RF-49 of 005).

        What happens next depends on the invoice and not on the receipt: one
        that has not fallen due can be issued another (RF-50); one that has
        becomes an incident, because it is now an overdue invoice with no
        receipt, which is exactly what RF-51 says.
        """
        receipt = await self.purchases.receipt(receipt_id)
        if receipt is None:
            raise NotFoundError("No encontramos ese recibo", details={"receipt_id": receipt_id})
        if not receipt.is_in_force:
            raise ConflictError(RECEIPT_ALREADY_VOIDED, details={"receipt_id": receipt_id})

        receipt.voided_by_user_id = actor_user_id
        receipt.voided_at = datetime.now(UTC)
        await self.session.flush()

        invoice = await self._require_invoice(receipt.invoice_id)
        if invoice.due_on is not None and invoice.due_on < today_here():
            await self.purchases.open_incident(invoice.id, today_here())

        await events.publish(
            ReceiptVoided(
                receipt_id=receipt.id, invoice_id=invoice.id, voided_by_user_id=actor_user_id
            ),
            self.session,
        )
        await self.session.commit()
        logger.info("Receipt voided", extra={"receipt_id": receipt_id})
        return ReceiptRead.model_validate(receipt)

    async def get_receipt(self, invoice_id: int) -> ReceiptRead:
        """The receipt in force of an invoice (RF-29, RF-47)."""
        receipt = await self.purchases.receipt_of(invoice_id)
        if receipt is None:
            raise NotFoundError(
                "La factura no tiene recibo emitido", details={"invoice_id": invoice_id}
            )
        return ReceiptRead.model_validate(receipt)

    async def open_incidents_for_overdue(self) -> int:
        """Flag every overdue invoice with no receipt as an incident (RF-37).

        Idempotent: an invoice that already has an open incident does not get a
        second one, and that is decided by the partial unique index rather than
        by this loop remembering to check.
        """
        opened = 0
        today = today_here()
        for invoice in await self.purchases.overdue_without_receipt(today):
            if await self.purchases.open_incident(invoice.id, today) is not None:
                opened += 1
        if opened:
            await self.session.commit()
            logger.info("Receipt incidents opened", extra={"incidents": opened})
        return opened

    async def list_incidents(self, *, only_open: bool = True) -> list[IncidentRead]:
        """The incidents, the pending ones by default (RF-37, RF-59)."""
        incidents = await self.purchases.incidents(only_open=only_open)
        names = {supplier.id: supplier.legal_name for supplier in await self.purchases.suppliers()}
        items: list[IncidentRead] = []
        for incident in incidents:
            invoice = await self.purchases.invoice(incident.invoice_id)
            read = IncidentRead.model_validate(incident)
            read.invoice_number = invoice.number if invoice else None
            read.supplier_name = names.get(invoice.supplier_id or 0) if invoice else None
            items.append(read)
        return items

    async def close_incident(
        self, incident_id: int, *, resolution: str, actor_user_id: int
    ) -> IncidentRead:
        """Close an incident with what was done about it (RF-57, RF-58, RF-59)."""
        incident = await self.purchases.incident(incident_id)
        if incident is None:
            raise NotFoundError(NO_SUCH_INCIDENT, details={"incident_id": incident_id})
        if incident.closed_at is not None:
            raise ConflictError(
                "El incidente ya está cerrado", details={"incident_id": incident_id}
            )
        incident.closed_by_user_id = actor_user_id
        incident.closed_at = datetime.now(UTC)
        incident.resolution = resolution
        await self.session.flush()
        await self.session.commit()
        return IncidentRead.model_validate(incident)

    async def invoices_due_soon(self) -> list[tuple[Invoice, int]]:
        """The invoices with no receipt that are about to fall due (RF-38 of 005).

        The window is the parameter the owner sets, three days while nobody has
        set another (RF-41, RF-52). An invoice that already has its receipt is
        not announced at all (RF-40): the alert is about the receipt, not about
        the money.
        """
        days = int(await self._setting(RECEIPT_NOTICE_KEY))
        today = today_here()
        receipts = await self.purchases.invoices_with_receipt()
        due = await self.purchases.due_between(today, today + timedelta(days=days))
        return [
            (invoice, (invoice.due_on - today).days)
            for invoice in due
            if invoice.id not in receipts and invoice.due_on is not None
        ]

    # --- The calendar of due dates (006) ---------------------------------

    async def _sync_due_date(self, invoice: Invoice) -> None:
        """Keep the calendar entry of an invoice in step with the invoice.

        An invoice puts itself on the calendar, and it stays there: RF-18 of 006
        forbids removing an entry that comes from an invoice, because the
        invoice exists and so does the day it is due.
        """
        if invoice.due_on is None:
            return
        entry = await self.purchases.due_date_of_invoice(invoice.id)
        description = f"Factura {invoice.number} — {invoice.supplier_text}"
        if entry is None:
            await self.purchases.add_due_date(
                DueDate(
                    on_date=invoice.due_on,
                    original_date=invoice.due_on,
                    description=description,
                    amount=invoice.total,
                    invoice_id=invoice.id,
                    origin=DueDateOrigin.INVOICE,
                )
            )
            return
        # Only while nobody has moved it by hand: a date a person rescheduled is
        # a decision, and the next reading of the portal does not get to undo it.
        if not entry.was_rescheduled:
            entry.on_date = invoice.due_on
            entry.original_date = invoice.due_on
        entry.description = description
        entry.amount = invoice.total
        await self.session.flush()

    async def calendar(self, *, since: date, until: date, **filters: bool) -> CalendarRead:
        """One window of the calendar, with everything a day shows (RF-01 to RF-11).

        The two filters of the spec are here: only what has no receipt (RF-10),
        and hiding what is already settled (RF-40 of 006). Both are applied over
        the computed state, never over a stored one.
        """
        entries = await self.purchases.due_dates_between(since, until)
        # Las facturas **de estas entradas**, y no las que vencen en la ventana:
        # una factura vencida que alguien reprogramó a otro mes tiene la tarjeta
        # acá y su `due_on` allá, y buscarla por fecha la devolvía sin proveedor,
        # sin estado de pago y sin la marca de vencida sin recibo — que es justo
        # lo contrario de lo que RF-30 promete que se sigue viendo.
        invoices = {
            invoice.id: invoice
            for invoice in await self.purchases.invoices_by_ids(
                [entry.invoice_id for entry in entries if entry.invoice_id is not None]
            )
        }
        read = {
            item.id: item
            for item in await self._read_invoices([invoice for invoice in invoices.values()])
        }
        names = {supplier.id: supplier.legal_name for supplier in await self.purchases.suppliers()}
        today = today_here()

        items: list[DueDateRead] = []
        for entry in entries:
            item = DueDateRead.model_validate(entry)
            item.was_rescheduled = entry.was_rescheduled
            item.is_past = entry.on_date < today
            invoice = invoices.get(entry.invoice_id or 0)
            if invoice is not None:
                detail = read.get(invoice.id)
                item.supplier_name = names.get(invoice.supplier_id or 0)
                item.receipt_issued = bool(detail and detail.receipt_issued)
                item.is_overdue_without_receipt = bool(detail and detail.is_overdue_without_receipt)
                item.payment_state = detail.payment_state if detail else None
            if entry.was_rescheduled:
                item.changes = [
                    DueDateChangeRead.model_validate(change)
                    for change in await self.purchases.changes_of(entry.id)
                ]
            items.append(item)

        if filters.get("without_receipt"):
            items = [item for item in items if not item.receipt_issued]
        if filters.get("hide_settled"):
            items = [item for item in items if item.payment_state != SETTLED]
        return CalendarRead(since=since, until=until, items=items)

    async def add_due_date(
        self,
        *,
        on_date: date,
        description: str,
        amount: Decimal | None,
        actor_user_id: int,
        actor_name: str = "",
    ) -> DueDateRead:
        """Add an entry to the calendar by hand (RF-12, RF-13, RF-14 of 006)."""
        entry = await self.purchases.add_due_date(
            DueDate(
                on_date=on_date,
                original_date=on_date,
                description=description,
                amount=amount,
                origin=DueDateOrigin.MANUAL,
                created_by_user_id=actor_user_id,
            )
        )
        await self._announce(
            entry, action="added", actor_user_id=actor_user_id, actor_name=actor_name
        )
        await self.session.commit()
        logger.info("Due date added", extra={"due_date_id": entry.id})
        return DueDateRead.model_validate(entry)

    async def edit_due_date(
        self,
        due_date_id: int,
        *,
        description: str | None,
        amount: Decimal | None,
        actor_user_id: int,
        actor_name: str = "",
    ) -> DueDateRead:
        """Correct a hand-made entry, keeping what it said before (RF-15, RF-16)."""
        entry = await self._require_due_date(due_date_id)
        self._only_manual(entry)
        # RF-16 pide quién, cuándo y **el valor anterior**, y lo tercero es lo
        # que obliga a mirar antes de escribir. Va a la bitácora de la
        # plataforma por el mismo evento que usa la corrección de un proveedor:
        # este módulo no sabe que existe una bitácora, sólo dice qué cambió.
        changes: list[tuple[str, object, object]] = []
        if description is not None and description != entry.description:
            changes.append(("description", entry.description, description))
            entry.description = description
        if amount is not None and amount != entry.amount:
            changes.append(("amount", entry.amount, amount))
            entry.amount = amount
        for field, previous, value in changes:
            await events.publish(
                ManualChangeRecorded(
                    entity_type=DUE_DATE_ENTITY,
                    entity_id=str(entry.id),
                    action=AuditAction.CORRECTED,
                    actor_user_id=actor_user_id,
                    section=PURCHASING_SECTION,
                    field=field,
                    old_value=str(previous) if previous is not None else None,
                    new_value=str(value),
                ),
                self.session,
            )
        await self.session.flush()
        await self._announce(
            entry, action="edited", actor_user_id=actor_user_id, actor_name=actor_name
        )
        await self.session.commit()
        return DueDateRead.model_validate(entry)

    async def move_due_date(
        self,
        due_date_id: int,
        *,
        on_date: date,
        reason: str | None,
        actor_user_id: int,
        actor_name: str = "",
        confirm_past: bool = False,
    ) -> DueDateRead:
        """Move an entry to another date, keeping where it was (RF-19 to RF-30).

        Three things follow from a move, and the difference between them is the
        subtle part of 006:

        * the previous date is kept and the move is recorded with who made it
          and whatever reason was written (RF-20, RF-21, RF-22, RF-23);
        * moving an invoice that **has not fallen due** moves its deadline to
          issue the receipt with it, and its supplier's delay is measured
          against the new date (RF-26, RF-27);
        * moving one that **has** fallen due changes none of that: the receipt
          stays refused, the delay is still measured against the original date,
          and it is still flagged as overdue without a receipt (RF-28 to RF-30).
        """
        entry = await self._require_due_date(due_date_id)
        today = today_here()
        if on_date < today and not confirm_past:
            raise ConflictError(
                MOVING_INTO_THE_PAST,
                details={
                    "code": MOVING_INTO_THE_PAST_CODE,
                    "due_date_id": due_date_id,
                    "on_date": str(on_date),
                },
            )

        previous = entry.on_date
        entry.on_date = on_date
        await self.purchases.add_due_date_change(
            DueDateChange(
                due_date_id=entry.id,
                previous_date=previous,
                new_date=on_date,
                reason=reason,
                actor_user_id=actor_user_id,
            )
        )

        rescheduled = None
        if entry.invoice_id is not None:
            invoice = await self._require_invoice(entry.invoice_id)
            was_overdue = invoice.due_on is not None and invoice.due_on < today
            if not was_overdue:
                invoice.due_on = on_date
            rescheduled = InvoiceDueDateRescheduled(
                invoice_id=invoice.id,
                previous_due_on=previous,
                due_on=on_date,
                was_overdue=was_overdue,
                actor_user_id=actor_user_id,
            )
        await self.session.flush()

        await events.publish(
            DueDateChanged(
                due_date_id=entry.id,
                action="moved",
                actor_user_id=actor_user_id,
                actor_name=actor_name,
                on_date=on_date,
                previous_date=previous,
                invoice_id=entry.invoice_id,
                reason=reason,
            ),
            self.session,
        )
        if rescheduled is not None:
            await events.publish(rescheduled, self.session)
        await self.session.commit()
        logger.info(
            "Due date moved",
            extra={"due_date_id": due_date_id, "from": str(previous), "to": str(on_date)},
        )
        return DueDateRead.model_validate(entry)

    async def remove_due_date(
        self, due_date_id: int, *, actor_user_id: int, actor_name: str = ""
    ) -> None:
        """Remove a hand-made entry (RF-17). One from an invoice is refused (RF-18)."""
        entry = await self._require_due_date(due_date_id)
        self._only_manual(entry)
        on_date, invoice_id = entry.on_date, entry.invoice_id
        await self.purchases.drop_due_date(entry)
        await events.publish(
            DueDateChanged(
                due_date_id=due_date_id,
                action="removed",
                actor_user_id=actor_user_id,
                # Iba vacío aunque la ruta tenía el nombre a mano, y con el
                # nombre vacío RF-33 no se puede cumplir para este verbo: la
                # otra pantalla diría «alguien borró esto».
                actor_name=actor_name,
                on_date=on_date,
                invoice_id=invoice_id,
            ),
            self.session,
        )
        await self.session.commit()

    async def _announce(
        self, entry: DueDate, *, action: str, actor_user_id: int, actor_name: str
    ) -> None:
        """Tell the other screens that the calendar moved under them (RF-31).

        One publisher for the four verbs. Two of them — adding and correcting —
        did not announce anything at all, so a live channel built on top of this
        event would have carried half the changes and looked like a bug in the
        channel.
        """
        await events.publish(
            DueDateChanged(
                due_date_id=entry.id,
                action=action,
                actor_user_id=actor_user_id,
                actor_name=actor_name,
                on_date=entry.on_date,
                invoice_id=entry.invoice_id,
            ),
            self.session,
        )

    @staticmethod
    def _only_manual(entry: DueDate) -> None:
        """Refuse to touch what an invoice put on the calendar (RF-18 of 006)."""
        if entry.origin is DueDateOrigin.INVOICE:
            raise ConflictError(
                INVOICE_FROM_A_LIST_IS_NOT_REMOVED, details={"due_date_id": entry.id}
            )

    async def _require_due_date(self, due_date_id: int) -> DueDate:
        """Return the entry, or say plainly that it is not there."""
        entry = await self.purchases.due_date(due_date_id)
        if entry is None:
            raise NotFoundError(NO_SUCH_DUE_DATE, details={"due_date_id": due_date_id})
        return entry

    # --- The purchase orders (007) ---------------------------------------

    async def register_orders(
        self, *, batch_id: int, orders: tuple[NormalizedPurchaseOrder, ...]
    ) -> None:
        """Bring a batch of purchase orders in, and watch them from here on.

        Two things this module knows that the portal does not say. **Since when
        an order has been where it is**: the portal publishes one date, the
        order's, so time in a state is counted from the moment this platform
        first saw it there (RF-05, RF-48). And **whether an order repeats an
        earlier one**: the same product to the same supplier inside the
        configured window is flagged, and the flag never blocks the order from
        being registered (RF-15, RF-16, RF-20).
        """
        today = today_here()
        window = int(await self._setting(REPEAT_WINDOW_KEY))
        held = 0

        for row in orders:
            # The reason is **kept**. It used to be thrown away here, and RF-55
            # asks for exactly the half that was being lost: «this supplier is
            # not in the register» is a different answer from «this name does
            # not disambiguate», and only the first one means nobody may resolve
            # the order by picking from the eight.
            supplier, reason = await self.resolve_supplier(row.supplier_text)
            existing = await self.purchases.order_numbered(row.number)
            if existing is not None:
                # Una orden que escribió una persona y que el portal por fin
                # publica: si no dicen lo mismo, no se pisa ninguna de las dos.
                # El **estado** se actualiza igual, porque el estado es un hecho
                # del portal y no está en discusión.
                if existing.origin is RecordOrigin.MANUAL:
                    published = {
                        "fecha": row.ordered_on.isoformat(),
                        "importe": _money_text(row.amount),
                    }
                    differs = existing.ordered_on != row.ordered_on or existing.amount != row.amount
                    if differs and existing.rejected_portal_values != published:
                        await self._dispute_order(existing, published)
                # El estado se actualiza igual: es un hecho del portal, y no es
                # lo que está en discusión.
                if existing.status_text != row.status_text:
                    # Seen somewhere else than last time: the clock of RF-05
                    # restarts, and an order that advanced stops being stalled
                    # without anybody clearing a flag (RF-14).
                    existing.status_text = row.status_text
                    existing.status_since = today
                    await self.session.flush()
                continue

            earlier = await self.purchases.earlier_order_for(
                supplier_id=supplier.id if supplier else None,
                product_code=row.product_code,
                since=row.ordered_on - timedelta(days=window),
                before=row.ordered_on,
            )
            order = await self.purchases.add_order(
                PurchaseOrder(
                    number=row.number,
                    ordered_on=row.ordered_on,
                    supplier_id=supplier.id if supplier else None,
                    supplier_text=row.supplier_text,
                    product_code=row.product_code,
                    product_text=row.product_text,
                    quantity=row.quantity,
                    amount=row.amount,
                    status_text=row.status_text,
                    status_since=today,
                    # An order the platform meets already in flight cannot be
                    # timed in its state: what can be said about it is how long
                    # ago it was placed, and it is said as that (RF-49).
                    observed_from_start=row.ordered_on >= today,
                    review_state=(
                        OrderReviewState.OK if supplier is not None else OrderReviewState.PENDING
                    ),
                    review_reason=None if supplier is not None else reason,
                    repeat_of_order_id=earlier.id if earlier else None,
                )
            )
            held += int(order.review_state is OrderReviewState.PENDING)

        logger.info(
            "Purchase orders registered",
            extra={"batch_id": batch_id, "orders": len(orders), "held": held},
        )

    async def list_orders(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        status_text: str | None = None,
        supplier_id: int | None = None,
        only_stalled: bool = False,
        only_in_review: bool = False,
        order_id: int | None = None,
    ) -> PurchaseOrderList:
        """The orders screen, with its counts, its stalled and its held ones.

        RF-02 to RF-13, plus RF-51 and RF-52: how many are set aside for review,
        and being able to ask for only those. `held` is counted over **all** the
        orders and not over the page, like `per_status`: they are the links the
        screen navigates by, and a count that changes when you filter is a count
        you cannot navigate by.
        """
        orders = await self.purchases.orders(
            skip=skip, limit=limit, status_text=status_text, supplier_id=supplier_id
        )
        if order_id is not None:
            orders = [order for order in orders if order.id == order_id] or (
                [found] if (found := await self.purchases.order(order_id)) else []
            )
        per_status = await self.purchases.orders_per_status()
        limit_days = int(await self._setting(STALLED_DAYS_KEY))
        names = {supplier.id: supplier.legal_name for supplier in await self.purchases.suppliers()}
        today = today_here()

        items: list[PurchaseOrderRead] = []
        for order in orders:
            read = PurchaseOrderRead.model_validate(order)
            read.supplier_name = names.get(order.supplier_id or 0)
            read.days_in_status = (today - order.status_since).days
            read.days_since_ordered = (today - order.ordered_on).days
            read.is_stalled = self._is_stalled(order, read.days_in_status, limit_days)
            if order.repeat_of_order_id is not None:
                earlier = await self.purchases.order(order.repeat_of_order_id)
                read.repeat_of_number = earlier.number if earlier else None
            items.append(read)

        stalled = [item for item in items if item.is_stalled]
        if only_stalled:
            items = stalled
        if only_in_review:
            items = [item for item in items if item.review_state is OrderReviewState.PENDING]
        return PurchaseOrderList(
            items=items,
            total=len(items),
            per_status=per_status,
            stalled=len(stalled),
            held=await self.purchases.count_orders_in_review(),
        )

    @staticmethod
    def _is_stalled(order: PurchaseOrder, days_in_status: int, limit_days: int) -> bool:
        """Whether an order has sat too long somewhere short of arriving (RF-10).

        A received order is finished: however long it sat before, it is not
        waiting for anybody now.
        """
        if order.status_text == RECEIVED_STATUS:
            return False
        return days_in_status > limit_days

    async def stalled_orders(self) -> list[PurchaseOrderRead]:
        """The orders that have sat too long, for the daily digest (RF-35 of 007)."""
        listing = await self.list_orders(limit=100_000, only_stalled=True)
        return listing.items

    async def dismiss_repeat(self, order_id: int, *, actor_user_id: int) -> PurchaseOrderRead:
        """Drop the repeated-order flag, recording who did it (RF-18, RF-19)."""
        order = await self.purchases.order(order_id)
        if order is None:
            raise NotFoundError(NO_SUCH_ORDER, details={"order_id": order_id})
        order.repeat_of_order_id = None
        order.repeat_dismissed_by_user_id = actor_user_id
        order.repeat_dismissed_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.commit()
        return PurchaseOrderRead.model_validate(order)

    # --- Deciding about an order held for review (007, H8) ---------------
    #
    # Calcado del molde que ya resuelve una factura apartada, doscientas líneas
    # más arriba, porque la spec dice que es el mismo criterio y porque lo es.
    # La única diferencia sin análogo es RF-60: al asignarle el proveedor hay
    # que **volver a evaluar** si repite un pedido anterior, que es lo que
    # RF-59 dejó sin hacer mientras no se supiera de quién era la orden.

    async def orders_in_review(self) -> list[PurchaseOrderRead]:
        """The orders waiting for a person to say whose they are (RF-52)."""
        listing = await self.list_orders(limit=100_000, only_in_review=True)
        return listing.items

    async def resolve_order(
        self, order_id: int, *, supplier_id: int, remember: bool, actor_user_id: int
    ) -> PurchaseOrderRead:
        """Say which supplier an order is from, and everything that follows.

        Asking to remember it turns the spelling into a rule, and **every other
        order and invoice written the same way is resolved with it** (RF-61,
        RF-62). That is not an extra: the survey measured twenty different
        spellings in the purchase orders alone, and deciding each of them once
        per document is the queue a team of three abandons.
        """
        order = await self.purchases.order(order_id)
        if order is None:
            raise NotFoundError(NO_SUCH_ORDER, details={"order_id": order_id})
        if order.review_state is not OrderReviewState.PENDING:
            raise ConflictError(ORDER_NOT_HELD, details={"order_id": order_id})

        supplier = await self._require_supplier(supplier_id)
        alias_id: int | None = None
        if remember:
            alias = await self.purchases.put_alias(
                text_normalized=normalize_entity_name(order.supplier_text),
                text_original=order.supplier_text,
                supplier_id=supplier.id,
                source=SupplierAliasSource.LEARNED,
                created_by_user_id=actor_user_id,
            )
            alias_id = alias.id

        await self._attach_order(order, supplier, actor_user_id=actor_user_id)
        if remember:
            await self._apply_alias(
                normalize_entity_name(order.supplier_text),
                supplier=supplier,
                alias_id=alias_id,
                actor_user_id=actor_user_id,
            )
        await self.session.commit()
        logger.info(
            "Purchase order resolved", extra={"order_id": order_id, "supplier_id": supplier.id}
        )
        return (await self.list_orders(limit=1, order_id=order_id)).items[0]

    async def _attach_order(
        self, order: PurchaseOrder, supplier: Supplier, *, actor_user_id: int
    ) -> None:
        """Give a held order its supplier, and re-check whether it repeats one.

        **RF-60 lives in the last two lines**, and it is the only thing this
        method does that resolving an invoice does not. While nobody knew whose
        the order was there was nothing to compare it against (RF-59); now there
        is, and the comparison happens once rather than never.
        """
        order.supplier_id = supplier.id
        order.review_state = OrderReviewState.RESOLVED
        order.review_reason = None
        order.resolved_by_user_id = actor_user_id
        order.resolved_at = datetime.now(UTC)

        window = int(await self._setting(REPEAT_WINDOW_KEY))
        earlier = await self.purchases.earlier_order_for(
            supplier_id=supplier.id,
            product_code=order.product_code,
            since=order.ordered_on - timedelta(days=window),
            before=order.ordered_on,
        )
        # Never itself: `earlier_order_for` looks at the same table, and an
        # order resolved on its own ordering day would otherwise repeat itself.
        if earlier is not None and earlier.id != order.id:
            order.repeat_of_order_id = earlier.id
        await self.session.flush()

    # --- Correcting a value by hand (004) --------------------------------

    async def correct_supplier(
        self,
        supplier_id: int,
        *,
        values: dict[str, Any],
        reason_code: str,
        reason_detail: str | None,
        actor_user_id: int,
    ) -> SupplierRead:
        """Correct the contact details of a supplier (RF-16 to RF-19 of 004).

        What the portal had said is kept, so the correction can be undone and so
        a later reading that contradicts it is a **conflict** rather than an
        overwrite — the mechanism 003 already built, reused here rather than
        rebuilt: `ManualChangeRecorded` puts it in the one log of the platform,
        and this module never learns that a log exists.
        """
        supplier = await self._require_supplier(supplier_id)
        now = datetime.now(UTC)
        changed: list[str] = []
        for field, value in values.items():
            if value is None:
                continue
            standing = await self.purchases.correction_in_force(
                entity_type=SUPPLIER_ENTITY, entity_id=str(supplier.id), field=field
            )
            previous = getattr(supplier, field)
            # Nothing to do only when there is nothing to change **and** nothing
            # standing: re-affirming the value already in force is how somebody
            # closes a conflict the register opened (RF-19), and it has to reach
            # the correction row even though the card does not move.
            if previous == value and standing is None:
                continue
            if standing is None:
                await self.purchases.add_correction(
                    PurchaseCorrection(
                        entity_type=SUPPLIER_ENTITY,
                        entity_id=str(supplier.id),
                        field=field,
                        portal_value=previous,
                        corrected_value=value,
                        reason_code=reason_code,
                        reason_detail=reason_detail,
                        corrected_by_user_id=actor_user_id,
                        corrected_at=now,
                    )
                )
            else:
                # A second correction over the same field rewrites what a person
                # left and clears the conflict — but never `portal_value`, which
                # is what the register said and what a reversal restores. Two
                # corrections in a row still give back the register's value and
                # not the previous person's.
                standing.corrected_value = value
                standing.reason_code = reason_code
                standing.reason_detail = reason_detail
                standing.corrected_by_user_id = actor_user_id
                standing.corrected_at = now
                standing.status = CorrectionStatus.ACTIVE
                standing.conflict_value = None
                standing.conflict_detected_at = None
            setattr(supplier, field, value)
            changed.append(field)
            await events.publish(
                ManualChangeRecorded(
                    entity_type=SUPPLIER_ENTITY,
                    entity_id=str(supplier.id),
                    action=AuditAction.CORRECTED,
                    actor_user_id=actor_user_id,
                    section=PURCHASING_SECTION,
                    field=field,
                    old_value=previous,
                    new_value=value,
                    reason_code=reason_code,
                    reason_detail=reason_detail,
                ),
                self.session,
            )
        await self.session.flush()
        # Corregir el plazo a mano mueve el vencimiento de sus facturas por el
        # mismo motivo que lo mueve leerlo del padrón: de ahí sale (RF-26).
        if "payment_term_days" in changed:
            await self._refresh_due_dates(supplier)
        await self.session.commit()
        logger.info("Supplier corrected", extra={"supplier_id": supplier_id, "fields": changed})
        return await self.get_supplier(supplier_id)
