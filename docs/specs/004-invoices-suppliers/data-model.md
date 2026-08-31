# Facturas y proveedores — Modelo de datos

<!-- ARTEFACTO INTERNO. Detalle de lo que plan.md resume. -->

**Feature:** 004-invoices-suppliers · **Fecha:** 2026-08-30

Tres tablas en `staging`, cinco en `core`, ninguna nueva en `raw` —la que hay alcanza— y dos `kind`
nuevos en la cola de `triage`, que ya es genérica y no cambia de forma.

## `raw` — sin tabla nueva

`raw.portal_document` ya guarda cualquier documento del portal con su hash único. Esta feature suma
tres valores al enum `PortalSection`, y nada más:

| Valor | Qué guarda |
|---|---|
| `INVOICES` | La pantalla `/facturas` renderizada, con sus 100 filas |
| `INVOICE_FILE` | El archivo de **una** factura, tal como se descargó: PDF, PDF escaneado o `.xlsx` |
| `SUPPLIER_LEDGER` | La pantalla `/estado-cuenta` con las ocho filas ya expandidas |

Una fila por archivo de factura, no un blob por corrida: es lo que permite volver a leer una sola
factura cuando cambia el motor de OCR, sin tocar las otras noventa y nueve (Artículo III).

## `staging.invoice_row` — lo que dijo la tabla del portal

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `bigint` PK | |
| `raw_document_id` | `bigint` | La pantalla de la que salió. |
| `batch_id` | `bigint` | De la secuencia de `staging`, como en la lista de precios. |
| `line_number` | `int` | La fila dentro de la tabla, para poder señalarla. |
| `invoice_number` | `varchar(50)` NULL | `F-9936`. Nulo si esa celda no se pudo leer. |
| `supplier_name_raw` | `varchar(200)` NULL | **La grafía tal como vino**, sin normalizar. Es el insumo de RF-10. |
| `issued_on` | `date` NULL | La tabla la publica en ISO. |
| `total` | `numeric(14,2)` NULL | La tabla la publica como `$223.376`: el punto es separador de miles. |
| `file_kind` | `varchar(20)` NULL | `PDF`, `PDF_SCANNED`, `EXCEL` — la columna *Tipo* (RF-05). |
| `status` | enum `row_status` | `VALID` o `QUARANTINED`, el enum que ya existe. |
| `reason` | `varchar(100)` NULL | Por qué se apartó. |
| `excerpt` | `text` | La fila entera como texto, para mostrarla en la revisión. |

## `staging.invoice_file_read` — lo que dijo el archivo

Una fila **por dato leído**, no por archivo: la certeza es por campo, y RF-27 pide registrarla campo
por campo.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `bigint` PK | |
| `raw_document_id` | `bigint` | El archivo del que salió. |
| `invoice_number_hint` | `varchar(50)` NULL | Con qué factura se lo asoció al descargarlo. |
| `field` | `varchar(30)` | `number`, `issued_on`, `supplier`, `total`. |
| `value` | `text` NULL | Lo leído, sin interpretar. |
| `confidence` | `numeric(4,3)` NULL | Lo que devolvió el lector. Nulo cuando el formato es determinista —PDF con texto y planilla no tienen confianza, tienen valor—. |
| `matches_listing` | `boolean` NULL | **La columna que decide.** Si el archivo y la tabla dicen lo mismo, el dato es certeza; si difieren, la factura va a revisión (RF-27, RF-29). |
| `excerpt` | `text` NULL | El recorte del archivo del que salió el dato: para el escaneado, el rectángulo; para la planilla, la celda (RF-30). |
| `reader` | `varchar(30)` | `pypdf`, `tesseract`, `openpyxl`. Sirve para reprocesar sólo lo que leyó un motor viejo. |

## `staging.supplier_row` — lo que dijo el padrón

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `bigint` PK | |
| `raw_document_id` | `bigint` | La pantalla `/estado-cuenta`. |
| `legal_name` | `varchar(200)` | Razón social, como la publica el portal. |
| `tax_id` | `varchar(20)` NULL | El CUIT del proveedor. |
| `email` · `phone` | `varchar(150)` NULL | Del detalle expandido. |
| `payment_terms_days` | `int` NULL | 30, 45 o 60. El portal lo escribe `45 dias`. |
| `status` · `reason` · `excerpt` | | Igual que las otras dos: nada se descarta. |

El domicilio que el portal también publica **no se guarda**: la spec firmada pide cinco campos y no
lo incluye.

## `core.supplier` — el padrón

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `int` PK | |
| `legal_name` | `varchar(200)` | RF-15. |
| `tax_id` | `varchar(20)` UNIQUE NULL | El CUIT. Único: es lo que hace determinista la identificación cuando está. |
| `email` · `phone` | `varchar(150)` NULL | Nulo se muestra como *falta*, no como vacío (RF-20). |
| `payment_terms_days` | `int` NULL | Valor inicial del portal, corregible (RF-16). |
| `portal_first_seen_at` | `timestamptz` | Cuándo apareció en el padrón. |

Ocho filas, y sólo se crean leyendo el padrón: **nada da de alta un proveedor** (RF-14).

