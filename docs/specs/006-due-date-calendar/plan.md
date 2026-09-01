# Calendario de vencimientos — Plan técnico

<!--
  ARTEFACTO INTERNO. Acá van las decisiones técnicas que spec.md no puede llevar.
  No se exporta al cliente.
-->

**Feature:** 006-due-date-calendar · **Spec aprobada el:** 2026-08-30 · **Fecha:** 2026-08-31
**Roles:** Backend-Architect (modelo, servicio, rutas) · Frontend-Architect (la pantalla)

Insumos: `spec.md` firmada (RF-01 a RF-42, ocho historias), los siete diagramas de `diagrams/`, y el
código ya construido en `backend/app/modules/purchases/` y `frontend/`.

> **Este plan es un acta, no un pronóstico.** La feature se construyó **antes** de que existiera este
> documento, y la spec se firmó el mismo día sobre código ya escrito (ver *Excepción al Artículo V*).
> Lo que sigue describe **lo que hay**, verificado archivo por archivo y con la línea a la vista, para
> que el Developer, el Tester y el Code-Reviewer no tengan que recorrer las 4.500 líneas de
> `purchases` para saber qué parte es de esta feature. Lo que **no** hay no se disuelve en el cuerpo:
> tiene dos secciones propias, *Lo que falta* y *Deriva contra la spec firmada*.

## Constitution Check

| Artículo | Cumple | Cómo |
|---|---|---|
| I — El origen es ajeno y de sólo lectura | Sí | El calendario no toca SIGProv: se arma con las facturas que `004` ya registró |
| II — Nada se descarta | Sí | Cada movimiento de un vencimiento queda en `core.due_date_change` con quién lo hizo y el motivo. Nada se pisa |
| III — Flujo unidireccional, `raw` inmutable | Sí | No hay extracción en esta feature |
| IV — Las fronteras entre módulos son reales | Sí | El calendario vive en `purchases`, con la factura. Ver *Alternativas descartadas* |
| **V — Spec primero, y con firma** | **Fuera de orden** | Firmada el 2026-08-30, después de construir. Ver abajo |
| VI — Lo que no está tipado y testeado no está terminado | Parcial, **sin excepción solicitada** | 8 tests de integración sobre las reglas de mover un vencimiento. La brecha es **la H5**, y el humano decidió el 2026-08-31 **construirla**, no exceptuarla: el artículo se cumple cuando cierren las tareas 31 a 36 de `tasks.md`. Una excepción habría dejado el artículo incumplido para siempre; una decisión de construir lo deja incumplido hasta una fecha |
| VII — Las credenciales de terceros viven sólo en el entorno | Sí | No hay credenciales en juego |
| VIII — Un idioma para cada audiencia | Sí | |
| IX — Las dependencias entran por la puerta | Sí | Cero dependencias nuevas |

### Excepción al Artículo V, y quién la aprobó

El Artículo V dice que ninguna feature pasa a planificación técnica sin firma, y que una excepción
**la aprueba el humano y queda registrada en el plan**. Es lo que pasó, en dos momentos.

**Al construir, el 2026-08-30.** El humano pidió implementar las seis specs pendientes y,
consultado sobre las tres que estaban en borrador, respondió *"Las seis, igual"*. Se construyó sin
acuerdo del cliente, sabiendo que si al firmar pedía cambios el costo sería de rehacer, no de
construir.

**Al firmar, el mismo día.** La spec quedó **Aprobada el 2026-08-30**, después de que una auditoría
la recorriera entera contra el paso 1 de `approve_spec.md` y no encontrara nada que corregir: sin
marcadores pendientes, sin secciones vacías, sin decisiones técnicas filtradas, con sus siete
diagramas hechos, validados y en lenguaje de negocio.

Queda dicho, porque el orden importa y este documento es donde consta: **se firmó sobre código ya
construido**. Eso convierte el gate del Artículo V en un registro, no en un filtro — para esta
feature no hubo un momento en que el acuerdo pudiera haber cambiado lo que se construía. Lo que el
gate sí puede hacer todavía es `/converge`: contrastar el código contra lo que quedó firmado, y si
no describen el mismo producto, la decisión de qué corregir sigue siendo del humano.

Al firmar estaba sobre la mesa que **la H5 completa —RF-31 a RF-36, el canal en vivo— no está
construida**. Las ocho historias son severables entre sí, así que diferirla era una salida posible.
**No es la que se tomó:** el 2026-08-31 el humano decidió construirla, y su diseño técnico está
arriba, en *La H5: el canal en vivo*. La spec firmada no se toca.

**Excepciones solicitadas:** la del Artículo V, ya registrada arriba. Ninguna otra.

## La H5: el canal en vivo, decidido el 2026-08-31

**RF-31 a RF-36 no están construidos**, y hasta esta fecha tampoco estaban *decididos*: el plan
delegaba en el Developer la elección del transporte, que es arquitectura y no le corresponde. La
corrida de `/analyze` lo marcó como bloqueante (`checklists/analyze.md`, B-1) y el humano decidió
**construir la H5**. Lo que sigue es la decisión que faltaba, con lo verificado contra el
despliegue real y no contra el hábito.

### El transporte: SSE, y no WebSocket ni polling

**El canal va en un solo sentido.** Todo lo que la pantalla necesita es enterarse de lo que otro
hizo; lo que ella hace ya viaja por las cuatro rutas de escritura que existen. Un WebSocket
resuelve un problema bidireccional que acá no hay, y trae su propio protocolo, su propio
`ping/pong` y su propia clase de bugs. **SSE** es un `GET` que no termina, sobre HTTP común.

