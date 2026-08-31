# Facturas y proveedores — Modelo de datos

<!-- ARTEFACTO INTERNO. Detalle de lo que plan.md resume. -->

**Feature:** 004-invoices-suppliers · **Fecha:** 2026-08-31

Escrito **contra el código**, no contra la intención: cada tabla lleva el archivo y la línea donde
está su modelo, y los nombres son los que existen. Tres tablas en `staging`, seis en `core` y ninguna
nueva en `raw`. **Tampoco hay tabla nueva en `triage`, pero la feature sí lo usa**: una fila de
`/facturas` que no se pudo ni tipar abre un caso de clase `unreadable_invoice_row` en la cola de
excepciones que ya existe, porque nada se descarta (Artículo II, RF-07). La versión anterior de este
documento decía que `triage` no participaba, y no era cierto — el handler que lo hace verdad se
escribió el 2026-08-31.

**Tres migraciones, no una.** La base la pone **`0011_invoices_and_suppliers.py`**, que trae de una
vez lo de 004, 005, 006 y 007 porque las cuatro specs se construyeron en la misma pasada; acá sólo
se describe la parte de 004. Después, **`0014_the_document_of_an_invoice.py`** suma el archivo y el
CUIT que a veces trae impreso (RF-04, RF-11), y **`0015_an_arrival_is_not_a_reread.py`**, de qué
lectura vino cada factura (RF-39). Las cinco columnas que agregan están marcadas abajo, cada una en
su tabla.

## `raw` — sin tabla nueva

`raw.portal_document` ya guarda cualquier documento del portal con su hash. Esta feature suma tres
valores al enum `PortalSection` (`backend/app/modules/portal/models.py:28-30`) y nada más:

| Valor | Qué guarda |
|---|---|
| `INVOICES` (`"invoices"`) | La pantalla `/facturas` renderizada, con sus 100 filas |
| `INVOICE_FILE` (`"invoice-file"`) | El archivo de **una** factura, tal como se descargó: PDF, PDF escaneado o `.xlsx` |
| `SUPPLIER_LEDGER` (`"supplier-ledger"`) | La pantalla `/estado-cuenta` con las ocho filas ya expandidas |

Una fila por archivo de factura, no un blob por corrida: es lo que permite volver a leer una sola
factura cuando cambie el motor de OCR, sin tocar las otras noventa y nueve (Artículo III).

---

## `staging.invoice_row` — lo que dijo la tabla del portal

`backend/app/modules/ingestion/models.py:167`

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `int` PK | |
| `raw_document_id` | `int`, indexada | La pantalla de la que salió |
| `batch_id` | `int` | De la secuencia de `staging`, como la lista de precios |
| `line_number` | `int` | La fila dentro de la tabla, para poder señalarla |
| `number` | `varchar(64)` NULL | `F-9936` |
| `supplier_text` | `varchar(255)` NULL | **La grafía tal como vino**, sin normalizar. Es el insumo de RF-10 |
| `issued_on` · `due_on` | `date` NULL | La tabla las publica en ISO |
| `total` · `paid` · `balance` | `numeric(14,4)` NULL | La tabla publica `$223.376`: el punto es separador de miles |
| `receipt_issued` | `boolean` | Columna *Recibo emitido* — la lee **005** |
| `portal_payment_status` | `varchar(50)` NULL | Lo que el portal **dice** del pago. Nunca decide; lo lee **005** |
| `file_kind` | `varchar(50)` NULL | `PDF`, `PDF (escaneado)`, `Excel` — la columna *Tipo* (RF-05) |
| `product_code` | `varchar(64)` NULL | Columna *Producto/insumo* |
| `status` | enum `staging.row_status` | `VALID` o `QUARANTINED`, el enum que ya existía |
| `reason` | `varchar(200)` NULL | Por qué se apartó |
| `excerpt` | `text` NULL | La fila entera como texto, para mostrarla |
| `created_at` | `timestamptz` | |

Índices: `ix_invoice_row_batch_status (batch_id, status)` y `ix_invoice_row_number (number)`.

