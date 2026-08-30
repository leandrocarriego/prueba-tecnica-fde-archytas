# Convenciones de código — Plataforma Cordillera

Este documento es la **fuente única** de las convenciones de código del proyecto. Lo usan dos
roles, con dos lecturas distintas:

- el **Developer**, mientras escribe: qué se puede y qué no, con el comando que lo verifica antes
  de pedir el review;
- el **Code-Reviewer**, mientras revisa: la lista que recorre entera, citando el identificador de
  cada hallazgo (`"esto viola PY-06"`) en lugar de reescribir la regla.

**Si una convención no está acá, no es una convención del proyecto.** No hay ni debe haber reglas de código en `AGENTS.md`, en `ARCHITECTURE.md`, en los roles ni en las skills: ahí hay punteros a este archivo.

## Cómo leer una entrada

Cada convención tiene tres cosas:

1. **Un identificador estable** (`PY-04`, `TS-02`, `ERR-01`, …). No cambia cuando el documento se
   reordena, y **no se reutiliza** si la convención se elimina (los retirados quedan listados al
   final).
2. **Su severidad**: `Blocker` frena el review; `Major` y `Minor` se anotan y vuelven al rol dueño.
   Un Blocker no se negocia en el review: se arregla o el changeset no pasa.
3. **Su verificación**, cuando existe: el comando que la prueba.

## Convenciones verificadas por un test que rompe el build

Esta es la distinción más importante del documento. Estas cinco convenciones **no dependen de que
alguien las lea**: hay un test que falla, y la suite no pasa.

**Dónde se verifican.** El hook `pytest-fast` del pre-commit corre `tests/unit` y
`tests/architecture`, así que `GEN-02`, `GEN-03`, `GEN-09` y `PY-09` frenan el commit antes de que
salga de la máquina. `TEST-05` mide la suite completa y por eso se verifica en CI
(`.github/workflows/ci.yml`), junto con integración, e2e y `alembic check`.

| Convención | Verificada por | Qué pasa si se viola |
|---|---|---|
| `GEN-02` | `backend/tests/architecture/test_module_boundaries.py::TestModuleBoundaries::test_no_module_imports_another_module` | La suite falla y nombra el archivo y el import. |
| `GEN-03` | `backend/tests/architecture/test_module_boundaries.py::TestModuleBoundaries::test_shared_does_not_import_any_module` | Ídem. |
| `GEN-09` | `backend/tests/unit/shared/test_events.py::TestPublishing::test_a_failing_handler_aborts_the_publisher` | La suite falla si el bus deja de propagar la excepción de un handler. |
| `PY-09` | `backend/tests/architecture/test_route_authorization.py` (`TestRoutesDeclareAuthorization` + `TestRoutesEnforceAuthorization`) | La suite falla por cada endpoint que responde sin decidir quién lo llama. |
| `TEST-05` | `--cov-fail-under=80` en `backend/pyproject.toml` | `pytest` termina en rojo aunque todos los tests pasen. |

Dos detalles que importan al revisarlas:

- `test_module_boundaries.py` es un chequeo **estático** (lee los imports con `ast`), así que
  detecta violaciones en código que todavía no ejercita ningún test. Además se testea a sí mismo
  (`test_the_check_catches_a_real_violation`).

- `test_route_authorization.py` verifica dos cosas distintas: que el árbol de dependencias de la
  ruta **declare** autenticación, y que un request anónimo real **reciba 401**. Una ruta pública
  nueva se agrega a `PUBLIC_ROUTES` con el motivo escrito.

**Todo lo demás depende de que el Developer lo aplique y el Code-Reviewer lo recorra.**

Cuando una convención de esa clase se rompe seguido, la respuesta correcta no es repetirla en otro documento: es escribirle un test o un grep.

## Verificación mecánica (la corrida completa)

```bash
# Backend
cd backend
uv run ruff format --check app tests && uv run ruff check app tests   # GEN-01, PY-08
uv run mypy app                                                       # PY-10
uv run pytest                                                         # GEN-02, GEN-03, PY-09, TEST-*

# Frontend
cd frontend
npx tsc --noEmit        # TS-01  (equivale a `npm run type-check`)
npm run lint            # TS-02, TS-06
npm run format:check    # TS-06

# Todo junto, desde la raíz
make lint && make test
pre-commit run --all-files
```

