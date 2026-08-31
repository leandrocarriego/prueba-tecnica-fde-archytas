# Review de calidad — 004-invoices-suppliers

**Feature:** 004-invoices-suppliers · **Rol:** `Code-Reviewer` · **Fecha:** 2026-08-31
**Rama:** `feat/004-to-009-remaining-specs`, HEAD `baedc02`
**Entra después de:** `/converge` (segunda corrida, deriva mayor cerrada el 2026-08-31)

> Este gate pregunta **¿está bien escrito?**. La otra pregunta —*¿es lo que se acordó?*— la
> contestó `converge.md`, y no se rehace acá.

## Veredicto: 🔴 CAMBIOS REQUERIDOS — dos Blockers

> ### ⏩ Estado al 2026-08-31, después de este review
>
> **B-1, M-1, M-2 y M-3 están arreglados y verificados.** Queda **B-2**, que no es del código y no
> lo puede cerrar quien escribe código: es la decisión sobre el orden del flujo. Y queda `m-1`,
> que **no se arregla** — abajo se explica por qué renombrar la rama ahora sería peor.
>
> El veredicto se conserva con su redacción original. Cada hallazgo lleva su cierre al lado; no se
> reescribe en pasado: un hallazgo borrado es un hallazgo que nadie vuelve a poder auditar, y la
> mitad del valor de esta lista es que la próxima feature vea qué clase de cosas se le escapan a un
> review anterior.

Uno es de una línea de comando. El otro no es del código: **es que este gate no tiene sobre qué
correr**, y eso importa más que cualquier hallazgo de la lista.

## Lo que está en verde, y no es poco

Toda la verificación mecánica que `CONVENTIONS.md` declara, corrida entera:

| Comando | Convenciones | Resultado |
|---|---|---|
| `uv run ruff format --check app tests` | `GEN-01`, `PY-08` | ✅ |
| `uv run ruff check app tests` | `GEN-01`, `PY-08` | ✅ `All checks passed!` |
| `uv run mypy app` | `PY-10` | ✅ `no issues found in 102 source files` |
| `uv run pytest` | `GEN-02`, `GEN-03`, `GEN-09`, `PY-09`, `TEST-05` | ✅ **1536 passed · 9 skipped**, cobertura **91.20 %** |
| `uv run alembic check` | `DB-01`, `DB-02` | ✅ `No new upgrade operations detected` |
| `npx tsc --noEmit` | `TS-01` | ✅ |
| `npm run lint` | `TS-02`, `TS-06` | ✅ 0 errores (2 warnings, y son de la 003) |
| `npm run format:check` | `TS-06` | ❌ **19 archivos** — Blocker B-1 |
| `scripts/diagrams/validate.sh` | paso 7 | ✅ los siete compilan |

Y el recorrido a mano de lo que ninguna herramienta detecta:

- **`GEN-02` / `GEN-03`** — ningún import cruzado en `purchases`, `ingestion`, `portal` ni `triage`.
  Los dos únicos `from app.modules.` que aparecen son al **propio** módulo. La tentación que el plan
  anticipaba —leer `triage` desde `purchases` para la cola— no se cayó en ella.
- **`GEN-06`** — `portal` no tiene un solo `httpx` ni `requests.`; ninguna escritura sobre `raw`.
  La copia del archivo en `core.invoice_document.content` **no** es una lectura de `raw`: es la
  proyección alimentada por `InvoiceFileRead`, que es lo que el Artículo IV prescribe.
- **`GEN-08`** — todos los eventos del catálogo son `frozen`, y ninguno lleva un modelo de
  SQLAlchemy. `bring_invoice_files` y `bring_held_invoice_files` **encolan y vuelven** (`GEN-09`).
- **`ERR-05`** — la grieta que el converge encontró está cerrada:
  `triage/handlers.py::open_unreadable_invoice_rows` escucha `InvoiceRowsQuarantined`, que se
  publicaba sin oyente desde el primer día.
- **`PY-01`, `PY-04`, `PY-05`, `PY-06`, `ERR-01`, `ERR-03`, `ERR-04`** — limpios.
  `PY-04` se verificó con un recorrido del AST sobre los cuatro módulos, no con un `grep` de línea:
  ninguna función sin retorno tipado y ningún argumento sin anotar.
