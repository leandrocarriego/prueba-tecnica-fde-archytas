"""Portal models: what the source system said, kept exactly as it said it.

`raw` is immutable (Artículo III). The repository over this table exposes
`insert` and `get` and nothing else, so a correction has nowhere to be written:
every correction happens on the way to `staging`, which is what makes the whole
pipeline reproducible without asking the portal anything again.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

RAW_SCHEMA = "raw"


class PortalSection(enum.StrEnum):
    """Which screen of the portal a document came from."""

    PRICES = "prices"
    PRICE_HISTORY = "price-history"


class PortalDocument(Base):
    """One document downloaded from the portal, verbatim, with its hash.

    `content_hash` is unique on purpose: if the portal publishes the same file
    twice, the second extraction finds it and nothing is reprocessed. That is
    the idempotency of the task (`PY-07`), and it does not depend on anybody
    remembering to check.

    The skip asks `normalized_at`, not merely "is it here": a document that was
    stored and then failed to be interpreted has to be interpreted again on the
    next attempt, or the retry would report a run as successful over a file
    nobody ever read.
    """

    __tablename__ = "portal_document"
    __table_args__ = {"schema": RAW_SCHEMA}

    id: Mapped[int] = mapped_column(primary_key=True)
    section: Mapped[str] = mapped_column(String(50), index=True)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    content_type: Mapped[str] = mapped_column(String(100))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Which run brought it. No foreign key across schemas: it is an identifier,
    # not a relationship — `operations` owns that table and this module does not
    # get to know its shape.
    job_run_id: Mapped[int | None] = mapped_column(Integer, default=None)
    # When the pipeline finished interpreting it. The only column here that is
    # written after the insert, and it says nothing about what the portal
    # delivered: it is this module recording that the publication it made
    # returned without raising. What the portal said is still never rewritten
    # (Artículo III); what changes is our own bookkeeping about it.
    normalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, index=True
    )

    def __repr__(self) -> str:
        return f"<PortalDocument id={self.id} section={self.section} hash={self.content_hash[:8]}>"
