"""Data access for the ingestion module. Private to this module."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ingestion.models import (
    PriceHistoryRow,
    PriceRow,
    ResolutionRuleProjection,
    batch_sequence,
)


class StagingRepository:
    """Writes the typed rows of a batch and reads the rules already learned."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def next_batch_id(self) -> int:
        """Take the next batch number from the database.

        From a sequence rather than from a counter in Python: two runs that
        overlap must never be handed the same batch.
        """
        result = await self.session.execute(select(batch_sequence.next_value()))
        return int(result.scalar_one())

    async def add_rows(self, rows: list[PriceRow]) -> list[PriceRow]:
        """Persist the rows of a batch and return them with their ids."""
        self.session.add_all(rows)
        await self.session.flush()
        return rows

    async def add_history_rows(self, rows: list[PriceHistoryRow]) -> list[PriceHistoryRow]:
        """Persist the points read from a product's history screen."""
        self.session.add_all(rows)
        await self.session.flush()
        return rows

    # --- The projection of what a person already decided -----------------

    async def rules(self) -> list[ResolutionRuleProjection]:
        """Return every rule this module knows about."""
        result = await self.session.execute(
            select(ResolutionRuleProjection).order_by(ResolutionRuleProjection.rule_id)
        )
        return list(result.scalars().all())

    async def save_rule(
        self,
        *,
        rule_id: int,
        kind: str,
        matcher: dict[str, object],
        decision: dict[str, object],
    ) -> ResolutionRuleProjection:
        """Record (or refresh) a rule in the projection.

        Only `handlers.py` calls this, and that is the point: the rules belong
        to `triage`, and this table is a copy kept in the shape this module
        needs to read while it normalises.
        """
        rule = await self.session.get(ResolutionRuleProjection, rule_id)
        if rule is None:
            rule = ResolutionRuleProjection(
                rule_id=rule_id, kind=kind, matcher=matcher, decision=decision
            )
            self.session.add(rule)
        else:
            rule.kind, rule.matcher, rule.decision = kind, matcher, decision
        await self.session.flush()
        return rule

    async def drop_rule(self, rule_id: int) -> None:
        """Forget a rule that was left without effect."""
        await self.session.execute(
            delete(ResolutionRuleProjection).where(ResolutionRuleProjection.rule_id == rule_id)
        )
        await self.session.flush()
