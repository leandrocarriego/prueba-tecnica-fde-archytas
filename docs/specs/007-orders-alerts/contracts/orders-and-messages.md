# Órdenes de compra y avisos — Contratos HTTP

<!-- ARTEFACTO INTERNO. Es el detalle largo que `plan.md` referencia. -->

**Feature:** 007-orders-alerts · **Fecha:** 2026-08-31 · **Prefijo:** `/api/v1`

Siete endpoints construidos y **uno diseñado y no construido**, marcado como tal. Cada uno declara su
sección y su nivel (`PY-09`); quién alcanza ese nivel lo decide la matriz de `identity` y no estas
rutas.

Los errores siguen la forma única de la plataforma (`ERR-01`): `{"detail": "...", "details": {...}}`,
con el `detail` en español porque lo lee una persona.

---

## Las órdenes de compra

`backend/app/modules/purchases/routes.py:577-612` · `orders_router`, prefijo `/purchase-orders`

### `GET /purchase-orders`

**`PURCHASE_ORDERS` · `READ`** — dueño y compras. Ventas recibe 403 (RF-09).

| Query | Tipo | Default | Qué hace |
|---|---|---|---|
| `skip` | `int ≥ 0` | `0` | |
| `limit` | `int 1..200` | `200` | |
| `status_text` | `str?` | — | Sólo las de ese estado, comparado **literal** contra lo que escribe el portal (RF-06) |
| `supplier_id` | `int?` | — | Sólo las de ese proveedor (RF-06) |
| `only_stalled` | `bool` | `false` | Sólo las estancadas (RF-12) |

**Respuesta `200` — `PurchaseOrderList`:**

```
{
  items: PurchaseOrderRead[],
  total: int,                 // los de esta vista, no los del padrón
  per_status: {str: int},     // RF-07, sobre TODAS las órdenes, no sobre la página
  stalled: int                // RF-13
}
```

**`PurchaseOrderRead`** (`purchases/schemas.py:333-356`):

```
id, number, ordered_on, supplier_id?, supplier_text, supplier_name?,
product_code?, product_text, quantity?, amount?, status_text, status_since,
observed_from_start, days_in_status, days_since_ordered, is_stalled,
repeat_of_order_id?, repeat_of_number?, repeat_dismissed_at?
```

Tres cosas que hay que leer juntas y no por separado:

- **`supplier_name` nulo con `supplier_text` lleno es RF-50**: la orden está apartada y se muestra
  con el nombre tal como llegó. La pantalla dibuja «*texto* · sin identificar».
- **`days_in_status` vale cuando `observed_from_start` es `true`**; cuando es `false` el número que
  significa algo es `days_since_ordered` (RF-49). Los dos vienen siempre; la pantalla elige.
- **`per_status` no respeta los filtros.** Es deliberado: son los enlaces de filtro, y un conteo que
  cambia al filtrar no sirve para navegar.

**Lo que a esta respuesta le falta y es de la H8:** `review_state` en el ítem, `held` en la lista
(RF-51) y un query `review_state=PENDING` (RF-52).

### `DELETE /purchase-orders/{order_id}/repeat-flag`

**`PURCHASE_ORDERS` · `WRITE`** — dueño y compras (RF-18).

Sin cuerpo. Baja `repeat_of_order_id` a nulo y escribe `repeat_dismissed_by_user_id` y
`repeat_dismissed_at` **con el usuario del token, nunca del cuerpo** (RF-19).

| Código | Cuándo |
|---|---|
| `200` | `PurchaseOrderRead` con el flag ya bajado |
| `403` | Ventas, o compras con nivel insuficiente |
| `404` | `No encontramos esa orden`, con `details.order_id` |

**Es un `DELETE` sobre un sub-recurso y no un `PATCH` sobre la orden** porque lo que se borra es el
señalamiento, no la orden: el verbo dice qué desaparece.

