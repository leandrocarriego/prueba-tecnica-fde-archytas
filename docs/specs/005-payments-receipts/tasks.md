# Pagos y recibos de recepción — Tareas

<!--
  ARTEFACTO INTERNO. Cada tarea mapea a una skill de agents/skills/ y es lo bastante
  chica como para terminarse de una sentada.
-->

**Feature:** 005-payments-receipts · **Plan:** `plan.md` · **Tareas:** 65

## Estado

**Escrito el 2026-08-31, después de la implementación.** Es la misma inversión del orden que registra
`plan.md`: la 005 se construyó junto con la 004 a la 009 en un solo changeset (rama
`feat/004-to-009-remaining-specs`) **sin que existiera este `tasks.md`**. Lo que sigue no es un plan
de trabajo por hacer y ya: es el desglose que le faltaba al plan, reconstruido contra el código que
existe y contra los quince hallazgos que el plan dejó a la vista, y usado para lo único que un
`tasks.md` tardío sirve — **decir con números qué del alcance firmado está construido y qué no**.

- ✅ **53 de 65** implementadas y verificadas por la suite. Todo lo del 2026-08-31: las dos pantallas
  que faltaban (58, 63) con sus tests (61, 64); los seis defectos que devolvían un número equivocado
  sin fallar (6, 23, 35, 38, 39, 41) con sus tests (7, 24, 34, 40); la verificación de proveedor del
  reparto (59); y la base de datos por corrida (65), que no es de esta feature y salió de intentar
  verificarla.
- ⛔ **Una frenada y escalada**: la 60, que necesita un evento nuevo del catálogo para poder cerrar el caso que abre.
- ⬜ **11 pendientes**, y no son alcance nuevo: **cada una nace de un hallazgo `H-n` de `plan.md`**
  o de un `RF` que quedó sin test. La columna *Hallazgo* de cada tabla dice cuál.
- 🔴 **Un requisito firmado sin una sola línea de implementación**: RF-43 (tarea 15). **Ya tiene
  diseño cerrado** en `plan.md` y en `contracts/` desde el 2026-08-31; lo que falta es escribirlo.
- ↗️ **Dos tareas se fueron a la 011**, la feature transversal de la cuarentena muda (17 y 18). El
  requisito que cubren —RF-08— sigue siendo alcance de **esta** spec: el trabajo cambia de carpeta,
  la promesa no.
- ✅ **Las dos historias que no tenían pantalla ya la tienen** (H-3, tareas 58 y 63): `/facturas/pagos`
  y `/facturas/incidentes`, las dos enlazadas desde la lista de facturas. Las Server Actions que
  revalidaban rutas inexistentes ahora revalidan rutas que existen.

Suite de la feature al cierre: **18 tests de integración** en
`backend/tests/integration/features/test_payments_and_receipts.py`, más 3 unitarios del parser del
estado de cuenta contra HTML fijado. **Cero tests de frontend.**

> **Dónde queda la cadena.** Con 27 tareas abiertas, la feature **no está lista para `/converge`**.
> Lo que corresponde antes es que el humano decida, hallazgo por hallazgo, qué se corrige: el código
> o el acuerdo (Artículo V). Este documento no toma esa decisión — la deja contable.

> **El módulo es compartido.** `purchases` es también de la 004 (padrón, facturas, revisión), la 006
> (calendario) y la 007 (órdenes). Ninguna tarea de acá toca esas partes, y si una parece tocarlas,
> es de la otra feature.

## Orden

Agrupadas por historia, en el orden de prioridad de la spec. Dentro de cada una:
migración → backend → frontend → tests.

> **Al terminar H1 hay algo entregable de verdad**: el dueño abre la lista de facturas y cada una
> dice si está saldada, a medias o sin tocar, con cuánto se pagó y cuánto queda, y el número coincide
> con la cuenta hecha a mano. Es exactamente el problema que P5 enuncia — *"termino sumando a mano y
> siempre me da distinto"*— y se resuelve sin ninguna de las nueve historias siguientes.

> **La tarea 1 construye tablas que son materia de H4, H7, H9 y H10.** No es un error de agrupación:
> el estado de pago de H1 se calcula sobre `core.payment`, así que la tabla tiene que existir antes
> de que H1 esté terminada. Las historias siguientes construyen encima.

### H1 — Saldada, a medias o sin tocar, de un vistazo