**El navegador no habla con la API directamente.** Verificado: el token de sesión vive en una cookie
que sólo lee el servidor (`frontend/lib/api/server.ts:1`, `next/headers`), y la autorización de la
API es `Bearer` (`identity/dependencies.py:60`, `HTTPBearer`). Un `EventSource` del navegador **no
puede mandar headers**, así que el stream no se consume contra el backend: se consume contra un
**Route Handler de Next** que lee la cookie del lado servidor, abre el stream contra la API con su
`Bearer` y lo reenvía. Eso deja `EventSource` utilizable tal cual —mismo origen— con su reconexión
automática incluida, y **sin poner nunca un token en una query string**, que es donde terminan los
tokens de los tutoriales de SSE y también los logs de acceso.

**El polling se descartó midiendo, no por gusto:** el calendario es una pantalla que dos personas
tienen abierta durante horas para mirar algo que cambia unas pocas veces por día. Preguntar cada
cinco segundos es gastar miles de requests para transportar casi siempre «nada nuevo».

### Cómo llega el cambio de un worker al otro

**El dato que hay que mirar antes de diseñar nada:** el backend corre con
`uvicorn --workers ${UVICORN_WORKERS:-2}` (`docker-compose.yml:163`). Son **dos procesos**. Una
persona con el calendario abierto está conectada a uno solo, y quien mueve un vencimiento puede
estar hablando con el otro. Un canal en memoria —una lista de suscriptores en el proceso— funciona
en la máquina del desarrollador y **falla en producción la mitad de las veces**, que es la peor
forma de fallar.

Hace falta un bus compartido, y hay uno que ya está y no agrega dependencias: **`LISTEN` / `NOTIFY`
de Postgres**. No se usa RabbitMQ —que es el broker de Celery (`config.py:45`)— porque el bus de
tareas y el canal de una pantalla tienen vidas distintas, y no se usa Redis porque **el único Redis
del despliegue es el de la pasarela de WhatsApp** (`docker-compose.yml:291`), que no es nuestro.

| Pieza | Dónde | Qué hace |
|---|---|---|
| El publicador | Un handler de `DueDateChanged` en `purchases` | `NOTIFY calendar_changed, '<json del evento>'` sobre la sesión de la transacción |
| El bus | Postgres | Entrega la notificación **sólo si la transacción commitea** |
| El oyente | Una conexión dedicada por worker de uvicorn, abierta en el `lifespan` de `main.py` | `LISTEN calendar_changed` y reparte a los streams abiertos de **ese** proceso |
| El stream | `GET /calendar/stream` | Un `StreamingResponse` por persona conectada |
| El proxy | Route Handler de Next | Pone el `Bearer` desde la cookie y reenvía |

### Por qué esto no viola `GEN-09`, que era la objeción del plan anterior

`GEN-09` dice que un handler corre en la transacción de quien publicó, y de ahí salía la advertencia
correcta: **empujar a un socket dentro de esa transacción hace que una caída del canal aborte el
movimiento del vencimiento**. Un vencimiento que no se movió porque a otra persona se le cayó el
WiFi es exactamente el tipo de acoplamiento que la convención prohíbe.

`NOTIFY` no tiene ese problema, y no por suerte: **es transaccional**. La notificación se encola en
la misma transacción y Postgres la entrega **al commitear**; si la transacción aborta, nadie recibe
nada. El handler no hace I/O de red, no espera a ningún consumidor y no puede fallar por algo que
pase del lado del que mira. La entrega es *best effort* —quien esté escuchando la recibe, quien no,
no— y **eso es correcto acá**: la pantalla que se reconecta vuelve a leer el calendario entero, que
es RF-36.

### Qué significa cada RF sobre este diseño

| RF | Cómo se cumple |
|---|---|
| RF-31 | El handler publica en los **cuatro** verbos. Hoy `add_due_date` y `edit_due_date` no publican nada: es la deriva D8 y hay que cerrarla o el canal transporta la mitad |
| RF-32 | La pantalla se actualiza con el mensaje recibido, sin `router.refresh()` de por medio |
| RF-33 | `DueDateChanged.actor_name`, que el evento ya lleva y que hoy `remove_due_date` manda vacío (D9) |
| RF-34 | **Ya está cumplido y no depende de este canal**: lo resuelve `core.due_date_change` |
| RF-35 | El evento `error` de `EventSource`, que se dispara al cortarse. La pantalla lo dice; no lo inventa un `setTimeout` |
| RF-36 | Al reconectar, **se relee el calendario entero** en vez de intentar recuperar los mensajes perdidos. Un canal que promete no perder nada es un canal que necesita persistencia, y acá la verdad está en la base a una consulta de distancia |

### Lo que este diseño deliberadamente no hace

- **No garantiza la entrega.** Quien está desconectado se pierde el mensaje y se entera al
  reconectar, releyendo. La alternativa —una cola por sesión— es infraestructura para una promesa
  que la spec no hace.
- **No manda el calendario entero en cada mensaje.** Viaja el hecho, y la pantalla decide.
- **No autentica en el stream por query string.** Es la razón del Route Handler.

## Enfoque

**Un vencimiento es una fila, no una columna de la factura.** Porque se mueve, y moverlo tiene que
conservar de dónde venía. `core.due_date` guarda la fecha vigente y la original; cada movimiento va
a `core.due_date_change`. Una columna de `core.invoice` no habría alcanzado por dos motivos
independientes: no hay dónde poner un vencimiento cargado a mano (RF-12), y no hay dónde conservar
la fecha original (RF-20).

