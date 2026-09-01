"""De qué área es cada pendiente

Una columna y un índice, y son RF-12 entero: hasta acá la cola de revisión
sabía **qué** no había podido resolverse y no sabía **de quién** era. Con una
sola pantalla para los siete orígenes —lo que la 011 decidió— eso deja de ser
un detalle: sin el área, Marcela ve los precios de Julián y Julián ve los pagos
de Marcela.

El área se **guarda**, no se deduce al leer. Un `dict[kind, section]` en el
servicio ahorraría esta migración y pondría la respuesta lejos de quien la
sabe: el que abre el caso es el único que conoce de dónde vino, y el día que un
`kind` cambie de dueño —que ya pasó con los rubros en la 010— la cola mostraría
el caso a la persona equivocada sin que nada falle.

El backfill enumera los **siete** `kind` que existen hoy, uno por uno y sin
default, y los siete son de compras.

Que den todos lo mismo no es una simplificación ni un descuido: los siete nacen
de la ingesta del portal, y resolver lo que la ingesta aparta es trabajo de
compras. Los de precios incluidos — el brief lo dice con las palabras del
cliente, que sobre los precios de lista Marcela *«sí puede pedir la lista sin
esperar al próximo ciclo y resolver lo que el sistema haya apartado»*—, y
`unknown_category` porque la 010 puso los rubros de ese lado y
`catalog/service.py::CATEGORY_SECTION` ya lo dice así. El primer `kind` de
ventas lo trae esta misma feature (`unreadable_sale_row`), y no aparece acá
porque nunca abrió un caso: no hay nada histórico que reubicar.

El mapa se escribe entero igual, con las siete filas y sin `DEFAULT`. Un
`section = 'PURCHASING'` para todos daría hoy el mismo resultado y sería una
trampa: el día que un `kind` nuevo entre sin pasar por acá, el default lo
archivaría bajo compras sin que nada falle, y un pendiente archivado bajo un
área inventada es un pendiente que no está en la lista de nadie.

**Un `kind` fuera de esa lista hace fallar la migración a propósito.** Un
`DEFAULT` que absorbiera lo desconocido archivaría un caso bajo un área
inventada, que es la forma más silenciosa de perderlo: seguiría existiendo en
la tabla y no estaría en la lista de nadie. Es el Artículo II aplicado a la
migración misma.

El tipo `operations.section` ya existe —lo usa `operations.manual_change`— así
que se reutiliza con `create_type=False`. Un segundo tipo con el mismo
vocabulario sería dos verdades sobre las mismas tres áreas.

Revision ID: 0018
Revises: 0017
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The seven kinds the queue can hold before this feature, and the area each one
# belongs to. Enumerated, never defaulted: see the docstring.
SECTION_OF_KIND: dict[str, str] = {
    "unreadable_row": "PURCHASING",
    "unknown_product": "PURCHASING",
    "missing_product": "PURCHASING",
    "unreadable_history": "PURCHASING",
    "unreadable_invoice_row": "PURCHASING",
    "unreadable_order_row": "PURCHASING",
    "unknown_category": "PURCHASING",
}

SECTION = sa.Enum(
    "PURCHASING", "SALES", "SYSTEM", name="section", schema="operations", create_type=False
)


def upgrade() -> None:
    op.add_column("exception", sa.Column("section", SECTION, nullable=True), schema="operations")

    for kind, section in SECTION_OF_KIND.items():
        op.execute(
            sa.text(
                "UPDATE operations.exception SET section = CAST(:section AS operations.section) "
                "WHERE kind = :kind"
            ).bindparams(section=section, kind=kind)
        )

    # Anything still null is a kind this migration does not know about. Failing
    # here is the point: it stops a case from being filed under an area nobody
    # decided, which is how a pending thing disappears without being deleted.
    op.execute(
        sa.text(
            "DO $$ DECLARE orphan text; BEGIN "
            "SELECT string_agg(DISTINCT kind, ', ') INTO orphan "
            "FROM operations.exception WHERE section IS NULL; "
            "IF orphan IS NOT NULL THEN "
            "RAISE EXCEPTION 'Unmapped exception kind(s): %. "
            "Add them to SECTION_OF_KIND in migration 0018.', orphan; "
            "END IF; END $$;"
        )
    )

    op.alter_column("exception", "section", nullable=False, schema="operations")
    op.create_index(
        "ix_exception_section_status",
        "exception",
        ["section", "status"],
        unique=False,
        schema="operations",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_exception_section_status", table_name="exception", schema="operations"
    )
    op.drop_column("exception", "section", schema="operations")
