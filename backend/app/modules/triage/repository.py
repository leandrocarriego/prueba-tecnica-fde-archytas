"""Data access for the triage module. Private to this module."""

from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.triage.models import CaseStatus, ExceptionCase, ResolutionRule


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
    ) -> list[ExceptionCase]:
        """Return a page of cases, newest first."""
        statement = self._filtered(select(ExceptionCase), status, kind, batch_id)
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
    ) -> int:
        """How many cases match the same filters as `list_cases`."""
        statement = self._filtered(
            select(func.count()).select_from(ExceptionCase), status, kind, batch_id
        )
        result = await self.session.execute(statement)
        return int(result.scalar_one())

    @staticmethod
    def _filtered(
        statement: Select[Any], status: CaseStatus | None, kind: str | None, batch_id: int | None
    ) -> Select[Any]:
        """Apply the filters the listing and its count share."""
        if status is not None:
            statement = statement.where(ExceptionCase.status == status)
        if kind is not None:
            statement = statement.where(ExceptionCase.kind == kind)
        if batch_id is not None:
            statement = statement.where(ExceptionCase.batch_id == batch_id)
        return statement

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
