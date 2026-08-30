"""Los rubros del catálogo, con el acuerdo firmado ya cargado

Tres tablas nuevas en `core` —el rubro, la equivalencia y la foto diaria del
stock—, seis columnas en `core.product`, una en `staging.price_row` y tres
cambios en `operations.resolution_rule`.

**Por qué la siembra.** Sin ella la primera corrida mandaría los cien productos
a revisión, que es exactamente lo que la spec promete evitar. Sembrar no es que
el sistema decida: es cargar el acuerdo que el cliente firmó.

Cada forma escrita se siembra **dos veces**: como regla en
`operations.resolution_rule` y como fila en `core.category_alias` que la
proyecta. Así no hay dos clases de equivalencia —una corregible y otra no— y
RF-28 a RF-31 alcanzan por igual a lo sembrado y a lo aprendido.

**Once filas para dieciocho formas escritas, y no dieciocho.** La tabla firmada
lista dieciocho grafías; la clave de matcheo es el texto con los espacios
colapsados y en `casefold`, así que `ELECTRICIDAD` y `Electricidad` **son la
misma clave** —que es justamente lo que la normalización tiene que colapsar—.
Las dieciocho grafías quedan cubiertas por once equivalencias distintas, y las
que difieren en algo más que mayúsculas —`Ferreteria Gral.`,
`Pinturas/Adhesivos`, `Seg. Industrial`, `Herram.`— siguen siendo filas propias
apuntando al mismo rubro. `data-model.md` dice "18 filas" y se contradice con su
propia regla de normalización dos párrafos antes; gana la regla, y la corrección
del documento queda anotada en el traspaso.

`created_by_user_id` pasa a nulo para que la siembra pueda decir la verdad: una
equivalencia que vino con el sistema **no la decidió nadie**, y atribuírsela al
dueño sería mentir en un registro de auditoría.

Revision ID: 0010
Revises: 0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE = "core"
STAGING = "staging"
OPERATIONS = "operations"

UNKNOWN_CATEGORY = "unknown_category"

# `create_type=False` so `create_table` does not try to create the type a
# second time: it is created once, explicitly, at the top of `upgrade`.
ALIAS_SOURCE = postgresql.ENUM(
    "SEED", "LEARNED", name="alias_source", schema=CORE, create_type=False
)
ALIAS_SOURCE_TYPE = postgresql.ENUM("SEED", "LEARNED", name="alias_source", schema=CORE)

# The table the client signed, rubro by rubro and written form by written form.
SEED: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Electricidad", ("ELECTRICIDAD", "Electricidad")),
    ("Ferretería General", ("FERRETERIA GENERAL", "Ferreteria General", "Ferreteria Gral.")),
    ("Herramientas", ("HERRAMIENTAS", "Herramientas", "Herram.")),
    ("Instrumental", ("INSTRUMENTAL", "Instrumental")),
    (
        "Pinturas y Adhesivos",
        ("PINTURAS Y ADHESIVOS", "Pinturas y Adhesivos", "Pinturas/Adhesivos"),
    ),
    ("Sanitarios", ("SANITARIOS", "Sanitarios")),
    (
        "Seguridad Industrial",
        ("SEGURIDAD INDUSTRIAL", "Seguridad Industrial", "Seg. Industrial"),
    ),
)


def _key(value: str) -> str:
    """The matching key: trim, collapse inner whitespace, casefold. Nothing else.

    Deliberately the same three steps as `app.shared.text.collapse_written_form`,
    written out here rather than imported: a migration is a historical record
    and must keep meaning what it meant even if that function is changed later.
    """
    return " ".join(value.split()).casefold()


def upgrade() -> None:
    """Create the rubros, seed the signed agreement, and let a rule be re-pointed."""
    ALIAS_SOURCE_TYPE.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "category",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        schema=CORE,
    )
    op.create_table(
        "category_alias",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("text_normalized", sa.String(length=200), nullable=False, unique=True),
        sa.Column("text_original", sa.String(length=200), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=True),
        sa.Column("source", ALIAS_SOURCE, server_default="LEARNED", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["category_id"], [f"{CORE}.category.id"], ondelete="RESTRICT"),
        schema=CORE,
    )
    op.create_index(
        "ix_core_category_alias_category_id", "category_alias", ["category_id"], schema=CORE
    )
    op.create_index("ix_core_category_alias_rule_id", "category_alias", ["rule_id"], schema=CORE)

    op.create_table(
        "stock_point",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], [f"{CORE}.product.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("product_id", "observed_on", name="uq_stock_point_product_day"),
        schema=CORE,
    )
    op.create_index("ix_core_stock_point_product_id", "stock_point", ["product_id"], schema=CORE)
    op.create_index("ix_stock_point_observed_on", "stock_point", ["observed_on"], schema=CORE)

    op.add_column("product", sa.Column("category_id", sa.Integer(), nullable=True), schema=CORE)
    op.create_foreign_key(
        "fk_product_category_id",
        "product",
        "category",
        ["category_id"],
        ["id"],
        source_schema=CORE,
        referent_schema=CORE,
        ondelete="RESTRICT",
    )
    op.create_index("ix_core_product_category_id", "product", ["category_id"], schema=CORE)
    op.add_column(
        "product", sa.Column("category_raw", sa.String(length=200), nullable=True), schema=CORE
    )
    op.add_column(
        "product", sa.Column("subcategory_raw", sa.String(length=200), nullable=True), schema=CORE
    )
    op.create_index("ix_core_product_subcategory_raw", "product", ["subcategory_raw"], schema=CORE)
    op.add_column(
        "product", sa.Column("classified_by_user_id", sa.Integer(), nullable=True), schema=CORE
    )
    op.add_column(
        "product",
        sa.Column("classified_at", sa.DateTime(timezone=True), nullable=True),
        schema=CORE,
    )
    op.add_column(
        "product", sa.Column("classified_by_rule_id", sa.Integer(), nullable=True), schema=CORE
    )
    op.create_index(
        "ix_core_product_classified_by_rule_id", "product", ["classified_by_rule_id"], schema=CORE
    )

    op.add_column("price_row", sa.Column("stock", sa.Integer(), nullable=True), schema=STAGING)

    op.alter_column(
        "resolution_rule",
        "created_by_user_id",
        existing_type=sa.Integer(),
        nullable=True,
        schema=OPERATIONS,
    )
    op.add_column(
        "resolution_rule",
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        schema=OPERATIONS,
    )
    op.add_column(
        "resolution_rule",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        schema=OPERATIONS,
    )

    _seed(op.get_bind())


def _seed(connection: sa.Connection) -> None:
    """Load the signed table: seven rubros, and the equivalences that reach them."""
    for name, written_forms in SEED:
        category_id = connection.execute(
            sa.text(f"INSERT INTO {CORE}.category (name) VALUES (:name) RETURNING id"),
            {"name": name},
        ).scalar_one()

        seen: set[str] = set()
        for form in written_forms:
            key = _key(form)
            if key in seen:
                # Two written forms that differ only in case are one
                # equivalence. Inserting the second would collide with the
                # unique key, and it would be the same decision twice.
                continue
            seen.add(key)
            rule_id = connection.execute(
                sa.text(
                    f"INSERT INTO {OPERATIONS}.resolution_rule "
                    "(kind, matcher, decision, created_by_user_id, created_by_name) "
                    "VALUES (:kind, CAST(:matcher AS jsonb), CAST(:decision AS jsonb), "
                    "NULL, :author) RETURNING id"
                ),
                {
                    "kind": UNKNOWN_CATEGORY,
                    "matcher": f'{{"kind": "{UNKNOWN_CATEGORY}", "category_text": "{form}"}}',
                    "decision": f'{{"category_id": {category_id}}}',
                    # Read on the screen as what it is: it came with the system,
                    # from a table the client signed, and nobody decided it here.
                    "author": "Sembrado en la puesta en marcha",
                },
            ).scalar_one()
            connection.execute(
                sa.text(
                    f"INSERT INTO {CORE}.category_alias "
                    "(category_id, text_normalized, text_original, rule_id, source) "
                    "VALUES (:category_id, :key, :original, :rule_id, 'SEED')"
                ),
                {
                    "category_id": category_id,
                    "key": key,
                    "original": form,
                    "rule_id": rule_id,
                },
            )


def downgrade() -> None:
    """Undo the tables, the columns and the seed, in the order that respects the keys."""
    op.execute(f"DELETE FROM {OPERATIONS}.resolution_rule WHERE kind = '{UNKNOWN_CATEGORY}'")
    op.drop_column("resolution_rule", "updated_at", schema=OPERATIONS)
    op.drop_column("resolution_rule", "updated_by_user_id", schema=OPERATIONS)
    op.alter_column(
        "resolution_rule",
        "created_by_user_id",
        existing_type=sa.Integer(),
        nullable=False,
        schema=OPERATIONS,
    )

    op.drop_column("price_row", "stock", schema=STAGING)

    for index in (
        "ix_core_product_classified_by_rule_id",
        "ix_core_product_subcategory_raw",
        "ix_core_product_category_id",
    ):
        op.drop_index(index, table_name="product", schema=CORE)
    op.drop_constraint("fk_product_category_id", "product", schema=CORE, type_="foreignkey")
    for column in (
        "classified_by_rule_id",
        "classified_at",
        "classified_by_user_id",
        "subcategory_raw",
        "category_raw",
        "category_id",
    ):
        op.drop_column("product", column, schema=CORE)

    op.drop_table("stock_point", schema=CORE)
    op.drop_table("category_alias", schema=CORE)
    op.drop_table("category", schema=CORE)
    ALIAS_SOURCE_TYPE.drop(op.get_bind(), checkfirst=True)
