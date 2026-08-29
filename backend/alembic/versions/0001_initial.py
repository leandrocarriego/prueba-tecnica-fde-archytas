"""initial schema: extensions, pipeline schemas, identity and operations tables

Revision ID: 0001
Revises:
Create Date: 2026-08-28

Hand-written baseline for a brand-new database. It creates, in order:

1. the PostgreSQL extensions the platform relies on,
2. the four pipeline schemas (`raw` -> `staging` -> `core`, plus `operations`),
3. the identity tables, which live in the default `public` schema because the
   application owns them, unlike the portal data,
4. the `operations` tables: what ran and the parameters the business can change.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# `pg_trgm` backs the trigram indexes behind supplier and product entity
# resolution; `pgcrypto` provides `gen_random_uuid()` and the digest functions
# used when hashing raw payloads.
EXTENSIONS: tuple[str, ...] = ("pg_trgm", "pgcrypto")

# One-way extraction pipeline: raw (verbatim + hash) -> staging (typed, normalised,
# quarantined) -> core (canonical model). `operations` is the system operating on
# itself: jobs, exceptions, parameters, audit.
PIPELINE_SCHEMAS: tuple[str, ...] = ("raw", "staging", "core", "operations")

OPERATIONS_SCHEMA = "operations"

# Enum types are created explicitly (`create_type=False` on the column) so the
# order of CREATE TYPE / CREATE TABLE stays under this migration's control and
# the downgrade can drop them.
user_role_enum = postgresql.ENUM(
    "OWNER",
    "PURCHASING",
    "SALES",
    name="user_role",
    create_type=False,
)
job_status_enum = postgresql.ENUM(
    "PENDING",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    name="job_status",
    schema=OPERATIONS_SCHEMA,
    create_type=False,
)


def upgrade() -> None:
    for extension in EXTENSIONS:
        op.execute(f'CREATE EXTENSION IF NOT EXISTS "{extension}"')

    # `env.py` already creates these before configuring the migration context, so
    # that a schema-qualified object cannot fail with InvalidSchemaName on a
    # brand-new database. Repeating them here keeps the migration self-contained
    # for anyone applying it as plain SQL (`alembic upgrade head --sql`).
    for schema in PIPELINE_SCHEMAS:
        op.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')

    bind = op.get_bind()
    user_role_enum.create(bind, checkfirst=True)
    job_status_enum.create(bind, checkfirst=True)

    # --- identity (public schema) ---

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("role", user_role_enum, server_default="SALES", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "user_passwords",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_passwords_user_id", "user_passwords", ["user_id"], unique=True)

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_password_reset_tokens_token",
        "password_reset_tokens",
        ["token"],
        unique=True,
    )

    # --- operations (operations schema) ---

    op.create_table(
        "job_run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_name", sa.String(length=255), nullable=False),
        sa.Column("status", job_status_enum, server_default="PENDING", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=OPERATIONS_SCHEMA,
    )
    op.create_index(
        "ix_operations_job_run_task_name",
        "job_run",
        ["task_name"],
        unique=False,
        schema=OPERATIONS_SCHEMA,
    )
    op.create_index(
        "ix_operations_job_run_status",
        "job_run",
        ["status"],
        unique=False,
        schema=OPERATIONS_SCHEMA,
    )

    op.create_table(
        "parameter",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=OPERATIONS_SCHEMA,
    )
    op.create_index(
        "ix_operations_parameter_key",
        "parameter",
        ["key"],
        unique=True,
        schema=OPERATIONS_SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_operations_parameter_key", table_name="parameter", schema=OPERATIONS_SCHEMA)
    op.drop_table("parameter", schema=OPERATIONS_SCHEMA)

    op.drop_index("ix_operations_job_run_status", table_name="job_run", schema=OPERATIONS_SCHEMA)
    op.drop_index("ix_operations_job_run_task_name", table_name="job_run", schema=OPERATIONS_SCHEMA)
    op.drop_table("job_run", schema=OPERATIONS_SCHEMA)

    op.drop_index("ix_password_reset_tokens_token", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")

    op.drop_index("ix_user_passwords_user_id", table_name="user_passwords")
    op.drop_table("user_passwords")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    job_status_enum.drop(bind, checkfirst=True)
    user_role_enum.drop(bind, checkfirst=True)

    # No CASCADE on purpose: if a schema still holds objects, the downgrade must
    # fail loudly instead of deleting extracted data.
    for schema in reversed(PIPELINE_SCHEMAS):
        op.execute(f'DROP SCHEMA IF EXISTS "{schema}"')

    # Extensions are database-wide and may be shared with other objects, so they
    # are deliberately left in place.
