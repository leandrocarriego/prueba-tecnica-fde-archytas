# Órdenes de compra y avisos — Plan técnico

<!--
  ARTEFACTO INTERNO. Acá van las decisiones técnicas que spec.md no puede llevar.
  No se exporta al cliente.
-->

**Feature:** 007-orders-alerts · **Spec aprobada el:** 2026-08-31 · **Fecha:** 2026-08-31
**Roles:** Backend-Architect (los dos módulos, el ruteo de avisos) · Frontend-Architect (las dos pantallas)

Insumos: `spec.md` firmada (RF-01 a RF-62, ocho historias), los diagramas de `diagrams/`, y el
código construido en `backend/app/modules/{purchases,messaging,notifications,ingestion,portal}/` y
`frontend/`.

> **Este plan es un acta con una parte de pronóstico.** El grueso de la feature se construyó el
> 2026-08-30, **antes** de que existiera este documento y antes de la firma. Lo que sigue describe
> **lo que hay**, verificado archivo por archivo. Pero al firmar el alcance creció —trece requisitos
> nuevos, RF-50 a RF-62, y una historia entera, la H8— y **de esos trece, once no están
> construidos**. Ese tramo no es acta: es plan, y tiene su sección propia, *Lo que falta: la H8*.

## Constitution Check

| Artículo | Cumple | Cómo |
|---|---|---|
| I — El origen es ajeno y de sólo lectura | Sí | Dos lecturas nuevas con automatización de navegador: `/ordenes-compra` y `/mensajes` (`portal/service.py:181-218`). Ningún endpoint JSON interno, ninguna escritura. La spec declara fuera de alcance contestarle al proveedor |
| II — Nada se descarta | **Parcial** | **Lo que se cumple:** un mensaje cuyo tipo no se reconoce se muestra sin clasificar (`messaging/service.py:120-122`, RF-25) y uno cuyo remitente no se identifica se muestra diciéndolo (`:124-137`, RF-24); una orden sin proveedor entra igual, en `PENDING` (`purchases/service.py:1800-1802`, RF-08). **Lo que falta:** `PurchaseOrderRowsQuarantined` se publica (`ingestion/service.py:633`) y **nadie está suscripto**, así que una fila de `/ordenes-compra` que no se pudo tipar queda en `staging` y no genera fila en `operations.exception`. La brecha es transversal —la comparten 004, 005 y 009— y está anotada en los tres planes. Ver *Riesgos* y D-1 |
| III — Flujo unidireccional, `raw` inmutable | Sí | `raw` → `staging.purchase_order_row` / `staging.message_row` → `core.purchase_order` / `core.supplier_message` (`ingestion/models.py:311-376`). Nada de esta feature escribe en `raw` |
| IV — Las fronteras entre módulos son reales | Sí | `messaging` no importa a nadie: identifica al remitente contra **su propia proyección** del padrón (`core.messaging_supplier`), alimentada por `SuppliersNormalized`. `notifications` no lee `identity`: mantiene `operations.notification_recipient`, alimentada por cuatro eventos de acceso. El resumen diario se arma preguntando, ver *Enfoque*. El único import cruzado del changeset es `identity.dependencies`, la excepción fijada por nombre de archivo |
| **V — Spec primero, y con firma** | **Fuera de orden** | Firmada el 2026-08-31, después de construir. Ver abajo |
| VI — Lo que no está tipado y testeado no está terminado | **Parcial** | Tipos completos, `mypy` limpio. 14 tests de integración (`tests/integration/features/test_orders_and_messages.py`) y 4 unitarios de parser (`tests/unit/ingestion/test_section_parsers.py:145-193`). Los tres huecos de cobertura que este documento listaba —la franja, el resumen y el ruteo— **quedaron cubiertos** el 2026-08-31 (`tests/integration/features/test_alert_routing.py`), y el fixture de la bandeja **se capturó del portal real**. Ver *Lo que hay que saber antes de confiar en esto*: la captura destapó dos defectos que ningún test podía ver |
| VII — Las credenciales de terceros viven sólo en el entorno | Sí | Se reusa el cliente de `portal`, cuyo envoltorio de errores está testeado en `test_alerts_and_guards.py:264-289`. El aviso viaja por `send_alert` y **no lleva ninguna credencial**, a diferencia de `send_access_link` |
| VIII — Un idioma para cada audiencia | Sí | Código y eventos en inglés; los textos de los avisos (`notifications/service.py`) y las dos pantallas, en español |
| IX — Las dependencias entran por la puerta | Sí | Cero dependencias nuevas. `rapidfuzz` y `celery` ya estaban |

### Excepción al Artículo V, y quién la aprobó

El Artículo V dice que ninguna feature pasa a planificación técnica sin firma, y que una excepción
**la aprueba el humano y queda registrada en el plan**. Pasó en dos momentos, como en la 006.

**Al construir, el 2026-08-30.** El humano pidió implementar las seis specs pendientes y, consultado
sobre las tres que estaban en borrador, respondió *"Las seis, igual"*. Se construyó sin acuerdo del
cliente, sabiendo que si al firmar pedía cambios el costo sería de rehacer, no de construir.

**Al firmar, el 2026-08-31.** Antes de la firma, una auditoría recorrió la spec contra el paso 1 de
`approve_spec.md` y encontró bloqueos reales, que se cerraron escribiendo lo que ya estaba acordado
en el brief, en otra spec firmada o en el código —nunca con una decisión de producto nueva—. Cada
elección quedó listada en la sección **«Para confirmar al firmar»** de `spec.md`.

**Y al firmar el alcance creció.** Trece requisitos nuevos —RF-50 a RF-62— y una historia, la H8. No
es alcance inventado: RF-08 ya apartaba las órdenes sin proveedor y las mandaba a una «revisión» que
el documento no definía en ninguna parte, y la salida está calcada de lo firmado para las facturas en
P2 y P4. Pero **el código se construyó antes de que esos trece existieran**, y once de ellos siguen
sin construirse. Es la primera cosa que tiene que mirar `/converge`, y tiene su sección abajo.

Queda dicho, porque el orden importa y este documento es donde consta: **se firmó sobre código ya
construido**. Para el tramo RF-01 a RF-49 el gate del Artículo V es un registro, no un filtro — no
hubo un momento en que el acuerdo pudiera haber cambiado lo que se construía. Para la H8 sí lo es:
está firmada y no está hecha, así que ahí el acuerdo llegó a tiempo.

**Excepciones solicitadas:** la del Artículo V, ya registrada. Ninguna otra.

## Lo que hay que saber antes de confiar en esto

