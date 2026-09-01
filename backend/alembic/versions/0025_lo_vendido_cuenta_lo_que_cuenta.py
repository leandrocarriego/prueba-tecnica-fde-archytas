"""Lo vendido por rubro se rehace contando sólo lo que cuenta

`core.sale_revenue` se llenó escuchando `SalesNormalized`, que dice qué **se
pudo leer**. No es lo mismo que qué **cuenta**: una venta cuyo total se aleja de
lo habitual para su producto, y una repetida con datos distintos, se leen
enteras y quedan apartadas igual. Así la proyección contaba noventa y seis
ventas mientras la pantalla de ventas contaba noventa y una — dos números
distintos sobre la misma plata.

Desde ahora la alimenta `SalesCounted`, que lo publica el módulo dueño del
veredicto y lleva las dos mitades: lo que empieza a contar y lo que dejó de
contar. Pero la tabla ya tiene adentro las cinco que sobran, y no se van solas:
nunca estuvieron en «lo que cuenta», así que ninguna baja las nombra.

Se vacía entera y se reconstruye. Es una proyección: su verdad está en
`core.sale`, y volver a leer el documento la escribe de nuevo. Al mismo tiempo
se borran las ventas que nadie decidió y se le saca la marca de leído al
documento, de modo que el lote se interprete una vez, completo, con la lógica
corregida — en lugar de quedar con las cuatro filas repetidas que dejó la
lectura anterior.

Como en 0024: **sólo lo que nadie decidió**. Y `normalized_at` es la única
columna de `raw` que se puede tocar, porque es contabilidad del pipeline y no el
contenido extraído (Artículo III).

Revision ID: 0025
Revises: 0024
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DELETE FROM core.sale_revenue")
    op.execute("DELETE FROM core.sale WHERE resolved_by_user_id IS NULL")
    op.execute("UPDATE raw.portal_document SET normalized_at = NULL WHERE section = 'sales'")


def downgrade() -> None:
    # Nada que deshacer: lo que esto borra es una proyección y un lote que se
    # reconstruyen leyendo el portal, que es de donde salieron.
    pass
