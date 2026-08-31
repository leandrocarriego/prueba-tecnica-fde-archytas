"""Triage schemas: the review queue and the rules learned from it."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.triage.models import CaseStatus


class CaseRead(BaseModel):
    """A case as the review screen shows it (RF-26)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    reason: str
    payload: dict[str, Any]
    status: CaseStatus
    batch_id: int | None
    occurrences: int
    decision: dict[str, Any] | None
    resolved_by_user_id: int | None
    resolved_by_name: str | None
    resolved_at: datetime | None
    created_at: datetime


class CaseList(BaseModel):
    """A page of cases."""

    items: list[CaseRead]
    total: int
    skip: int
    limit: int


class ResolutionRequest(BaseModel):
    """What a person decided about a case.

    `decision` is free-form because the queue is generic: an unreadable row is
    resolved with a price and a product, an unknown product with whether to
    incorporate it, a missing one with whether it is discontinued.
    """

    decision: dict[str, Any] = Field(
        description="What to do. For instance {'action': 'incorporate'} or {'price': '48210'}"
    )
    # A decision is remembered by default: that is the point of Artículo II.
    # Turning it off resolves this one case and teaches the system nothing.
    remember: bool = True


class RuleRead(BaseModel):
    """A rule that is being applied on its own (RF-36)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    matcher: dict[str, Any]
    decision: dict[str, Any]
    created_by_user_id: int | None
    created_by_name: str | None
    created_at: datetime
    revoked_by_user_id: int | None
    revoked_at: datetime | None
    updated_by_user_id: int | None = None
    updated_at: datetime | None = None


class RedecisionRequest(BaseModel):
    """Where a rule already in force should point from now on.

    It is not a revocation and it does not send anything back to the queue:
    whoever projected the rule re-points what it had resolved. Confusing the
    two is the classic mistake of 008 — revoking returns the products to
    review, re-pointing reassigns them (RF-29 against RF-31).
    """

    decision: dict[str, Any] = Field(
        description="The new decision. For instance {'category_id': 4}"
    )