> **El fixture de `/mensajes` ya no es derivado: se capturó del portal real el 2026-08-31**
> (`messages-page-2026-08-31.html`, 67 mensajes, 33 sin leer). Y hay que leer lo que la captura
> encontró, porque cambia cómo se mira el resto de esta feature.
>
> **Dos defectos que los tests no podían ver:**
>
> - **La bandeja no está en `/mensajes`.** Está en `/mensajes-internos`, y esa ruta devolvía 404: la
>   lectura nocturna fallaba **siempre**, desde el primer día. Corregido en `portal/client.py`.
> - **No hay columna `Tipo`.** Las columnas reales son `Fecha`, `Remitente`, `Asunto` y `Estado`. El
>   parser leía un `Tipo` inexistente, así que los sesenta y siete mensajes entraban
>   `UNCLASSIFIED` — y con eso **RF-33 y RF-34 no podían dispararse nunca**. El tipo está en el
>   asunto: «Reclamo de pago - F-1809». Corregido en `parse_messages`, y los tres tipos firmados
>   aparecen con 27 vencimientos, 24 reclamos y 16 de stock.
>
> **Los dos tests del parser pasaban todo ese tiempo.** Corrían contra un fixture derivado que
> reproducía la deducción, así que probaban la deducción. Es el argumento entero a favor de capturar:
> `TEST-03` dice que un parser no se prueba contra el portal en vivo, no que se pruebe contra algo
> inventado.
>
> **El de `/ordenes-compra` sí era capturado** desde el principio, y por eso no tuvo ninguna sorpresa.

## Lo que falta: la H8, y RF-38

> **Decidido el 2026-08-31 por Leandro Carriego — FDE: la H8 se construye antes del PR.** Deja de
> ser deriva a la espera de una decisión y pasa a ser el trabajo de esta feature. Lo que sigue es su
> plan, no su acta.
>
> **Y RF-38 también se decidió, el mismo día y por el mismo humano: se resuelve con un evento
> `AlertDeliveryFailed`.** Las dos cosas que faltaban en esta feature pasan a estar planificadas.

### La H8 — once de sus trece requisitos no están construidos

La orden sin proveedor **se aparta bien** —eso es RF-08 y está hecho— y después no hay nada. No
existe ninguna ruta para resolverla, ni conteo, ni filtro.

| RF | Lo que pide | Qué hay hoy |
|---|---|---|
| RF-50 | Mostrarla con el nombre tal como llegó y señalada | **Está.** `supplier_text` viaja en el schema y `OrderTable.tsx:74-76` dibuja «*nombre* · sin identificar» cuando no hay `supplier_name` |
| RF-51 | Cuántas órdenes están apartadas | ✗ `PurchaseOrderList` lleva `total`, `per_status` y `stalled`, y ningún conteo de apartadas (`purchases/schemas.py:359-365`) |
| RF-52 | Poder pedir sólo las apartadas | ✗ `list_orders` filtra por estado, proveedor y estancadas, y no por `review_state` (`service.py:1813-1822`) |
| RF-53 | Sólo dueño y compras resuelven | ✗ No hay ruta que resolver |
| RF-54 | Asignarle un proveedor del padrón | ✗ |
| RF-55 | Apartarla diciendo que el proveedor no está en el padrón | ✗ **El motivo se descarta al registrar**: `register_orders` llama `supplier, _ = await self.resolve_supplier(...)` (`service.py:1766`) y tira la razón, que es justamente `OUTSIDE_REGISTER` o `AMBIGUOUS_SUPPLIER`. `core.purchase_order` **no tiene columna `review_reason`**, a diferencia de `core.invoice` |
| RF-56 | Registrar quién la resolvió y cuándo | ✗ No hay columnas `resolved_by_user_id` / `resolved_at` en `core.purchase_order` |
| RF-57 | Que salga de las apartadas | ✗ |
| RF-58 | Una grafía ya asignada entra identificada, sin apartarse | **Está, y gratis.** `resolve_supplier` consulta `supplier_alias` antes que nada (`service.py:454-456`), y esa tabla es la misma que usan las facturas |
| RF-59 | Sin proveedor, no se la señala como repetida | **Está.** `earlier_order_for` devuelve `None` si `supplier_id is None` (`repository.py:637-639`) |
| RF-60 | Al resolverla, evaluar si repite un pedido anterior | ✗ |
| RF-61 | Guardar la grafía como criterio | ✗ |
| RF-62 | Aplicar esa decisión a las otras apartadas escritas igual | ✗ `_apply_alias` recorre `pending_invoices()` y sólo facturas (`service.py:979-990`) |

**Lo que hay que construir, y de dónde se copia.** El mecanismo entero existe a doscientas líneas de
distancia, para las facturas, y es lo que la spec dice explícitamente que se replica: *«es el mismo
criterio con el que ya se resuelven las facturas»*. El molde es
`# --- Deciding about an invoice held for review ---` (`service.py:842-1010`), con cuatro piezas:

1. **`core.purchase_order` necesita tres columnas**: `review_reason`, `resolved_by_user_id`,
   `resolved_at`, y una migración propia (ver *Datos*).
2. **`register_orders` deja de tirar el motivo** (`service.py:1766`): la razón que devuelve
   `resolve_supplier` va a `review_reason`, y eso es RF-55.
3. **Un `resolve_order(order_id, supplier_id, actor_user_id)`** que asigne el proveedor, marque
   `RESOLVED`, guarde quién y cuándo (RF-54, RF-56, RF-57), aprenda la grafía como
   `SupplierAlias(source=LEARNED)` (RF-61) y la aplique a las demás apartadas (RF-62) — y que
   **después** vuelva a evaluar el pedido repetido, que es RF-60 y es lo único que no tiene análogo
   en facturas.
4. **`_apply_alias` se generaliza a las órdenes.** Hoy sólo mira facturas, y la spec advierte que el
   criterio es **uno solo para las dos cosas**: resolver una orden identifica también las facturas
   que esperaban esa grafía, y al revés. Esa reciprocidad es alcance firmado, no un extra.

Del lado de la pantalla: un conteo y un filtro en `/ordenes` (RF-51, RF-52) y un selector de
proveedor en la fila apartada. La spec es explícita en que **no** hay pantalla de revisión aparte
(*«se la pide desde la misma lista de órdenes»*), y en que una orden apartada **no lleva
responsable**.

### RF-38 — el aviso que falló se muestra y nunca se escribe

`MessageRead.alert_failure` viaja, y `MessageList.tsx:84-88` lo dibuja con su cartel. El servicio
tiene el método que lo escribe, `record_alert_failure` (`messaging/service.py:209-221`), con su
docstring explicando por qué existe. **Nadie lo llama.** La entrega falla dentro de
`notifications.tasks.send_alert`, que reintenta dos veces y devuelve `{"sent": False}` sin avisarle a
nadie: el fallo termina siendo una línea de log y un job con resultado, no una marca en la pantalla.

