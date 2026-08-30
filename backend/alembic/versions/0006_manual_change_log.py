"""The log of every manual change, and the triggers that make it append-only

`operations.audit_entry` answers the one question the feature exists for: who
edited what, when, what it said before, and why. Every module that lets a
person edit a datum publishes `ManualChangeRecorded`, and this module turns it
into a row here.

The triggers are the point of this migration and not decoration. RF-16 and
RF-17 say the system **must prevent** a log entry from being modified or
deleted, and a repository that merely does not expose the method prevents it
only until somebody adds the method. Two triggers over one function prevent it
for a `psql` session too: one `FOR EACH ROW` for `UPDATE` and `DELETE`, and a
second one `FOR EACH STATEMENT` for the `TRUNCATE` that a row-level trigger
never sees.

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OPERATIONS = "operations"

# `restrict_violation` rather than the generic one: a driver that maps SQLSTATE
# to an exception class then reports this as the integrity failure it is.
APPEND_ONLY_FUNCTION = f"""
CREATE OR REPLACE FUNCTION {OPERATIONS}.audit_entry_stays_written() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION
        'operations.audit_entry is append-only: % is not allowed', TG_OP
        USING ERRCODE = 'restrict_violation';
END;
$$ LANGUAGE plpgsql;
"""

APPEND_ONLY_TRIGGER = f"""
CREATE TRIGGER audit_entry_append_only
    BEFORE UPDATE OR DELETE ON {OPERATIONS}.audit_entry
    FOR EACH ROW EXECUTE FUNCTION {OPERATIONS}.audit_entry_stays_written();
"""

# `TRUNCATE` empties the table without touching a single row, so the row-level
# trigger above never fires for it. Postgres only allows a statement-level
# trigger on `TRUNCATE`, which is why this is a second one and not another
# event on the first; the function it runs is the same.
NO_TRUNCATE_TRIGGER = f"""
CREATE TRIGGER audit_entry_no_truncate
    BEFORE TRUNCATE ON {OPERATIONS}.audit_entry
    FOR EACH STATEMENT EXECUTE FUNCTION {OPERATIONS}.audit_entry_stays_written();
"""


def upgrade() -> None:
    """Create the log, its four indexes, and the triggers that freeze it."""
    op.create_table(
        "audit_entry",
        sa.Column("id", sa.BigInteger(), nullable=False),
        # The publisher's own word for the kind of datum. A string and not a
        # foreign key: `operations` never learns whose datum it was.
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column("field", sa.String(length=100), nullable=True),
        sa.Column(
            "action",
            sa.Enum(
                "CREATED",
                "UPDATED",
                "CORRECTED",
                "CORRECTION_REVERTED",
                name="audit_action",
                schema=OPERATIONS,
            ),
            nullable=False,
        ),
        sa.Column("old_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reason_code", sa.String(length=50), nullable=True),
        sa.Column("reason_detail", sa.Text(), nullable=True),
        # No FK to `users`: `identity` is another module, and a key between two
        # modules' schemas is the coupling Artículo IV forbids.
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "section",
            sa.Enum("PURCHASING", "SALES", "SYSTEM", name="section", schema=OPERATIONS),
            nullable=False,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=OPERATIONS,
    )
    # One index per question the history screen asks (RF-13 to RF-15, RF-19).
    op.create_index(
        "ix_audit_entry_actor_occurred",
        "audit_entry",
        ["actor_user_id", "occurred_at"],
        schema=OPERATIONS,
    )
    op.create_index(
        "ix_audit_entry_entity", "audit_entry", ["entity_type", "entity_id"], schema=OPERATIONS
    )
    op.create_index("ix_audit_entry_occurred_at", "audit_entry", ["occurred_at"], schema=OPERATIONS)
    op.create_index("ix_audit_entry_section", "audit_entry", ["section"], schema=OPERATIONS)

    op.execute(APPEND_ONLY_FUNCTION)
    op.execute(APPEND_ONLY_TRIGGER)
    op.execute(NO_TRUNCATE_TRIGGER)


def downgrade() -> None:
    """Drop the log with its triggers. There is nothing here to preserve elsewhere."""
    op.execute(f"DROP TRIGGER IF EXISTS audit_entry_no_truncate ON {OPERATIONS}.audit_entry")
    op.execute(f"DROP TRIGGER IF EXISTS audit_entry_append_only ON {OPERATIONS}.audit_entry")
    op.execute(f"DROP FUNCTION IF EXISTS {OPERATIONS}.audit_entry_stays_written()")
    op.drop_index("ix_audit_entry_section", table_name="audit_entry", schema=OPERATIONS)
    op.drop_index("ix_audit_entry_occurred_at", table_name="audit_entry", schema=OPERATIONS)
    op.drop_index("ix_audit_entry_entity", table_name="audit_entry", schema=OPERATIONS)
    op.drop_index("ix_audit_entry_actor_occurred", table_name="audit_entry", schema=OPERATIONS)
    op.drop_table("audit_entry", schema=OPERATIONS)
    sa.Enum(name="section", schema=OPERATIONS).drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="audit_action", schema=OPERATIONS).drop(op.get_bind(), checkfirst=True)
