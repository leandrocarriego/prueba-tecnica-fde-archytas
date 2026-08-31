# Pagos y recibos de recepción — Plan técnico

<!--
  ARTEFACTO INTERNO. Acá van las decisiones técnicas que spec.md no puede llevar.
  No se exporta al cliente.
-->

**Feature:** 005-payments-receipts · **Spec aprobada el:** 2026-08-29 · **Fecha:** 2026-08-31
**Rol:** `Backend-Architect` (el grueso) · `Frontend-Architect` (las pantallas)

> **Este plan se escribió después de la implementación, no antes.** El humano pidió implementar las
> seis specs pendientes en una sola pasada y lo confirmó como decisión suya. El orden normal es
> `/plan` → `/tasks` → `/implement`; acá el plan **documenta lo que se construyó**, verificado
> archivo por archivo, para que sirva al Developer, al Tester y al Code-Reviewer que vienen después
> y para que `/converge` pueda contrastar el código contra lo firmado. Está anotado así porque un
> documento que finge haber sido escrito antes es peor que uno que dice cuándo se escribió.
>
> Todo lo que **no cierra** entre el código y la spec firmada está en una sección propia
> —*Lo que no coincide con la spec firmada*— y no disuelto en el cuerpo.

> **Este plan cubre sólo la parte 005 del módulo `purchases`.** El módulo es compartido con la
> **004** (padrón, facturas, revisión, grafías, archivo de la factura), la **006** (calendario de
> vencimientos) y la **007** (órdenes de compra). Cada sección de acá dice explícitamente qué es de
> esta feature y qué no: un plan que se adjudica el módulo entero le miente al que venga después.

---

## Constitution Check

| Artículo | Cumple | Cómo |
|---|---|---|
| I — El origen es ajeno y de sólo lectura | Sí | Los comprobantes salen de `/estado-cuenta`, leído con Playwright expandiendo las filas a click (`portal/client.py:253`). Ninguna escritura contra SIGProv, ningún endpoint JSON interno, ningún `httpx` en `portal/` |
| II — Nada se descarta | **No cumple** | Lo que se cumple: un comprobante que no dice a qué factura corresponde **no se reparte solo** — queda `PENDING`, contado y visible por API (`purchases/service.py:1161`), y una factura con más pagos que total no se declara saldada (`purchases/service.py:809`). Lo que **falta**: una fila de `staging.payment_row` en cuarentena no genera ninguna fila en `operations.exception` —no existe un evento `PaymentRowsQuarantined` en el catálogo, y cinco de las normalizaciones del pipeline sí publican el suyo: `ingestion/service.py:201` (precios), `:266` (historial), `:426` (facturas), `:633` (órdenes), `:760` (ventas)— y `PaymentsNeedingReview` se publica sin suscriptor, así que un comprobante apartado tampoco abre un caso de `triage`. **La brecha es más ancha que esta feature**: de esos cinco eventos, `triage/handlers.py` sólo suscribe los dos de precios (`:34`, `:92`), así que las cuarentenas de facturas, órdenes y ventas tampoco llegan a `operations.exception`. Ver *Lo que no coincide* (H-1, H-2) |
| III — Flujo unidireccional, `raw` inmutable | Sí | `raw.portal_document` guarda la pantalla verbatim con su hash único (`portal/models.py:37`); los pagos se tipan en `staging.payment_row` (`ingestion/models.py:274`) y recién ahí llegan a `core.payment`. Esta feature no escribe ninguna columna de `raw` |
| IV — Las fronteras entre módulos son reales | Sí | Todo el dominio vive en `purchases`, que ya es dueño de la factura. `notifications` se entera por `InvoiceDueSoon` y no lee ninguna tabla de `purchases`; `purchases` lee `receipt.notice_days` de su **propia** proyección `core.purchase_setting`, alimentada por `BusinessParameterChanged`. El único import cruzado es `identity.dependencies` en `routes.py:22`, que es la excepción fijada por nombre de archivo en el test |
| V — Spec primero, y con firma | Sí, con reserva | `spec.md` está en `Aprobado`, firmada por Leandro Carriego (FDE) el 2026-08-29. La reserva es de proceso y no de alcance: el plan se escribió después de construir (ver la nota de arriba) |
| VI — Lo que no está tipado y testeado no está terminado | Sí, en el backend | 18 tests de integración en `backend/tests/integration/features/test_payments_and_receipts.py` y 3 unitarios del parser del estado de cuenta en `backend/tests/unit/ingestion/test_section_parsers.py:124-141`, contra HTML fijado (`tests/fixtures/portal/suppliers-ledger-page-2026-08-29.html`). El frontend de esta feature no tiene tests, y **dos historias no tienen pantalla** (ver H-3) |
| VII — Las credenciales de terceros viven sólo en el entorno | Sí | Esta feature no toca credenciales: reusa el cliente de `portal`, que las lee de `Settings` |
| VIII — Un idioma para cada audiencia | Sí | Código, nombres y docstrings en inglés; los motivos que lee una persona en español (`purchases/service.py:120-143`), las pantallas en español, este documento en español |
| IX — Las dependencias entran por la puerta | Sí | Cero dependencias nuevas. El documento del recibo es texto plano armado a mano justamente para no meter una librería de PDF (`purchases/service.py:1388`) |

**Excepciones solicitadas:** ninguna, y **ninguna concedida**.

