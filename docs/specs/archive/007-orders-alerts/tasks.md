# Órdenes de compra y avisos — Tareas

<!--
  ARTEFACTO INTERNO. Cada tarea mapea a una skill de agents/skills/ y es lo bastante
  chica como para terminarse de una sentada. Si una tarea no tiene skill, o no
  corresponde al proyecto, o falta la skill: preguntá antes de inventarla.
-->

**Feature:** 007-orders-alerts · **Plan:** `plan.md` · **Tareas:** 54

## Estado

**Este documento se escribió después de la implementación**, el 2026-08-31. La 007 se construyó en el
commit `b759a37`, junto con las otras cinco specs pendientes, sin que existiera un `tasks.md` que la
desglosara. El desglose de abajo es el que `plan.md` implica; las marcas dicen qué encontré en el
árbol de trabajo al recorrer archivo por archivo.

- ✅ **53 de 54**, al 2026-08-31: las 35 que estaban construidas, más la **H8 entera**, **RF-38**, la
  validación y la pantalla de RF-30, y los tests de la franja, del ruteo, del resumen y de los
  permisos — que no existían.
- ✅ **54 de 54**: la 27 también, el 2026-08-31. Las credenciales estaban en el entorno y el portal
  responde — **la tarea nunca estuvo bloqueada**, y darla por bloqueada sin comprobarlo fue un error
  de este documento.

> **Capturar el fixture destapó dos defectos que los tests no podían ver**, y son el argumento entero
> a favor de `TEST-03` bien entendido:
>
> - **`MESSAGES_PATH` apuntaba a `/mensajes`, que devuelve 404.** La sección es `/mensajes-internos`.
>   La lectura nocturna de la bandeja fallaba **siempre**, desde el primer día.
> - **No existe la columna `Tipo`** que el parser leía. El tipo está en el asunto —«Reclamo de pago -
>   F-1809»—, así que los sesenta y siete mensajes entraban `UNCLASSIFIED` y **RF-33 y RF-34 no
>   podían dispararse nunca**: ni un solo aviso inmediato, sin que nada fallara.
>
> Los dos tests del parser de la bandeja **pasaban** todo ese tiempo, contra un fixture derivado que
> reproducía la deducción. Un test verde contra una suposición prueba la suposición.
- **La suite queda en 1530 tests y 91,11 % de cobertura**, contra 1443 y 89,70 % antes de esta pasada.

> **La migración `0016` se aplicó y se revirtió contra la base real**, no sólo contra los modelos: la
> suite construye su esquema desde `Base.metadata` y una migración rota no se notaría ahí.

> **La suite corrió entera y está en verde.** Lo que sigue faltando son las **pruebas de sistema del
> `Tester`** —abrir las pantallas a mano— y, sobre todo, **probar el canal de WhatsApp de verdad**:
> los tests fijan a quién le tocaría el aviso y cuándo, no que Evolution API lo entregue.

> **Falta `/converge` y falta `/review-feature`.** D-0, D-3 y D-5 quedaron cerrados en esta pasada;
> D-1, D-2 y D-4 siguen abiertos y son material del gate.

> **Dos decisiones del humano, del 2026-08-31.** La **H8 se construye antes del PR** —está firmada y
> no está hecha— y **RF-38 se resuelve con un evento `AlertDeliveryFailed`**. Las dos están registradas
> en `plan.md` → *Lo que falta: la H8, y RF-38*, con lo que se descartó y por qué.

## Orden

Agrupadas por historia, en el orden de prioridad de la spec. Dentro de cada una:
migración → backend → frontend → tests.

> **Al terminar H1 hay algo entregable de verdad**: Marcela abre `/ordenes` y ve las cuarenta con su
> proveedor, su fecha, su monto y su estado, agrupadas, con cuántas hay en cada uno, y puede pedir sólo
> las de un proveedor. Las siete historias siguientes agregan encima.

> **La mitad que avisa no tiene ni un test, y es la mitad que puede despertar a alguien un sábado a
> las once de la noche.** Las tareas 40, 41 y 46 son eso, y no son opcionales: si RF-42 se rompe, el
> síntoma es que el equipo silencia el canal, y un canal silenciado es la feature entera sin efecto.

