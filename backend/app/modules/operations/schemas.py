"""Operations schemas: the HTTP contract and the contract towards other modules."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.operations.models import JobStatus
from app.shared.events import AuditAction
from app.shared.parameters import ParameterKind
from app.shared.sections import BusinessSection

KEY_MAX = 100


class HealthState(enum.StrEnum):
    """How a component is answering right now.

    `OFF` is not a milder `DOWN`: it means somebody decided this dependency is
    not in use. A channel with no credentials is doing exactly what was asked
    of it, and reporting that as a fault would train whoever reads this to
    ignore the one time it is real.
    """

    OK = "ok"
    DOWN = "down"
    OFF = "off"


class ComponentHealth(BaseModel):
    """The state of one dependency.

    `detail` is deliberately generic: `/health` is public, so it must not leak
    hostnames, drivers or credentials from the underlying exception. The real
    exception goes to the log.
    """

    status: HealthState
    detail: str | None = None


class HealthRead(BaseModel):
    """The answer of `/health`: the service plus every dependency it needs.

    `status` is whether this process can serve a request, and **only the
    database decides it**. WhatsApp is reported beside it and deliberately does
    not count: the route answers 503 when `status` is not OK and Docker
    restarts on that, so letting a WhatsApp outage in would restart the API
    every fifteen seconds because a third party's gateway is down. That is the
    opposite of what the channel promises — a message that cannot be sent never
    takes anything else with it.
    """

    status: HealthState
    service: str
    environment: str
    database: ComponentHealth
    whatsapp: ComponentHealth


class JobRunRead(BaseModel):
    """A run as exposed by the API and to other modules."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_name: str
    status: JobStatus
    started_at: datetime | None
    finished_at: datetime | None
    payload: dict[str, Any] | None
    result: dict[str, Any] | None
    error: str | None
    attempts: int


class JobRunList(BaseModel):
    """A page of runs."""

    items: list[JobRunRead]
    total: int
    skip: int
    limit: int


class ParameterRead(BaseModel):
    """A business parameter: what it is, what it may be, and what it is worth.

    Assembled from the declaration in `app.shared.parameters` with the stored
    value on top — **not** read off the table. A parameter nobody ever changed
    has no row and still appears here with its starting value, which is what
    RF-01 and RF-04 ask for together.
    """

    key: str
    # Spanish: the owner reads these two next to the field (RF-05).
    label: str
    effect: str
    kind: ParameterKind
    value: Any
    initial: Any
    minimum: Any | None
    maximum: Any | None
    unit: str | None
    # Which functionality reads the value, and whether any does yet. Five of
    # the seven are waiting for the feature that will read them, and the screen
    # says so rather than offering a knob that moves nothing.
    consumed_by: str
    has_effect: bool
    # Null while nobody has changed it: that is what tells apart the starting
    # value from a decision somebody took.
    changed_at: datetime | None


class ParameterWrite(BaseModel):
    """A parameter to set.

    No description: the sentence beside the field belongs to the catalog, which
    is also where the range that validates this value lives. Two sources for
    one parameter is one source and one bug.
    """

    key: str = Field(min_length=1, max_length=KEY_MAX)
    value: Any


class ParameterUpdateRequest(BaseModel):
    """The body of `PUT /operations/parameters`.

    The parameters screen saves every field at once, so the endpoint takes the
    whole set and applies it in one transaction: either all the changes land or
    none of them do.
    """

    items: list[ParameterWrite] = Field(min_length=1)


class AuditEntryRead(BaseModel):
    """One line of the history of manual changes (RF-12, RF-13)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: str
    field: str | None
    action: AuditAction
    old_value: Any
    new_value: Any
    reason_code: str | None
    # What the reason means, in the words the person picked it by. Resolved
    # from the same catalog that validates it, so the screen never has a list
    # of its own.
    reason_label: str | None
    reason_detail: str | None
    actor_user_id: int
    # Filled in by the route, not by the service: `operations` stores the id and
    # never learns the name, and `identity.dependencies` is the one surface
    # allowed to translate one into the other.
    actor_name: str | None = None
    section: BusinessSection
    occurred_at: datetime


class AuditEntryList(BaseModel):
    """A page of the history."""

    items: list[AuditEntryRead]
    total: int
    skip: int
    limit: int


class CorrectionReasonRead(BaseModel):
    """One of the reasons a correction may be given (RF-11).

    Served by the API because the API is what validates it: a list living in
    the browser would be a second list, and the two would drift.
    """

    code: str
    label: str


# --- The price update ----------------------------------------------------
#
# The state of the update, asking for one, and the two parameters the owner
# decides. They live here because they are `operations`' own vocabulary: what
# ran, when, and the rules the business can change without a deploy.

# Bounds for what the owner may set. Below one hour the platform would be
# knocking on a third party's door for nothing — the supplier publishes twice a
# day — and a week is the point where "automatic" stops meaning anything.
MIN_INTERVAL_HOURS = 1
MAX_INTERVAL_HOURS = 168
MAX_THRESHOLD_PCT = 1000


class PriceUpdateStatusRead(BaseModel):
    """What the prices screen shows about the update itself (RF-09, RF-11)."""

    last_success_at: datetime | None
    last_run_id: int | None
    last_run_status: JobStatus | None
    last_result: dict[str, Any] | None
    # How many rows that update set aside (RF-27), typed out of the generic
    # `result` so the screen does not have to read an untyped dictionary and a
    # rename of the key breaks the build instead of blanking the number.
    last_quarantined: int | None
    consecutive_failures: int
    # Two scheduled runs in a row went by without a successful update. The
    # screen says so on its own, whether or not WhatsApp worked.
    is_stalled: bool
    interval_hours: int
    highlight_threshold_pct: Decimal


class PriceUpdateRequested(BaseModel):
    """The answer to asking for an update by hand (RF-14, RF-16)."""

    job_run_id: int
    status: JobStatus


class PriceUpdateSettingsRead(BaseModel):
    """The two parameters of this feature, with the value in force (RF-20)."""

    interval_hours: int
    highlight_threshold_pct: Decimal


class PriceUpdateSettingsWrite(BaseModel):
    """What the owner may change (RF-18, RF-19)."""

    interval_hours: int = Field(ge=MIN_INTERVAL_HOURS, le=MAX_INTERVAL_HOURS)
    highlight_threshold_pct: Decimal = Field(ge=0, le=MAX_THRESHOLD_PCT)