> **El Artículo II no se cumple, y la decisión del humano fue no aprobar ninguna excepción**
> (2026-08-31, al cerrar los hallazgos de `/analyze`). La cuarentena muda de `staging.payment_row`
> es **trabajo bloqueante**: la feature **no pasa al gate de calidad** hasta que una fila que no se
> pudo tipar llegue a una persona. Está desglosado en las tareas 17, 18 y 60 de `tasks.md`.
>
> Un plan que no pasa el Constitution Check no avanza, y este no lo pasa. Queda escrito acá y no en
> una nota al pie porque es la diferencia entre una deuda declarada y una deuda escondida: el
> Code-Reviewer tiene que encontrar esta línea antes de mirar una sola función.
>
> **Dónde se cierra.** La brecha no es de esta feature —cinco normalizaciones publican su evento de
> cuarentena y sólo las dos de precios tienen suscriptor, así que 004, 007 y 009 tienen la misma—.
> El humano decidió, el mismo día, que el trabajo vive en **una feature transversal propia (011)**,
> que todavía no tiene spec. Para la 005 eso significa: la tarea 17 **se retira de este alcance** y
> el gate de esta feature queda condicionado a que la 011 cierre. Ver *Lo que no coincide* → H-1.

---

## Enfoque

Cuatro decisiones sostienen la feature, y las cuatro salen de la spec firmada y no del gusto.

**El estado de pago se calcula, nunca se guarda.** Sale de sumar los pagos en estado `IMPUTED`
(`repository.py:443`, `service.py:809`) y no de lo que informa el portal (RF-45). Guardarlo sería
una segunda respuesta a una pregunta que los pagos ya contestan, y las dos se separarían la primera
vez que alguien dejara un pago sin efecto. Lo que dice el portal se guarda **al lado**, en
`invoice.portal_payment_status` y `invoice.portal_paid`, y cuando los dos no coinciden la factura lo
dice con los dos datos a la vista (`service.py:823`, RF-46): no gana ninguno. Cuatro estados y no
tres: `SALDADA`, `PARCIAL`, `SIN_PAGOS` e `INCONSISTENTE`, porque pagado > total no es "saldada de
más", es un número que no cierra y que queda afuera de los totales (RF-14 a RF-17).

**El vencimiento sale del plazo pactado con el proveedor y de nada más** (RF-26):
`issued_on + payment_term_days` (`service.py:596`). No de la columna *Vencimiento* que publica la
tabla del portal, que sólo se usa como respaldo mientras el plazo del proveedor no se conoce —una
fila del padrón que el portal no expandió—. Cuando una factura apartada recibe su proveedor, el
vencimiento se recalcula (`service.py:1007`). La 006 puede después mover esa fecha en el calendario, y
lo que manda para emitir el recibo es la **vigente** (`invoice.due_on`): esa es la frontera entre las
dos features y está descrita en el plan de la 006.

**Un comprobante no se reparte solo, y dos pagos parecidos no se unen solos.** Tres caminos, ninguno
de ellos una adivinanza (`service.py:1176`): el comprobante nombra una factura que existe y se imputa
(RF-09); nombra una que nadie registró y queda apartado hasta que esa factura entre, momento en el
que se imputa solo (RF-11, RF-44, `handlers.py:81`); o nombra varias —o ninguna— y espera a que una
persona reparta (RF-12, RF-53). Y si el comprobante coincide en factura y monto con un pago cargado a
mano, se aparta en lugar de imputarse (RF-42, `service.py:1136`): unirlos por cuenta propia esconde un
pago y contarlos por separado infla lo pagado.

**Cuando los dos pagos son el mismo, sobrevive el del portal.** Es la decisión que faltaba para
RF-43 y se tomó el 2026-08-31; no requirió volver al cliente porque **sólo hay una salida que no
rompe una regla ya firmada**. Un comprobante apartado por `VOUCHER_LOOKS_MANUAL` y el pago cargado a
mano que se le parece se resuelven con una ruta nueva, `POST /payments/{payment_id}/same-as`, que
recibe el id del otro pago y hace exactamente tres cosas: **imputa el comprobante del portal**, deja
el pago manual en `VOIDED` con su motivo, y registra quién lo decidió y cuándo.

El orden importa y no es arbitrario: **RF-23 prohíbe dejar sin efecto un pago traído del portal**, así
que conservar el manual habría exigido romper un requisito firmado para cumplir otro. Conservar el del
portal no rompe nada — dejar sin efecto un pago cargado a mano es justamente lo que RF-22 permite— y
además deja el registro del lado del dato que el origen puede volver a mandar: si mañana el mismo
comprobante llega otra vez, `uq_payment_external_id` lo reconoce, cosa que no pasaría si el
sobreviviente fuera el manual, que no tiene `external_id`.

Dos consecuencias que hay que sostener al implementar: la ruta **no** acepta un par donde los dos
pagos sean del mismo origen —dos manuales no son este caso, y dos del portal los resuelve el índice—,
y el pago que se conserva **no cambia de monto ni de fecha**: unir no es promediar.

**Tres reglas del negocio las decide la base y no el código**, con índices únicos parciales
(`models.py:358`, `models.py:401`, `models.py:305`): un recibo vigente por factura, un incidente
abierto por factura, y un comprobante del portal imputado una sola vez. Un chequeo en el servicio
puede correr una carrera consigo mismo; un índice no.

