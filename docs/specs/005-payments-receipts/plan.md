# Pagos y recibos — Plan técnico

<!--
  ARTEFACTO INTERNO. Acá van las decisiones técnicas que spec.md no puede llevar.
  No se exporta al cliente.
-->

**Feature:** 005-payments-receipts · **Spec aprobada el:** 2026-08-29 · **Fecha:** 2026-08-30
**Rol:** `Backend-Architect` (el grueso) · `Frontend-Architect` (las pantallas)

> **Este plan se escribió junto con la implementación, no antes.** El humano pidió implementar las
> seis specs pendientes en una sola pasada y lo confirmó como decisión suya. El orden normal es
> `/plan` y después `/implement`; acá el plan documenta lo que se construyó. Está anotado así
> porque un documento que finge haber sido escrito antes es peor que uno que dice cuándo se
> escribió.

## Constitution Check

| Artículo | Cumple | Cómo |
|---|---|---|
| I — El origen es ajeno y de sólo lectura | Sí | Los comprobantes salen de `/estado-cuenta`, leído con Playwright. Ninguna escritura, ningún endpoint JSON interno |
| II — Nada se descarta | Sí | **Es el artículo que esta feature encarna dos veces.** Un comprobante que no dice a qué factura corresponde no se reparte solo: queda pendiente, contado y visible (RF-12, RF-54). Una factura con más pagos que total no se declara saldada: se señala inconsistente, se informa y se excluye (RF-14 a RF-17) |
| III — Flujo unidireccional, `raw` inmutable | Sí | `raw.portal_document` guarda la pantalla del estado de cuenta; los pagos se tipan en `staging.payment_row` y recién ahí llegan a `core.payment` |
| IV — Las fronteras entre módulos son reales | Sí | Todo vive en `purchases`, que ya es dueño de la factura. `notifications` se entera de un vencimiento por `InvoiceDueSoon` y no lee ninguna tabla |
| V — Spec primero, y con firma | Sí | `spec.md` en `Aprobado`, firmada el 2026-08-29 |
| VI — Lo que no está tipado y testeado no está terminado | Sí | `tests/integration/features/test_payments_and_receipts.py`: 18 tests sobre las reglas que se rompen solas |
| VII — Las credenciales de terceros viven sólo en el entorno | Sí | Se reusa el cliente de `portal` |
| VIII — Un idioma para cada audiencia | Sí | Código en inglés; motivos, pantallas y este documento en español |
| IX — Las dependencias entran por la puerta | Sí | Cero dependencias nuevas |

**Excepciones solicitadas:** ninguna.

## Enfoque

Tres decisiones sostienen la feature, y las tres son de la spec y no de gusto.

**El estado de pago se calcula, no se guarda.** Sale de los pagos imputados (RF-45) y no de lo que
informa el portal. Guardarlo sería una segunda respuesta a una pregunta que los pagos ya contestan,
y las dos se separarían la primera vez que alguien deje un pago sin efecto. Lo que el portal dice se
guarda al lado, en `portal_payment_status`, y cuando los dos no coinciden la factura lo dice (RF-46):
no gana ninguno.

**El vencimiento sale del plazo pactado y de nada más** (RF-26). No de la columna `Vencimiento` que
publica la tabla del portal, que se usa sólo mientras el plazo del proveedor no se conoce —una fila
del padrón que el portal no expandió— y se corrige el día que se lee.

**Un comprobante no se reparte solo.** Y acá aparece el hallazgo de la implementación, abajo.

## Lo que la implementación encontró

> **Los comprobantes del portal no dicen a qué factura corresponden.** En `/estado-cuenta` un
> movimiento de tipo `Pago` trae como referencia **su propio número de recibo** (`REC-1084`), no el
> de la factura. El parser lo confirma sobre el fixture fijado, y hay un test que lo afirma
> (`test_a_voucher_that_names_its_own_receipt_names_no_invoice`).