Es media línea de diseño y no una línea de código: `send_alert` corre en el worker, no conoce el
`message_id` —hoy recibe sólo teléfono y texto— y `notifications` no puede llamar a `messaging`
(Artículo IV).

**Decidido el 2026-08-31 por Leandro Carriego — FDE: se resuelve con un evento.** Se descartó
guardar el fallo en una tabla propia de `notifications` y componer la pantalla desde dos endpoints
—más limpio conceptualmente, porque entregar es su dominio, y más caro: tabla, migración, ruta y
frontend, y dejaría muerta la columna `alert_failure` que ya existe—. Y se descartó dejarlo abierto,
porque un cartel que nunca se enciende es una promesa muerta en el código.

Cómo queda:

1. **`send_alert` recibe además el `message_id`**, nulable. `_deliver` (`notifications/handlers.py:189-204`)
   se lo pasa cuando el aviso viene de un mensaje de la bandeja, y `None` cuando viene de
   `InvoiceDueSoon`, que es de la 005 y no tiene mensaje detrás.
2. **Cuando se agotan los reintentos**, la task publica
   `AlertDeliveryFailed(message_id, kind, reason)`. Necesita sesión propia: la abre con
   `SessionFactory`, exactamente como ya hace `daily_digest` (`tasks.py:118-135`).
3. **`messaging` se suscribe** y llama a `record_alert_failure`, que ya existe y ya escribe la
   columna que la pantalla ya dibuja. **No se toca el frontend.**

**Cuándo cuenta como fallado, que es la parte que hay que decidir al escribirlo:** hoy `send_alert`
reintenta dos veces y **no reintenta** cuando el canal no está configurado (`NOT_CONFIGURED`), porque
eso no es un fallo transitorio. Las dos salidas terminan en «no llegó», así que las dos publican; lo
que no puede pasar es publicar en el **primer** intento, porque un aviso que el segundo intento
entrega dejaría la pantalla diciendo que falló algo que sí llegó.

**Un aviso con `message_id` nulo se publica igual y nadie lo registra.** Es a propósito: la 005 no
tiene un RF-38 propio, y el evento queda listo para el día que lo tenga.

## Enfoque

**Desde cuándo una orden está donde está no lo dice el portal.** Publica una sola fecha, la del
pedido. Así que el tiempo en un estado se cuenta desde que **esta plataforma** observó la orden ahí
(`purchase_order.status_since`, puesto en `today_here()` al registrarla), y cuando la orden aparece
en otro estado el reloj se reinicia (`service.py:1770-1777`), que es RF-48 y de paso hace que RF-14
—una orden que avanza deja de estar señalada— no necesite que nadie limpie un flag. Las órdenes que
ya existían cuando arrancó el sistema dicen otra cosa: `observed_from_start=False` y la pantalla
muestra «pedida hace N días» en vez de «N días observada así» (`OrderTable.tsx:84-86`), que es RF-49.
Son dos números distintos y la pantalla no los confunde.

**El estancamiento no se guarda: se calcula en cada lectura.** `_is_stalled` compara los días en el
estado contra el parámetro (`service.py:1854-1862`), y devuelve `False` para una orden recibida sin
mirar nada más, que es la regla de negocio *«una orden recibida ya llegó y no se estanca»*. Guardar
un booleano habría creado una segunda verdad que hay que recalcular cada vez que el dueño mueve el
parámetro; calcularlo hace que RF-11 —cambiar el límite cambia qué órdenes quedan señaladas— sea
gratis.

**El resumen diario se arma preguntando.** Es un mensaje sobre el negocio de dos módulos que no
pueden leerse entre sí, y que `notifications`, que lo manda, tampoco puede leer. Entonces
`notifications` publica `DailyDigestRequested` y cada módulo contesta con un
`DailyDigestContribution` (`purchases/handlers.py:112-131`, `messaging/handlers.py:43-62`). El bus es
en proceso y sincrónico: cuando `publish` vuelve, están todas las respuestas. Es lo que motivó
agregar `EventBus.unsubscribe` (`shared/events/bus.py:60-72`), y su docstring explica que es para una
suscripción **temporal** y para nada más — el acumulador es de esa corrida, y un handler a nivel de
módulo lo compartirían todos los resúmenes que el proceso mande en su vida.

**Beat despierta el resumen cada hora y la task decide si es la hora.** `_is_the_hour`
(`notifications/tasks.py:141-146`) lee el parámetro en cada corrida en vez de escribirlo en el
`crontab`. Es lo que hace que cambiar la hora del resumen valga desde el día siguiente y no desde un
redeploy — el mismo criterio que la actualización de precios.

**Fuera de la franja el aviso se demora, no se descarta.** `delay_until_window`
(`notifications/delivery.py:59-83`) devuelve segundos, nunca un «no», y el `countdown` se lo come el
broker (`handlers.py:189-204`). Un aviso que tiene que salir a las ocho de la mañana no depende de que
haya un worker vivo a medianoche esperándolo. Sábado 22:00 → lunes 08:00, que es el criterio de
aceptación de RF-42 al pie de la letra.

**Los destinatarios son una proyección.** `operations.notification_recipient` la alimenta `identity`
con `UserRegistered`, `UserDeactivated`, `UserReactivated` y `UserRoleChanged`
(`notifications/handlers.py:128-153`). La consecuencia buena: RF-45 —quien pierde el acceso deja de
recibir avisos— **no es una regla que alguien tenga que recordar**, es lo que pasa cuando llega
`UserDeactivated`. `UserRegistered` suma el teléfono; es un evento en proceso que no se persiste y,
a diferencia de `UserInvited`, **no lleva ninguna credencial** (Artículo VII).

**El ruteo es por rol y no por persona, con una salida de emergencia.** `phones_for`
(`delivery.py:42-58`) traduce el tipo de aviso a un rol y el rol a los teléfonos activos; si nadie
tiene ese rol en este momento, **el aviso cae al dueño** en vez de desaparecer. Los valores firmados
—reclamos y vencimientos a compras, resumen al dueño— viven en código (`notifications/service.py:191-195`) y
la tabla guarda sólo lo que el dueño cambie, que es como se comporta todo valor inicial de la
plataforma.

