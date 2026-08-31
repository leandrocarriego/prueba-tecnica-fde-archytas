# Calendario de vencimientos — Tareas

<!--
  ARTEFACTO INTERNO. Cada tarea mapea a una skill de agents/skills/ y es lo bastante
  chica como para terminarse de una sentada.
-->

**Feature:** 006-due-date-calendar · **Plan:** `plan.md` · **Tareas:** 45

## Estado

**Escrito el 2026-08-31, después de la implementación.** `plan.md` ya lo dice de sí mismo —*"es un
acta, no un pronóstico"*— y este documento es su desglose: la feature se construyó en el changeset de
la 004 a la 009, la spec se firmó el 2026-08-30 **sobre código ya escrito**, y este `tasks.md` no
existía. Lo que sigue no es un plan de trabajo por hacer y ya: es el desglose que le faltaba al plan,
reconstruido contra el código y contra las doce derivas `D0`–`D11` que el plan dejó registradas.

- ✅ **41 de 45** implementadas y verificadas por la suite. El 2026-08-31 se cerró **la H5 entera**
  —el canal en vivo, que era un tercio de la spec firmada— más todo el frontend pendiente: el
  arrastre, el selector de fecha, el control de mes, el recorte por día, el botón de corregir, y
  quién cargó y quién movió cada vencimiento.
- ⬜ **4 pendientes**, y ninguna es alcance nuevo: **cada una nace de una deriva `Dn` de `plan.md`**
  o de un `RF` sin test. La columna *Deriva* dice cuál.
- ✅ **La H5 está construida** (2026-08-31): SSE sobre `GET /calendar/stream`, `LISTEN`/`NOTIFY` de
  Postgres para cruzar los dos workers de uvicorn, y un Route Handler de Next que pone el `Bearer`
  desde la cookie. Cero dependencias nuevas. `GEN-09` se cumple sin acoplar nada, y hay un test que
  lo sostiene: **un movimiento rechazado no anuncia nada**.
- ❌ **Dos tareas de la H5 desaparecieron y otras dos ocuparon su lugar.** Se fue la que pedía
  cerrar el plan —el plan ya está cerrado— y se fue el cartel provisorio de «esta pantalla no se
  actualiza sola», que era superficie que el cliente no firmó: el humano decidió no construirlo
  (2026-08-31) y el riesgo se acepta durante la ventana en que se construye el canal. En su lugar
  entraron el stream y su Route Handler, que antes viajaban escondidos en una sola tarea.
- 🔴 **La pantalla no es un calendario**: es una lista de los días que tienen algo (D6), sin control
  de mes (D5), y mover una tarjeta son dos `window.prompt` encadenados (D3, D11).

Suite de la feature al cierre: **8 tests de integración** en
`backend/tests/integration/features/test_due_date_calendar.py`, todos de servicio. **Ni un test de
ruta, ni uno de permisos de calendario por comportamiento, ni uno de frontend.**

> **Dónde queda la cadena.** Con la H5 sin construir y once derivas abiertas, la feature **no está
> lista para `/converge`**. Las ocho historias son severables: si el humano decide diferir el canal en
> vivo, se saca la H5 con sus seis requisitos —RF-34 se queda— y el resto de la spec se sostiene sin
> reescritura. Esa decisión es del humano, no de este documento (Artículo V).

> **El módulo es compartido.** De esta feature son `DueDate`, `DueDateChange`, `DueDateOrigin`, el
> bloque de calendario del repositorio y del servicio, los seis schemas `DueDate*`/`CalendarRead`, el
> `calendar_router` y las dos tablas de calendario de la migración `0011`. Todo lo demás de
> `purchases` es de la 004, la 005 o la 007.

## Orden

Agrupadas por historia, en el orden de prioridad de la spec. Dentro de cada una:
migración → backend → frontend → tests.

