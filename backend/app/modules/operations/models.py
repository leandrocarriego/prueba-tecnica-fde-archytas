"""Operations models.

`operations` is where the platform keeps track of itself: what ran, when, how it
ended, the parameters the business can change without a deploy, and the log of
every manual change anybody made. Every table is schema-qualified so none of
them lands in `public` next to identity.
"""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DDL,
    BigInteger,
    DateTime,
    Enum,
    Index,
    Integer,
    String,
    Text,
    event,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.shared.events.catalog import AuditAction
from app.shared.sections import BusinessSection

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


class AuditEntry(Base):
    """One manual change, by one person, on one datum. Append-only.

    Every module that lets somebody edit a datum publishes
    `ManualChangeRecorded`, and this module turns it into a row here. It never
    learns whose datum it was: `entity_type` is a string in the publisher's own
    vocabulary (`catalog.product_price`), not a foreign key.

    **Nothing here can be rewritten.** The migration installs triggers that
    make any `UPDATE`, `DELETE` or `TRUNCATE` fail, and the repository does not
    expose the methods either (RF-16, RF-17). The two are not redundant: the
    repository stops the application, the triggers stop a `psql` session as
    well, and a requirement that says "the system must prevent" is not honoured
    by a method somebody merely has not written yet.

    No foreign key to `users`, deliberately: `identity` is another module, and a
    key between two modules' schemas is the coupling the boundary rule forbids
    (Artículo IV). The name is resolved when the screen is drawn.
    """

    __tablename__ = "audit_entry"
    __table_args__ = (
        # What a datum's own history costs to read (RF-15).
        Index("ix_audit_entry_entity", "entity_type", "entity_id"),
        # The listing, newest first (RF-13). Ascending on purpose: a btree is
        # walked backwards just as cheaply, and a plain index is what
        # `alembic check` can compare without drifting.
        Index("ix_audit_entry_occurred_at", "occurred_at"),
        # Filtering by person inside a date range (RF-14).
        Index("ix_audit_entry_actor_occurred", "actor_user_id", "occurred_at"),
        # Showing everybody else only their own sections (RF-19).
        Index("ix_audit_entry_section", "section"),
        {"schema": OPERATIONS_SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # The publisher's word for what kind of datum this is: `catalog.product`,
    # `operations.parameter`. A string, because the log outlives the module.
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(100))
    # Null when the change is the whole record rather than one of its fields.
    field: Mapped[str | None] = mapped_column(String(100), default=None)
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action", schema=OPERATIONS_SCHEMA)
    )
    # JSONB because one column has to hold a price, a date and a description
    # without a column per type. Null in a creation, and in a reversal that
    # gives the datum back to the portal.
    old_value: Mapped[Any | None] = mapped_column(JSONB, default=None)
    new_value: Mapped[Any | None] = mapped_column(JSONB, default=None)
    reason_code: Mapped[str | None] = mapped_column(String(50), default=None)
    reason_detail: Mapped[str | None] = mapped_column(Text, default=None)
    actor_user_id: Mapped[int] = mapped_column(Integer)
    section: Mapped[BusinessSection] = mapped_column(
        Enum(BusinessSection, name="section", schema=OPERATIONS_SCHEMA)
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<AuditEntry id={self.id} {self.action} {self.entity_type}:{self.entity_id}>"


# The log stays written wherever the schema is built.
#
# The same function and both triggers are in migration 0006, which is what
# installs them in a real database. They are attached to the metadata as well
# because `Base.metadata.create_all()` builds the schema from the models alone —
# the test database among them — and an invariant that exists only in production
# is an invariant no test can prove. The duplication is these three statements
# and nothing else, and a migration is a frozen historical record that must not
# import application code.
APPEND_ONLY_FUNCTION = f"""
CREATE OR REPLACE FUNCTION {OPERATIONS_SCHEMA}.audit_entry_stays_written() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION
        'operations.audit_entry is append-only: % is not allowed', TG_OP
        USING ERRCODE = 'restrict_violation';
END;
$$ LANGUAGE plpgsql;
"""

APPEND_ONLY_TRIGGER = f"""
CREATE TRIGGER audit_entry_append_only
    BEFORE UPDATE OR DELETE ON {OPERATIONS_SCHEMA}.audit_entry
    FOR EACH ROW EXECUTE FUNCTION {OPERATIONS_SCHEMA}.audit_entry_stays_written();
"""

# A second trigger for the one statement the first cannot see. `TRUNCATE`
# removes every row without touching any of them, so a `FOR EACH ROW` trigger
# never fires and the whole log would go in silence — the opposite of what
# RF-17 promises. Only a statement-level trigger is allowed on `TRUNCATE`, so
# it cannot be folded into the one above; the function it runs is the same one.
NO_TRUNCATE_TRIGGER = f"""
CREATE TRIGGER audit_entry_no_truncate
    BEFORE TRUNCATE ON {OPERATIONS_SCHEMA}.audit_entry
    FOR EACH STATEMENT EXECUTE FUNCTION {OPERATIONS_SCHEMA}.audit_entry_stays_written();
"""

# One listener per statement and not one concatenated string: asyncpg prepares
# whatever it is given, and a prepared statement holds exactly one command.
#
# `DDL` also runs its text through Python's `%` formatting, and the message
# above carries a `%` of its own (`% is not allowed`, which PL/pgSQL fills with
# the operation). Doubling it here rather than in the constant keeps the SQL
# identical to the migration's, which is the point of having both.
for statement in (APPEND_ONLY_FUNCTION, APPEND_ONLY_TRIGGER, NO_TRUNCATE_TRIGGER):
    event.listen(
        AuditEntry.__table__,
        "after_create",
        DDL(statement.replace("%", "%%")).execute_if(dialect="postgresql"),
    )
