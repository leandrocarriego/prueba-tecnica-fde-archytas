"""Facturas, proveedores, pagos, recibos, calendario y órdenes de compra

Todo lo que las specs 004, 005, 006 y 007 necesitan del negocio, más las siete
tablas de `staging` donde primero aterriza lo que se pudo leer de cada pantalla
nueva del portal.

**Lo que hay que mirar dos veces son tres índices únicos parciales**, porque
cada uno es una regla del negocio decidida por la base y no por el código:

- `uq_invoice_supplier_number` — el duplicado es *(proveedor, número)*, y sólo
  alcanza a las facturas con proveedor identificado: mientras el proveedor no
  está resuelto, una factura no puede ser duplicada de nadie (RF-40 de 004).
- `uq_receipt_in_force` — un recibo vigente por factura. Una factura puede tener
  varios a lo largo de su vida y uno solo que cuente (RF-35, RF-50 de 005).
- `uq_receipt_incident_open` — un incidente abierto por factura, así abrirlo dos
  veces no depende de que el código se acuerde de chequear (RF-37 de 005).

Dos tipos enum **se reusan y no se vuelven a crear**: `correction_status`, que
`core.correction` ya declaró sin esquema justamente para que un segundo módulo
lo comparta, y `staging.row_status`, que las siete tablas nuevas de `staging`
usan igual que `price_row`.

Revision ID: 0011
Revises: 0010
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

CORE = "core"
STAGING = "staging"

# Created in 0007 without a schema, so a second module in another schema reuses
# it. Declared here with `create_type=False` for the same reason.
CORRECTION_STATUS = postgresql.ENUM(
    "ACTIVE", "CONFLICTED", "REVERTED", name="correction_status", create_type=False
)
# Created in 0001 for `staging.price_row`; the seven new tables of `staging` are
# the same pipeline and use the same two states.
ROW_STATUS = postgresql.ENUM(
    "VALID", "QUARANTINED", name="row_status", schema=STAGING, create_type=False
)

# The types this migration does create. Dropped by name on the way down: a
# table that goes away does not take its enum with it.
NEW_TYPES: tuple[tuple[str, str], ...] = (
    ("supplier_alias_source", CORE),
    ("invoice_review_state", CORE),
    ("order_review_state", CORE),
    ("payment_origin", CORE),
    ("payment_state", CORE),
    ("due_date_origin", CORE),
)

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the business model of purchases and the staging it is fed from."""
    op.create_table(
        "purchase_correction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column("field", sa.String(length=100), nullable=False),
        sa.Column("portal_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("corrected_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason_code", sa.String(length=50), nullable=False),
        sa.Column("reason_detail", sa.Text(), nullable=True),
        sa.Column("corrected_by_user_id", sa.Integer(), nullable=False),
        sa.Column("corrected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", CORRECTION_STATUS, server_default="ACTIVE", nullable=False),
        sa.Column("conflict_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("conflict_detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reverted_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="core",
    )
    op.create_index(
        "uq_purchase_correction_in_force",
        "purchase_correction",
        ["entity_type", "entity_id", "field"],
        unique=True,
        schema="core",
        postgresql_where=sa.text("status <> 'REVERTED'"),
    )
    op.create_table(
        "purchase_setting",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key"),
        schema="core",
    )
    op.create_table(
        "supplier",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("tax_id", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("payment_term_days", sa.Integer(), nullable=True),
        sa.Column("balance", sa.Numeric(precision=14, scale=4), nullable=True),
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
        sa.UniqueConstraint("legal_name"),
        sa.UniqueConstraint("tax_id"),
        schema="core",
    )
    op.create_index(
        "ix_supplier_legal_name", "supplier", ["legal_name"], unique=False, schema="core"
    )
    op.create_table(
        "invoice_file_read",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_document_id", sa.Integer(), nullable=False),
        sa.Column("invoice_number", sa.String(length=64), nullable=False),
        sa.Column("readable", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("agrees", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("number", sa.String(length=64), nullable=True),
        sa.Column("issued_on", sa.Date(), nullable=True),
        sa.Column("total", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("supplier_text", sa.String(length=255), nullable=True),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="staging",
    )
    op.create_index(
        "ix_invoice_file_read_number",
        "invoice_file_read",
        ["invoice_number"],
        unique=False,
        schema="staging",
    )
    op.create_index(
        op.f("ix_staging_invoice_file_read_raw_document_id"),
        "invoice_file_read",
        ["raw_document_id"],
        unique=False,
        schema="staging",
    )
    op.create_table(
        "invoice_row",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_document_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(length=64), nullable=True),
        sa.Column("supplier_text", sa.String(length=255), nullable=True),
        sa.Column("issued_on", sa.Date(), nullable=True),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("total", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("paid", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("balance", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("receipt_issued", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("portal_payment_status", sa.String(length=50), nullable=True),
        sa.Column("file_kind", sa.String(length=50), nullable=True),
        sa.Column("product_code", sa.String(length=64), nullable=True),
        sa.Column("status", ROW_STATUS, server_default="VALID", nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="staging",
    )
    op.create_index(
        "ix_invoice_row_batch_status",
        "invoice_row",
        ["batch_id", "status"],
        unique=False,
        schema="staging",
    )
    op.create_index(
        "ix_invoice_row_number", "invoice_row", ["number"], unique=False, schema="staging"
    )
    op.create_index(
        op.f("ix_staging_invoice_row_raw_document_id"),
        "invoice_row",
        ["raw_document_id"],
        unique=False,
        schema="staging",
    )
    op.create_table(
        "message_row",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_document_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sender_text", sa.String(length=255), nullable=True),
        sa.Column("kind_text", sa.String(length=100), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("already_read", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("status", ROW_STATUS, server_default="VALID", nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="staging",
    )
    op.create_index(
        "ix_message_row_batch_status",
        "message_row",
        ["batch_id", "status"],
        unique=False,
        schema="staging",
    )
    op.create_index(
        op.f("ix_staging_message_row_external_id"),
        "message_row",
        ["external_id"],
        unique=False,
        schema="staging",
    )
    op.create_index(
        op.f("ix_staging_message_row_raw_document_id"),
        "message_row",
        ["raw_document_id"],
        unique=False,
        schema="staging",
    )
    op.create_table(
        "payment_row",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_document_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("supplier_text", sa.String(length=255), nullable=True),
        sa.Column("reference", sa.String(length=255), nullable=True),
        sa.Column("paid_on", sa.Date(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("status", ROW_STATUS, server_default="VALID", nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="staging",
    )
    op.create_index(
        "ix_payment_row_batch_status",
        "payment_row",
        ["batch_id", "status"],
        unique=False,
        schema="staging",
    )
    op.create_index(
        op.f("ix_staging_payment_row_external_id"),
        "payment_row",
        ["external_id"],
        unique=False,
        schema="staging",
    )
    op.create_index(
        op.f("ix_staging_payment_row_raw_document_id"),
        "payment_row",
        ["raw_document_id"],
        unique=False,
        schema="staging",
    )
    op.create_table(
        "purchase_order_row",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_document_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(length=64), nullable=True),
        sa.Column("ordered_on", sa.Date(), nullable=True),
        sa.Column("supplier_text", sa.String(length=255), nullable=True),
        sa.Column("product_code", sa.String(length=64), nullable=True),
        sa.Column("product_text", sa.String(length=500), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("status_text", sa.String(length=100), nullable=True),
        sa.Column("status", ROW_STATUS, server_default="VALID", nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="staging",
    )
    op.create_index(
        "ix_purchase_order_row_batch_status",
        "purchase_order_row",
        ["batch_id", "status"],
        unique=False,
        schema="staging",
    )
    op.create_index(
        op.f("ix_staging_purchase_order_row_raw_document_id"),
        "purchase_order_row",
        ["raw_document_id"],
        unique=False,
        schema="staging",
    )
    op.create_table(
        "sale_row",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_document_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("code_key", sa.String(length=64), nullable=True),
        sa.Column("sold_on", sa.Date(), nullable=True),
        sa.Column("product_code", sa.String(length=64), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("total", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("status", ROW_STATUS, server_default="VALID", nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="staging",
    )
    op.create_index(
        "ix_sale_row_batch_status",
        "sale_row",
        ["batch_id", "status"],
        unique=False,
        schema="staging",
    )
    op.create_index(
        "ix_sale_row_code_key", "sale_row", ["code_key"], unique=False, schema="staging"
    )
    op.create_index(
        op.f("ix_staging_sale_row_raw_document_id"),
        "sale_row",
        ["raw_document_id"],
        unique=False,
        schema="staging",
    )
    op.create_table(
        "supplier_row",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_document_id", sa.Integer(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=True),
        sa.Column("tax_id", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("payment_term_days", sa.Integer(), nullable=True),
        sa.Column("balance", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("status", ROW_STATUS, server_default="VALID", nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="staging",
    )
    op.create_index(
        op.f("ix_staging_supplier_row_raw_document_id"),
        "supplier_row",
        ["raw_document_id"],
        unique=False,
        schema="staging",
    )
    op.create_table(
        "invoice",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(length=64), nullable=False),
        sa.Column("issued_on", sa.Date(), nullable=False),
        sa.Column("total", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("supplier_text", sa.String(length=255), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("original_due_on", sa.Date(), nullable=True),
        sa.Column("portal_paid", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("portal_payment_status", sa.String(length=50), nullable=True),
        sa.Column("portal_receipt_issued", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("file_kind", sa.String(length=50), nullable=True),
        sa.Column("product_code", sa.String(length=64), nullable=True),
        sa.Column(
            "review_state",
            sa.Enum("OK", "PENDING", "RESOLVED", name="invoice_review_state", schema="core"),
            server_default="OK",
            nullable=False,
        ),
        sa.Column("review_reason", sa.String(length=200), nullable=True),
        sa.Column("resolved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_alias_id", sa.Integer(), nullable=True),
        sa.Column("arrival_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("staging_row_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["supplier_id"], ["core.supplier.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        schema="core",
    )
    op.create_index(
        op.f("ix_core_invoice_due_on"), "invoice", ["due_on"], unique=False, schema="core"
    )
    op.create_index(
        op.f("ix_core_invoice_resolved_by_alias_id"),
        "invoice",
        ["resolved_by_alias_id"],
        unique=False,
        schema="core",
    )
    op.create_index(
        op.f("ix_core_invoice_supplier_id"), "invoice", ["supplier_id"], unique=False, schema="core"
    )
    op.create_index("ix_invoice_issued_on", "invoice", ["issued_on"], unique=False, schema="core")
    op.create_index("ix_invoice_number", "invoice", ["number"], unique=False, schema="core")
    op.create_index(
        "ix_invoice_review_state", "invoice", ["review_state"], unique=False, schema="core"
    )
    op.create_index(
        "uq_invoice_supplier_number",
        "invoice",
        ["supplier_id", "number"],
        unique=True,
        schema="core",
        postgresql_where=sa.text("supplier_id IS NOT NULL"),
    )
    op.create_table(
        "purchase_order",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(length=64), nullable=False),
        sa.Column("ordered_on", sa.Date(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("supplier_text", sa.String(length=255), nullable=False),
        sa.Column("product_code", sa.String(length=64), nullable=True),
        sa.Column("product_text", sa.String(length=500), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("status_text", sa.String(length=100), nullable=False),
        sa.Column("status_since", sa.Date(), nullable=False),
        sa.Column("observed_from_start", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "review_state",
            sa.Enum("OK", "PENDING", "RESOLVED", name="order_review_state", schema="core"),
            server_default="OK",
            nullable=False,
        ),
        sa.Column("repeat_of_order_id", sa.Integer(), nullable=True),
        sa.Column("repeat_dismissed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("repeat_dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["supplier_id"], ["core.supplier.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("number", name="uq_purchase_order_number"),
        schema="core",
    )
    op.create_index(
        "ix_purchase_order_status", "purchase_order", ["status_text"], unique=False, schema="core"
    )
    op.create_index(
        "ix_purchase_order_supplier", "purchase_order", ["supplier_id"], unique=False, schema="core"
    )
    op.create_table(
        "supplier_alias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("text_normalized", sa.String(length=255), nullable=False),
        sa.Column("text_original", sa.String(length=255), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=True),
        sa.Column(
            "source",
            sa.Enum("OBSERVED", "LEARNED", name="supplier_alias_source", schema="core"),
            server_default="LEARNED",
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["supplier_id"], ["core.supplier.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("text_normalized"),
        schema="core",
    )
    op.create_index(
        op.f("ix_core_supplier_alias_rule_id"),
        "supplier_alias",
        ["rule_id"],
        unique=False,
        schema="core",
    )
    op.create_index(
        op.f("ix_core_supplier_alias_supplier_id"),
        "supplier_alias",
        ["supplier_id"],
        unique=False,
        schema="core",
    )
    op.create_table(
        "due_date",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("on_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("invoice_id", sa.Integer(), nullable=True),
        sa.Column(
            "origin",
            sa.Enum("INVOICE", "MANUAL", name="due_date_origin", schema="core"),
            server_default="MANUAL",
            nullable=False,
        ),
        sa.Column("original_date", sa.Date(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["invoice_id"], ["core.invoice.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="core",
    )
    op.create_index("ix_due_date_on_date", "due_date", ["on_date"], unique=False, schema="core")
    op.create_index(
        "uq_due_date_invoice",
        "due_date",
        ["invoice_id"],
        unique=True,
        schema="core",
        postgresql_where=sa.text("invoice_id IS NOT NULL"),
    )
    op.create_table(
        "invoice_document",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("raw_document_id", sa.Integer(), nullable=True),
        sa.Column("readable", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("agrees", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("read_number", sa.String(length=64), nullable=True),
        sa.Column("read_issued_on", sa.Date(), nullable=True),
        sa.Column("read_total", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("read_supplier_text", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["invoice_id"], ["core.invoice.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_id"),
        schema="core",
    )
    op.create_table(
        "payment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("invoice_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.Column(
            "origin",
            sa.Enum("PORTAL", "MANUAL", name="payment_origin", schema="core"),
            server_default="PORTAL",
            nullable=False,
        ),
        sa.Column(
            "state",
            sa.Enum("IMPUTED", "PENDING", "VOIDED", name="payment_state", schema="core"),
            server_default="IMPUTED",
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=160), nullable=True),
        sa.Column("reference", sa.String(length=255), nullable=True),
        sa.Column("supplier_text", sa.String(length=255), nullable=True),
        sa.Column("review_reason", sa.String(length=200), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("voided_by_user_id", sa.Integer(), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["core.invoice.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supplier_id"], ["core.supplier.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id", name="uq_payment_external_id"),
        schema="core",
    )
    op.create_index("ix_payment_invoice_id", "payment", ["invoice_id"], unique=False, schema="core")
    op.create_index("ix_payment_state", "payment", ["state"], unique=False, schema="core")
    op.create_table(
        "receipt",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(length=32), nullable=False),
        sa.Column("issued_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "issued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("document", sa.Text(), nullable=True),
        sa.Column("voided_by_user_id", sa.Integer(), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["core.invoice.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("number", name="uq_receipt_number"),
        schema="core",
    )
    op.create_index(
        op.f("ix_core_receipt_invoice_id"), "receipt", ["invoice_id"], unique=False, schema="core"
    )
    op.create_index(
        "uq_receipt_in_force",
        "receipt",
        ["invoice_id"],
        unique=True,
        schema="core",
        postgresql_where=sa.text("voided_at IS NULL"),
    )
    op.create_table(
        "receipt_incident",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("opened_on", sa.Date(), nullable=False),
        sa.Column("closed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["core.invoice.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="core",
    )
    op.create_index(
        op.f("ix_core_receipt_incident_invoice_id"),
        "receipt_incident",
        ["invoice_id"],
        unique=False,
        schema="core",
    )
    op.create_index(
        "uq_receipt_incident_open",
        "receipt_incident",
        ["invoice_id"],
        unique=True,
        schema="core",
        postgresql_where=sa.text("closed_at IS NULL"),
    )
    op.create_table(
        "due_date_change",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("due_date_id", sa.Integer(), nullable=False),
        sa.Column("previous_date", sa.Date(), nullable=False),
        sa.Column("new_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["due_date_id"], ["core.due_date.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="core",
    )
    op.create_index(
        op.f("ix_core_due_date_change_due_date_id"),
        "due_date_change",
        ["due_date_id"],
        unique=False,
        schema="core",
    )


def downgrade() -> None:
    """Undo the tables, and then the types they were the only users of."""
    op.drop_index(
        op.f("ix_core_due_date_change_due_date_id"), table_name="due_date_change", schema="core"
    )
    op.drop_table("due_date_change", schema="core")
    op.drop_index(
        "uq_receipt_incident_open",
        table_name="receipt_incident",
        schema="core",
        postgresql_where=sa.text("closed_at IS NULL"),
    )
    op.drop_index(
        op.f("ix_core_receipt_incident_invoice_id"), table_name="receipt_incident", schema="core"
    )
    op.drop_table("receipt_incident", schema="core")
    op.drop_index(
        "uq_receipt_in_force",
        table_name="receipt",
        schema="core",
        postgresql_where=sa.text("voided_at IS NULL"),
    )
    op.drop_index(op.f("ix_core_receipt_invoice_id"), table_name="receipt", schema="core")
    op.drop_table("receipt", schema="core")
    op.drop_index("ix_payment_state", table_name="payment", schema="core")
    op.drop_index("ix_payment_invoice_id", table_name="payment", schema="core")
    op.drop_table("payment", schema="core")
    op.drop_table("invoice_document", schema="core")
    op.drop_index(
        "uq_due_date_invoice",
        table_name="due_date",
        schema="core",
        postgresql_where=sa.text("invoice_id IS NOT NULL"),
    )
    op.drop_index("ix_due_date_on_date", table_name="due_date", schema="core")
    op.drop_table("due_date", schema="core")
    op.drop_index(
        op.f("ix_core_supplier_alias_supplier_id"), table_name="supplier_alias", schema="core"
    )
    op.drop_index(
        op.f("ix_core_supplier_alias_rule_id"), table_name="supplier_alias", schema="core"
    )
    op.drop_table("supplier_alias", schema="core")
    op.drop_index("ix_purchase_order_supplier", table_name="purchase_order", schema="core")
    op.drop_index("ix_purchase_order_status", table_name="purchase_order", schema="core")
    op.drop_table("purchase_order", schema="core")
    op.drop_index(
        "uq_invoice_supplier_number",
        table_name="invoice",
        schema="core",
        postgresql_where=sa.text("supplier_id IS NOT NULL"),
    )
    op.drop_index("ix_invoice_review_state", table_name="invoice", schema="core")
    op.drop_index("ix_invoice_number", table_name="invoice", schema="core")
    op.drop_index("ix_invoice_issued_on", table_name="invoice", schema="core")
    op.drop_index(op.f("ix_core_invoice_supplier_id"), table_name="invoice", schema="core")
    op.drop_index(op.f("ix_core_invoice_resolved_by_alias_id"), table_name="invoice", schema="core")
    op.drop_index(op.f("ix_core_invoice_due_on"), table_name="invoice", schema="core")
    op.drop_table("invoice", schema="core")
    op.drop_index(
        op.f("ix_staging_supplier_row_raw_document_id"), table_name="supplier_row", schema="staging"
    )
    op.drop_table("supplier_row", schema="staging")
    op.drop_index(
        op.f("ix_staging_sale_row_raw_document_id"), table_name="sale_row", schema="staging"
    )
    op.drop_index("ix_sale_row_code_key", table_name="sale_row", schema="staging")
    op.drop_index("ix_sale_row_batch_status", table_name="sale_row", schema="staging")
    op.drop_table("sale_row", schema="staging")
    op.drop_index(
        op.f("ix_staging_purchase_order_row_raw_document_id"),
        table_name="purchase_order_row",
        schema="staging",
    )
    op.drop_index(
        "ix_purchase_order_row_batch_status", table_name="purchase_order_row", schema="staging"
    )
    op.drop_table("purchase_order_row", schema="staging")
    op.drop_index(
        op.f("ix_staging_payment_row_raw_document_id"), table_name="payment_row", schema="staging"
    )
    op.drop_index(
        op.f("ix_staging_payment_row_external_id"), table_name="payment_row", schema="staging"
    )
    op.drop_index("ix_payment_row_batch_status", table_name="payment_row", schema="staging")
    op.drop_table("payment_row", schema="staging")
    op.drop_index(
        op.f("ix_staging_message_row_raw_document_id"), table_name="message_row", schema="staging"
    )
    op.drop_index(
        op.f("ix_staging_message_row_external_id"), table_name="message_row", schema="staging"
    )
    op.drop_index("ix_message_row_batch_status", table_name="message_row", schema="staging")
    op.drop_table("message_row", schema="staging")
    op.drop_index(
        op.f("ix_staging_invoice_row_raw_document_id"), table_name="invoice_row", schema="staging"
    )
    op.drop_index("ix_invoice_row_number", table_name="invoice_row", schema="staging")
    op.drop_index("ix_invoice_row_batch_status", table_name="invoice_row", schema="staging")
    op.drop_table("invoice_row", schema="staging")
    op.drop_index(
        op.f("ix_staging_invoice_file_read_raw_document_id"),
        table_name="invoice_file_read",
        schema="staging",
    )
    op.drop_index("ix_invoice_file_read_number", table_name="invoice_file_read", schema="staging")
    op.drop_table("invoice_file_read", schema="staging")
    op.drop_index("ix_supplier_legal_name", table_name="supplier", schema="core")
    op.drop_table("supplier", schema="core")
    op.drop_table("purchase_setting", schema="core")
    op.drop_index(
        "uq_purchase_correction_in_force",
        table_name="purchase_correction",
        schema="core",
        postgresql_where=sa.text("status <> 'REVERTED'"),
    )
    op.drop_table("purchase_correction", schema="core")

    for name, schema in NEW_TYPES:
        postgresql.ENUM(name=name, schema=schema).drop(op.get_bind(), checkfirst=True)
