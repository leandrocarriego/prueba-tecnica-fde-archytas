# Órdenes de compra y avisos — Modelo de datos

<!-- ARTEFACTO INTERNO. Es el detalle largo que `plan.md` referencia. -->

**Feature:** 007-orders-alerts · **Fecha:** 2026-08-31

Ocho tablas: dos en `staging`, tres en `core` y tres en `operations`. Cuatro de las ocho son
**proyecciones** —copias de datos que son de otro módulo, alimentadas por eventos— y existen por el
Artículo IV: ningún módulo lee la tabla de otro.

Lo que **no** hay en esta feature: ninguna vista materializada, ningún campo calculado guardado, y
ningún estado derivado persistido. `is_stalled`, `days_in_status`, `days_since_ordered`,
`repeat_of_number` y `sender_unidentified` se calculan en cada lectura, y el porqué está en
`plan.md` → *Enfoque*.

---

## `staging.purchase_order_row`

Lo que se pudo tipar de `/ordenes-compra`. `backend/app/modules/ingestion/models.py:311-341`.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `int` PK | |
| `raw_document_id` | `int`, indexado | El documento de `raw` del que salió. Es la trazabilidad del Artículo III |
| `batch_id` | `int` | La corrida |
| `line_number` | `int` | La fila dentro de la pantalla |
| `number` | `str(64)?` | El número de OC |
| `ordered_on` | `date?` | La **única** fecha que publica el portal |
| `supplier_text` | `str(255)?` | El nombre tal como vino escrito |
| `product_code`, `product_text` | `str(64)?`, `str(500)?` | Un pedido es un producto |
| `quantity` | `int?` | |
| `amount` | `Numeric(14,4)?` | |
| `status_text` | `str(100)?` | El estado **en palabras**, como lo escribe el portal |
| `status` | `RowStatus` | `VALID` \| `QUARANTINED` |
| `reason` | `str(200)?` | Por qué no se pudo tipar |
| `excerpt` | `text?` | Lo que decía la fila |
| `created_at` | `timestamptz` | |

Índices: `ix_purchase_order_row_batch_status (batch_id, status)` y el de `raw_document_id`.

> **Las filas `QUARANTINED` de esta tabla no llegan a ninguna pantalla.** El evento
> `PurchaseOrderRowsQuarantined` se publica y nadie está suscripto. Es D-1 de `plan.md`.

## `staging.message_row`

Lo que se pudo tipar de `/mensajes`. `ingestion/models.py:345-376`.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `int` PK | |
| `raw_document_id`, `batch_id`, `line_number` | | Como arriba |
| `external_id` | `str(128)?`, indexado | **La clave de la idempotencia.** Es lo que hace que leer la bandeja cada media hora no duplique nada |
| `received_at` | `timestamptz?` | |
| `sender_text` | `str(255)?` | El remitente tal como vino |
| `kind_text` | `str(100)?` | El tipo **en las palabras del portal** |
| `subject`, `body` | `str(500)?`, `text?` | |
| `already_read` | `bool` | Si el portal lo daba por leído. Los 30 sin leer del relevamiento salen de acá |
| `status`, `reason`, `excerpt`, `created_at` | | Como arriba |

`ingestion` decide `first_run` preguntándole a esta tabla si alguna vez tipó un mensaje
(`ingestion/service.py:651`). Es RF-47, y depende de que la tabla **no se vacíe**: un `TRUNCATE` de
`staging.message_row` convierte la próxima lectura en una primera lectura, con lo que sesenta y
cuatro mensajes vuelven a registrarse como nuevos —no se duplican, `core.supplier_message` los
rechaza por `external_id`— pero el flag miente. No es un riesgo operativo hoy; es una dependencia que
conviene conocer.

---

## `core.purchase_order`

Una orden y **desde cuándo esta plataforma la viene viendo donde está**.
`backend/app/modules/purchases/models.py:495-541`.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `int` PK | |
| `number` | `str(64)`, **único** (`uq_purchase_order_number`) | Lo que hace idempotente `register_orders` |
| `ordered_on` | `date` | Del portal |
| `supplier_id` | `int?` FK → `core.supplier`, `ON DELETE RESTRICT` | Nulo mientras no se identifique |
| `supplier_text` | `str(255)` | El nombre tal como llegó. Es lo que RF-50 muestra |
| `product_code`, `product_text` | `str(64)?`, `str(500)` | |
| `quantity`, `amount` | `int?`, `Numeric(14,4)?` | |
| `status_text` | `str(100)`, indexado | El estado en palabras. **No es un enum**, y el porqué está en `plan.md` → *Alternativas descartadas* |
| `status_since` | `date` | **De esta plataforma, no del portal.** El día en que se vio la orden en este estado por primera vez (RF-05, RF-48) |
| `observed_from_start` | `bool`, default `true` | `False` para las que ya estaban al arrancar. Decide si la pantalla dice «N días observada así» o «pedida hace N días» (RF-49) |
| `review_state` | `OrderReviewState` (`OK`\|`PENDING`\|`RESOLVED`) | `PENDING` cuando el proveedor no se pudo identificar (RF-08) |
| `repeat_of_order_id` | `int?` | La orden anterior que ésta repite (RF-15, RF-16). **No es FK**, a propósito: apunta a una fila de su propia tabla y una FK circular complica el borrado sin comprar nada |
| `repeat_dismissed_by_user_id`, `repeat_dismissed_at` | `int?`, `timestamptz?` | Quién descartó el señalamiento y cuándo (RF-19) |
| `created_at` | `timestamptz` | |