> **Al terminar H1 hay algo entregable de verdad**: se abre el calendario y están todos los
> vencimientos de las facturas ubicados en su fecha, con su descripción, su monto y su proveedor, sin
> que nadie los cargue, y desde cada uno se llega a la factura que lo originó. Las siete historias
> siguientes agregan sobre eso.

> **Tres decisiones tomadas que ninguna tarea puede deshacer**, y están así en el traspaso del plan:
> la guarda `if not entry.was_rescheduled` de `_sync_due_date` —que impide que la próxima lectura del
> portal deshaga la reprogramación de una persona—; las tres líneas de `was_overdue` en
> `move_due_date` —donde vive toda la diferencia entre RF-26/RF-27 y RF-28/RF-30, que funcionan **por
> no escribir** `invoice.due_on`—; y que `original_due_on` de `core.invoice` **no** es la fuente de
> RF-29.

### H1 — Ver de un vistazo qué vence y cuándo

| # | Tarea | Skill | Rol | Cubre | Deriva |
|---|-------|-------|-----|-------|--------|
| ✅ 1 | Migración, parte 006 de `0011_invoices_and_suppliers`: `core.due_date` —fecha vigente, fecha original, descripción, monto, origen y la factura si viene de una— y `core.due_date_change`, con el **índice único parcial `uq_due_date_invoice`**: una factura tiene exactamente una tarjeta, y los cargados a mano quedan fuera del índice porque no son duplicados entre sí. | `add_database_migration` | Developer | RF-03, RF-12, RF-20 | — |
| ✅ 2 | `purchases`: `_sync_due_date` — la factura **se pone sola** en el calendario, en los dos caminos que le fijan vencimiento: al registrarla y cuando aparece el plazo del proveedor al resolverla. La descripción y el monto se refrescan siempre; **la fecha no se pisa si alguien ya la movió**. | `add_backend_feature` | Developer | RF-03 | — |
| ✅ 3 | `purchases`: `calendar()` arma la ventana y calcula en cada lectura los siete campos que la tarjeta muestra —vencida, con recibo, saldada, reprogramada, el proveedor, el historial—, **reusando `_read_invoices`**, que es el mismo render de la pantalla de facturas. Nada del estado del calendario se guarda calculado. | `add_backend_feature` | Developer | RF-01, RF-02, RF-06 | — |
| ✅ 4 | `GET /calendar` con su autorización declarada y **el mes en curso por defecto**, decidido en el backend sobre `today_here()` (Buenos Aires, no UTC). Ocho líneas, cero dependencias nuevas. | `add_backend_feature` | Developer | RF-04 | — |
| ✅ 5 | Pantalla `(private)/calendario` y `CalendarGrid`: los vencimientos con su descripción, su monto y su proveedor, los pasados distinguidos de los que vienen, y el enlace a la factura que lo originó. | `add_frontend_feature` | Developer | RF-01, RF-02, RF-06, RF-07 | — |
| ✅ 6 | Test: una factura registrada aparece sola en el calendario, en su fecha. | `add_tests` | Tester | RF-02, RF-03 | — |
| ✅ 7 | **Hecho el 2026-08-31.** Cada día recorta a cuatro entradas y ofrece «y N más», que es RF-08: el recorte existe para que un día cargado no empuje los demás fuera de la pantalla. Lo que había antes:: es una lista de días agrupados, y sólo aparecen los días que tienen algo. Falta la grilla del mes y, con ella, el recorte por día que RF-08 necesita para decir «y N más» — hoy RF-08 no tiene implementación porque no hay recorte que lo dispare. | `add_frontend_feature` | Developer | RF-01, RF-08 | D6 |
| ✅ 8 | **Hecho el 2026-08-31**: «Mes anterior» y «Mes siguiente», calculados sobre la ventana que devolvió el backend y conservando los filtros puestos. Lo que había antes: La ventana se cambia editando la URL a mano; los tres enlaces de la pantalla son «Este mes», «Sólo sin recibo» y «Esconder las saldadas». | `add_frontend_feature` | Developer | RF-05 | D5 |
| 🟡 9 | **A medias**: la ventana por defecto y los filtros están cubiertos; **falta el test del control de mes y del recorte por día**, que son de pantalla. Tests de H1: la ventana por defecto es el mes en curso; el mes anterior y el siguiente traen lo suyo; un vencimiento pasado y uno futuro se distinguen; y un día con más de los que entran informa cuántos hay. **Ventana relativa a hoy, nunca un mes fijo**: un test con un mes concreto empieza a fallar solo el día que ese mes queda en el pasado. | `add_tests` | Tester | RF-01, RF-04, RF-05, RF-06, RF-07, RF-08 | D5, D6 |