**Lleva más de lo que 004 necesita, a propósito.** La pantalla se lee una vez y se tipa una vez;
interpretarla otra vez para 005 serían dos verdades sobre la misma fila.

## `staging.invoice_file_read` — lo que dijo el archivo

`backend/app/modules/ingestion/models.py:211`

Una fila **por archivo leído**, no por campo: la señal que decide es una sola y es del documento
entero.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `int` PK | |
| `raw_document_id` | `int`, indexada | El archivo del que salió |
| `invoice_number` | `varchar(64)`, indexada | Con qué factura se lo asoció al descargarlo |
| `readable` | `boolean` | Si algún lector sacó texto |
| **`agrees`** | `boolean` | **La columna que decide.** Si el archivo y la tabla dicen lo mismo, el dato es certeza; si difieren, o el archivo no se pudo leer, la factura va a revisión (RF-27, RF-29) |
| `number` · `issued_on` · `total` · `supplier_text` | | Lo que leyó el documento, campo por campo |
| `tax_id` | `varchar(20)` NULL | **El CUIT del emisor**, cuando el documento imprime uno que no es el de Cordillera. Es de dónde sale RF-11: la lista de facturas del portal no publica CUIT, así que el número sólo existe acá, y llega después de la fila. El lector descarta el de la línea del cliente |
| `reason` | `varchar(200)` NULL | Por qué no se pudo leer |
| `excerpt` | `text` NULL | El texto del que salieron los datos, recortado a 2000 caracteres (RF-30) |
| `created_at` | `timestamptz` | |

**No hay columna de confianza, y es deliberado.** La lógica está en `agrees_with`
(`ingestion/documents.py:85`), que decide tres cosas: un campo que el documento **no trae** no es
desacuerdo —es una confirmación menos—; un documento que **no confirmó nada** tampoco es acuerdo; y
**el proveedor no entra en la comparación**, aunque se lea y se guarde. Eso último es coherente con
que identificar al proveedor sea trabajo de `purchases` contra el padrón, y hay que saberlo: un
archivo que nombra a otro proveedor **no** manda la factura a revisión por sí solo.

**Tampoco hay columna `reader`.** El motor con el que se leyó no se guarda: `read_invoice_document`
prueba los tres en el orden que sugiere `file_kind` y devuelve el primero que dio texto
(`documents.py:108-124`). Reprocesar "sólo lo que leyó el motor viejo" hoy no se puede: se reprocesa
por `file_kind`.

## `staging.supplier_row` — lo que dijo el padrón

`backend/app/modules/ingestion/models.py:246`

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `int` PK · `raw_document_id` `int` indexada · `line_number` `int` | |
| `legal_name` | `varchar(255)` NULL | Razón social, como la publica el portal |
| `tax_id` | `varchar(20)` NULL | El CUIT del proveedor |
| `email` | `varchar(255)` NULL · `phone` `varchar(50)` NULL | Del detalle expandido |
| `payment_term_days` | `int` NULL | 30, 45 o 60. El portal lo escribe `45 dias` |
| `balance` | `numeric(14,4)` NULL | El saldo que publica la cuenta corriente |
| `status` · `reason` · `excerpt` · `created_at` | | Igual que las otras dos: nada se descarta |

El **domicilio** que el portal también publica **no se guarda**: la spec firmada pide cinco campos y
no lo incluye.

En la misma pasada, el parser separa de esa pantalla los movimientos de cuenta corriente hacia
`staging.payment_row`, que es de **005** (`ingestion/service.py:494-545`).

---

## `core.supplier` — el padrón

`backend/app/modules/purchases/models.py:118`

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `int` PK | |
| `legal_name` | `varchar(255)` **UNIQUE** | RF-15. Es también la clave con la que `put_supplier` reconoce a un proveedor que vuelve |
| `tax_id` | `varchar(20)` UNIQUE NULL | Único cuando está: dos proveedores con un CUIT es el portal contradiciéndose. Nulo si el portal no expandió la fila |
| `email` | `varchar(255)` NULL · `phone` `varchar(50)` NULL | Nulo se muestra como *falta*, no como vacío (RF-20) |
| `payment_term_days` | `int` NULL | Valor inicial del portal, corregible (RF-16). Es de lo único que se deriva un vencimiento (**005**, **006**) |
| `balance` | `numeric(14,4)` NULL | El saldo del portal. Lo lee **005** |
| `created_at` · `updated_at` | `timestamptz` | |

