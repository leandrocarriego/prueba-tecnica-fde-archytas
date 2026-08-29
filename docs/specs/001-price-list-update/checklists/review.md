# Code review — 001-price-list-update

**Rol:** Code-Reviewer · **Skill:** `agents/skills/review_feature.md` · **Fecha:** 2026-08-29
**Rama:** `feat/001-price-list-update` · **Suite:** 511 en verde, cobertura 95.01%

> Este gate pregunta **¿está bien escrito?**. La pregunta *¿es lo que se acordó?* ya la contestó
> [`converge.md`](converge.md), con veredicto de deriva menor.

---

## Veredicto

# ✅ Aprobado

El changeset está bien construido y no queda ningún Blocker. El único que hubo —`B1`, la escritura
sobre `raw`— se cerró el mismo día por la vía que la Constitución prescribe.

---

## Cómo se cerró el Blocker

**`B1` · `GEN-06`** — el humano aprobó la excepción, y eso la convirtió en una **reforma `PATCH` del
Artículo III** (Constitución **2.0.1**, 2026-08-29). El artículo ahora dice qué es lo inmutable:
*lo extraído* —contenido, hash, tipo y fecha de llegada—, y deja explícito que una columna de
contabilidad del pipeline no lo sobrescribe.

La cláusula de Reforma pide tres cosas, y las tres están:

| | |
|---|---|
| Versión y fecha | `2.0.0` → **`2.0.1`**, última reforma 2026-08-29 (Artículo III) |
| Que los otros documentos no la contradigan | `CONVENTIONS.md` (`GEN-06`) y `ARCHITECTURE.md` (tabla de esquemas) actualizados. `AGENTS.md` no hacía falta: delega en el artículo |
| El test que la verifica | **`tests/architecture/test_raw_immutability.py`** |

**`M1` cerrado por el mismo test.** Enumera las cuatro columnas que nadie puede tocar fuera del
`insert`, y prohíbe un `update` o `delete` genérico sobre el repositorio. Lo probé contra una
violación real antes de darlo por bueno: escribí `content_hash` dentro de `mark_normalized` y el
test falló nombrando la función y la columna. Un test que no puede fallar no es una regla.

**`m1` cerrado**: el `Contexto de traspaso` ya no manda a buscar `update` y `delete` a mano, ahora
apunta al test.

**Suite: 520 en verde, cobertura 94.64%.**

---

## El recorrido, convención por convención

### Lo que verifica un test que rompe el build
La suite corrió y pasó, así que estas cinco no se revisan a ojo: `GEN-02`, `GEN-03`, `GEN-09`,
`PY-09`, `TEST-05`. **511 en verde, cobertura 95.01%** (piso 80%).

### Verificación mecánica

| Comando | Convenciones | Resultado |
|---|---|---|
| `ruff check app tests` | `PY-08` | ✅ |
| `ruff format --check app tests` | `GEN-01` | ⚠️ un archivo, de 002 |
| `mypy app` | `PY-10` | ✅ 69 archivos |
| `alembic check` | `DB-01`, `DB-02` | ✅ |
| `tsc --noEmit` | `TS-01` | ✅ |
| `eslint` · `prettier --check` | `TS-02`, `TS-06` | ✅ (dos warnings de 002, no errores) |

### A mano, que es donde ninguna herramienta llega

| Convención | Qué busqué | Resultado |
|---|---|---|
| `GEN-04` | Los routers registrados en `main.py` | ✅ nueve |
| `GEN-05` | Ciclos entre módulos | ✅ ninguno |
| `GEN-06` | Reglas del dominio | 🔴 **B1** — el resto ✅: sin cliente HTTP en `portal`, historial por `staging`, flujo en un sentido |
| `GEN-07` | Código en inglés, UI en español | ✅ |
| `PY-03` | Imports dentro de funciones | ✅ ninguno |
| `PY-04` | Funciones sin anotar (mypy no las ve) | ✅ ninguna |
| `PY-05` | Sesiones sincrónicas | ✅ ninguna |
| `PY-06` | `asyncio.run` fuera del puente | ✅ ninguno |
| `PY-07` | Idempotencia | ✅ y **reverificada**: `C8` cambió el mecanismo de salteo, y los dos tests que lo fijan —lista e historial— siguen pasando |
| `ERR-01` | Excepciones tragadas | ✅ ninguna |
| `ERR-03` | `print` en vez de logging | ✅ ninguno |
| `ERR-04` | `HTTPException` en un `service.py` | ✅ ninguna |
| `ERR-05` | Cuarentena en `staging` + `operations.exception` | ✅ |
| `SEC-01` | Secretos commiteados | ✅ ninguno |
| `SEC-02` | Credenciales del portal | ✅ sólo `settings.PORTAL_*`, y `test_the_reason_never_carries_a_credential` lo fija |
| `SEC-04` | Valores hardcodeados | ✅ ninguno |
| `DB-03` | Cada tabla con su esquema | ✅ dieciséis declaraciones |
| `DB-04` | Migración leída antes de commitear | ✅ `0004` y `0005` escritas a mano, con su porqué en el docstring |
| `TEST-01`/`TEST-02` | Unitarios e integración | ✅ |
| `TEST-03` | Parsers contra HTML fijado | ✅ `tests/fixtures/portal/`, nunca el portal en vivo |
| `TEST-04` | Idempotencia de las tasks | ✅ dos tests |
| `TEST-06` | Tests debilitados | ✅ ninguno. Verificado sobre el diff, no sobre el verde: los tests que cambiaron **ganaron** aserciones, y `test_sales_cannot` sigue exigiendo `403` después de que 002 migrara la autorización a secciones |
| `DEP-01`/`02`/`03` | `uv` y `npm`, con lockfile | ✅ sin `requirements.txt`; `uv.lock` en el changeset |
| `GIT-01`/`GIT-03` | Rama y mensajes | ✅ |

### Diagramas
Los ocho compilan, están en español y a nivel de negocio.

### Contexto de traspaso
Existe y sigue siendo verdad, con la salvedad de `m1`.

---

## Qué hace falta para aprobar

**Una sola decisión tuya**: aprobar la excepción al Artículo III —con la reforma `PATCH` y su
test— o sacar la marca de `raw`. `M1` viaja con esa decisión, y `m1` es una línea.

Nada más de este changeset está bloqueado.