### H2 — Cuáles ya tienen su recibo y cuáles no

| # | Tarea | Skill | Rol | Cubre | Deriva |
|---|-------|-------|-----|-------|--------|
| ✅ 10 | `purchases`: `receipt_issued` e `is_overdue_without_receipt` en cada tarjeta, calculados desde la factura, y el filtro `without_receipt` aplicado **sobre los campos calculados**, después de armarlos. | `add_backend_feature` | Developer | RF-09, RF-10, RF-11 | — |
| ✅ 11 | Pantalla: la marca de recibo emitido, el señalamiento de las vencidas sin recibo y el enlace que muestra sólo las que no lo tienen. | `add_frontend_feature` | Developer | RF-09, RF-10, RF-11 | — |
| ✅ 12 | Test: el calendario muestra sólo lo que no tiene recibo cuando se lo pide. | `add_tests` | Tester | RF-10 | — |
| ✅ 13 | **Arreglado el 2026-08-31.** El cruce ahora se hace por **la factura que la entrada nombra** y no por las que vencen en la ventana pedida. Lo que había antes:: se arman con las facturas cuyo `due_on` cae en la ventana pedida, no con las facturas de las entradas que se van a mostrar. Una factura **vencida y reprogramada a otro mes** tiene la tarjeta en una ventana y el `due_on` en otra, y vuelve sin proveedor, sin `receipt_issued`, sin `payment_state` y **sin la marca de vencida sin recibo** — que es justo lo contrario de lo que RF-30 pide. El criterio firmado de RF-30 cae entero dentro de un mes y por eso pasa; lo que falla es el requisito apenas la fecha nueva cruza el borde. | `debug` | Developer | RF-02, RF-09, RF-11, RF-30, RF-39 | D1 |
| ✅ 14 | **Hecho el 2026-08-31**, y verificado en las dos direcciones: **falla sin el arreglo** —vuelve `supplier_name = None`— y pasa con él. Cruza el borde del mes a propósito, que es donde el criterio firmado no llegaba. Test de la deriva anterior: mover una factura vencida de fin de mes al mes siguiente y pedir el calendario del mes nuevo — la tarjeta sigue trayendo su proveedor, su estado de pago y `is_overdue_without_receipt`. **Hoy falla.** | `add_tests` | Tester | RF-02, RF-09, RF-11, RF-30, RF-39 | D1 |

### H3 — Agregar un vencimiento propio