### Lo que la implementación encontró sobre el origen

> **Los comprobantes de `/estado-cuenta` no dicen a qué factura corresponden.** Un movimiento de
> tipo `Pago` trae como referencia **su propio número de recibo** (`REC-1084`), no el de la factura
> (`F-8291`). El parser lo deja escrito (`ingestion/parsers.py:682-684`) y hay un test que lo
> afirma contra el HTML fijado:
> `tests/unit/ingestion/test_section_parsers.py:132` —
> `test_a_voucher_that_names_its_own_receipt_names_no_invoice`.

La H2 de la spec asume que el comprobante indica la factura. Con los datos medidos eso no pasa, y la
consecuencia es concreta: **la mayoría de los comprobantes van a quedar esperando a que una persona
diga qué cubren** (RF-53). Es el Artículo II funcionando —la alternativa sería que la plataforma
decidiera adónde fue la plata de alguien— pero es un costo operativo real y es una **pregunta para el
cliente**, no una decisión del equipo:

- ¿el portal expone en algún lado la relación comprobante → factura que la pantalla no muestra?
- ¿o el reparto a mano es aceptable como parte del trabajo de compras?

Hasta que eso se resuelva, la plataforma **no imputa por parecido**: ni por monto, ni por fecha, ni
por saldo. Adivinar acá es exactamente lo que la spec prohíbe.

---

## Módulos afectados

| Módulo | Qué cambia | Nuevo |
|---|---|---|
| `portal` | Nada propio de 005. Reusa `extract_supplier_ledger` (`service.py:162`, `client.py:253`), que la 004 construyó para el padrón: los movimientos de la cuenta corriente viajan en la **misma** pantalla | No |
| `ingestion` | `staging.payment_row` y la mitad de `parse_supplier_ledger` que lee los movimientos (`parsers.py:824`), más `invoice_references_in` (`parsers.py:853`) y la publicación de `PaymentsNormalized` (`service.py:565`) | No |
| `purchases` | **El grueso.** `core.payment`, `core.receipt`, `core.receipt_incident`; tres columnas `portal_*` sobre `core.invoice`; el estado de pago calculado; la antigüedad y el atraso promedio del proveedor; la task `watch_due_dates` | No |
| `notifications` | Una suscripción a `InvoiceDueSoon` (`handlers.py:162`) y el texto del aviso (`service.py:207`). Ninguna tabla nueva: reusa `notification_recipient`, `notification_route` y la ventana horaria que construyó la 007 | No |

> **H8 no es autónoma, y conviene saberlo antes del merge.** El aviso de vencimiento se apoya en
> tablas y en la ventana horaria que construyó la **007**, y las tablas de esta feature viajan en la
> migración `0011`, compartida con 004, 006 y 007. Mientras las seis specs se entreguen juntas es
> inofensivo; deja de serlo si la 007 se difiere o si hay que partir la migración. En cualquiera de
> esos dos escenarios, **RF-38 se cae sin que nada más en este plan lo anuncie**. Es información
> para el Release-Manager, no trabajo para el Developer.
| `operations` | El parámetro `receipt.notice_days` del catálogo (`shared/parameters.py:252`) pasa a tener quien lo lea | No |
| `identity` | Dos secciones del mapa de permisos, `PAYMENTS` y `RECEIPTS`, ambas `WRITE` para dueño y compras y `NONE` para ventas (`permissions.py:79`, `permissions.py:81`) | No |

**Qué del módulo `purchases` NO es de esta feature:** el padrón (`Supplier`, `SupplierAlias`), la
factura como entidad y su cola de revisión, `InvoiceDocument`, `PurchaseCorrection` (todo 004);
`DueDate` y `DueDateChange` (006); `PurchaseOrder` (007). Esta feature **lee** `supplier.payment_term_days`
—que es de 004— porque es lo único de lo que sale un vencimiento (RF-26).

---

## Eventos de dominio

Los módulos no se importan entre sí (Artículo IV): todo lo que uno le cuenta a otro es un evento del
catálogo compartido, `backend/app/shared/events/catalog.py`. Verificado contra el `handlers.py` de
cada módulo, no contra el catálogo solo.

| Evento | Lo publica | Lo consume | Qué lleva |
|---|---|---|---|
| `SupplierLedgerExtracted` | `portal` — `service.py:169` | `ingestion` — `handlers.py:96` | `raw_document_id`, `content`, `job_run_id`. **Es de la 004**; 005 viaja en él porque los movimientos están en la misma pantalla que el padrón |
| `PaymentsNormalized` | `ingestion` — `service.py:565` | `purchases` — `handlers.py:75` | `batch_id`, `raw_document_id`, `payments: tuple[NormalizedPayment, ...]`, `quarantined`. Cada `NormalizedPayment` lleva `staging_row_id`, `supplier_text`, `references`, `paid_on`, `amount`, `external_id` |
| `PaymentsNeedingReview` | `purchases` — `service.py:1173` | **nadie hoy** | `cases: tuple[PaymentReviewCase, ...]` con `payment_id`, `reason`, `reference`, `supplier_text`, `amount`. Publicar sin oyentes es legal, pero acá **es un hallazgo**: ver H-2 |
| `InvoicesRegistered` | `purchases` — `service.py:555` | `purchases` — `handlers.py:81` | **Es de la 004.** 005 se suscribe al evento del propio módulo para RF-44: cuando entra la factura que un comprobante apartado nombraba, se lo imputa sin que nadie tenga que acordarse de llamar un paso |
| `ReceiptIssued` | `purchases` — `service.py:1374` | **nadie hoy** | `receipt_id`, `invoice_id`, `number`, `issued_by_user_id`, `issued_at` |
| `ReceiptVoided` | `purchases` — `service.py:1435` | **nadie hoy** | `receipt_id`, `invoice_id`, `voided_by_user_id` |
| `InvoiceDueSoon` | `purchases` (task) — `tasks.py:44` | `notifications` — `handlers.py:162` | `invoice_id`, `number`, `supplier_name`, `due_on`, `days_ahead`, `total`. El único evento que sale del módulo hacia otro |
| `BusinessParameterChanged` | `operations` | `purchases` — `handlers.py:103` (`WATCHED_PARAMETERS`, `handlers.py:36`) | `key`, `value`. **Es de la 003.** 005 lo usa para mantener `receipt.notice_days` en `core.purchase_setting` |