**La primera lectura de la bandeja no despierta a nadie.** `first_run` lo decide `ingestion`
preguntándole a `staging` si ya tipeó mensajes alguna vez (`ingestion/service.py:651`), y viaja en el
evento hasta `register_messages`, que registra todo como pendiente y no publica ningún
`SupplierMessageReceived` (`messaging/service.py:100-114`). Es RF-47, y sin eso la puesta en marcha
manda sesenta y cuatro avisos.

## Módulos afectados

| Módulo | Qué cambia | Nuevo |
|---|---|---|
| `portal` | Dos lecturas: `extract_purchase_orders` y `extract_messages` (`service.py:181-218`), con su task cada una (`tasks.py:183-195`) | No |
| `ingestion` | `staging.purchase_order_row` y `staging.message_row` (`models.py:311-376`), sus dos parsers (`parsers.py:858-1013`) y sus dos normalizaciones (`service.py:600-702`) | No |
| `operations` | Dos entradas en `SYNC_JOBS` —`purchase_orders` y `messages`— con su parámetro de intervalo (`service.py:160-174`), y dos parámetros más en el panel | No |
| `purchases` | `core.purchase_order`, el bloque `# --- The purchase orders (007) ---` (`service.py:1746-1879`), el bloque de repositorio (`repository.py:587-651`), dos schemas, dos rutas y la contribución al resumen (`handlers.py:112-131`) | No |
| `messaging` | **Todo lo de la bandeja**: `core.supplier_message`, su proyección del padrón `core.messaging_supplier`, la clasificación, la identificación del remitente, el estado y el responsable | **Sí** |
| `notifications` | Destinatarios, rutas de aviso, franja horaria, el resumen diario y la task `send_alert` | No |
| `identity` | **Nada propio.** `Section.PURCHASE_ORDERS` y `Section.SUPPLIER_MESSAGES` los fija la 002, y esta feature los consume | No |
| Frontend | Dos pantallas (`/ordenes`, `/mensajes`), dos componentes (`OrderTable.tsx`, `MessageList.tsx`), `app/actions/messaging.ts` y dos entradas del menú | No |

**`messaging` es un módulo nuevo y está justificado.** Una bandeja de mensajes de proveedores tiene
lenguaje propio —remitente, tipo, estado, responsable, nota— que no es el de una factura ni el de una
orden, y lo único que necesita del resto del negocio es *quiénes son los proveedores*, que le llega
como proyección. Si en vez de eso viviera en `purchases`, el módulo más grande del repositorio
—1.964 líneas de servicio— sumaría un cuarto dominio.

## Eventos de dominio

Todos son del catálogo compartido (`backend/app/shared/events/catalog.py`), en pasado, `frozen`, con
identificadores y valores planos: `GEN-08` cumplido.

### Los que esta feature publica

| Evento | Lo publica | Lo consume | Qué lleva |
|---|---|---|---|
| `PurchaseOrdersExtracted` (`:826`) | `portal` | `ingestion` | El documento crudo de `/ordenes-compra` |
| `PurchaseOrdersNormalized` (`:851`) | `ingestion` (`service.py:608`) | `purchases` (`handlers.py:99`) | `batch_id` y las órdenes tipadas |
| `PurchaseOrderRowsQuarantined` (`:862`) | `ingestion` (`service.py:633`) | **nadie** | Las filas que no se pudieron tipar. **Es un hallazgo**, ver D-1 |
| `SupplierMessagesExtracted` (`:878`) | `portal` | `ingestion` | El documento crudo de `/mensajes` |
| `SupplierMessagesNormalized` (`:902`) | `ingestion` (`service.py:691`) | `messaging` (`handlers.py:34`) | Los mensajes nuevos y el flag `first_run` (RF-47) |
| `SupplierMessageReceived` (`:915`) | `messaging` (`service.py:104`) | `notifications` (`handlers.py:180`) | `message_id`, `kind`, `supplier_name`, `subject`, `body`, `received_at`. **Sólo para los dos tipos urgentes** (RF-33, RF-34) |
| `AlertDeliveryFailed` — **a crear** | `notifications.tasks.send_alert`, al agotar los reintentos | `messaging` | `message_id` (nulable), `kind`, `reason`. Es RF-38, decidido el 2026-08-31. Ver *Lo que falta* |
| `DailyDigestRequested` (`:986`) | `notifications.tasks.daily_digest` | `purchases` y `messaging` | La fecha. Es una **pregunta**, no un hecho, y es la única del catálogo |
| `DailyDigestContribution` (`:993`) | `purchases` y `messaging` | el acumulador temporal de la task | `source`, `pending`, `lines` |

### Los que esta feature consume sin publicar

`SuppliersNormalized` alimenta la proyección del padrón de `messaging` (`handlers.py:28`).
`UserRegistered`, `UserDeactivated`, `UserReactivated` y `UserRoleChanged` alimentan los
destinatarios. `BusinessParameterChanged` alimenta las dos proyecciones de parámetros —la de
`purchases` (`handlers.py:104-110`, filtrada por `WATCHED_PARAMETERS`) y la de `notifications`
(`handlers.py:154-161`, filtrada por tres claves)—.

### El resumen diario merece un párrafo

`DailyDigestRequested` es **una pregunta publicada como evento**, y es la única del catálogo. Se
sostiene porque el bus es en proceso y sincrónico: cuando `publish` vuelve, los handlers ya corrieron
y sus respuestas están en la lista. Si el bus alguna vez se vuelve asincrónico o distribuido, este
mecanismo se rompe en silencio —el resumen saldría vacío, no fallaría—, y es la primera cosa a
revisar el día que eso se discuta. Está anotado acá porque es la clase de supuesto que no se ve
leyendo el código de un solo módulo.

## Datos

Dos tablas nuevas en `core`, dos en `staging`, tres en `operations`, y una proyección. **El detalle
completo —columnas, tipos, índices, qué se calcula y qué se guarda— está en
[`data-model.md`](./data-model.md).** Lo mínimo para orientarse:

- **`core.purchase_order`** — una orden y desde cuándo la plataforma la viene viendo donde está.
  `status_since` es de esta plataforma, no del portal; `observed_from_start` distingue las que ya
  estaban. Único por `number`. **Le faltan las tres columnas de la H8**, ver abajo.
- **`core.supplier_message`** — un mensaje de la bandeja, con su tipo, su estado, su responsable, su
  nota y `alerted_at` para no avisar dos veces (RF-39). Único por `external_id`, que es lo que hace
  idempotente la lectura horaria.
- **`core.messaging_supplier`** — la proyección del padrón que `messaging` compara contra el
  remitente. Es el Artículo IV hecho tabla.
- **`operations.notification_recipient`**, **`notification_route`**, **`notification_setting`** — a
  quién se le avisa, de qué, y dentro de qué franja. Las tres son proyecciones: los datos son de
  `identity` y de `operations`, y este módulo no puede leer sus tablas.