| # | Tarea | Skill | Rol | Cubre | Deriva |
|---|-------|-------|-----|-------|--------|
| ✅ 15 | `POST /calendar` → `add_due_date`, con quién lo agregó y cuándo; `DELETE /calendar/{id}` → `remove_due_date`, que **sólo borra los cargados a mano**: uno que viene de una factura no se elimina del calendario. | `add_backend_feature` | Developer | RF-12, RF-13, RF-17, RF-18 | — |
| ✅ 16 | `PATCH /calendar/{id}` → `edit_due_date`: la descripción y el monto de un vencimiento cargado a mano. | `add_backend_feature` | Developer | RF-15 | — |
| ✅ 17 | Pantalla: el formulario de alta con su selector de fecha, la distinción entre lo cargado a mano y lo que viene de una factura, y el botón de borrar que **no se dibuja** para una entrada de factura. | `add_frontend_feature` | Developer | RF-12, RF-14, RF-17, RF-18 | — |
| ✅ 18 | Tests de H3: una entrada a mano que se agrega, se corrige y se borra; y la que viene de una factura, que no se borra. | `add_tests` | Tester | RF-12, RF-14, RF-15, RF-17, RF-18 | — |
| ✅ 19 | **Hecho el 2026-08-31.** `DueDateRead` expone `created_by_user_id`, `created_at` y el nombre, que resuelve la **ruta** con `ActorDirectory` —el módulo guarda un id y no tiene clave foránea a `users`, así que el nombre se resuelve en el borde—. La tarjeta lo muestra. Lo que había antes:: `DueDateRead` no expone `created_by_user_id` ni `created_at`, así que el dato no llega al navegador y ninguna tarjeta lo muestra. El criterio firmado —*"figura con el nombre de Marcela y la fecha en que lo cargó"*— **no se puede verificar en pantalla**. Hay que exponerlo y resolverlo a un nombre. | `add_feature` | Developer | RF-13 | D10 |
| ✅ 20 | **Hecho el 2026-08-31.** Ahora publica `ManualChangeRecorded` por cada campo que cambia, con **el valor anterior**, que era lo que obligaba a mirar antes de escribir. Va a la bitácora por el mismo camino que la corrección de un proveedor, sin que este módulo sepa que existe una bitácora. Lo que había antes:: ni quién, ni cuándo, ni el valor anterior — el servicio recibe `actor_user_id` y lo descarta. El mecanismo existe y el mismo módulo lo usa a tres pantallas de distancia (`ManualChangeRecorded` → `operations`). | `debug` | Developer | RF-16 | D2 |
| ✅ 21 | **Hecho el 2026-08-31**: botón «Corregir» con su formulario, sólo para las entradas cargadas a mano. Corregir un monto dejó de ser borrar y volver a cargar. Lo que había antes:: el endpoint y la Server Action `editDueDate` existen y no hay botón de corregir. Hoy, corregir un monto mal cargado es borrar y volver a cargar. | `add_frontend_feature` | Developer | RF-15 | D4 |
| ✅ 22 | **Hecho el 2026-08-31**: tres tests —quién la cargó y cuándo, la corrección con su valor anterior, y quién movió— más el que fija qué hacen los dos filtros con una entrada cargada a mano. Tests: la corrección de una entrada a mano deja su registro con el valor anterior, quién y cuándo; y la tarjeta muestra quién la cargó y en qué fecha. | `add_tests` | Tester | RF-13, RF-16 | D2, D10 |

### H4 — Reprogramar arrastrando, sin perder la fecha original

