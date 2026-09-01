"""Data access for the triage module. Private to this module."""

from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.triage.models import (
    CaseStatus,
    ExceptionCase,
    ResolutionRule,
    TriageSetting,
)
from app.shared.sections import BusinessSection


class TriageRepository:
    """Reads and writes the review queue and the learned rules."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- The queue -------------------------------------------------------

    async def open_case(
        self,
        *,
        kind: str,
        reason: str,
        payload: dict[str, Any],
        fingerprint: str,
        batch_id: int | None,
        section: BusinessSection,
    ) -> None:
        """Open a case, or count one more occurrence of the one already pending.

        The `ON CONFLICT` targets the partial unique index over pending
        fingerprints, so RF-35 is decided by the database: the same case seen
        three times leaves one pending row with `occurrences = 3`.
        """
        await self.session.execute(
            insert(ExceptionCase)
            .values(
                kind=kind,
                reason=reason,
                payload=payload,
                fingerprint=fingerprint,
                batch_id=batch_id,
                section=section,
                status=CaseStatus.PENDING,
                occurrences=1,
            )
            .on_conflict_do_update(
                index_elements=[ExceptionCase.fingerprint],
                # Written as literal SQL, matching the index predicate word for
                # word: PostgreSQL has to *prove* that the conflict target is
                # the partial index, and it cannot prove anything about a bound
                # parameter.
                index_where=text("status = 'PENDING'"),
                set_={
                    "occurrences": ExceptionCase.occurrences + 1,
                    "batch_id": batch_id,
                    "reason": reason,
                    "payload": payload,
                    # The area travels on the re-arrival too. A kind that
                    # changes owner — the rubros already did, in 010 — would
                    # otherwise leave every case opened before the change
                    # filed under the old area for ever.
                    "section": section,
                },
            )
        )
        await self.session.flush()

    async def get_case(self, case_id: int) -> ExceptionCase | None:
        """Return a case by id, or None."""
        return await self.session.get(ExceptionCase, case_id)

    async def list_cases(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        status: CaseStatus | None = CaseStatus.PENDING,
        kind: str | None = None,
        batch_id: int | None = None,
        sections: frozenset[BusinessSection] | None = None,
    ) -> list[ExceptionCase]:
        """Return a page of cases, newest first."""
        statement = self._filtered(select(ExceptionCase), status, kind, batch_id, sections)
        result = await self.session.execute(
            statement.order_by(ExceptionCase.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def count_cases(
        self,
        *,
        status: CaseStatus | None = CaseStatus.PENDING,
        kind: str | None = None,
        batch_id: int | None = None,
        sections: frozenset[BusinessSection] | None = None,
    ) -> int:
        """How many cases match the same filters as `list_cases`."""
        statement = self._filtered(
            select(func.count()).select_from(ExceptionCase), status, kind, batch_id, sections
        )
        result = await self.session.execute(statement)
        return int(result.scalar_one())

    @staticmethod
    def _filtered(
        statement: Select[Any],
        status: CaseStatus | None,
        kind: str | None,
        batch_id: int | None,
        sections: frozenset[BusinessSection] | None = None,
    ) -> Select[Any]:
        """Apply the filters the listing and its count share.

        `sections` is the one that is not a convenience: it is what keeps a case
        of an area somebody does not reach off their screen (RF-12). An
        **empty** set is honoured as "nothing" rather than ignored as "no
        filter" — a role nobody decided the areas of reads an empty queue, never
        everybody's.
        """
        if status is not None:
            statement = statement.where(ExceptionCase.status == status)
        if kind is not None:
            statement = statement.where(ExceptionCase.kind == kind)
        if batch_id is not None:
            statement = statement.where(ExceptionCase.batch_id == batch_id)
        if sections is not None:
            statement = statement.where(ExceptionCase.section.in_(sections))
        return statement

    async def count_resolved_since(
        self, *, since: datetime, sections: frozenset[BusinessSection] | None = None
    ) -> int:
        """How many cases left the queue since `since` (RF-15).

        Both ways of leaving count, because both are work that got done: a
        person deciding it here, and a person doing the work on the screen that
        owned it, which closes the case on its own (RF-20).

        Narrowed by the same areas as the listing: what the screen says was
        resolved today is what **this** person could have seen waiting.
        """
        statement = self._filtered(
            select(func.count()).select_from(ExceptionCase),
            CaseStatus.RESOLVED,
            None,
            None,
            sections,
        ).where(ExceptionCase.resolved_at >= since)
        result = await self.session.execute(statement)
        return int(result.scalar_one())

    async def oldest_pending_at(
        self, *, sections: frozenset[BusinessSection] | None = None
    ) -> datetime | None:
        """When the case that has been waiting longest was opened (RF-16).

        Narrowed by the same areas as the listing: the oldest thing somebody may
        not see is not "their" oldest thing.
        """
        statement = self._filtered(
            select(func.min(ExceptionCase.created_at)), CaseStatus.PENDING, None, None, sections
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def ensure_case(
        self,
        *,
        kind: str,
        reason: str,
        payload: dict[str, Any],
        fingerprint: str,
        section: BusinessSection,
    ) -> None:
        """Make sure this case is listed, **without counting a re-arrival**.

        The difference with `open_case` is the fact each one records.
        `open_case` says *esto volvió a pasar* and bumps `occurrences`, which is
        right for a row that arrives unreadable in three extractions in a row.
        This one says *esto sigue pendiente*, which is the answer to a question
        somebody asked, and re-asking it is not something happening again: a
        reconciliation that ran every fifteen minutes would report an invoice
        as having occurred ninety-six times by the end of the day.

        So the conflict does nothing at all. A case already pending stays
        exactly as it is —its `occurrences`, its `batch_id`, its `created_at`,
        and therefore how long it has been waiting— and one that a person
        already resolved is **not** re-opened here: the partial index only
        covers pending rows, so a resolved case simply does not conflict, and
        deciding whether it should come back is the caller's business and not a
        side effect of an insert.
        """
        await self.session.execute(
            insert(ExceptionCase)
            .values(
                kind=kind,
                reason=reason,
                payload=payload,
                fingerprint=fingerprint,
                batch_id=None,
                section=section,
                status=CaseStatus.PENDING,
                occurrences=1,
            )
            .on_conflict_do_nothing(
                index_elements=[ExceptionCase.fingerprint],
                # Word for word like the index predicate, for the same reason as
                # in `open_case`: PostgreSQL has to *prove* which index this is.
                index_where=text("status = 'PENDING'"),
            )
        )

    async def pending_of_kinds(self, kinds: tuple[str, ...]) -> list[ExceptionCase]:
        """Every case still open under one of these kinds."""
        if not kinds:
            return []
        result = await self.session.execute(
            select(ExceptionCase).where(
                ExceptionCase.kind.in_(kinds),
                ExceptionCase.status == CaseStatus.PENDING,
            )
        )
        return list(result.scalars().all())

    async def pending_by_fingerprint(self, fingerprint: str) -> ExceptionCase | None:
        """The case still open under this fingerprint, if there is one."""
        result = await self.session.execute(
            select(ExceptionCase).where(
                ExceptionCase.fingerprint == fingerprint,
                ExceptionCase.status == CaseStatus.PENDING,
            )
        )
        return result.scalars().first()

    async def closed_elsewhere_by_fingerprint(
        self, fingerprint: str, *, action: str
    ) -> ExceptionCase | None:
        """The case this fingerprint closed **by itself**, if there is one.

        Deliberately narrower than `pending_by_fingerprint`: it only ever finds
        a case whose decision was taken by the screen that owned the work, never
        one a person resolved by hand. Reopening one of those would throw away
        somebody's decision because a *different* record happened to share a
        fingerprint, and their name is on it (RF-08).

        `action` travels as an argument rather than being read from `service`,
        which imports this file: the vocabulary of a decision belongs up there,
        and a repository that reached for it would close the import in a circle.
        """
        result = await self.session.execute(
            select(ExceptionCase).where(
                ExceptionCase.fingerprint == fingerprint,
                ExceptionCase.status == CaseStatus.RESOLVED,
                ExceptionCase.resolved_by_user_id.is_(None),
                ExceptionCase.decision["action"].astext == action,
            )
        )
        return result.scalars().first()

    # --- The parameters this module reads --------------------------------

    async def setting(self, key: str) -> Any | None:
        """The value of a parameter as this module last heard it, or None."""
        row = await self.session.get(TriageSetting, key)
        return None if row is None else row.value

    async def put_setting(self, key: str, value: Any) -> None:
        """Record the value of a parameter the owner changed."""
        row = await self.session.get(TriageSetting, key)
        if row is None:
            self.session.add(TriageSetting(key=key, value=value))
        else:
            row.value = value
        await self.session.flush()

    async def reopen_by_rule(self, rule_id: int) -> int:
        """Bring back the cases a revoked rule was resolving (RF-37).

        Returns how many came back.
        """
        result = await self.session.execute(
            select(ExceptionCase).where(
                ExceptionCase.status == CaseStatus.RESOLVED,
                ExceptionCase.decision["rule_id"].astext == str(rule_id),
            )
        )
        cases = list(result.scalars().all())
        for case in cases:
            case.status = CaseStatus.PENDING
            case.resolved_at = None
            case.resolved_by_user_id = None
            case.resolved_by_name = None
            case.decision = None
        await self.session.flush()
        return len(cases)

    # --- The rules -------------------------------------------------------

    async def add_rule(
        self,
        *,
        kind: str,
        matcher: dict[str, Any],
        decision: dict[str, Any],
        created_by_user_id: int | None,
        created_by_name: str | None = None,
    ) -> ResolutionRule:
        """Store what a person decided, so it is not asked again."""
        rule = ResolutionRule(
            kind=kind,
            matcher=matcher,
            decision=decision,
            created_by_user_id=created_by_user_id,
            created_by_name=created_by_name,
        )
        self.session.add(rule)
        await self.session.flush()
        await self.session.refresh(rule)
        return rule

    async def get_rule(self, rule_id: int) -> ResolutionRule | None:
        """Return a rule by id, or None."""
        return await self.session.get(ResolutionRule, rule_id)

    async def list_rules(
        self, *, include_revoked: bool = False, kind: str | None = None
    ) -> list[ResolutionRule]:
        """Return the rules, newest first."""
        statement = select(ResolutionRule)
        if not include_revoked:
            statement = statement.where(ResolutionRule.revoked_at.is_(None))
        if kind is not None:
            statement = statement.where(ResolutionRule.kind == kind)
        result = await self.session.execute(statement.order_by(ResolutionRule.id.desc()))
        return list(result.scalars().all())

    async def revoke_rule(self, rule: ResolutionRule, *, user_id: int, moment: datetime) -> None:
        """Leave a rule without effect. It is never deleted."""
        rule.revoked_by_user_id = user_id
        rule.revoked_at = moment
        await self.session.flush()

    async def redecide_rule(
        self,
        rule: ResolutionRule,
        *,
        decision: dict[str, Any],
        user_id: int,
        moment: datetime,
    ) -> None:
        """Point a rule in force at another decision, keeping who created it."""
        rule.decision = decision
        rule.updated_by_user_id = user_id
        rule.updated_at = moment
        await self.session.flush()