La H2 de la spec asume que el comprobante indica la factura. Con los datos medidos eso no pasa, y la
consecuencia es visible: **la mayoría de los comprobantes van a quedar esperando a que una persona
diga qué cubren**, que es la pantalla de RF-53. Es Artículo II funcionando —la alternativa sería que
la plataforma decidiera adónde fue la plata de alguien— pero es un costo operativo real y es una
pregunta para el cliente, no una decisión del equipo:

- ¿el portal expone en algún lado la relación comprobante → factura que la pantalla no muestra?
- ¿o el reparto a mano es aceptable como parte del trabajo de compras?

Hasta que eso se resuelva, la plataforma **no imputa por parecido**: ni por monto, ni por fecha, ni
por saldo. Adivinar acá es exactamente lo que la spec prohíbe.

## Módulos afectados

| Módulo | Qué cambia | Nuevo |
|---|---|---|
| `portal` | Lee `/estado-cuenta` expandiendo las ocho filas | No |
| `ingestion` | `staging.payment_row` y el parser de los movimientos | No |
| `purchases` | `core.payment`, `core.receipt`, `core.receipt_incident`, y el estado calculado | No |
| `notifications` | El aviso de una factura que vence sin recibo, con su franja horaria | No |
| `operations` | El parámetro `receipt.notice_days` pasa a tener quien lo lea | No |

## Datos

- **`core.payment`** — origen (`PORTAL` \| `MANUAL`), estado (`IMPUTED` \| `PENDING` \| `VOIDED`),
  `external_id` **único**: el mismo comprobante leído dos veces se imputa una sola (RF-13).
- **`core.receipt`** — número propio y correlativo (`RC-000001`), con índice único **parcial** sobre
  los no anulados: una factura puede tener varios a lo largo de su vida y uno solo que cuente.
- **`core.receipt_incident`** — índice único parcial sobre los abiertos, así abrir dos veces el
  mismo incidente no depende de que el código se acuerde de chequear.

## Contratos

| Ruta | Quién | Requisitos |
|---|---|---|
| `GET /invoices/{id}/payments` | dueño · compras | RF-10, RF-20 |
| `POST /invoices/{id}/payments` | dueño · compras | RF-18, RF-19, RF-21 |
| `DELETE /payments/{id}` | dueño · compras | RF-22, RF-23 |
| `GET /payments/pending` | dueño · compras | RF-11, RF-12, RF-54 |
| `POST /payments/{id}/split` | dueño · compras | RF-53, RF-55, RF-56 |
| `GET`/`POST /invoices/{id}/receipt` | dueño · compras | RF-29, RF-33 a RF-36, RF-47, RF-48 |
| `DELETE /receipts/{id}` | dueño · compras | RF-49, RF-50, RF-51 |
| `GET /receipt-incidents` · `POST /receipt-incidents/{id}/close` | dueño · compras | RF-37, RF-57 a RF-59 |

El aviso de RF-21 es un **409 con el saldo en `details`**, y se contesta mandando el pago de nuevo
con `confirm_over_balance`. Es lo que "avisar antes de registrar" significa sobre HTTP: un aviso que
no hay que contestar es un aviso que nadie lee.

## Contexto de traspaso

**Para el Developer** — Lo que **no** hay que tocar: el estado de pago no se guarda en ninguna
columna, y el vencimiento no sale de la columna del portal salvo que no haya plazo pactado.

**Para el Tester** — Los tres que fallan en silencio: que una factura con más pagos que total **no**
figure como saldada y quede afuera de los totales; que un pago del portal no se pueda deshacer; y
que el recibo se niegue después del vencimiento aunque alguien mueva la fecha en el calendario
—eso último es de la 006 y está testeado ahí—.

**Para el Code-Reviewer** — `GEN-08` en `InvoiceDueSoon` y `ReceiptIssued`, y `PY-09` en las nueve
rutas: ventas no llega a ninguna.