---

## General (`GEN-*`)

**`GEN-01` · Minor — Se siguen las convenciones del proyecto: nombres, espaciado, imports, formato.**
No se discuten a mano: las resuelven el formateador y el linter.
```bash
cd backend && uv run ruff format --check app tests && uv run ruff check app tests
cd frontend && npm run lint && npm run format:check
```

**`GEN-02` · Blocker — Un módulo nunca importa otro módulo: se comunican por eventos.**
Todo el contenido de un módulo es privado incluyendo`service.py`. Lo que un módulo necesita
comunicar es un evento de dominio publicado en `app.shared.events`; quien lo necesite se suscribe en su `handlers.py`. Ésta es la única regla de arquitectura que vive acá, porque es verificable.
El porqué y la anatomía del módulo están en `ARCHITECTURE.md`.

- ❌ `from app.modules.suppliers.service import SupplierService`
- ❌ `from app.modules.suppliers.repository import SupplierRepository`
- ❌ `from app.modules.suppliers.models import Supplier`
- ✅ `from app.shared.events import events, InvoiceRegistered`
- ✅ `from app.modules.identity.dependencies import require_roles` — **única excepción**

`dependencies.py` cruza porque es autorización HTTP: la respuesta hace falta antes de que corra el handler, y un evento no puede darla. La excepción está fijada por nombre de archivo en el test.

```bash
cd backend && grep -rnE "^from app\.modules\.|^import app\.modules\." app/modules
```
Cada resultado debe pertenecer al **propio** módulo del archivo, o ser un `dependencies`; cualquier otro es Blocker. El chequeo definitivo lo hace `test_module_boundaries.py`.

**`GEN-03` · Blocker — `app/shared/` no importa de `app/modules/`.**
`shared/` es el kernel: se depende de él, no depende. Tampoco contiene reglas de negocio.
```bash
cd backend && grep -rn "app.modules" app/shared
```

**`GEN-04` · Major — El router de un módulo nuevo se registra explícitamente en `app/main.py`.**
`main.py` es el *composition root*: es el único lugar que conoce a todos los módulos y el que mapea
los errores de dominio a códigos HTTP.

**`GEN-05` · Blocker — No hay ciclos entre módulos.**
Con eventos el ciclo ya no es un import: es `A` publica → `B` reacciona y publica → `A` reacciona, y
el compilador no lo ve. Si dos módulos se disparan mutuamente, la frontera está mal trazada: se
corrige la frontera, no se agrega el evento. Escalá al `Backend-Architect`.

**`GEN-06` · Blocker — Se respetan las reglas del dominio (INVIOLABLES) de `AGENTS.md`.**
No se reproducen acá para que exista un solo lugar donde cambiarlas. En resumen operativo: SIGProv
es solo lectura, la extracción es automatización de navegador (nunca un cliente HTTP contra el
portal ni sus endpoints JSON internos), nada se descarta, lo extraído en `raw` nunca se sobrescribe
—contenido, hash, tipo y fecha de llegada— y las credenciales del portal viven solo en el entorno.
```bash
cd backend && grep -rnE "httpx|requests\." app/modules/portal
cd backend && uv run pytest tests/architecture/test_raw_immutability.py
```
Ver también `ERR-05` (cuarentena) y `SEC-02` (credenciales), que son sus manifestaciones en código.

**`GEN-07` · Minor — Idioma: el código va en inglés, la documentación en español.**
Nombres, comentarios, docstrings y mensajes de commit en inglés; los strings que ve el usuario en la
UI, en español (`TS-09`). Los términos del dominio se traducen (`supplier`, `invoice`,
`purchase_order`) salvo los que no tienen equivalente limpio, que se dejan como están y se
documentan.

**Los archivos de configuración cuentan como código**: YAML, `Makefile`, `Dockerfile`, scripts de
shell y `.env.example` llevan sus **comentarios en inglés**. Van intercalados con palabras clave en
inglés (`repos`, `hooks`, `services`, `RUN`, `.PHONY`) y una mezcla se lee peor que cualquiera de
las dos opciones puras.

