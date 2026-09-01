# Calendario de vencimientos — Contratos HTTP

<!--
  ARTEFACTO INTERNO. Es el detalle largo que `plan.md` referencia.
  Todo lo de acá sale de backend/app/modules/purchases/routes.py y schemas.py.
-->

**Feature:** 006-due-date-calendar · **Fecha:** 2026-08-31

Cinco endpoints, todos bajo el router `calendar_router`
(`backend/app/modules/purchases/routes.py:79`, registrado en `backend/app/main.py:258`). El prefijo
efectivo es `/api/v1/calendar`.

`PY-09` se cumple en los cinco por declaración explícita: ninguno está en `PUBLIC_ROUTES`, y el test
`backend/tests/architecture/test_route_authorization.py` verifica dos cosas distintas —que el árbol
de dependencias declare autenticación, y que un anónimo real reciba 401—. Además,
`test_a_route_that_writes_demands_the_level_to_write` verifica que los cuatro que escriben pidan
`Level.WRITE` y no `READ`, que es lo que separa RF-37 de RF-38.

## La autorización, en una línea

Todos piden `require_section(Section.CALENDAR, ...)`. La matriz
(`backend/app/modules/identity/permissions.py:76`) dice:

| Rol | `CALENDAR` | Qué puede |
|---|---|---|
| `OWNER` | `WRITE` | Todo |
| `PURCHASING` | `WRITE` | Todo (RF-12, RF-15, RF-17, RF-19, RF-42) |
| `SALES` | `READ` | Sólo `GET` (RF-37). Los otros cuatro le vuelven **403** (RF-38) |

El calendario es **la única superficie de `purchases` que ventas alcanza**: el resto del módulo la
deja afuera por RF-06 de la 004 y RF-09/RF-46 de la 007. Está dicho en el docstring del módulo de
rutas (`routes.py:1-13`).

---

## `GET /api/v1/calendar` — una ventana del calendario

`routes.py:474-493` · `Section.CALENDAR`, `Level.READ` · **200** `CalendarRead`

**Query**

| Parámetro | Tipo | Default | Qué hace |
|---|---|---|---|
| `since` | `date?` | — | Primer día mostrado |
| `until` | `date?` | — | Último día mostrado |
| `without_receipt` | `bool` | `false` | Sólo lo que no tiene recibo emitido (RF-10) |
| `hide_settled` | `bool` | `false` | Esconde las facturas saldadas (RF-40) |

**RF-04 vive en `_month_of` (`routes.py:567-574`)**: si `since` o `until` faltan, la ventana es el
mes en curso, calculado sobre `today_here()` — Buenos Aires, no UTC. Que el default lo resuelva el
backend y no el navegador es deliberado: el mes en curso es el del negocio.

**Respuesta** — `CalendarRead` (`schemas.py:301-306`)

```
{ since: date, until: date, items: DueDateRead[] }
```

`DueDateRead` (`schemas.py:280-298`) — los siete campos calculados están marcados:

| Campo | Tipo | Origen |
|---|---|---|
| `id`, `on_date`, `description`, `amount`, `invoice_id`, `origin`, `original_date` | | columnas de `core.due_date` |
| `was_rescheduled` | `bool` | calculado (RF-24) |
| `is_past` | `bool` | calculado (RF-06) |
| `supplier_name` | `str?` | calculado (RF-02) |
| `receipt_issued` | `bool` | calculado (RF-09) |
| `is_overdue_without_receipt` | `bool` | calculado (RF-11, RF-30) |
| `payment_state` | `str?` | calculado (RF-39) |
| `changes` | `DueDateChangeRead[]` | calculado, y **sólo si fue reprogramada** (RF-23) |

`DueDateChangeRead` (`schemas.py:267-277`): `id`, `previous_date`, `new_date`, `reason`,
`actor_user_id`, `changed_at`.

> **`actor_user_id` viaja como número, no como nombre.** La pantalla hoy no lo resuelve a una
> persona: lo que RF-33 pide —decir quién hizo el cambio que llegó— es de la H5, que no está
> construida.

## `POST /api/v1/calendar` — agregar un vencimiento a mano

`routes.py:496-511` · `Section.CALENDAR`, `Level.WRITE` · **201** `DueDateRead`

**Cuerpo** — `DueDateWrite` (`schemas.py:309-314`)

| Campo | Tipo | Regla |
|---|---|---|
| `on_date` | `date` | requerido |
| `description` | `str` | requerido, 1 a 300 caracteres |
| `amount` | `Decimal?` | opcional |

`created_by_user_id` y `created_at` los pone el servicio con el usuario de la sesión
(`service.py:1608`); no viajan en el cuerpo. El `origin` queda en `MANUAL` (RF-14) y `original_date`
se fija igual a `on_date`.

> **Y no vuelven a salir.** `DueDateRead` **no expone** ninguno de los dos —por eso no están en la
> tabla de campos de arriba—, así que el navegador nunca los ve y ninguna tarjeta los muestra
> (`CalendarGrid.tsx:96-104`). RF-13 queda registrado en la base y sin forma de verificarlo en
> pantalla, que es lo que su criterio firmado pide. Está anotado como deriva **D10** en `plan.md`.

## `PATCH /api/v1/calendar/{due_date_id}` — corregir uno cargado a mano

`routes.py:514-528` · `Section.CALENDAR`, `Level.WRITE` · **200** `DueDateRead`

**Cuerpo** — `DueDateEdit` (`schemas.py:317-321`): `description` (`str?`, 1 a 300) y `amount`
(`Decimal?`). Los dos opcionales; el que llega `null` no se toca.