Índice: `ix_supplier_legal_name`.

Ocho filas, y sólo se crean leyendo el padrón: **nada más da de alta un proveedor** (RF-14). El único
llamador de `put_supplier` es `remember_suppliers` (`service.py:207`), que corre desde el handler de
`SuppliersNormalized`.

**Un campo que el padrón no publicó esta vez se deja como está, no se blanquea**
(`repository.py:82-89`): una fila que el portal no expandió no dice nada nuevo, y nada no es lo mismo
que vacío.

## `core.supplier_alias` — las grafías

`backend/app/modules/purchases/models.py:154`

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `int` PK | |
| `supplier_id` | `int` FK → `core.supplier.id` `ON DELETE RESTRICT`, indexada | |
| `text_normalized` | `varchar(255)` **UNIQUE** | La grafía pasada por `normalize_entity_name` de `app/shared/text.py`. Única: la misma grafía no puede apuntar a dos proveedores, y **esa es toda la garantía de RF-50** |
| `text_original` | `varchar(255)` | La grafía tal como llegó |
| `source` | enum `core.supplier_alias_source` | `OBSERVED` — coincidió con certeza contra el padrón — o `LEARNED` — una persona la asignó (RF-47) |
| `created_by_user_id` | `int` NULL | Quién la decidió (RF-51). Nulo para las `OBSERVED` |
| `created_at` | `timestamptz` | Cuándo |
| `rule_id` | `int` NULL, indexada | **Columna muerta.** Es el resto del diseño anterior, que apoyaba las grafías en las reglas de `triage`. Ningún llamador de `put_alias` la pasa: siempre queda `NULL` |

**Lo que reemplazó a `rule_id`** es `core.invoice.resolved_by_alias_id`: la reversión de una
asignación (RF-53) alcanza a las facturas que esa asignación resolvió, y se pregunta desde la
factura, no desde la regla.

## `core.invoice` — la factura

`backend/app/modules/purchases/models.py:185`

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `int` PK | |
| `number` | `varchar(64)` **NOT NULL** | |
| `issued_on` | `date` **NOT NULL** | |
| `total` | `numeric(14,4)` **NOT NULL** | |
| `supplier_id` | `int` FK NULL, indexada | **Nulo mientras no esté identificado**, y por eso el índice de duplicado no la alcanza (RF-40) |
| `supplier_text` | `varchar(255)` | La grafía con la que llegó. Es lo que muestra la revisión y sobre lo que matchea una asignación |
| `review_state` | enum `core.invoice_review_state` | `OK` · `PENDING` · `RESOLVED`, default `OK` |
| `review_reason` | `varchar(200)` NULL | En español, porque lo lee una persona: *"No pudimos identificar con certeza al proveedor"*, *"El proveedor no está en el padrón"*, *"Ya había una factura con ese número y otro monto"*, *"El archivo de la factura no coincide con lo que informa el portal"*, *"No se pudo leer el archivo de la factura"* (`service.py:120-124`) |
| `resolved_by_user_id` · `resolved_at` | | Quién resolvió y cuándo (RF-32). Viajan en `InvoiceRead`, y el nombre lo resuelve la ruta con `ActorDirectory`, igual que la bitácora |
| `resolved_by_alias_id` | `int` NULL, indexada | Qué asignación guardada la resolvió. Es lo que hace exacta la reversión (RF-53): alcanza lo que esa decisión resolvió y nunca una factura que alguien decidió una por una |
| `arrival_count` | `int` default 1 | Cuántas veces llegó la misma (RF-39) |
| `last_batch_id` | `int` NULL | **De qué lectura vino la última vez.** Es lo que hace que un arribo sea el portal publicando la factura dos veces en la misma lectura y no la pantalla releída: sin esta columna, `arrival_count` contaba relecturas y con la sincronización cada 12 h todas las facturas «llegaban» dos veces por día |
| `file_kind` | `varchar(50)` NULL | El formato, para RF-05 |
| `staging_row_id` | `int` NULL | De qué fila de `staging` salió |
| `due_on` · `original_due_on` · `portal_paid` · `portal_payment_status` · `portal_receipt_issued` · `product_code` | | **De 005 y 006.** Están en la misma tabla porque son la misma entidad |
| `created_at` | `timestamptz` | |