| # | Tarea | Skill | Rol | Cubre | Hallazgo |
|---|-------|-------|-----|-------|----------|
| ✅ 1 | Migración, parte 005 de `0011_invoices_and_suppliers`: `core.payment` con `external_id` único, `core.receipt` con índice único parcial sobre los no anulados, `core.receipt_incident` con índice único parcial sobre los abiertos, y sobre `core.invoice` las tres columnas `portal_*` más `due_on`. Los tres índices son **reglas del negocio, no optimizaciones**: un chequeo en el servicio corre una carrera consigo mismo. Los modelos entran a `app/models.py` en el mismo commit (`DB-01`). | `add_database_migration` | Developer | RF-08, RF-13, RF-35, RF-37 | — |
| ✅ 2 | `purchases`: el estado de pago **calculado y nunca guardado**, sumando los pagos `IMPUTED` — `SALDADA`, `PARCIAL`, `SIN_PAGOS`, `INCONSISTENTE`— con el monto pagado, el saldo y el porcentaje. Lo dicen los pagos, no el portal. | `add_backend_feature` | Developer | RF-01, RF-02, RF-03, RF-45 | — |
| ✅ 3 | `GET /invoices` con `payment_state`, `due_from`/`due_to` y `with_receipt`, y `GET /invoices/{id}` con el estado de pago **adentro de la factura** y no en otra pantalla. Las dos con su autorización declarada (`PY-09`). | `add_backend_feature` | Developer | RF-04, RF-05, RF-06, RF-31 | — |
| ✅ 4 | Pantallas `(private)/facturas` y `(private)/facturas/[invoiceId]`: el estado a simple vista en la lista, y pagado, saldo y porcentaje dentro de la factura. | `add_frontend_feature` | Developer | RF-01 a RF-06 | — |
| ✅ 5 | Tests de H1: una factura sin pagos que figura sin pagar, y una parcial que informa qué parte de ella está paga. | `add_tests` | Tester | RF-01, RF-02, RF-03, RF-06 | — |
| ✅ 6 | **Arreglado el 2026-08-31.** El estado se sigue **sin guardar** —eso era la decisión, y no cambió— pero ahora se filtra en la consulta, sobre la suma de lo imputado. La regla queda escrita dos veces, en `_payment_state` y en el `WHERE`, y hay un test que recorre los cuatro estados por los dos caminos para que no se separen. Lo que había antes:, y `total` no lo tiene en cuenta: la página vuelve corta y el contador dice otra cosa. Es el costo aceptado de calcular el estado en cada lectura, y hay que pagarlo en la consulta, no en la respuesta. | `debug` | Developer | RF-04 | H-7 |
| ✅ 7 | **Hecho el 2026-08-31**: una página de dos sobre nueve facturas devuelve las parciales que corresponden y `total` dice 3, no 9. Antes volvía corta y el contador contaba otra cosa. Incluye el test que fija que el SQL y el lector coinciden en los cuatro estados. Tests de los filtros: pedir sólo las parciales sobre un conjunto más grande que la página devuelve todas y el total coincide; y las facturas de un proveedor que vencen en un rango de fechas. | `add_tests` | Tester | RF-04, RF-05 | H-7 |

### H2 — Los pagos se imputan solos

| # | Tarea | Skill | Rol | Cubre | Hallazgo |
|---|-------|-------|-----|-------|----------|
| ✅ 8 | `ingestion`: `staging.payment_row` y la mitad de `parse_supplier_ledger` que lee los movimientos de tipo `Pago`, con `invoice_references_in` y la publicación de `PaymentsNormalized`. **La referencia se guarda entera y como la escribió el portal**: partir el texto acá sería decidir en el parser qué cubre un comprobante. | `add_backend_feature` | Developer | RF-07, RF-08 | — |
| ✅ 9 | La extracción corre sola: reusa `extract_supplier_ledger` de la 004 —los movimientos viajan en la **misma** pantalla que el padrón— con la frecuencia de `invoice_sync.interval_hours`. Sin endpoints JSON internos (Artículo I). | `add_integration` | Developer | RF-07 | — |
| ✅ 10 | `purchases`: `register_payments` con sus tres caminos, ninguno de ellos una adivinanza — nombra una factura que existe y se imputa; nombra una que nadie registró y queda apartado; nombra varias o ninguna y espera a una persona. El duplicado lo decide `uq_payment_external_id`, no el código. | `add_backend_feature` | Developer | RF-09, RF-11, RF-12, RF-13 | — |
| ✅ 11 | `purchases`: un comprobante que coincide en factura y monto con un pago cargado a mano **se aparta en lugar de imputarse** (`VOUCHER_LOOKS_MANUAL`). Unirlos esconde un pago; contarlos por separado infla lo pagado. | `add_backend_feature` | Developer | RF-42 | — |
| ✅ 12 | `purchases`: la suscripción a `InvoicesRegistered` del propio módulo — cuando entra la factura que un comprobante apartado nombraba, se lo imputa sin que nadie tenga que acordarse de llamar un paso. | `add_backend_feature` | Developer | RF-44 | — |
| ✅ 13 | `GET /invoices/{id}/payments` y la lista de pagos dentro de la factura, con su fecha, su monto y **de dónde vino**. | `add_backend_feature` | Developer | RF-10, RF-20 | — |
| ✅ 14 | Tests de H2: el mismo comprobante leído dos veces que se imputa una sola —contra la base, porque lo decide un índice—; el que nombra una factura inexistente y se imputa solo el día que esa factura entra; y el que nombra varias y espera a una persona. | `add_tests` | Tester | RF-07, RF-09, RF-11, RF-12, RF-13, RF-44 | — |
| ⬜ 15 | **RF-43: `POST /payments/{id}/same-as`**, con el diseño ya cerrado en `plan.md` y en `contracts/`. Recibe el id del pago manual y hace tres cosas en orden: imputa el comprobante del portal a la factura, deja el pago manual en `VOIDED` con su motivo, y registra quién lo decidió y cuándo. **Sobrevive el del portal** porque RF-23 prohíbe dejar sin efecto un pago del origen — conservar el manual habría exigido romper un requisito firmado para cumplir otro. Rechaza con `409` un par del mismo origen, y **no toca ni el monto ni la fecha**: unir no es promediar. | `add_backend_feature` | Developer | RF-43 | H-14 |
| ⬜ 16 | Tests: el comprobante de $50 que llega del portal sobre una factura que ya tenía $50 cargados a mano queda en revisión y el saldo no baja dos veces (RF-42, hoy sin test); y resuelto que eran el mismo, queda un solo pago y figura quién lo resolvió (RF-43). | `add_tests` | Tester | RF-42, RF-43 | H-14 |
| ↗️ 17 | **Retirada de esta feature el 2026-08-31, por decisión del humano.** La cuarentena muda —`PaymentRowsQuarantined` en el catálogo, su publicación en `ingestion` y el suscriptor en `triage`— **no es de la 005**: cinco normalizaciones publican su evento y sólo las dos de precios tienen suscriptor, así que 004, 007 y 009 tienen la misma brecha y arreglarla sólo acá no cambiaría nada para nadie. Va a **una feature transversal propia, la 011 — «Lo apartado se ve»**, **firmada el 2026-08-31** (`docs/specs/011-set-aside-visibility/spec.md`, 23 requisitos, sin preguntas abiertas y con sus seis diagramas). RF-02 de esa spec es exactamente esta tarea. **El gate de calidad de la 005 queda condicionado a que la 011 cierre** — el Artículo II está declarado como incumplido en el Constitution Check, sin excepción concedida. | `specify` | Solution-Designer | RF-08 · Artículo II | H-1 |
| ↗️ 18 | El test de lo anterior —una fila ilegible del estado de cuenta genera su fila en `operations.exception` y llega a una persona— **se va con la 011**, por el mismo motivo. Queda listado acá, y no borrado, porque RF-08 sigue siendo alcance firmado de **esta** spec: la 005 no está terminada mientras eso no ande, sólo que el trabajo se hace en otra carpeta. | `add_tests` | Tester | RF-08 · Artículo II | H-1 |