| # | Tarea | Skill | Rol | Cubre | Deriva |
|---|-------|-------|-----|-------|--------|
| ✅ 23 | `PUT /calendar/{id}/date` → `move_due_date`: conserva la fecha original, registra quién movió y cuándo, **ofrece el motivo sin exigirlo**, y marca la entrada como reprogramada. | `add_backend_feature` | Developer | RF-19, RF-20, RF-21, RF-22, RF-24, RF-42 | — |
| ✅ 24 | `purchases`: mover a una fecha ya pasada devuelve `409` y la confirmación vuelve como `confirm_past=true`. Es lo que «pedir confirmación» significa sobre HTTP sin dejar un vencimiento a medio mover en el servidor. | `add_backend_feature` | Developer | RF-25 | — |
| ✅ 25 | `purchases`: **la bisagra de la feature.** `was_overdue` decide todo — reprogramada **antes** de vencer, se reescribe `invoice.due_on` y con eso se mueven el plazo del recibo y la medición del atraso; reprogramada **después**, `invoice.due_on` no se toca y de ahí salen solos los tres efectos: el recibo sigue negado, el atraso se mide contra la fecha original y la factura sigue señalada como vencida sin recibo. | `add_backend_feature` | Developer | RF-26, RF-27, RF-28, RF-29, RF-30 | — |
| ✅ 26 | `purchases`: `changes_of()` — el historial completo de una tarjeta reprogramada, en orden. Es lo que hace que **dos personas moviendo lo mismo no necesiten ningún bloqueo**: vale el último y los dos quedan. | `add_backend_feature` | Developer | RF-23, RF-34 | — |
| ✅ 27 | Pantalla: mover una entrada, y al abrirla su fecha original, todas sus reprogramaciones y los motivos escritos, con la marca de reprogramada. | `add_frontend_feature` | Developer | RF-23, RF-24 | — |
| ✅ 28 | Tests de H4: dónde estaba y quién la movió; mover al pasado pregunta primero; reprogramar antes de vencer mueve el plazo del recibo; y **reprogramar una que ya venció no cambia nada de eso** — el test que nunca hay que debilitar, porque es también la defensa de RF-34 de la 005: si mover una tarjeta habilitara el recibo de una factura vencida, ese requisito dejaría de valer con sólo arrastrar. | `add_tests` | Tester | RF-20, RF-21, RF-22, RF-23, RF-25, RF-26, RF-27, RF-28, RF-29 | — |
| ✅ 29 | **Hecho el 2026-08-31**: las tarjetas se arrastran y los días las aceptan. Arrastrar y elegir la fecha terminan en la misma llamada, porque para el sistema son la misma decisión. Lo que había antes: Mover se hace con dos `window.prompt` encadenados —fecha y motivo—, y H4 es la historia que lo pide por su nombre. El backend no distingue cómo lo dijo la persona: es trabajo de frontend sobre una llamada que ya está. | `add_frontend_feature` | Developer | RF-19 | D3 |
| ✅ 30 | **Hecho el 2026-08-31**: el historial dice «lo movió Marcela» junto a la fecha y el motivo. Lo que había antes: La tarjeta muestra `de → a` y el motivo; el actor está guardado y viaja en el schema, y la pantalla no lo resuelve a un nombre. La prueba firmada de H4 dice *"se ve que originalmente vencía el 10 y quién lo movió"*. | `add_frontend_feature` | Developer | RF-21 | D7 |

### H5 — Dos personas, el mismo calendario

> **La historia se construye, y su diseño ya está cerrado** en `plan.md` → *La H5: el canal en vivo*
> (decisión del 2026-08-31): **SSE** sobre `GET /calendar/stream`, **`LISTEN`/`NOTIFY` de Postgres**
> para cruzar los dos workers de uvicorn, y un **Route Handler de Next** que pone el `Bearer` desde
> la cookie. Ninguna dependencia nueva. Las tareas de abajo ya no deciden nada: construyen.
>
> **El orden importa.** Las tareas 31 y 32 van primero aunque parezcan detalles: con el canal andando
> y esas dos sin cerrar, agregar y corregir no llegarían a nadie y ningún cambio diría quién lo hizo
> — se vería como un bug del canal, y no lo sería.
>
> RF-34 no está en esta lista: está cumplido, lo resuelve `core.due_date_change` y no depende del
> canal.