Tres observaciones que valen para el review:

- **Ninguno de estos eventos lleva un modelo de SQLAlchemy** (`GEN-08`): identificadores, strings,
  `Decimal`, `date` y tuplas de dataclasses `frozen`.
- **Ningún handler atrapa su excepción** (`GEN-09`): los cuatro handlers de `purchases` que tocan esta
  feature (`handlers.py:75`, `:81`, `:103`) delegan en el servicio y dejan propagar.
- **No hay ciclo** (`GEN-05`): `InvoiceDueSoon` va de `purchases` a `notifications` y `notifications`
  no publica nada que `purchases` escuche.

---

## Datos

El detalle campo por campo está en **[`data-model.md`](./data-model.md)**. Acá, lo que hay que saber
sin abrirlo:

- **`staging.payment_row`** — un movimiento de tipo `Pago` de la cuenta corriente, tipado. La
  referencia se guarda **entera y como la escribió el portal**: un comprobante que nombra dos
  facturas es exactamente el caso que la plataforma no parte sola, y partir el texto acá sería tomar
  esa decisión en el parser.
- **`core.payment`** — un pago: traído del portal o cargado a mano (`origin`), y contado, esperando o
  sin efecto (`state`). `external_id` **único** (`Aceros Belgrano SA|REC-1084`): el mismo comprobante
  leído dos veces se imputa una sola (RF-13). Nulo en un pago a mano, porque dos pagos a mano del
  mismo monto y el mismo día **son** dos pagos.
- **`core.receipt`** — número propio y correlativo (`RC-000001`), con índice único **parcial** sobre
  los no anulados: una factura puede tener varios a lo largo de su vida y uno solo que cuente
  (RF-35, RF-50).
- **`core.receipt_incident`** — índice único parcial sobre los abiertos, así abrir dos veces el mismo
  incidente no depende de que el código se acuerde de chequear (RF-37).
- **Tres columnas sobre `core.invoice` que son de esta feature**: `portal_paid`,
  `portal_payment_status` y `portal_receipt_issued` — lo que informa el portal, guardado al lado y
  nunca decidiendo. Más `due_on`, que 005 calcula (RF-26) y 006 puede mover.
- **Una migración, y ya está aplicada**: `backend/alembic/versions/0011_invoices_and_suppliers.py`,
  que crea las tablas de 004, 005, 006 y 007 juntas (`payment` en la línea 621, `receipt` en la 661,
  `receipt_incident` en la 689, `payment_row` en la 266). No hay migración exclusiva de 005.

---

## Contratos

El detalle —payloads, códigos de error, forma de cada schema— está en
**[`contracts/`](./contracts/README.md)**. Acá, las rutas con su autorización declarada (`PY-09`),
tal como salen de `backend/app/modules/purchases/routes.py`. Prefijo `/api/v1`.

| Ruta | Autorización declarada | Requisitos |
|---|---|---|
| `GET /invoices` | `require_section(PURCHASE_INVOICES, READ)` — `routes.py:88` | RF-01 a RF-05, RF-31, RF-32 (los parámetros `payment_state`, `due_from`/`due_to`, `with_receipt`) |
| `GET /invoices/{id}` | `require_section(PURCHASE_INVOICES, READ)` — `routes.py:132` | RF-06 |
| `GET /invoices/{id}/payments` | `require_section(PAYMENTS, READ)` — `routes.py:142` | RF-10, RF-20 |
| `POST /invoices/{id}/payments` | `require_section(PAYMENTS, WRITE)` — `routes.py:153` | RF-18, RF-19, RF-21 |
| `GET /invoices/{id}/receipt` | `require_section(RECEIPTS, READ)` — `routes.py:177` | RF-29, RF-47 |
| `POST /invoices/{id}/receipt` | `require_section(RECEIPTS, WRITE)` — `routes.py:188` | RF-33 a RF-36, RF-47, RF-48 |
| `GET /suppliers/{id}/totals` | `require_section(SUPPLIERS, READ)` — `routes.py:271` | RF-24 a RF-28 (compartida con RF-22/RF-23 de 004) |
| `GET /payments/pending` | `require_section(PAYMENTS, WRITE)` — `routes.py:387` | RF-11, RF-12, RF-54 |
| `POST /payments/{id}/split` | `require_section(PAYMENTS, WRITE)` — `routes.py:397` | RF-53, RF-55, RF-56 |
| `DELETE /payments/{id}` | `require_section(PAYMENTS, WRITE)` — `routes.py:416` | RF-22, RF-23 |
| `POST /payments/{id}/same-as` ⬜ **por construir** | `require_section(PAYMENTS, WRITE)` | RF-43 |
| `DELETE /receipts/{id}` | `require_section(RECEIPTS, WRITE)` — `routes.py:431` | RF-49, RF-50, RF-51 |
| `GET /receipt-incidents` | `require_section(RECEIPTS, READ)` — `routes.py:443` | RF-37, RF-59 |
| `POST /receipt-incidents/{id}/close` | `require_section(RECEIPTS, WRITE)` — `routes.py:456` | RF-57, RF-58, RF-59 |

