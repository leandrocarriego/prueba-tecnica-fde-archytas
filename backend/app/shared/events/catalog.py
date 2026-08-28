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

from dataclasses import dataclass, field
from datetime import UTC, datetime


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


# ── operations ───────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class JobRunFailed(DomainEvent):
    """A background job finished in failure."""

    job_run_id: int
    job_name: str
    message: str