### H3 — Cuando los números no cierran, el sistema lo dice

| # | Tarea | Skill | Rol | Cubre | Hallazgo |
|---|-------|-------|-----|-------|----------|
| ✅ 19 | `purchases`: pagado > total es `INCONSISTENTE` —no "saldada de más"—, queda **afuera de los totales de deuda diciendo que quedó afuera**, y no figura como saldada en ningún filtro ni total. Ningún número se acomoda para que cierre. | `add_backend_feature` | Developer | RF-14, RF-16, RF-17 | — |
| ✅ 20 | `purchases`: lo que informa el portal se guarda **al lado** —`portal_payment_status`, `portal_paid`— y `_disagrees` señala la contradicción con los dos estados a la vista. No gana ninguno. Una palabra que la plataforma no conoce **no** es una contradicción. | `add_backend_feature` | Developer | RF-45, RF-46 | — |
| ✅ 21 | Pantalla: la factura señalada muestra su total y la suma de sus pagos, los dos números juntos. | `add_frontend_feature` | Developer | RF-15 | — |
| ✅ 22 | Tests de H3: la factura con más pagos que total que queda señalada y **nunca saldada**; la que queda afuera de los totales con la exclusión informada; la discrepancia con el portal dicha en voz alta; y la palabra nueva que no señala nada. | `add_tests` | Tester | RF-14, RF-16, RF-17, RF-28, RF-45, RF-46 | — |
| ✅ 23 | **Arreglado el 2026-08-31.** `warningFor` pasó a ser `warningsFor` y devuelve todos: una factura inconsistente que además contradice al portal muestra las dos cosas. Los cuatro señalamientos son independientes y no hay motivo para que uno tape a otro. Lo que había antes:: una factura inconsistente que además discrepa con el portal no muestra la discrepancia. Los dos señalamientos son independientes y tienen que poder verse juntos. | `debug` | Developer | RF-46 | H-13 |
| ✅ 24 | **Hecho el 2026-08-31**: una factura de $10.000 con $13.000 pagados que el portal informa «Impaga» viaja con `is_inconsistent` **y** `payment_state_disagrees`, y con los dos números. Test: la factura señalada expone su total y la suma de sus pagos, y una que es inconsistente **y** discrepa muestra las dos cosas. | `add_tests` | Tester | RF-15, RF-46 | H-13 |

### H4 — Registrar un pago a mano

