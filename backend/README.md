# Backend — Plataforma Cordillera

API FastAPI construida como **monolito modular**: cada módulo de dominio es autocontenido y
**nunca importa otro módulo** — se comunican publicando eventos de dominio en
`app/shared/events`. La única excepción es `dependencies.py`, que es autorización HTTP.
Lo verifica `tests/architecture/test_module_boundaries.py`.

La arquitectura completa está en [`../ARCHITECTURE.md`](../ARCHITECTURE.md); las reglas
operativas, en [`../AGENTS.md`](../AGENTS.md).

## Estructura

```
app/
├── main.py            Composition root: registra los routers y mapea los errores de dominio
├── config.py          Settings (pydantic-settings), lee el .env de la raíz del repositorio
├── database.py        Engine y sesión async (SQLAlchemy 2.0 + asyncpg)
├── logging.py         Logging estructurado
├── models.py          Registro de modelos para el mapper y para el autogenerate de Alembic
├── shared/            Kernel transversal: errores, repositorio base, normalización
│   └── events/        El bus y el catálogo de eventos de dominio
├── worker/            Celery: aplicación, scheduler y el puente async
└── modules/           Módulos de dominio
    └── <module>/      routes · schemas · service · repository · models · tasks · handlers
```

## Módulos de dominio

El mapa completo de los once módulos está en [`../ARCHITECTURE.md`](../ARCHITECTURE.md). Hoy
existen dos:

| Módulo | Responsabilidad |
|---|---|
| `identity` | Usuarios, roles y sesión (RBAC) |
| `operations` | Jobs, parámetros configurables y auditoría |

Los otros nueve —`portal`, `ingestion`, `suppliers`, `catalog`, `purchasing`, `billing`, `sales`,
`messaging`, `triage`— todavía no están construidos.

## Puesta en marcha

La versión de Python está fijada en `.python-version`, y `uv sync` se la trae sola. No es un
detalle de gusto: sin ese archivo `uv` elegía lo que encontrara —3.14 en una máquina, 3.12 en
CI— y la cobertura salía distinta en cada lado sobre el mismo código. Un build que no es
reproducible no es verificable (Artículo IX).

```bash
# Dependencias (uv es el único gestor soportado)
uv sync

# Navegador para la extracción del portal (una sola vez)
uv run playwright install chromium

# La infraestructura corre en Docker desde la raíz del repo
cd .. && make dev && cd backend

# Migraciones
uv run alembic upgrade head

# Servidor de desarrollo
uv run uvicorn app.main:app --reload
```

La API queda en http://localhost:8000 y la documentación interactiva en
http://localhost:8000/docs.

## Tests

```bash
uv run pytest                              # todos
uv run pytest tests/unit                   # solo unitarios (rápidos)
uv run pytest --cov=app --cov-report=html  # con coverage
```

Los parsers del portal se testean contra **HTML fijado** (fixtures), nunca contra SIGProv en
vivo: los tests tienen que ser reproducibles y no depender de un sistema de terceros.

## Calidad

```bash
uv run ruff format app tests       # formatear
uv run ruff check --fix app tests  # lintear
uv run mypy app                    # tipos
```

Ruff es formateador y linter a la vez: reemplaza a Black y a isort, que ya no son dependencias
del proyecto.

## Migraciones

```bash
uv run alembic revision --autogenerate -m "descripcion"
uv run alembic upgrade head
```

Los esquemas del pipeline de datos (`raw`, `staging`, `core`, `operations`) los crea `alembic/env.py` antes
de configurar el contexto de migración: la tabla de versión de Alembic vive en un esquema que la
primera migración todavía no habría creado, así que el orden importa.

## Dependencias

```bash
uv add <paquete>          # agregar
uv add --dev <paquete>    # agregar de desarrollo
uv lock                   # actualizar el lockfile
```

Nunca editar a mano las dependencias de `pyproject.toml` ni usar `pip install` o
`requirements.txt`.
