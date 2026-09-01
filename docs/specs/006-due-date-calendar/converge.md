# Informe de convergencia — 006, Calendario de vencimientos

**Corrido el 2026-08-31** · Rol: `Lead` · Skill: `agents/skills/converge.md`

> `review_feature` pregunta *¿está bien escrito?*. Esto pregunta *¿es lo que se firmó?*.

**Qué se comparó.** Los 42 requisitos de `spec.md` (firmada el 2026-08-30) contra
`backend/app/modules/purchases/`, `frontend/`, la suite, los siete diagramas y las doce derivas
`D0`–`D11` que `plan.md` había dejado anotadas para esta corrida. La rama es
`fix/extractions-were-wedged`, que no sigue `feat/<NNN-feature>`, así que el changeset se armó con
los archivos que nombran `plan.md` y `tasks.md` y se completó con búsquedas sobre el código.

---

> **Segunda corrida, 2026-08-31 (misma fecha).** El humano decidió construir la barra plegable y
> corregir todo lo hallado. Los cinco hallazgos están cerrados y verificados; el veredicto final
> está al pie, en *Cierre*. Lo que sigue —el veredicto de la primera corrida y sus hallazgos— se
> deja tal como se emitió: un hallazgo que se reescribe después de arreglarlo deja de ser evidencia
> de que el código y la spec se habían separado.

## Veredicto de la primera corrida: **Deriva mayor** 🔴

**Bloquea el gate.** La feature no pasa al `Code-Reviewer` hasta que el humano resuelva el
hallazgo H1.

Hay **un requisito firmado que hoy no se cumple** —RF-41, consultar el calendario desde un
teléfono— y **está demostrado, no supuesto**: la verificación a mano de la tarea 45 se corrió hoy
y quedó con capturas y medidas en `evidence/README.md`. Otros dos requisitos quedan **Parciales**
por la forma de la pantalla, no por su contenido.

Lo demás converge, y conviene decirlo con la misma claridad: **39 de 42 requisitos tienen
implementación con evidencia localizable**, incluidas las ocho derivas que `plan.md` daba por
abiertas y que el trabajo del 2026-08-31 cerró. No apareció **una sola línea de alcance no
pedido**.

---

## Hallazgos

| # | Tipo | Qué dice el artefacto | Qué hace el código | Rol dueño | Acción |
|---|---|---|---|---|---|
| **H1** | Requisito sin implementar | RF-41: *"El sistema debe permitir consultar el calendario desde un teléfono"*, y el criterio firmado *"El calendario se abre desde un teléfono y se ve qué vence cada día"* | El **contenido** del calendario está bien en 390px: sin desplazamiento horizontal, ninguna tarjeta se sale, el recorte por día sigue avisando, los botones se tocan. Pero **la primera pantalla entera es el menú**: la barra lateral mide 832px de alto sobre un viewport de 664px y el título «Calendario» arranca en y=864px. Hay que desplazarse una pantalla y media para ver el primer vencimiento. `frontend/app/(private)/layout.tsx`, `frontend/components/auth/Navigation.tsx:105` (`w-60 flex-none`) | **Humano** decide; ejecuta `Frontend-Architect` | Ver las dos opciones abajo |
| **H2** | Requisito sin implementar (Parcial) | RF-01 y H1: *"ver en un calendario todo lo que vence, **mes por mes**"*; el cliente pidió *"un calendario visual donde se vea de un vistazo"* | La pantalla es una **lista de los días que tienen algo**, ordenada por fecha: un día sin vencimientos no existe en pantalla, y no hay grilla del mes. Cada vencimiento **sí** está bajo su día, que es lo que RF-01 dice literalmente. `frontend/components/purchases/CalendarGrid.tsx:134-150`. Es la mitad de `D6` que quedó abierta: `tasks.md` cerró la tarea 7 por RF-08 —el recorte— y su propio texto sigue diciendo *"falta la grilla del mes"* | **Humano** decide; ejecuta `Frontend-Architect` | Construir la grilla, o dejar por escrito que la lista agrupada es lo acordado |
| **H3** | Requisito sin implementar (Parcial) | RF-02: *"su descripción, su monto y **su proveedor cuando lo tenga**"*, y `flujo-general.mmd` paso 3 lo repite | El backend **calcula** el proveedor (`service.py:2030`, `DueDateRead.supplier_name` en `schemas.py:333`) y **ninguna pantalla lo muestra**: `CalendarGrid` no lee `supplier_name` en ninguna línea. El proveedor se ve sólo de refilón, dentro de la descripción de las tarjetas que vienen de una factura (`«Factura 0001-123 — FERRUM SA»`, `service.py:1975`), que es el texto crudo del portal y no el proveedor resuelto. Un vencimiento cargado a mano no muestra proveedor ninguno, lo cual es correcto | `Developer` | Renderizar `supplier_name` en la tarjeta. Es una línea, y el dato ya viaja |
| **H4** | Deriva del plan | `plan.md` → *"Deriva contra la spec firmada"* lista `D0`–`D11` como abiertas, y afirma cosas que hoy son falsas: *"no hay canal en vivo"* (`D0`), *"no se puede arrastrar"* (`D3`), *"no hay botón de corregir"* (`D4`), *"no hay control para avanzar ni retroceder de mes"* (`D5`), *"corregir no registra nada"* (`D2`) | **Ocho de las doce están cerradas** y verificadas: `D0` (H5 completa), `D1` (`calendar()` usa `invoices_by_ids`, `service.py:2011`), `D2` (`edit_due_date` publica `ManualChangeRecorded`, `:2099`), `D3` (arrastre, `CalendarGrid.tsx:151-156` y `:143-148`), `D4` (botón «Corregir», `:203`), `D5` (control de mes, `page.tsx:79-87`), `D7` y `D10` (quién movió y quién cargó, en pantalla), `D8`, `D9` y `D11` también. Queda abierta media `D6` → H2 | `Frontend-Architect` · `Backend-Architect` | Reescribir la sección: el plan describe un producto que ya no existe |
| **H5** | Deriva del plan | `plan.md` → `D0` cita `frontend/app/(private)/calendario/page.tsx:26-29` como el lugar donde está anotado que la pantalla no se actualiza sola | Ese comentario ya no existe: la pantalla **sí** se actualiza sola y el docstring lo dice. La referencia quedó apuntando a otra cosa | `Frontend-Architect` | Se corrige junto con H4 |