| # | Tarea | Skill | Rol | Cubre | Hallazgo |
|---|-------|-------|-----|-------|----------|
| ✅ 25 | `POST /invoices/{id}/payments`: el pago a mano con su monto y su fecha, quién lo cargó y cuándo, origen `MANUAL`, y **el aviso de RF-21 como un `409` con el saldo**, que se contesta reenviando con `confirm_over_balance`. Un aviso que no hay que contestar es un aviso que nadie lee. | `add_backend_feature` | Developer | RF-18, RF-19, RF-20, RF-21 | — |
| ✅ 26 | `DELETE /payments/{id}`: un pago cargado a mano se deja sin efecto y deja de contar; **uno traído del portal no se borra**, y se rechaza con su motivo. | `add_backend_feature` | Developer | RF-22, RF-23 | — |
| ✅ 27 | Pantalla: el formulario del pago a mano, el aviso de saldo antes de confirmar, la distinción de origen en la lista y la opción de deshacer que **no aparece** para un pago del portal. | `add_frontend_feature` | Developer | RF-18, RF-20, RF-21, RF-22, RF-23 | — |
| ✅ 28 | Tests de H4: la advertencia antes de registrar más que el saldo; el pago del portal que no se deshace —y es un `409`, no un `403`—; y el cargado a mano que se deshace y deja de contar. | `add_tests` | Tester | RF-18, RF-20, RF-21, RF-22, RF-23 | — |
| ⬜ 29 | **Ninguna pantalla de 005 dice quién hizo cada cosa**: los schemas exponen `*_user_id` y ningún componente lo resuelve a un nombre. Y ninguna acción de la feature publica `ManualChangeRecorded`, así que tampoco aparecen en `/historial`. Alcanza a los cuatro requisitos que piden un nombre —el pago cargado, el recibo emitido, el reparto y el incidente cerrado—. | `add_feature` | Developer | RF-19, RF-36, RF-56, RF-58 | H-9 |
| ⬜ 30 | Test: un pago cargado a mano figura con el nombre de quien lo cargó y la fecha, y el cambio aparece en la bitácora. | `add_tests` | Tester | RF-19 | H-9 |

### H5 — Cuánto le debo a cada proveedor, y hace cuánto

| # | Tarea | Skill | Rol | Cubre | Hallazgo |
|---|-------|-------|-----|-------|----------|
| ✅ 31 | `purchases`: **el vencimiento sale de `issued_on + payment_term_days` y de nada más** —la columna del portal es sólo respaldo mientras no haya plazo—, y sobre esa fecha se calculan la deuda, el total pagado, la antigüedad por tramos y el atraso promedio, que incluye las impagas ya vencidas: dejarlas afuera bajaría el número justo cuando peor se está cumpliendo. | `add_backend_feature` | Developer | RF-24, RF-25, RF-26, RF-27 | — |
| ✅ 32 | `GET /suppliers/{id}/totals`: la deuda con **cuántas facturas quedaron excluidas** por estar en revisión o señaladas. Ningún total miente por omisión. | `add_backend_feature` | Developer | RF-28 | — |
| ✅ 33 | Pantalla `(private)/proveedores/[supplierId]`: deuda, pagado, los tramos de 30, 60 y 90 días, el atraso promedio y la frase de cuántas quedaron afuera. | `add_frontend_feature` | Developer | RF-24, RF-25, RF-27, RF-28 | — |
| ✅ 34 | **Completa el 2026-08-31.** La primera mitad: RF-26 tiene sus dos tests —el plazo del proveedor manda sobre la fecha del documento, y el vencimiento se recalcula cuando el plazo aparece—. **Los tramos de antigüedad y el atraso promedio ya están**: cuatro facturas, una por tramo, con cada peso en un solo tramo; y el atraso promedio que **cuenta las impagas vencidas** — una pagada diez días tarde y una impaga vencida hace veinte dan quince, no diez, que es el número que baja justo cuando peor se está cumpliendo. Tests de H5: una factura del 1 de marzo de un proveedor con plazo de 45 días **vence el 15 de abril aunque el documento traiga otra fecha** (RF-26); los cuatro tramos de antigüedad contados desde el vencimiento; y el atraso promedio contra la cuenta hecha a mano, con una pagada tarde y una impaga vencida. Fijar las fechas con `today_here()` y no con `date.today()` de UTC. | `add_tests` | Tester | RF-24, RF-25, RF-26, RF-27 | — |
| ✅ 35 | **Arreglado el 2026-08-31.** `_refresh_due_dates` rehace la cuenta cuando el padrón trae el plazo y cuando alguien lo corrige a mano, y **no toca una fecha que una persona reprogramó** — la misma regla que ya siguen el padrón y el calendario. Importa más de lo que parece: de esa fecha cuelgan el plazo del recibo, los tramos de antigüedad y el atraso promedio, así que una fecha mal calculada equivoca tres números a la vez. Lo que había antes:: cae a la columna del portal y se queda ahí: ni cuando el padrón publica el plazo, ni cuando alguien lo corrige a mano. Sólo se recalcula al resolver una factura apartada. Con el vencimiento equivocado se equivocan la antigüedad, el atraso y el plazo del recibo. | `debug` | Developer | RF-26 | H-10 |

### H6 — Qué facturas ya tienen su recibo y cuáles no