**Una entrada por factura, garantizada por la base y no por el código.** El índice único parcial
`uq_due_date_invoice` —único sobre `invoice_id` `WHERE invoice_id IS NOT NULL`— hace que una factura
tenga exactamente una tarjeta, y deja fuera del índice a los cargados a mano, que no son duplicados
entre sí. Es la misma técnica que la 004 usa para el duplicado de facturas.

**La factura se pone sola en el calendario, y se queda.** `_sync_due_date`
(`backend/app/modules/purchases/service.py:1522-1552`) corre en los dos caminos que le fijan
vencimiento a una factura —al registrarla (`service.py:593`) y cuando aparece el plazo del proveedor
al resolverla (`service.py:1011`)—, y es RF-03. Tiene una decisión que no hay que romper: **si
alguien ya movió la entrada a mano, la próxima lectura del portal no la pisa**
(`service.py:1547-1549`, la guarda `if not entry.was_rescheduled`). La descripción y el monto sí se
refrescan siempre, porque son de la factura y se corrigen ahí.

**La distinción que hay que no romper** es la que separa RF-26/RF-27 de RF-28/RF-30, y se decide en
tres líneas (`service.py:1681-1683`): `was_overdue = invoice.due_on < hoy`, y sólo si es falso se
reescribe `invoice.due_on`.

| | Se reprograma **antes** de vencer | Se reprograma **después** |
|---|---|---|
| El plazo para emitir el recibo | se mueve con la fecha nueva | **no se mueve**: sigue negado |
| El atraso del proveedor | se mide contra la fecha nueva | se mide contra la **original** |
| ¿Sigue señalada como vencida sin recibo? | no | **sí** |

Lo notable del diseño es que las tres columnas de la derecha **no se implementan**: salen solas de no
tocar `invoice.due_on`. `issue_receipt` ya rechaza si `due_on < hoy` (`service.py:1358-1362`, que es
RF-34 de la 005), `_average_delay` ya mide contra `due_on` (`service.py:1088-1105`) y
`is_overdue_without_receipt` ya se calcula con `due_on` (`service.py:802-804`). Si mover una tarjeta
habilitara el recibo de una factura vencida, RF-34 de la 005 dejaría de valer con sólo arrastrar.
Está fijado en `test_rescheduling_one_that_already_fell_due_changes_none_of_that`.

**Nada del estado del calendario se guarda calculado.** Los siete campos que una tarjeta muestra
además de sus columnas —vencida, con recibo, saldada, reprogramada, el proveedor, el historial— se
calculan en cada lectura, reusando `_read_invoices`, que es el mismo render que usa la pantalla de
facturas de la 004. Los dos filtros de la spec (RF-10, RF-40) se aplican **sobre esos campos
calculados**, después de armarlos (`service.py:1591-1594`). Detalle en `data-model.md`.

**RF-25 se implementa como rechazo y reintento, no como estado.** Mover a una fecha pasada devuelve
409; la confirmación de la persona vuelve como `confirm_past=true`. Es lo que "pedir confirmación"
significa sobre HTTP sin inventar un vencimiento a medio mover en el servidor.

**Arrastrar (RF-19) y elegir la fecha (RF-42) son la misma llamada.** El backend no distingue cómo lo
dijo la persona, así que los dos dependen **sólo del frontend** — y el frontend no hace **ninguna de
las dos**: mover es un `window.prompt` donde la fecha se **escribe** como texto
(`CalendarGrid.tsx:49-65`). RF-19 (arrastrar) no tiene implementación, y RF-42 tampoco la tiene en la forma
en que la spec lo prueba —*"eligiendo la fecha nueva **de un selector**"*, `spec.md:121`—. Las dos son
deriva de frontend sobre un backend que ya está (D3 y D11).

## Módulos afectados

| Módulo | Qué cambia | Nuevo |
|---|---|---|
| `purchases` | **Todo el backend de la feature.** Dos modelos (`DueDate`, `DueDateChange`) y un enum (`DueDateOrigin`); siete métodos de repositorio en su propio bloque (`repository.py:543-586`), más `due_between` que se reusa; ocho métodos de servicio en el bloque `# --- The calendar of due dates (006) ---` (`service.py:1520-1744`); seis schemas (`DueDateChangeRead`, `DueDateRead`, `CalendarRead`, `DueDateWrite`, `DueDateEdit`, `DueDateMove`); cinco rutas bajo `calendar_router` | No |
| `notifications` | **Nada.** Verificado: `notifications/handlers.py` no se suscribe a ninguno de los dos eventos de esta feature. El aviso de vencimiento próximo que sí existe (`warn_about_a_due_invoice`, `handlers.py:162-174`) escucha `InvoiceDueSoon`, que es **RF-38 de la 005**, y la 006 lo declara fuera de alcance | No |
| `identity` | **Nada.** `Section.CALENDAR` y el nivel `READ` de ventas ya existían: los fija **RF-34 de la 002-access-control**, archivada. La 006 los consume, no los define | No |
| `operations` | **Nada** — y ver la deriva de RF-16: es justamente el módulo que debería estar registrando la corrección de un vencimiento, por `ManualChangeRecorded`, y no la recibe | No |
| Frontend | Una pantalla (`app/(private)/calendario/page.tsx`), un componente (`components/purchases/CalendarGrid.tsx`), cuatro Server Actions (`app/actions/purchases.ts:228-285`) y la entrada del menú (`components/auth/Navigation.tsx:23`). ⬜ **Por construir**: el Route Handler que proxya el stream poniendo el `Bearer` de la cookie | No |
| `main.py` | ⬜ **Por construir**: el `lifespan` abre y cierra la conexión dedicada que hace `LISTEN calendar_changed`, una por worker de uvicorn. Va acá y no en el módulo porque es composición de la app, como el registro de routers (`GEN-04`) | No |

