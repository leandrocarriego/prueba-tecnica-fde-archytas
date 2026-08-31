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
| **El canal en vivo (H5) todavía no existe.** Hasta que esté, dos personas pueden mirar el mismo calendario y decidir sobre fotos distintas | Alto — es un tercio de la promesa firmada | Ya no es un riesgo sin plan: el diseño está cerrado (*La H5: el canal en vivo*) y desglosado en las tareas 31 a 36. **El humano decidió el 2026-08-31 no poner un cartel provisorio** que avisara que la pantalla no se actualiza sola: sería superficie que el cliente no firmó, y la ventana en que serviría es la que tarde en construirse el canal. El riesgo se acepta durante esa ventana |
| **`_sync_due_date` no pisa una entrada movida a mano.** Si el portal corrige el vencimiento de una factura que alguien ya reprogramó, el dato nuevo del portal se ignora en silencio | Medio | Es deliberado (RF-20: una decisión de una persona no la deshace una lectura). El riesgo es que **nadie se entera** del desacuerdo. El mecanismo existe y `purchases` ya lo usa para el padrón (`CorrectionConflicted`, `service.py:305`); acá no se aplicó |
| **El cruce factura ↔ entrada usa dos ventanas distintas.** Una factura vencida reprogramada a otro mes pierde su proveedor, su estado de pago y su marca de vencida-sin-recibo | Medio | Sin mitigar. Es la deriva D1, abajo |
| **Migración compartida entre cuatro features.** Un rollback de la 006 no se puede hacer solo: `0011` se lleva puestas también 004, 005 y 007 | Medio | Se acepta: las cuatro se entregan juntas. Si alguna se difiere, la migración hay que partirla antes del merge |
| **La cobertura de la feature descansa en 8 tests de integración de servicio.** No hay ni un test de ruta, ni uno de permisos de calendario más allá de la matriz | Medio | `TEST-05` (80%) lo mide sobre `app/` entera, así que esta feature puede quedar floja sin que el umbral se entere. Está listado para el Tester |
| **Todo el calendario cuelga de `today_here()`.** Un test que fije un mes concreto empieza a fallar el día que ese mes queda en el pasado | Bajo | Los tests existentes ya trabajan con una ventana relativa a hoy (`test_due_date_calendar.py:23-31`); la convención hay que sostenerla |
| **La pantalla confunde una caída del backend con una negativa de permiso.** Lee con `fetchFromApi` (`calendario/page.tsx:40`) y devuelve `<NoPermission>` ante cualquier `null` (`:44-46`), y `fetchFromApi` colapsa 401/403, 404, 500 y timeout en el mismo `null` | Medio — con la API caída, al **dueño** le dice «No tenés permiso · Tu acceso no llega al calendario de vencimientos … pedíselo al dueño»: un consejo sobre el que nadie puede actuar, sobre un permiso que nunca faltó | Sin mitigar. El arreglo es leer `readFromApi`, que dice cuál de los tres fue; el docstring de `fetchFromApi` lo pide con todas las letras —*"una pantalla que renderiza una negativa … tiene que leer `readFromApi`, porque `null` acá es también lo que parece un timeout"*, `frontend/lib/api/server.ts:85-87`—. La regla está fijada por un test de arquitectura, pero **sólo para las pantallas de la 003** (`backend/tests/architecture/test_screen_reads.py`, `SCREENS` en `:65`), que no alcanza al calendario. **Este plan no autoriza el cambio**: es hallazgo, igual que la deriva |

## Deriva contra la spec firmada (para `/converge`)

**Esto no es alcance nuevo ni una lista de tareas: es lo que no cierra entre el código y lo que se
firmó.** Se anota, no se arregla acá: qué corregir —el código o el acuerdo— lo decide el humano
(Artículo V).

### Requisitos firmados sin correlato en el código