| # | Tarea | Skill | Rol | Cubre | Hallazgo |
|---|-------|-------|-----|-------|----------|
| ✅ 36 | `purchases`: `receipt_issued` calculado desde `core.receipt` y el filtro `with_receipt` sobre la lista. | `add_backend_feature` | Developer | RF-29, RF-31 | — |
| ✅ 37 | Pantalla: la marca de recibo en cada factura, el filtro de las que no lo tienen y el contador de cuántas faltan. | `add_frontend_feature` | Developer | RF-29, RF-31, RF-32 | — |
| ✅ 38 | **Arreglado el 2026-08-31.** «Tiene recibo» estaba repetido en cuatro consultas que miraban sólo `core.receipt`; ahora es **un solo predicado** que usan el render, el filtro, los incidentes y el aviso. Con una decisión que hubo que tomar y no estaba escrita: **anular un recibo le gana a lo que diga el portal**, porque si no, mi propio arreglo rompía RF-50. Lo que había antes:: la pantalla, el filtro y el incidente miran sólo `core.receipt`. Una factura cuyo recibo ya existía en el portal figura como «Falta», admite que se le emita un segundo recibo y genera un incidente que no existe. El dato ya está guardado: falta leerlo. | `debug` | Developer | RF-29, RF-30, RF-31, RF-37 | H-6 |
| ✅ 39 | **Arreglado el 2026-08-31.** El contador sale de un pedido propio con `with_receipt=false&limit=1` y usa su `total`: cuántas facturas están sin recibo es una pregunta sobre el sistema, no sobre la página. Lo que había antes: (límite 200) y lo dice como «en esta vista». RF-32 pide cuántas facturas están sin recibo, no cuántas se ven. | `debug` | Developer | RF-32 | H-12 |
| ✅ 40 | **Hecho el 2026-08-31**: una factura vencida cuyo recibo ya existía en el portal figura con recibo, **sin número** —ese número no es nuestro—, no abre incidente, no admite un segundo y cae del lado correcto de los dos filtros. Más el test de que anular el nuestro habilita emitir otro aunque el portal insista. Tests de H6: un recibo que ya existía en el portal aparece sin que nadie lo cargue y **no admite un segundo**; el filtro devuelve las que no lo tienen; y el contador es el del sistema, no el de la página. | `add_tests` | Tester | RF-29, RF-30, RF-31, RF-32 | H-6, H-12 |
| ✅ 41 | **Arreglado el 2026-08-31**: se completa desde `core.receipt` en vez de borrarse. Una factura cuyo recibo lo emitió el portal se queda sin número, y eso es exacto: ese número no es nuestro y no lo conocemos. Lo que había antes: `InvoiceRead.receipt_number` estaba declarado en el schema, **nunca se asigna** y no hay columna que lo respalde — viaja siempre `null` y está espejado en el tipo generado del frontend. Completarlo desde `core.receipt` o borrarlo del schema; las dos cosas son mejores que un campo que miente. | `debug` | Developer | — (sin RF) | H-15 |

### H7 — Emitir el recibo, hasta la fecha y no después

| # | Tarea | Skill | Rol | Cubre | Hallazgo |
|---|-------|-------|-----|-------|----------|
| ✅ 42 | `POST /invoices/{id}/receipt`: emite con **número propio y correlativo** (`RC-000001`), registra quién y cuándo, **se niega pasada la fecha de vencimiento vigente** explicando el motivo, y se niega si ya hay uno en pie —lo decide el índice único parcial, no un `if`—. | `add_backend_feature` | Developer | RF-33, RF-34, RF-35, RF-36, RF-48 | — |
| ✅ 43 | El documento del recibo, en texto plano y en español, con la factura y el proveedor, y `GET /invoices/{id}/receipt` para recuperarlo. Sin librería de PDF: la presentación la resuelve el navegador y `IX` queda en cero dependencias nuevas. | `add_backend_feature` | Developer | RF-47 | — |
| ✅ 44 | `DELETE /receipts/{id}`: anula registrando quién y cuándo; si la factura todavía no venció se le puede emitir otro, y si ya venció **queda señalada como incidente**. | `add_backend_feature` | Developer | RF-49, RF-50, RF-51 | — |
| ✅ 45 | `purchases.watch_due_dates` abre un incidente por cada factura vencida sin recibo, idempotente **por el índice único parcial** sobre los abiertos. | `add_celery_task` | Developer | RF-37 | — |
| ✅ 46 | Pantalla: emitir el recibo desde la factura, verlo con su número, y anularlo. | `add_frontend_feature` | Developer | RF-33, RF-34, RF-35, RF-49, RF-50 | — |
| ✅ 47 | Tests de H7: el número correlativo; la negativa después del vencimiento; la negativa a emitir un segundo; anular y volver a emitir mientras no venció; y la vencida sin recibo que se vuelve incidente —probada dos veces, que es lo único que verifica la idempotencia de verdad—. | `add_tests` | Tester | RF-33, RF-34, RF-35, RF-37, RF-48, RF-49, RF-50 | — |
| ⬜ 48 | **El recibo no se descarga**: el documento se muestra en un `<pre>` y no hay enlace ni botón. RF-47 pide poder mandárselo al proveedor. | `add_frontend_feature` | Developer | RF-47 | H-8 |
| ⬜ 49 | Tests: anular el recibo de una factura **ya vencida** la deja señalada como incidente (RF-51); el recibo emitido figura con quién y cuándo (RF-36); y el documento se descarga y dice de qué factura y de qué proveedor es (RF-47). | `add_tests` | Tester | RF-36, RF-47, RF-51 | H-8 |

### H8 — Que avise antes de que se pase la fecha