- **`SEC-02`** — las credenciales sólo se leen de `settings`, en `portal/client.py:346-347`.
- **`TEST-03`** — los parsers corren contra los fixtures capturados de `tests/fixtures/portal/`.
- **`TEST-06`** — ningún test debilitado. Los `skip` que aparecen son guardas legítimas
  (`test_writes_are_committed.py` saltea un módulo sin `service.py`) y el `xfail(strict=True)` de
  `normalize_entity_name` está documentado como bug conocido, no tapado.
- **`DEP-01` a `DEP-03`** — sin cambios de dependencias en este changeset.

## Blockers

### B-1 · `TS-06` — el formateo del frontend está roto

`npm run format:check` falla en **19 archivos**, y cuatro son pantallas de esta feature:

```
components/purchases/InvoiceTable.tsx
components/purchases/ReviewQueue.tsx
components/purchases/SpellingList.tsx
components/purchases/InvoicePanel.tsx
```

`TS-06` es Blocker y rompe el pre-commit, así que esto tenía que estar resuelto antes de pedir el
review. **Arreglo:** `cd frontend && npm run format`. Es una línea, pero no se aprueba con la
herramienta en rojo — un formateo que se deja pasar «porque es cosmético» es el que después mete
ruido en el diff del cambio que sí importa.

**Rol dueño:** `Developer`.

> **Cerrado.** `npm run format` sobre el frontend; `npm run format:check` contesta
> `All matched files use Prettier code style!`.

### B-2 · Este gate no tiene changeset — y el código ya está en `main`

No corresponde a ninguna convención con identificador, y por eso se dice explícito. Dos hechos:

1. **La 004 ya está mergeada a `main`.** `git log main` tiene
   `738e198 Merge pull request #21 from leandrocarriego/feat/004-to-009-remaining-specs`. El
   quality gate está corriendo **después** del merge que existe para autorizar. `GIT-01` fija el
   orden —el merge entra por PR **después** del gate— y acá se invirtió.
2. **Todo lo que cerró los catorce hallazgos del converge está sin commitear**: 166 archivos en el
   árbol de trabajo, incluidas las migraciones `0014` y `0015`, `SupplierCorrection.tsx`,
   `SupplierPeriod.tsx` y los dos archivos de tests nuevos. No hay commit, no hay PR, no hay
   changeset. **No hay nada que aprobar ni que bloquear.**

Y hay un tercer hecho que agrava a los dos: **ese árbol se mueve mientras se lo revisa.** Durante
esta corrida `HEAD` pasó de `890918f` a `baedc02` y una suite completa falló por un fixture de la
**007** que se renombró en el medio. Lo verificado acá es una foto, y la foto ya cambió.

Lo que este review **sí** puede afirmar es lo de la tabla de arriba: sobre el árbol tal como estaba
hoy, la calidad está en verde salvo B-1. Lo que **no** puede es dar por pasado un gate sobre un
changeset que no existe como tal.

**Arreglo:** separar el trabajo de la 004 en commits propios y abrir su PR —o, si el orden ya está
consumado, dejar registrado que la 004 entró a `main` sin gate y que este review se corrió después,
para que nadie lea el historial al revés—. **Rol dueño:** `Release-Manager`, y la decisión sobre el
orden es del humano.

