"""Quién recibe cada aviso, en qué número, y dentro de qué franja

Tres tablas chicas en `operations`, y las tres existen por la misma frontera: un
aviso tiene que llegarle a una persona, a su teléfono, según su rol — y los tres
datos son de `identity`, cuyas tablas este módulo no puede leer (Artículo IV).

La consecuencia buena es que **RF-45 de 007 no es una regla que alguien tenga
que recordar**: cuando alguien pierde el acceso, `identity` publica
`UserDeactivated` y el destinatario queda inactivo. No hay un paso que se pueda
olvidar.

`notification_route` no se siembra: los valores iniciales firmados —los reclamos
y los vencimientos a compras, el resumen diario al dueño— viven en el código,
como todo valor inicial de la plataforma, así que una instalación nueva se
comporta como una configurada sin que haya que cargar nada.

Revision ID: 0013
Revises: 0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the recipients, the routing and the settings this module reads."""
    op.create_table(
        "notification_recipient",
        sa.Column("user_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id"),
        schema="operations",
    )
    op.create_index(
        op.f("ix_operations_notification_recipient_role"),
        "notification_recipient",
        ["role"],
        unique=False,
        schema="operations",
    )
    op.create_table(
        "notification_route",
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("kind"),
        schema="operations",
    )
    op.create_table(
        "notification_setting",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key"),
        schema="operations",
    )


def downgrade() -> None:
    """Drop the three tables. No type of its own to drop with them."""
    op.drop_table("notification_setting", schema="operations")
    op.drop_table("notification_route", schema="operations")
    op.drop_index(
        op.f("ix_operations_notification_recipient_role"),
        table_name="notification_recipient",
        schema="operations",
    )
    op.drop_table("notification_recipient", schema="operations")