### H1 — Seguir cada pedido hasta que llega

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 1 | `app/shared/events/catalog.py`: `PurchaseOrdersExtracted`, `NormalizedPurchaseOrder`, `PurchaseOrdersNormalized` y `PurchaseOrderRowsQuarantined`. | `add_backend_feature` | Developer | RF-01 |
| ✅ 2 | `portal.extract_purchase_orders` con su task, y la entrada `SyncJob(key="purchase_orders")` en `operations`. **Automatización de navegador, no el endpoint JSON del portal** (Artículo I). | `add_integration` | Developer | RF-01 |
| ✅ 3 | Migración `0011`: `core.purchase_order` con el enum `order_review_state`, `staging.purchase_order_row`, y los índices por estado y por proveedor. | `add_database_migration` | Developer | RF-02, RF-05, RF-08 |
| ✅ 4 | `parse_purchase_orders`, con sus **dos tests unitarios contra el fixture capturado** `purchase-orders-page-2026-08-29.html` (`TEST-03`). De las dos pantallas de esta feature, ésta es la única probada contra la realidad. | `add_backend_feature` | Developer | RF-02, RF-03 |
| ✅ 5 | `ingestion.normalize_purchase_orders`: tipar la pantalla a `staging` y publicar el lote. | `add_backend_feature` | Developer | RF-01 |
| ✅ 6 | `purchases.register_orders`: `status_since` **del sistema y no del portal**, `observed_from_start` para las que ya estaban, y `review_state = PENDING` cuando el proveedor no se identifica. Una grafía ya asignada entra identificada sin pasar por revisión, porque `resolve_supplier` mira `supplier_alias` antes que nada. | `add_backend_feature` | Developer | RF-04, RF-05, RF-08, RF-49, RF-50, RF-58 |
| ✅ 7 | `list_orders` y el bloque de repositorio: la página, los filtros por estado y proveedor, y `orders_per_status`. Lo que la pantalla muestra —`days_in_status`, `days_since_ordered`, `is_stalled`— **se calcula en cada lectura y no se guarda**. | `add_backend_feature` | Developer | RF-02, RF-03, RF-05, RF-06, RF-07 |
| ✅ 8 | `GET /purchase-orders` con `require_section(PURCHASE_ORDERS, READ)`, y la sección en la matriz de `identity` con `_SALES: NONE`. RF-09 es la matriz, no una comprobación en la ruta. | `add_backend_feature` | Developer | RF-06, RF-09 |
| ✅ 9 | Pantalla `(private)/ordenes` con `OrderTable.tsx`: las órdenes con sus conteos por estado, y la orden apartada mostrada **con el nombre tal como llegó** y la marca «sin identificar» (RF-50). | `add_frontend_feature` | Developer | RF-02, RF-03, RF-07, RF-12, RF-13, RF-16, RF-49, RF-50 |
| ✅ 10 | **Tests de permisos y de frecuencia, por comportamiento.** Hoy RF-09 y RF-46 están probados por construcción: no hay ni una request real como ventas contra `/purchase-orders` ni contra `/messages` que espere `403`. Sumar que los dos jobs se disparan por su parámetro (RF-01, RF-21) y que el filtro por proveedor devuelve sólo las suyas (RF-06). | `add_tests` | Tester | RF-01, RF-06, RF-09, RF-21, RF-46 |

### H2 — Las que quedaron ahí, señaladas

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 11 | `_is_stalled` y el parámetro `purchase_order.stalled_days` (inicial 15) con su proyección en `core.purchase_setting`. **Una orden recibida nunca se estanca**, por larga que sea su espera. | `add_backend_feature` | Developer | RF-10, RF-11 |
| ✅ 12 | El filtro `only_stalled` y el conteo `stalled` de `PurchaseOrderList`. | `add_backend_feature` | Developer | RF-12, RF-13 |
| ✅ 13 | El reinicio de `status_since` cuando el portal muestra la orden en otro estado. **Ahí viven RF-05, RF-14 y RF-48 juntos, y ninguno tiene código propio**: una orden que avanza deja de estar señalada sin que nadie limpie un flag. | `add_backend_feature` | Developer | RF-14, RF-48 |
| ✅ 14 | Tests de H1 y H2: `TestWatchingAnOrder` (4 casos) — el tiempo contado desde la primera observación, el reloj que se reinicia al avanzar, la recibida que nunca se estanca, y los conteos por estado. | `add_tests` | Tester | RF-02, RF-03, RF-04, RF-05, RF-07, RF-10, RF-11, RF-12, RF-13, RF-14, RF-48, RF-49 |

