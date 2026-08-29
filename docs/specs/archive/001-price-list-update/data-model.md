# Actualización de la lista de precios — Modelo de datos

<!-- ARTEFACTO INTERNO. Detalle de `plan.md` → Datos. No se exporta al cliente. -->

**Feature:** 001-price-list-update · **Fecha:** 2026-08-28

Cuatro schemas de PostgreSQL, en un solo sentido. Cada tabla nueva entra con su migración de
Alembic y su línea en `app/models.py`, en el mismo commit (`DB-01`, Blocker).

```
                        ┌─> staging.price_row ─────────> core.product_price
SIGProv ──> raw.portal_document                                │
 (Playwright)           └─> staging.price_history_row ──> core.price_point
                                     │
                                     └── CUARENTENA ──> operations.exception ──> revisión humana
```

**Los dos caminos son el mismo camino.** La lista del día y la pantalla de historial de un producto
entran igual —`raw` verbatim con su hash, `staging` tipado con su estado, `core` canónico— porque el
Artículo III no admite un atajo para uno de los dos. Y porque sin fila en `staging` no hay dónde
marcar `CUARENTENA`: un historial ilegible no tendría lugar donde quedar apartado (RF-39).

## `raw` — lo que dijo el portal

### `raw.portal_document`

El archivo del día tal como llegó (RF-05). **Inmutable**: su repositorio expone `insert` y `get`, y no
expone `update` ni `delete`. Es lo que permite reprocesar todo el histórico cuando cambia un
criterio, sin volver a pedirle nada al portal (Artículo III).

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `int` PK | |
| `section` | `str(50)` | `prices` para el archivo del día, `price-history` para la pantalla de historial de un producto. P2 traerá `invoices` |
| `content` | `bytea` | Los bytes del archivo, sin tocar |
| `content_hash` | `str(64)` **unique** | SHA-256 del contenido. Es lo que hace idempotente a la task (`PY-07`, `TEST-04`) |
| `content_type` | `str(100)` | Lo que declaró el portal al descargar |
| `fetched_at` | `timestamptz` | |
| `job_run_id` | `int` | Qué corrida lo trajo. Sin FK entre schemas: es un identificador, no una relación |

> **`content_hash` es único a propósito.** Si el portal publica dos veces el mismo archivo, la
> segunda extracción choca contra la restricción y la task no reprocesa nada. Esa es la
> idempotencia, y no depende de que nadie se acuerde de chequear.

## `staging` — lo que se pudo interpretar

### `staging.price_row`

Una fila por línea del archivo; la que no se entiende queda `CUARENTENA` y no frena al resto (RF-06). Reproducible: se puede reconstruir entera desde `raw`.

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `int` PK | |
| `raw_document_id` | `int` | De qué documento salió |
| `batch_id` | `int` | Agrupa la corrida. Es lo que viaja en los eventos |
| `line_number` | `int` | Para poder señalar la fila exacta en la pantalla de revisión |
| `product_code` | `str(64)` nullable | Nulo si no se pudo ni leer el código |
| `description` | `str(500)` nullable | |
| `price` | `numeric(14,4)` nullable | Nunca `float`: es dinero |
| `currency` | `str(3)` | |
| `status` | `enum` | `VALIDO` · `CUARENTENA` |
| `reason` | `str(200)` nullable | Por qué quedó en cuarentena. Nulo si es válida |
| `excerpt` | `text` nullable | El texto crudo de la fila, para que una persona pueda leer qué decía |
| `category_raw` | `str(200)` nullable | La categoría **tal como vino**, sin interpretar |
| `subcategory_raw` | `str(200)` nullable | Ídem la subcategoría |
| `resolved_by_rule_id` | `int` nullable | Si una regla aprendida la resolvió sola (RF-34) |

Índices: `(batch_id, status)` para contar lo apartado al cerrar la corrida (RF-27), y
`(product_code)` para la reaplicación de reglas.

> **`category_raw` y `subcategory_raw` no las lee nadie en esta feature.** El portal escribe el mismo
> rubro de cuatro formas distintas —`PINTURAS Y ADHESIVOS`, `Pinturas/Adhesivos`,
> `Pinturas y Adhesivos`, `Pinturas`— y unificarlas es **P7**, que la spec de P1 deja fuera de
> alcance con nombre propio. Se guardan crudas para que P7 no tenga que reparsear el archivo entero,
> y con el sufijo `_raw` para que nadie las confunda con un valor normalizado.

### `staging.price_history_row`