- **`staging.purchase_order_row`** y **`staging.message_row`** — lo tipado, con su `status` y su
  `reason` cuando no se pudo.

**Migraciones:** `0011_invoices_and_suppliers.py` trae `core.purchase_order`,
`staging.purchase_order_row` y `staging.message_row`; `0012_messages_and_sales.py` trae
`core.supplier_message` y `core.messaging_supplier`; `0013_who_gets_told_what.py` trae las tres de
`operations`. `DB-01` se cumple —los modelos están en esas migraciones— pero la `0011` la comparten
cuatro features, y el costo está en *Riesgos*.

**La H8 necesita una migración nueva**, la primera de esta feature que se escriba después del plan:
tres columnas sobre `core.purchase_order` —`review_reason VARCHAR(200) NULL`,
`resolved_by_user_id INTEGER NULL`, `resolved_at TIMESTAMPTZ NULL`— más un índice sobre
`review_state`, que es lo que RF-52 va a filtrar. Ninguna de las tres tiene *backfill*: una orden ya
apartada no sabe por qué lo fue, porque el motivo se descartó al registrarla, y **eso no se puede
reconstruir sin volver a leer el portal**. La migración deja `review_reason` nulo para lo existente y
la pantalla dice «sin identificar» sin motivo, que es lo que hay.

## Contratos

Seis endpoints, todos con su autorización declarada (`PY-09`). **El detalle —query, cuerpos, errores
y códigos— está en [`contracts/orders-and-messages.md`](./contracts/orders-and-messages.md).**

| Método · ruta | Sección · nivel | Quién | RF |
|---|---|---|---|
| `GET /purchase-orders` | `PURCHASE_ORDERS` · `READ` | dueño · compras | RF-02 a RF-07, RF-12, RF-13, RF-49, RF-50 |
| `DELETE /purchase-orders/{id}/repeat-flag` | `PURCHASE_ORDERS` · `WRITE` | dueño · compras | RF-18, RF-19 |
| `GET /messages` | `SUPPLIER_MESSAGES` · `READ` | dueño · compras | RF-22 a RF-27, RF-31 |
| `POST /messages/{id}/resolution` | `SUPPLIER_MESSAGES` · `WRITE` | dueño · compras | RF-28, RF-29 |
| `PUT /messages/{id}/assignee` | `SUPPLIER_MESSAGES` · `WRITE` | dueño · compras | RF-30 |
| `POST /messages/{id}/note` | `SUPPLIER_MESSAGES` · `WRITE` | dueño · compras | RF-32 |
| `GET`/`PUT /alerts/routes[/{kind}]` | `SYSTEM_PARAMETERS` · `READ`/`WRITE` | dueño | RF-37 |

**Ventas no llega a ninguna** (RF-09, RF-46), y no porque estas rutas hagan nada al respecto: la
matriz de `identity` le da `NONE` sobre las dos secciones (`permissions.py:80, 82`). Las rutas
declaran nivel; quién lo tiene se decide en un solo lugar.

**Lo que la H8 va a agregar** (`POST /purchase-orders/{id}/resolution`, más `held` en la lista y
`review_state` en el filtro) está diseñado en el contrato y marcado como no construido.

## Mapa de requisitos

Los 62 firmados, y **los 62 tienen implementación y test** desde el 2026-08-31. Lo que este mapa
listaba como `✗` —RF-38 y once de la H8— se construyó ese día; lo que queda abierto no son
requisitos sin código sino los tres puntos de *Deriva* que van a `/converge`.

| RF | Dónde vive |
|---|---|
| RF-01 | `SyncJob(key="purchase_orders")` (`operations/service.py:160-166`), disparado por `tick_extractions` |
| RF-02 | `PurchaseOrderRead` con `supplier_name`/`supplier_text`, `ordered_on`, `amount`, `status_text` |
| RF-03 | `status_text`, tal como lo escribe el portal. **No hay enum de estados**: el recorrido es el que el portal nombre (ver D-4) |
| RF-04 | `register_orders` reescribe `status_text` cuando difiere (`service.py:1770-1777`) |
| RF-05 | `days_in_status`, calculado contra `status_since` en cada lectura |
| RF-06 | Los parámetros `status_text` y `supplier_id` del `GET` (`repository.py:606-624`) |
| RF-07 | `orders_per_status()` (`repository.py:626-632`), dibujado como los enlaces de filtro |
| RF-08 | `review_state = PENDING` cuando `resolve_supplier` no identifica (`service.py:1800-1802`) |
| RF-09 | `Section.PURCHASE_ORDERS` con `_SALES: Level.NONE` (`permissions.py:80`) |
| RF-10 | `_is_stalled` (`service.py:1854-1862`) |
| RF-11 | `purchase_order.stalled_days`, inicial 15 (`shared/parameters.py:241-246`), proyectado por `BusinessParameterChanged` |
| RF-12 | El parámetro `only_stalled` del `GET` |
| RF-13 | `PurchaseOrderList.stalled` |
| RF-14 | Sale solo: `status_since` se reinicia al cambiar de estado, y `days_in_status` vuelve a cero |
| RF-15, RF-16 | `earlier_order_for` (`repository.py:634-651`) y `repeat_of_order_id`; `repeat_of_number` se resuelve al leer |
| RF-17 | `purchase_order.repeat_window_days`, inicial 15 (`parameters.py:299-305`) |
| RF-18, RF-19 | `DELETE /purchase-orders/{id}/repeat-flag` → `dismiss_repeat` (`service.py:1869-1879`) |
| RF-20 | La orden se registra igual: el flag es una columna, no una condición del `INSERT` |
| RF-21 | `message_sync.interval_minutes`, inicial **30** (`parameters.py:311-317`) — la mitad de la hora que pide el requisito |
| RF-22 | `KINDS` sobre el texto normalizado (`messaging/service.py:37-45`) |
| RF-23 | `_sender_of` contra la proyección del padrón, umbral 88 (`service.py:125-137`) |
| RF-24 | `sender_unidentified`, calculado en cada lectura (`service.py:173-177`); `MessageList.tsx:73-78` |
| RF-25 | `MessageKind.UNCLASSIFIED` como salida por omisión de `_kind_of` |
| RF-26 | Los tres parámetros del `GET`: `kind`, `state`, `supplier_name` |
| RF-27 | `MessageState.PENDING` al registrar |
| RF-28, RF-29 | `POST /messages/{id}/resolution` → `resolve`, con el usuario del token |
| RF-30 | `PUT /messages/{id}/assignee` → `assign`. **Parcial**: ninguna pantalla lo llama, y el backend no valida el rol del asignado (ver D-3) |
| RF-31 | `MessageList.pending` |
| RF-32 | `POST /messages/{id}/note` → `annotate` |
| RF-33, RF-34 | `SupplierMessageReceived` → `warn_about_a_message` (`notifications/handlers.py:177-187`) |
| RF-35 | `notifications.tasks.daily_digest`, armado por `DailyDigestRequested` |
| RF-36 | `daily_digest.time`, inicial `08:00`, leída en cada corrida por `_is_the_hour` |
| RF-37 | `notification_route` + `DEFAULT_ROUTES`, y `GET`/`PUT /alerts/routes` |
| RF-38 | `AlertDeliveryFailed`, publicado por `send_alert` **al agotar los reintentos** y consumido por `messaging`, que escribe `alert_failure`. La pantalla ya lo dibujaba |
| RF-39 | `message.alerted_at` y el `if not first_run and message.kind in URGENT` que sólo corre para mensajes nuevos: un mensaje ya registrado se saltea por `external_id` (`service.py:87-89`) |
| RF-40 | `pending_messages()` filtra por `PENDING` (`messaging/handlers.py:52`) |
| RF-41 | Una sola contribución por corrida del resumen, y el resumen corre una vez al día |
| RF-42 | `delay_until_window` como `countdown` de la task |
| RF-43 | `alerts.window_start` / `alerts.window_end`, iniciales `08:00`/`18:00`, más `WORKING_DAYS` |
| RF-44 | `send_alert(phone, message)`, con el teléfono de `notification_recipient` |
| RF-45 | `is_active=False` al llegar `UserDeactivated`; `active_with_role` no los devuelve |
| RF-46 | `Section.SUPPLIER_MESSAGES` con `_SALES: Level.NONE` (`permissions.py:82`) |
| RF-47 | `first_run`, decidido en `ingestion/service.py:651` y obedecido en `messaging/service.py:100-113` |
| RF-48 | `status_since = today` cuando el estado difiere |
| RF-49 | `observed_from_start` y `days_since_ordered`; `OrderTable.tsx:84-86` |
| RF-50 | `supplier_text` + la ausencia de `supplier_name`; `OrderTable.tsx:74-76` |
| RF-51, RF-52 | `PurchaseOrderList.held` y el filtro `only_in_review` de `list_orders`, más los dos enlaces de `/ordenes` |
| RF-53 a RF-57 | `POST /purchase-orders/{id}/resolution` con `PURCHASE_ORDERS · WRITE`, y `resolve_order` + `_attach_order`, que guardan proveedor, autor y fecha. El motivo lo conserva `register_orders`, que antes lo tiraba |
| RF-58 | `resolve_supplier` mira `supplier_alias` primero (`service.py:454-456`) |
| RF-59 | `earlier_order_for` devuelve `None` sin proveedor (`repository.py:637-639`) |
| RF-60 a RF-62 | `_attach_order` reevalúa el pedido repetido con el proveedor recién asignado (RF-60), y `_apply_alias` recorre **facturas y órdenes** en la misma pasada (RF-61, RF-62) |

