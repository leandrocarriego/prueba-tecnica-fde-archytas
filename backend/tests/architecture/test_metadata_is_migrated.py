"""Lo que el metadata declara, alguna migración lo crea.

**Por qué existe este archivo.** `staging.document_batch_seq` vivió meses
declarada en `ingestion/models.py` y en ninguna migración. En desarrollo y en
esta suite las tablas se crean con `create_all` desde el metadata, así que la
secuencia existía y **todo pasaba en verde**; en producción sólo corren las
migraciones, así que no existía, y la primera línea de cada normalización
—`next_batch_id()`— moría con `UndefinedTableError`. Cinco secciones del portal
dejaron su documento en `raw` durante meses sin llegar nunca a `staging`.

**Lo que no lo atrapó, y es lo importante.** `alembic check` corre en CI y decía
`No new upgrade operations detected`: autogenerate compara tablas y columnas, y
una `Sequence` declarada suelta queda fuera de esa comparación. Un chequeo verde
que no mira lo que se rompió es peor que no tenerlo, porque además tranquiliza.

La regla es de texto sobre los archivos de migración, como el resto de este
paquete, y por el mismo motivo: es estática, y montar una base para probarla
costaría más que la regla.
"""

import re
from pathlib import Path

import pytest

import app
from app.database import Base

REPOSITORY_ROOT = Path(app.__file__).resolve().parents[1]
VERSIONS = REPOSITORY_ROOT / "alembic" / "versions"


def migrations() -> str:
    """Every migration of the project, as one string."""
    files = sorted(VERSIONS.glob("[0-9]*.py"))
    assert files, f"no migrations under {VERSIONS}: this rule would pass over nothing"
    return "\n".join(path.read_text(encoding="utf-8") for path in files)


def declared_sequences() -> list[str]:
    """The sequences the models declare, by name."""
    return sorted(sequence.name for sequence in Base.metadata._sequences.values())


@pytest.mark.unit
class TestEverySequenceHasItsMigration:
    """`DB-01`: un modelo sin su migración es un despliegue roto que pasa los tests."""

    def test_there_are_sequences_to_check(self) -> None:
        """Si el metadata deja de declarar secuencias, esta regla queda ciega y lo dice."""
        assert declared_sequences(), (
            "el metadata no declara ninguna secuencia: o se movieron, o esta regla "
            "dejó de mirar donde están."
        )

    @pytest.mark.parametrize("name", declared_sequences())
    def test_some_migration_creates_it(self, name: str) -> None:
        """Declararla en el metadata la crea en los tests, no en producción."""
        written = migrations()
        created = re.search(rf"\b{re.escape(name)}\b", written)
        assert created, (
            f"`{name}` está declarada en el metadata y ninguna migración la crea. "
            "En esta suite la crea `create_all` y todo pasa; en producción sólo "
            "corren las migraciones, así que no va a existir."
        )