Un punto por fila de la pantalla de historial. Espejo de `price_row`: mismo ciclo, mismos estados,
misma cuarentena.

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `int` PK | |
| `raw_document_id` | `int` | El documento de `section = 'price-history'` del que salió |
| `product_code` | `str(64)` | De qué producto es este historial |
| `line_number` | `int` | Para señalar la fila exacta en la pantalla de revisión |
| `price` | `numeric(14,4)` nullable | Nulo si no se pudo interpretar |
| `changed_at` | `timestamptz` nullable | La fecha que publica el portal |
| `status` | `enum` | `VALIDO` · `CUARENTENA` |
| `reason` | `str(200)` nullable | Por qué quedó apartado |
| `excerpt` | `text` nullable | El texto crudo de la fila |

> **En esta pantalla el precio sí viene como texto** —`$25.308`—, a diferencia del archivo del día,
> donde es un entero. Son dos parsers distintos y el de acá tiene que interpretar el separador de
> miles: es el que más filas va a mandar a cuarentena.
>
> La columna *Variacion vs. anterior* que publica el portal **no se guarda**: es derivable de dos
> puntos consecutivos, y guardarla sería tener dos fuentes para el mismo número.

### `staging.resolution_rule` — proyección, no fuente

**Es una proyección de `operations.resolution_rule`, que es de `triage`.** Existe porque `ingestion`
necesita consultar las reglas mientras normaliza y **no puede importar `triage`** (Artículo IV). Se
alimenta de `QuarantineCaseResolved` y se vacía con `QuarantineRuleRevoked`.

| Columna | Tipo | Notas |
|---|---|---|
| `rule_id` | `int` PK | El id de la regla en `triage`. No es un PK propio: es el ajeno |
| `kind` | `str(50)` | `unreadable_row` · `unknown_product` · `missing_product` |
| `matcher` | `jsonb` | Con qué se compara una fila nueva para saber si es "el mismo caso" |
| `decision` | `jsonb` | Qué hacer cuando coincide |
| `learned_at` | `timestamptz` | |

> **Nunca se escribe desde `ingestion` por su cuenta.** Sólo la escriben sus dos handlers. Si alguna
> vez hace falta editarla desde el servicio, la frontera está mal trazada.

## `core` — el modelo canónico

### `core.product`

El padrón de productos conocidos. **Se siembra con la primera lista** (RF-02) y después sólo crece
por decisión humana (RF-30) — nunca por una corrida automática (RF-07).

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `int` PK | |
| `code` | `str(64)` **unique** | El código del proveedor |
| `description` | `str(500)` | |
| `status` | `enum` | `ACTIVE` · `DISCONTINUED` — `DISCONTINUED` sólo por RF-31 |
| `first_seen_at` / `last_seen_at` | `timestamptz` | `last_seen_at` es lo que detecta al que dejó de venir (RF-28) |

### `core.product_price` — el precio vigente

Una fila por producto, reescrita en cada actualización con el precio que trajo la lista (RF-03). Es la que lee la pantalla de precios (RF-04).

| Columna | Tipo | Notas |
|---|---|---|
| `product_id` | `int` PK/FK | Uno a uno con el producto |
| `price` | `numeric(14,4)` | |
| `currency` | `str(3)` | |
| `effective_at` | `timestamptz` | Cuándo lo trajo la lista |
| `previous_price` | `numeric(14,4)` nullable | El precio de la actualización anterior. **Es contra este que se mide el destacado** (RF-25) |
| `is_highlighted` | `bool` | Derivado, pero materializado: la pantalla filtra por él |
| `is_stale` | `bool` | El producto no vino en la última lista y se conserva el último precio (RF-08, RF-28) |

> `previous_price` está desnormalizado a propósito. RF-25 compara contra "la actualización
> anterior", no contra el punto anterior del historial, y **no son lo mismo**: si el precio no
> cambió, el historial no suma un punto (RF-22) pero la actualización sí ocurrió.

### `core.price_point` — el historial

Un punto **por cambio de precio**, no por consulta (RF-22). Con dos consultas diarias, un punto por
consulta daría ~60 puntos mensuales por producto; el brief dice *"entre 2 y 11 puntos cada uno"* —que
es, ahora se sabe, lo que el portal ya publica por producto, no lo que el sistema acumularía.

