# Pagos y recibos de recepción — Contratos

<!-- ARTEFACTO INTERNO. El detalle que plan.md resume en una tabla. -->

**Feature:** 005-payments-receipts · **Fecha:** 2026-08-31

Dos contratos, y son de naturaleza distinta:

- **[El contrato HTTP](#el-contrato-http)** — lo que el frontend le pide al backend. Se genera solo
  desde el schema de OpenAPI (`make frontend-api-types`, `TS-05`), así que **la fuente de verdad es
  `backend/app/modules/purchases/routes.py` y `schemas.py`**, y este documento explica lo que el
  schema no puede decir: quién puede llamar cada ruta y por qué un error es el que es.
- **[El contrato de eventos](#el-contrato-de-eventos)** — lo que un módulo le cuenta a otro. La
  fuente de verdad es `backend/app/shared/events/catalog.py`.

Prefijo de todas las rutas: `/api/v1`. Ninguna es pública.

---

## El contrato HTTP

### Cómo se declara la autorización

Cada ruta declara su dependencia con `require_section(Section.X, Level.Y)`, importado de
`app.modules.identity.dependencies` — el **único** import que cruza una frontera de módulo, y lo
hace porque una request tiene que saber si puede seguir antes de que corra su handler (Artículo IV).
Lo verifica `backend/tests/architecture/test_route_authorization.py`, que además comprueba que un
request anónimo reciba `401`.

Dos secciones gobiernan esta feature, y **ventas no llega a ninguna**
(`identity/permissions.py:79`, `:81`):

| Sección | `OWNER` | `PURCHASING` | `SALES` |
|---|---|---|---|
| `PAYMENTS` | `WRITE` | `WRITE` | `NONE` |
| `RECEIPTS` | `WRITE` | `WRITE` | `NONE` |

`Level` está ordenado, así que quien tiene `WRITE` también lee.

### Los errores

Los servicios lanzan errores de dominio de `app/shared/errors.py` y **nunca** `HTTPException`
(`ERR-04`); `app/main.py` los traduce:

| Error de dominio | HTTP | Cuándo, en esta feature |
|---|---|---|
| `NotFoundError` | `404` | No existe la factura, el pago, el recibo o el incidente. También: la factura **no tiene** recibo emitido |
| `ConflictError` | `409` | El pago supera el saldo (RF-21) · un pago del portal no se deja sin efecto (RF-23) · la factura ya tiene recibo (RF-35) · ya venció (RF-34) · el recibo ya está anulado · el comprobante ya está imputado · el incidente ya está cerrado |
| `ValidationError` | `422` | Las partes de un reparto no suman el monto del comprobante (RF-55) |

Todos responden `{"error": {"type", "message", "details"}}`. **`message` está en español**: lo lee
una persona.

---

### Las facturas, en lo que 005 les agrega

#### `GET /invoices`

`require_section(PURCHASE_INVOICES, READ)` · `routes.py:88`

Parámetros que son de esta feature:

| Parámetro | Tipo | Qué hace | RF |
|---|---|---|---|
| `payment_state` | `SALDADA` \| `PARCIAL` \| `SIN_PAGOS` \| `INCONSISTENTE` | Filtra por el estado **calculado** | RF-04 |
| `due_from` / `due_to` | `date` | Por fecha de vencimiento. **No** confundir con `issued_from`/`issued_to`, que son la fecha de emisión | RF-05 |
| `with_receipt` | `bool` | Con o sin recibo de recepción vigente | RF-31 |
| `supplier_id` | `int` | | RF-05 |

Respuesta `InvoiceList`: `{items, total, skip, limit}`. Cada `InvoiceRead` trae, además de lo de
004, diez campos que no vienen de la tabla (`schemas.py:214-224`). **Nueve los calcula
`_read_invoices` (`service.py:775-806`); `receipt_number` no lo calcula nadie**:

```
paid                     Decimal   suma de los pagos IMPUTED            RF-02
balance                  Decimal   total - paid                          RF-02
paid_pct                 int       porcentaje pagado                     RF-03
payment_state            str       SALDADA | PARCIAL | SIN_PAGOS | INCONSISTENTE   RF-01
portal_payment_status    str|null  lo que dice el portal                 RF-46
payment_state_disagrees  bool      los dos no coinciden                  RF-46
is_inconsistent          bool      payment_state == INCONSISTENTE        RF-14
receipt_issued           bool      tiene recibo vigente                  RF-29
receipt_number           str|null  DECLARADO Y NUNCA ASIGNADO — siempre null (H-15)
is_overdue_without_receipt  bool   venció y no tiene recibo              RF-37
```

> **Cuidado (H-7 del plan):** `payment_state` se aplica **después** de paginar y `total` no lo tiene
> en cuenta (`service.py:743-755`). La página puede venir corta y el contador decir otra cosa.
>
> **Cuidado (H-15 del plan):** `receipt_number` está en el schema y **nada lo completa** —no es
> columna de `core.invoice` y `_read_invoices` no lo asigna—, así que llega siempre `null`. No
> escribas un test que afirme un número acá: el número del recibo se pide por
> `GET /invoices/{id}/receipt`.

#### `GET /invoices/{id}/payments`

`require_section(PAYMENTS, READ)` · `routes.py:142` · RF-10, RF-20

Devuelve `PaymentRead[]` — **todos** los pagos de la factura, los `VOIDED` incluidos, ordenados por
fecha. Que se vean los dejados sin efecto es deliberado: RF-22 pide que quede registrado.

```
PaymentRead = {
  id, invoice_id, supplier_id, amount, paid_on,
  origin: "PORTAL" | "MANUAL",          # RF-20
  state:  "IMPUTED" | "PENDING" | "VOIDED",
  reference, supplier_text, review_reason,
  created_by_user_id, created_at,
  voided_by_user_id, voided_at
}
```

> **Cuidado (H-9 del plan):** viaja el `id` del usuario, no su nombre. RF-19 pide el **nombre**.

#### `POST /invoices/{id}/payments`

`require_section(PAYMENTS, WRITE)` · `routes.py:153` · RF-18, RF-19, RF-21 · `201`

```
PaymentWrite = {
  amount: Decimal > 0,
  paid_on: date,
  reference: str|null (<=255),
  confirm_over_balance: bool = false
}
```

**Quién lo cargó sale del token, nunca del cuerpo** (`routes.py:170`).

El aviso de RF-21 **es el rechazo**:

```
1º intento, amount > balance, confirm_over_balance = false
  → 409 ConflictError
    message: "El pago supera el saldo de la factura"
    details: { invoice_id, balance, amount }

2º intento, confirm_over_balance = true
  → 201 PaymentRead
```

Es lo que "avisar antes de registrarlo" significa sobre HTTP: un aviso que no hay que contestar es
un aviso que nadie lee.

#### `GET /invoices/{id}/receipt`

`require_section(RECEIPTS, READ)` · `routes.py:177` · RF-29, RF-47

Devuelve el recibo **vigente**, o `404` con `"La factura no tiene recibo emitido"`. El `404` no es un
error de la pantalla: es la respuesta normal para una factura sin recibo, y la pantalla la lee como
`missing` (`frontend/lib/api/server.ts:36`).

```
ReceiptRead = { id, invoice_id, number, issued_by_user_id, issued_at,
                voided_by_user_id, voided_at, document }
```

`document` es el texto plano del recibo (RF-47).

> **Cuidado (H-8 del plan):** no hay ruta ni cabecera de descarga. La pantalla muestra `document` en
> un `<pre>`. RF-47 pide **descargarlo**.

#### `POST /invoices/{id}/receipt`

`require_section(RECEIPTS, WRITE)` · `routes.py:188` · RF-33, RF-36, RF-47, RF-48 · `201`

Sin cuerpo: quién emite sale del token. Dos rechazos, los dos `409` con su motivo en español:

| Motivo | `message` | RF |
|---|---|---|
| Ya tiene recibo vigente | `La factura ya tiene su recibo emitido` | RF-35 |
| Ya venció | `La factura ya venció y por eso no se le puede emitir el recibo` (+ `details.due_on`) | RF-34 |

La fecha que manda es `invoice.due_on`, **la vigente**: si la 006 reprogramó el vencimiento antes de
que la factura venciera, el plazo corre hasta la fecha nueva.

Publica `ReceiptIssued`.

---

### Los pagos apartados

#### `GET /payments/pending`

`require_section(PAYMENTS, WRITE)` · `routes.py:387` · RF-11, RF-12, RF-54

`PaymentRead[]` con `state = PENDING`, ordenados por fecha. `review_reason` dice por qué está
apartado, en español y listo para mostrar.

> **Cuidado (H-2, H-3 del plan): esta ruta no tiene pantalla.** Hoy un comprobante apartado es
> invisible para una persona.

#### `POST /payments/{id}/split`

`require_section(PAYMENTS, WRITE)` · `routes.py:397` · RF-53, RF-55, RF-56

```
PaymentSplitWrite = { parts: [ { invoice_id: int, amount: Decimal > 0 }, ... ] }   # min 1
```

Tres verificaciones, en este orden (`service.py:1300-1313`):

1. el pago existe → `404`
2. está en `PENDING` → si no, `409 "Ese comprobante ya está imputado"`
3. **las partes suman exactamente el monto** → si no, `422 "Las partes no suman el monto del
   comprobante"` con `details.amount` (RF-55)

Efecto: se crean N pagos `IMPUTED`, uno por parte, con `created_by_user_id` = quien repartió
(RF-56), y **el comprobante original queda `VOIDED`** con quién y cuándo. Nada se borra. Devuelve las
partes creadas.

> **Cuidado (H-11 del plan):** no verifica que las facturas sean del **mismo proveedor**, ni que sean
> del proveedor del comprobante. El supuesto firmado dice que un comprobante que cruza dos
> proveedores queda apartado.

#### `DELETE /payments/{id}`

`require_section(PAYMENTS, WRITE)` · `routes.py:416` · RF-22, RF-23

No borra: pasa el pago a `VOIDED` con quién y cuándo, y devuelve el `PaymentRead`. Un pago con
`origin = PORTAL` se rechaza con `409 "Un pago traído del portal no se puede dejar sin efecto"`
(RF-23).

#### `POST /payments/{payment_id}/same-as` ⬜ **por construir**

`require_section(PAYMENTS, WRITE)` · RF-43

La salida del comprobante apartado por `VOUCHER_LOOKS_MANUAL`: una persona declara que el
comprobante del portal y un pago cargado a mano **son el mismo pago**, y el sistema conserva uno
solo.

Cuerpo: `{ "manual_payment_id": int }`. `payment_id` es el del comprobante del portal.

Efecto, en este orden: el comprobante del portal pasa a `IMPUTED` sobre la factura del pago manual;
el pago manual pasa a `VOIDED` con el motivo «Es el mismo pago que el comprobante RC-…»; y se
registra `resolved_by_user_id` y `resolved_at`.

**Sobrevive el del portal, y no es una preferencia.** RF-23 prohíbe dejar sin efecto un pago traído
del portal, así que conservar el manual habría exigido romper un requisito firmado para cumplir otro.
Además el que sobrevive queda con `external_id`, así que si el mismo comprobante vuelve a llegar,
`uq_payment_external_id` lo reconoce.

Errores:

- `409` si los dos pagos tienen el mismo `origin` — dos manuales no son este caso, y dos del portal
  los resuelve el índice único.
- `409` si el comprobante no está `PENDING` con motivo `VOUCHER_LOOKS_MANUAL`.
- `404` si cualquiera de los dos pagos no existe.

**Ni el monto ni la fecha del pago que se conserva cambian:** unir dos pagos no es promediarlos.

---

### Los recibos y sus incidentes

#### `DELETE /receipts/{id}`

`require_section(RECEIPTS, WRITE)` · `routes.py:431` · RF-49, RF-50, RF-51

Anula, no borra. Rechaza con `409` si ya estaba anulado. Después de anular, **el efecto depende de la
factura y no del recibo**: si todavía no venció, se le puede emitir otro (RF-50); si ya venció, se le
abre un incidente (RF-51, `service.py:1433`). Publica `ReceiptVoided`.

#### `GET /receipt-incidents`

`require_section(RECEIPTS, READ)` · `routes.py:443` · RF-37, RF-59

| Parámetro | Default | Qué hace |
|---|---|---|
| `include_closed` | `false` | Con `true`, también los ya cerrados (RF-59) |

```
IncidentRead = { id, invoice_id, opened_on, closed_by_user_id, closed_at,
                 resolution, invoice_number, supplier_name }
```

#### `POST /receipt-incidents/{id}/close`

`require_section(RECEIPTS, WRITE)` · `routes.py:456` · RF-57, RF-58, RF-59

```
IncidentClose = { resolution: str (1..1000) }   # obligatorio: se cierra explicando qué se hizo
```

`409` si ya estaba cerrado. Quién lo cerró sale del token.

> **Cuidado (H-3 del plan): estas dos rutas tampoco tienen pantalla.**

---

### La ficha del proveedor

#### `GET /suppliers/{id}/totals`

`require_section(SUPPLIERS, READ)` · `routes.py:271` · RF-24 a RF-28 (y RF-22/RF-23 de 004)

| Parámetro | Qué hace |
|---|---|
| `since` / `until` | Acotan por fecha de **emisión** de la factura |

```
SupplierTotalsRead = {
  supplier_id, invoiced, paid, owed,        # RF-24
  invoices,                                  # cuántas entran
  excluded,                                  # cuántas quedaron afuera   RF-28
  aging: [ { label, amount, invoices } ],    # RF-25
  average_delay_days: Decimal | null,        # RF-27
  since, until
}
```

**`excluded` no es una nota al pie.** Una factura en revisión (004) o señalada como inconsistente
(RF-14) queda **fuera** de los totales, y cuántas quedaron afuera viaja con el número: un total que
descarta filas en silencio es un total que el cliente desmiente la primera vez que lo verifica a
mano (RF-16, RF-28).

Las bandas de `aging` son cinco y salen del vencimiento vigente: *Por vencer*, *1 a 30 días*,
*31 a 60 días*, *61 a 90 días*, *Más de 90 días*.

`average_delay_days` es `null` cuando no hay ningún atraso, y **no** cero: son dos cosas distintas.
Cuenta las pagadas hasta el pago que las saldó y las impagas vencidas hasta hoy; una que todavía no
venció no entra (RF-27).

---

## El contrato de eventos

Todos viven en `backend/app/shared/events/catalog.py`, líneas 698 a 782 para los de esta feature.
Todos son `@dataclass(frozen=True, slots=True)` y llevan identificadores y valores planos, nunca un
modelo de SQLAlchemy (`GEN-08`).

### Los que 005 define

```python
NormalizedPayment(               # no es un evento: es la carga de PaymentsNormalized
    staging_row_id: int,
    supplier_text: str,
    references: tuple[str, ...],  # tupla porque un comprobante puede nombrar varias facturas
    paid_on: date,
    amount: Decimal,
    external_id: str,
)

PaymentsNormalized(              # ingestion → purchases
    batch_id: int,
    raw_document_id: int,
    payments: tuple[NormalizedPayment, ...],
    quarantined: int = 0,
)

PaymentReviewCase(               # carga de PaymentsNeedingReview
    payment_id: int, reason: str, reference: str,
    supplier_text: str, amount: Decimal,
)

PaymentsNeedingReview(           # purchases → (nadie hoy)
    cases: tuple[PaymentReviewCase, ...],
)

ReceiptIssued(                   # purchases → (nadie hoy)
    receipt_id: int, invoice_id: int, number: str,
    issued_by_user_id: int, issued_at: datetime,
)

ReceiptVoided(                   # purchases → (nadie hoy)
    receipt_id: int, invoice_id: int, voided_by_user_id: int,
)

InvoiceDueSoon(                  # purchases (task) → notifications
    invoice_id: int, number: str, supplier_name: str,
    due_on: date, days_ahead: int, total: Decimal,
)
```

### Los que 005 consume y no define

| Evento | De quién es | Para qué lo usa 005 |
|---|---|---|
| `SupplierLedgerExtracted` | 004 (`portal`) | Los movimientos de la cuenta corriente vienen en la misma pantalla que el padrón |
| `InvoicesRegistered` | 004 (`purchases`) | RF-44: cuando entra la factura que un comprobante apartado nombraba, se lo imputa (`purchases/handlers.py:81`) |
| `BusinessParameterChanged` | 003 (`operations`) | Mantiene `receipt.notice_days` en la proyección del módulo (`purchases/handlers.py:103`) |

### Reglas que se cumplen y hay que seguir cumpliendo

- **Los handlers corren en la transacción de quien publicó**, y si fallan la abortan (`GEN-09`).
  Ninguno de los handlers de esta feature atrapa su excepción.
- **`InvoiceDueSoon` se publica desde una task**, no desde un handler, precisamente porque el envío
  de un WhatsApp no puede vivir dentro de la transacción de nadie. `notifications` lo recibe y
  **encola** (`notifications/handlers.py:189-200`): nunca llama a la API de terceros en línea.
- **Publicar sin oyentes es legal.** Tres eventos de acá no tienen suscriptor. Para `ReceiptIssued` y
  `ReceiptVoided` eso está bien —son hechos que alguien puede querer escuchar mañana—; para
  `PaymentsNeedingReview` es el hallazgo H-2 del plan.
- **No hay ciclo** (`GEN-05`): `notifications` no publica nada que `purchases` escuche.
