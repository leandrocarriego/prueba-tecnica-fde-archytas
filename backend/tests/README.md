# Tests — Plataforma Cordillera (backend)

Suite de la aplicación FastAPI: unitarios, de integración, end-to-end y de
arquitectura. La documentación va en español; **el código de los tests va en
inglés**, como el resto del código (ver `AGENTS.md`).

## Cómo correrlos

```bash
cd backend
uv sync

# Toda la suite (con coverage, según pyproject.toml)
uv run pytest

# Un archivo o un test puntual
uv run pytest tests/unit/shared/test_text.py
uv run pytest tests/integration/api/test_rbac.py -k purchasing

# Por marcador
uv run pytest -m unit            # rápidos, sin base de datos
uv run pytest -m integration
uv run pytest -m e2e
uv run pytest -m "not database"  # todo lo que no necesita Postgres

# Sin coverage (más rápido mientras se escribe)
uv run pytest --no-cov

# Formato y lint de la suite
uv run ruff format tests && uv run ruff check --fix tests
```

**Requisito**: PostgreSQL levantado (`make dev` o `docker compose up -d postgres`).
No hace falta RabbitMQ, ni Celery, ni el portal SIGProv: la suite corre con
SIGProv apagado.

## Base de datos de test

Los tests **nunca** tocan la base de desarrollo.

- `tests/__init__.py` fuerza `POSTGRES_DB=cordillera_test` **antes** de que
  `app.config` lea el entorno (las `Settings` se construyen una sola vez, al
  importar). Se puede cambiar el nombre con `TEST_POSTGRES_DB`.
- `tests/conftest.py` aborta la corrida si el nombre de la base no termina en
  `_test`.
- La base se crea sola si no existe, y el esquema (`raw`, `staging`, `core`, `operations`
  más las tablas de los modelos) se arma una vez por corrida, con
  `Base.metadata`. No se corre Alembic: las migraciones gobiernan el esquema de
  producción, y atarlas a cada corrida haría que un branch a medio migrar
  rompiera la suite.

El resto de la configuración (usuario, clave, host, puerto, `SECRET_KEY`) sale
del `.env` de la raíz del repositorio; si no existe, se usan valores por defecto
apuntados a `localhost:5433`.

## Aislamiento entre tests

Cada test corre dentro de una transacción que **siempre** se revierte:

```
engine  ->  connection  ->  transacción externa (rollback al terminar)
                                `- AsyncSession(join_transaction_mode="create_savepoint")
