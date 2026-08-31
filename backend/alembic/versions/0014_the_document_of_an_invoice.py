"""El archivo de la factura, y el CUIT que a veces trae impreso

Cinco columnas, y las cinco cierran requisitos firmados de la 004 que hasta
ahora no tenían dónde vivir.

`core.invoice_document.content` y `content_type` son **RF-04**: el archivo tal
como llegó, para poder abrirlo desde la factura. Es una copia deliberada de lo
que ya está en `raw.portal_document`, y no un atajo: `raw` es de `portal`, y
`purchases` no puede leer las tablas de otro módulo (Artículo IV). Lo que la
constitución prescribe para este caso exacto es que el módulo que necesita el
dato mantenga su propia proyección alimentada por eventos, y eso es esta
columna. `raw` sigue siendo la evidencia y sigue sin tocarse (Artículo III).

`read_supplier_tax_id` —acá y en `staging.invoice_file_read`— es **RF-11**: el
CUIT del emisor cuando el documento imprime uno que no es el de Cordillera. El
lector descarta el del cliente por la línea en la que está escrito, y el
servicio sólo identifica si el número coincide con uno de los ocho del padrón.

Nada se rellena hacia atrás. Un documento leído antes de esta migración no tiene
sus bytes guardados, y `GET /invoices/{id}/file` contesta que todavía no está en
lugar de servir un archivo vacío: la factura vuelve a bajar su archivo la próxima
vez que el portal se relee.

Revision ID: 0014
Revises: 0013
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Keep the file of an invoice, and the tax id its document printed."""
    op.add_column(
        "invoice_file_read",
        sa.Column("supplier_tax_id", sa.String(length=20), nullable=True),
        schema="staging",
    )
    op.add_column(
        "invoice_document",
        sa.Column("read_supplier_tax_id", sa.String(length=20), nullable=True),
        schema="core",
    )
    op.add_column(
        "invoice_document",
        sa.Column("content", sa.LargeBinary(), nullable=True),
        schema="core",
    )
    op.add_column(
        "invoice_document",
        sa.Column("content_type", sa.String(length=120), nullable=True),
        schema="core",
    )


def downgrade() -> None:
    """Give back the four columns."""
    op.drop_column("invoice_document", "content_type", schema="core")
    op.drop_column("invoice_document", "content", schema="core")
    op.drop_column("invoice_document", "read_supplier_tax_id", schema="core")
    op.drop_column("invoice_file_read", "supplier_tax_id", schema="staging")