| # | Tarea | Skill | Rol | Cubre | Hallazgo |
|---|-------|-------|-----|-------|----------|
| ✅ 50 | `purchases.watch_due_dates` publica `InvoiceDueSoon` por cada factura **sin recibo** que vence dentro de `receipt.notice_days`. Que una factura **con** recibo no avise no es un `if` en `notifications`: es el filtro de `invoices_due_soon`. El aviso es sobre el recibo, no sobre la plata. | `add_celery_task` | Developer | RF-38, RF-40 | — |
| ✅ 51 | `notifications`: la suscripción a `InvoiceDueSoon` y el texto del aviso por WhatsApp. Ninguna tabla nueva y ninguna lectura de `purchases`: se entera por el evento (Artículo IV). | `add_backend_feature` | Developer | RF-38 | — |
| ✅ 52 | `purchases`: `receipt.notice_days` mantenido en la **proyección propia** `core.purchase_setting` por `BusinessParameterChanged`, con tres días mientras el dueño no configure otro valor. | `add_backend_feature` | Developer | RF-41, RF-52 | — |
| ⬜ 53 | **El aviso se repite todos los días** mientras la factura siga sin recibo: `invoices_due_soon` devuelve todo lo que vence en la ventana y la task corre cada 24 h, sin registro de qué ya se avisó. Un aviso que llega todos los días es un aviso que nadie lee. Falta el registro de «esto ya se avisó», del lado de `notifications`. | `debug` | Developer | RF-39 | H-4 |
| ⬜ 54 | **El aviso va a un solo rol** —compras, y al dueño sólo si nadie tiene el rol compras—. RF-38 pide compras **y** el dueño. | `debug` | Developer | RF-38 | H-5 |
| ⬜ 55 | Tests de H8: con la anticipación en tres días el aviso llega tres días antes **a compras y al dueño**; una misma factura genera uno solo; emitido el recibo deja de llegar; sin tocar ningún parámetro sale con tres días; y cambiado por el dueño, el próximo sale con el valor nuevo. | `add_tests` | Tester | RF-38, RF-39, RF-40, RF-41, RF-52 | H-4, H-5 |

### H9 — Un pago que cubre varias facturas

| # | Tarea | Skill | Rol | Cubre | Hallazgo |
|---|-------|-------|-----|-------|----------|
| ✅ 56 | `GET /payments/pending` y `POST /payments/{id}/split`: hasta que el reparto no cierra **exacto** contra el monto del comprobante ningún saldo se mueve; confirmado, el comprobante queda `VOIDED` con quién lo repartió y cuándo, y valen sus partes. Nada se elimina. | `add_backend_feature` | Developer | RF-53, RF-54, RF-55, RF-56 | — |
| ✅ 57 | Tests del reparto: el que suma $280 sobre $300 no se puede confirmar, y el comprobante que nombra varias facturas espera a una persona en lugar de repartirse solo. | `add_tests` | Tester | RF-54, RF-55 | — |
| ✅ 58 | **Construida el 2026-08-31.** La pantalla de comprobantes por repartir, en `/facturas/pagos`. Trae las facturas candidatas **por proveedor** —el reparto es entre facturas de uno solo, que es el supuesto firmado—, muestra en vivo cuánto se repartió y cuánto falta, y **no habilita confirmar hasta que cierra exacto** (RF-55, que el backend vuelve a verificar). Sin sugerencia por monto ni reparto automático: lo decide una persona. Lo que había antes: El backend está entero y la Server Action `splitPayment` **ya está escrita**, revalidando `/facturas/pagos`, una ruta que nadie construyó: es la mitad de una pantalla. Sin ella, un comprobante apartado es invisible para una persona — y el plan mide que **la mayoría** van a quedar apartados, porque el portal no dice qué factura cubren. | `add_frontend_feature` | Developer | RF-11, RF-12, RF-53, RF-54, RF-55 | H-3 |
| ✅ 59 | **Arreglado el 2026-08-31.** El reparto rechaza dos proveedores distintos y también el caso más silencioso: un solo proveedor, pero el que no pagó. No es una regla de prolijidad — plata atribuida al proveedor equivocado equivoca a los dos a la vez, y de esos números salen la antigüedad y el atraso de ambos. Lo que había antes:, ni que sean del proveedor del comprobante. El supuesto firmado dice que un comprobante que cruza dos proveedores queda apartado y se pregunta. | `debug` | Developer | RF-53 | H-11 |
| ⛔ 60 | **Frenada el 2026-08-31 y escalada al `Backend-Architect`.** Abrir el caso es de una línea —`triage` ya suscribe seis eventos y `open_unreadable_invoice_rows` es el molde exacto—, pero **no hay forma de cerrarlo**: cuando el comprobante se reparte o se imputa, `purchases` no publica nada que `triage` pueda escuchar, y cerrarlo a mano dejaría dos lugares diciendo cosas distintas del mismo comprobante. Un caso que no se puede cerrar convierte `/revisión` en una cola que sólo crece, que es lo contrario de lo que esa pantalla promete. **Lo que falta decidir**: un evento nuevo del catálogo (`PaymentResolved`, con el `payment_id` y qué pasó) publicado al imputar y al repartir. Es `GEN-08` y no lo decide un Developer. **Mientras tanto la invisibilidad de H-2 ya está resuelta** por la tarea 58: el comprobante apartado se ve, se lee su motivo y se reparte. | `add_backend_feature` | Developer | RF-11, RF-12, RF-54 | H-2 |
| ✅ 61 | **Completa el 2026-08-31.** La primera mitad: `test_a_split_moves_each_balance_by_its_own_part` reparte $30.000 en partes **desiguales** entre tres facturas —10/5/15, a propósito: un reparto en partes iguales pasaría igual si el servicio dividiera por la cantidad, que es justo lo que la spec prohíbe— y verifica cada saldo y quién repartió (RF-53, RF-56). **La otra mitad ya está**: dos tests fijan que un comprobante no se reparte entre facturas de dos proveedores ni se imputa a las de otro, y los dos **fallan sin la tarea 59**, que se construyó el mismo día. | `add_tests` | Tester | RF-53, RF-56 | H-11 |

