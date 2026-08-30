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
from app.shared.errors import ConflictError, NotFoundError
from app.shared.events import (
    QuarantineCaseResolved,
    QuarantineRuleRedecided,
    QuarantineRuleRevoked,
    events,
)

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

# What the person reads in the review screen (RF-26), in Spanish like every
# other user-facing string.
UNKNOWN_PRODUCT_REASON = "El producto no está entre los conocidos"
MISSING_PRODUCT_REASON = "El producto dejó de figurar en la lista"
UNKNOWN_CATEGORY_REASON = "No sabemos a qué rubro corresponde esta forma escrita"

ALREADY_RESOLVED = "This case has already been resolved"
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
        batch_id: int | None = None,
    ) -> None:
        """Put one thing in front of a person, once."""
        await self.triage.open_case(
            kind=kind,
            reason=reason,
            payload=payload,
            fingerprint=fingerprint_of(kind, key),
            batch_id=batch_id,
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
    ) -> CaseList:
        """The review screen: what was set aside and why (RF-26, RF-27)."""
        cases = await self.triage.list_cases(
            skip=skip, limit=limit, status=status, kind=kind, batch_id=batch_id
        )
        total = await self.triage.count_cases(status=status, kind=kind, batch_id=batch_id)
        return CaseList(
            items=[CaseRead.model_validate(case) for case in cases],
            total=total,
            skip=skip,
            limit=limit,
        )

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
    ) -> CaseRead:
        """Record what a person decided, and tell whoever has to act on it.

        The decision is stored with who took it and when (RF-32), the case
        leaves the pending list (RF-33), and — unless the person asked
        otherwise — it becomes a rule so the same case resolves itself next
        time (RF-34).
        """
        case = await self._require_case(case_id)
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
