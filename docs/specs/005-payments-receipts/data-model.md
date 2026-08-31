# Pagos y recibos de recepción — Modelo de datos

<!-- ARTEFACTO INTERNO. Detalle de lo que plan.md resume. -->

**Feature:** 005-payments-receipts · **Fecha:** 2026-08-31

Escrito **contra el código construido**, no contra una intención: cada tabla se corresponde con su
modelo de SQLAlchemy en `backend/app/modules/*/models.py` y con la migración que la creó. Si este
documento y el modelo se contradicen, gana el modelo — y es un defecto de este documento.

**Una tabla nueva en `staging`, tres en `core`, ninguna en `raw`.** Todas nacen en la misma
migración: `backend/alembic/versions/0011_invoices_and_suppliers.py`, que crea juntas las tablas de
la 004, la 005, la 006 y la 007. **No hay migración exclusiva de esta feature.**

`purchases` es un módulo **compartido**. Lo que sigue marca explícitamente qué es de 005 y qué no.

---

## `raw` — sin tabla nueva, sin valor nuevo

`raw.portal_document` (`portal/models.py:37`) ya guarda cualquier pantalla del portal verbatim, con
su `content_hash` **único**. Los comprobantes de pago viajan dentro del documento
`SUPPLIER_LEDGER` —la pantalla `/estado-cuenta` con las ocho filas ya expandidas—, que es un valor
que agregó la **004** para el padrón. 005 no agrega ninguno.

Consecuencia que importa dos veces:

- **Idempotencia de la extracción** (`PY-07`): si `/estado-cuenta` no cambió, el hash coincide, el
  documento no se vuelve a guardar y los pagos no se vuelven a procesar.
- **Artículo III**: `content`, `content_hash`, `content_type` y `fetched_at` nunca se reescriben. La
  única columna que se escribe después del insert es `normalized_at`, que es contabilidad del
  pipeline y no algo que dijo el portal.

---

## `staging.payment_row` — el movimiento de la cuenta corriente, tipado

Modelo: `ingestion/models.py:274`. Migración: `0011`, línea 266.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `bigint` PK | |
| `raw_document_id` | `integer`, indexado | La pantalla `/estado-cuenta` de la que salió |
| `batch_id` | `integer` | De la secuencia de `staging`, como en el resto del pipeline |
| `line_number` | `integer` | El movimiento dentro de la pantalla, para poder señalarlo |
| `supplier_text` | `varchar(255)` NULL | El proveedor **como lo escribió el encabezado** del bloque. Es lo único que dice de quién es el movimiento |
| `reference` | `varchar(255)` NULL | La referencia **entera y tal cual**. Acá está el hallazgo del origen: para un pago dice `REC-1084` —su propio recibo— y no `F-8291`. Partir este texto en el parser sería tomar en el parser la decisión que RF-12 le reserva a una persona |
| `paid_on` | `date` NULL | La columna *Fecha*. Nulo si no se pudo leer |
| `amount` | `numeric(14,4)` NULL | La columna *Haber*. Nulo si no se pudo leer |
| `external_id` | `varchar(128)` NULL, indexado | `"{proveedor}\|{referencia}"`. **Lo que hace que el mismo comprobante sea el mismo entre dos corridas** (RF-13). Se arma en `parsers.py:845` |
| `status` | enum `staging.row_status` | `VALID` o `QUARANTINED`. Reusa el enum que ya existía |
| `reason` | `varchar(200)` NULL | Por qué se apartó |
| `excerpt` | `text` NULL | La fila entera como texto |
| `created_at` | `timestamptz` | |

Índice: `ix_payment_row_batch_status` sobre `(batch_id, status)`.

