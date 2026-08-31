# Órdenes de compra y avisos — Plan técnico

<!--
  ARTEFACTO INTERNO. No se exporta al cliente.
-->

**Feature:** 007-orders-alerts · **Spec aprobada el:** 2026-08-31 · **Fecha:** 2026-08-30
**Rol:** `Backend-Architect` · `Frontend-Architect`

## Constitution Check

| Artículo | Cumple | Cómo |
|---|---|---|
| I — El origen es ajeno y de sólo lectura | Sí | Dos lecturas nuevas con Playwright: `/ordenes-compra` y `/mensajes` |
| II — Nada se descarta | Sí | Un mensaje cuyo tipo no se reconoce **se muestra** sin clasificar (RF-25); uno cuyo remitente no se identifica se muestra diciéndolo (RF-24). Un aviso que no se pudo entregar queda señalado en la pantalla (RF-38) |
| III — Flujo unidireccional, `raw` inmutable | Sí | `raw` → `staging.purchase_order_row` / `staging.message_row` → `core` |
| IV — Las fronteras entre módulos son reales | Sí | `messaging` es nuevo y no importa a nadie: identifica al remitente contra **su propia proyección** del padrón, alimentada por `SuppliersNormalized`. El resumen diario se arma preguntando, ver abajo |
| **V — Spec primero, y con firma** | **Fuera de orden** | Firmada el 2026-08-31, después de construir. Ver abajo |
| VI — Lo que no está tipado y testeado no está terminado | Parcial | 14 tests de integración y 4 unitarios del parser. **Los fixtures de `/mensajes` son derivados, no capturados**, ver abajo |
| VII — Las credenciales de terceros viven sólo en el entorno | Sí | Se reusa el cliente de `portal` |
| VIII — Un idioma para cada audiencia | Sí | |
| IX — Las dependencias entran por la puerta | Sí | Cero dependencias nuevas |

### Excepción al Artículo V, y quién la aprobó

El Artículo V dice que ninguna feature pasa a planificación técnica sin firma, y que una excepción
**la aprueba el humano y queda registrada en el plan**. Pasó en dos momentos, como en la 006.

**Al construir, el 2026-08-30.** El humano pidió implementar las seis specs pendientes y, consultado
sobre las tres que estaban en borrador, respondió *"Las seis, igual"*.

**Al firmar, el 2026-08-31.** Antes de la firma, una auditoría recorrió la spec contra el paso 1 de
`approve_spec.md` y encontró bloqueos reales, que se cerraron escribiendo lo que ya estaba acordado
en el brief, en otra spec firmada o en el código —nunca con una decisión de producto nueva—. Cada
elección quedó listada en la sección **«Para confirmar al firmar»** de `spec.md`.

Al firmar, el alcance creció: trece requisitos nuevos (RF-50 a RF-62) y una historia, H8. No son alcance inventado —RF-08 ya apartaba las órdenes sin proveedor y mandaba a una «revisión» que el documento no definía en ninguna parte, y la salida está calcada de lo firmado para las facturas en P2 y P4—, pero **el código se construyó antes de que esos trece existieran**. Es la primera cosa que tiene que mirar `/converge`.

Queda dicho, porque el orden importa y este documento es donde consta: **se firmó sobre código ya
construido**. Para esta feature el gate del Artículo V es un registro, no un filtro — no hubo un
momento en que el acuerdo pudiera haber cambiado lo que se construía. Lo que el gate sí puede hacer
todavía es `/converge`.

## Enfoque

**Desde cuándo una orden está donde está no lo dice el portal.** Publica una sola fecha, la del
pedido. Así que el tiempo en un estado se cuenta desde que **esta plataforma** observó la orden ahí
(`status_since`), y las órdenes que ya existían cuando arrancó el sistema dicen otra cosa: cuántos
días pasaron desde el pedido (RF-49). Son dos números distintos y la pantalla no los confunde.