**Ninguna es pública** y **ventas no llega a ninguna**: `PAYMENTS` y `RECEIPTS` valen `NONE` para el
rol `SALES` en `identity/permissions.py:79` y `:81`, que es la regla de negocio "los pagos y las
cuentas de proveedores no las ve ventas" escrita donde se verifica.

**El aviso de RF-21 es un `409` con el saldo en `details`**, y se contesta mandando el pago de nuevo
con `confirm_over_balance: true` (`service.py:1237`, `schemas.py:157`). Es lo que "avisar antes de
registrar" significa sobre HTTP: un aviso que no hay que contestar es un aviso que nadie lee.

> **Dónde vive la trazabilidad.** Este plan mapea requisitos a **rutas y pantallas**; `tasks.md`
> los mapea a **tareas y tests**, y su tabla de cobertura es la fuente única de qué está construido
> y qué no. Son dos tablas que hay que mover juntas: si alguna vez se contradicen, gana la de
> `tasks.md`, que es la que `/converge` recorre.

**Los routers están registrados** en `app/main.py:251-257`, que es el único lugar que conoce a todos
los módulos (`GEN-04`).

### Lo que corre solo, sin que nadie apriete nada

| Tarea | Cada cuánto | Qué hace | RF |
|---|---|---|---|
| `portal.extract_supplier_ledger` | El parámetro `invoice_sync.interval_hours`, compartido con las facturas y las órdenes (`operations/service.py:153-159`) | Lee `/estado-cuenta` y dispara todo el pipeline de pagos | RF-07 |
**RF-41 y RF-52 no tienen superficie propia, y por eso casi se pierden.** Los días de anticipación
del aviso son un parámetro del catálogo, `receipt.notice_days` (`shared/parameters.py:252`), con
`initial=3` —que es RF-52, el valor mientras el dueño no toque nada— y `consumed_by="purchases"`. La
pantalla donde el dueño lo cambia (RF-41) es **el panel de parámetros de la 003**, que se dibuja
solo desde el catálogo: no hay pantalla de esta feature que construir ni ruta que agregar. Queda
escrito porque un requisito que el plan no nombra es un requisito que nadie verifica — el Tester no
tenía dónde ir a buscarlo, y `/converge` tampoco.

| `purchases.watch_due_dates` | 24 h (`purchases/tasks.py:22`, `:63`) | Publica `InvoiceDueSoon` por cada factura **sin recibo** que vence dentro de `receipt.notice_days`, y abre incidente por cada una que ya venció sin recibo | RF-37, RF-38, RF-40 |

Que una factura **con** su recibo no genere aviso (RF-40) no es un `if` en `notifications`: es el
filtro de `invoices_due_soon` (`service.py:1514-1518`), que descarta las que están en
`receipts_in_force()`. El aviso es sobre el recibo, no sobre la plata.

### Pantallas

| Pantalla | Archivo | Requisitos |
|---|---|---|
| Lista de facturas | `frontend/app/(private)/facturas/page.tsx` + `components/purchases/InvoiceTable.tsx` | RF-01 a RF-05, RF-29, RF-31, RF-32 |
| Una factura: pagos y recibo | `frontend/app/(private)/facturas/[invoiceId]/page.tsx` + `components/purchases/InvoicePanel.tsx` | RF-06, RF-10, RF-15, RF-18 a RF-23, RF-33 a RF-35, RF-49, RF-50 |
| Ficha del proveedor | `frontend/app/(private)/proveedores/[supplierId]/page.tsx` | RF-24, RF-25, RF-27, RF-28 |
| **Comprobantes por repartir (H9)** | **no existe** | RF-11, RF-12, RF-53 a RF-56 → H-3 |
| **Incidentes de recibo (H10)** | **no existe** | RF-37, RF-57 a RF-59 → H-3 |

Las server actions `splitPayment` y `closeIncident` **sí** están escritas
(`frontend/app/actions/purchases.ts:180` y `:216`) y revalidan rutas que no existen
(`/facturas/pagos`, `/facturas/incidentes`): son la mitad de una pantalla que nunca se construyó.

---

## Lo que no coincide con la spec firmada

**Esto no legitima nada.** Son hallazgos para `/converge` y para el humano: no se arreglan en este
documento y no se esconden en el cuerpo. Cada uno con archivo, línea y el requisito que toca.