**Un módulo `calendar` propio no se justificó.** Está argumentado en *Alternativas descartadas*.

## Eventos de dominio

Los dos son del catálogo compartido (`backend/app/shared/events/catalog.py`), en pasado, `frozen`,
con identificadores y valores planos: `GEN-08` cumplido.

| Evento | Lo publica | Lo consume | Qué lleva |
|---|---|---|---|
| `DueDateChanged` (`catalog.py:787-803`) | `purchases.service.move_due_date` (`service.py:1693-1705`) con `action="moved"`, y `remove_due_date` (`service.py:1720-1728`) con `action="removed"`. ⬜ **Falta que lo publiquen `add_due_date` y `edit_due_date`** (D8) | ⬜ **El handler del canal en vivo**, que hace `NOTIFY calendar_changed` en la transacción del publicador (ver *La H5*) | `due_date_id`, `action`, `actor_user_id`, `actor_name`, `on_date`, `previous_date`, `invoice_id`, `reason` |
| `InvoiceDueDateRescheduled` (`catalog.py:806-819`) | `purchases.service.move_due_date` (`service.py:1684-1690`), **sólo si la entrada tiene factura** | **Nadie** | `invoice_id`, `previous_due_on`, `due_on`, `was_overdue`, `actor_user_id` |

**Los dos se publican sin oyentes, y eso es legal** (`ARCHITECTURE.md` → *un módulo informa un hecho,
no exige audiencia*). Pero el motivo por el que no tienen oyente es el que importa:

- **`DueDateChanged` es la mitad backend de la H5**, y desde el 2026-08-31 tiene decidido quién lo
  escucha: el handler que hace `NOTIFY`. Existe para que el canal tenga qué empujar y lleva
  `actor_name` justamente por RF-33. **El servicio no se toca para construir la H5** — salvo por lo
  que ya le falta hoy: `add_due_date` y `edit_due_date` no lo publican (D8), y `remove_due_date` lo
  publica con el nombre vacío (D9). Sin cerrar esas dos, el canal transportaría la mitad de los
  cambios y ninguno diría quién lo hizo.
- **`InvoiceDueDateRescheduled` no lo necesita**, y conviene decirlo para que nadie lo "arregle": el
  efecto sobre el plazo del recibo y sobre el atraso ocurre **dentro** de `purchases`, en la misma
  transacción, escribiendo `invoice.due_on`. El evento está para que otro módulo pueda enterarse el
  día que lo necesite, no porque el efecto dependa de él.

**Eventos que esta feature consume: ninguno.** `purchases/handlers.py` no tiene un handler de
calendario; la entrada de una factura al calendario ocurre dentro de `register_invoices` y
`resolve_invoice`, que ya corren en el módulo.

**Ningún import cruza la frontera por esta feature.** El único de todo el archivo de rutas es
`app.modules.identity.dependencies`, que es la excepción fijada por nombre de archivo en
`backend/tests/architecture/test_module_boundaries.py`.

## Datos

Dos tablas nuevas en `core` y dos columnas de `core.invoice` que la feature lee, una de las cuales
escribe. **El detalle completo —columnas, tipos, índices, qué se calcula y qué se guarda— está en
[`data-model.md`](./data-model.md).** Lo mínimo para orientarse:

- **`core.due_date`** — una entrada del calendario: fecha vigente, fecha original, descripción,
  monto, origen (`INVOICE` | `MANUAL`), y la factura si viene de una. Índice único parcial sobre
  `invoice_id`.
- **`core.due_date_change`** — un movimiento: de dónde, a dónde, quién, cuándo y el motivo si lo
  escribieron. Es RF-23 y es lo que hace que RF-34 no necesite bloqueos.
- **`core.invoice.due_on`** — la reescribe `move_due_date` **sólo si la factura no venció**. Es la
  bisagra de RF-26 a RF-30.
- **`core.invoice.original_due_on`** — el calendario **no la toca**. RF-29 funciona porque `due_on`
  se queda quieto, no por esta columna.

**Migración:** no hay una propia de la 006. El DDL viaja en
`backend/alembic/versions/0011_invoices_and_suppliers.py`, compartida con 004, 005 y 007 porque las
cuatro se construyeron en la misma pasada. `DB-01` se cumple —los modelos están en esa migración—,
pero el costo está anotado en *Riesgos*.

## Contratos

Cinco endpoints bajo `/api/v1/calendar`, todos con su autorización declarada (`PY-09`). **El detalle
—query, cuerpos, errores y códigos— está en [`contracts/calendar.md`](./contracts/calendar.md).**

| Método | Ruta | Sección · nivel | Qué hace |
|---|---|---|---|
| `GET` | `/calendar` | `CALENDAR` · `READ` | Una ventana; sin `since`/`until` es el mes en curso (RF-04) |
| `POST` | `/calendar` | `CALENDAR` · `WRITE` | Agregar a mano (RF-12 a RF-14) |
| `PATCH` | `/calendar/{due_date_id}` | `CALENDAR` · `WRITE` | Corregir uno cargado a mano (RF-15) |
| `PUT` | `/calendar/{due_date_id}/date` | `CALENDAR` · `WRITE` | Mover (RF-19 a RF-30, RF-42) |
| `DELETE` | `/calendar/{due_date_id}` | `CALENDAR` · `WRITE` | Eliminar uno cargado a mano (RF-17, RF-18) |
| `GET` | `/calendar/stream` ⬜ **por construir** | `CALENDAR` · `READ` | El canal en vivo (RF-31 a RF-33, RF-35, RF-36). `text/event-stream`, se consume por el Route Handler de Next que pone el `Bearer`. **`READ`, no `WRITE`**: ventas también mira el calendario en vivo |