### H3 — Avisar si ya pedimos lo mismo

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 15 | `earlier_order_for` y `repeat_of_order_id`, más el parámetro `purchase_order.repeat_window_days` (inicial 15). **Sin proveedor identificado devuelve `None`**, que es RF-59: sin proveedor no hay con qué comparar, y señalarla igual sería adivinar. El señalamiento **nunca bloquea** el registro de la orden (RF-20). | `add_backend_feature` | Developer | RF-15, RF-17, RF-20, RF-59 |
| ✅ 16 | `dismiss_repeat` y `DELETE /purchase-orders/{id}/repeat-flag`, con quién lo descartó y cuándo tomados del token. Es un `DELETE` sobre un sub-recurso porque lo que desaparece es el señalamiento, no la orden. | `add_backend_feature` | Developer | RF-18, RF-19 |
| ✅ 17 | `repeat_of_number` resuelto al leer, y la orden anterior mostrada junto a la señalada. | `add_backend_feature` | Developer | RF-16 |
| ✅ 18 | Tests de H3: `TestARepeatedOrder` (2 casos) — que se señale sin bloquear el registro, y que el descarte quede con su autor. | `add_tests` | Tester | RF-15, RF-16, RF-17, RF-18, RF-19, RF-20 |

### H4 — Los mensajes salen de la bandeja del portal

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 19 | Los eventos de la bandeja: `SupplierMessagesExtracted`, `NormalizedMessage`, `SupplierMessagesNormalized` con su flag `first_run`, y `SupplierMessageReceived`. | `add_backend_feature` | Developer | RF-21, RF-33, RF-34, RF-47 |
| ✅ 20 | `portal.extract_messages` con su task y `SyncJob(key="messages")` sobre `message_sync.interval_minutes` (inicial **30**, la mitad de la hora que RF-21 tolera). | `add_integration` | Developer | RF-21 |
| ✅ 21 | Migraciones: `staging.message_row` en la `0011`; `core.supplier_message` y `core.messaging_supplier` en la `0012`, con los enums `message_kind` y `message_state`. El **único** sobre `external_id` es lo que hace idempotente leer la bandeja cada media hora. | `add_database_migration` | Developer | RF-21, RF-22, RF-27, RF-39 |
| ✅ 22 | `parse_messages`, con sus dos tests unitarios. **Contra un fixture derivado, no capturado**: ver la tarea 27. | `add_backend_feature` | Developer | RF-21, RF-22 |
| ✅ 23 | Módulo `messaging`: el mapa `KINDS` sobre el texto normalizado, `_sender_of` contra **su propia proyección del padrón** —alimentada por `SuppliersNormalized`, nunca importando `purchases`—, y `register_messages`. Un tipo que nadie mapeó queda `UNCLASSIFIED` y **se muestra**; un remitente que no resuelve con certeza queda nulo y **se dice**. | `add_backend_feature` | Developer | RF-22, RF-23, RF-24, RF-25, RF-27, RF-33, RF-34 |
| ✅ 24 | `GET /messages` con sus tres filtros y el conteo de pendientes, y la sección `SUPPLIER_MESSAGES` en la matriz con `_SALES: NONE` — que también deja a ventas fuera de los mensajes de stock bajo. | `add_backend_feature` | Developer | RF-26, RF-31, RF-46 |
| ✅ 25 | Pantalla `(private)/mensajes` con `MessageList.tsx`: los cuatro tipos, el remitente sin identificar dicho como tal, la palabra cruda del portal cuando el tipo es desconocido, y el cartel del aviso que no se pudo entregar. | `add_frontend_feature` | Developer | RF-24, RF-25, RF-26, RF-31 |
| ✅ 26 | Tests de H4: `TestTheInbox` (4 de sus 6 casos) — la clasificación por lo que escribe el portal, el tipo desconocido mostrado sin clasificar, el remitente fuera del padrón dicho como tal, y que el mismo mensaje no se registre dos veces. | `add_tests` | Tester | RF-22, RF-23, RF-24, RF-25, RF-27, RF-39 |
| ✅ 27 | **Fixture de `/mensajes` recapturado del portal real** el 2026-08-31, con el lector del módulo `portal` (`messages-page-2026-08-31.html`, 67 mensajes, 33 sin leer). La deducción falló en dos cosas, y **ninguna se notaba corriendo los tests**: la sección está en **`/mensajes-internos`** y no en `/mensajes` —la lectura nocturna fallaba siempre—, y **no hay columna `Tipo`**: el tipo va en el asunto. El fixture derivado se retiró y `derive_portal_fixtures.py` dejó de generarlo. | `inspect_portal` | Developer | RF-22, RF-23, RF-24, RF-25 |