**Ningún hallazgo de tipo *Alcance no pedido*.** Se recorrieron las cinco rutas del
`calendar_router`, las dos tablas (`core.due_date`, `core.due_date_change`), los seis schemas
`DueDate*`/`CalendarRead`, la pantalla y sus dos formularios: cada uno tiene un requisito que lo
pide. El único andamiaje sin requisito propio —`LISTEN`/`NOTIFY` y el Route Handler de Next— está
justificado en `plan.md` → *"Cómo llega el cambio de un worker al otro"*.

**Ninguna tarea sin respaldo.** Las 45 tareas de `tasks.md` se contrastaron contra el archivo que
nombran. Las cuatro que quedaban en ⬜ o 🟡 se cerraron hoy y su código existe: los cinco tests de
ruta de la 39, los diez tests de pantalla de la 9, `TestWhatTheFiltersDoWithAHandMadeEntry` de la
42, y el acta de la 45.

**Ninguna contradicción con las reglas del dominio.** La feature no toca `portal/` ni `raw`: nace
de una factura que ya está en `core` y escribe sólo en `core.due_date`. No hay HTTP contra SIGProv,
no hay escritura en `raw`, no hay credenciales.

**Los diagramas compilan y son verdad**, con una excepción que ya está en H3: `flujo-general.mmd`
promete el proveedor en la tarjeta y la pantalla no lo muestra. El resto —incluida
`estados-vencimiento.mmd`, transición por transición— corresponde a lo que el servicio permite.

---

## Las dos salidas de H1, con lo que cuesta cada una

La decisión **es del humano** (Artículo V). El agente no elige.

**Opción 1 — Implementar lo que falta.** Que la barra lateral se pliegue en pantallas angostas:
un encabezado con el nombre de la sección y un botón que la abre. Vuelve al `Developer` y después
otra vez al `Tester`.
*Costo:* toca el shell de **todas** las pantallas, no sólo el calendario, y una barra plegable es
**superficie nueva que el cliente no firmó** — el mismo argumento por el que el 2026-08-31 se
decidió no construir el cartel provisorio de la H5. Es trabajo de la 012, que ya está abierta.

**Opción 2 — Corregir la spec.** Si el teléfono no era un requisito de esta feature sino del
sistema entero, RF-41 sale de la 006 y entra donde corresponda. Vuelve al `Solution-Designer`, y
**el cliente vuelve a firmar** con `/approve-spec`: el gate de la firma se reabre.
*Costo:* H8 se queda con RF-42 solo, y el cliente tiene que aceptar que el teléfono se difiere.

