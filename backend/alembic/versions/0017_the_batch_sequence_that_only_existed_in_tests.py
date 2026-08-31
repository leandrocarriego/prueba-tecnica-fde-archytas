"""La secuencia de lote que sólo existía en los tests

Una secuencia, y es la razón por la que **ninguna sección nueva del portal llegó
nunca a `staging` en producción**.

`staging.document_batch_seq` está declarada en el metadata de los modelos
(`ingestion/models.py:164`) y **ninguna migración la creaba**. En desarrollo y en
la suite las tablas se crean desde el metadata con `create_all`, así que la
secuencia existe y todo pasa; en producción sólo corren las migraciones, así que
no existía. La primera línea de cada normalización pide un número de lote, y ahí
moría.

Su hermana `staging.price_batch_seq` **sí** existe: la creó la migración del
camino de precios, que se construyó primero. Por eso la lista de precios anda y
las cinco secciones que vinieron después —facturas, padrón, órdenes, mensajes y
ventas— dejaban su documento en `raw` y no pasaban de ahí.

**Por qué nadie lo vio.** `alembic check` no lo detecta: autogenerate compara
tablas y columnas, y las secuencias declaradas sueltas quedan fuera de su
comparación. El chequeo decía «No new upgrade operations detected» con la
secuencia faltando. Lo cubre desde hoy
`tests/architecture/test_metadata_is_migrated.py`.

`IF NOT EXISTS` porque cualquier base creada desde el metadata —una de
desarrollo, la de la suite— ya la tiene, y esta migración tiene que poder correr
sobre las dos.

Revision ID: 0017
Revises: 0016
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STAGING = "staging"
SEQUENCE = "document_batch_seq"


def upgrade() -> None:
    op.execute(f"CREATE SEQUENCE IF NOT EXISTS {STAGING}.{SEQUENCE}")


def downgrade() -> None:
    op.execute(f"DROP SEQUENCE IF EXISTS {STAGING}.{SEQUENCE}")