### H5 — Saber cuáles quedaron sin resolver y de quién son

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 28 | `resolve`, `assign` y `annotate` con sus tres rutas bajo `SUPPLIER_MESSAGES · WRITE`. Quién resolvió sale del token, nunca del cuerpo. El `409` de resolver dos veces es deliberado: significa que dos personas creyeron tener el mismo pendiente, y eso es información. | `add_backend_feature` | Developer | RF-27, RF-28, RF-29, RF-30, RF-32 |
| ✅ 29 | `MessageList.pending`, el conteo que no respeta los filtros porque es el estado de la bandeja entera. | `add_backend_feature` | Developer | RF-31 |
| ✅ 30 | **RF-30, las dos mitades que faltan.** La Server Action `assignMessage` existe y **ninguna pantalla la llama**: no hay control para asignar responsable. Y el backend **acepta cualquier `user_id`** sin validar el rol, cuando el criterio firmado dice que Julián no figura entre los asignables. Es la deriva **D-3**. | `add_frontend_feature` | Developer | RF-30 |
| ✅ 31 | Tests de H5: los dos casos de `TestTheInbox` que cubren resolver con su autor y fecha, y asignar y anotar. | `add_tests` | Tester | RF-28, RF-29, RF-31, RF-32 |
| ✅ 32 | Test de RF-30 completo: que un mensaje se pueda asignar desde la pantalla, y que **asignárselo a ventas se rechace**. | `add_tests` | Tester | RF-30 |

