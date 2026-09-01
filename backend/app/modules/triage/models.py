"""Triage models.

They live in the `operations` schema, next to the tables of `operations` itself.
That is a namespace, **not** a boundary: the boundary is the module, and the
test verifies it by import. Neither module reads the other's tables.
"""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.shared.sections import BusinessSection

OPERATIONS_SCHEMA = "operations"


class CaseStatus(enum.StrEnum):
    """Whether somebody has already decided about a case."""

    PENDING = "PENDING"
    RESOLVED = "RESOLVED"


class ExceptionCase(Base):
    """Something the pipeline could not resolve on its own.

    `payload` is JSONB and `kind` is a plain string on purpose: this queue is
    not about prices, and the screen that shows it reads the reason, not the
    domain.
    """

    __tablename__ = "exception"
    __table_args__ = (
        # RF-35, enforced by the database: while a case is pending, the same
        # case cannot be opened twice. A `SELECT` first would race with the
        # insert; a partial unique index cannot.
        Index(
            "uq_exception_pending_fingerprint",
            "fingerprint",
            unique=True,
            postgresql_where=text("status = 'PENDING'"),
        ),
        Index("ix_exception_status_kind", "status", "kind"),
        # The query the review screen makes: everything pending of the areas
        # this person reaches (RF-12, RF-22).
        Index("ix_exception_section_status", "section", "status"),
        {"schema": OPERATIONS_SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(50))
    # Which part of the business this case belongs to, so the queue can show it
    # to the person who can do something about it (RF-12). It is **written by
    # whoever opens the case**, not deduced from `kind` when reading: the
    # publisher is the only one who knows, and the day a kind changes owner —
    # which already happened to the rubros in 010 — a lookup table far from it
    # would show the case to the wrong person without anything failing.
    section: Mapped[BusinessSection] = mapped_column(
        # `create_type=False` in the migration: `operations.section` is the
        # same type `operations.manual_change` already uses. One vocabulary,
        # one type.
        Enum(BusinessSection, name="section", schema=OPERATIONS_SCHEMA)
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # What the person reads (RF-26), so it is written in Spanish.
    reason: Mapped[str] = mapped_column(String(200))
    # Hash of whatever makes two cases "the same case".
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, name="case_status", schema=OPERATIONS_SCHEMA),
        default=CaseStatus.PENDING,
        server_default=CaseStatus.PENDING.value,
    )
    batch_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    # How many times it came back while it was still pending.
    occurrences: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    decision: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    resolved_by_user_id: Mapped[int | None] = mapped_column(Integer, default=None)
    # The name is stored, not looked up: RF-32 asks who decided, and that is a
    # historical fact. Joining live against `identity` would also mean crossing
    # a module boundary to render a screen (Artículo IV).
    resolved_by_name: Mapped[str | None] = mapped_column(String(255), default=None)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<ExceptionCase id={self.id} kind={self.kind} status={self.status}>"


class TriageSetting(Base):
    """The business parameters this module reads, as its own projection.

    `triage.stale_days` says from how many days a pending case counts as
    delayed (RF-18 of 011). It is copied here rather than asked for because
    `operations` owns the parameters and this module may not import it: the
    projection is fed by `BusinessParameterChanged`, which is the shape
    `sales` and `purchases` already use for exactly this.
    """

    __tablename__ = "triage_setting"
    __table_args__ = {"schema": OPERATIONS_SCHEMA}

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<TriageSetting key={self.key}>"


class ResolutionRule(Base):
    """A decision a person took, kept so the system stops asking (Artículo II).

    It is revoked, never deleted: a deleted rule cannot be audited, and RF-36
    asks for who took it and when.
    """

    __tablename__ = "resolution_rule"
    __table_args__ = {"schema": OPERATIONS_SCHEMA}

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(50), index=True)
    matcher: Mapped[dict[str, Any]] = mapped_column(JSONB)
    decision: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # Nullable, and that is a statement about honesty rather than convenience:
    # an equivalence **seeded from the table the client signed** was decided by
    # nobody. Stamping the owner's id on it would be more comfortable and would
    # be a lie in an audit record, which is the one place a comfortable lie
    # cannot be afforded (RF-27 of 008).
    created_by_user_id: Mapped[int | None] = mapped_column(Integer, default=None)
    # Who took it, in the words the screen shows (RF-36). Kept next to the id
    # for the same reason as on the case: it is a record of a decision, and a
    # person who later leaves does not stop having taken it.
    created_by_name: Mapped[str | None] = mapped_column(String(255), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_by_user_id: Mapped[int | None] = mapped_column(Integer, default=None)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    # Who corrected where this rule points, and when. It is what lets a rule be
    # re-pointed **without** losing who created it — and therefore what makes
    # re-pointing something other than a contradiction of "revoked, never
    # deleted": nothing is lost, one more fact is added (RF-28 of 008).
    updated_by_user_id: Mapped[int | None] = mapped_column(Integer, default=None)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    @property
    def is_active(self) -> bool:
        """A rule stops applying the moment it is revoked."""
        return self.revoked_at is None

    def __repr__(self) -> str:
        return f"<ResolutionRule id={self.id} kind={self.kind} active={self.is_active}>"