La excepción es la misma que en la UI: **lo que la terminal le muestra al equipo va en español**.
Las descripciones de `make help`, los `name:` de los hooks de pre-commit y los nombres de los pasos
de CI son salida para quien corre el comando, no comentarios para quien edita el archivo. Es el
Artículo VIII aplicado igual que siempre: un idioma para cada audiencia.
```bash
grep -rnE '^\s*#.*\b(que|para|los|las|del|con|una|sin)\b' \
  .pre-commit-config.yaml docker-compose.yml Makefile .github/ scripts/ .env.example
```

**`GEN-08` · Blocker — Los eventos de dominio viven en `app/shared/events/catalog.py`.**
No dentro del módulo que los publica: si `billing` tuviera que importar `purchasing.events` para
suscribirse, volvería el acoplamiento que `GEN-02` prohíbe. Un evento va en **pasado**
(`InvoiceRegistered`, no `RegisterInvoice`), es un dataclass **frozen**, y lleva identificadores y
valores planos — **nunca** un modelo de SQLAlchemy.

**`GEN-09` · Blocker — Un handler que falla aborta a quien publicó.**
Los handlers corren en la sesión y la transacción del publicador. No se atrapa la excepción para
"seguir": eso commitearía un hecho cuyas consecuencias no ocurrieron, que es exactamente la pérdida
silenciosa que prohíbe el Artículo II. El trabajo que no puede bloquear al publicador, o que tiene
que sobrevivir a una caída, encola una task de Celery y vuelve.

---

## Python (`PY-*`)

**`PY-01` · Blocker — No se importan tipos desde `typing`.**
Prohibidos `List`, `Dict`, `Tuple`, `Set`, `Optional`, `Union`. Permitidos, porque no tienen
equivalente built-in: `Any`, `Callable`, `TypeVar`, `Generic`, `Annotated` (lo exige `Depends()` de
FastAPI) y `TYPE_CHECKING`.
```bash
cd backend && grep -rnE "from typing import .*\b(List|Dict|Tuple|Set|Optional|Union)\b" app
```

**`PY-02` · Blocker — Se usan genéricos built-in y sintaxis moderna de uniones.**
`list[str]`, `dict[str, int]`, `str | None`. `target-version = "py312"`, así que `UP` de Ruff marca
buena parte de esto solo.

**`PY-03` · Major — Todos los imports van a nivel de módulo.**
Sin imports dentro de funciones o métodos. Ruff **no** lo detecta con el `select` actual
(`E`, `F`, `I`, `UP`, `B`, `SIM`): depende del review.
```bash
cd backend && grep -rnE "^\s+(import |from .+ import )" app | grep -v "TYPE_CHECKING"
```

**`PY-04` · Blocker — Toda función y todo método tienen entradas y retorno tipados.**
Sin `Any` implícito. `mypy` corre con `disallow_untyped_defs = false`, así que **no** atrapa una
función sin anotar: esto lo verifica el review, no la herramienta. `PY-10` cubre lo demás.

**`PY-05` · Blocker — El acceso a datos es async (SQLAlchemy 2.0 + asyncpg).**
Una `Session` sincrónica o un engine sincrónico es Blocker.
```bash
cd backend && grep -rnE "\bcreate_engine\(|sessionmaker\(|\bSession\(" app
```

**`PY-06` · Blocker — Las tasks de Celery usan el puente único; no hay `asyncio.run()` suelto.**
Los workers son sincrónicos y el acceso a datos es async: el puente es uno solo,
`app/worker/bridge.py` (`@async_task` / `run_async`). Abrir un event loop en cualquier otro lado es
Blocker.

La excepción son los **entry points de línea de comandos**: un comando que se corre una vez —al
instalar, o a mano— es un proceso propio que no tiene loop, y no es un worker. La regla protege al
worker de abrir un segundo loop sobre el que ya tiene; un `python -m ...` no está en esa situación.
```bash
cd backend && grep -rnE "asyncio\.(run|new_event_loop|get_event_loop)" app/modules | grep -v "bootstrap.py"
```

**`PY-07` · Major — Toda task es idempotente: re-ejecutarla no duplica efectos.**
La deduplicación se apoya en el hash de `raw`. Su test es `TEST-04`.

**`PY-08` · Blocker — Formato y lint con Ruff (`line-length = 100`).**
Rompe el pre-commit y el `make lint`, así que no llega al review como opinión.
```bash
cd backend && uv run ruff format --check app tests && uv run ruff check app tests
```