### H6 — Que el aviso salga del sistema

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 33 | Migración `0013`: `operations.notification_recipient`, `notification_route` y `notification_setting`. **`notification_route` nace vacía y no se siembra**: los valores firmados viven en `DEFAULT_ROUTES`, como todo valor inicial de la plataforma. | `add_database_migration` | Developer | RF-37, RF-44, RF-45 |
| ✅ 34 | La proyección de destinatarios, alimentada por `UserRegistered`, `UserDeactivated`, `UserReactivated` y `UserRoleChanged`. **RF-45 no es una regla que alguien recuerde**: es lo que pasa cuando llega `UserDeactivated`. `UserRegistered` suma el teléfono y **no lleva ninguna credencial**, a diferencia de `UserInvited` (Artículo VII). | `add_backend_feature` | Developer | RF-44, RF-45 |
| ✅ 35 | `AlertRouter.phones_for`: el tipo de aviso → un rol → los teléfonos activos. Si nadie tiene ese rol, **el aviso cae al dueño** en vez de desaparecer. | `add_backend_feature` | Developer | RF-37, RF-44 |
| ✅ 36 | `delay_until_window` y los parámetros `alerts.window_start` / `alerts.window_end` (iniciales 08:00 y 18:00, lunes a viernes). **Devuelve segundos, nunca un «no»**: fuera de la franja el aviso se demora, no se descarta. | `add_backend_feature` | Developer | RF-42, RF-43 |
| ✅ 37 | La task `send_alert` y el `_deliver` que la encola con `countdown`. **El `countdown` se lo come el broker**: un aviso que sale a las ocho de la mañana no depende de que haya un worker vivo a medianoche. `send_alert` y `send_access_link` son dos tasks con el mismo cuerpo a propósito — una lleva credenciales y la otra no. | `add_celery_task` | Developer | RF-33, RF-34, RF-42, RF-44 |
| ✅ 38 | `GET` y `PUT /alerts/routes` bajo `SYSTEM_PARAMETERS`, sólo del dueño. El `GET` devuelve **los tres tipos siempre**, con el valor que la plataforma está obedeciendo, y cuántas personas lo alcanzan. | `add_backend_feature` | Developer | RF-37 |
| ✅ 39 | **RF-38: el evento `AlertDeliveryFailed`.** `send_alert` pasa a recibir el `message_id` —nulable, porque también entrega los avisos de la 005, que no tienen mensaje detrás— y **al agotar los reintentos** publica `AlertDeliveryFailed(message_id, kind, reason)`, abriendo sesión con `SessionFactory` como ya hace `daily_digest`. `messaging` se suscribe y llama a `record_alert_failure`, que **ya está escrito**. **No se toca el frontend**: la columna existe y el cartel ya se dibuja. Decidido el 2026-08-31. | `add_backend_feature` | Developer | RF-38 |
| ✅ 40 | **Tests de la franja horaria — hoy no existe ninguno.** El caso firmado (sábado 22:00 → lunes 08:00) y sus vecinos: viernes 19:00, martes 06:00 —que espera dos horas, no veintiséis— y el límite exacto de las 18:00. Es la regla que impide despertar a alguien de madrugada, y está probada por lectura. | `add_tests` | Tester | RF-42, RF-43 |
| ✅ 41 | **Tests de ruteo y entrega — hoy no existe ninguno.** Que un reclamo llegue al teléfono de compras y no al de otro (RF-33, RF-34, RF-44); que un desactivado no reciba (RF-45); que el aviso caiga al dueño cuando el rol está vacante; que el ruteo cambiado por el dueño se obedezca (RF-37); y que un envío que **agota los reintentos** deje la marca en el mensaje, y uno que falla al primer intento y entrega al segundo **no la deje** (RF-38). | `add_tests` | Tester | RF-33, RF-34, RF-37, RF-38, RF-44, RF-45 |

### H7 — Que no me avisen dos veces lo mismo

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 42 | El único de `external_id` más `alerted_at`. **RF-39 se cumple por dos mecanismos que se ven distintos y no lo son**: un mensaje ya visto no se vuelve a registrar, y queda constancia de cuándo se avisó. Si alguien «arregla» el primero permitiendo re-registrar, el aviso se duplica. | `add_backend_feature` | Developer | RF-39 |
| ✅ 43 | `first_run`, decidido en `ingestion` preguntándole a `staging` si alguna vez tipó un mensaje, y obedecido en `register_messages`. Sin esto, la puesta en marcha manda **sesenta y cuatro avisos** a tres teléfonos. | `add_backend_feature` | Developer | RF-47 |
| ✅ 44 | El resumen diario: `DailyDigestRequested` publicado por la task, `DailyDigestContribution` contestado por `purchases` y por `messaging`, y `EventBus.unsubscribe` **en un `finally`** para el acumulador temporal. Beat despierta cada hora y la task decide si es la hora, que es lo que hace que cambiar el horario valga desde el día siguiente y no desde un redeploy. | `add_celery_task` | Developer | RF-35, RF-36, RF-40, RF-41 |
| ✅ 45 | Tests de H7: `TestWhoIsWokenUp` (2 casos) — que la primera lectura no despierte a nadie, y que un reclamo posterior sí. | `add_tests` | Tester | RF-39, RF-47 |
| ✅ 46 | **Tests del resumen diario — hoy no existe ninguno.** Que se arme preguntando, con los dos contribuyentes respondiendo; que salga **aunque no haya nada pendiente** —es la diferencia entre «no hay nada» y «el resumen se rompió»—; que un mensaje resuelto no aparezca (RF-40); y que `_is_the_hour` deje pasar **una sola** de las veinticuatro corridas del día (RF-41). | `add_tests` | Tester | RF-35, RF-36, RF-40, RF-41 |

### H8 — La orden que quedó sin proveedor se resuelve una sola vez y vuelve a la lista

