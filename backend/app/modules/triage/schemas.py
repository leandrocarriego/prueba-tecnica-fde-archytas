"""Triage schemas: the review queue and the rules learned from it."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.triage.models import CaseStatus
from app.shared.sections import BusinessSection


class CaseRead(BaseModel):
    """A case as the review screen shows it (RF-26)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    reason: str
    payload: dict[str, Any]
    # Which part of the business the case belongs to (RF-12). The screen shows
    # it and filters by it; the service is what makes sure a case of an area
    # somebody does not reach never gets this far.
    section: BusinessSection
    status: CaseStatus
    batch_id: int | None
    occurrences: int
    decision: dict[str, Any] | None
    resolved_by_user_id: int | None
    resolved_by_name: str | None
    resolved_at: datetime | None
    created_at: datetime
    # How long it has been waiting, and whether that is too long (RF-16,
    # RF-17). Both are computed when the case is read and neither is stored: a
    # subtraction between two dates kept in a column is a derived state that
    # goes stale the moment nobody re-runs the job that wrote it.
    waiting_days: int = 0
    is_stale: bool = False


class CaseList(BaseModel):
    """A page of cases."""

    items: list[CaseRead]
    total: int
    skip: int
    limit: int
    # What the header of the screen says: how many are waiting and since when
    # (RF-15, RF-16). They are about **every** pending case of the areas this
    # person reaches, not about the page — a page-sized total would say the
    # list is short whenever the page is.
    pending_total: int = 0
    oldest_at: datetime | None = None
    # What the queue emptied today, on the shop's clock. It is the other half of
    # the same sentence: a screen that only counts what is left reads as a list
    # that never moves, and the work that did move is the reason it is shorter.
    resolved_today: int = 0
    # The areas this person may ask to see on their own (RF-22). It travels with
    # the page so the screen can draw the filter **without keeping a second copy
    # of the role matrix**: which areas a role reaches is `identity`'s answer
    # and nobody else's, and a copy of it in the browser would be one rule in
    # two places, which is one rule and one bug.
    sections: list[BusinessSection] = []


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
