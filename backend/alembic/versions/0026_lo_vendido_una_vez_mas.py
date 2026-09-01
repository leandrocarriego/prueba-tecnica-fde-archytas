"""Lo vendido se rehace una vez más, con el alta y la baja ya disjuntas

`SalesCounted` viajaba con una venta en sus dos listas a la vez: el mismo lote la
contó y después la apartó, porque más abajo llegó su repetida. Quien lo recibe
aplica el alta y la baja en algún orden, y el orden decidía el total — la
proyección quedó con una fila y $334.774 de más frente a lo que la pantalla de
ventas cuenta.

Ya no puede pasar: el módulo que publica el hecho saca de las altas lo que está
en las bajas, así que las dos listas son disjuntas por construcción.

Falta rehacer lo que quedó mal escrito, y es lo mismo que 0025: vaciar la
proyección, borrar las ventas que nadie decidió y sacarle al documento la marca
de leído, para que el lote se interprete de nuevo, completo.

Revision ID: 0026
Revises: 0025
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DELETE FROM core.sale_revenue")
    op.execute("DELETE FROM core.sale WHERE resolved_by_user_id IS NULL")
    op.execute("UPDATE raw.portal_document SET normalized_at = NULL WHERE section = 'sales'")


def downgrade() -> None:
    # Nada que deshacer: es una proyección y un lote que se reconstruyen leyendo
    # el portal, que es de donde salieron.
    pass