## Alternativas descartadas

- **Guardar `is_stalled` como columna.** Habría hecho el `GET` más barato y habría creado una segunda
  verdad que hay que recalcular cada vez que el dueño mueve `stalled_days`. Se calcula.
- **Un `Enum` para los estados de la orden.** El portal escribe los estados en palabras y no promete
  cuáles son: fijarlos en un enum hace que un estado nuevo del portal **rompa la ingesta** en vez de
  aparecer en la pantalla. `status_text` es un `String(100)` a propósito, y el costo es que RF-03 no
  tiene un recorrido declarado en ningún lado (D-4).
- **`messaging` dentro de `purchases`.** Ver *Módulos afectados*.
- **Que `notifications` lea `identity` para saber a quién avisarle.** Es el import cruzado más
  tentador del changeset y lo prohíbe el Artículo IV. La proyección cuesta una tabla y cuatro
  handlers, y devuelve RF-45 gratis.
- **Un proceso que espere a que abra la franja.** `delay_until_window` calcula un `countdown` y se lo
  da al broker. Un aviso de las ocho de la mañana no puede depender de que un worker siga vivo desde
  la medianoche.
- **Escribir la hora del resumen en el `crontab` de beat.** Cambiar la hora exigiría un redeploy. Beat
  despierta cada hora y la task decide.
- **Un canal alternativo para quien no dé su teléfono.** La spec lo declara fuera de alcance y lo dice
  con todas las letras: para esa persona P8 sigue abierto. No se inventó un correo ni un número del
  negocio.
- **Una bandeja de revisión aparte para las órdenes apartadas.** La spec la descarta: se resuelven
  desde la misma lista. Vale para la H8 cuando se construya.
- **Un catálogo de grafías propio de las órdenes.** El criterio es **uno solo** para facturas y
  órdenes, y la spec lo dice y lo justifica: veinte formas distintas de escribir el mismo nombre, y
  decidir cada una dos veces es la cola que un equipo de tres abandona.

## Riesgos