> **Brecha conocida (H-1 del plan).** Una fila `QUARANTINED` acá **no genera nada más**: no existe un
> evento `PaymentRowsQuarantined` en el catálogo, así que no se abre caso de `triage` ni fila en
> `operations.exception`. Sólo viaja un número en `PaymentsNormalized.quarantined`
> (`ingestion/service.py:569`), y ni siquiera es el de las filas apartadas: es
> `len(payment_rows) - len(imputable)`, o sea todo lo que no pasó —apartado o `VALID` sin fecha o sin
> monto—; y el evento entero sólo se publica si quedó al menos un pago imputable (`if imputable:`,
> `:563`), así que una corrida en la que **nada** se pudo leer no reporta nada. Es una brecha contra
> el Artículo II y está registrada para `/converge`, no aprobada acá.

Sólo pasan a `core` las filas `VALID` **con fecha y monto** (`ingestion/service.py:551-562`).

---

## `core.payment` — un pago, del portal o de una persona

Modelo: `purchases/models.py:292`. Migración: `0011`, línea 621. **Enteramente de 005.**

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `bigint` PK | |
| `supplier_id` | `bigint` FK → `core.supplier` `ON DELETE RESTRICT`, NULL | De quién es el pago. Nulo mientras el proveedor no se resuelve |
| `invoice_id` | `bigint` FK → `core.invoice` `ON DELETE CASCADE`, NULL | **A qué factura se imputa. Nulo es el caso normal de este portal**, no una excepción: el comprobante no dice qué factura cubre |
| `amount` | `numeric(14,4)` | |
| `paid_on` | `date` | |
| `origin` | enum `core.payment_origin` | `PORTAL` \| `MANUAL` (RF-20). Es lo que decide si se puede dejar sin efecto (RF-22, RF-23) |
| `state` | enum `core.payment_state` | `IMPUTED` \| `PENDING` \| `VOIDED`. **Sólo `IMPUTED` suma** al pagado de una factura (`repository.py:443`) |
| `external_id` | `varchar(160)` NULL, **único** | `Aceros Belgrano SA\|REC-1084`. `NULL` en un pago a mano: dos pagos a mano del mismo monto el mismo día **son** dos pagos, y una clave única los fusionaría |
| `reference` | `varchar(255)` NULL | La referencia del comprobante, o lo que escribió quien cargó a mano |
| `supplier_text` | `varchar(255)` NULL | El proveedor tal como vino escrito |
| `review_reason` | `varchar(200)` NULL | Por qué está apartado, en español y para leer: *«El comprobante no dice a qué factura corresponde»*, *«…menciona una factura que no tenemos registrada»*, *«…cubre más de una factura»*, *«Coincide con un pago cargado a mano»* (`service.py:125-128`) |
| `created_by_user_id` | `integer` NULL | Quién lo cargó (RF-19). Nulo en un pago del portal |
| `created_at` | `timestamptz` | Cuándo |
| `voided_by_user_id` | `integer` NULL | Quién lo dejó sin efecto (RF-22) |
| `voided_at` | `timestamptz` NULL | Cuándo |

Restricciones e índices:

| Nombre | Qué garantiza | RF |
|---|---|---|
| `uq_payment_external_id` (UNIQUE) | El mismo comprobante leído dos veces se imputa **una sola** | RF-13 |
| `ix_payment_invoice_id` | La lectura de los pagos de una factura | RF-10 |
| `ix_payment_state` | La cola de comprobantes apartados | RF-54 |

### Máquina de estados de un pago

```
             comprobante que nombra
             una factura conocida
   (portal) ─────────────────────────────────────────►  IMPUTED
      │                                                    │
      │ no nombra factura · nombra una desconocida ·        │ (nunca: RF-23)
      │ nombra varias · coincide con uno a mano             ✗
      ▼
   PENDING ──── una persona reparta (RF-53) ────────► VOIDED  (el comprobante)
      │                                              + N pagos IMPUTED (las partes)
      │
      └── entra la factura que nombraba (RF-44) ────► IMPUTED

   (a mano) ───────────────────────────────────────►  IMPUTED
                                                         │
                                    dejarlo sin efecto (RF-22)
                                                         ▼
                                                      VOIDED
```