| # | Qué | Dónde | RF |
|---|---|---|---|
| H-1 | Una fila de `staging.payment_row` que no se pudo tipar queda `QUARANTINED` y **nada más**: no existe `PaymentRowsQuarantined` en el catálogo, no se abre caso de `triage` ni fila en `operations.exception`. **Cinco** normalizaciones sí publican su evento de cuarentena —precios, historial, facturas, órdenes, ventas— y la de pagos no (tampoco la de proveedores ni la del buzón). Y hay una segunda mitad que **no es de 005**: de esos cinco eventos sólo los dos de precios tienen suscriptor, así que aun publicando el evento la cuarentena de pagos seguiría sin llegar a nadie. La brecha del Artículo II es transversal a 004, 007 y 009 | `ingestion/service.py:515-528`, `:563`; publicadores `:201`, `:266`, `:426`, `:633`, `:760`; suscriptores `triage/handlers.py:34`, `:92` (y ninguno más); `shared/events/catalog.py` (no está) | Artículo II · RF-08 |
| H-2 | `PaymentsNeedingReview` se publica sin ningún suscriptor, y `GET /payments/pending` no tiene pantalla: un comprobante apartado es invisible para una persona | `purchases/service.py:1173`; `triage/handlers.py` (no suscribe) | RF-11, RF-12, RF-54 |
| H-3 | H9 (repartir un comprobante) y H10 (cerrar un incidente) **no tienen pantalla**. Las server actions existen y revalidan rutas inexistentes | `frontend/app/actions/purchases.ts:188`, `:224` | RF-11, RF-12, RF-37, RF-53 a RF-59 |
| H-4 | El aviso de vencimiento **se repite todos los días** mientras la factura siga sin recibo: `invoices_due_soon` devuelve todo lo que vence en la ventana y la task corre cada 24 h, sin registro de qué ya se avisó | `purchases/service.py:1502`; `purchases/tasks.py:41`; `notifications/handlers.py:189` | RF-39 |
| H-5 | El aviso va **a un solo rol** —compras por defecto, y al dueño sólo si nadie tiene el rol compras—, no a compras **y** al dueño | `notifications/service.py:191`; `notifications/delivery.py:42` | RF-38 |
| H-6 | `portal_receipt_issued` se guarda pero **no se lee nunca**: la pantalla, el filtro y el incidente miran sólo `core.receipt`. Una factura cuyo recibo ya existía en el portal figura como "Falta", puede recibir un segundo recibo y genera incidente | `purchases/service.py:583`, `:790`; `repository.py:367`, `:332` | RF-29, RF-30, RF-31, RF-37 |
| H-7 | El filtro por estado de pago se aplica **después** de paginar, y `total` no lo tiene en cuenta: la página puede venir corta y el contador dice otra cosa | `purchases/service.py:743-755` | RF-04 |
| H-8 | El recibo **no se descarga**: el documento se muestra en un `<pre>` y no hay enlace ni botón de descarga | `frontend/components/purchases/InvoicePanel.tsx:179` | RF-47 |
| H-9 | Ninguna pantalla de 005 dice **quién** hizo cada cosa: los schemas exponen `*_user_id` y no un nombre, y ningún componente lo resuelve. Además, ninguna acción de 005 publica `ManualChangeRecorded`, así que tampoco aparecen en `/historial` | `purchases/schemas.py:142`, `:168`, `:376`; `frontend/components/purchases/InvoicePanel.tsx:103-125` | RF-19, RF-36, RF-56, RF-58 |
| H-10 | El vencimiento cae a la columna del portal cuando el proveedor no tiene plazo, y **no se recalcula** después: ni cuando el padrón publica el plazo (`put_supplier`) ni cuando alguien lo corrige a mano. Sólo se recalcula al resolver una factura apartada | `purchases/service.py:596`, `:998`; `repository.py:62`; `service.py:1883` | RF-26 |
| H-11 | `split_payment` no verifica que las facturas del reparto sean **del mismo proveedor**, ni que sean del proveedor del comprobante. El supuesto firmado dice que un comprobante que cruza dos proveedores queda apartado | `purchases/service.py:1292-1320` | Supuesto de la spec · RF-53 |
| H-12 | El contador de "sin recibo" de la lista cuenta sólo lo que entró en la página (límite 200) y lo dice como "en esta vista"; no es el total del sistema | `frontend/app/(private)/facturas/page.tsx:62` | RF-32 |
| H-14 | **RF-43 no tiene implementación, y ya tiene diseño** (ver *Enfoque*: sobrevive el pago del portal, por `POST /payments/{id}/same-as`). Un comprobante apartado por «Coincide con un pago cargado a mano» no se puede resolver: `void_payment` rechaza los de origen `PORTAL` (RF-23) y `split_payment` lo imputaría a la misma factura, duplicando el pago. No hay ruta que diga «son el mismo, conservá uno» ni registro de quién lo decidió | `purchases/service.py:1145` (único uso de `VOUCHER_LOOKS_MANUAL`); no hay consumidor | RF-43 |
| H-13 | `warningFor` muestra **un** señalamiento por factura, por precedencia: una factura inconsistente que además discrepa con el portal no muestra la discrepancia | `frontend/lib/purchases/labels.ts:40-47` | RF-46 |
| H-15 | `InvoiceRead.receipt_number` está **declarado en el schema y nunca se asigna**: `_read_invoices` completa los otros nueve campos calculados del bloque y ese no, y no hay columna que lo respalde en `core.invoice`. Viaja siempre `null`. Ningún componente lo lee; sólo está espejado en el tipo generado. Hay que completarlo (el número está en `core.receipt`) o borrarlo del schema | `purchases/schemas.py:223`; `purchases/service.py:775-806` (no lo asigna); `frontend/lib/api/types.ts:2459` | Sin RF — campo muerto |

