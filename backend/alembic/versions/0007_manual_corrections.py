"""What a person put on top of what the portal said

`core.correction` holds one row per corrected field: what the portal informed,
what the value is now, who decided it and why. It lives in `core` because
`catalog` writes it — the module that owns the datum owns its corrections, so
that detecting a conflict while a new price is being applied is a local
comparison and not a read of somebody else's table.

Two things the schema itself enforces, rather than the code remembering to:

* **One correction in force per field.** The partial unique index covers every
  row that is not `REVERTED`, so a second correction on the same field either
  replaces the first or collides.
* **`portal_value` is not null.** A correction without the original value could
  never be undone (RF-31), which is half of what the table is for.

Nothing is backfilled. There are no previous corrections, and inventing rows
for a past nobody recorded is the opposite of what this feature promises.

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE = "core"
IN_FORCE = "status <> 'REVERTED'"


def upgrade() -> None:
    """Create the corrections table and the index that keeps one per field."""
    op.create_table(
        "correction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column("field", sa.String(length=100), nullable=False),
        # What the portal informed. Never written again (RF-25), and what a
        # reversal restores (RF-31).
        sa.Column("portal_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("corrected_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason_code", sa.String(length=50), nullable=False),
        sa.Column("reason_detail", sa.Text(), nullable=True),
        sa.Column("corrected_by_user_id", sa.Integer(), nullable=False),
        sa.Column("corrected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            # No schema on the type: the next module to keep corrections lives
            # in another schema and reuses this one rather than declaring a
            # near-identical twin.
            sa.Enum("ACTIVE", "CONFLICTED", "REVERTED", name="correction_status"),
            server_default="ACTIVE",
            nullable=False,
        ),
        # What the portal came back with, when it contradicted the original.
        sa.Column("conflict_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("conflict_detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reverted_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=CORE,
    )
    op.create_index(
        "uq_correction_in_force",
        "correction",
        ["entity_type", "entity_id", "field"],
        unique=True,
        schema=CORE,
        postgresql_where=sa.text(IN_FORCE),
    )


def downgrade() -> None:
    """Drop the table and its enum. Nothing the portal said lived only here."""
    op.drop_index(
        "uq_correction_in_force",
        table_name="correction",
        schema=CORE,
        postgresql_where=sa.text(IN_FORCE),
    )
    op.drop_table("correction", schema=CORE)
    sa.Enum(name="correction_status").drop(op.get_bind(), checkfirst=True)
