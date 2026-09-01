"""De qué lectura salió un comprobante

Una columna, y es la que faltaba de un juego de tres.

`core.invoice` y `core.sale` guardan desde siempre el `staging_row_id` de la
fila que las originó; `core.payment` no, y nadie lo había extrañado. La 011 lo
extraña: cuando el trabajo sobre algo apartado se hace en la pantalla que le
corresponde, esa pantalla tiene que poder decir **qué lectura** resolvió, con la
misma clave con la que la lectura lo había apartado (RF-20). Sin la columna, un
módulo puede anunciar que un comprobante se movió y nada puede decir cuál.

Se llena hacia adelante nada más. Los comprobantes ya registrados no guardaron
de qué fila salieron y reconstruirlo exigiría volver a leer el portal, así que
quedan en `NULL`: inventar una procedencia es exactamente lo que el Artículo II
prohíbe. Un comprobante cargado a mano queda en `NULL` para siempre, y eso no es
un dato faltante — es el dato: vino de una persona y no de una lectura.

Revision ID: 0020
Revises: 0019
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "payment", sa.Column("staging_row_id", sa.Integer(), nullable=True), schema="core"
    )


def downgrade() -> None:
    op.drop_column("payment", "staging_row_id", schema="core")