---

## Alternativas descartadas

- **Guardar el estado de pago en una columna de `invoice`.** Descartado: sería una segunda respuesta
  a una pregunta que los pagos ya contestan, y las dos se separarían la primera vez que alguien
  dejara un pago sin efecto. Se calcula en cada lectura (`service.py:775-809`). El costo aceptado es
  que el filtro por estado no puede ir en el `WHERE` — y eso es exactamente H-7.
- **Imputar por parecido cuando el comprobante no nombra factura** (por monto, por fecha, por saldo
  que cierra). Descartado por la spec, no por gusto: sería la plataforma decidiendo adónde fue la
  plata de alguien. Queda apartado y espera (`service.py:1112-1126`).
- **Unir solo el pago cargado a mano y el comprobante del portal que coinciden.** Descartado
  (RF-42): unirlos esconde un pago y contarlos por separado infla lo pagado, así que se pregunta
  (`service.py:1136`).
- **Dejar que se borre un pago traído del portal.** Descartado (RF-23): es lo que informó el origen y
  no nos toca borrar el registro de otro. Se rechaza con su motivo (`service.py:1275`).
- **Borrar el comprobante al repartirlo.** Descartado: queda `VOIDED`, con quién lo repartió y
  cuándo, y sus partes son las que valen (`service.py:1331-1336`). Nada se elimina.
- **Renderizar el recibo como PDF.** Descartado: metería una librería de renderizado entre el
  registro y el hecho que registra, y la presentación la puede resolver el navegador después. El
  documento es texto plano en español (`service.py:1388`), y por eso `IX` sigue en cero dependencias
  nuevas.
- **Adoptar una serie de numeración heredada del recibo en papel.** Descartado por el supuesto
  firmado: la numeración la lleva el sistema, correlativa y propia (`RC-%06d`, `service.py:1364`). Si
  el recibo de papel tiene su serie, se conversa antes de emitir el primero.
- **Chequear en el servicio "un recibo vigente por factura" y "un incidente abierto por factura".**
  Descartado: un chequeo puede correr una carrera consigo mismo. Lo deciden dos índices únicos
  parciales (`models.py:358`, `models.py:401`).
- **Un aviso de RF-21 que no haya que contestar** (un `warning` en el cuerpo de un `201`).
  Descartado: un aviso que no hay que contestar es un aviso que nadie lee. Es un `409` con el saldo
  y se confirma reenviando (`service.py:1237`).
- **Un módulo `payments` propio.** Descartado: no es una capacidad del negocio con lenguaje propio,
  es la misma factura mirada en otro momento. Separarlo obligaría a que el saldo de una factura
  viajara por eventos hasta el módulo que la muestra, que es la definición de una frontera mal
  trazada (`ARCHITECTURE.md` → *Cómo se lee lo que es de otro*).

---

## Riesgos

| Riesgo | Impacto | Cómo se mitiga |
|---|---|---|
| **La mayoría de los comprobantes quedan sin imputar**, porque el portal no dice qué factura cubren | Alto. El saldo de las facturas no se mueve solo y compras tiene que repartir a mano | No se mitiga con código: es una **pregunta al cliente** (ver *Lo que la implementación encontró*). Hoy se agrava porque no hay pantalla donde repartir (H-2, H-3) |
| **`next_receipt_number` es `count(*) + 1`** (`repository.py:507`) | Dos emisiones simultáneas piden el mismo número; la segunda falla contra `uq_receipt_number` con un error de base, no con un mensaje legible | El índice único evita el número repetido, que es lo que RF-48 pide. La carrera es rara —un solo usuario emitiendo— pero está sin cubrir: correspondería una secuencia de Postgres |
| **El estado de pago se calcula en cada lectura** y `_read_invoices` trae los totales de **todos** los pagos y todos los proveedores | Con 100 facturas es gratis; con 10.000 la lista se pone lenta | Aceptado a esta escala. `supplier_totals` ya pide `limit=100_000` (`service.py:1027`) y `_average_delay` consulta los pagos factura por factura (`service.py:1093`): es lo primero que hay que mirar si la ficha del proveedor se pone lenta |
| **El aviso se repite** (H-4) | Compras recibe el mismo mensaje varios días seguidos y deja de leerlos | Sin mitigar. Necesita un registro de "esto ya se avisó" del lado de `notifications`, como el que ya existe conceptualmente para la actualización de precios interrumpida |
| **Un recibo ya emitido en el portal no se ve** (H-6) | Se emite un segundo recibo por una factura que ya tenía el suyo, y se abre un incidente que no existe | Sin mitigar. El dato ya está guardado: falta leerlo |
| **La cuarentena de pagos es muda** (H-1) | Una fila ilegible del estado de cuenta no llega a ninguna persona | Sin mitigar, y **publicar el evento no alcanza**: hoy `triage` sólo suscribe los dos de precios, así que hace falta también el suscriptor. Es la brecha del Artículo II y excede esta feature —toca por igual a facturas, órdenes y ventas |

---

## Contexto de traspaso