**RF-37 y RF-38 no se implementan en este módulo: se declaran.** `READ` para el `GET` y `WRITE` para
los otros cuatro es todo lo que hace falta, porque la matriz de `identity` ya le da a ventas `READ`
sobre `CALENDAR` (RF-34 de la 002). El test `test_a_route_that_writes_demands_the_level_to_write`
verifica que ninguna de las cuatro escrituras se conforme con `READ`, que es exactamente la forma en
que RF-38 se rompería sin que nadie lo note.

**El calendario es la única superficie de `purchases` que ventas alcanza**, y está dicho en el
docstring del archivo de rutas (`routes.py:1-13`) para que la próxima ruta que se agregue ahí no
herede la excepción por descuido.

## Mapa de requisitos

Los 42 requisitos firmados, y dónde vive cada uno. **`✗` significa que no hay implementación**, y
cada uno de esos tiene su entrada en *Deriva contra la spec firmada*.

| RF | Dónde vive |
|---|---|
| RF-01 | `calendar()` arma la ventana; la pinta `CalendarGrid.tsx`. **Parcial**: es una lista de días, no una grilla (D6) |
| RF-02 | `DueDateRead.description`, `.amount`, `.supplier_name`. El proveedor sale de la factura (ver D1) |
| RF-03 | `_sync_due_date` (`service.py:1522-1552`), disparado al registrar y al resolver una factura |
| RF-04 | `_month_of` (`routes.py:567-574`): el mes en curso lo decide el backend, sobre `today_here()` |
| RF-05 | ✗ No hay control de mes anterior/siguiente (D5) |
| RF-06 | `DueDateRead.is_past`, calculado contra `today_here()` |
| RF-07 | El enlace a `/facturas/{invoice_id}` (`CalendarGrid.tsx:116-120`); la pantalla destino existe |
| RF-08 | ✗ No hay recorte por día, así que tampoco el "y N más" (D6) |
| RF-09 | `DueDateRead.receipt_issued`, de `_read_invoices` |
| RF-10 | El filtro `without_receipt` del `GET` (`service.py:1591-1592`) |
| RF-11 | `DueDateRead.is_overdue_without_receipt`, y el borde rojo de `CalendarGrid.tsx:88-90` |
| RF-12 | `POST /calendar` → `add_due_date` |
| RF-13 | `due_date.created_by_user_id` y `created_at`, puestos por el servicio con el usuario de la sesión (`service.py:1608`, `models.py:457-458`). **Parcial**: se guardan y no salen del backend — ninguna pantalla los muestra (D10) |
| RF-14 | `due_date.origin` (`INVOICE` \| `MANUAL`), mostrado en la tarjeta |
| RF-15 | `PATCH /calendar/{id}` → `edit_due_date`. **Parcial**: ninguna pantalla lo llama (D4) |
| RF-16 | ✗ La corrección no registra quién, cuándo ni el valor anterior (D2) |
| RF-17 | `DELETE /calendar/{id}` → `remove_due_date` |
| RF-18 | `_only_manual` (`service.py:1731-1737`), y el botón que no se dibuja (`CalendarGrid.tsx:131`) |
| RF-19 | ✗ No se arrastra: mover es un `window.prompt` (D3) |
| RF-20 | `due_date.original_date`, más `due_date_change.previous_date` de cada movimiento |
| RF-21 | `due_date_change.actor_user_id` y `.changed_at`. **Parcial**: la pantalla no muestra quién (D7) |
| RF-22 | `due_date_change.reason`, nullable: ofrecido y no exigido |
| RF-23 | `repository.changes_of(...)`, en orden, adjunto a la tarjeta sólo si fue reprogramada |
| RF-24 | `DueDate.was_rescheduled` (property), mostrado con la fecha original |
| RF-25 | 409 `La fecha nueva ya pasó` y el reintento con `confirm_past=true` |
| RF-26, RF-27 | `move_due_date` reescribe `invoice.due_on` cuando la factura **no** venció |
| RF-28, RF-29, RF-30 | `move_due_date` **no** toca `invoice.due_on` cuando ya venció, y los tres efectos salen de eso |
| RF-31 a RF-33, RF-35, RF-36 | ⬜ **Diseñado y sin construir.** SSE sobre `GET /calendar/stream`, con `LISTEN`/`NOTIFY` de Postgres para cruzar los dos workers de uvicorn y un Route Handler de Next que pone el `Bearer`: ver *La H5: el canal en vivo*. Antes hay que cerrar D8 y D9, o el canal transporta la mitad |
| RF-34 | `core.due_date_change`: gana el último y quedan los dos. **Cumplido, y sin depender de la H5** |
| RF-37 | `GET /calendar` con `Level.READ` sobre `Section.CALENDAR` |
| RF-38 | Las otras cuatro rutas con `Level.WRITE`, y el test que verifica que no se conformen con `READ` |
| RF-39 | `DueDateRead.payment_state`, de `_read_invoices` (ver D1) |
| RF-40 | El filtro `hide_settled` del `GET` (`service.py:1593-1594`) |
| RF-41 | Sin código propio: la pantalla usa utilidades responsive y **nunca se probó en un teléfono** |
| RF-42 | `PUT /calendar/{id}/date`, que es la misma llamada que RF-19 pediría. **Parcial**: el backend está, y la pantalla no ofrece un selector — la fecha se escribe en un `window.prompt` (D11) |

## Alternativas descartadas