| # | Tarea | Skill | Rol | Cubre | Deriva |
|---|-------|-------|-----|-------|--------|
| ✅ 31 | **Hecho el 2026-08-31**: los cuatro verbos publican por un único `_announce`. `add_due_date` y `edit_due_date` no publicaban nada, con el mismo `action` que ya usan los otros dos verbos (`added`, `edited`). Sin esto, el canal transporta dos de los cuatro verbos que RF-31 nombra. | `debug` | Developer | RF-31 | D8 |
| ✅ 32 | **Hecho el 2026-08-31**: las cuatro rutas pasan `current_user.name` y el evento lo lleva. `remove_due_date` mandaba el nombre vacío, que hoy manda vacío aunque la ruta lo tiene a mano. Es la diferencia entre «alguien movió esto» y RF-33. | `debug` | Developer | RF-33 | D9 |
| ✅ 33 | **Hecho el 2026-08-31**: `app/shared/live.py` —transporte sin dominio— con el `NOTIFY` en la transacción del publicador y una conexión `LISTEN` por worker, abierta en el `lifespan`. Si no puede abrirse, la app sirve igual y sólo se pierde el vivo. El handler hace `NOTIFY` en la transacción del publicador, y la conexión dedicada que hace `LISTEN`, abierta y cerrada en el `lifespan` —una por worker—. El `NOTIFY` es transaccional: si la transacción aborta, nadie recibe nada, y por eso esto **no** viola `GEN-09`. Cero dependencias nuevas: el bus es la base que ya está. | `add_backend_feature` | Developer | RF-31, RF-32 | D0 |
| ✅ 34 | **Hecho el 2026-08-31.** `GET /calendar/stream`: un `StreamingResponse` de `text/event-stream` por persona conectada, con `require_section(CALENDAR, READ)` —**`READ`, porque ventas también mira**— que reparte lo que llega por `LISTEN`. Un mensaje por cambio, con el evento serializado; nunca el calendario entero. | `add_backend_feature` | Developer | RF-31, RF-32, RF-33 | D0 |
| ✅ 35 | **Hecho el 2026-08-31**, y con un motivo que no era obvio: el proxy general lee `arrayBuffer()`, que espera a que la respuesta termine — sobre un stream se colgaría para siempre. Este pasa el cuerpo tal cual. El **Route Handler** que lee la cookie del lado servidor, abre el stream contra la API con su `Bearer` y lo reenvía al navegador. Existe por una razón concreta: `EventSource` no manda headers, y **un token no va en una query string**. | `add_frontend_feature` | Developer | RF-31, RF-32 | D0 |
| ✅ 36 | **Hecho el 2026-08-31**: `useLiveCalendar` releé la pantalla con cada cambio y dice quién lo hizo; el corte lo avisa el evento `error` de `EventSource`, no un temporizador adivinando. Pantalla: el calendario se actualiza con lo que llega **sin recargar**, diciendo quién hizo el cambio; **avisa cuando la conexión se corta** —el evento `error` de `EventSource`, no un `setTimeout` adivinando— y al reconectar **relee el calendario entero** en lugar de intentar recuperar lo que se perdió. | `add_frontend_feature` | Developer | RF-31, RF-32, RF-33, RF-35, RF-36 | D0 |
| ✅ 37 | **Hecho el 2026-08-31**: los cuatro verbos anuncian con nombre; **un movimiento rechazado no anuncia nada** —que es lo que sostiene `GEN-09`—; y dos movimientos seguidos dejan los dos en el historial (RF-34). Tests de H5: el cambio de una sesión llega a otra y dice quién lo hizo; **una transacción que aborta no notifica a nadie** —el que sostiene que `GEN-09` se cumple—; el corte avisa y la reconexión pone al día; y **dos movimientos sobre la misma entrada dejan los dos en el historial valiendo el último** (RF-34, hoy cumplido y sin test propio). ⚠️ Un test que publique y escuche **en el mismo proceso pasa siempre y no prueba nada**: el despliegue corre con `--workers 2`, y lo que se rompe es cruzar de un worker al otro. | `add_tests` | Tester | RF-31, RF-32, RF-33, RF-34, RF-35, RF-36 | D0 |

### H6 — Ventas mira, no toca

| # | Tarea | Skill | Rol | Cubre | Deriva |
|---|-------|-------|-----|-------|--------|
| ✅ 38 | Las cinco rutas con su autorización declarada: `READ` sobre `CALENDAR` para el `GET`, `WRITE` para las cuatro escrituras. **RF-37 y RF-38 no se implementan acá: se declaran** — la matriz de `identity` ya le da a ventas `READ` sobre el calendario desde la 002. El calendario es la única superficie de `purchases` que ventas alcanza, y está dicho en el docstring del archivo de rutas para que la próxima ruta no herede la excepción por descuido. | `add_backend_feature` | Developer | RF-37, RF-38 | — |
| ⬜ 39 | Test de comportamiento: **una request real como ventas** contra las cuatro escrituras devuelve `403`, y el `GET` devuelve `200`. Hoy RF-38 está probado por construcción —la matriz y el test de arquitectura— y no por comportamiento. | `add_tests` | Tester | RF-37, RF-38 | — |