**Índice único parcial `uq_invoice_supplier_number`** sobre `(supplier_id, number)` con
`WHERE supplier_id IS NOT NULL`: la clave de duplicado firmada, y la razón por la que dos facturas
sin proveedor no se pisan.

**Índices de búsqueda** (H8): `ix_invoice_issued_on`, `ix_invoice_number`, `ix_invoice_review_state`,
más `ix_core_invoice_supplier_id`, `ix_core_invoice_due_on` y `ix_core_invoice_resolved_by_alias_id`.
La búsqueda por CUIT y por razón social entra por el `LEFT JOIN` a `core.supplier`, que sólo se agrega
cuando hay algo que buscar (`repository.py:340-368`). **No hay índice sobre `total`**: el orden por
monto (RF-45) es un `ORDER BY` sin índice, y con cien facturas eso alcanza.

**Tres columnas `NOT NULL` y no cuatro.** Número, fecha y total no admiten nulo; el **proveedor sí**.
Una factura sin proveedor resuelto es una factura registrada esperando a una persona, no una
descartada. La otra mitad de RF-35 la sostiene `ingestion`, que no normaliza una fila sin número,
fecha o total (`ingestion/service.py:406-410`).

## `core.invoice_document` — el archivo, y si coincidió

`backend/app/modules/purchases/models.py:262`

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `int` PK | |
| `invoice_id` | `int` FK → `core.invoice.id` `ON DELETE CASCADE`, **UNIQUE** | Uno por factura |
| `raw_document_id` | `int` NULL | El archivo en `raw`, para poder volver a él |
| `readable` · `agrees` | `boolean` | La señal, ya decidida en `staging` |
| `excerpt` | `text` NULL | El recorte que ve quien revisa (RF-30) |
| `reason` | `varchar(200)` NULL | |
| `read_number` · `read_issued_on` · `read_total` · `read_supplier_text` | | Lo que dijo el archivo, al lado de lo que dijo la tabla |
| `read_supplier_tax_id` | `varchar(20)` NULL | El CUIT que el archivo imprimió (RF-11). Identifica sólo si coincide con uno de los ocho del padrón, donde Cordillera no está |
| `content` · `content_type` | `bytea` NULL · `varchar(120)` NULL | **El archivo tal como llegó** (RF-04). Es una copia deliberada de lo que ya está en `raw.portal_document`, no un atajo: `raw` es de `portal` y este módulo no puede leer sus tablas (Artículo IV). Lo que la constitución prescribe para este caso es una proyección propia alimentada por eventos, y es esta columna. `raw` sigue siendo la evidencia y sigue sin tocarse (Artículo III). No se rellena hacia atrás: un documento leído antes de la migración `0014` no tiene sus bytes, y pedir el archivo contesta que todavía no está en lugar de servir uno vacío |
| `created_at` | `timestamptz` | |

Vive en `core` y no sólo en `staging` porque es lo que la pantalla de una factura le muestra a una
persona: la evidencia sobre la que se toma la decisión.

**No hay columna `field_origin` en `jsonb`.** El origen por campo no se guarda: la señal es del
documento entero (`agrees`), y los cuatro `read_*` dejan ver de dónde salió cada número sin un JSON
que haya que interpretar.

## `core.purchase_correction` — la corrección de contacto

`backend/app/modules/purchases/models.py:569`

