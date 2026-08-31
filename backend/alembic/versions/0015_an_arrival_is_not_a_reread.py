"""De qué lote vino cada factura la última vez

Una columna, y existe para que `arrival_count` diga lo que RF-39 firmó.

La pantalla de facturas se relee dos veces por día y se **renormaliza entera**
en cuanto cambia su hash —un proveedor que paga una factura reescribe una celda
y arrastra las otras noventa y nueve—, así que «la volvimos a ver» era el caso
normal y no decía nada. Contando cada encuentro, todas las facturas «llegaban»
dos veces por día para siempre.

Con `last_batch_id`, un arribo es el portal publicando la factura **dos veces en
la misma lectura**: dos filas, una página, un lote. Encontrarla en un lote
posterior es la misma fila leída otra vez y no suma.

Las facturas que ya están registradas quedan con la columna en `NULL`, que es lo
correcto: no sabemos de qué lote vinieron, y hasta la próxima lectura ninguna
suma nada. Sus `arrival_count` inflados **no se corrigen hacia atrás** — nadie
sabe cuál era el número verdadero, y escribir uno inventado sería exactamente lo
que el Artículo II prohíbe.

Revision ID: 0015
Revises: 0014
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remember which reading last brought each invoice."""
    op.add_column(
        "invoice",
        sa.Column("last_batch_id", sa.Integer(), nullable=True),
        schema="core",
    )


def downgrade() -> None:
    """Give the column back."""
    op.drop_column("invoice", "last_batch_id", schema="core")
