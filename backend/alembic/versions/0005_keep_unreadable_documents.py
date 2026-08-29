"""Keep what the portal delivered even when it cannot be read

The extraction used to store the document and interpret it in one transaction,
so a file that failed to parse took its own evidence down with it. The day the
portal changes its format is the day the parser breaks — and the day the file is
most needed. `normalized_at` splits the two: the bytes are committed first, and
the mark is what says the pipeline managed to read them.

It also keeps the retry honest. The skip now asks "did I already read this?"
instead of "do I already have this": a stored document that was never
interpreted is interpreted on the next attempt, rather than closing the run as
successful over a file nobody read.

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | None = None
depends_on: str | None = None

RAW = "raw"


def upgrade() -> None:
    """Add the mark, and consider everything already stored as already read."""
    op.add_column(
        "portal_document",
        sa.Column("normalized_at", sa.DateTime(timezone=True), nullable=True),
        schema=RAW,
    )
    op.create_index(
        "ix_raw_portal_document_normalized_at",
        "portal_document",
        ["normalized_at"],
        schema=RAW,
    )
    # Under the old design a stored document was always an interpreted one:
    # they shared a transaction. Leaving them null would make the next run
    # reprocess the whole history.
    op.execute(f"UPDATE {RAW}.portal_document SET normalized_at = fetched_at")


def downgrade() -> None:
    """Drop the mark. Nothing the portal said is lost either way."""
    op.drop_index("ix_raw_portal_document_normalized_at", "portal_document", schema=RAW)
    op.drop_column("portal_document", "normalized_at", schema=RAW)