- **Un módulo `calendar` propio.** El contenido central del calendario es el vencimiento de una
  factura, y reprogramarlo cambia el plazo del recibo de esa factura y la medición del atraso de su
  proveedor. Serían dos módulos leyéndose todo el tiempo, que es la señal de que son uno
  (`ARCHITECTURE.md` → *Cómo se lee lo que es de otro*). El costo aceptado: `purchases` es el módulo
  más grande del repositorio.
- **Guardar el vencimiento sólo en `core.invoice`.** No habría dónde poner un vencimiento cargado a
  mano (RF-12), ni cómo conservar la fecha original (RF-20).
- **Bloqueo optimista sobre `due_date` para RF-34.** Una columna de versión y un 409 cuando dos
  personas mueven lo mismo. Se descartó porque la spec pide lo contrario: *"vale el último cambio y
  los dos quedan registrados"*. La tabla de movimientos ya da eso sin pedirle a nadie que reintente.
- **Una columna `receipt_issued` / `payment_state` guardada en `due_date`.** Habría evitado recalcular
  en cada lectura, y habría creado un segundo lugar donde vive la verdad sobre una factura. Se
  calcula, reusando `_read_invoices`.
- **Una biblioteca de calendario en el backend para el "mes en curso".** `_month_of` son ocho líneas
  (`routes.py:567-574`). Cero dependencias nuevas en toda la feature (`IX`).
- **Escribir la reprogramación en el portal.** Prohibido por el Artículo I y declarado fuera de
  alcance en la spec. La fecha reprogramada vive de este lado.

## Riesgos

| Riesgo | Impacto | Cómo se mitiga |
|---|---|---|
| ~~**El canal en vivo (H5) todavía no existe.**~~ | — | **Cerrado el 2026-08-31**: el canal está construido y testeado. Queda su descendiente, que es el riesgo de siempre de un canal: que el mensaje no cruce del otro worker. Está listado para el Tester |
| **`_sync_due_date` no pisa una entrada movida a mano.** Si el portal corrige el vencimiento de una factura que alguien ya reprogramó, el dato nuevo del portal se ignora en silencio | Medio | **Sigue abierto.** Es deliberado (RF-20: una decisión de una persona no la deshace una lectura), y el riesgo es que **nadie se entera** del desacuerdo. El mecanismo existe y `purchases` ya lo usa para el padrón (`CorrectionConflicted`); acá no se aplicó, y ningún RF firmado lo pide |
| ~~**El cruce factura ↔ entrada usa dos ventanas distintas.**~~ | — | **Cerrado el 2026-08-31** (deriva D1): `calendar()` busca las facturas por las entradas que va a mostrar, y lo sostiene `TestAnOverdueOneMovedToAnotherMonth` |
| **Migración compartida entre cuatro features.** Un rollback de la 006 no se puede hacer solo: `0011` se lleva puestas también 004, 005 y 007 | Medio | Se acepta: las cuatro se entregan juntas. Si alguna se difiere, la migración hay que partirla antes del merge |
| ~~**La cobertura descansa en 8 tests de integración de servicio.**~~ | — | **Cerrado el 2026-08-31**: cinco tests de ruta que llaman como ventas, y 21 de pantalla que cubren lo que el backend no puede ver —la grilla, el control de mes, el recorte y la barra plegable— |
| **Todo el calendario cuelga de `today_here()`.** Un test que fije un mes concreto empieza a fallar el día que ese mes queda en el pasado | Bajo | Los tests existentes ya trabajan con una ventana relativa a hoy (`test_due_date_calendar.py:23-31`); la convención hay que sostenerla |
| ~~**La pantalla confunde una caída del backend con una negativa de permiso.**~~ | — | **Cerrado**: la pantalla lee con `readFromApi` y distingue la negativa (`<NoPermission>`) de la caída («No pudimos traer el calendario»). Lo que **sigue abierto** es que la regla la fija un test de arquitectura sólo para las pantallas de la 003 (`test_screen_reads.py`), que no alcanza al calendario: nada impide que la próxima pantalla vuelva a `fetchFromApi` |

## Deriva contra la spec firmada (para `/converge`)

**Esto no es alcance nuevo ni una lista de tareas: es lo que no cierra entre el código y lo que se
firmó.** Se anota, no se arregla acá: qué corregir —el código o el acuerdo— lo decide el humano
(Artículo V).

### Requisitos firmados sin correlato en el código

**Ninguno, desde el 2026-08-31.** Las doce derivas `D0`–`D11` que esta sección enumeraba están
cerradas, y así es como se cerró cada una. Se deja la lista y no se borra: qué faltaba, y por qué,
es lo que le explica al próximo por qué el código tiene la forma que tiene.

