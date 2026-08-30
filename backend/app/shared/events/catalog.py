"""The shared vocabulary of domain events.

Events live here, not inside the module that publishes them, and the reason is
the boundary rule itself: if `billing` had to import `purchasing.events` to
subscribe to one of its events, the two modules would be coupled again — by the
import that the rule forbids. A shared catalog is the price of modules that
genuinely do not know about each other.

The consequence to accept: this file is a public vocabulary. Adding an event is
a decision about the language of the business, and it belongs in `plan.md`.

Rules for an event:
- **Past tense.** An event reports something that already happened and cannot be
  refused. `InvoiceRegistered`, not `RegisterInvoice`.
- **Immutable.** Frozen dataclasses: a handler never rewrites what it received.
- **Identifiers, not entities.** An event carries ids and plain values, never a
  SQLAlchemy model — models are private to their module.
"""

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.shared.sections import BusinessSection


class AuditAction(enum.StrEnum):
    """What a manual change did to the datum it touched.

    One vocabulary rather than four events. Four — created, updated, corrected,
    correction reverted — would be four handlers writing into the same table,
    and the log would have four doors instead of one. The distinction survives
    as a field, typed, in `shared/` so both the event and the row that stores it
    read it from the same place.
    """

    CREATED = "CREATED"
    UPDATED = "UPDATED"
    CORRECTED = "CORRECTED"
    CORRECTION_REVERTED = "CORRECTION_REVERTED"


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Base class for every event that crosses a module boundary."""

    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC), kw_only=True)


# ── identity ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class UserRegistered(DomainEvent):
    """A user account was created."""

    user_id: int
    email: str
    role: str


@dataclass(frozen=True, slots=True)
class UserDeactivated(DomainEvent):
    """A user account was disabled and can no longer authenticate."""

    user_id: int


@dataclass(frozen=True, slots=True)
class UserReactivated(DomainEvent):
    """A user account was enabled again and was invited to set a new password."""

    user_id: int


@dataclass(frozen=True, slots=True)
class UserRoleChanged(DomainEvent):
    """A user's role changed, so what they may reach changed with it."""

    user_id: int
    previous_role: str
    role: str


@dataclass(frozen=True, slots=True)
class UserInvited(DomainEvent):
    """A person was invited to set the password of their own access.

    Carries the token because a message without it is useless, and the module
    that delivers it cannot ask identity for it without importing it. The bus
    is in-process and the event is never persisted: **it must never be
    logged**, whole or in part.
    """

    user_id: int
    phone: str
    name: str
    token: str
    expires_at: datetime
    # NEW_ACCESS or REACTIVATION: the same mechanism, a different sentence.
    reason: str


@dataclass(frozen=True, slots=True)
class PasswordResetRequested(DomainEvent):
    """Somebody asked to recover their access. Carries the token, like `UserInvited`."""

    user_id: int
    phone: str
    name: str
    token: str
    expires_at: datetime


# ── operations ───────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class JobRunFailed(DomainEvent):
    """A background job finished in failure."""

    job_run_id: int
    job_name: str
    message: str


@dataclass(frozen=True, slots=True)
class JobRunSucceeded(DomainEvent):
    """A background job finished successfully.

    Symmetric to `JobRunFailed`, and published by the module that owns the work
    rather than by `operations`: the extraction task is the only one that knows
    it got to the end, and it cannot call `operations` to say so.
    """

    job_run_id: int
    job_name: str


# ── the price update pipeline ────────────────────────────────────────────────
#
# Five modules that do not know each other, chained by the events below:
#
#   portal ──PriceListExtracted──► ingestion ──PriceListNormalized──► catalog
#      ▲                               │                                │
#      │                    PriceRowsQuarantined              UnknownProductsObserved
#      │                               ▼                      KnownProductsMissing
#   ProductsRegistered ◄── catalog     triage ◄────────────────────────┘
#
# Every payload is flat: identifiers, strings, numbers and frozen tuples of
# small dataclasses. Never a SQLAlchemy model (`GEN-08`).


@dataclass(frozen=True, slots=True)
class NormalizedPriceRow:
    """One row of the daily list that could be interpreted."""

    staging_row_id: int
    product_code: str
    description: str
    price: Decimal
    currency: str


@dataclass(frozen=True, slots=True)
class QuarantinedRow:
    """One row that could not be interpreted, with what a person needs to read it."""

    staging_row_id: int
    reason: str
    excerpt: str
    product_code: str | None = None


@dataclass(frozen=True, slots=True)
class UnknownProduct:
    """A product the catalog does not know, held back instead of created."""

    staging_row_id: int
    product_code: str
    description: str
    price: Decimal


@dataclass(frozen=True, slots=True)
class MissingProduct:
    """A known product that stopped appearing in the list."""

    product_id: int
    product_code: str
    description: str


@dataclass(frozen=True, slots=True)
class RegisteredProduct:
    """A product the catalog just started to know."""

    product_id: int
    product_code: str


@dataclass(frozen=True, slots=True)
class NormalizedHistoryPoint:
    """One point of the history the portal already publishes for a product."""

    staging_row_id: int
    price: Decimal
    changed_at: datetime


# ── portal ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PriceListExtracted(DomainEvent):
    """The daily price list was downloaded and stored verbatim in `raw`.

    It carries the bytes as well as the identifier. `ingestion` normalises them
    and cannot read `raw.portal_document`, which belongs to `portal`: the row is
    the audit trail (Artículo III), the payload is how the next step gets its
    input without crossing the boundary.
    """

    raw_document_id: int
    content_hash: str
    content: bytes
    content_type: str
    fetched_at: datetime
    job_run_id: int | None = None