**El resumen diario se arma preguntando.** Es un mensaje sobre el negocio de dos módulos que no
pueden leerse entre sí, y que `notifications`, que lo manda, tampoco puede leer. Entonces
`notifications` publica `DailyDigestRequested` y cada módulo contesta con un
`DailyDigestContribution`. El bus es en proceso y sincrónico: cuando `publish` vuelve, están todas
las respuestas. Es lo que motivó agregar `EventBus.unsubscribe`, y su docstring explica que es para
una suscripción **temporal** y para nada más.

**Los destinatarios son una proyección.** `operations.notification_recipient` la alimenta `identity`
con `UserRegistered`, `UserDeactivated`, `UserReactivated` y `UserRoleChanged`. La consecuencia
buena: RF-45 —quien pierde el acceso deja de recibir avisos— **no es una regla que alguien tenga que
recordar**, es lo que pasa cuando llega `UserDeactivated`.

`UserRegistered` suma el teléfono. Es un evento en proceso que no se persiste y, a diferencia de
`UserInvited`, no lleva ninguna credencial.

## Lo que hay que saber antes de confiar en esto

> **El fixture de `/mensajes` es derivado, no capturado.** El relevamiento contó qué hay en esa
> pantalla —64 mensajes, 27 de vencimiento, 21 reclamos, 16 de stock, 30 sin leer— pero no guardó el
> DOM. `scripts/fixtures/derive_portal_fixtures.py` genera un archivo que reproduce esos números con
> la estructura que sí se capturó en las otras cuatro pantallas.
>
> **Las columnas son una deducción.** El día que alguien pueda entrar al portal hay que recapturar y
> volver a correr los tests del parser. Si las columnas se llaman distinto, `parse_messages` levanta
> `ExtractionError` y el fallo queda visible en `operations`, que es exactamente lo que tiene que
> pasar — pero es una lectura que todavía no se probó contra la realidad.

## Módulos afectados

| Módulo | Qué cambia | Nuevo |
|---|---|---|
| `portal` | Lee `/ordenes-compra` y `/mensajes` | No |
| `ingestion` | `staging.purchase_order_row`, `staging.message_row` y sus parsers | No |
| `purchases` | `core.purchase_order`, el estancamiento y el pedido repetido | No |
| `messaging` | **Todo lo de la bandeja**, más su proyección del padrón | **Sí** |
| `notifications` | Destinatarios, ruteo por tipo de aviso, franja horaria y resumen diario | No |

## Contratos

| Ruta | Quién | Requisitos |
|---|---|---|
| `GET /purchase-orders` | dueño · compras | RF-02 a RF-07, RF-12, RF-13 |
| `DELETE /purchase-orders/{id}/repeat-flag` | dueño · compras | RF-18, RF-19 |
| `GET /messages` | dueño · compras | RF-22 a RF-26, RF-31 |
| `POST /messages/{id}/resolution` | dueño · compras | RF-28, RF-29 |
| `PUT /messages/{id}/assignee` · `POST /messages/{id}/note` | dueño · compras | RF-30, RF-32 |
| `GET`/`PUT /alerts/routes` | dueño | RF-37 |

Ventas no llega a ninguna (RF-09, RF-46), y lo verifica `test_route_authorization.py`.

## Contexto de traspaso

**Para el Developer** — Lo decidido y que no se rediscute: `messaging` es un módulo aparte y no
importa a `purchases`; el ruteo de avisos es por **rol** y no por persona, con los valores firmados
en código y la tabla sólo para lo que el dueño cambie; y un aviso fuera de franja **se demora**, no
se descarta (RF-42), con el `countdown` del broker y no con un proceso esperando.

**Para el Tester** — Lo que falla en silencio: que en la **primera** lectura de la bandeja no se
despierte a nadie (RF-47) — si se rompe, la puesta en marcha manda sesenta y cuatro avisos—; y que
una orden recibida no cuente como estancada por más que lleve meses.

**Para el Code-Reviewer** — `GEN-02` sobre `messaging`, que es donde más fácil aparecería el import
a `purchases` para leer el padrón. Y el `unsubscribe` nuevo del bus: verificar que sólo lo usa el
resumen diario y que está en un `finally`.