Las columnas salen del mixin `CorrectionColumns` de `app/shared/corrections.py:88`, **sin inventar
nada**: `entity_type`, `entity_id`, `field`, `portal_value`, `corrected_value`, `reason_code`,
`reason_detail`, `corrected_by_user_id`, `corrected_at`, `status`, `conflict_value`,
`conflict_detected_at`, `reverted_by_user_id`, `reverted_at`.

Lo único propio es el nombre de la tabla y su índice único parcial `uq_purchase_correction_in_force`
sobre `(entity_type, entity_id, field)` con `WHERE status <> 'REVERTED'`.

Cubre RF-16 a RF-19: la corrección gana sobre el portal, `portal_value` queda guardado para poder
deshacer, y cuando el portal trae otro valor la fila pasa a `CONFLICTED` en vez de perderse
(`service.py:270-325`). Los campos corregibles son tres: `email`, `phone`, `payment_term_days`.

## `core.purchase_setting` — los parámetros que este módulo lee

`backend/app/modules/purchases/models.py:546`

`key` (PK), `value` (`jsonb`), `updated_at`. Es la **proyección** del módulo: los parámetros son de
`operations` y `purchases` no puede leer su tabla (Artículo IV), así que guarda los que le importan,
alimentado por `BusinessParameterChanged`. De 004, el único es
**`supplier_match.threshold_pct`** (inicial 92). Hasta que alguien lo mueva, el servicio cae al valor
inicial de `shared/parameters.py`, que es lo que hace que una instalación nueva se comporte como una
configurada.

---

## Máquina de estados de una factura

Los estados reales son tres —`OK`, `PENDING`, `RESOLVED`— y no dos. `RESOLVED` existe para poder
distinguir una factura que nunca necesitó a nadie de una que alguien tuvo que mirar; para los totales
las dos cuentan igual, y sólo `PENDING` queda afuera (`service.py:1030-1040`).

| Desde | Hacia | Cuándo | Dónde |
|---|---|---|---|
| — | `OK` | Los cuatro datos y el proveedor identificado | `_create_invoice` (`service.py:567`) |
| — | `PENDING` | El proveedor no se pudo identificar, o no está en el padrón | `_create_invoice`, con `review_reason` |
| `OK` | `PENDING` | El archivo no se pudo leer, o no coincide con la tabla | `record_document` (`service.py:688-691`) |
| `OK` | `PENDING` | Repite número con **otro** total | `_count_arrival` (`service.py:625-631`) |
| `PENDING` | `RESOLVED` | Una persona asignó el proveedor, o dijo que la factura está bien como está | `resolve_invoice` (`service.py:850`) · `_attach` (`service.py:991`) |
| `PENDING` | `RESOLVED` | Se guardó una grafía que alcanza a esta factura (RF-49) | `_apply_alias` (`service.py:979`) |
| `RESOLVED` | `PENDING` | Se dejó sin efecto la grafía que la resolvía (RF-53) | `drop_alias` (`service.py:954-977`) |

**La última es la que se olvida: volver a revisión es un estado válido**, no un error. Y tiene una
asimetría deliberada: al volver, la factura pierde `supplier_id`, `resolved_*` y recupera el motivo
*proveedor ambiguo* — una factura que alguien decidió una por una no lleva `resolved_by_alias_id` y
**no vuelve**.

`diagrams/estados-factura.mmd` dibuja esto en el vocabulario del cliente y **le falta esa última
transición**. Es una diferencia entre dos documentos, no entre el documento y el código.

## Qué **no** hay, contra lo que un lector supondría

- **Ningún `kind` nuevo en `triage`.** La cola de excepciones no participa de esta feature. La
  revisión de facturas es `core.invoice.review_state` y la sirve `GET /invoice-review`.
- **Ninguna regla de `triage`** detrás de las grafías. La retroactividad y la reversión están
  enteramente en `purchases`, sobre `resolved_by_alias_id`.
- **Ninguna tabla propia para el log de cambios manuales.** RF-18 se resuelve publicando
  `ManualChangeRecorded`, que `operations` guarda.
