# Tablero del negocio — Modelo de datos

<!-- ARTEFACTO INTERNO. Es el detalle largo que `plan.md` referencia. -->

**Feature:** 009-business-dashboard · **Fecha:** 2026-08-31

Cinco tablas: una en `staging`, tres en `core` para el módulo `sales`, y una en `core` que es de
`catalog` y existe por esta feature. Dos de las cinco son **proyecciones**, y existen por el Artículo
IV: ningún módulo lee la tabla de otro.

**Nada del tablero se guarda calculado.** No hay tabla de totales por mes, ni de promedios por
producto, ni un booleano de «apartada». Todo se agrega en cada lectura, y el porqué está en `plan.md`
→ *Enfoque*: una cifra guardada sobre las mismas ventas es una segunda verdad que queda vieja la
primera vez que se corrige una.

---

## `staging.sale_row`

Lo que se pudo tipar de `/ventas`. `backend/app/modules/ingestion/models.py:378-413`.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `int` PK | |
| `raw_document_id` | `int`, indexado | El documento de `raw` del que salió. Trazabilidad del Artículo III |
| `batch_id` | `int` | La corrida |
| `line_number` | `int` | La fila dentro de la pantalla |
| `code` | `str(64)?` | El código de venta, tal como vino |
| `code_key` | `str(64)?`, indexado | El código **sin sus diferencias de escritura** (RF-10) |
| `sold_on` | `date?` | Nulo cuando falta o cuando la fecha no existe (31/02/2025) |
| `product_code` | `str(64)?` | |
| `quantity` | `int?` | |
| `total` | `Numeric(14,4)?` | |
| `status` | `RowStatus` | `VALID` \| `QUARANTINED` |
| `reason` | `str(200)?` | Por qué se apartó: sin código, sin fecha, fecha inexistente, sin total, cantidad negativa |
| `excerpt` | `text?` | Lo que decía la fila |
| `created_at` | `timestamptz` | |

Índices: `ix_sale_row_batch_status (batch_id, status)`, `ix_sale_row_code_key (code_key)`, y el de
`raw_document_id`.

> **Ésta es la tabla donde se quedan los doce registros rotos.** `normalize_sales` publica
> `SalesNormalized` filtrando por `status is VALID and code and sold_on is not None and total is not
> None` (`ingestion/service.py:743-750`), así que una fila `QUARANTINED` **nunca se convierte en un
> `core.sale`** y no llega a ninguna pantalla. `SaleRowsQuarantined` se publica y no tiene
> suscriptor. Es D-1 de `plan.md`, y es la mitad de la H3.

### Por qué `code_key` se guarda en vez de derivarse

Es una decisión y no una optimización. Guardado, el agrupamiento es una búsqueda por índice y
`code_key` significa **siempre lo mismo que significaba cuando la fila aterrizó**. Derivado al leer,
cambiar `sale_code_key` redibujaría los grupos del histórico entero de forma retroactiva y silenciosa.
La regla vive en un solo lugar —`parsers.py:1022-1027`— y se aplica una sola vez, al entrar.

La normalización saca espacios, guiones, guiones bajos y puntos, y baja a minúsculas. **Nada más.**
Un código que difiere en un dígito es otra venta, y ninguna regla puede tapar eso.

---

## `core.sale`

Un registro de venta, y hasta dónde la plataforma responde por él.
`backend/app/modules/sales/models.py:45-91`.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `int` PK | |
| `code` | `str(64)` | Tal como vino |
| `code_key` | `str(64)`, indexado | Copiado de `staging`, no recalculado |
| `sold_on` | `date?` | **Nulable**, y hoy nunca nulo: el publicador filtra las que no tienen fecha. El modelo ya admite lo que D-1 pide arreglar |
| `product_code` | `str(64)?` | |
| `quantity` | `int?` | |
| `total` | `Numeric(14,4)?` | **Nulable**, misma nota que `sold_on` |
| `state` | `SaleState`, indexado | `COUNTED` \| `HELD` \| `DISCARDED` |
| `reason` | `str(200)?` | Por qué está apartada, en las palabras que lee una persona (RF-23) |
| `portal_values` | `JSONB?` | **Lo que informó el portal**, copiado al registrar y **nunca tocado después** (RF-02, RF-41) |
| `is_estimated` | `bool`, default `false` | Un valor que una persona estimó porque el correcto no se puede conocer (RF-39). Todo indicador que lo use lo declara (RF-40) |
| `duplicate_of_sale_id` | `int?` | De cuál otra venta es copia. **No es FK**: apunta a su propia tabla |
| `decision` | `JSONB?` | Qué se decidió: `{"action": "keep"\|"distinct", "sale_id": N}` (RF-36) |
| `resolved_by_user_id`, `resolved_at` | `int?`, `timestamptz?` | Quién y cuándo (RF-36) |
| `staging_row_id` | `int?` | La fila de `staging` de la que salió |
| `created_at` | `timestamptz` | |