### `POST /purchase-orders/{order_id}/resolution` — **diseñado, no construido**

**`PURCHASE_ORDERS` · `WRITE`** — dueño y compras (RF-53).

Es la H8, y el contrato está calcado del que ya resuelve una factura apartada
(`POST /invoice-review/{id}/resolution` de la 004), porque la spec dice explícitamente que es el
mismo criterio.

```
{ supplier_id: int, remember: bool = true }
```

| Código | Cuándo |
|---|---|
| `200` | `PurchaseOrderRead` con `supplier_id`, `review_state: RESOLVED`, `resolved_*` y —si corresponde— `repeat_of_order_id` recién evaluado (RF-60) |
| `403` | Ventas |
| `404` | La orden, o el proveedor, no existen |
| `409` | La orden no está apartada |

Con `remember: true` —el default, y lo que la pantalla manda— la grafía queda guardada como criterio
(RF-61) y **la misma llamada resuelve todas las órdenes apartadas escritas así** (RF-62), más las
facturas que estaban esperando esa grafía, porque `core.supplier_alias` es una sola tabla para las
dos cosas.

**Lo que no lleva, y está decidido en la spec:** no hay `responsable` —una orden apartada no se
reparte de a una— y no hay forma de dar de alta un proveedor desde acá (RF-55). Un proveedor fuera
del padrón deja la orden apartada con ese motivo, y sumar un proveedor se decide aparte.

---

## La bandeja de mensajes

`backend/app/modules/messaging/routes.py` · `router`, prefijo `/messages`

### `GET /messages`

**`SUPPLIER_MESSAGES` · `READ`** — dueño y compras. Ventas recibe 403 (RF-46), y eso incluye los
mensajes de stock bajo.

| Query | Tipo | Default | Qué hace |
|---|---|---|---|
| `skip` | `int ≥ 0` | `0` | |
| `limit` | `int 1..200` | `50` | |
| `kind` | `MessageKind?` | — | `PAYMENT_CLAIM` \| `DUE_SOON` \| `LOW_STOCK` \| `UNCLASSIFIED` (RF-26) |
| `state` | `MessageState?` | — | `PENDING` \| `RESOLVED` (RF-26) |
| `supplier_name` | `str(255)?` | — | Por proveedor **ya identificado** (RF-26) |

**Respuesta `200` — `MessageList`:** `{ items, total, pending, skip, limit }`.

`pending` **no respeta los filtros**: es el total de pendientes de la bandeja (RF-31), por el mismo
motivo que `per_status` en las órdenes.

**`MessageRead`** (`messaging/schemas.py:12-34`):

```
id, external_id, received_at, sender_text, supplier_name?, kind, kind_text?,
subject, body?, state, assignee_user_id?, note?, resolved_by_user_id?,
resolved_at?, alert_failure?, sender_unidentified
```

- **`sender_unidentified` es RF-24** y se calcula al leer, no se guarda.
- **`kind_text` es lo que salva RF-25**: cuando `kind` es `UNCLASSIFIED`, la pantalla muestra la
  palabra que usó el portal en vez de esconder el mensaje en un cajón de «otros».
- **`alert_failure` es RF-38, y hoy siempre viene nulo**: la pantalla lo dibuja y nada lo escribe.
  Se conecta con el evento `AlertDeliveryFailed`, decidido el 2026-08-31 — sin tocar este contrato,
  porque el campo ya viaja. Ver `plan.md` → *Lo que falta*.

Filtrar por `supplier_name` **no encuentra los de remitente no identificado**, y no hay un filtro
«sin identificar». No lo pide ningún requisito; se anota porque es la pregunta que alguien va a
hacerse frente a la pantalla.

### `POST /messages/{message_id}/resolution`

**`SUPPLIER_MESSAGES` · `WRITE`** — dueño y compras (RF-28).

Sin cuerpo. Quién resolvió sale del token (RF-29).

