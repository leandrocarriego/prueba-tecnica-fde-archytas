"""Los mensajes de la bandeja y las ventas del tablero

Las tablas de `007` (la bandeja) y `009` (las ventas), más las dos proyecciones
que hacen que ninguno de los dos módulos tenga que importar a nadie:

- `core.messaging_supplier` — el padrón, como lo necesita leer `messaging` para
  identificar quién manda un mensaje. Lo alimenta el mismo evento que alimenta a
  `purchases`, así que los dos aciertan sin conocerse.
- `core.sales_product` — los códigos de producto que conoce el catálogo, que es
  lo que le permite a `sales` contestar "ese producto no existe" (RF-20 de 009)
  sin leer la tabla de otro módulo.

Revision ID: 0012
Revises: 0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

CORE = "core"

# The types this migration creates. Dropped by name on the way down: a table
# that goes away does not take its enum with it.
NEW_TYPES: tuple[str, ...] = ("message_kind", "message_state", "sale_state")

# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the inbox, the sales and the two projections they read."""
    op.create_table(
        "messaging_supplier",
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("name_key", sa.String(length=255), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("legal_name"),
        schema="core",
    )
    op.create_index(
        op.f("ix_core_messaging_supplier_name_key"),
        "messaging_supplier",
        ["name_key"],
        unique=False,
        schema="core",
    )
    op.create_table(
        "sale",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("code_key", sa.String(length=64), nullable=False),
        sa.Column("sold_on", sa.Date(), nullable=True),
        sa.Column("product_code", sa.String(length=64), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("total", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column(
            "state",
            sa.Enum("COUNTED", "HELD", "DISCARDED", name="sale_state", schema="core"),
            server_default="COUNTED",
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("portal_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_estimated", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("duplicate_of_sale_id", sa.Integer(), nullable=True),
        sa.Column("decision", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("resolved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("staging_row_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="core",
    )
    op.create_index("ix_sale_code_key", "sale", ["code_key"], unique=False, schema="core")
    op.create_index("ix_sale_sold_on", "sale", ["sold_on"], unique=False, schema="core")
    op.create_index("ix_sale_state", "sale", ["state"], unique=False, schema="core")
    op.create_table(
        "sales_product",
        sa.Column("product_code", sa.String(length=64), nullable=False),
        sa.Column(
            "known_since",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("product_code"),
        schema="core",
    )
    op.create_table(
        "sales_setting",
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
        "supplier_message",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=160), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sender_text", sa.String(length=255), nullable=False),
        sa.Column("supplier_name", sa.String(length=255), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "PAYMENT_CLAIM",
                "DUE_SOON",
                "LOW_STOCK",
                "UNCLASSIFIED",
                name="message_kind",
                schema="core",
            ),
            server_default="UNCLASSIFIED",
            nullable=False,
        ),
        sa.Column("kind_text", sa.String(length=100), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column(
            "state",
            sa.Enum("PENDING", "RESOLVED", name="message_state", schema="core"),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("assignee_user_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("resolved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("alerted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("alert_failure", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
        schema="core",
    )
    op.create_index(
        op.f("ix_core_supplier_message_supplier_name"),
        "supplier_message",
        ["supplier_name"],
        unique=False,
        schema="core",
    )
    op.create_index(
        "ix_supplier_message_received_at",
        "supplier_message",
        ["received_at"],
        unique=False,
        schema="core",
    )
    op.create_index(
        "ix_supplier_message_state_kind",
        "supplier_message",
        ["state", "kind"],
        unique=False,
        schema="core",
    )


def downgrade() -> None:
    """Undo the tables, and then the types they were the only users of."""
    op.drop_index("ix_supplier_message_state_kind", table_name="supplier_message", schema="core")
    op.drop_index("ix_supplier_message_received_at", table_name="supplier_message", schema="core")
    op.drop_index(
        op.f("ix_core_supplier_message_supplier_name"), table_name="supplier_message", schema="core"
    )
    op.drop_table("supplier_message", schema="core")
    op.drop_table("sales_setting", schema="core")
    op.drop_table("sales_product", schema="core")
    op.drop_index("ix_sale_state", table_name="sale", schema="core")
    op.drop_index("ix_sale_sold_on", table_name="sale", schema="core")
    op.drop_index("ix_sale_code_key", table_name="sale", schema="core")
    op.drop_table("sale", schema="core")
    op.drop_index(
        op.f("ix_core_messaging_supplier_name_key"), table_name="messaging_supplier", schema="core"
    )
    op.drop_table("messaging_supplier", schema="core")

    for name in NEW_TYPES:
        postgresql.ENUM(name=name, schema=CORE).drop(op.get_bind(), checkfirst=True)