Índices: `ix_sale_code_key`, `ix_sale_state`, `ix_sale_sold_on`.

### Los tres estados, y por qué son tres

| Estado | Qué significa | Suma en un indicador |
|---|---|---|
| `COUNTED` | La plataforma responde por este registro | **Sí**, y es el único |
| `HELD` | Espera a una persona. **No es un error**: está contado y visible | No (RF-15) |
| `DISCARDED` | La copia de un registro que ya se contó una vez. Guardada, nunca borrada, y mostrada al lado de la que se eligió (RF-34) | No |

`DISCARDED` llega por dos caminos que la tabla **no distingue**, y eso es D-3 de `plan.md`: una
repetida idéntica que el sistema unificó solo (RF-11), y una versión que una persona descartó al
resolver un grupo (RF-31). Las dos quedan con `reason = "Repetida idéntica: se cuenta una sola vez"`
—que en el segundo caso es falso (D-7)— y las dos se suman juntas en `Indicator.excluded`, con lo que
RF-12 —informar cuántas unificó solo— no se puede contestar desde esta tabla sin mirar `decision`.

### Lo que **no** es columna, y por qué

| Lo que la pantalla muestra | De dónde sale |
|---|---|
| El total facturado del período | `SUM(total) WHERE state = COUNTED` y la ventana (`repository.py:95-105`) |
| El total mes a mes | `date_trunc('month', sold_on)` sobre lo mismo (`:80-93`) |
| Cuántos registros excluyó cada indicador | `COUNT` de `HELD` + `COUNT` de `DISCARDED` en la ventana |
| Si algún valor del indicador es estimado | `EXISTS` sobre `is_estimated` entre las contadas (`:108-115`) |
| Lo habitual de un producto | `AVG(total) WHERE product_code = ? AND state = COUNTED`, **sin ventana** (`:117-131`) |
| En qué campos difieren dos versiones | Comparación en memoria de los cuatro campos de `COMPARED` (`service.py:227-231`) |

**El promedio de RF-21 se mueve solo.** Cada venta que entra cambia el umbral para la siguiente, y
resolver un grupo también. Es la consecuencia deliberada de derivarlo de lo contado en vez de
guardarlo, y tiene un efecto que conviene conocer: **el orden de llegada puede cambiar cuáles ventas
se apartan por monto atípico**. Está en `plan.md` → *Riesgos*.

### El filtro que sostiene tres requisitos

`SalesRepository._filtered` (`repository.py:66-77`) es el único lugar donde vive «sólo lo contado», y
lo comparten el listado, los conteos y las tres agregaciones. De ahí salen RF-04 (los indicadores se
calculan sólo con lo no apartado), RF-15 (una apartada no suma) y RF-33 (resolver recalcula) **sin una
línea de código propia para ninguno de los tres**.

Una consulta nueva sobre `Sale` que no pase por ahí es un indicador que suma lo que no debe, y no hay
nada que lo delate por el nombre.

## `core.sales_product` — proyección de los códigos del catálogo

`sales/models.py:94-110`.

| Columna | Tipo | Nota |
|---|---|---|
| `product_code` | `str(64)` PK | El código, como lo publicó `catalog` |
| `known_since` | `timestamptz` | Cuándo esta plataforma lo empezó a conocer |

La alimenta `ProductsRegistered`, y es lo único que hace posible RF-20 —una venta que apunta a un
producto que no existe— sin que `sales` importe `catalog`. Es el costo que el Artículo IV declara
aceptar, hecho tabla de dos columnas.

**Depende del orden de llegada.** Si las ventas se leen antes de que el catálogo haya registrado un
producto, esa venta se aparta como «producto inexistente» y **no vuelve sola** cuando el producto
aparece: hay que corregirla a mano desde la pantalla de revisión. Ningún requisito pide lo contrario,
y es un comportamiento que conviene conocer antes de mirar la primera corrida.