### H7 — Qué falta pagar, sin salir del calendario

| # | Tarea | Skill | Rol | Cubre | Deriva |
|---|-------|-------|-----|-------|--------|
| ✅ 40 | `purchases`: el estado de pago de cada tarjeta que viene de una factura, calculado con `_read_invoices`, y el filtro `hide_settled`. | `add_backend_feature` | Developer | RF-39, RF-40 | — |
| ✅ 41 | Pantalla: el estado de pago en la tarjeta y el enlace que esconde las saldadas. | `add_frontend_feature` | Developer | RF-39, RF-40 | — |
| ⬜ 42 | Tests de H7: esconder las saldadas las esconde y deja el resto; y **qué hacen los dos filtros con una entrada cargada a mano** —sin recibo posible y sin estado de pago—, que hoy pasa los dos sin que ningún test lo fije. **Decidir con el Lead si eso es lo que la spec quiere antes de escribir el assert**: puede ser un defecto o puede ser lo correcto, y el test lo va a congelar. | `add_tests` | Tester | RF-39, RF-40 | — |

### H8 — El calendario en el teléfono

| # | Tarea | Skill | Rol | Cubre | Deriva |
|---|-------|-------|-----|-------|--------|
| ✅ 43 | `PUT /calendar/{id}/date` sirve igual para arrastrar que para elegir la fecha: el backend no distingue cómo lo dijo la persona. Las dos formas de H8 y de H4 dependen **sólo del frontend**. | `add_backend_feature` | Developer | RF-42 | — |
| ✅ 44 | **Hecho el 2026-08-31**: mover abre un panel con `<Input type="date">` y un motivo opcional. Se fue el `window.prompt` donde la fecha se escribía a mano — que es la peor forma de elegir un día en una pantalla que existe para no equivocarse de día. Lo que había antes:: hoy la única forma es `window.prompt('Fecha nueva (aaaa-mm-dd)')`, donde la persona **escribe** la fecha como texto, y H8 se prueba *"eligiendo la fecha nueva de un selector"*. El propio componente demuestra que el patrón está a mano: el formulario de alta ya usa un `<Input type="date">` — es la deriva más barata de cerrar de toda la lista. **Corregir también el docstring del componente**, que afirma lo contrario de lo que el código hace. | `add_frontend_feature` | Developer | RF-42 | D11 |
| ⬜ 45 | Verificación a mano, con Playwright y en un teléfono real: **el calendario se consulta desde un teléfono** (RF-41, que no tiene código propio —la pantalla usa utilidades responsive y nunca se abrió en uno—), se **arrastra** una tarjeta (RF-19) y se mueve **eligiendo la fecha de un selector** (RF-42). Nada de esto necesita el portal: la feature no extrae nada. | `add_tests` | Tester | RF-19, RF-41, RF-42 | D3, D11 |

## Cobertura de requisitos

<!--
  Todo requisito funcional de la spec tiene al menos una tarea que lo construye y
  al menos un test que lo verifica. Un RF sin fila acá es alcance firmado que nadie
  se comprometió a hacer — y es exactamente lo que /converge va a encontrar.
-->

Los 42 requisitos firmados. **Una tarea o un test en ⬜ significa que ese requisito todavía no está
cubierto**, aunque tenga otras tareas en ✅.