@dataclass(frozen=True, slots=True)
class ProductHistoryExtracted(DomainEvent):
    """The history screen of one product was read and stored verbatim in `raw`."""

    raw_document_id: int
    product_code: str
    content_hash: str
    content: bytes


# ── ingestion ────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PriceListNormalized(DomainEvent):
    """The rows of a list that could be typed, as one batch.

    One event per batch, not one per row: a hundred publications inside the same
    transaction would be a hundred handler dispatches for no benefit.
    """

    batch_id: int
    raw_document_id: int
    rows: tuple[NormalizedPriceRow, ...]
    # Every product code the file carried, the quarantined rows included. A row
    # that could not be read is **not** a product that stopped coming, and
    # without this the catalog could not tell the two apart (RF-28).
    seen_codes: tuple[str, ...] = ()
    quarantined: int = 0
    job_run_id: int | None = None


@dataclass(frozen=True, slots=True)
class PriceRowsQuarantined(DomainEvent):
    """Rows of a list that could not be interpreted, set aside for a person."""

    batch_id: int
    cases: tuple[QuarantinedRow, ...]


@dataclass(frozen=True, slots=True)
class PriceHistoryNormalized(DomainEvent):
    """The points of a product's published history that could be typed."""

    product_code: str
    points: tuple[NormalizedHistoryPoint, ...]


@dataclass(frozen=True, slots=True)
class PriceHistoryRowsQuarantined(DomainEvent):
    """Points of a published history that could not be interpreted."""

    product_code: str
    cases: tuple[QuarantinedRow, ...]


# ── catalog ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ProductPricesUpdated(DomainEvent):
    """A batch of prices was applied to the products the catalog knows."""

    batch_id: int
    updated: int
    unchanged: int
    highlighted: int
    quarantined: int = 0
    job_run_id: int | None = None


@dataclass(frozen=True, slots=True)
class UnknownProductsObserved(DomainEvent):
    """The list brought products the catalog does not know. None was created."""

    batch_id: int
    cases: tuple[UnknownProduct, ...]


@dataclass(frozen=True, slots=True)
class KnownProductsMissing(DomainEvent):
    """Known products that did not come in this list. Their last price is kept."""

    batch_id: int
    products: tuple[MissingProduct, ...]


@dataclass(frozen=True, slots=True)
class ProductsRegistered(DomainEvent):
    """Products the catalog started to know, for the first time."""

    batch_id: int
    products: tuple[RegisteredProduct, ...]


# ── triage ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class QuarantineCaseResolved(DomainEvent):
    """A person decided what to do with a case, and the decision became a rule."""

    case_id: int
    kind: str
    decision: dict[str, Any]
    payload: dict[str, Any]
    rule_id: int | None
    matcher: dict[str, Any]
    decided_by_user_id: int
    decided_at: datetime


@dataclass(frozen=True, slots=True)
class QuarantineRuleRevoked(DomainEvent):
    """A learned rule was left without effect, so its cases come back."""

    rule_id: int
    kind: str
    matcher: dict[str, Any]
    decision: dict[str, Any]


# ── operations ───────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PriceUpdateStalled(DomainEvent):
    """Two scheduled runs in a row went by without a successful update.

    Published once per interruption: whoever holds the history of `JobRun` is
    the only one that can tell a new interruption from the same one.
    """

    consecutive_failures: int
    last_success_at: datetime | None
    reason: str


@dataclass(frozen=True, slots=True)
class PriceUpdateRecovered(DomainEvent):
    """The price update started working again after an interruption."""

    recovered_at: datetime


@dataclass(frozen=True, slots=True)
class BusinessParameterChanged(DomainEvent):
    """The owner changed a business parameter.

    The parameters live in `operations`, and a module that needs one keeps its
    own projection fed by this event rather than reading somebody else's table.
    """

    key: str
    value: Any


# ── manual changes, in any module ────────────────────────────────────────────
#
# The two events of the platform operating on itself. Neither belongs to a
# module: whoever edits a datum by hand publishes the first, and whoever owns a
# datum the portal contradicted publishes the second.


@dataclass(frozen=True, slots=True)
class ManualChangeRecorded(DomainEvent):
    """Somebody changed a datum by hand, and the log has to say so.

    Published by the module that owns the datum, consumed by `operations`,
    which turns it into a row. The publisher never learns that a log exists,
    and `operations` never learns whose datum it was — the boundary used in
    favour instead of worked around.

    The handler runs in the publisher's transaction, so a change without its
    record does not exist: if writing the row fails, the edit fails with it
    (`GEN-09`).

    Values travel as plain JSON — a price, a date and a description have to fit
    the same two columns, and an event never carries a model (`GEN-08`).
    """

    entity_type: str
    entity_id: str
    action: AuditAction
    actor_user_id: int
    section: BusinessSection
    field: str | None = None
    old_value: Any = None
    new_value: Any = None
    reason_code: str | None = None
    reason_detail: str | None = None


@dataclass(frozen=True, slots=True)
class CorrectionConflicted(DomainEvent):
    """The portal came back with something other than what it had said.

    The correction is **not** overwritten (RF-28): the module that owns the
    datum marks the conflict and says so here, and the owner is told without
    having to be looking at that screen (RF-29).
    """

    entity_type: str
    entity_id: str
    field: str
    correction_id: int
    original_value: Any
    corrected_value: Any
    incoming_value: Any
