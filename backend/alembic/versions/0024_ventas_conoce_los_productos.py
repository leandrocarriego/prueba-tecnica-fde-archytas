"""Ventas conoce los productos del catálogo, y relee lo que juzgó sin conocerlos

`core.sales_product` es la proyección con la que `sales` contesta «¿este
producto existe?» sin importar `catalog` (Artículo IV). Se alimenta del evento
`ProductsRegistered`, que el catálogo publica **cuando empieza a conocer un
producto**.

Los cien productos entraron el 2026-08-29, con la primera lista. La proyección
quedó en cero, y nadie lo notó porque hasta hoy no había llegado ni una venta:
el parser pedía columnas que la pantalla del portal no publica. La primera
lectura que funcionó apartó **noventa y seis ventas de noventa y seis** con el
motivo «la venta apunta a un producto que no existe», sobre productos que están
todos en el catálogo.

Esta migración hace dos cosas, y la segunda es la que no se puede omitir.

**Llena la proyección con lo que el catálogo ya sabe.** Hacia adelante se
alimenta sola: un producto nuevo publica su evento y `sales` lo escucha. Lo que
faltaba era el arranque, y un `INSERT ... SELECT` es exactamente eso. Es
idempotente por la clave primaria.

**Y deja que se vuelvan a leer las ventas que se juzgaron sin ella.** No alcanza
con llenar la tabla: los registros ya están guardados con un veredicto que se
tomó con la proyección vacía, y volver a leer el portal no los revisa —los
encontraría repetidos y los descartaría—. Así que se borran los que ese defecto
produjo y se le saca la marca de leído al documento, para que el pipeline lo
vuelva a interpretar. Es lo que el Artículo III promete: el estado se
reconstruye desde el origen sin volver a extraer.

Se borra **sólo lo que nadie decidió** (`resolved_by_user_id IS NULL`). Una
venta sobre la que alguien ya se pronunció es una decisión humana, y una
migración no la pisa: si quedara alguna, se queda donde está y su caso también.

`normalized_at` es la única columna de `raw` que se puede tocar, y el Artículo
III lo dice con todas las letras: es contabilidad propia del pipeline —«ya leí
esto»—, no el contenido extraído. El documento, su hash y su momento quedan
intactos.

Revision ID: 0024
Revises: 0023
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# El motivo, tal como `sales/service.py` lo escribe. Va literal porque una
# migración no importa código de la aplicación —el código cambia y la migración
# ya corrió—, y es el mismo criterio con el que 0010 escribe `unknown_category`.
UNKNOWN_PRODUCT = "La venta apunta a un producto que no existe"


def upgrade() -> None:
    op.execute(
        "INSERT INTO core.sales_product (product_code) "
        "SELECT code FROM core.product "
        "ON CONFLICT (product_code) DO NOTHING"
    )
    # Lo que produjo el defecto: apartado por un producto que sí existe. Se
    # borra el registro y su proyección de ventas por rubro, que se reescribe
    # sola en la próxima lectura.
    op.execute(
        "DELETE FROM core.sale_revenue WHERE staging_row_id IN ("
        f"  SELECT staging_row_id FROM core.sale WHERE reason = '{UNKNOWN_PRODUCT}'"
        "   AND resolved_by_user_id IS NULL AND staging_row_id IS NOT NULL)"
    )
    op.execute(
        f"DELETE FROM core.sale WHERE reason = '{UNKNOWN_PRODUCT}' AND resolved_by_user_id IS NULL"
    )
    # Y que se vuelva a leer. El contenido no se toca: sólo la marca de que el
    # pipeline ya pasó por él.
    op.execute("UPDATE raw.portal_document SET normalized_at = NULL WHERE section = 'sales'")


def downgrade() -> None:
    # La proyección se vacía; lo demás no se deshace. Las ventas borradas se
    # reconstruyen leyendo el portal, que es de dónde salieron, y volver a
    # marcar documentos como leídos sería afirmar algo que no pasó.
    op.execute("DELETE FROM core.sales_product")