## `core.sales_setting` — proyección de un parámetro

`sales/models.py:113-127`. `key` (PK) → `value` (JSONB) → `updated_at`.

Guarda exactamente **una** clave, filtrada en el handler (`sales/handlers.py:36-42`):
`sales.outlier_threshold_pct`. Cualquier otro parámetro que el dueño mueva pasa de largo. Mientras no
haya fila, `_setting` cae al valor inicial de `shared/parameters.py`, que es lo que hace que una
instalación nueva se comporte como una configurada.

---

## `core.stock_point` — la foto diaria

Es de `catalog` y existe por esta feature. `backend/app/modules/catalog/models.py:265-291`.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `int` PK | |
| `product_id` | `int` FK → `core.product`, `ON DELETE CASCADE`, indexado | |
| `quantity` | `int` | El stock que publicó la lista ese día |
| `observed_on` | `date`, indexado | |
| `batch_id` | `int?` | La corrida que la escribió |

`UNIQUE (product_id, observed_on)` — `uq_stock_point_product_day`. **Es lo que hace idempotente
reprocesar la lista de un día** en vez de duplicar el historial, y es la misma técnica que el resto de
la plataforma usa para lo mismo.

La escribe `catalog` al aplicar la lista de precios, y sólo cuando la fila trae stock
(`catalog/service.py:309-315`). Es decir: **la feature depende de que `staging.price_row.stock` venga
lleno**, que es el supuesto que la spec declara.

### Cómo se arma el corte, y qué queda afuera

`stock_at(moment, latest)` devuelve, por producto, **la foto más cercana** al borde de la ventana —la
última hasta `until`, la primera desde `since`— y no la del día exacto (`catalog/repository.py:450-470`).
La lista se publica los días que se publica, y exigir la fecha exacta dejaría el corte vacío cada vez
que el período empiece un domingo.

Después, para cada producto activo (`catalog/service.py:1893-1911`):

- con foto en los dos extremos → entra al corte, con `opening`, `closing` y `ran_out = (closing == 0)`;
- **sin ninguna foto que tomar** → **excluido**, y el corte lo informa. No se cuenta como cero,
  porque decir cero sería inventar un stock.

**Con una sola observación dentro de la ventana la misma foto es la de apertura y la de cierre**, y el
producto se lee como «no se movió»: es la consecuencia de tomar la foto *más cercana* a cada borde y
no la del día exacto. Es una inferencia sobre un solo dato, y `test_a_single_observation_is_reported_at_both_ends`
la deja escrita; si el negocio prefiere que un producto con una única observación quede excluido, eso
cambia RF-43 y lo decide el humano.

**Sin `since` no hay foto de apertura y todos los productos quedan excluidos.** Abrir el tablero sin
período muestra el corte de stock vacío con «N quedaron afuera», y la pantalla no explica por qué.
Está en `plan.md` → *Riesgos*.

---

## Los parámetros que esta feature lee

| Clave | Inicial | Quién lo proyecta | RF |
|---|---|---|---|
| `sales.outlier_threshold_pct` | `300` | `sales` | RF-21, RF-22 |
| `sales_sync.interval_hours` | `24` | `operations` | RF-01 |

**Mover la tolerancia no reevalúa lo ya cargado.** La comparación se hace cuando cada venta entra, y
el motivo queda guardado con ella. Está declarado en la spec, en «Para confirmar al firmar», porque
es exactamente la clase de cosa que se descubre después.

## Las migraciones, y por qué son tres

| Migración | Qué trae de esta feature |
|---|---|
| `0010_product_categories.py` | `core.stock_point` y la columna `staging.price_row.stock` (`:119-131, :167`) |
| `0011_invoices_and_suppliers.py` | `staging.sale_row` (`:349-388`) |
| `0012_messages_and_sales.py` | `core.sale`, `core.sales_product`, `core.sales_setting` y el enum `sale_state` |

Tres migraciones para una feature, y ninguna es suya sola: es la consecuencia de que seis specs se
construyeran en la misma pasada. La `0010` es la de la 008 y **lleva carga que no es de ella** —está
anotado en el plan de aquella feature, punto 11 de su *Deriva*—. **Un rollback de la 009 sola no
existe.**