| Riesgo | Impacto | Cómo se mitiga |
|---|---|---|
| **La H8 está firmada y no está construida.** Once requisitos, y el que más duele es RF-62: hoy cada orden apartada se decidiría de a una, veinte veces según lo que midió el relevamiento | Alto — es una historia entera de las ocho | **Se construye antes del PR** (decidido el 2026-08-31). El riesgo que queda no es que falte: es que se construya distinto del molde de facturas y aparezcan dos criterios de grafía. Lo cubre el punto 1 de la lista del Code-Reviewer |
| **Generalizar `_apply_alias` toca código de la 004 que ya está entregado y testeado.** Es lo que RF-62 exige, y la reciprocidad factura ↔ orden es alcance firmado | Medio | Es la única decisión de diseño que la H8 tiene abierta, y está al principio de la lista del Developer. Los tests de resolución de facturas de la 004 son la red: si se rompen, se rompió la generalización |
| **`PurchaseOrderRowsQuarantined` se publica y nadie escucha.** Una fila de `/ordenes-compra` que no se pudo tipar queda en `staging` y no aparece en ninguna pantalla | Alto — es el Artículo II | Sin mitigar. La brecha es transversal a 004, 007 y 009, y los tres planes la anotan. Se cierra con un handler en `triage`, que es el mismo que ya existe para los precios (`triage/handlers.py:34-51`) |
| **Cero cobertura de la mitad que avisa.** No hay un test de `delay_until_window`, ni del resumen diario, ni de `phones_for`. RF-42 es la regla que impide despertar a alguien un sábado a las once de la noche, y está probada por lectura | Alto, y silencioso: si se rompe, el síntoma es un teléfono que suena de madrugada y un canal que la gente silencia | Sin mitigar. Encabeza la lista del Tester. `TEST-05` mide 80 % sobre `app/` entera, así que este módulo puede quedar flojo sin que el umbral se entere |
| ~~El fixture de `/mensajes` es derivado~~ — **capturado el 2026-08-31**, y la deducción estaba mal en la ruta y en las columnas | Era alto, y se vio recién al capturar | Cerrado. Lo que queda es el riesgo general: **el portal puede cambiar y nada avisa hasta que un parser se rompe**. Sigue valiendo para `sales-page`, que todavía es derivado |
| **RF-21 depende de un parámetro que el dueño puede subir.** El requisito dice «no más de una hora» y el inicial son 30 minutos; nada impide ponerlo en 240 | Bajo | No se valida el rango. Es la clase de cosa que se pone en el panel con un tope y hoy no lo tiene |
| **Migración compartida entre cuatro features.** Un rollback de la 007 no se puede hacer solo: la `0011` se lleva puestas también 004, 005 y 006 | Medio | Se acepta: las cuatro se entregan juntas. Si alguna se difiere, hay que partir la migración antes del merge |
| **El resumen diario supone un bus sincrónico en proceso.** Si el bus cambia, el resumen sale vacío en vez de fallar | Bajo hoy, alto el día que se discuta | Anotado en *Eventos de dominio*. El `unsubscribe` está en un `finally`, que es lo único que hoy lo sostiene |
| **`send_alert` reintenta dos veces y después se rinde en silencio** (`tasks.py:69-83`). Un aviso puede no llegar nunca y no dejar rastro fuera del log | Medio | **Se cierra con `AlertDeliveryFailed`** (decidido el 2026-08-31). El riesgo que queda es de ruido: publicar en el primer intento marcaría como fallado un aviso que el segundo entrega. Se publica al agotar los reintentos, y está dicho en *Lo que falta* |

## Deriva contra la spec firmada (para `/converge`)

**Esto no es alcance nuevo ni una lista de tareas: es lo que no cierra entre el código y lo que se
firmó.** Se anota, no se arregla acá: qué corregir —el código o el acuerdo— lo decide el humano
(Artículo V).

### Requisitos firmados sin correlato en el código

| # | RF | Qué falta | Dónde |
|---|---|---|---|
| **D-0** | **RF-51 a RF-57, RF-60 a RF-62** | **La H8 entera menos RF-50, RF-58 y RF-59.** Detallada arriba, requisito por requisito. **Ya no es material de `/converge`: el 2026-08-31 se decidió construirla antes del PR**, así que para cuando el gate corra, o está hecha o esta fila vuelve a ser deriva | No existe todavía |
| **D-1** | RF-08, y el **Artículo II** | ~~`PurchaseOrderRowsQuarantined` se publica y **nadie está suscripto**~~ **Cerrada el 2026-08-31**, después del `/converge`: `triage/handlers.py::open_unreadable_order_rows` abre un caso `unreadable_order_row`. Lo que sigue abierto es el mismo agujero en la 009 (`SaleRowsQuarantined`), que es material del converge de esa feature. Lo que decía antes: una fila que no se pudo tipar no genera caso en `triage` ni fila en `operations.exception`. No se cuenta, no se ve, nadie la decide | `ingestion/service.py:633` · `triage/handlers.py` (sin handler) |
| **D-3** | RF-30 | `PUT /messages/{id}/assignee` y la Server Action `assignMessage` existen, y **ninguna pantalla las llama**: no hay control para asignar responsable. Además, el criterio de aceptación dice *«Julián no figura entre los asignables»* y **el backend no valida el rol del asignado**: acepta cualquier `user_id`, ventas incluido | `frontend/app/actions/messaging.ts:49-57`, sin uso en `app/` ni en `components/`; `messaging/service.py:193-199` |
| **D-5** | RF-38 | El aviso que no se pudo entregar **se dibuja y nunca se escribe**: `record_alert_failure` no lo llama nadie. **Ya no es material de `/converge`: el 2026-08-31 se decidió resolverlo con `AlertDeliveryFailed`**, y el recorrido está en *Lo que falta* | `messaging/service.py:209-221` (sin llamadores); `notifications/tasks.py:69-83` |

### Código y catálogo sin requisito firmado

| # | Qué | Dónde |
|---|---|---|
| **D-2** | ~~`PurchaseOrdersStalled` existe en el catálogo, se exporta, y no se publica ni se consume en ningún lado.~~ **Cerrada el 2026-08-31**: se quitó la clase del catálogo y su export. El aviso de estancamiento fuera del resumen diario no es alcance firmado; si alguna vez lo fuera, el evento se agrega junto a su publicador | `shared/events/catalog.py`, `shared/events/__init__.py` |

### Requisitos cumplidos que conviene no dar por obvios

- **RF-03 no tiene recorrido declarado.** «El punto del recorrido que va del pedido a la recepción»
  se muestra como el texto que escribe el portal, y la única constante del código que nombra un
  estado es `RECEIVED_STATUS`, usada por `_is_stalled`. Es deliberado (ver *Alternativas
  descartadas*) y hay que saberlo: si el portal escribe «RECIBIDA» con otra grafía, **todas las
  órdenes recibidas pasan a poder estancarse**. Es la dependencia más frágil de la feature y no tiene
  test propio. Se anota como **D-4**.
- **RF-09 y RF-46 salen de la matriz de la 002**, no de estas rutas. La 007 declaró niveles; no
  agregó permisos.
- **RF-39 se cumple por dos mecanismos que se ven distintos y no lo son**: `external_id` único hace
  que un mensaje ya visto no se vuelva a registrar, y `alerted_at` deja constancia. Si alguien
  «arregla» el primero permitiendo re-registrar, el aviso se duplica.
- **RF-14 no tiene código.** Sale de reiniciar `status_since`. Un refactor que «optimice» no tocando
  la fecha cuando el estado cambia lo rompe sin que ningún nombre lo delate.

## Contexto de traspaso

**Para el Developer** — Empezá por **la H8**, que es lo único grande que falta, lo único que se
firmó sabiendo que no estaba, y lo que el 2026-08-31 se decidió construir **antes del PR**. Arrancá
por la migración de las tres columnas, y **copiá el molde de las facturas**: `service.py:842-1010` tiene resuelto todo lo que la H8 pide, con una sola diferencia
—RF-60, volver a evaluar el pedido repetido después de asignar el proveedor— que no tiene análogo.
Antes de la primera línea, cerrá con el arquitecto **una sola cosa**: si `_apply_alias` se generaliza
a las dos entidades o si las órdenes tienen su propio recorrido. La spec dice que el criterio es uno
solo y que la reciprocidad con las facturas es alcance firmado, así que lo más probable es
generalizarlo — pero eso toca código de la 004 que ya está testeado, y hay que decidirlo a propósito
y no de costado.

