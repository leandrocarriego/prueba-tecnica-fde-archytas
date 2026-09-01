"""Ventas por rubro: la proyección que suma lo que se vendió

El gemelo exacto de `order_spend` (0021), por el otro lado del negocio, y el
motivo es concreto: el tablero de quien vende mostraba **gasto** por rubro. Una
pantalla que contesta qué se compró, puesta delante de la persona cuyo trabajo
es vender.

No se podía cambiar sin esta tabla. La venta sabe su producto y el producto sabe
su rubro, pero viven en dos módulos que no se leen entre sí (Artículo IV): los
montos son de `sales` (`core.sale`) y el rubro es de `catalog`. Así que
`catalog` guarda su propia proyección, alimentada por `SalesNormalized`.

Igual que en 0021, el rubro no se guarda acá: sale de unir `product_code` contra
el `product` de este módulo al leer, de modo que una venta cuyo producto todavía
no tiene rubro —o cuyo código no matchea ningún producto— es venta «sin rubro».

`sold_on` sí está, y es la diferencia con la tabla gemela: una venta publica su
día y «cuánto vendimos este mes» es la pregunta que se le hace. Una orden de
compra no publica el suyo, y por eso `order_spend` no tiene la columna.

Se llena hacia adelante, como aquélla. En este caso el «hacia adelante» empieza
de cero: hasta hoy el parser de ventas pedía columnas que la pantalla del portal
no publica, así que ninguna venta llegó nunca a `core`.

Revision ID: 0023
Revises: 0022
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sale_revenue",
        # La clave es la fila de staging que originó el registro: leer el mismo
        # día dos veces deja el mismo total.
        sa.Column("staging_row_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("product_code", sa.String(length=64), nullable=True),
        sa.Column("amount", sa.Numeric(14, 4), nullable=False),
        sa.Column("sold_on", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("staging_row_id"),
        schema="core",
    )
    op.create_index("ix_sale_revenue_product_code", "sale_revenue", ["product_code"], schema="core")


def downgrade() -> None:
    op.drop_index("ix_sale_revenue_product_code", table_name="sale_revenue", schema="core")
    op.drop_table("sale_revenue", schema="core")
