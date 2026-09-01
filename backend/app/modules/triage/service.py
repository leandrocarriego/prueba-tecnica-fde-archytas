"""Triage business logic: keep what could not be resolved, and learn from it.

Two ideas hold this module together, and both are Artículo II:

* **A case is not an error.** It is work waiting for a person, counted and
  visible, and the run it came from finished fine without it.
* **A decision is taken once.** What a person decides becomes a rule, and the
  rule is what stops the system from asking the same question tomorrow.
"""

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.modules.triage.models import CaseStatus, ExceptionCase
from app.modules.triage.repository import TriageRepository
from app.modules.triage.schemas import CaseList, CaseRead, RuleRead
from app.shared.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.shared.events import (
    QuarantineCaseResolved,
    QuarantineRuleRedecided,
    QuarantineRuleRevoked,
    events,
)
from app.shared.parameters import initial_value
from app.shared.sections import BusinessSection
from app.shared.time import start_of_business_day

logger = get_logger(__name__)

# The four kinds of case this feature opens. Strings, not an enum shared with
# anybody: the queue is generic and the next problem will add its own.
UNREADABLE_ROW = "unreadable_row"
UNKNOWN_PRODUCT = "unknown_product"
MISSING_PRODUCT = "missing_product"
UNREADABLE_HISTORY = "unreadable_history"
# The kind 008 adds. The queue did not have to change to take it: that is the
# point of a generic queue with learned rules.
UNKNOWN_CATEGORY = "unknown_category"
# The kind 004 adds: a row of the invoices screen that could not be typed. It
# went to quarantine in `staging` and nowhere else for a year of commits —
# nobody was subscribed to the event that announced it — so it was not counted,
# not shown and never decided, which is the one thing the Artículo II forbids.
UNREADABLE_INVOICE_ROW = "unreadable_invoice_row"
# The kind 007 adds, and it is the same silence as the one above on the other
# screen: a row of the purchase orders that could not be typed was quarantined
# in `staging` and announced to nobody. An order that never arrives is exactly
# the problem the feature exists to solve, so losing one without a trace is the
# worst place for the Artículo II to be half-applied.
UNREADABLE_ORDER_ROW = "unreadable_order_row"

# The four kinds 011 adds, and they all say the same thing: `ingestion` was
# already setting these rows aside in `staging` and announcing it to nobody, so
# they were held, not counted, not shown and never decided. A datum set aside
# in silence is a datum discarded with extra steps (Artículo II), and closing
# those four silences is the whole of that feature.
UNREADABLE_SUPPLIER_ROW = "unreadable_supplier_row"
UNREADABLE_PAYMENT_ROW = "unreadable_payment_row"
UNREADABLE_MESSAGE_ROW = "unreadable_message_row"
UNREADABLE_SALE_ROW = "unreadable_sale_row"

# Las dos clases que abre la **carga manual**, y que no existían mientras la
# única salida de una fila ilegible era darla por revisada: una persona
# reconstruye la factura o la orden que el portal publicó rota, y meses después
# el portal la publica de nuevo, ya legible y distinta.
#
# Ninguno de los dos gana solo. Pisar lo cargado a mano tira trabajo hecho sin
# avisar; dejarlo ganar deja la plataforma discrepando del origen sin que nadie
# se entere. Así que el registro queda apartado —fuera de todos los totales,
# como cualquier dato dudoso— y la diferencia se pregunta con los dos valores al
# lado. Es la decisión del dueño del 2026-09-01.
DISPUTED_INVOICE = "disputed_invoice"
DISPUTED_ORDER = "disputed_order"

# Where each of the four came from, in the words of the portal screen a person
# would go looking at (RF-11). Spanish, because the screen shows it.
SUPPLIER_ORIGIN = "padrón de proveedores"
PAYMENT_ORIGIN = "comprobantes de pago"
MESSAGE_ORIGIN = "buzón"
SALE_ORIGIN = "ventas"
# Y las de todo lo que ya abría caso antes de la 011 y no decía de dónde salía.
# RF-11 dice «para **cada** pendiente», y hasta acá lo cumplían cinco de once:
# quien miraba la lista tenía que saber de antemano cuáles lo traían, que es
# justo el trabajo que el requisito existe para ahorrarle.
ORDER_ORIGIN = "órdenes de compra"
PRICE_LIST_ORIGIN = "lista de precios"
HISTORY_ORIGIN = "historial del producto"
INVOICE_ORIGIN = "facturas"

# What the person reads in the review screen (RF-26), in Spanish like every
# other user-facing string.
UNKNOWN_PRODUCT_REASON = "El producto no está entre los conocidos"
MISSING_PRODUCT_REASON = "El producto dejó de figurar en la lista"
UNKNOWN_CATEGORY_REASON = "No sabemos a qué rubro corresponde esta forma escrita"
DISPUTED_ENTRY_REASON = "La cargó una persona y el portal la publicó distinta"

