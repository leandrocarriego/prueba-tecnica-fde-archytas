"""price update: raw documents, staging rows, catalog and triage

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-29

The tables of the price update, one schema at a time and in the direction the
data flows:

1. `raw.portal_document` — what the portal said, verbatim, with its hash,
2. `staging.price_row` / `price_history_row` — typed, valid or quarantined —
   plus `staging.resolution_rule`, the projection `ingestion` reads,
3. `core.product`, `core.product_price` and `core.price_point` — the canonical
   model — plus `core.catalog_setting`, the parameters `catalog` projects,
4. `operations.exception` and `operations.resolution_rule` — the review queue
   and the decisions learned from it.

It ends by seeding the two parameters the feature starts with, so a brand-new
installation queries every 12 hours and highlights any rise above 10% before
anybody configures anything (RF-20).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RAW_SCHEMA = "raw"
STAGING_SCHEMA = "staging"
CORE_SCHEMA = "core"
OPERATIONS_SCHEMA = "operations"

# Enum types are created explicitly (`create_type=False` on the column) so this
# migration controls the order of CREATE TYPE / CREATE TABLE and the downgrade
# can drop them. Without that, `downgrade -1` followed by `upgrade head` fails
# on a type that was never removed.
row_status_enum = postgresql.ENUM(
    "VALID",
    "QUARANTINED",
    name="row_status",
    schema=STAGING_SCHEMA,
    create_type=False,
)
product_status_enum = postgresql.ENUM(
    "ACTIVE",
    "DISCONTINUED",
    name="product_status",
    schema=CORE_SCHEMA,
    create_type=False,
)
price_source_enum = postgresql.ENUM(
    "PORTAL",
    "SYSTEM",
    name="price_source",
    schema=CORE_SCHEMA,
    create_type=False,
)
case_status_enum = postgresql.ENUM(
    "PENDING",
    "RESOLVED",
    name="case_status",
    schema=OPERATIONS_SCHEMA,
    create_type=False,
)

# What the platform does on day one, before the owner changes anything (RF-20).
# Twelve hours because the supplier publishes twice a day, and 10% is a starting
# point the owner moves whenever they like.
INITIAL_PARAMETERS: tuple[tuple[str, str, str], ...] = (
    (
        "price_update.interval_hours",
        "12",
        "Cada cuántas horas se consulta el portal",
    ),
    (
        "price_update.highlight_threshold_pct",
        '"10"',
        "Porcentaje de suba a partir del cual un producto se destaca",
    ),
)


def upgrade() -> None:
    bind = op.get_bind()
    row_status_enum.create(bind, checkfirst=True)
    product_status_enum.create(bind, checkfirst=True)
    price_source_enum.create(bind, checkfirst=True)
    case_status_enum.create(bind, checkfirst=True)

    # --- raw: what the portal said -----------------------------------

    op.create_table(
        "portal_document",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(length=50), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("job_run_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=RAW_SCHEMA,
    )
    # Unique on purpose: the same file downloaded twice is stored once, and that
    # is what makes the extraction task idempotent.
    op.create_index(
        "ix_raw_portal_document_content_hash",
        "portal_document",
        ["content_hash"],
        unique=True,
        schema=RAW_SCHEMA,
    )
    op.create_index(
        "ix_raw_portal_document_section",
        "portal_document",
        ["section"],
        unique=False,
        schema=RAW_SCHEMA,
    )

    # --- staging: what could be interpreted ---------------------------

    # One number per run of the pipeline, handed out by the database so two
    # overlapping runs can never share a batch.
    op.execute(f'CREATE SEQUENCE IF NOT EXISTS "{STAGING_SCHEMA}".price_batch_seq')

    op.create_table(
        "price_row",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_document_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("product_code", sa.String(length=64), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("price", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="ARS", nullable=False),
        sa.Column("status", row_status_enum, server_default="VALID", nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("category_raw", sa.String(length=200), nullable=True),
        sa.Column("subcategory_raw", sa.String(length=200), nullable=True),
        sa.Column("resolved_by_rule_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=STAGING_SCHEMA,
    )
    op.create_index(
        "ix_price_row_batch_status",
        "price_row",
        ["batch_id", "status"],
        unique=False,
        schema=STAGING_SCHEMA,
    )
    op.create_index(
        "ix_price_row_product_code",
        "price_row",
        ["product_code"],
        unique=False,
        schema=STAGING_SCHEMA,
    )
    op.create_index(
        "ix_staging_price_row_raw_document_id",
        "price_row",
        ["raw_document_id"],
        unique=False,
        schema=STAGING_SCHEMA,
    )

    op.create_table(
        "price_history_row",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_document_id", sa.Integer(), nullable=False),
        sa.Column("product_code", sa.String(length=64), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", row_status_enum, server_default="VALID", nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=STAGING_SCHEMA,
    )
    op.create_index(
        "ix_price_history_row_product_code",
        "price_history_row",
        ["product_code"],
        unique=False,
        schema=STAGING_SCHEMA,
    )
    op.create_index(
        "ix_staging_price_history_row_raw_document_id",
        "price_history_row",
        ["raw_document_id"],
        unique=False,
        schema=STAGING_SCHEMA,
    )

    op.create_table(
        "resolution_rule",
        sa.Column("rule_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("matcher", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("decision", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "learned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("rule_id"),
        schema=STAGING_SCHEMA,
    )
    op.create_index(
        "ix_staging_resolution_rule_kind",
        "resolution_rule",
        ["kind"],
        unique=False,
        schema=STAGING_SCHEMA,
    )

    # --- core: the canonical model ------------------------------------

    op.create_table(
        "product",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("status", product_status_enum, server_default="ACTIVE", nullable=False),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("registered_by_rule_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=CORE_SCHEMA,
    )
    op.create_index("ix_core_product_code", "product", ["code"], unique=True, schema=CORE_SCHEMA)

    op.create_table(
        "product_price",
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="ARS", nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_price", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("is_highlighted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_stale", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], [f"{CORE_SCHEMA}.product.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("product_id"),
        schema=CORE_SCHEMA,
    )

    op.create_table(
        "price_point",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=True),
        sa.Column("source", price_source_enum, server_default="SYSTEM", nullable=False),
        sa.ForeignKeyConstraint(["product_id"], [f"{CORE_SCHEMA}.product.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # RF-40 lives here: importing a published history twice collides against
        # this and leaves one point, without a `SELECT` first.
        sa.UniqueConstraint("product_id", "changed_at", name="uq_price_point_product_changed"),
        schema=CORE_SCHEMA,
    )
    op.create_index(
        "ix_core_price_point_product_id",
        "price_point",
        ["product_id"],
        unique=False,
        schema=CORE_SCHEMA,
    )
    op.create_index(
        "ix_price_point_product_changed",
        "price_point",
        ["product_id", "changed_at"],
        unique=False,
        schema=CORE_SCHEMA,
    )

    op.create_table(
        "catalog_setting",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key"),
        schema=CORE_SCHEMA,
    )

    # --- operations: the review queue and what it taught --------------

    op.create_table(
        "exception",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", case_status_enum, server_default="PENDING", nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=True),
        sa.Column("occurrences", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("decision", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("resolved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=OPERATIONS_SCHEMA,
    )
    op.create_index(
        "ix_operations_exception_fingerprint",
        "exception",
        ["fingerprint"],
        unique=False,
        schema=OPERATIONS_SCHEMA,
    )
    op.create_index(
        "ix_operations_exception_batch_id",
        "exception",
        ["batch_id"],
        unique=False,
        schema=OPERATIONS_SCHEMA,
    )
    op.create_index(
        "ix_exception_status_kind",
        "exception",
        ["status", "kind"],
        unique=False,
        schema=OPERATIONS_SCHEMA,
    )
    # RF-35, decided by the database: while a case is pending, the same case
    # cannot be opened twice. A `SELECT` before the insert would race.
    op.create_index(
        "uq_exception_pending_fingerprint",
        "exception",
        ["fingerprint"],
        unique=True,
        schema=OPERATIONS_SCHEMA,
        postgresql_where=sa.text("status = 'PENDING'"),
    )

    op.create_table(
        "resolution_rule",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("matcher", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("decision", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revoked_by_user_id", sa.Integer(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=OPERATIONS_SCHEMA,
    )
    op.create_index(
        "ix_operations_resolution_rule_kind",
        "resolution_rule",
        ["kind"],
        unique=False,
        schema=OPERATIONS_SCHEMA,
    )

    # --- the values the platform starts with (RF-20) ------------------

    for key, value, description in INITIAL_PARAMETERS:
        op.execute(
            sa.text(
                f'INSERT INTO "{OPERATIONS_SCHEMA}".parameter (key, value, description) '
                "VALUES (:key, CAST(:value AS jsonb), :description) "
                "ON CONFLICT (key) DO NOTHING"
            ).bindparams(key=key, value=value, description=description)
        )


def downgrade() -> None:
    op.execute(
        sa.text(f'DELETE FROM "{OPERATIONS_SCHEMA}".parameter WHERE key = ANY(:keys)').bindparams(
            keys=[key for key, _, _ in INITIAL_PARAMETERS]
        )
    )

    op.drop_index(
        "ix_operations_resolution_rule_kind",
        table_name="resolution_rule",
        schema=OPERATIONS_SCHEMA,
    )
    op.drop_table("resolution_rule", schema=OPERATIONS_SCHEMA)

    op.drop_index(
        "uq_exception_pending_fingerprint",
        table_name="exception",
        schema=OPERATIONS_SCHEMA,
        postgresql_where=sa.text("status = 'PENDING'"),
    )
    op.drop_index("ix_exception_status_kind", table_name="exception", schema=OPERATIONS_SCHEMA)
    op.drop_index(
        "ix_operations_exception_batch_id", table_name="exception", schema=OPERATIONS_SCHEMA
    )
    op.drop_index(
        "ix_operations_exception_fingerprint", table_name="exception", schema=OPERATIONS_SCHEMA
    )
    op.drop_table("exception", schema=OPERATIONS_SCHEMA)

    op.drop_table("catalog_setting", schema=CORE_SCHEMA)
    op.drop_index("ix_price_point_product_changed", table_name="price_point", schema=CORE_SCHEMA)
    op.drop_index("ix_core_price_point_product_id", table_name="price_point", schema=CORE_SCHEMA)
    op.drop_table("price_point", schema=CORE_SCHEMA)
    op.drop_table("product_price", schema=CORE_SCHEMA)
    op.drop_index("ix_core_product_code", table_name="product", schema=CORE_SCHEMA)
    op.drop_table("product", schema=CORE_SCHEMA)

    op.drop_index(
        "ix_staging_resolution_rule_kind", table_name="resolution_rule", schema=STAGING_SCHEMA
    )
    op.drop_table("resolution_rule", schema=STAGING_SCHEMA)
    op.drop_index(
        "ix_staging_price_history_row_raw_document_id",
        table_name="price_history_row",
        schema=STAGING_SCHEMA,
    )
    op.drop_index(
        "ix_price_history_row_product_code",
        table_name="price_history_row",
        schema=STAGING_SCHEMA,
    )
    op.drop_table("price_history_row", schema=STAGING_SCHEMA)
    op.drop_index(
        "ix_staging_price_row_raw_document_id", table_name="price_row", schema=STAGING_SCHEMA
    )
    op.drop_index("ix_price_row_product_code", table_name="price_row", schema=STAGING_SCHEMA)
    op.drop_index("ix_price_row_batch_status", table_name="price_row", schema=STAGING_SCHEMA)
    op.drop_table("price_row", schema=STAGING_SCHEMA)
    op.execute(f'DROP SEQUENCE IF EXISTS "{STAGING_SCHEMA}".price_batch_seq')

    # `raw` is immutable, and dropping the table is not a correction of what it
    # holds: it is the whole feature being rolled back.
    op.drop_index("ix_raw_portal_document_section", table_name="portal_document", schema=RAW_SCHEMA)
    op.drop_index(
        "ix_raw_portal_document_content_hash", table_name="portal_document", schema=RAW_SCHEMA
    )
    op.drop_table("portal_document", schema=RAW_SCHEMA)

    bind = op.get_bind()
    case_status_enum.drop(bind, checkfirst=True)
    price_source_enum.drop(bind, checkfirst=True)
    product_status_enum.drop(bind, checkfirst=True)
    row_status_enum.drop(bind, checkfirst=True)