| Requisito | Tareas | Test |
|-----------|--------|------|
| RF-01 | 3, 5, 7 | 🟡9 |
| RF-02 | 3, 5, 13 | 6, 14 |
| RF-03 | 1, 2 | 6 |
| RF-04 | 4 | 9 |
| RF-05 | 8 | 🟡9 |
| RF-06 | 3, 5 | 9 |
| RF-07 | 5 | 9 |
| RF-08 | 7 | 🟡9 |
| RF-09 | 10, 11, 13 | 12, 14 |
| RF-10 | 10, 11 | 12 |
| RF-11 | 10, 11, 13 | 14 |
| RF-12 | 1, 15, 17 | 18 |
| RF-13 | 15, 19 | 22 |
| RF-14 | 17 | 18 |
| RF-15 | 16, 21 | 18 |
| RF-16 | 20 | 22 |
| RF-17 | 15, 17 | 18 |
| RF-18 | 15, 17 | 18 |
| RF-19 | 23, 29 | ⬜45 |
| RF-20 | 1, 23 | 28 |
| RF-21 | 23, 30 | 28, 22 |
| RF-22 | 23 | 28 |
| RF-23 | 26, 27 | 28 |
| RF-24 | 23, 27 | 28 |
| RF-25 | 24 | 28 |
| RF-26 | 25 | 28 |
| RF-27 | 25 | 28 |
| RF-28 | 25 | 28 |
| RF-29 | 25 | 28 |
| RF-30 | 25, 13 | 14 |
| RF-31 | 31, 33, 34, 35, 36 | 37 |
| RF-32 | 33, 34, 35, 36 | 37 |
| RF-33 | 32, 34, 36 | 37 |
| RF-34 | 26 | 37 |
| RF-35 | 36 | 37 |
| RF-36 | 36 | 37 |
| RF-37 | 38 | ⬜39 |
| RF-38 | 38 | ⬜39 |
| RF-39 | 40, 41, 13 | 14, 42 |
| RF-40 | 40, 41 | 42 |
| RF-41 | ⬜45 (sin código propio: se verifica, no se construye) | ⬜45 |
| RF-42 | 43, 44 | ⬜45 |

**Qué dice la tabla, leída de una:** 14 requisitos están construidos y verificados; **28 tienen algo
en ⬜**, y de esos **seis —RF-31 a RF-33, RF-35, RF-36 y RF-41— no tienen ni una línea propia**.
RF-41 es un caso aparte: no es que falte código, es que **nunca se probó en un teléfono**, y no hay
manera de demostrarlo sin abrirlo en uno.

## Decisiones tomadas el 2026-08-31

Salieron de la corrida de `/analyze` (`checklists/analyze.md`). Las dos primeras las tomó el humano;
la tercera es de arquitectura y está justificada en `plan.md`.

| Decisión | Quién | Consecuencia acá |
|---|---|---|
| **La H5 se construye**, no se difiere | El humano | Las tareas 31 a 37 pasan de «falta decidir» a «falta escribir». La spec firmada no se toca |
| **No se pone el cartel provisorio** de «no se actualiza sola» | El humano | La antigua tarea 36 se dio de baja: era superficie que el cliente no firmó |
| **SSE + `LISTEN`/`NOTIFY` + Route Handler** | Backend-Architect | El diseño está en `plan.md`; ninguna tarea de acá decide transporte |

Y una corrección de la spec que no cambia el alcance: **el criterio de aceptación de RF-30 ahora
mueve la fecha al mes siguiente**. El ejemplo firmado la movía dentro del mismo mes, así que pasaba
aunque el requisito fallara — que es justo la deriva D1 de las tareas 13 y 14.

## Lo que queda por decidir

Nada bloquea. Lo único abierto es un hallazgo **sin `RF`** que registró `/analyze` y que este
documento no puede resolver solo: la pantalla del calendario lee con `fetchFromApi`, que colapsa
`401`/`403`, `404`, `500` y timeout en el mismo `null`, y ante cualquiera de los cuatro dice «No
tenés permiso». Con la API caída, al **dueño** le da un consejo sobre el que nadie puede actuar. El
arreglo es leer `readFromApi`, y el test de arquitectura que lo obliga existe **pero sólo alcanza a
las pantallas de la 003**. Extenderlo al calendario es una decisión del Lead, no alcance firmado.
