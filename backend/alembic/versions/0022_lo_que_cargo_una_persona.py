"""De dónde salió una factura o una orden: del portal, o de una persona

Hasta acá una fila que el portal publicaba rota sólo se podía dar por revisada:
quedaba contada y visible, y el dato no entraba nunca. Cargarla a mano es la
otra mitad del Artículo II —el sistema avisa **y** deja arreglarlo—, y trae una
obligación que es de esta migración: un dato que escribió una persona no se
puede mostrar como algo que publicó el portal (Artículo I).

Por eso la columna, y no una inferencia. «Sin batch» parecía alcanzar para
deducirlo, y no alcanza: la primera vez que el portal publica esa misma fila ya
legible, el batch se escribe y el hecho de que alguien la había reconstruido se
pierde — justo en el momento en que hace falta saberlo para no terminar con dos
facturas donde hay una.

Los pagos y los vencimientos ya trazaban esta misma línea (`payment_origin`,
`due_date_origin`). Este es el mismo tipo, compartido por las dos tablas que lo
necesitan ahora.

Revision ID: 0022
Revises: 0021
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ORIGIN = sa.Enum("PORTAL", "MANUAL", name="record_origin", schema="core")


def upgrade() -> None:
    """Add `origin` to invoices and orders, with everything existing as PORTAL."""
    ORIGIN.create(op.get_bind(), checkfirst=True)
    for table in ("invoice", "purchase_order"):
        op.add_column(
            table,
            sa.Column(
                "origin",
                ORIGIN,
                nullable=False,
                server_default="PORTAL",
            ),
            schema="core",
        )
        # Lo que el portal publicó y una persona rechazó, para no volver a
        # preguntar lo mismo cada doce horas.
        op.add_column(
            table,
            sa.Column("rejected_portal_values", postgresql.JSONB(), nullable=True),
            schema="core",
        )


def downgrade() -> None:
    """Drop the column and the type, in that order."""
    for table in ("invoice", "purchase_order"):
        op.drop_column(table, "rejected_portal_values", schema="core")
        op.drop_column(table, "origin", schema="core")
    ORIGIN.drop(op.get_bind(), checkfirst=True)