> **Sigue abierto, y el intento de cerrarlo el 2026-08-31 se detuvo a propósito.** El humano eligió
> commitear en la rama actual con un commit por feature y abrir un PR. Al armar los grupos
> aparecieron dos cosas que lo impiden:
>
> 1. **El corte por spec no es alcanzable a nivel de archivo.** Los cambios sin commitear mezclan
>    specs *dentro* del mismo archivo — `purchases/routes.py` trae 8 hunks de 004 y 3 de 007;
>    `service.py` mezcla 004 y 005 a lo largo de 831 líneas—. Separarlos exige partir hunks a mano.
> 2. **El árbol tiene trabajo ajeno en curso**, y la skill `ship_changes` prohíbe tocarlo:
>    - `docs/specs/archive/003-system-control/` está **staged para borrarse** (catorce rutas en
>      `D`), y la carpeta tampoco está en `docs/specs/`. Commitear el árbol **borraría la spec de la
>      003**, que en `main` existe (`b65005f`).
>    - Un **rediseño visual** en curso: `docs/design/*.html`, `globals.css`, los dos `layout.tsx` y
>      `components/ui/*`, tocados minutos antes — sobre los mismos `.tsx` que M-1.
>    - Una spec nueva, `011-set-aside-visibility`, y `HEAD` moviéndose durante el review
>      (`890918f` → `baedc02` → `a36f75b`, merge del PR #23).
>
> **Nada se commiteó.** Los arreglos de B-1, M-1, M-2 y M-3 están en el árbol, hechos y verificados
> con el gate en verde; lo que falta es que el árbol se quede quieto. Cuando eso pase, el ship son
> cinco minutos: cuatro commits limpios por feature y uno que nombra la superficie compartida.

## Major

### M-1 · `TS-08` y `ERR-06` — las seis pantallas de 004 confunden un 403 con una caída

Las seis usan `fetchFromApi`, que colapsa un 403, un timeout y un 500 en `null`, y las seis
renderizan `<NoPermission>` para los tres casos:

```
facturas/page.tsx · facturas/revision/page.tsx · facturas/[invoiceId]/page.tsx
proveedores/page.tsx · proveedores/[supplierId]/page.tsx · proveedores/grafias/page.tsx
```

El resultado en pantalla es que **al dueño se le dice que no tiene permiso y que se lo pida a quien
maneja compras** cuando lo que pasó es que el backend no contestó. Es exactamente el defecto que la
003 ya corrigió con `readFromApi` y fijó en `tests/architecture/test_screen_reads.py` — pero su
lista `SCREENS` tiene **tres entradas, y las tres son de la 003**.

**Arreglo:** pasar las seis a `readFromApi` (la ficha del proveedor ya lo usa para los motivos de
corrección, así que el patrón está a mano) y agregarlas a `SCREENS`. **Rol dueño:** `Developer`.

> **Cerrado.** Las seis leen `readFromApi` y ninguna llama ya a `fetchFromApi`. Cada una separa las
> tres respuestas: `unauthorized` es `<NoPermission>`, y lo demás es «No pudimos traer …» con el
> nombre de lo que no vino. Dos ganaron un caso que antes no tenían: una factura y un proveedor que
> **no existen** ahora dan `notFound()` en vez de decirle a alguien que no tiene permiso sobre algo
> que no está.
>
> Y la regla quedó fijada donde no depende de que alguien la recuerde: las seis están en `SCREENS`
> de `tests/architecture/test_screen_reads.py`, que pasó de 3 pantallas a 9 y de sus tests a **47**.
> Se corrigió además el mensaje de un assert que decía «no screen of 003», porque el archivo ya no
> es de la 003.

### M-2 · `PY-03` — tres imports dentro de funciones

```
app/modules/purchases/service.py:602   from app.shared.parameters import initial_value
app/modules/ingestion/documents.py:176 import pytesseract
app/modules/ingestion/documents.py:177 from PIL import Image
```

Ninguno declara por qué es diferido. El de `purchases` no tiene motivo visible: `app.shared` no
importa de `app.modules` (`GEN-03`), así que no hay ciclo que evitar. Los de `documents.py`
arrastran además una consecuencia de diseño: obligan a pasar el módulo como argumento
(`_ocr(image, pytesseract)`), tipado `Any`, para que la función de abajo lo alcance.

**Arreglo:** subirlos al nivel del módulo. Si alguno tiene que quedarse abajo —una dependencia
pesada que no se quiere cargar al importar— va con el motivo escrito en una línea, como hace el
resto del repositorio con sus excepciones. **Rol dueño:** `Developer`.

> **Cerrado.** Los tres subieron al bloque de imports. El de `documents.py` se llevó puesta la
> consecuencia que arrastraba: `_ocr` ya no recibe el módulo como argumento y su firma pasó de
> `_ocr(image: Any, pytesseract: Any)` a `_ocr(image: Image.Image)`. `typing.Any` quedó sin uso en
> el archivo y salió. `ruff` y `mypy`, limpios.

### M-3 · `TEST-04` — las tres tasks nuevas no tienen test de idempotencia propio

`extract_invoices`, `extract_invoice_file` y `extract_supplier_ledger` son tasks nuevas de esta
feature. En `tests/` aparecen sólo como nombre de job y en el fixture que las intercepta; ninguna se
corre dos veces.

El mecanismo que las hace idempotentes —el salto por hash de `_extract` (`portal/service.py:263`)—
**sí** está testeado, pero por el camino de precios
(`test_price_pipeline.py::test_a_document_that_was_read_is_skipped`). Es un argumento razonable y
no alcanza para `TEST-04`: el camino de facturas tiene un paso más que el de precios —la descarga
del archivo por factura— y ese paso no lo ejercita nadie dos veces.

**Arreglo:** un test que corra `extract_invoice_file` dos veces sobre la misma factura y verifique
que queda **un** `raw.portal_document` y **un** `core.invoice_document`. **Rol dueño:** `Tester`.

> **Cerrado.** `tests/integration/features/test_invoice_pipeline.py`, tres casos, uno por task.
> `FakePortal` ganó las tres lecturas que le faltaban —`fetch_invoices`, `download_invoice_file` y
> `fetch_supplier_ledger`— contra los fixtures capturados, así que la suite sigue corriendo con el
> portal apagado (`TEST-03`).
>
> Dos cosas que el test dice y conviene no perder. La primera: la pantalla de facturas se corre
> **tres** veces, no dos — la idempotencia no es una propiedad del segundo intento sino del
> enésimo. La segunda: se afirma que el portal **sí** se visitó las tres veces. El hash sólo se
> conoce después de leer, así que lo que no se repite es el efecto, no la visita, y un test que
> esperara una sola visita estaría fijando algo que el diseño no promete.

## Minor

### m-1 · `GIT-02` — la rama no es la de la feature

`feat/004-to-009-remaining-specs` empaqueta seis specs. La convención pide `feat/<NNN-feature>`, con
el nombre exacto de la carpeta: `feat/004-invoices-suppliers`. Es Minor y a esta altura no se
renombra —pero es la causa de B-2, no una coincidencia: una rama con seis features adentro no puede
tener un gate por feature.

> **No se arregla, y la decisión es deliberada.** Renombrar la rama ahora rompería el vínculo entre
> el merge que ya está en `main` (`738e198`, PR #21) y la rama que lo produjo, y dejaría el
> historial mintiendo sobre de dónde salió el código — que es peor que el nombre mal puesto. Lo
> único accionable de este hallazgo mira hacia adelante: **la próxima feature abre
> `feat/<NNN-feature>`, una por spec**, que es lo que vuelve posible un gate por feature. Queda
> anotado acá y no arreglado, que es la forma honesta de cerrarlo.

## Lo que se miró y no es hallazgo

- **`TS-04`** — las cuatro directivas `'use client'` de la feature (`ReviewQueue`,
  `SpellingList`, `SupplierCorrection`, `InvoicePanel`) tienen estado y handlers. Justificadas.
  `InvoiceTable`, `InvoiceFilters`, `SupplierContact` y `SupplierPeriod` son Server Components.
- **`GEN-03` y `app/shared/events/bus.py`** — el bus nombra `app.modules` en un `import_module` para
  descubrir los `handlers.py`. Es el mecanismo de composición, es dinámico, y el test que verifica
  la convención (estático, con `ast`) lo da por bueno. Cuando un documento y un test se
  contradicen, gana el test.
- **`SEC-03`** — sin variables de entorno nuevas en este changeset.
- **El punto ciego que el plan pedía mirar** (ningún dato dudoso llega a `core` sin pasar por una
  persona): `record_document` manda a `PENDING` cuando el archivo no coincide o no se pudo leer, y
  `register_invoices` aparta sin bloquear al resto. Los dos con test.
- **`purchases` con cuatro specs adentro** no es drift arquitectónico aceptado en silencio: está
  decidido y explicado en `plan.md`, y la frontera se sostiene.

## Qué falta para aprobar

**Uno solo: B-2**, y no es del código. La decisión sobre el orden es del humano y su ejecución, del
`Release-Manager`.

## Cómo quedó la verificación después de los arreglos

Todo corrido de nuevo, entero:

| Comando | Antes | Después |
|---|---|---|
| `uv run ruff format --check app tests` | ✅ | ✅ |
| `uv run ruff check app tests` | ✅ | ✅ `All checks passed!` |
| `uv run mypy app` | ✅ | ✅ `no issues found in 102 source files` |
| `uv run pytest` | 1536 passed · 91.20 % | ✅ **1563 passed · 9 skipped**, cobertura **92.11 %** |
| `npx tsc --noEmit` | ✅ | ✅ |
| `npm run lint` | ✅ 0 errores | ✅ 0 errores |
| `npm run format:check` | ❌ 19 archivos | ✅ `All matched files use Prettier code style!` |

**27 tests más y casi un punto de cobertura**, y ninguno vino de bajar una vara: tres son el
pipeline de facturas corrido dos veces, y los otros son las seis pantallas nuevas pasando por las
cuatro reglas de `test_screen_reads.py`.