**Lo que no es una salida:** darlo por bueno. La verificación se corrió, y el resultado fue que no.

---

## Tabla de trazabilidad

| Requisito | Qué promete la spec | Dónde está implementado | Evidencia | Estado |
|---|---|---|---|---|
| RF-01 | Un calendario con cada vencimiento en su fecha | `lib/purchases/calendar.ts::weeksOf`; `CalendarGrid.tsx`, la grilla y la lista | Grilla del mes desde `md`, días agrupados en un teléfono; `calendar-day-trim.test.tsx` | Implementado |
| RF-02 | Descripción, monto y proveedor | `CalendarGrid.tsx::DueDateCard`; `service.py:2030` | Descripción, monto y `supplier_name` en la tarjeta | Implementado |
| RF-03 | La factura se pone sola en el calendario | `service.py::_sync_due_date:1964` | `test_an_invoice_puts_itself_on_the_calendar` | Implementado |
| RF-04 | Abre en el mes en curso | `routes.py::read_calendar:536` → `_month_of` sobre `today_here()` | `evidence/rf41-mes-en-curso.png`: 01/08 al 31/08 | Implementado |
| RF-05 | Avanzar y retroceder de mes | `lib/purchases/calendar.ts::windowFor`; `page.tsx:79-87` | `frontend/tests/calendar-month-control.test.ts` (6 tests) | Implementado |
| RF-06 | Distingue lo pasado de lo por venir | `service.py:2027` (`is_past`); `CalendarGrid.tsx:168` | «ya pasó» en la tarjeta | Implementado |
| RF-07 | Del vencimiento a la factura | `CalendarGrid.tsx:190-194` | Enlace a `/facturas/{invoice_id}` | Implementado |
| RF-08 | Un día cargado dice cuántos hay y deja verlos | `CalendarGrid.tsx:150` y `:313-330`; `PER_DAY=4` | `frontend/tests/calendar-day-trim.test.tsx` (4 tests) + `evidence/rf41-dia-abierto.png` | Implementado |
| RF-09 | Distingue las que tienen recibo | `service.py:2031` ← `_read_invoices:994` | `CalendarGrid.tsx:171` | Implementado |
| RF-10 | Ver sólo las que no tienen recibo | `service.py:2041`; `page.tsx:88-90` | `test_it_can_show_only_what_has_no_receipt` | Implementado |
| RF-11 | Señala las vencidas sin recibo | `service.py:1011`, `:2032`; `CalendarGrid.tsx:158-160` | Borde y fondo de peligro + «venció sin recibo» | Implementado |
| RF-12 | Agregar un vencimiento a mano | `service.py::add_due_date:2047`; `POST /calendar` | `test_a_hand_made_entry_is_added_corrected_and_removed` | Implementado |
| RF-13 | Queda quién lo agregó y cuándo | `models.py:464` + `DueDateRead.created_by_*`; `CalendarGrid.tsx:174-178` | `test_adding_one_records_who_and_when`; «lo cargó Marcela el 31/08/2026» en las capturas | Implementado |
| RF-14 | Distingue lo cargado a mano de lo que viene de una factura | `DueDateOrigin` (`models.py:97`); `CalendarGrid.tsx:167` | «De una factura» / «Cargado a mano» | Implementado |
| RF-15 | Corregir descripción y monto | `service.py::edit_due_date:2074`; botón «Corregir» en `CalendarGrid.tsx:208-215` | `PATCH /calendar/{id}` | Implementado |
| RF-16 | Queda quién, cuándo y el valor anterior | `service.py:2089-2110` → `ManualChangeRecorded` | `test_correcting_one_leaves_what_it_said_before` | Implementado |
| RF-17 | Eliminar un vencimiento cargado a mano | `service.py::remove_due_date:2198` | `test_a_hand_made_entry_is_added_corrected_and_removed` | Implementado |
| RF-18 | No se elimina el que viene de una factura | `service.py::_only_manual` | `test_an_entry_that_comes_from_an_invoice_is_not_removed` | Implementado |
| RF-19 | Mover arrastrando | `CalendarGrid.tsx:151-156` y `:143-148` (`draggable`, `onDragStart`, `onDrop`) | **Verificado a mano**: del 26/08 al 30/08, `evidence/rf19-arrastre-escritorio.png` | Implementado |
| RF-20 | Conserva la fecha anterior | `models.py::DueDate.original_date`; `service.py:2151` | `test_it_keeps_where_it_was_and_who_moved_it`; en la base: `26/08 → 30/08` | Implementado |
| RF-21 | Queda quién lo movió y cuándo | `DueDateChange.actor_user_id`; `routes.py::_name_whoever_touched_the_calendar` | `test_a_move_carries_who_made_it`; «lo movió Marcela» en pantalla | Implementado |
| RF-22 | Ofrece motivo sin exigirlo | `DueDateMove.reason` opcional; `CalendarGrid.tsx:253` | Verificado a mano: el arrastre sin motivo, el selector con motivo | Implementado |
| RF-23 | Fecha original, todas las reprogramaciones y sus motivos | `service.py:2035-2039`; `CalendarGrid.tsx:179-190` | `test_it_keeps_where_it_was_and_who_moved_it` | Implementado |
| RF-24 | Señala los reprogramados | `DueDate.was_rescheduled`; `CalendarGrid.tsx:169-171` | «reprogramado, original dd/mm/aaaa» | Implementado |
| RF-25 | Pide confirmación al mover al pasado | `service.py:2145-2148` (`ConflictError`) + `CalendarGrid.tsx:83-89` | `test_moving_it_into_the_past_asks_first`; **verificado a mano en los dos sentidos**: sin respuesta no movió nada | Implementado |
| RF-26 | Reprogramar antes de vencer mueve el plazo del recibo | `service.py:2164-2166`; `issue_receipt:1800` | `test_rescheduling_before_it_falls_due_moves_the_receipt_deadline` | Implementado |
| RF-27 | …y el atraso se mide contra la fecha nueva | `service.py:1483-1486` sobre `invoice.due_on` | mismo test | Implementado |
| RF-28 | Reprogramar después de vencer mantiene impedido el recibo | `service.py:2164` (`was_overdue` → **no** escribe `due_on`) | `test_rescheduling_one_that_already_fell_due_changes_none_of_that` | Implementado |
| RF-29 | …y el atraso se mide contra la fecha original | mismo `was_overdue`: `due_on` queda en la original | mismo test | Implementado |
| RF-30 | …y sigue señalada como vencida sin recibo, aun en otro mes | `service.py:2011` (`invoices_by_ids`, no por ventana) | `TestAnOverdueOneMovedToAnotherMonth` | Implementado |
| RF-31 | El cambio llega a las otras pantallas | `DueDateChanged` en los cuatro verbos; `GET /calendar/stream:653` | `test_a_change_that_commits_is_announced_with_who_made_it` | Implementado |
| RF-32 | Sin recargar | `useLiveCalendar.ts` (`EventSource` + `router.refresh`) | — | Implementado |
| RF-33 | Dice quién lo hizo | `actor_name` en los cuatro verbos; `CalendarGrid.tsx:120-123` | mismo test | Implementado |
| RF-34 | Dos movimientos: vale el último, quedan los dos | `add_due_date_change` acumula | `test_two_people_moving_the_same_entry_keep_both_moves` | Implementado |
| RF-35 | Avisa si se corta la conexión | `useLiveCalendar.ts` (`onerror` → `caido`); `CalendarGrid.tsx:113-119` | — | Implementado |
| RF-36 | Al reconectar, muestra el estado al día | `useLiveCalendar.ts`: relee todo, no parchea | — | Implementado |
| RF-37 | Ventas consulta el calendario | `routes.py:531` (`READ` sobre `CALENDAR`) | `test_sales_can_read_the_calendar` → 200 | Implementado |
| RF-38 | Ventas no agrega, corrige, mueve ni elimina | `routes.py:578`, `:597`, `:615`, `:638` (`WRITE`) | `test_sales_is_refused_on_every_write` → 403 en las cuatro | Implementado |
| RF-39 | Estado de pago de cada factura | `service.py:2033` ← `_read_invoices`; `CalendarGrid.tsx:173` | — | Implementado |
| RF-40 | Ocultar las saldadas | `service.py:2043`; `page.tsx:91-93` | `test_a_hand_made_entry_survives_both_filters` | Implementado |
| RF-41 | Consultar el calendario desde un teléfono | `components/auth/Navigation.tsx` (la barra plegable) | `navigation-collapsible.test.tsx` + `evidence/README.md`: el calendario se ve al abrir, sin desplazarse | Implementado |
| RF-42 | Mover eligiendo la fecha, sin arrastrar | `CalendarGrid.tsx:238-268` (`<Input type="date">` + motivo) | **Verificado a mano en el teléfono**: `evidence/rf42-*.png`; en la base, `30/08 → 20/09` con motivo | Implementado |

