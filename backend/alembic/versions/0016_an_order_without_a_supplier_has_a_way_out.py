"""Por qué quedó apartada una orden, y quién la resolvió

Tres columnas y un índice, y son la H8 entera de la 007 del lado de la base.

Una orden cuyo proveedor no se pudo identificar **ya se apartaba** —eso es
RF-08 y estaba construido— y después no había salida: ninguna ruta para
resolverla, ningún conteo, ningún filtro, y ningún lugar donde guardar quién la
resolvió. La H8 se firmó el 2026-08-31 con trece requisitos, y once no tenían
dónde apoyarse sin esto.

`review_reason` es el que importa entender. `resolve_supplier` ya distingue dos
cosas muy distintas —«el nombre no alcanza para desambiguar» y «este proveedor
**no está en el padrón**»— y `register_orders` recibía las dos y las tiraba:
`supplier, _ = await self.resolve_supplier(...)`. RF-55 pide justamente el
segundo motivo con todas las letras, porque de él depende que nadie intente dar
de alta un proveedor desde la revisión.

**Las órdenes que ya están apartadas quedan con `review_reason` en `NULL`, y no
hay backfill posible**: el motivo nunca se guardó, y reconstruirlo exigiría
volver a leer el portal. Inventar uno sería exactamente lo que el Artículo II
prohíbe. La pantalla las muestra «sin identificar» sin motivo, que es lo que de
verdad se sabe de ellas.

El índice sobre `review_state` es por donde filtra RF-52.

Revision ID: 0016
Revises: 0015
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE = "core"
TABLE = "purchase_order"


def upgrade() -> None:
    """Give a held order a reason, an author and a date."""
    op.add_column(
        TABLE,
        sa.Column("review_reason", sa.String(length=200), nullable=True),
        schema=CORE,
    )
    op.add_column(
        TABLE,
        sa.Column("resolved_by_user_id", sa.Integer(), nullable=True),
        schema=CORE,
    )
    op.add_column(
        TABLE,
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        schema=CORE,
    )
    op.create_index(
        "ix_purchase_order_review_state", TABLE, ["review_state"], unique=False, schema=CORE
    )


def downgrade() -> None:
    """Take them away again."""
    op.drop_index("ix_purchase_order_review_state", table_name=TABLE, schema=CORE)
    op.drop_column(TABLE, "resolved_at", schema=CORE)
    op.drop_column(TABLE, "resolved_by_user_id", schema=CORE)
    op.drop_column(TABLE, "review_reason", schema=CORE)