## `core.supplier_alias` — las grafías

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `bigint` PK | |
| `supplier_id` | `int` FK → `core.supplier` | |
| `spelling` | `varchar(200)` | La grafía tal como llegó. |
| `normalized` | `varchar(200)` | La misma pasada por `app/shared/text.py`, que ya existe. Indexada: es por donde entra la búsqueda. |
| `source` | enum `alias_source` | `PORTAL` — la razón social del padrón — o `DECIDED` — una persona la asignó (RF-47). |
| `rule_id` | `bigint` NULL | La regla de `triage` que la creó, para poder deshacerla exactamente (RF-53). |
| `decided_by_user_id` · `decided_at` | | Quién y cuándo (RF-51). |

**Único** por `normalized`: la misma grafía no puede apuntar a dos proveedores, y esa es toda la
garantía de RF-50.

## `core.invoice` — la factura

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `bigint` PK | |
| `supplier_id` | `int` FK NULL | **Nulo mientras no esté identificado**, y por eso el duplicado no la alcanza (RF-40). |
| `number` | `varchar(50)` | |
| `issued_on` | `date` | |
| `total` | `numeric(14,2)` | |
| `status` | enum `invoice_status` | `REGISTERED` · `IN_REVIEW`. |
| `review_reason` | `varchar(50)` NULL | `doubtful_data`, `ambiguous_supplier`, `supplier_not_in_padron`, `duplicate_mismatch`, `unreadable_file`. |
| `arrival_count` | `int` default 1 | Cuántas veces llegó la misma (RF-39). |
| `supplier_name_raw` | `varchar(200)` | La grafía con la que llegó: es lo que se muestra en la revisión. |
| `registered_at` | `timestamptz` | |

**Índice único parcial** `uq_invoice_in_force` sobre `(supplier_id, number)` con
`WHERE supplier_id IS NOT NULL`: la clave de duplicado firmada, y la razón por la que dos facturas
sin proveedor no se pisan.

**Índices de búsqueda** (H8): `(issued_on DESC)`, `(supplier_id, issued_on DESC)`, `(status)`, y
`(total)` para el ordenamiento. La búsqueda por CUIT y por razón social entra por `core.supplier`.

Ninguna fila puede existir sin número, fecha y total: las tres columnas son `NOT NULL` (RF-35). Lo
que todavía no los tiene no es una factura registrada, es un caso en la cola.

## `core.invoice_file` — el archivo, y de dónde salió cada dato

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `bigint` PK | |
| `invoice_id` | `bigint` FK | |
| `raw_document_id` | `bigint` | Para servir el original sin copiarlo (RF-04). |
| `file_kind` | enum | `PDF` · `PDF_SCANNED` · `EXCEL` (RF-05). |
| `field_origin` | `jsonb` | Por campo: si salió de la tabla, del archivo, o de una persona, y si hubo coincidencia. Es lo que la pantalla muestra como *certeza* o *duda* (RF-23, RF-27). |

## `core.purchase_correction` — la corrección de contacto

Las columnas salen de `CorrectionColumns`, en `app/shared/corrections.py`, **sin inventar nada**: su
docstring dice que existe para que las facturas de compra tengan su tabla con la misma forma. Lo
único propio es el nombre de la tabla y su índice único parcial sobre `(entity_type, entity_id,
field)` para las que no están `REVERTED`.

Cubre RF-16 a RF-19: la corrección gana sobre el portal, guarda `portal_value` para poder deshacer,
y cuando el portal trae otro valor pasa a `CONFLICTED` en vez de perderse.

## Máquina de estados de una factura

Es la del diagrama `diagrams/estados-factura.mmd`, en columnas:

| Desde | Hacia | Cuándo |
|---|---|---|
| — | `IN_REVIEW` | El archivo no se pudo leer, un dato quedó en duda, o difiere de la tabla |
| — | `IN_REVIEW` | El proveedor no se pudo identificar, o no está en el padrón |
| — | `IN_REVIEW` | Repite `(proveedor, número)` con otro total |
| — | `REGISTERED` | Los cuatro datos con certeza y el proveedor identificado |
| `IN_REVIEW` | `REGISTERED` | Una persona confirmó el dato o asignó el proveedor |
| `REGISTERED` | `IN_REVIEW` | Se dejó sin efecto la asignación de grafía que la resolvía (RF-53) |

La última transición es la que se olvida: **volver a revisión es un estado válido**, no un error.

## Los dos `kind` nuevos de `triage`

La cola no cambia de forma: `ExceptionCase.kind` ya es texto libre y `payload` es `jsonb`.

| `kind` | Motivo que ve la persona | Qué lleva el `payload` |
|---|---|---|
| `invoice_doubtful_data` | "Un dato de la factura no se pudo leer con certeza" | La factura, el campo, lo que dijo cada fuente y el recorte |
| `invoice_supplier_unresolved` | "No se pudo saber de qué proveedor es" | La grafía, los candidatos del padrón, y si está fuera de él |

La regla que nace al resolver el segundo (`matcher` = la grafía normalizada, `decision` = el
proveedor) es exactamente lo que hace que RF-49 y RF-50 funcionen sin código nuevo en `triage`.

## Migración

`0009_invoices_and_suppliers.py`: tres valores al enum de secciones, tres tablas de `staging`, cinco
de `core`, dos enums nuevos —`invoice_status`, `alias_source`—, y los índices de arriba. Sin
`downgrade` destructivo: bajar borra tablas nuevas y nada más (`DB-01`).
