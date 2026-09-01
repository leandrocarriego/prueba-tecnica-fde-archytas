"""Lo que `triage` lee de los parámetros

Una tabla de una fila, y existe por el Artículo IV.

RF-18 de la 011 deja que el dueño decida a partir de cuántos días un pendiente
queda señalado como demorado, y ese valor vive en `operations.parameter`, que es
de `operations`. `triage` no puede leer la tabla de otro módulo, así que se
queda con **su propia proyección** del único parámetro que consume, alimentada
por `BusinessParameterChanged`. Es exactamente la forma que ya tienen
`core.sales_setting` y `core.purchase_setting`: no se inventa nada acá, se
repite el patrón que la constitución obligó a inventar la primera vez.

Una fila sola no justifica una tabla, dice la intuición. La alternativa sí que
no se justifica: leer `operations.parameter` desde `triage` es el import cruzado
que rompe el build, y pasar el número por la ruta lo convertiría en algo que el
que llama puede mentir.

Mientras nadie toque el parámetro la tabla está vacía y el valor es el inicial
del catálogo —siete días, RF-19—, así que no hay backfill: no existe un valor
anterior que preservar.

Revision ID: 0019
Revises: 0018
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "triage_setting",
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
    op.drop_table("triage_setting", schema="operations")