```

La sesión se engancha a la transacción de la conexión como SAVEPOINT. Así, un
`session.commit()` de un servicio —que los servicios hacen— libera el savepoint
pero nunca llega al commit real: al terminar el test se revierte todo y la base
queda como estaba.

Es la opción más rápida (no se recrea el esquema por test) y la única que
permite testear servicios que commitean. El cliente HTTP comparte esa misma
sesión mediante un override de `get_session`, de modo que lo que escribe un
request lo ve el test que lo hizo, y desaparece con él.

Consecuencia práctica: **los tests son independientes y se pueden correr
aislados o en cualquier orden**. `test_rows_do_not_leak_between_tests`
(`tests/integration/repositories/`) verifica justamente eso.

## Estructura

```
tests/
├── __init__.py                  # bootstrap del entorno (base de test)
├── conftest.py                  # fixtures compartidas
├── factories/                   # datos de prueba (UserFactory)
├── unit/                        # lógica pura, sin base de datos
│   ├── shared/                  # normalización de texto
│   ├── identity/                # hash de claves y JWT
│   └── worker/                  # puente async de Celery
├── integration/                 # base de datos real
│   ├── api/                     # endpoints: health, envelope de errores, RBAC
│   ├── features/                # IdentityService, OperationsService
│   └── repositories/            # BaseRepository async
├── e2e/                         # flujos completos, sólo por HTTP
└── architecture/                # las fronteras, verificadas por test
```

## Fixtures principales (`conftest.py`)

| Fixture | Qué da |
|---|---|
| `session` | `AsyncSession` dentro de la transacción del test |
| `engine`, `connection` | motor sin pool y conexión con la transacción externa |
| `client` | `AsyncClient` de httpx contra la app (`ASGITransport`), sin credenciales |
| `client_for` | fábrica de clientes: `client_for(user)` devuelve uno autenticado |
| `owner`, `purchasing_user`, `sales_user` | un usuario por rol, con clave utilizable |
| `owner_client`, `purchasing_client`, `sales_client` | un cliente autenticado por rol |
| `authorization_header(user)` | el header `Bearer` de un token emitido para ese usuario |

La clave de los usuarios de fixture es `DEFAULT_PASSWORD`
(`tests/factories/user_factory.py`). bcrypt es lento a propósito, así que la
factory cachea el hash por valor de clave: eso mantiene la suite rápida sin
bajar el costo con el que la aplicación se despliega.

## Tests de arquitectura

Son las reglas que sostienen el monolito modular. Están verificadas por test, no
sólo documentadas:

- **`test_module_boundaries.py`** — ningún módulo importa otro módulo (se
  comunican por eventos; la única excepción es `dependencies.py`), y
  `app/shared/` no importa de `app/modules/`. El chequeo es estático (lee los
  imports con `ast`), así que también detecta violaciones en código que todavía
  no ejercita ningún test. Incluye un caso que le da al detector un archivo que
  viola la regla, para que un chequeo que no puede fallar no pase inadvertido.
- **`unit/shared/test_events.py`** — el bus por el que se comunican los módulos.
  Fija las tres propiedades de las que depende la frontera: un handler recibe la
  sesión del publicador, el orden de ejecución es el de registro, y **un handler
  que falla aborta al publicador** (`GEN-09`). Esta última es la que importa:
  ningún import hace falta para perder un evento, alcanza con atrapar la
  excepción y seguir.
- **`test_route_authorization.py`** — ninguna ruta responde sin haber decidido
  quién la llama. Se verifica dos veces: que el árbol de dependencias de la ruta
  declare autenticación (o rol), y que un request anónimo real devuelva 401. Las
  rutas públicas viven en una lista explícita, `PUBLIC_ROUTES`, con el motivo de
  cada una. **Agregar un endpoint sin autorización rompe la suite**; si el
  endpoint tiene que ser público, hay que decirlo ahí.

## Convenciones

- Patrón **AAA** (Arrange / Act / Assert) explícito en cada test.
- Marcadores: `unit`, `integration`, `e2e`, `database`, `slow`, `external`,
  `portal` (definidos en `pyproject.toml`, con `--strict-markers`).
- Los tests async no llevan decorador: `asyncio_mode = "auto"`.
- Los servicios lanzan errores de dominio (`NotFoundError`, `ConflictError`,
  `AuthenticationError`, …). En los tests de servicio se verifica el error de
  dominio; en los de API, el código HTTP y el envelope al que `app/main.py` lo
  mapea.
- Siempre se cubren los casos de error, no sólo el camino feliz.
- Los parsers del portal se testean contra HTML fijado en
  `tests/fixtures/portal/`, **nunca** contra SIGProv en vivo (todavía no hay
  módulo `portal`; cuando lo haya, ahí van).

## Bug conocido, marcado con `xfail`

`tests/unit/shared/test_text.py::test_dotted_legal_suffix_is_dropped` está
marcado `xfail(strict=True)`: `normalize_entity_name` no elimina las formas
societarias escritas con puntos (`S.A.` queda como `s a`), aunque el docstring
del módulo afirma lo contrario. El test queda como está —fallando en rojo si
alguien lo arregla— para que la corrección se note. El detalle está en el
`reason` del marcador.

## Cobertura

`pyproject.toml` exige `--cov-fail-under=80`; la suite está muy por encima
(~98% sobre `app/`). El reporte HTML queda en `htmlcov/`.