### H10 — Cerrar lo que se pasó de fecha

| # | Tarea | Skill | Rol | Cubre | Hallazgo |
|---|-------|-------|-----|-------|----------|
| ✅ 62 | `GET /receipt-incidents` y `POST /receipt-incidents/{id}/close`: se cierra explicando qué se hizo, con quién y cuándo; deja de contarse entre los pendientes y **se sigue pudiendo consultar**. No se borra ni se apaga en silencio. | `add_backend_feature` | Developer | RF-57, RF-58, RF-59 | — |
| ✅ 63 | **Construida el 2026-08-31.** La pantalla de incidentes, en `/facturas/incidentes`, con los abiertos y los cerrados por separado, el motivo a la vista y el botón que espera a que haya explicación —un incidente que se cierra sin motivo es un incidente que se apaga—. Dice explícitamente que cerrar no habilita emitir el recibo. Lo que había antes: Igual que la de repartos: la Server Action `closeIncident` está escrita y revalida `/facturas/incidentes`, que nadie construyó. Es la historia entera de H10 sin superficie, y también la única forma de ver las 17 facturas vencidas sin recibo que midió el relevamiento. | `add_frontend_feature` | Developer | RF-37, RF-57, RF-58, RF-59 | H-3 |
| ✅ 64 | **Hecha el 2026-08-31.** Cerrar y seguir consultable ya estaba cubierto; lo que faltaba y ahora está fijado es `test_closing_an_incident_does_not_reopen_the_receipt`: el motivo queda guardado y **la emisión sigue negada después de cerrar**. Sin ese test, la forma más natural de «resolver» un incidente sería emitir el recibo que faltaba, y RF-34 dejaría de valer por la puerta de atrás. | `add_tests` | Tester | RF-57, RF-58, RF-59 | — |

### Fuera de la feature — la suite

| # | Tarea | Skill | Rol | Cubre | Hallazgo |
|---|-------|-------|-----|-------|----------|
| ✅ 65 | **Una base de datos por corrida** (`tests/conftest.py`), **opt-out con `CORDILLERA_TEST_DB_PER_RUN=0`** para quien quiera una base fija que después va a abrir a mirar. No cubre ningún requisito y no es de esta feature: está acá porque salió de intentar verificarla. La suite reconstruye su esquema en cada corrida —`drop_all` y `create_all`, que toman `AccessExclusiveLock` sobre cada tabla—, así que **dos corridas sobre una misma base no se degradan: se rompen**. La que arranca le borra las tablas a la que ya está andando, y lo que sale es un deadlock en cualquier test que estuviera leyendo, o un archivo entero de errores en el setup. Parece una suite inestable y no lo es: cada test pasa solo. Ahora el nombre de la base lleva el pid y se borra al terminar. Es **opt-out y no opt-in** a propósito: olvidarse de encenderlo cuesta una corrida corrupta que parece un test flaky, y olvidarse de apagarlo cuesta volver a crear una base. | `debug` | Tester | — (infraestructura) | — |

## Cobertura de requisitos

<!--
  Todo requisito funcional de la spec tiene al menos una tarea que lo construye y
  al menos un test que lo verifica. Un RF sin fila acá es alcance firmado que nadie
  se comprometió a hacer — y es exactamente lo que /converge va a encontrar.
-->

Los 59 requisitos firmados. **Una tarea o un test en ⬜ significa que ese requisito todavía no está
cubierto**, aunque tenga otras tareas en ✅.