ALREADY_RESOLVED = "This case has already been resolved"
NOT_YOUR_SECTION = "No tenés permiso para resolver un pendiente de esta área"

# The parameter that says when a pending case has been waiting too long
# (RF-17). Read through this module's own projection, like every other module
# reads the ones it consumes.
STALE_DAYS_KEY = "triage.stale_days"

# How a case closed by the screen that owned the work is recorded (RF-21). No
# name of a person goes in it, and that is the decision the spec took: whoever
# did the work is recorded where the work happened, and a second copy of that
# fact here could only ever drift from the first.
RESOLVED_ELSEWHERE = "resolved_elsewhere"
ALREADY_REVOKED = "This rule is already revoked"


def fingerprint_of(kind: str, key: str) -> str:
    """What makes two cases the same case.

    It is a hash of the kind plus whatever identifies the case in its domain —
    the product code, the product id — so the database can hold "one pending
    case" without this module explaining itself to it.
    """
    return sha256(f"{kind}|{key}".encode()).hexdigest()


class TriageService:
    """Opens cases, resolves them, and keeps the rules that come out of them."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.triage = TriageRepository(session)

    # --- Opening cases ----------------------------------------------------

    async def open_case(
        self,
        *,
        kind: str,
        reason: str,
        payload: dict[str, Any],
        key: str,
        section: BusinessSection,
        batch_id: int | None = None,
    ) -> None:
        """Put one thing in front of a person, once.

        `section` has no default on purpose. It says who this case is for, and
        the only moment anybody knows that is now, while the publisher is still
        in the room: a default here would quietly file the next kind somebody
        adds under one area and show it to the wrong person, with nothing
        failing (RF-12).
        """
        await self.triage.open_case(
            kind=kind,
            reason=reason,
            payload=payload,
            fingerprint=fingerprint_of(kind, key),
            batch_id=batch_id,
            section=section,
        )

    # --- Reading ----------------------------------------------------------

    async def list_cases(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        status: CaseStatus | None = CaseStatus.PENDING,
        kind: str | None = None,
        batch_id: int | None = None,
        visible: frozenset[BusinessSection],
        section: BusinessSection | None = None,
    ) -> CaseList:
        """The review screen: what was set aside and why (RF-26, RF-27).

        `visible` is the areas this person reaches, and everything below is
        narrowed to them (RF-12, RF-14). It is keyword-only and has **no
        default** on purpose: a default of "every area" would turn the next
        caller that forgets it into a leak of purchasing's money to whoever
        reads sales, and it would do it silently.

        `section` on top of that is the person **choosing** to see less
        (RF-22). Asking for an area they do not reach is refused rather than
        quietly emptied: an empty list reads as «no hay nada ahí», which is a
        different answer and an untrue one.
        """
        if section is not None and section not in visible:
            raise PermissionDeniedError(NOT_YOUR_SECTION, details={"section": section.value})
        sections = frozenset({section}) if section is not None else visible

        cases = await self.triage.list_cases(
            skip=skip, limit=limit, status=status, kind=kind, batch_id=batch_id, sections=sections
        )
        total = await self.triage.count_cases(
            status=status, kind=kind, batch_id=batch_id, sections=sections
        )
        # The header counts what is pending regardless of the `status` being
        # browsed: somebody reading the resolved ones still wants to know how
        # many are waiting (RF-15).
        pending_total = await self.triage.count_cases(status=CaseStatus.PENDING, sections=sections)
        oldest_at = await self.triage.oldest_pending_at(sections=sections)
        # And what left the queue today, which is the half of the header that
        # says the list moves. The day is the shop's, never UTC's.
        resolved_today = await self.triage.count_resolved_since(
            since=start_of_business_day(), sections=sections
        )

        stale_days = int(await self._setting(STALE_DAYS_KEY))
        now = datetime.now(UTC)
        return CaseList(
            items=[self._read(case, now=now, stale_days=stale_days) for case in cases],
            total=total,
            skip=skip,
            limit=limit,
            pending_total=pending_total,
            oldest_at=oldest_at,
            resolved_today=resolved_today,
            sections=sorted(visible),
        )

    @staticmethod
    def _read(case: ExceptionCase, *, now: datetime, stale_days: int) -> CaseRead:
        """A case with how long it has been waiting worked out (RF-16, RF-17).

        A resolved case is never stale: it stopped waiting the day somebody —
        or the screen that owned the work — decided about it, so what it shows
        is how long it waited, not how long it has been ignored.
        """
        waiting_days = max((now - case.created_at).days, 0)
        read = CaseRead.model_validate(case)
        read.waiting_days = waiting_days
        read.is_stale = case.status is CaseStatus.PENDING and waiting_days > stale_days
        return read

    async def _setting(self, key: str) -> Any:
        """A business parameter, from this module's projection or its initial value."""
        stored = await self.triage.setting(key)
        return initial_value(key) if stored is None else stored

    async def remember_setting(self, key: str, value: Any) -> None:
        """Keep a business parameter this module reads."""
        await self.triage.put_setting(key, value)

    async def count_pending(self, *, batch_id: int | None = None) -> int:
        """How many cases are waiting for somebody."""
        return await self.triage.count_cases(status=CaseStatus.PENDING, batch_id=batch_id)

    async def list_rules(
        self, *, include_revoked: bool = False, kind: str | None = None
    ) -> list[RuleRead]:
        """The decisions being applied on their own, with who took them (RF-36).

        `kind` narrows the list to one family of decision. It exists because
        the queue stopped being about one problem: the equivalences screen of
        008 wants its own, and reading the whole list to filter it in the
        browser would send the seeded table down the wire on every visit.
        """
        return [
            RuleRead.model_validate(rule)
            for rule in await self.triage.list_rules(include_revoked=include_revoked, kind=kind)
        ]

    # --- Deciding ---------------------------------------------------------

    async def resolve(
        self,
        case_id: int,
        *,
        decision: dict[str, Any],
        user_id: int,
        user_name: str | None = None,
        remember: bool = True,
        visible: frozenset[BusinessSection],
    ) -> CaseRead:
        """Record what a person decided, and tell whoever has to act on it.

        The decision is stored with who took it and when (RF-32), the case
        leaves the pending list (RF-33), and — unless the person asked
        otherwise — it becomes a rule so the same case resolves itself next
        time (RF-34).
        """
        case = await self._require_case(case_id)
        # RF-13, and it lives here rather than on the route because it depends
        # on the **case**: a `Depends` runs before the row is read, so it cannot
        # know which area this one belongs to.
        if case.section not in visible:
            raise PermissionDeniedError(
                NOT_YOUR_SECTION, details={"case_id": case_id, "section": case.section.value}
            )
        if case.status is CaseStatus.RESOLVED:
            raise ConflictError(ALREADY_RESOLVED, details={"case_id": case_id})

        matcher = self._matcher_of(case)
        rule = None
        if remember:
            rule = await self.triage.add_rule(
                kind=case.kind,
                matcher=matcher,
                decision=decision,
                created_by_user_id=user_id,
                created_by_name=user_name,
            )

        now = datetime.now(UTC)
        case.status = CaseStatus.RESOLVED
        case.decision = {**decision, "rule_id": rule.id if rule else None}
        case.resolved_by_user_id = user_id
        case.resolved_by_name = user_name
        case.resolved_at = now
        await self.session.flush()

        await events.publish(
            QuarantineCaseResolved(
                case_id=case.id,
                kind=case.kind,
                decision=decision,
                payload=dict(case.payload),
                rule_id=rule.id if rule else None,
                matcher=matcher,
                decided_by_user_id=user_id,
                decided_at=now,
            ),
            self.session,
        )
        await self.session.commit()
        logger.info(
            "Case resolved",
            extra={"case_id": case.id, "kind": case.kind, "rule_id": rule.id if rule else None},
        )
        return CaseRead.model_validate(case)

    async def close_resolved_elsewhere(self, *, kind: str, key: str, where: str) -> bool:
        """Close the case whose cause was resolved on its own screen (RF-20).

        The list of pending things has to be the one truth about what is still
        pending. Asking somebody to close a case here after they already did
        the work on the payments screen is the same work twice, and the day
        they forget, the list lies — so the list keeps itself honest instead.

        The case is found by the **same** fingerprint that opened it, rebuilt
        from the kind and key the publisher sends, never by a looser match: a
        fingerprint reconstructed generously would close a case nobody
        resolved, which is the same silence read backwards.

        Nothing found is not a failure. Most payments never had a case, and an
        event that closes nothing is the ordinary outcome, so it returns
        whether it closed one and does not raise.
        """
        case = await self.triage.pending_by_fingerprint(fingerprint_of(kind, key))
        if case is None:
            return False

        case.status = CaseStatus.RESOLVED
        # No `resolved_by_*`. RF-21 asks to record that it was resolved this
        # way and keep it readable — not to name a person, whose name belongs
        # to the screen where the work actually happened.
        case.decision = {"action": RESOLVED_ELSEWHERE, "where": where}
        case.resolved_at = datetime.now(UTC)
        await self.session.flush()
        logger.info(
            "Case closed by the screen that owned it",
            extra={"case_id": case.id, "kind": kind, "where": where},
        )
        return True

    async def reopen_closed_elsewhere(self, *, kind: str, key: str) -> bool:
        """What had closed a case got undone on its own screen (RF-24).

        The mirror of `close_resolved_elsewhere`, and it exists because the rule
        the client signed holds in both directions: a list that knows how to
        close itself and not how to reopen is true only until somebody changes
        their mind. The sales screen lets them — 009 promised that undo — and
        without this the record went back to being reviewed while the queue kept
        saying there was nothing to review about it.

        **Only a case that closed itself is reopened.** One a person resolved by
        hand carries their name and their decision, and reopening it would erase
        both because some other record happened to share a fingerprint. That is
        why the lookup asks for `resolved_by_user_id IS NULL` and for this exact
        action, rather than for any resolved case.

        Nothing found is the ordinary outcome, same as its mirror: most undos
        are of work that never had a case.
        """
        case = await self.triage.closed_elsewhere_by_fingerprint(
            fingerprint_of(kind, key), action=RESOLVED_ELSEWHERE
        )
        if case is None:
            return False

        case.status = CaseStatus.PENDING
        # Back to how it arrived. The `decision` goes because there is no longer
        # a decision — what closed it was undone — and `resolved_at` with it, so
        # the age the screen shows keeps counting from `created_at`, which is
        # when it actually started waiting (RF-16).
        case.decision = None
        case.resolved_at = None
        await self.session.flush()
        logger.info("Case reopened by the screen that owned it", extra={"case_id": case.id})
        return True

    async def revoke_rule(self, rule_id: int, *, user_id: int) -> None:
        """Leave a rule without effect and give its cases back (RF-37)."""
        rule = await self.triage.get_rule(rule_id)
        if rule is None:
            raise NotFoundError("Rule not found", details={"rule_id": rule_id})
        if not rule.is_active:
            raise ConflictError(ALREADY_REVOKED, details={"rule_id": rule_id})

        await self.triage.revoke_rule(rule, user_id=user_id, moment=datetime.now(UTC))
        reopened = await self.triage.reopen_by_rule(rule_id)
        await events.publish(
            QuarantineRuleRevoked(
                rule_id=rule.id,
                kind=rule.kind,
                matcher=dict(rule.matcher),
                decision=dict(rule.decision),
            ),
            self.session,
        )
        await self.session.commit()
        logger.info("Rule revoked", extra={"rule_id": rule_id, "cases_reopened": reopened})

    async def redecide_rule(
        self, rule_id: int, *, decision: dict[str, Any], user_id: int
    ) -> RuleRead:
        """Point a rule in force at another decision (RF-28 of 008).

        Nothing goes back to the queue and nothing is deleted: the rule keeps
        who created it and gains who corrected it. Revoking and re-creating —
        the purist alternative — is ruled out by the spec itself, because
        revoking sends the products back to review and RF-29 asks for the
        opposite, that they be reassigned.

        A rule already revoked is refused: reviving an equivalence somebody
        switched off, without anybody deciding it, is the failure this guard
        exists for.
        """
        rule = await self.triage.get_rule(rule_id)
        if rule is None:
            raise NotFoundError("Rule not found", details={"rule_id": rule_id})
        if not rule.is_active:
            raise ConflictError(ALREADY_REVOKED, details={"rule_id": rule_id})

        previous = dict(rule.decision)
        await self.triage.redecide_rule(
            rule, decision=decision, user_id=user_id, moment=datetime.now(UTC)
        )
        await events.publish(
            QuarantineRuleRedecided(
                rule_id=rule.id,
                kind=rule.kind,
                matcher=dict(rule.matcher),
                decision=decision,
                previous_decision=previous,
                decided_by_user_id=user_id,
            ),
            self.session,
        )
        await self.session.commit()
        logger.info("Rule re-pointed", extra={"rule_id": rule_id, "kind": rule.kind})
        return RuleRead.model_validate(rule)

    # --- Internals --------------------------------------------------------

    async def _require_case(self, case_id: int) -> ExceptionCase:
        """Return the case, or say plainly that it is not there."""
        case = await self.triage.get_case(case_id)
        if case is None:
            raise NotFoundError("Case not found", details={"case_id": case_id})
        return case

    @staticmethod
    def _matcher_of(case: ExceptionCase) -> dict[str, Any]:
        """What a future case has to look like for this decision to apply to it."""
        payload = case.payload
        matcher: dict[str, Any] = {"kind": case.kind}
        # A decision about a **written form** matches on the text, never on the
        # product that happened to carry it: matching by product would apply an
        # equivalence to one row and leave the other ninety-nine in the queue,
        # and RF-25 of 008 would fail while everything else looked fine.
        if case.kind == UNKNOWN_CATEGORY:
            if payload.get("category_text"):
                matcher["category_text"] = payload["category_text"]
            return matcher
        if payload.get("product_code"):
            matcher["product_code"] = payload["product_code"]
        if payload.get("product_id"):
            matcher["product_id"] = payload["product_id"]
        return matcher