**Para el Developer** — Empezá por `backend/app/modules/purchases/service.py`, secciones *The
payments* (línea 1112) y *The reception receipts and their incidents* (línea 1347): ahí está todo el
dominio de esta feature. Tres decisiones **ya tomadas** que no hay que rediscutir: (1) el estado de
pago no se guarda en ninguna columna —si te pinta agregar `invoice.payment_state`, es exactamente lo
que se descartó—; (2) el vencimiento sale de `supplier.payment_term_days` y de nada más, y la
columna del portal es sólo un respaldo mientras no haya plazo; (3) un comprobante que no nombra su
factura **nunca** se imputa por parecido. Lo que **no** hay que tocar sin hablarlo: `core.payment` y
`core.receipt` los comparte la 006 para pintar el calendario y la 009 para el tablero, y los índices
únicos parciales de `models.py:358`, `:401` y `:305` son reglas del negocio, no optimizaciones.
Cuidado con el módulo compartido: `purchases` es también de la 004, la 006 y la 007 — el padrón, la
cola de revisión, el calendario y las órdenes **no son de esta feature**. Lo que falta construir está
en *Lo que no coincide*, empezando por H-3: las dos pantallas que faltan tienen su backend entero y
sus server actions escritas.

**Para el Tester** — Lo que se rompe de verdad, y en silencio, es aritmética: **una factura con más
pagos que su total no puede figurar como saldada en ningún filtro ni total** (RF-14, RF-16, RF-17), y
la cuenta de `excluded` tiene que sumar con la de `invoices` en la ficha del proveedor; **un pago
traído del portal no se puede dejar sin efecto** (RF-23), y ese es un `409`, no un `403`; **el recibo
se niega después del vencimiento vigente** (RF-34), incluida la factura que la 006 reprogramó — ese
caso está testeado en la 006, no acá. Los casos borde que importan: el mismo comprobante leído dos
veces (RF-13, lo decide `uq_payment_external_id`, así que el test tiene que llegar a la base y no
mockear el repositorio); el comprobante que nombra una factura inexistente y se imputa solo el día
que esa factura entra (RF-44, `handlers.py:81`); el reparto que suma $280 sobre $300 (RF-55); y
`_disagrees` con un estado que el portal escribe con una palabra nueva —eso **no** es una
contradicción y no debe señalar nada (`service.py:823`). Lo que se prueba contra **HTML fijado** y
nunca contra el portal: `parse_supplier_ledger` sobre
`tests/fixtures/portal/suppliers-ledger-page-2026-08-29.html` (`TEST-03`); ahí está el test que
sostiene el hallazgo del origen —`test_a_voucher_that_names_its_own_receipt_names_no_invoice`— y si
alguna vez pasa a fallar es porque el portal cambió, no porque el test esté mal. **No escribas tests
que pasen por accidente**: `today_here()` (`service.py:188`) devuelve el día en Buenos Aires y no en
UTC, así que un test que fije fechas con `date.today()` de UTC va a pasar once meses al año y fallar
de madrugada; y `open_incidents_for_overdue` es idempotente **por el índice parcial**, así que
probarla dos veces sobre una base real es lo único que verifica RF-37 de verdad. La suite de la
feature es `backend/tests/integration/features/test_payments_and_receipts.py` (18 tests); **no hay
ningún test de frontend de esta feature**.

**Para el Code-Reviewer** — Mirá primero cuatro lugares. **`PY-09` en `routes.py`**: trece rutas de
005, ninguna pública, y ventas fuera de todas — la prueba está en `identity/permissions.py:79` y
`:81`, no en el docstring de la ruta. **`GEN-08` en `catalog.py:698-782`**: los cinco eventos de la
feature son `frozen`, en pasado, y llevan identificadores y `Decimal`/`date`, nunca un modelo;
`PaymentsNeedingReview`, `ReceiptIssued` y `ReceiptVoided` no tienen suscriptor, lo cual es legal —
pero fijate que el hallazgo H-2 depende de eso. **`ERR-04` y `ERR-05`**: el servicio lanza
`ConflictError`/`NotFoundError`/`ValidationError` de `shared/errors.py` y nunca `HTTPException`; y la
cuarentena de `staging.payment_row` **no genera excepción de operaciones** — ese es H-1, el hallazgo
más serio del changeset, y **no lo revises como un olvido de 005**: cinco normalizaciones publican su
evento de cuarentena (`ingestion/service.py:201`, `:266`, `:426`, `:633`, `:760`) y la de pagos no,
pero de esas cinco sólo las dos de precios tienen suscriptor (`triage/handlers.py:34`, `:92`). La
brecha del Artículo II alcanza también a facturas (004), órdenes (007) y ventas (009), y arreglarla
sólo acá —publicando el evento sin suscriptor— no cambiaría nada. **`DB-01`**: las tres tablas
viven en `alembic/versions/0011_invoices_and_suppliers.py` (líneas 621, 661, 689) y los índices únicos
parciales tienen que estar en la migración y en el modelo — si difieren, el modelo miente.
Y una advertencia de contexto: **este módulo es compartido**. Un hallazgo sobre el padrón, la cola de
revisión, el calendario o las órdenes de compra **no es de esta feature**: va a la 004, la 006 o la
007. Lo que sí es de acá, y no está en `CONVENTIONS.md` porque no es una convención sino la spec, es
que **ningún número se acomoda para que cierre**: si ves un `if paid > total` que redondea, corrige o
tapa, es un Blocker por `GEN-06`.