| # | RF | Qué faltaba | Cómo se cerró |
|---|---|---|---|
| D0 | RF-31 a RF-36 | La H5 entera: ni canal en vivo, ni aviso de desconexión, ni quién hizo el cambio | SSE sobre `GET /calendar/stream` con `LISTEN`/`NOTIFY`, y `useLiveCalendar.ts` del lado de la pantalla |
| D1 | RF-30, y de refilón RF-02, RF-09, RF-39 | Los campos de la factura se buscaban por ventana de fechas, así que una factura vencida reprogramada a otro mes volvía sin proveedor ni estado | `calendar()` los busca **por las facturas de las entradas** (`service.py:2011`), no por fecha |
| D2 | RF-16 | Corregir no registraba nada: el servicio recibía el actor y lo descartaba | `edit_due_date` publica `ManualChangeRecorded` por campo, con el valor anterior (`service.py:2089`) |
| D3 | RF-19 | No se podía arrastrar: mover eran dos `window.prompt` encadenados | Tarjetas y chips `draggable`, y cada día —celda de la grilla o fila de la lista— es zona de caída |
| D4 | RF-15 | El `PATCH` y su Server Action existían y ninguna pantalla los llamaba | Botón «Corregir» en la tarjeta, con su formulario |
| D5 | RF-05 | No había control de mes: la ventana se cambiaba editando la URL | `windowFor` en `lib/purchases/calendar.ts`, con test |
| D6 | RF-01, RF-08 | La pantalla no era un calendario: una lista de los días con algo, y sin recorte | El recorte primero, y después la **grilla del mes** (`weeksOf`), donde un día vacío existe igual |
| D7 | RF-21 | El historial no decía quién movió | La ruta resuelve los nombres (`_name_whoever_touched_the_calendar`) y la tarjeta los muestra |
| D8 | RF-31 | Agregar y corregir no publicaban nada | Los cuatro verbos publican `DueDateChanged` |
| D9 | RF-33 | `remove_due_date` publicaba con el nombre vacío | La ruta le pasa `current_user.name`, como los otros tres |
| D10 | RF-13 | Quién cargó el vencimiento se guardaba y nunca salía | `DueDateRead` expone `created_by_*` y la tarjeta lo escribe |
| D11 | RF-42 | No había selector de fecha: la fecha se escribía a mano en un `prompt` | `<Input type="date">` con motivo opcional, verificado a mano en un teléfono |

Las dos que encontró `/converge` el 2026-08-31 (`converge.md`) se cerraron el mismo día: **RF-02**,
el proveedor que el backend calculaba y ninguna pantalla mostraba, y **RF-41**, que no fallaba por
el calendario sino por el menú del shell —832px de alto sobre un teléfono de 664px—. La barra se
pliega desde entonces, y **esa decisión la tomó el humano**, no este plan.

### Código sin requisito firmado

Ninguno. Todo lo construido responde a un RF de esta spec; no se encontró superficie, tabla ni ruta
de calendario que la spec no pida.

### Requisitos cumplidos que conviene no dar por obvios

- **RF-34 está cumplido sin canal en vivo.** Es de la H5 por redacción, pero no depende de ella: la
  tabla de movimientos lo resuelve.
- **RF-37 y RF-38** salen de la matriz de `identity`, que ya los tenía por RF-34 de la 002. La 006 no
  agregó permisos: declaró niveles. Desde el 2026-08-31 hay además un test que llama a las cinco
  rutas como ventas, porque un permiso declarado y un permiso aplicado no son lo mismo.
- **RF-41** no tiene código propio en el calendario, y por eso fue el último en cerrarse: no era
  demostrable sin abrirlo en un teléfono, y hasta que alguien lo abrió, nadie sabía que lo que
  estorbaba era el menú. El acta está en `evidence/README.md`.

## Contexto de traspaso

**Estado, al 2026-08-31.** La feature está construida, verificada y convergida (`converge.md`,
segunda corrida). Lo que sigue no es un plan de trabajo: es lo que el próximo tiene que saber antes
de tocar este código.

**Para el Developer** — Lo que **no** hay que tocar, porque es una decisión tomada y testeada:

- **La guarda `if not entry.was_rescheduled` de `_sync_due_date`.** Es lo que impide que la próxima
  lectura del portal deshaga la reprogramación de una persona. Se ve como un olvido de
  sincronización y no lo es.
- **Las tres líneas de `was_overdue` en `move_due_date`.** Ahí vive toda la diferencia entre
  RF-26/RF-27 y RF-28/RF-30, y las tres columnas del «después» funcionan **por no escribir**
  `invoice.due_on`. Cualquier refactor que «simplifique» eso reabre el recibo de una factura vencida
  con sólo mover una tarjeta.
- **`original_due_on` de `core.invoice` no es la fuente de RF-29.** Está, se muestra, y el calendario
  no la usa. No la conectes «para arreglar» nada sin leer `data-model.md` primero.
- **El `NOTIFY` va en la transacción del publicador, y ahí está bien.** Si la transacción aborta,
  nadie recibe nada: es lo que hace que `GEN-09` se cumpla sin acoplar el movimiento de un
  vencimiento a la conexión de otra persona. Cambiarlo por un `POST` a un servicio de sockets mete
  I/O de red dentro de la transacción.
- **RF-25 se pregunta con un diálogo de la aplicación, no con `window.confirm`.**
  `components/ui/confirm-dialog.tsx`, sobre `@radix-ui/react-dialog` —que ya era dependencia y no
  usaba nadie—. No es un `Dialog` genérico a propósito: se pasa la pregunta y las dos respuestas, y
  no hay siete formas de armar mal el mismo diálogo. **Cerrarlo por `Escape` o por el fondo es
  decir que no**, y hay un test que lo fija: es lo que más se rompe de una confirmación. La guía
  visual todavía no tiene una entrada para el diálogo — es deuda de la 012, no de esta feature.
- **RF-25 se reconoce por un código, no por el texto del mensaje.** El backend manda
  `details.code = "DUE_DATE_MOVING_INTO_THE_PAST"` y la pantalla pregunta por eso
  (`MOVING_INTO_THE_PAST`, en `lib/purchases/calendar.ts`). Hasta el review de la 006 se comparaba
  el castellano —`message.includes('ya pasó')`—, y eso hacía de la redacción un contrato que nadie
  declaró: reescribir el mensaje mataba la confirmación en silencio y dejaba un movimiento legítimo
  como error. Los dos extremos están comentados, uno apuntando al otro, y hay un test que usa un
  mensaje **distinto** a propósito.