**Y hay una segunda cosa, más chica: RF-38.** Un evento `AlertDeliveryFailed` publicado por
`send_alert` al agotar los reintentos, y `messaging` suscripto llamando a `record_alert_failure`, que
ya está escrito. **No toques el frontend**: la columna existe y el cartel ya se dibuja. Lo único que
hay que pensar es que `send_alert` también entrega los avisos de la 005, que no tienen mensaje
detrás: el `message_id` viaja nulable y un aviso sin mensaje se publica igual y no lo registra nadie.

Lo que **no** hay que tocar, porque es una decisión tomada:

- **`status_since = today` cuando el estado difiere** (`service.py:1770-1777`). Ahí viven RF-05,
  RF-14 y RF-48 juntos, y ninguno tiene código propio.
- **El `if not first_run` de `register_messages`** (`messaging/service.py:103`). Es RF-47, y si se
  rompe la puesta en marcha manda sesenta y cuatro avisos a tres teléfonos.
- **`delay_until_window` devuelve segundos y nunca un `None`.** La tentación de «si está fuera de
  franja, no mandes» convierte RF-42 en descartar, que es exactamente lo que la spec prohíbe.
- **El `finally` que hace `unsubscribe`** en `daily_digest` (`tasks.py:118-135`). Sin él, cada
  resumen deja un acumulador colgado del bus para siempre.
- **`send_alert` y `send_access_link` son dos tasks con el mismo cuerpo.** No las unifiques: una lleva
  credenciales y la otra no, y leer un log tiene que decir cuál salió (Artículo VII).

Compartís `purchases` con la 004, la 005 y la 006. **De esta feature son**: `PurchaseOrder`,
`OrderReviewState`, el bloque `# --- The purchase orders ---` del repositorio
(`repository.py:587-651`), el bloque `# --- The purchase orders (007) ---` del servicio
(`service.py:1746-1879`), los dos schemas `PurchaseOrder*`, el `orders_router` (`routes.py:577-612`)
y el handler del resumen (`handlers.py:112-131`). Todo lo demás de ese módulo es de otra feature.

**Para el Tester** — Lo que hay son 14 tests de integración
(`tests/integration/features/test_orders_and_messages.py`) y 4 de parser. Cubren el reloj del
estancamiento, el pedido repetido, la clasificación de la bandeja y la primera lectura. **No cubren
nada de lo que avisa.** En orden de lo que puede romperse de verdad:

1. **La franja horaria.** `delay_until_window` **no tiene un solo test**. El caso firmado —sábado
   22:00 → lunes 08:00— y sus vecinos: viernes 19:00, martes 06:00 (que espera dos horas, no
   veintiséis), y el límite exacto de las 18:00. Si esto se rompe, el síntoma es un teléfono que suena
   de madrugada, la gente silencia el canal, y la feature entera deja de existir.
2. **El resumen diario.** Tampoco tiene test. Que se arme preguntando —los dos contribuyentes
   respondiendo—, que salga aunque no haya nada pendiente (es la diferencia entre «no hay nada» y «el
   resumen se rompió»), que un mensaje resuelto no aparezca (RF-40), y que `_is_the_hour` deje pasar
   una sola de las veinticuatro corridas del día (RF-41).
3. **`phones_for`.** Que un desactivado no reciba (RF-45), que el aviso caiga al dueño cuando el rol
   está vacante, y que el ruteo cambiado por el dueño se obedezca (RF-37).
4. **RF-39, el aviso que no se repite.** El criterio dice «el mismo reclamo procesado tres veces
   genera un solo aviso inmediato». Hoy eso se sostiene en el índice único de `external_id`; un test
   que normalice tres lecturas del mismo fixture y cuente las publicaciones de
   `SupplierMessageReceived` es el que fija la promesa.
5. **`RECEIVED_STATUS` contra el fixture real.** Es la dependencia más frágil de la feature (D-4): si
   el texto no coincide, once órdenes ya recibidas empiezan a estancarse. Un test que tome el fixture
   capturado y verifique que ninguna orden recibida queda señalada, cualquiera sea el límite.
6. **Los permisos por comportamiento.** No hay ningún test que haga una request real como ventas
   contra `/purchase-orders` o `/messages` y espere 403. RF-09 y RF-46 están probados por
   construcción.
7. **RF-38, ahora que se construye.** Que un envío que falla **y agota los reintentos** deje la marca
   en el mensaje, y que uno que falla en el primer intento y entrega en el segundo **no la deje**. El
   segundo es el que se rompe sin ruido: deja la pantalla diciendo que falló algo que sí llegó.

Nada de la parte de avisos necesita el portal. Lo que sí necesita HTML fijado son los dos parsers
—y los dos son ahora capturas reales. Si alguna vez volvés a trabajar contra un fixture derivado,
acordate de lo que pasó acá: **los dos tests de la bandeja pasaron durante toda la construcción** y
probaban una suposición, no el portal.

**Para el Code-Reviewer** — Cinco lugares, en este orden:

1. **`GEN-02` sobre `messaging` y `notifications`.** Son los dos módulos donde el import cruzado
   aparecería solo: `messaging` para leer el padrón de `purchases`, `notifications` para leer los
   usuarios de `identity`. Los dos tienen su proyección; si aparece el import, el diseño se rompió y
   el test de fronteras lo va a decir, pero conviene entender **por qué** está la proyección antes de
   aprobar un cambio ahí.
2. **`shared/events/bus.py:60-72` y su único uso.** `unsubscribe` se agregó para el resumen diario y
   para nada más. Verificar que sigue teniendo un solo llamador y que está en un `finally`.
3. **`notifications/handlers.py`.** `GEN-09`: un handler corre en la transacción de quien publicó. Los
   cuatro que entregan algo hacen `.delay()` y vuelven; ninguno llama a Evolution API adentro. Un
   handler que espere una respuesta HTTP ahí aborta la ingesta que lo disparó.
4. **`purchases/service.py:1766`.** El `supplier, _ =` que descarta el motivo. Es el origen de RF-55
   sin implementación, y es una línea que se lee como correcta.
5. **`messaging/service.py:193-199` (`assign`).** Acepta cualquier `assignee_user_id` sin validar el
   rol, y ninguna pantalla lo llama. Es D-3, y es la clase de ruta que pasa un review por no hacer
   nada mal.
