"""Operations models.

`operations` is where the platform keeps track of itself: what ran, when, how it
ended, and the parameters the business can change without a deploy. Both
tables are schema-qualified so they never land in `public` next to identity.
"""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

OPERATIONS_SCHEMA = "operations"


class JobStatus(enum.StrEnum):
    """The life of a run: queued, executing, and how it ended."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class JobRun(Base):
    """One execution of a background task.

    A failed overnight extraction has to be explainable the next morning, so
    the payload that started the run and the error that ended it are stored
    with the row instead of living only in the worker's log. `attempts` counts
    executions of the same run: tasks are idempotent, so a retry reuses the
    row rather than opening a second one.
    """

    __tablename__ = "job_run"
    __table_args__ = {"schema": OPERATIONS_SCHEMA}

    id: Mapped[int] = mapped_column(primary_key=True)
    task_name: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", schema=OPERATIONS_SCHEMA),
        default=JobStatus.PENDING,
        server_default=JobStatus.PENDING.value,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    def __repr__(self) -> str:
        return f"<JobRun id={self.id} task={self.task_name} status={self.status}>"


class Parameter(Base):
    """A business rule that can change without a deploy.

    Thresholds, schedules and tolerances belong to the business, not to the
    source code. The value is JSONB so a parameter can be a number, a flag or
    a small structure without a migration per setting; `description` is what
    the owner reads next to the field.
    """

    __tablename__ = "parameter"
    __table_args__ = {"schema": OPERATIONS_SCHEMA}

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[Any] = mapped_column(JSONB)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Parameter key={self.key}>"