Índices: `ix_purchase_order_status (status_text)`, `ix_purchase_order_supplier (supplier_id)`.

### Lo que a esta tabla le falta, y es de la H8

Tres columnas y un índice, sin construir (`plan.md` → *Lo que falta*):

| Columna | Tipo | Para qué |
|---|---|---|
| `review_reason` | `str(200)?` | RF-55: si el proveedor **no está en el padrón** hay que decirlo, y es distinto de «no se pudo desambiguar». Hoy `register_orders` recibe ese motivo de `resolve_supplier` y **lo descarta** (`service.py:1766`) |
| `resolved_by_user_id` | `int?` | RF-56 |
| `resolved_at` | `timestamptz?` | RF-56 |
| índice sobre `review_state` | | RF-52 filtra por él |

**Sin backfill posible.** Una orden ya apartada no sabe por qué lo fue, porque el motivo nunca se
guardó, y reconstruirlo exige volver a leer el portal. La migración deja `review_reason` nulo para lo
existente.

`core.supplier_alias` —la tabla de grafías de la 004— es la que RF-58, RF-61 y RF-62 usan. **No hay
una tabla de grafías propia de las órdenes**, y es alcance firmado: *«el criterio es uno solo para
las facturas y las órdenes»*.

## `core.supplier_message`

Un mensaje de la bandeja del portal. `backend/app/modules/messaging/models.py:43-90`.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `int` PK | |
| `external_id` | `str(160)`, **único** | La idempotencia de la lectura horaria (RF-21, y la mitad de RF-39) |
| `received_at` | `timestamptz` | Del portal |
| `sender_text` | `str(255)` | El remitente tal como vino |
| `supplier_name` | `str(255)?`, indexado | El proveedor del padrón, **o nulo**. Nulo es RF-24: se muestra diciendo que no se identificó, nunca atribuido al más parecido |
| `kind` | `MessageKind` | `PAYMENT_CLAIM` \| `DUE_SOON` \| `LOW_STOCK` \| `UNCLASSIFIED` |
| `kind_text` | `str(100)?` | El tipo **en las palabras del portal**, que es lo que se muestra cuando `kind` es `UNCLASSIFIED` (RF-25) |
| `subject`, `body` | `str(500)`, `text?` | |
| `state` | `MessageState` | `PENDING` \| `RESOLVED`. Nace `PENDING` (RF-27) |
| `assignee_user_id` | `int?` | RF-30. **No es FK y no se valida el rol**: ver D-3 |
| `note` | `text?` | RF-32 |
| `resolved_by_user_id`, `resolved_at` | `int?`, `timestamptz?` | RF-29 |
| `alerted_at` | `timestamptz?` | Cuándo salió el aviso inmediato por este mensaje. La otra mitad de RF-39 |
| `alert_failure` | `str(200)?` | RF-38. La escribe `record_alert_failure`, que **hoy no llama nadie** — se conecta con el evento `AlertDeliveryFailed`, decidido el 2026-08-31 (`plan.md` → *Lo que falta*) |
| `created_at` | `timestamptz` | |

`sender_unidentified` **no es columna**: se calcula al leer, como `supplier_name is None`
(`messaging/service.py:173-177`). Una columna habría sido una segunda verdad sobre el mismo hecho.

## `core.messaging_supplier` — proyección del padrón

Lo que `messaging` necesita saber de los proveedores para identificar un remitente, y nada más.
`messaging/models.py:93-115`.

| Columna | Tipo | Nota |
|---|---|---|
| `legal_name` | `str(255)` PK | Como lo publica el portal |
| `name_key` | `str(255)`, indexado | El nombre normalizado con `normalize_entity_name`, que es contra lo que se compara |
| `updated_at` | `timestamptz` | |

La alimenta `SuppliersNormalized`, el **mismo** evento que alimenta a `purchases`. Los dos módulos
aciertan sobre el mismo padrón sin conocerse, que es el costo que el Artículo IV declara aceptar: una
lectura sincrónica entre módulos deja de ser gratis y se paga con una proyección.