**39 Implementado · 2 Parcial · 1 Ausente** en la primera corrida. Los estados de la tabla ya
reflejan la corrección; qué era cada uno antes está en los hallazgos de arriba.

---

## Validación de la corrida

- [x] Los 42 requisitos tienen fila y estado.
- [x] Ninguna fila `Implementado` sin archivo, símbolo, ruta o test.
- [x] Sentido inverso recorrido: rutas, tablas, schemas, pantallas y formularios. Sin alcance no pedido.
- [x] Las 45 tareas contrastadas contra el archivo que nombran.
- [x] `plan.md` y su *Contexto de traspaso* comparados contra el código → H4, H5.
- [x] `bash scripts/diagrams/validate.sh` pasa; los siete diagramas se leyeron contra el código.
- [x] Las cinco reglas del dominio contrastadas: ninguna en riesgo.
- [x] Veredicto escrito, cada hallazgo con tipo, rol dueño y acción.
- [x] No se tocó código ni artefactos de otros roles: lo único escrito es este informe.


---

## Cierre — segunda corrida, 2026-08-31

**Veredicto: Converge** ✅ · **El gate se abre**: la feature pasa al `Code-Reviewer`.

Los cinco hallazgos, uno por uno:

| # | Qué se hizo | Cómo se sostiene |
|---|---|---|
| **H1** · RF-41 | **La barra lateral se pliega** en pantallas angostas (`components/auth/Navigation.tsx`): una franja con dónde está parada la persona y el botón que abre el resto, cerrada por omisión y que se cierra sola al elegir una sección. Desde `md` no cambió nada. La decisión —construirlo, sabiendo que toca el shell de todas las pantallas— **la tomó el humano**, que es lo que el informe pedía | `frontend/tests/navigation-collapsible.test.tsx` (4 tests) fija la conducta; la vista, medida a mano: la barra pasó de **832px a 76px** y el calendario, de empezar en y=864px a **y=108px** sobre un viewport de 664px (`evidence/README.md`) |
| **H2** · RF-01 | **La pantalla es una grilla del mes**: semanas de lunes a domingo, y un día sin vencimientos que existe igual, vacío — que es exactamente lo que una lista de los días con algo no puede mostrar. Elegir un día abre su tarjeta entera debajo. En un teléfono no hay grilla y siguen los días uno debajo del otro, porque siete columnas en 390px no se leen: las dos vistas se dibujan y el CSS elige | `weeksOf`/`isInWindow` en `lib/purchases/calendar.ts`, con 4 tests; `calendar-day-trim.test.tsx` fija que la grilla tiene 42 celdas para marzo y que la celda también recorta. Visto en `evidence/rf01-grilla-del-mes.png` |
| **H3** · RF-02 | **El proveedor se muestra** en la tarjeta (`DueDateCard`). El backend ya lo calculaba y nadie lo leía | Una línea, y el dato ya viajaba en `DueDateRead.supplier_name` |
| **H4** · plan viejo | La sección *Deriva contra la spec firmada* de `plan.md` está reescrita: las doce `D0`–`D11` figuran **cerradas**, con cómo se cerró cada una. La lista no se borró —qué faltaba, y por qué, es lo que explica la forma que tiene el código— | `plan.md` |
| **H5** · referencia muerta | El *Contexto de traspaso* y los *Riesgos* de `plan.md` describen la feature terminada: cuatro riesgos pasaron a cerrados, y los dos que siguen abiertos dicen que lo están | `plan.md` |

**Lo que la segunda corrida no cambia.** Sigue sin haber alcance no pedido, sigue sin haber tareas
sin respaldo, los siete diagramas siguen compilando y siendo verdad —`flujo-general.mmd` prometía el
proveedor en la tarjeta y ahora la tarjeta lo muestra—, y ninguna regla del dominio está en riesgo.

**Lo que sigue dependiendo de una persona.** RF-41 se verificó en un iPhone 13 **emulado**. Un
emulador no es un teléfono: la última palabra es de alguien con el aparato en la mano, y hasta que
eso pase, lo que hay es una verificación buena y no una firma.

**Trazabilidad, después de la corrección: 42 Implementado · 0 Parcial · 0 Ausente.**