- **Al reconectar se relee el calendario entero**, no se recuperan mensajes perdidos. La verdad está
  en la base a una consulta de distancia, y una cola por sesión es infraestructura para una promesa
  que la spec no hace.
- **La pantalla dibuja las dos vistas a la vez y el CSS elige.** La grilla del mes desde `md`, los
  días uno debajo del otro en un teléfono. No es duplicación: es la misma tarjeta
  (`DueDateCard`) en dos formas, y unificarlas en una sola vista rompe RF-01 o rompe RF-41 —siete
  columnas no entran en 390px, y una lista no muestra el día en que no vence nada.

Compartís `purchases` con la 004 y la 005. **De esta feature son**: `DueDate`, `DueDateChange`,
`DueDateOrigin`, los métodos de repositorio bajo `# --- The calendar ---`, el bloque
`# --- The calendar of due dates (006) ---` del servicio, los seis schemas `DueDate*` y
`CalendarRead`, el `calendar_router` y las dos tablas de la migración `0011`. Del lado del
frontend: `CalendarGrid.tsx`, `useLiveCalendar.ts`, `lib/purchases/calendar.ts`, la pantalla
`(private)/calendario` y el Route Handler `app/api/calendar/stream`. Todo lo demás que toques ahí es
de otra feature.

**Para el Tester** — La suite de la feature son 13 tests de integración
(`backend/tests/integration/features/test_due_date_calendar.py`) y 21 de pantalla
(`frontend/tests/`). Lo que **de verdad** se puede romper, en orden:

1. **Reprogramar una factura ya vencida.** Si después de moverla se puede emitir el recibo, se
   implementó RF-26 donde iba RF-28. Está testeado
   (`test_rescheduling_one_that_already_fell_due_changes_none_of_that`), y es el test que nunca hay
   que debilitar: es también la defensa de RF-34 de la 005.
2. **Mover una vencida a otro mes** y pedir el calendario del mes nuevo. Era la deriva D1, está
   cerrada y la fija `TestAnOverdueOneMovedToAnotherMonth`. Si alguien «optimiza» `calendar()`
   volviendo a buscar las facturas por ventana de fechas, ese test es el que avisa.
3. **El canal en vivo desde el otro worker.** Lo que de verdad se rompe no es que el mensaje llegue:
   es que llegue desde el otro proceso —el despliegue corre con `--workers 2`—. Y el caso que hay
   que sostener antes que ninguno: **una transacción que aborta no notifica a nadie**. Desde el
   review de la 006 los dos tienen test propio, contra la base de verdad y con una conexión que
   escucha aparte: `tests/integration/features/test_the_live_channel.py`, doce tests que dejan
   `app/shared/live.py` al 100%. Antes de eso el transporte entero —`LiveBus`, la ruta del stream—
   no tenía ninguno y el archivo quedaba al 50%; `announce` sólo estaba probado por el evento de
   dominio, que demuestra que **se anuncia**, no que viaje.
4. **El reloj.** Todo cuelga de `today_here()`, que es Buenos Aires. Los tests usan una ventana
   relativa a hoy a propósito: un mes fijo empieza a fallar solo el día que queda en el pasado.
5. **Lo que ningún test puede sostener: el teléfono.** RF-41 no tiene código propio en el calendario
   y se cumple por la barra plegable del shell. Los tests fijan su conducta; que se **vea** se
   verifica a mano, y el acta está en `evidence/README.md`. Si alguien vuelve a tocar
   `Navigation.tsx`, hay que volver a abrirlo en un teléfono.

Nada de esto necesita HTML fijado ni el portal: la feature **no extrae nada**. Si un test de
calendario pide el portal, está mal escrito.

**Para el Code-Reviewer** — Cuatro lugares, en este orden:

1. **`calendar()` en el servicio.** Es el único lugar donde el render de una factura y el de una
   entrada del calendario se cruzan, y donde vivió la deriva D1 durante toda la construcción.
2. **`edit_due_date`.** Publica `ManualChangeRecorded` por campo con el valor anterior, que es
   RF-16 entero. El módulo hace lo mismo en `correct_supplier`: comparalos.
3. **Las fronteras y el catálogo.** `GEN-02`: el único import que cruza en toda la feature es
   `app.modules.identity.dependencies` en `routes.py`, que es la excepción. `GEN-08`: los dos
   eventos están en `shared/events/catalog.py`, en pasado, `frozen`, y llevan ids y no modelos —
   verificalo, porque `DueDateChanged` lleva `actor_name`, que es un valor plano y no una entidad, y
   es fácil «mejorarlo» pasando el `User`.
4. **`PY-09` en las cinco rutas.** No alcanza con que declaren sección: las cuatro escrituras tienen
   que pedir `Level.WRITE`. Lo verifica un test de arquitectura, y desde el 2026-08-31 también uno
   de comportamiento que llama a las cinco como ventas.

Y dos de forma, aunque una no lo es. **`TS-09`**: los textos de `CalendarGrid.tsx` van en español y
están. **`TS-08`**: la pantalla resuelve **vacío**, el **error de una escritura**, el **error de la
lectura** —`readFromApi` distingue una negativa de una caída, así que un backend caído ya no se le
muestra al dueño como falta de permiso— y, desde el review de la 006, **«cargando»**: `move()`
pasa por el guard de `busy` como el resto —antes era el único que no, así que el botón seguía
habilitado y la tarjeta arrastrable durante todo el viaje, y soltarla dos veces mandaba dos
`PUT`— y mientras la escritura viaja la pantalla lo dice en lugar de sólo congelarse.