**`PY-09` · Blocker — Toda ruta declara su autorización.**
O el endpoint declara su dependencia de autenticación (`get_current_user`, directa o vía
`require_roles(...)`), o está listado en `PUBLIC_ROUTES` de
`backend/tests/architecture/test_route_authorization.py` **con el motivo escrito**. Las rutas de
escritura bajo `/users` necesitan además chequeo de rol: autenticación no es autorización.
Verificada por test (ver la tabla de arriba).
```bash
cd backend && uv run pytest tests/architecture/test_route_authorization.py
```

**`PY-10` · Blocker — `mypy` pasa limpio sobre `app/`.**
```bash
cd backend && uv run mypy app
```

---

## TypeScript y frontend (`TS-*`)

**`TS-01` · Blocker — Modo estricto de TypeScript activado, y el proyecto compila.**
```bash
cd frontend && npx tsc --noEmit
```

**`TS-02` · Blocker — Sin tipos `any`; se usa `unknown` cuando hace falta.**
```bash
cd frontend && grep -rnE ":\s*any\b|<any>|as any" app components lib
```

**`TS-03` · Major — Server Components por defecto.**

**`TS-04` · Major — `'use client'` sólo cuando hace falta y justificado.**
Interactividad, hooks o APIs del navegador. Cada directiva nueva se justifica en el review.
```bash
cd frontend && grep -rln "use client" app components
```

**`TS-05` · Major — Los tipos de la API se generan desde el schema de OpenAPI.**
No se escriben a mano ni se duplican los schemas del backend.
```bash
cd frontend && npm run generate-api-types      # o `make frontend-api-types`
```

**`TS-06` · Blocker — Formato con Prettier y lint con ESLint.**
```bash
cd frontend && npm run lint && npm run format:check
```

**`TS-07` · Minor — Cada cosa en su lugar.**
Páginas en `frontend/app/(private)/<modulo>/`, componentes de dominio en
`frontend/components/<modulo>/`, primitivas de shadcn/ui en `frontend/components/ui/`, acceso a
datos y utilidades en `frontend/lib/`, Server Actions en `frontend/app/actions/`.

**`TS-08` · Major — Los estados de carga, error y vacío están manejados.**

**`TS-09` · Minor — Los textos visibles por el usuario están en español.**

---

## Manejo de errores (`ERR-*`)

**`ERR-01` · Major — Ninguna excepción se traga en silencio.**
Un `except` que no loguea, no re-lanza y no decide nada es un hallazgo.
```bash
cd backend && grep -rn -A2 "except" app | grep -E "pass$|continue$"
```

**`ERR-02` · Minor — Los mensajes de error tienen sentido para quien los lee.**

**`ERR-03` · Blocker — Logging estructurado; nunca `print`.**
La excepción son los **entry points de línea de comandos** (`if __name__ == "__main__"`): lo que un
comando le contesta a quien lo corrió va a su terminal, no al log, donde esa persona no lo está
mirando. Acotada a la función `main()` del comando: todo lo que ese comando llama sigue logueando.
```bash
cd backend && grep -rnE "^\s*print\(" app | grep -v "bootstrap.py"
```

**`ERR-04` · Blocker — Los servicios no lanzan `HTTPException`.**
Lanzan los errores de dominio de `app/shared/errors.py` (`NotFoundError`, `ConflictError`,
`ValidationError`, `AuthenticationError`, `PermissionDeniedError`, `ExtractionError`), y `main.py`
los traduce a códigos HTTP. Un servicio que conoce HTTP deja de ser reutilizable desde una task.
```bash
cd backend && grep -rn "HTTPException" app/modules/*/service.py
```

**`ERR-05` · Blocker — Un error de interpretación de datos no es un error técnico.**
Va a cuarentena en `staging` y genera su fila en `operations.exception` para revisión humana. **No** va a un
`raise` que corta la ingesta, ni se descarta en silencio. Es la regla "nada se descarta" de
`GEN-06`, escrita como convención de código.

**`ERR-06` · Major — Hay manejo de errores en todas las capas: rutas, servicios, componentes.**

**`ERR-07` · Major — Los jobs quedan registrados en `operations` y son auditables.**