| # | RF | Qué falta | Dónde |
|---|---|---|---|
| D0 | **RF-31 a RF-36** | La H5 entera: no hay canal en vivo, ni aviso de desconexión, ni indicación de quién hizo el cambio recibido. **Desde el 2026-08-31 tiene diseño y tareas** (31 a 36); sigue siendo deriva hasta que esté construida | No existe. Anotado en `frontend/app/(private)/calendario/page.tsx:26-29` |
| D1 | RF-30, y de refilón RF-02, RF-09, RF-39 | Los campos que vienen de la factura se buscan en un diccionario armado con `due_between(since, until)` —facturas cuyo `due_on` cae en la ventana—, no con las facturas de las entradas que se van a mostrar. Una factura **vencida** reprogramada a otro mes tiene la entrada en una ventana y el `due_on` en otra, y vuelve sin proveedor, sin `receipt_issued`, sin `is_overdue_without_receipt` y sin `payment_state`. RF-30 pide justo lo contrario: que siga señalada como vencida sin recibo aunque su fecha ahora sea otra. **Matiz que importa al evaluar:** el ejemplo firmado del criterio RF-30 —vence el 10, se reprograma el 12 para el 20— cae entero dentro de un mes, así que el criterio **tal como está escrito pasa**; lo que falla es el requisito cuando la fecha nueva cruza el borde de la ventana | `backend/app/modules/purchases/service.py:1562` y `:1577` |
| D2 | RF-16 | Corregir un vencimiento cargado a mano **no registra nada**: ni quién, ni cuándo, ni el valor anterior. El servicio recibe `actor_user_id` y lo descarta con un `del`. El mecanismo existe y se usa a tres pantallas de distancia (`ManualChangeRecorded` → `operations`, `service.py:1946-1960`) | `backend/app/modules/purchases/service.py:1632` |
| D3 | RF-19 | **No se puede arrastrar.** Mover se hace con dos `window.prompt` encadenados —fecha y motivo—, y H4 es la historia que lo pide por su nombre. Es el mismo camino que rompe RF-42, por otro motivo: ver D11 | `frontend/components/purchases/CalendarGrid.tsx:49-65` |
| D4 | RF-15 | El endpoint `PATCH` y la Server Action `editDueDate` existen, y **ninguna pantalla las llama**: no hay botón de corregir. Corregir un monto mal cargado hoy es borrar y volver a cargar | `frontend/app/actions/purchases.ts:245-256`, sin uso en `app/` ni en `components/` |
| D5 | RF-05 | No hay control para avanzar ni retroceder de mes. La ventana se cambia editando la URL a mano; los tres enlaces de la pantalla son "Este mes", "Sólo sin recibo" y "Esconder las saldadas" | `frontend/app/(private)/calendario/page.tsx:57-67` |
| D6 | RF-01, RF-08 | La pantalla **no es un calendario**: es una lista de días agrupados, y sólo aparecen los días que tienen algo. RF-08 —"indicar cuántos hay y permitir verlos todos" cuando un día no entra en pantalla— no tiene implementación, porque no hay recorte que lo dispare | `frontend/components/purchases/CalendarGrid.tsx:73-149` |
| D7 | RF-21, y la prueba de H4 | El historial de una tarjeta muestra `de → a` y el motivo, pero **no muestra quién movió**. Está guardado (`due_date_change.actor_user_id`) y viaja en el schema; la pantalla no lo resuelve a un nombre. La prueba de H4 dice "se ve que originalmente vencía el 10 **y quién lo movió**" | `frontend/components/purchases/CalendarGrid.tsx:105-114` |
| D8 | RF-31 (parcial) | De los cuatro verbos que RF-31 nombra, `DueDateChanged` sólo se publica en dos: `add_due_date` y `edit_due_date` no publican nada. Cuando se construya la H5, agregar y corregir no llegarían a las otras pantallas aunque el canal existiera | `service.py:1597-1613` y `:1615-1633` |
| D9 | RF-33 | `remove_due_date` publica con `actor_name=""` fijo: el nombre no llega desde la ruta, que sí lo tiene (`current_user.name`). `move_due_date` sí lo pasa | `service.py:1725`, contra `routes.py:544-551` |
| D10 | RF-13 | Quién cargó el vencimiento y cuándo **se guardan y nunca salen**. El servicio los escribe (`service.py:1608`, sobre `models.py:457-458`), pero `DueDateRead` no expone `created_by_user_id` ni `created_at` —no están en su lista de campos—, así que el dato no llega al navegador y ninguna tarjeta lo muestra. El criterio firmado dice *"Ese vencimiento figura con el nombre de Marcela y la fecha en que lo cargó"* (`spec.md:210`): **no se puede verificar en pantalla**. Es el mismo defecto que D7 —guardado, no mostrado— un escalón más abajo: en RF-21 el dato al menos viaja en el schema | `backend/app/modules/purchases/schemas.py:280-298` y `frontend/components/purchases/CalendarGrid.tsx:96-104` |
| D11 | RF-42, y la prueba de H8 | **No hay selector de fecha en el camino de mover.** La única forma es `window.prompt('Fecha nueva (aaaa-mm-dd)', entry.on_date)`: la persona **escribe** la fecha como texto. H8 se prueba *"reprogramando un vencimiento eligiendo la fecha nueva de un selector, sin arrastrarlo"* (`spec.md:121`; el criterio de RF-42 está en `:239`). El propio componente demuestra que el patrón está a mano —el formulario de alta usa `<Input type="date">` (`CalendarGrid.tsx:168-173`)—, así que es la deriva más barata de cerrar de toda la lista. **Ojo con el docstring del componente** (`CalendarGrid.tsx:15-16`), que afirma lo contrario: dice que mover se hace *"eligiendo la fecha nueva, que es RF-42"* | `frontend/components/purchases/CalendarGrid.tsx:49-65`, contra `:168-173` |

