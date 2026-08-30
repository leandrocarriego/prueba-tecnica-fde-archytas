"""Operations schemas: the HTTP contract and the contract towards other modules."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.operations.models import JobStatus
from app.quality import Quality

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
    # What the suite measured for the code this image was built from. `None`
    # when the image carries no snapshot, which is the honest way to say "we do
    # not know" — the screen shows nothing rather than a number nobody checked.
    quality: Quality | None = None


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
    """A business parameter as exposed by the API and to other modules."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    value: Any
    description: str | None
    updated_at: datetime


class ParameterWrite(BaseModel):
    """A parameter to create or overwrite.

    Leaving `description` unset keeps the stored one, so a caller that only
    changes the value does not have to resend the text next to the field.
    """

    key: str = Field(min_length=1, max_length=KEY_MAX)
    value: Any
    description: str | None = None


class ParameterUpdateRequest(BaseModel):
    """The body of `PUT /operations/parameters`.

    The parameters screen saves every field at once, so the endpoint takes the
    whole set and applies it in one transaction: either all the changes land or
    none of them do.
    """

    items: list[ParameterWrite] = Field(min_length=1)


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