> **Está firmada y no está construida.** Once de sus trece requisitos no tienen una línea. El humano
> decidió el 2026-08-31 que se construye **antes del PR**, y el molde está a doscientas líneas de
> distancia: `# --- Deciding about an invoice held for review ---` (`purchases/service.py:842-1010`)
> tiene resuelto todo lo que esta historia pide, con **una sola** diferencia sin análogo, que es RF-60.

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 47 | Migración: `review_reason`, `resolved_by_user_id` y `resolved_at` en `core.purchase_order`, más un índice sobre `review_state` que es por donde RF-52 filtra. **Sin backfill posible**: una orden ya apartada no sabe por qué lo fue, porque el motivo nunca se guardó, y reconstruirlo exige volver a leer el portal. | `add_database_migration` | Developer | RF-55, RF-56 |
| ✅ 48 | `register_orders` **deja de tirar el motivo**. Hoy hace `supplier, _ = await self.resolve_supplier(...)` y descarta la razón, que es justamente «no está en el padrón» o «no se pudo desambiguar». Esa razón va a `review_reason`, y eso es RF-55. | `add_backend_feature` | Developer | RF-55 |
| ✅ 49 | **`resolve_order(order_id, supplier_id, actor_user_id)`**: asignar el proveedor, marcar `RESOLVED`, guardar quién y cuándo, aprender la grafía como `SupplierAlias(source=LEARNED)`, y **después volver a evaluar el pedido repetido** contra el proveedor recién asignado — que es RF-60 y es lo único de esta historia que no tiene análogo en facturas. | `add_backend_feature` | Developer | RF-54, RF-56, RF-57, RF-60, RF-61 |
| ✅ 50 | **Generalizar `_apply_alias` a las dos entidades.** Hoy recorre sólo `pending_invoices()`. La spec firma que el criterio es **uno solo** para facturas y órdenes: resolver una orden identifica también las facturas que esperaban esa grafía, y al revés. **Es la única decisión de diseño abierta de la H8** y toca código de la 004 ya entregado y testeado: los tests de resolución de facturas son la red. | `add_backend_feature` | Developer | RF-61, RF-62 |
| ✅ 51 | `held` en `PurchaseOrderList` y el filtro `review_state` en `list_orders`, más `review_state` y `review_reason` en `PurchaseOrderRead`. | `add_backend_feature` | Developer | RF-51, RF-52 |
| ✅ 52 | `POST /purchase-orders/{order_id}/resolution` con `require_section(PURCHASE_ORDERS, WRITE)` y cuerpo `{supplier_id, remember}`. **No lleva responsable** —una orden apartada no se reparte de a una— y **no da de alta un proveedor**: uno fuera del padrón deja la orden apartada con ese motivo. El contrato está diseñado en `contracts/orders-and-messages.md`. | `add_backend_feature` | Developer | RF-53, RF-54 |
| ✅ 53 | Pantalla: el conteo de apartadas, el filtro para verlas solas, y el selector de proveedor en la fila. **Desde la misma lista de órdenes, no en una pantalla de revisión aparte** — la spec lo decide así y da el motivo: una cola que cuesta tiempo se abandona. | `add_frontend_feature` | Developer | RF-51, RF-52 |
| ✅ 54 | Tests de H8: que una orden sin proveedor entre igual y quede apartada con su motivo (RF-08, RF-50, RF-55); que **ventas no pueda resolverla y el dueño y compras sí** (RF-53); que resolverla la saque de las apartadas con su autor (RF-56, RF-57); que **tres órdenes escritas igual queden resueltas con una sola decisión** (RF-62) y que la siguiente entre ya identificada (RF-58); que una apartada **no** se señale como repetida (RF-59) y que **sí** se evalúe al resolverla (RF-60). | `add_tests` | Tester | RF-08, RF-50, RF-51, RF-52, RF-53, RF-54, RF-55, RF-56, RF-57, RF-58, RF-59, RF-60, RF-61, RF-62 |

## Cobertura de requisitos