---

## Configuración y secretos (`SEC-*`)

**`SEC-01` · Blocker — No se commitean secretos.**
El hook `detect-private-key` de pre-commit cubre las claves privadas; el resto lo mira el review.
```bash
pre-commit run detect-private-key --all-files
```

**`SEC-02` · Blocker — Las credenciales del portal viven sólo en el entorno.**
Nunca en la base, nunca en el repositorio, nunca en un log. Es una regla del dominio (`GEN-06`).

**`SEC-03` · Major — La configuración es tipada (`Settings`) y está documentada en `.env.example`.**
Una variable nueva que no está en `.env.example` rompe el deploy de otro.

**`SEC-04` · Major — Sin valores hardcodeados.**
Van a `Settings` (si son de entorno) o a parámetros configurables en `operations` (si son de negocio).

**`SEC-05` · Minor — Los valores por defecto son seguros y explícitos.**

---

## Base de datos (`DB-*`)

**`DB-01` · Blocker — Los modelos están sincronizados con las tablas vía migraciones de Alembic.**
Modificar un modelo de SQLAlchemy sin su migración es Blocker. Flujo: modificar el modelo → crear la
migración → aplicarla → verificar.
```bash
cd backend && uv run alembic revision --autogenerate -m "descripcion"
cd backend && uv run alembic upgrade head
```

**`DB-02` · Blocker — No hay cambios manuales en la base de datos sin migración.**

**`DB-03` · Major — Los modelos usan `Mapped[...]` + `mapped_column(...)` y declaran su esquema.**
`raw`, `staging`, `core` u `operations` — identidad en el esquema por defecto. Qué va en cada esquema está en
`ARCHITECTURE.md` ("Flujo de datos"); acá sólo importa que el modelo lo declare.

**`DB-04` · Major — Las migraciones se revisan antes de aplicarse.**
`--autogenerate` propone; no decide. Una migración autogenerada que se commitea sin leer es un
hallazgo.

---

## Tests (`TEST-*`)

**`TEST-01` · Major — Hay tests unitarios de la lógica de negocio.**
Servicios, parsers, normalización. Los escribe el `Developer` para su propia lógica; la suite como
sistema es del `Tester`.

**`TEST-02` · Major — Hay tests de integración de endpoints y repositorios.**

**`TEST-03` · Blocker — Los parsers del portal se testean contra HTML fijado, nunca contra SIGProv en vivo.**
Los fixtures van en `backend/tests/fixtures/portal/` (el directorio se crea junto con el módulo
`portal`). Corolario verificable: **la suite completa corre con el portal apagado** y sin RabbitMQ.
```bash
cd backend && uv run pytest -m portal
```

**`TEST-04` · Major — Toda task nueva tiene su test de idempotencia** (`PY-07`).

**`TEST-05` · Blocker — La cobertura no baja del 80%.**
El umbral es `--cov-fail-under=80` en `backend/pyproject.toml`: no es una meta, es una condición de
la corrida.
```bash
cd backend && uv run pytest --cov=app --cov-report=term-missing
```

**`TEST-06` · Blocker — No se debilitan los tests para pasar el gate.**
Ni `skip`, ni asserts vaciados, ni umbral de cobertura bajado, ni un `xfail` del `Tester` tapado en
vez de arreglado. Un bug reportado con `xfail(strict=True)` se arregla y se saca el marcador.
```bash
cd backend && git diff --stat -- tests/ && grep -rn "skip\|xfail" tests | head -20
```

**`TEST-07` · Minor — Convenciones de la suite.**
Patrón AAA (Arrange / Act / Assert) explícito, marcadores declarados en `pyproject.toml`
(`--strict-markers`), tests async sin decorador (`asyncio_mode = "auto"`) y cobertura de los casos
de error, no sólo del camino feliz. Detalle en `backend/tests/README.md`.

---

## Dependencias (`DEP-*`)

**`DEP-01` · Blocker — Backend: las dependencias se gestionan sólo con `uv`.**
Prohibidos `pip install`, `requirements.txt` y `poetry add`. No se editan a mano las dependencias de
`pyproject.toml`.
```bash
cd backend && uv add <package>        # o `uv add --dev <package>`
cd backend && uv lock
cd backend && uv sync
```