Dos bordes que no son negociables: **un pago `PORTAL` nunca llega a `VOIDED` por decisión de una
persona** (`service.py:1275` lo rechaza con un `409`) — la única forma de que un `PORTAL` quede
`VOIDED` es que se lo reparta, y entonces lo reemplazan sus partes; y **un `PENDING` no suma nada**
mientras no se confirme el reparto (RF-54).

---

## `core.receipt` — el recibo de recepción

Modelo: `purchases/models.py:346`. Migración: `0011`, línea 661. **Enteramente de 005.**

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `bigint` PK | |
| `invoice_id` | `bigint` FK → `core.invoice` `ON DELETE CASCADE`, indexado | |
| `number` | `varchar(32)`, **único** | `RC-000001`. **Serie propia de la plataforma**, correlativa, calculada como `count(*) + 1` (`repository.py:507`). El portal no numera los nuestros (RF-48) |
| `issued_by_user_id` | `integer` | Quién lo emitió (RF-36) |
| `issued_at` | `timestamptz` | Cuándo |
| `document` | `text` NULL | **El documento que se descarga** (RF-47). Texto plano en español, armado en `service.py:1388`: número, factura, proveedor, fecha, monto, vencimiento y la constancia. No es un PDF a propósito: renderizarlo es una decisión de presentación y meter una librería acá pondría un motor entre el registro y el hecho que registra |
| `voided_by_user_id` | `integer` NULL | Quién lo anuló (RF-49) |
| `voided_at` | `timestamptz` NULL | Cuándo. `is_in_force` es `voided_at IS NULL` |

Restricciones:

| Nombre | Qué garantiza | RF |
|---|---|---|
| `uq_receipt_in_force` — UNIQUE **parcial** sobre `invoice_id WHERE voided_at IS NULL` | **Un recibo vigente por factura.** Una factura puede tener varios a lo largo de su vida y uno solo que cuente | RF-35, RF-50 |
| `uq_receipt_number` — UNIQUE | Ningún número se repite | RF-48 |

**Anulado, nunca borrado**: un recibo que desapareciera no se podría auditar, y RF-49 pide quién lo
anuló y cuándo.

### Máquina de estados del recibo de una factura

```
   sin recibo ──emitir, si due_on >= hoy (RF-33)──► vigente
       ▲                                              │
       │                                              │ anular (RF-49)
       │                                              ▼
       └──── si due_on >= hoy (RF-50) ────────────  anulado
                                                      │
                                                      │ si due_on < hoy (RF-51)
                                                      ▼
                                             incidente abierto
```

Emitir se niega en dos casos, y los dos con su motivo escrito (`service.py:1353`, `:1355`): la
factura ya tiene uno vigente (RF-35) o ya venció (RF-34). **Nada reabre la emisión una vez pasada la
fecha**: ni cerrar el incidente, ni reprogramar el vencimiento después.

---

## `core.receipt_incident` — la factura que venció sin su recibo

Modelo: `purchases/models.py:392`. Migración: `0011`, línea 689. **Enteramente de 005.**

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `bigint` PK | |
| `invoice_id` | `bigint` FK → `core.invoice` `ON DELETE CASCADE`, indexado | |
| `opened_on` | `date` | El día que se detectó |
| `closed_by_user_id` | `integer` NULL | Quién lo cerró (RF-58) |
| `closed_at` | `timestamptz` NULL | Cuándo |
| `resolution` | `text` NULL | **Qué se hizo.** Obligatorio al cerrar (`schemas.py:386`, `min_length=1`) |

Restricción: `uq_receipt_incident_open` — UNIQUE **parcial** sobre `invoice_id WHERE closed_at IS
NULL`. Un incidente abierto por factura, decidido por la base y no por un `if`: por eso
`open_incidents_for_overdue` es idempotente sin acordarse de chequear nada (RF-37).

**Cerrado, nunca borrado**: RF-59 pide que deje de contarse entre los pendientes y siga consultable
(`GET /receipt-incidents?include_closed=true`).