Se alimenta de dos orígenes: lo que el portal ya tenía publicado cuando el producto se registró
(RF-38) y lo que el sistema fue viendo después (RF-22).

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `int` PK | |
| `product_id` | `int` FK | |
| `price` | `numeric(14,4)` | |
| `changed_at` | `timestamptz` | |
| `batch_id` | `int` nullable | Qué corrida lo produjo. Nulo en los puntos importados del portal |
| `source` | `enum` | `PORTAL` · `SYSTEM` — de dónde salió el punto |

Índice `(product_id, changed_at DESC)`: sirve a la evolución (RF-23) y a la variación mensual
(RF-24), que busca el último punto **anterior al primer día del mes calendario actual**.

Restricción única `(product_id, changed_at)`: es lo que hace cumplir RF-40 sin un `SELECT` previo.
Importar dos veces el historial de un producto choca contra la base y deja un solo punto, en lugar de
depender de que el código se acuerde de chequear. `source` no entra en la clave a propósito: un mismo
precio y una misma fecha son el mismo punto, lo haya visto el portal o el sistema.

## `operations` — el sistema operando sobre sí mismo

### `operations.exception` — la cola de revisión

Es de **`triage`**, aunque comparta schema con las tablas de `operations`. El schema es un
namespace, no una frontera: la frontera es el módulo y la verifica el test por import.

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `int` PK | |
| `kind` | `str(50)` | `unreadable_row` · `unknown_product` · `missing_product` · `unreadable_history` — lo abre `PriceHistoryRowsQuarantined` |
| `payload` | `jsonb` | Todo lo que el caso necesita para mostrarse y resolverse |
| `reason` | `str(200)` | Lo que ve la persona (RF-26) |
| `fingerprint` | `str(64)` | Hash de lo que define "el mismo caso". **Es lo que evita el pendiente duplicado** (RF-35) |
| `status` | `enum` | `PENDING` · `RESOLVED` |
| `batch_id` | `int` | En qué corrida apareció |
| `occurrences` | `int` | Cuántas veces volvió a aparecer estando pendiente |
| `resolved_by_user_id` / `resolved_at` / `decision` | | Quién, cuándo y qué decidió (RF-32) |

Índice único parcial sobre `(fingerprint) WHERE status = 'PENDING'`: la base garantiza el "un solo
pendiente" de RF-35, en lugar de un `SELECT` previo que tiene carrera.

> **`payload` es JSONB y `kind` es un string, a propósito.** `triage` no sabe qué es un precio, y P2
> va a meter facturas en esta misma cola sin migrar nada.

### `operations.resolution_rule` — la regla aprendida

La fuente de verdad de lo que `staging.resolution_rule` proyecta. Es el Artículo II: *"cada decisión
humana sobre una excepción se guarda como regla reutilizable"*.

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `int` PK | |
| `kind` | `str(50)` | |
| `matcher` | `jsonb` | |
| `decision` | `jsonb` | |
| `created_by_user_id` / `created_at` | | Quién la enseñó (RF-36) |
| `revoked_by_user_id` / `revoked_at` | nullable | Se anula, **no se borra**: una regla borrada no se puede auditar (RF-36) |

### `operations.parameter` — ya existe

Sin migración nueva. Dos claves:

| Clave | Valor inicial | Requisitos |
|---|---|---|
| `price_update.interval_hours` | `12` | RF-18, RF-20, RF-21 |
| `price_update.highlight_threshold_pct` | `10` | RF-19, RF-20 |

### `operations.job_run` — ya existe

Sin migración nueva. `task_name = "extract_price_list"`. `payload` lleva
`requested_by_user_id` cuando la actualización se pidió a mano (RF-17); nulo cuando la disparó el
scheduler. `status` y `finished_at` sostienen la última exitosa (RF-09) y la detección de dos
seguidas sin éxito (RF-11, RF-12).

## Máquinas de estado

Las tres están dibujadas para el cliente en [`diagrams/`](diagrams/). Acá, sus valores:

| Entidad | Estados | Diagrama |
|---|---|---|
| `staging.price_row` | `VALIDO` · `CUARENTENA` | `estados-fila.mmd` |
| `staging.price_history_row` | `VALIDO` · `CUARENTENA` | `estados-fila.mmd` |
| `core.price_point` | sin estados; `source` es `PORTAL` o `SYSTEM` | `estados-precio.mmd` |
| `operations.exception` | `PENDING` · `RESOLVED` | `estados-fila.mmd` |
| `core.product` | `ACTIVE` · `DISCONTINUED` | `estados-precio.mmd` |
| `operations.job_run` | `PENDING` · `RUNNING` · `SUCCEEDED` · `FAILED` *(ya existe)* | `estados-actualizacion.mmd` |