| Error | Cuándo |
|---|---|
| **404** `No encontramos ese vencimiento` | el id no existe |
| **409** `Un vencimiento que viene de una factura no se elimina` | `origin == INVOICE` (RF-15 sólo alcanza a los cargados a mano) |

> **RF-16 no está cumplido acá.** El endpoint recibe el usuario y el servicio lo descarta
> (`service.py:1632`): no queda registrado quién corrigió, cuándo, ni cuál era el valor anterior.
> Está anotado como deriva en `plan.md`.

## `PUT /api/v1/calendar/{due_date_id}/date` — mover un vencimiento

`routes.py:531-551` · `Section.CALENDAR`, `Level.WRITE` · **200** `DueDateRead`

**Cuerpo** — `DueDateMove` (`schemas.py:324-330`)

| Campo | Tipo | Regla |
|---|---|---|
| `on_date` | `date` | la fecha nueva |
| `reason` | `str?` | hasta 1000 caracteres. **Ofrecido, nunca exigido** (RF-22) |
| `confirm_past` | `bool` | `false` por defecto |

**Arrastrar (RF-19) y elegir la fecha (RF-42) son esta misma llamada.** Cómo lo dice la persona es
asunto del navegador; la plataforma no tiene motivo para distinguirlos.

> **Y hoy el navegador no dice ninguna de las dos.** Mover es un `window.prompt` donde la fecha se
> **escribe** como texto (`CalendarGrid.tsx:49-65`): no hay arrastre (RF-19) y tampoco el selector con
> el que la spec prueba RF-42 —*"eligiendo la fecha nueva de un selector, sin arrastrarlo"*,
> `spec.md:121`—. Que el contrato esté cumplido **no alcanza** para dar por cumplido ninguno de los
> dos requisitos: son las derivas **D3** y **D11** de `plan.md`.

**RF-25 se implementa como un rechazo y un reintento:** mover a una fecha ya pasada con
`confirm_past=false` devuelve **409 `La fecha nueva ya pasó`**; la confirmación del usuario se
manda como `confirm_past=true`. Es lo que "pedir confirmación" significa sobre HTTP sin inventar un
estado intermedio en el servidor.

| Error | Cuándo |
|---|---|
| **404** `No encontramos ese vencimiento` | el id no existe |
| **409** `La fecha nueva ya pasó` | `on_date < hoy` y `confirm_past` es `false` (RF-25) |

**Efectos sobre la factura** — sólo si la entrada tiene `invoice_id`:

| | Reprogramada **antes** de vencer | Reprogramada **después** |
|---|---|---|
| `invoice.due_on` | se reescribe con la fecha nueva | **no se toca** |
| Plazo del recibo | se mueve (RF-26) | sigue negado (RF-28) |
| Atraso del proveedor | contra la fecha nueva (RF-27) | contra la original (RF-29) |
| ¿Sigue señalada vencida sin recibo? | no | **sí** (RF-30) |

## `DELETE /api/v1/calendar/{due_date_id}` — eliminar uno cargado a mano

`routes.py:554-564` · `Section.CALENDAR`, `Level.WRITE` · **204** sin cuerpo

| Error | Cuándo |
|---|---|
| **404** `No encontramos ese vencimiento` | el id no existe |
| **409** `Un vencimiento que viene de una factura no se elimina` | `origin == INVOICE` (RF-18) |

---

## Cómo llegan al navegador

El navegador **no llama a la API**: habla con Next, y Next habla con la API por la red interna
adosando el token de sesión (`ARCHITECTURE.md` → *Estrategia de deploy*). Las cuatro escrituras son
Server Actions en `frontend/app/actions/purchases.ts:228-285`, y la lectura la hace la página con
`fetchFromApi` (`frontend/app/(private)/calendario/page.tsx:39-42`).

Los tipos del frontend **se generan desde el OpenAPI** (`TS-05`): `Calendar`, `DueDate` y
`DueDateChange` son alias de `components['schemas'][...]` en `frontend/lib/purchases/types.ts:22-24`.
No hay un schema escrito a mano de este lado.

`editDueDate` (`actions.ts:245-256`) **existe y no la llama ninguna pantalla**: el `PATCH` no tiene
superficie de usuario. Está anotado como deriva en `plan.md`.


## `GET /api/v1/calendar/stream` — el canal en vivo ⬜ por construir

`require_section(Section.CALENDAR, Level.READ)` · RF-31 a RF-33, RF-35, RF-36

El canal en vivo. Un `GET` que no termina, `Content-Type: text/event-stream`, un mensaje por cada
cambio que otra persona hace sobre el calendario.

**Quién lo llama.** No el navegador contra esta API: el token vive en una cookie del lado servidor y
`EventSource` no manda headers. Lo llama un **Route Handler de Next**, que lee la cookie y reenvía el
stream al navegador. Ningún token viaja en la query string.

**`READ` y no `WRITE`:** ventas consulta el calendario (RF-37), así que también lo mira en vivo.

Cada mensaje lleva el evento `DueDateChanged` serializado:

```
event: due-date-changed
data: {"due_date_id": 41, "action": "moved", "actor_name": "Marcela",
       "on_date": "2026-09-20", "previous_date": "2026-09-10",
       "invoice_id": 812, "reason": "El proveedor pidió correrlo"}
```

`action` es uno de `added`, `edited`, `moved`, `removed` — los cuatro verbos de RF-31.

**Qué no hace este contrato:**

- **No garantiza entrega.** Quien está desconectado no recibe el mensaje: al reconectar, la pantalla
  vuelve a pedir `GET /calendar` y se pone al día (RF-36). No hay reintento ni cola por sesión.
- **No manda el calendario entero.** Viaja el hecho; la pantalla decide qué hacer con él.
- **No sirve para escribir.** Las cuatro escrituras siguen siendo las cuatro rutas de siempre.