---

## `core.invoice` — las cuatro columnas que son de esta feature

La tabla es de la **004**. 005 le suma cuatro columnas y ninguna más (`purchases/models.py:185`):

| Columna | Tipo | De quién | Nota |
|---|---|---|---|
| `due_on` | `date` NULL, indexado | **005 la calcula**, 006 la puede mover | `issued_on + supplier.payment_term_days` (RF-26). Respaldo: la columna *Vencimiento* del portal **sólo** mientras el plazo no se conozca |
| `original_due_on` | `date` NULL | **006** | La primera fecha. No es de esta feature; se menciona porque vive al lado |
| `portal_paid` | `numeric(14,4)` NULL | 005 | Lo que el portal dice que se pagó. Guardado y mostrado, **nunca decide** |
| `portal_payment_status` | `varchar(50)` NULL | 005 | `Pagada` \| `Pago parcial` \| `Impaga`. Se compara contra el estado calculado y la diferencia se señala (RF-46) |
| `portal_receipt_issued` | `boolean` | 005 | Lo que el portal dice sobre el recibo (RF-30). **Hoy se guarda y no se lee** — H-6 del plan |

También **lee** `core.supplier.payment_term_days` (`models.py:143`), que es de la 004: es lo único de
lo que sale un vencimiento.

---

## Lo que NO se guarda, y por qué

- **El estado de pago.** No hay columna `payment_state`, y no debe haberla. Se calcula en cada
  lectura a partir de los pagos `IMPUTED` (`service.py:809`): guardarlo sería una segunda respuesta a
  una pregunta que los pagos ya contestan, y las dos se separarían la primera vez que alguien dejara
  un pago sin efecto (RF-45).
- **El saldo, el porcentaje pagado y "si tiene recibo".** Derivados, calculados en `_read_invoices`
  (`service.py:775-806`).
- **La antigüedad de la deuda y el atraso promedio.** Calculados por proveedor y a pedido
  (`service.py:1057`, `:1080`). Las bandas son constantes del código, no una tabla: *Por vencer*,
  *1 a 30*, *31 a 60*, *61 a 90*, *Más de 90* (`service.py:172`).
- **Si un aviso ya se mandó.** No se guarda en ningún lado, y por eso el aviso se repite: es H-4 del
  plan.

## Los estados que una pantalla lee

Cuatro, y son strings del servicio, no un enum de base (`service.py:146-149`):

| Valor | Cuándo | Qué pasa con él |
|---|---|---|
| `SIN_PAGOS` | `pagado <= 0` | Entra en los totales |
| `PARCIAL` | `0 < pagado < total` | Entra en los totales, con su `paid_pct` |
| `SALDADA` | `pagado >= total` | Entra en los totales |
| `INCONSISTENTE` | `pagado > total` | **Queda afuera** de los totales, y cuántas quedaron afuera viaja con el número (RF-16, RF-28) |

Una factura en `PENDING` de revisión (004) también queda afuera de los totales
(`service.py:1032-1039`).

## El parámetro

| Clave | Dónde vive | Valor inicial | Quién lo lee |
|---|---|---|---|
| `receipt.notice_days` | Catálogo en `shared/parameters.py:252`; proyección del módulo en `core.purchase_setting` | **3** (RF-52) | `purchases.invoices_due_soon` (`service.py:1502`), a través de su propia proyección alimentada por `BusinessParameterChanged` (`handlers.py:103`) |

Cambiarlo es del dueño: la sección `SYSTEM_PARAMETERS` es `WRITE` sólo para `OWNER`
(`identity/permissions.py:90`), que es RF-41.

> `due_date.notice_days` existe en el catálogo y **no lo lee nadie**: la 003 lo declaró esperando que
> el calendario lo tomara, y el aviso que terminó existiendo es el del recibo. Está marcado
> `consumed_by=""` a propósito (`shared/parameters.py:238`). No es de esta feature y no hay que
> confundirlo con el de arriba.