| Requisito | Tareas | Test |
|-----------|--------|------|
| RF-01 | 1, 2, 5 | **10** |
| RF-02 | 3, 4, 6, 7, 9 | 14 |
| RF-03 | 4, 6, 7, 9 | 14 |
| RF-04 | 6 | 14 |
| RF-05 | 3, 6, 7 | 14 |
| RF-06 | 7, 8 | **10** |
| RF-07 | 7, 9 | 14 |
| RF-08 | 3, 6 | **54** |
| RF-09 | 8 | **10** |
| RF-10 | 11 | 14 |
| RF-11 | 11 | 14 |
| RF-12 | 9, 12 | 14 |
| RF-13 | 9, 12 | 14 |
| RF-14 | 13 | 14 |
| RF-15 | 15 | 18 |
| RF-16 | 9, 17 | 18 |
| RF-17 | 15 | 18 |
| RF-18 | 16 | 18 |
| RF-19 | 16 | 18 |
| RF-20 | 15 | 18 |
| RF-21 | 19, 20, 21, 22 | **10** |
| RF-22 | 21, 22, 23 | 26, **27** |
| RF-23 | 23 | 26, **27** |
| RF-24 | 23, 25 | 26, **27** |
| RF-25 | 23, 25 | 26, **27** |
| RF-26 | 24, 25 | 26 |
| RF-27 | 21, 23, 28 | 26 |
| RF-28 | 28 | 31 |
| RF-29 | 28 | 31 |
| RF-30 | 28, **30** | **32** |
| RF-31 | 25, 29 | 31 |
| RF-32 | 28 | 31 |
| RF-33 | 19, 23, 37 | **41** |
| RF-34 | 19, 23, 37 | **41** |
| RF-35 | 44 | **46** |
| RF-36 | 44 | **46** |
| RF-37 | 33, 35, 38 | **41** |
| RF-38 | **39** | **41** |
| RF-39 | 21, 42 | 45 |
| RF-40 | 44 | **46** |
| RF-41 | 44 | **46** |
| RF-42 | 36, 37 | **40** |
| RF-43 | 36 | **40** |
| RF-44 | 33, 34, 37 | **41** |
| RF-45 | 33, 34 | **41** |
| RF-46 | 24 | **10** |
| RF-47 | 19, 43 | 45 |
| RF-48 | 13 | 14 |
| RF-49 | 6, 9 | 14 |
| RF-50 | 6, 9 | **54** |
| RF-51 | **51**, **53** | **54** |
| RF-52 | **51**, **53** | **54** |
| RF-53 | **52** | **54** |
| RF-54 | **49**, **52** | **54** |
| RF-55 | **47**, **48** | **54** |
| RF-56 | **47**, **49** | **54** |
| RF-57 | **49** | **54** |
| RF-58 | 6 | **54** |
| RF-59 | 15 | **54** |
| RF-60 | **49** | **54** |
| RF-61 | **49**, **50** | **54** |
| RF-62 | **50** | **54** |

En negrita, lo pendiente. **Los 62 requisitos tienen tarea y tienen test**, y la tabla se lee mejor
por dónde se acumula la negrita:

- **Once requisitos no tienen hoy ni una línea construida**: RF-51 a RF-57 y RF-60 a RF-62, más
  RF-38. Son la H8 y la decisión sobre el aviso fallido.
- **Trece requisitos están construidos y probados por lectura, no por comportamiento**: los cuatro de
  la franja y el resumen (RF-35, RF-36, RF-40 a RF-43), los cinco del ruteo y la entrega (RF-33,
  RF-34, RF-37, RF-44, RF-45), y RF-01, RF-06, RF-09, RF-21 y RF-46. **La mitad que avisa no tiene un
  solo test**, y es la que puede sonar de madrugada.
- **Tres requisitos de la H8 ya están cumplidos y conviene no rehacerlos**: RF-50 (la pantalla ya
  muestra el nombre tal como llegó), RF-58 (`resolve_supplier` mira las grafías antes que nada) y
  RF-59 (`earlier_order_for` devuelve `None` sin proveedor).

## Lo que cerró el `/converge` (2026-08-31)

El informe está en `converge.md`. El veredicto fue **deriva mayor**, el humano eligió **implementar
lo que falta**, y esto es lo que se construyó después:

| # | Qué faltaba | Qué se hizo |
|---|---|---|
| **55** | **RF-37 sin pantalla.** `GET/PUT /alerts/routes` existía y nadie la llamaba: el dueño sólo podía cambiar los destinatarios con una request a mano | `components/notifications/AlertRoutes.tsx` dentro de `/configuracion`, con `app/actions/alerts.ts` y `lib/notifications/types.ts`. Cada tipo de aviso muestra a cuántas personas alcanza hoy, porque una ruta apuntada a un rol vacante entrega al dueño por descarte y eso hay que verlo antes de que el aviso no llegue. **`RouteWrite` pasó a aceptar sólo `OWNER` y `PURCHASING`**: con un control en pantalla, un string libre dejaba ofrecer ventas para los reclamos de la bandeja a la que ventas no entra (RF-46) |
| **56** | **RF-06 a medias.** El filtro por proveedor vivía sólo en la API | Un `form` con GET en `/ordenes`, con los demás filtros en campos ocultos para que elegir proveedor no borre el estado que ya estaba puesto. La pantalla sigue siendo un Server Component |
| **57** | **RF-26 a medias.** Lo mismo en la bandeja | El mismo `form` en `/mensajes`, y `GET /messages/senders`, que devuelve el padrón **como lo guarda `messaging`**: son exactamente los valores que `supplier_name` puede tomar, así que el filtro no ofrece nombres que no encuentran nada. Lo fija `::test_the_inbox_can_be_asked_for_one_supplier` |
| **58** | **D-1, el Artículo II en las órdenes** | `triage` suscripto a `PurchaseOrderRowsQuarantined`, con el caso `unreadable_order_row` en la cola de `/revision` |

**La suite queda en 1569 tests y 92,20 % de cobertura**, contra 1530 y 91,11 % antes de esta pasada.

**H-5 quedó cerrada el 2026-08-31**: el humano eligió quitar `PurchaseOrdersStalled` del catálogo.
Era un evento muerto —se exportaba y nadie lo publicaba ni lo consumía—; el aviso de estancamiento
fuera del resumen diario no es alcance firmado.

## Notas para `/converge`

**La lista completa de deriva vive en `plan.md` → *Deriva contra la spec firmada*.** Acá van las cinco
cosas que se ven desde este documento:

- **D-0 y D-5 tienen tarea desde el 2026-08-31**, y antes no podían tenerla: la H8 estaba firmada sin
  construir y RF-38 tenía dos salidas incompatibles. Las dos las decidió el humano.
- **D-1 está cerrada el 2026-08-31**, después del `/converge`. `triage` se suscribe a
  `PurchaseOrderRowsQuarantined` (`triage/handlers.py::open_unreadable_order_rows`) y abre un caso
  `unreadable_order_row`, que la cola de `/revision` muestra y se cierra dándolo por revisado —el
  mismo molde que la fila de facturas. Lo fija
  `test_orders_and_messages.py::TestAnOrderRowNobodyCouldInterpret`. **Queda abierto el mismo agujero
  en la 009**: `SaleRowsQuarantined` se publica y nadie escucha, y es material del converge de esa
  feature, no de ésta.
- **D-2 está cerrada el 2026-08-31.** `PurchaseOrdersStalled` se quitó del catálogo y de su export:
  era vocabulario compartido que nadie publicaba ni consumía. El aviso de estancamiento fuera del
  resumen diario no es alcance firmado; si lo fuera, el evento vuelve junto a su publicador.
- **RF-03 no tiene recorrido declarado, y es deliberado.** El estado es el texto que escribe el portal
  y la única constante que nombra uno es `RECEIVED_STATUS`. Si el portal cambia esa grafía, **todas las
  órdenes recibidas pasan a poder estancarse**. Es la dependencia más frágil de la feature y no tiene
  test propio.
- **Seis cosas están fuera de alcance y un converge que las busque está leyendo el pedido original**:
  registrar un pedido nuevo, contestarle al proveedor, los avisos de stock bajo hacia afuera, un canal
  que no sea WhatsApp al teléfono personal, la pantalla donde el dueño ajusta los parámetros —eso es
  la 003— y dar de alta un proveedor desde la revisión de una orden.