| Requisito | Tareas | Test |
|-----------|--------|------|
| RF-01 | 2, 4 | 5 |
| RF-02 | 2, 4 | 5 |
| RF-03 | 2, 4 | 5 |
| RF-04 | 3, 4, 6 | 7 |
| RF-05 | 3, 4 | 7 |
| RF-06 | 3, 4 | 5 |
| RF-07 | 8, 9 | 14 |
| RF-08 | 1, 8, ↗️17 (011) | ↗️18 (011) |
| RF-09 | 10 | 14 |
| RF-10 | 13 | 14 |
| RF-11 | 10, 58, ⛔60 | 14 |
| RF-12 | 10, 58, ⛔60 | 14 |
| RF-13 | 1, 10 | 14 |
| RF-14 | 19 | 22 |
| RF-15 | 21 | 24 |
| RF-16 | 19 | 22 |
| RF-17 | 19 | 22 |
| RF-18 | 25, 27 | 28 |
| RF-19 | 25, ⬜29 | ⬜30 |
| RF-20 | 13, 25, 27 | 28 |
| RF-21 | 25, 27 | 28 |
| RF-22 | 26, 27 | 28 |
| RF-23 | 26, 27 | 28 |
| RF-24 | 31, 32, 33 | 34 |
| RF-25 | 31, 33 | 34 |
| RF-26 | 31, 35 | 34 |
| RF-27 | 31, 33 | 34 |
| RF-28 | 32, 33 | 22 |
| RF-29 | 36, 37, 38 | 40 |
| RF-30 | 38 | 40 |
| RF-31 | 3, 36, 37, 38 | 40 |
| RF-32 | 37, 39 | ⬜40 (el contador no tiene test) |
| RF-33 | 42, 46 | 47 |
| RF-34 | 42, 46 | 47 |
| RF-35 | 1, 42, 46 | 47 |
| RF-36 | 42, ⬜29 | ⬜49 |
| RF-37 | 45, 63, 38 | 47, 40 |
| RF-38 | 50, 51, ⬜54 | ⬜55 |
| RF-39 | ⬜53 | ⬜55 |
| RF-40 | 50 | ⬜55 |
| RF-41 | 52 | ⬜55 |
| RF-42 | 11 | ⬜16 |
| RF-43 | ⬜15 (diseñada) | ⬜16 |
| RF-44 | 12 | 14 |
| RF-45 | 2, 20 | 22 |
| RF-46 | 20, 23 | 22, 24 |
| RF-47 | 43, ⬜48 | ⬜49 |
| RF-48 | 42 | 47 |
| RF-49 | 44, 46 | 47 |
| RF-50 | 44, 46 | 47, 40 |
| RF-51 | 44 | ⬜49 |
| RF-52 | 52 | ⬜55 |
| RF-53 | 56, 58, 59 | 61 |
| RF-54 | 56, 58, ⛔60 | 57 |
| RF-55 | 56, 58 | 57 |
| RF-56 | 56, ⬜29 | 61 |
| RF-57 | 62, 63 | 64 |
| RF-58 | 62, ⬜29 | 64 |
| RF-59 | 62, 63 | 64 |

**Qué dice la tabla, leída de una** (2026-08-31, al cierre del día): **41 de los 59 requisitos**
están construidos y verificados —quince más que al empezar—; **18 tienen algo pendiente**, y de esos
RF-43 sigue sin una línea de código, aunque ya con diseño y contrato. Lo que se cerró hoy: las dos
historias que no tenían pantalla (RF-11, RF-12, RF-53 a RF-59), el recibo que el portal ya había
emitido (RF-29 a RF-31, RF-37), el filtro que paginaba mal (RF-04, RF-05), el vencimiento que no se
recalculaba (RF-26) y los dos señalamientos que se tapaban entre sí (RF-15, RF-46). La tarea 41 (el campo muerto) es la
única sin `RF`: no cubre alcance, es higiene.

## Antes de la primera tarea

Una pregunta que ninguna tarea de esta lista contesta, porque no la contesta el equipo:

> **Los comprobantes de `/estado-cuenta` no dicen a qué factura corresponden.** Un movimiento de tipo
> `Pago` trae su propio número de recibo, no el de la factura, y hay un test contra HTML fijado que lo
> afirma. La consecuencia es que **la mayoría de los comprobantes van a quedar esperando a que una
> persona diga qué cubren**, que es el Artículo II funcionando pero también un costo operativo real.
>
> ¿El portal expone en algún lado esa relación, o el reparto a mano es aceptable como parte del
> trabajo de compras?

Si la respuesta es la segunda, **la tarea 58 —la pantalla de repartos— sube a la primera posición de
todo lo pendiente**, porque sin ella el trabajo que la plataforma le deja a compras no tiene dónde
hacerse.

## Decisiones tomadas el 2026-08-31

Las cuatro salieron de la corrida de `/analyze` (`checklists/analyze.md`) y las tomó el humano, salvo
la primera, que es de arquitectura y no volvió al cliente:

| Decisión | Quién | Consecuencia acá |
|---|---|---|
| **En RF-43 sobrevive el pago del portal**, por `POST /payments/{id}/same-as` | Backend-Architect | La tarea 15 pasa de enunciado a tarea |
| **No se aprueba excepción al Artículo II**: es trabajo bloqueante | El humano | La 005 **no pasa al gate** hasta que la cuarentena llegue a una persona |
| **La cuarentena muda vive en una feature transversal (011)** | El humano | Las tareas 17 y 18 se retiran de acá y esperan la spec de la 011 |
| El aviso a compras **y** al dueño, y el aviso que no se repite, siguen siendo de esta feature | — | Tareas 53 y 54, sin cambios |
| **La 011 se especifica después** de bajar las tareas pendientes, no ahora | El humano | La 005 **no se entrega antes que la 011**: su gate depende de ella. Postergarla posterga el cierre de esta feature |