### Código sin requisito firmado

Ninguno. Todo lo construido responde a un RF de esta spec; no se encontró superficie, tabla ni ruta
de calendario que la spec no pida.

### Requisitos cumplidos que conviene no dar por obvios

- **RF-34 está cumplido sin canal en vivo.** Es de la H5 por redacción, pero no depende de ella: la
  tabla de movimientos lo resuelve. Si el humano decide diferir la H5, RF-34 **no se va con ella**.
- **RF-37 y RF-38** salen de la matriz de `identity`, que ya los tenía por RF-34 de la 002. La 006 no
  agregó permisos: declaró niveles.
- **RF-41** (consultar desde el teléfono) no tiene código propio: la pantalla usa las utilidades
  responsive de Tailwind (`flex-wrap`, `max-w-4xl`) y nunca se probó en un teléfono. No es una deriva
  demostrable sin abrirlo en uno; es lo primero que el Tester tiene que verificar a mano. **La otra
  mitad de H8 sí es demostrable sin teléfono**, y falla: RF-42 pide mover eligiendo la fecha de un
  selector, y no hay selector (D11).

## Contexto de traspaso

**Para el Developer** — Empezá por **la H5**, que es lo único grande que falta, y arrancá por el
backend que ya está: `DueDateChanged` se publica y nadie lo escucha, así que el trabajo es el
transporte y el suscriptor, no el dominio. **Las dos decisiones que este plan antes te delegaba ya
están tomadas** y su justificación está en *La H5: el canal en vivo* — no las reabras sin leer esa
sección: **SSE** sobre `GET /calendar/stream`, **`LISTEN`/`NOTIFY` de Postgres** para cruzar los dos
workers de uvicorn, y un **Route Handler de Next** que pone el `Bearer` desde la cookie porque
`EventSource` no manda headers.

Tres cosas que se rompen si las hacés distinto:

- **El `NOTIFY` va en la transacción del publicador, y ahí está bien.** Es transaccional: si la
  transacción aborta, nadie recibe nada. Eso es lo que hace que `GEN-09` se cumpla sin acoplar el
  movimiento de un vencimiento a la conexión de otra persona. Si en algún momento te tienta cambiarlo
  por un `POST` a un servicio de sockets, ese `POST` **sí** es I/O de red dentro de la transacción.
- **Empezá por D8 y D9, no por el transporte.** `add_due_date` y `edit_due_date` no publican
  `DueDateChanged`, y `remove_due_date` lo publica con `actor_name` vacío. Con el canal construido y
  eso sin cerrar, agregar y corregir no llegarían a nadie y el resto no diría quién fue: se vería
  como un bug del canal y no lo sería.
- **Al reconectar se relee el calendario entero**, no se recuperan mensajes perdidos. La verdad está
  en la base a una consulta de distancia, y una cola por sesión es infraestructura para una promesa
  que la spec no hace.

Lo que **no** hay que tocar, porque es una decisión tomada y testeada:

- **La guarda `if not entry.was_rescheduled` de `_sync_due_date` (`service.py:1547-1549`).** Es lo que
  impide que la próxima lectura del portal deshaga la reprogramación de una persona. Se ve como un
  olvido de sincronización y no lo es.
- **Las tres líneas de `was_overdue` en `move_due_date` (`service.py:1681-1683`).** Ahí vive toda la
  diferencia entre RF-26/RF-27 y RF-28/RF-30, y las tres columnas del "después" funcionan **por no
  escribir** `invoice.due_on`. Cualquier refactor que "simplifique" eso reabre el recibo de una
  factura vencida con sólo mover una tarjeta.
- **`original_due_on` de `core.invoice` no es la fuente de RF-29.** Está, se muestra, y el calendario
  no la usa. No la conectes "para arreglar" nada sin leer `data-model.md` primero.

Compartís `purchases` con la 004 y la 005. **De esta feature son**: `DueDate`, `DueDateChange`,
`DueDateOrigin`, los siete métodos de repositorio bajo `# --- The calendar ---`
(`repository.py:543-586`), el bloque `# --- The calendar of due dates (006) ---` del servicio
(`service.py:1520-1744`), los seis schemas `DueDate*` y `CalendarRead`, el `calendar_router`
(`routes.py:471-574`) y las dos tablas de la migración `0011`. Todo lo demás que toques ahí es de
otra feature y de otra sesión.

**Para el Tester** — Los ocho tests que hay
(`backend/tests/integration/features/test_due_date_calendar.py`) cubren el corazón de la H4 y poco
más. Lo que **de verdad** se puede romper, en orden:

1. **Reprogramar una factura ya vencida.** Si después de moverla se puede emitir el recibo, se
   implementó RF-26 donde iba RF-28. Está testeado (`test_rescheduling_one_that_already_fell_due_changes_none_of_that`),
   y es el test que nunca hay que debilitar: es también la defensa de RF-34 de la 005.