El umbral de identificación es `SENDER_THRESHOLD = 88` (`messaging/service.py:51`), **más alto que el
92 configurable de las facturas** y fijo en código. No es un descuido: identificar mal al remitente de
un reclamo es peor que decir que no se pudo, y a diferencia de las facturas acá no hay una pantalla
donde alguien lo corrija.

---

## `operations.notification_recipient` — proyección de las personas

`backend/app/modules/notifications/models.py:36-59`.

| Columna | Tipo | Nota |
|---|---|---|
| `user_id` | `int` PK, sin autoincremento | El id que usa `identity`, copiado |
| `role` | `str(20)`, indexado | `OWNER` \| `PURCHASING` \| `SALES` |
| `phone` | `str(20)` | El número personal (RF-44) |
| `name` | `str(255)` | |
| `is_active` | `bool`, default `true` | `False` desde que su acceso se desactiva. **Nada se borra**: quien vuelve recupera sus avisos sin recrearse |
| `updated_at` | `timestamptz` | |

**RF-45 vive acá y no en una regla.** Cuando llega `UserDeactivated`, `is_active` pasa a `False` y
`active_with_role` deja de devolverlo. No hay ningún lugar donde alguien tenga que acordarse de dejar
de avisarle.

## `operations.notification_route`

Qué rol recibe qué tipo de aviso (RF-37). `notifications/models.py:62-84`.

| Columna | Tipo | Nota |
|---|---|---|
| `kind` | `str(30)` PK | `PAYMENT_CLAIM` \| `DUE_SOON` \| `DAILY_DIGEST` |
| `role` | `str(20)` | |
| `updated_by_user_id`, `updated_at` | `int?`, `timestamptz` | |

**Nace vacía y no se siembra.** Los valores firmados —reclamos y vencimientos a compras, resumen al
dueño— viven en `DEFAULT_ROUTES` (`notifications/service.py:191-195`), como todo valor inicial de la
plataforma, y la tabla guarda **sólo lo que el dueño cambie**. Una instalación nueva se comporta como
una configurada sin cargar nada, y el `GET /alerts/routes` muestra los tres tipos siempre, con el
valor que la plataforma está obedeciendo de verdad.

## `operations.notification_setting` — proyección de tres parámetros

`notifications/models.py:87-104`. `key` (PK) → `value` (JSONB) → `updated_at`.

Guarda exactamente tres claves, filtradas en el handler (`handlers.py:154-161`):
`alerts.window_start`, `alerts.window_end` y `daily_digest.time`. Cualquier otro parámetro que el
dueño mueva pasa de largo. Mientras no haya fila, `AlertRouter.setting` cae al valor inicial de
`shared/parameters.py`.

---

## Los parámetros que esta feature lee

Cinco, todos del catálogo único (`backend/app/shared/parameters.py`) y todos ajustables desde el
panel de la 003. Ninguno vive escondido en una pantalla, que es la regla de negocio de la spec.

| Clave | Inicial | Quién lo proyecta | RF |
|---|---|---|---|
| `purchase_order.stalled_days` | `15` | `purchases` | RF-10, RF-11 |
| `purchase_order.repeat_window_days` | `15` | `purchases` | RF-15, RF-17 |
| `daily_digest.time` | `"08:00"` | `notifications` | RF-35, RF-36 |
| `alerts.window_start` | `"08:00"` | `notifications` | RF-42, RF-43 |
| `alerts.window_end` | `"18:00"` | `notifications` | RF-42, RF-43 |

Y uno más que la feature usa sin ser suyo: `message_sync.interval_minutes`, inicial `30`, que es
`operations` decidiendo cada cuánto se lee la bandeja (RF-21). Su inicial es la mitad del máximo que
el requisito tolera, y **nada valida que el dueño no lo suba a cuatro horas**.

## Las migraciones, y por qué son tres

| Migración | Qué trae de esta feature |
|---|---|
| `0011_invoices_and_suppliers.py` | `core.purchase_order` (`:483-522`), `staging.purchase_order_row` (`:309-347`), `staging.message_row` (`:220-264`), y el enum `order_review_state` |
| `0012_messages_and_sales.py` | `core.supplier_message`, `core.messaging_supplier`, y los enums `message_kind` y `message_state` |
| `0013_who_gets_told_what.py` | Las tres tablas de `operations` |

Tres migraciones para una feature es una consecuencia de que seis specs se construyeran en la misma
pasada, no un diseño. La `0011` la comparten 004, 005, 006 y 007: **un rollback de esta feature sola
no existe**. Si alguna de las cuatro se difiere, hay que partirla antes del merge, y está anotado en
`plan.md` → *Riesgos*.
