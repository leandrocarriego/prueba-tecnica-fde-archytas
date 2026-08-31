# 007 — Órdenes de compra y avisos · Quality gate

**Feature:** 007-orders-alerts · **Rama:** `feat/004-to-009-remaining-specs` · **Fecha:** 2026-08-31
**Rol:** Code-Reviewer · **Skill:** `agents/skills/review_feature.md`

## Veredicto

> **Bloqueado por un solo Blocker, y no es de esta feature.** La superficie de la 007 —`purchases`
> (bloques 007), `messaging`, `notifications`, el handler de `triage`, `shared/events`, y las
> pantallas `/ordenes`, `/mensajes` y `/configuracion`— **no tiene un solo hallazgo**. Lo que frena
> el merge es un bloque de imports sin ordenar en un test de la **006**, que entró con el último
> commit de la rama.

Arreglado B-1, la 007 **pasa al `Release-Manager`**.

## Changeset

7 commits contra `origin/main`, 200 archivos, +29.041 / −8.222. La rama trae las seis specs; este
review recorre la superficie de la 007, delimitada por `plan.md` → *Contexto de traspaso*.

## Gates automáticos

| Comando | Convenciones | Resultado |
|---|---|---|
| `uv run ruff format --check app tests` | `GEN-01` | ✅ 186 archivos |
| `uv run ruff check app tests` | `PY-08` | 🔴 **1 error** — ver B-1 |
| `uv run mypy app` | `PY-10` | ✅ 103 archivos |
| `uv run pytest` | `GEN-02`, `GEN-03`, `GEN-09`, `PY-09`, `TEST-05` | ✅ **1578 passed, 9 skipped**, cobertura **91,74 %** |
| `npx tsc --noEmit` | `TS-01` | ✅ |
| `npm run lint` | `TS-02` | ✅ |
| `npm run format:check` | `TS-06` | ✅ |
| `scripts/diagrams/validate.sh` | — | ✅ 9/9 |

> La cobertura bajó de 92,20 % a 91,74 % al quitar `PurchaseOrdersStalled` (H-5 del converge): el
> catálogo de eventos estaba cubierto por import, así que sacar una clase muerta baja el
> denominador y el numerador a la vez. Muy por encima del 80 % que exige `TEST-05`.

## Blockers

| # | Convención | Dónde | Qué pasa | Arreglo |
|---|---|---|---|---|
| **B-1** | `PY-08` / `GEN-01` | `backend/tests/integration/features/test_due_date_calendar.py:9` | `I001`: el bloque de imports no está ordenado —`app.shared.events` va antes que `app.shared.errors`—. Entró con `a0de286`, que es de la **006** | `cd backend && uv run ruff check --fix tests` |

No es de la 007, pero está en la rama que se mergea: frena el merge igual.

## Los cinco puntos que el plan pidió mirar

`plan.md` → *Contexto de traspaso* → *Para el Code-Reviewer*. Los cinco pasan, y tres de ellos
eran deriva abierta al empezar.

1. **`GEN-02` sobre `messaging` y `notifications`.** Cero imports cruzados en `messaging`,
   `notifications`, `purchases` y `triage`. El único `from app.modules` es intra-módulo
   (`notifications/handlers.py:13` importa `notifications.tasks`). Las dos proyecciones —el padrón
   en `messaging`, los usuarios en `notifications`— siguen siendo el mecanismo, y son exactamente
   el costo que el Artículo IV acepta a cambio de la frontera.
2. **`shared/events/bus.py::unsubscribe`.** Sigue teniendo **un solo llamador**,
   `notifications/tasks.py:163`, y sigue dentro del `finally`. Sin él cada resumen dejaría un
   acumulador colgado del bus.
3. **`GEN-09` en `notifications/handlers.py`.** Los cinco handlers que entregan algo hacen
   `.delay()` y vuelven (`:52`, `:64`, `:79`, `:89`, `:104`). Ninguno espera una respuesta HTTP
   dentro de la transacción del publicador.
4. **`purchases/service.py`: el motivo que se descartaba.** El `supplier, _ =` ya no existe en el
   camino de las órdenes: `:2237` captura `reason` y `:2274` lo persiste en `review_reason`. Es
   RF-55, que el converge había marcado sin implementación.
5. **`messaging` `assign`.** `routes.py:136-140` valida el destinatario contra
   `who_reaches(Section.SUPPLIER_MESSAGES)` y devuelve `NOT_ASSIGNABLE`. Era D-3 —la ruta que
   aceptaba cualquier `assignee_user_id`— y está cerrada, con test.

## El resto del checklist

- **`GEN-04`** — `orders_router`, `messages_router` y `alerts_router` registrados explícitamente en
  `main.py:266-268`.
- **`GEN-08`** — los eventos de la feature viven en el catálogo compartido, en pasado e inmutables.
  `PurchaseOrdersStalled`, que estaba en el catálogo sin publicador ni suscriptor, se quitó al
  cerrar H-5.
- **Lo que ninguna herramienta detecta** (`PY-03`, `PY-04`, `ERR-01`, `SEC-04`): sin hallazgos en la
  superficie de la 007. Ni imports dentro de funciones, ni defs sin anotar, ni `except: pass`, ni
  URLs o números hardcodeados.
- **Reglas del dominio** (`GEN-06`, `ERR-05`, `SEC-02`): el portal sigue siendo solo lectura y por
  navegador; `triage/handlers.py::open_unreadable_order_rows` cierra el `ERR-05` de las órdenes que
  no se pueden tipar —era H-4 del converge—; las credenciales siguen sólo en el entorno.
- **`TEST-06`** — los tests que desaparecen del diff **no se debilitaron, se reemplazaron**. Los dos
  de la bandeja pasaron de un fixture derivado a la captura real del portal
  (`test_section_parsers.py:189-229`). No hay un solo `xfail` ni `skip` nuevo en el changeset.
- **`DB-01`, `DB-04`** — `alembic/versions/0016_an_order_without_a_supplier_has_a_way_out.py` está
  leída y documentada, y las tres columnas coinciden con `models.py:539-561`. Deja dicho por qué
  **no** hay backfill de `review_reason`: el motivo nunca se guardó, y reconstruirlo exigiría volver
  a leer el portal. Inventarlo sería el Artículo II al revés.
- **Diagramas** — 9/9 validados, en español y sin detalle de implementación (Artículo VIII).

## Observaciones que no bloquean

- **`send_alert` y `send_access_link` siguen siendo dos tasks con el mismo cuerpo**, y el plan pide
  que no se unifiquen: una lleva credenciales y la otra no, y el log tiene que decir cuál salió
  (Artículo VII). Está bien como está; se anota para que un refactor futuro no lo lea como
  duplicación.
- **`RECEIVED_STATUS` sigue sin test propio** (D-4). El aviso temprano existe de costado:
  `test_section_parsers.py` afirma sobre la captura real que hay once órdenes `"Recibida"`. No es
  una convención violada, así que no bloquea — pero es la dependencia más frágil de la feature.
- **`purchase_orders` comparte el parámetro `invoice_sync.interval_hours` con las facturas.** RF-01
  no pide una frecuencia propia, así que no es deriva; cambiar la de facturas cambia la de órdenes
  y eso no está dicho en ninguna pantalla.
