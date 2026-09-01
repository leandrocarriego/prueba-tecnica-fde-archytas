"""Gasto por rubro: la proyección que suma lo que se compró

La otra mitad de P7. Los rubros ya se unifican (008); faltaba lo que el cliente
pidió con sus palabras: **cuánto se gastó en cada uno**. El dato existe —las
órdenes de compra traen el producto y el monto de cada línea—, pero los montos
son de `purchases` y `catalog` no lee su tabla (Artículo IV). Así que `catalog`
guarda su propia proyección, alimentada por el evento `PurchaseOrdersNormalized`:
una fila por línea de orden, con el producto y el monto.

El rubro no se guarda acá: sale de unir `product_code` contra el `product` de
este módulo al leer, de modo que una línea cuyo producto todavía no tiene rubro
—o cuyo código no matchea ningún producto— es gasto «sin rubro», que es
exactamente los «pedazos sueltos» que el cliente describe. Nada se estima:
cada monto es uno que el portal imprimió en una orden.

Se llena hacia adelante: las órdenes que ya estaban tipadas antes de esta tabla
no dispararon el evento y quedan afuera hasta que se vuelvan a leer. Repartir un
total sin ese dato sería inventarlo (Artículo II).

Revision ID: 0021
Revises: 0020
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "order_spend",
        # La clave es la fila de staging que originó la línea: leer la misma
        # orden dos veces deja el mismo total. La proyección es idempotente,
        # como las tareas que la alimentan.
        sa.Column("staging_row_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("product_code", sa.String(length=64), nullable=True),
        sa.Column("amount", sa.Numeric(14, 4), nullable=False),
        sa.PrimaryKeyConstraint("staging_row_id"),
        schema="core",
    )
    op.create_index("ix_order_spend_product_code", "order_spend", ["product_code"], schema="core")


def downgrade() -> None:
    op.drop_index("ix_order_spend_product_code", table_name="order_spend", schema="core")
    op.drop_table("order_spend", schema="core")