**`DEP-02` · Blocker — `pyproject.toml` y `uv.lock` se commitean juntos.**
Evitando un lockfile desactualizado.

**`DEP-03` · Blocker — Frontend: las dependencias se gestionan con `npm`.**
No se editan a mano los números de versión de `package.json`; `package-lock.json` se actualiza solo
y se commitea.
```bash
cd frontend && npm install <package>
```

**`DEP-04` · Major — Una dependencia nueva del frontend pasa la auditoría.**
```bash
scripts/npm-audit-gate.sh
```

---

## Git y commits (`GIT-*`)

**`GIT-01` · Blocker — Nunca se commitea directo a `main`.**
Se trabaja en una rama de feature creada desde `main`, y el merge entra por PR después del gate de
`/review-feature`.
```bash
git checkout -b feat/<NNN-feature>
```

**`GIT-02` · Minor — Convención de ramas.**
**Los nombres de rama van en inglés**, como los mensajes de commit. `feat/<NNN-feature>` para
features, donde `<NNN-feature>` es exactamente el nombre de la carpeta de la spec
(`feat/001-portal-extraction`): un solo slug para la feature, no uno por herramienta.
`fix/<description>` para correcciones, `test/<description>` para cambios o agregados relacionados
sólo a tests, y `chore/<description>` para mantenimiento, dependencias y tooling.

**`GIT-03` · Blocker — Los mensajes de commit son Conventional Commits, en inglés.**
Tipos permitidos: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`,
`chore`, `revert`. Lo verifica el hook `conventional-pre-commit` en `commit-msg`: un mensaje fuera
de convención no llega a commitearse.

**`GIT-04` · Minor — Higiene de archivos.**
Sin whitespace al final, con newline al final del archivo, sin conflictos de merge sin resolver y
sin archivos de más de 1 MB. Todo lo verifica pre-commit.
```bash
pre-commit run --all-files
```

---

## Índice de Blockers

El `Code-Reviewer` marca estos hallazgos como **Blocker**, sin excepción. Es la **lista completa**:
las 32 convenciones marcadas `Blocker` en este documento entran acá, sin un segundo grupo aparte. Si
una convención está marcada Blocker y no aparece en esta tabla, la tabla está incompleta.

| # | Hallazgo | Convención |
|---|---|---|
| 1 | Violación de frontera entre módulos (import cruzado, `shared/` importando de `modules/`, ciclo de eventos) | `GEN-02`, `GEN-03`, `GEN-05` |
| 2 | `HTTPException` dentro de un `service.py` | `ERR-04` |
| 3 | Sesiones sincrónicas de base de datos | `PY-05` |
| 4 | `asyncio.run()` fuera del puente único | `PY-06` |
| 5 | Modelos desincronizados de las tablas | `DB-01`, `DB-02` |
| 6 | Violación de una regla del dominio (SIGProv) | `GEN-06`, `ERR-05`, `SEC-02` |
| 7 | Type safety roto (tipos de `typing`, funciones sin tipar, `any`) | `PY-01`, `PY-02`, `PY-04`, `PY-10`, `TS-01`, `TS-02` |
| 8 | Gestión de dependencias fuera de `uv` / `npm` | `DEP-01`, `DEP-02`, `DEP-03` |
| 9 | Ruta sin autorización declarada | `PY-09` |
| 10 | Tests debilitados para pasar el gate | `TEST-06`, `TEST-05` |
| 11 | Evento fuera del catálogo compartido, mutable, o que lleva un modelo | `GEN-08` |
| 12 | Handler que atrapa su excepción y deja seguir al publicador | `GEN-09` |
| 13 | `print` en lugar de logging estructurado | `ERR-03` |
| 14 | Formato o lint rotos — rompen el pre-commit | `PY-08`, `TS-06` |
| 15 | Secretos commiteados | `SEC-01` |
| 16 | Parsers testeados contra el portal en vivo en lugar de HTML fijado | `TEST-03` |
| 17 | Commit directo a `main`, o mensaje fuera de Conventional Commits | `GIT-01`, `GIT-03` |

## Identificadores retirados

Ninguno todavía. Cuando una convención se elimine, su identificador se lista acá con la fecha y el
motivo, y **no se reutiliza**.