2. **El caso que ningún test toca: mover una vencida a otro mes** y pedir el calendario del mes
   nuevo. Es la deriva D1. Un test que mueva de fin de mes al siguiente y verifique que la tarjeta
   sigue trayendo `is_overdue_without_receipt=True` falla hoy.
3. **Los filtros con entradas cargadas a mano.** `without_receipt` y `hide_settled` se piensan para
   facturas, y una entrada manual (sin recibo posible y sin estado de pago) **pasa los dos filtros**.
   Ningún test lo fija; decidí con el Lead si eso es lo que la spec quiere antes de escribir el assert.
4. **Los permisos por ruta.** `test_route_authorization.py` verifica que las cuatro escrituras pidan
   `WRITE`, y `test_permissions.py` que ventas tenga `READ`. **No hay ningún test que haga una
   request real como ventas y espere 403** sobre el calendario: RF-38 hoy está probado por
   construcción, no por comportamiento.
5. **Idempotencia de `_sync_due_date`.** Llamarlo dos veces sobre la misma factura no debe crear dos
   entradas —lo garantiza `uq_due_date_invoice`— y no debe pisar una fecha movida a mano. Lo segundo
   no tiene test.
6. **El canal en vivo, cuando exista.** Lo que de verdad se rompe no es que el mensaje llegue: es
   que llegue **desde el otro worker**. Un test que publique y escuche en el mismo proceso pasa
   siempre y no prueba nada — el despliegue corre con `--workers 2`. Y el caso que hay que fijar
   antes que ninguno: **una transacción que aborta no notifica a nadie**.
7. **El reloj.** Todo cuelga de `today_here()`, que es Buenos Aires. Los tests existentes usan una
   ventana relativa a hoy a propósito (`test_due_date_calendar.py:23-31`): no fijes un mes concreto,
   empieza a fallar solo.

Nada de esto necesita HTML fijado ni el portal: la feature **no extrae nada**. Si un test de calendario
pide el portal, está mal escrito.

**Para el Code-Reviewer** — Cuatro lugares, en este orden:

1. **`service.py:1554-1595` (`calendar`).** Ahí está la deriva D1, y ahí está el único lugar donde el
   render de una factura y el de una entrada del calendario se cruzan. Mirá que las dos consultas usen
   la misma ventana.
2. **`service.py:1615-1633` (`edit_due_date`).** El `del actor_user_id` de la línea 1632 es un
   parámetro aceptado y tirado: es la deriva D2 (RF-16 sin registro) y roza `ERR-01` en espíritu. El
   módulo ya publica `ManualChangeRecorded` en `correct_supplier` (`service.py:1946-1960`); comparalos.
3. **Las fronteras y el catálogo.** `GEN-02`: el único import que cruza en toda la feature es
   `app.modules.identity.dependencies` en `routes.py:22`, que es la excepción. `GEN-08`: los dos
   eventos están en `shared/events/catalog.py`, en pasado, `frozen`, y llevan ids y no modelos —
   verificalo, porque `DueDateChanged` lleva `actor_name`, que es un valor plano y no una entidad, y
   es fácil "mejorarlo" pasando el `User`.
4. **`PY-09` en las cinco rutas.** No alcanza con que declaren sección: las cuatro escrituras tienen
   que pedir `Level.WRITE`. Lo verifica un test, pero es la línea donde RF-38 se rompería sin ruido.

Y dos más que parecen de forma, aunque una no lo es. **`TS-09`**: los textos de `CalendarGrid.tsx`
van en español y están. **`TS-08`**: la pantalla resuelve **vacío** (`No vence nada en este período`,
`CalendarGrid.tsx:73-76`) y el **error de una escritura** (el cartel rojo, `:69-71`); **no resuelve
"cargando"** —los `window.prompt` del movimiento son bloqueantes y el `busy` sólo deshabilita
botones—; y, lo que de verdad cuenta, **no resuelve el error de la lectura**: lee con `fetchFromApi`
(`calendario/page.tsx:40`) y devuelve `<NoPermission>` ante cualquier `null` (`:44-46`), así que una
caída del backend se le muestra al dueño como una negativa de permiso. Está en *Riesgos*, con la
línea del docstring de `fetchFromApi` que lo prohíbe (`frontend/lib/api/server.ts:85-87`) y el test
de la 003 que fija la regla para otras pantallas y no para ésta.

**Lo que este plan no autoriza.** Nada de la sección *Deriva* es una tarea aprobada, y tampoco lo es
el arreglo del último riesgo —pasar la pantalla a `readFromApi`—. Son hallazgos para `/converge`, y
quien decide si se corrige el código o se enmienda la spec es el humano.