| Código | Cuándo |
|---|---|
| `200` | `MessageRead` en `RESOLVED`, con `resolved_by_user_id` y `resolved_at` |
| `404` | `No encontramos ese mensaje` |
| `409` | `El mensaje ya está resuelto` |

El `409` importa: resolver dos veces no es idempotente a propósito, porque el segundo intento
significa que dos personas creyeron tener el mismo pendiente, y eso es información.

Resolver saca al mensaje del resumen diario a partir de la corrida siguiente (RF-40).

### `PUT /messages/{message_id}/assignee`

**`SUPPLIER_MESSAGES` · `WRITE`** — dueño y compras (RF-30).

```
{ assignee_user_id: int | null }
```

`null` deja el mensaje sin responsable. **Es un `PUT` porque reemplaza el valor entero**, y por eso
desasignar es el mismo verbo que asignar.

> **Dos cosas que este contrato promete y hoy no cumple** (`plan.md` → D-3): el requisito dice «al
> dueño o a una persona del rol compras» y **el backend acepta cualquier `user_id`**, ventas
> incluido; y **ninguna pantalla llama a esta ruta**. La Server Action existe
> (`frontend/app/actions/messaging.ts:49-57`) y no la usa nadie.

### `POST /messages/{message_id}/note`

**`SUPPLIER_MESSAGES` · `WRITE`** — dueño y compras (RF-32).

```
{ note: str }   // 1..2000
```

Reemplaza la nota anterior; no acumula. La spec pide *«escribir una nota sobre un mensaje»*, en
singular, y una lista de notas habría sido una tabla que nadie pidió.

---

## El ruteo de los avisos

`backend/app/modules/notifications/routes.py` · `router`, prefijo `/alerts`

### `GET /alerts/routes`

**`SYSTEM_PARAMETERS` · `READ`** — sólo el dueño (RF-37).

Devuelve **los tres tipos siempre**, configurados o no. Los que nadie tocó muestran el valor firmado,
que es el que la plataforma está obedeciendo de verdad — una lista que sólo mostrara lo configurado
le mentiría al dueño sobre qué está pasando.

```
[ { kind, role, updated_by_user_id?, updated_at?, recipients } ]
```

`recipients` es cuántas personas tienen hoy ese rol **y siguen teniendo acceso**. Se muestra porque
una ruta apuntada a un rol que nadie ocupa es una ruta que no entrega nada, y el dueño tiene que
verlo antes de que un aviso no llegue. (Si eso pasa igual, `phones_for` cae al dueño en vez de
descartar el aviso.)

### `PUT /alerts/routes/{kind}`

**`SYSTEM_PARAMETERS` · `WRITE`** — sólo el dueño (RF-37).

```
{ role: str }   // "OWNER" | "PURCHASING" | "SALES"
```

`kind` va en la ruta y se valida contra el enum: un tipo inventado da `422`.

> **`role` es un `str` sin validar contra los tres roles.** Un `role: "GERENTE"` se acepta, se
> guarda, y a partir de ahí ese tipo de aviso no le llega a nadie — salvo por el respaldo al dueño de
> `phones_for`. `notifications` no puede importar `UserRole` de `identity` (Artículo IV), así que la
> salida limpia es un `Literal` en el schema o un enum en `shared/`. Está sin hacer y no lo pide
> ningún requisito.

---

## Lo que ninguna ruta expone, a propósito

- **La franja horaria y la hora del resumen** se ajustan en el panel de parámetros de la 003, no acá.
  Es la regla de negocio de la spec: *«no hay valores escondidos en las pantallas de órdenes ni de
  mensajes»*.
- **Disparar un aviso a mano.** No lo pide ningún requisito, y una ruta que manda un WhatsApp a
  pedido es una ruta que alguien va a usar para probar en producción.
- **Marcar un mensaje como leído en el portal.** El Artículo I: por el portal no sale nada.
