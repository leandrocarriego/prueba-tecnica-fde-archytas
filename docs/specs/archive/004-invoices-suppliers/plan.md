# Facturas y proveedores — Plan técnico

<!--
  ARTEFACTO INTERNO. Acá van las decisiones técnicas que spec.md no puede llevar.
  No se exporta al cliente.
-->

**Feature:** 004-invoices-suppliers · **Spec aprobada el:** 2026-08-29 · **Fecha:** 2026-08-31
**Roles:** Backend-Architect (dueño) · Frontend-Architect (pantallas)

Insumos: `spec.md` firmada (RF-01 a RF-53), `research.md` (la decisión de lectura, medida), el
relevamiento del portal del 2026-08-29 y 2026-08-30 —cuyos fixtures están en
`backend/tests/fixtures/portal/`— y `data-model.md`, que lleva el detalle de las tablas.

> **Este plan se escribió después de la implementación**, junto con los de la 005, 006 y 007, que
> se construyeron en una sola pasada. No finge lo contrario: describe **lo que hay en el árbol**,
> verificado archivo por archivo, para que el Developer, el Tester y el Code-Reviewer lean algo que
> corresponde al código y para que `/converge` pueda contrastarlo contra lo firmado. Toda afirmación
> de acá abajo lleva su `archivo:línea`.

> **Revisión del 2026-08-31, después del `/converge`.** El converge corrió, dio **deriva mayor** y
> su informe está en `converge.md`. Encontró tres requisitos firmados sin implementar —uno de ellos,
> **RF-31**, que este plan daba por cumplido— y once más a medias. **El humano decidió implementar
> los catorce**, y están implementados: lo que sigue describe el árbol después de eso.
>
> La sección *Lo que no cierra contra la spec firmada* de la versión anterior listaba trece
> defectos. **Ninguno queda abierto**, y esa sección se conserva más abajo como registro de qué
> eran y cómo se cerró cada uno — no se borra, porque un hallazgo borrado es un hallazgo que nadie
> vuelve a poder auditar. Lo que hay que saber al leer el resto del documento:
>
> - **D-2 y D-13 los cerró el commit `8e40cf3`**, antes del converge: Tesseract entró al Dockerfile
>   y al CI, y `conftest.py` tiene el fixture `queued_invoice_files` que faltaba. La suite corre
>   entera.
> - **D-1, D-3, D-4, D-5 y D-6 a D-12 se cerraron el 2026-08-31**, y con ellos el hallazgo que el
>   converge agregó sobre RF-31. Las migraciones `0014` y `0015` son de ese trabajo.
> - **Dos afirmaciones del cuerpo de este plan quedaron viejas y se corrigieron en su lugar**: ya
>   **no** es cierto que «no hay camino por CUIT» ni que `GET /invoices/{id}/file` devuelva el
>   recorte.

## Constitution Check

| Artículo | Cumple | Cómo |
|---|---|---|
| I — El origen es ajeno y de sólo lectura | ✅ | `portal` sólo navega y lee, con Playwright y sobre la pantalla renderizada: `fetch_invoices` (`portal/client.py:237`), `fetch_supplier_ledger` (`:253`, ocho clicks para expandir las ocho filas, sin cambio de URL) y `download_invoice_file` (`:284`, el click que genera el enlace y la descarga en el mismo contexto). Ninguna escritura, ningún endpoint JSON interno |
| II — Nada se descarta | ✅ | Lo que no se pudo leer va a `staging` en cuarentena (`ingestion/service.py:380-388`, `RowStatus.QUARANTINED`) y lo que no se pudo decidir queda como factura `PENDING`, contada y visible en `GET /invoice-review`. **La grieta que este documento declaraba está cerrada**: `InvoiceRowsQuarantined` ya tiene oyente —`triage/handlers.py::open_unreadable_invoice_rows`—, que abre un caso de clase `unreadable_invoice_row`, igual que sus dos hermanas del lado de los precios desde la 001. Lo único que se puede hacer con ese caso es verlo y darlo por revisado: una factura nace de una fila que el portal publicó, y cargarla a mano desde la cola es lo que la spec dejó fuera de alcance |
| III — Flujo unidireccional, `raw` inmutable | ✅ | `raw.portal_document` guarda la tabla, cada archivo de factura y la pantalla del padrón con su hash; tres valores nuevos de `PortalSection` (`portal/models.py:28-30`). Nada de esta feature actualiza `raw`; lo verifica `tests/architecture/test_raw_immutability.py` |
| IV — Las fronteras entre módulos son reales | ✅ | `purchases` no importa ningún otro módulo salvo `identity.dependencies`, que es la excepción fijada por nombre de archivo. Habla con `portal`, `ingestion`, `operations` y `notifications` por eventos del catálogo compartido, y con el worker por **nombre de task** sobre el broker (`operations/service.py:145`, `celery_task` como string) |
| V — Spec primero, y con firma | ✅ | `spec.md` en `Aprobado`, firmada por Leandro Carriego — FDE el 2026-08-29. **Este plan llegó después del código**, que es una desviación del proceso y está declarada arriba: no es una excepción a la constitución, es un plan que documenta en lugar de anticipar |
| VI — Lo que no está tipado y testeado no está terminado | ✅ | Tipos completos en `models`, `service`, `repository` y `routes`; unitarios de los tres lectores contra archivos fijados (`tests/unit/ingestion/test_invoice_documents.py`) e integración en `test_invoices_and_suppliers.py`, `test_invoice_search_and_order.py` y `test_invoice_identity_file_and_doubt.py`, con los fixtures del portal versionados (`TEST-03`). Los ocho fallos que este documento declaraba —siete por el broker, uno por Tesseract— los cerró el commit `8e40cf3`. Y `tests/architecture/test_invoice_screens_show_what_they_are_given.py` mecaniza el defecto que el converge encontró seis veces: que un requisito no está cumplido porque el backend devuelva el dato |
| VII — Las credenciales de terceros viven sólo en el entorno | ✅ | Se reusa el cliente de `portal`, que toma `PORTAL_USER` y `PORTAL_PASSWORD` de `settings` y nunca los deja salir en un traceback. Esta feature no agrega ninguna credencial |
| VIII — Un idioma para cada audiencia | ✅ | Código, eventos y modelos en inglés (`Invoice`, `Supplier`, `SupplierAlias`); los motivos de revisión que ve una persona, en español (`purchases/service.py:120-124`); pantallas y esta documentación, en español |
| IX — Las dependencias entran por la puerta | ✅ | Los cinco paquetes entraron con `uv` y están en `pyproject.toml` con su `uv.lock` (`pypdf`, `pytesseract`, `pillow`, `openpyxl`, `rapidfuzz`). El paquete de sistema que faltaba entró en los dos lugares donde hace falta: `backend/Dockerfile:16-18` y `.github/workflows/ci.yml:60-64` instalan `tesseract-ocr`, `tesseract-ocr-spa` y `tesseract-ocr-eng` |

**Excepciones solicitadas:** ninguna.

**Ningún ⚠️ queda.** Los tres que esta tabla tenía —la grieta del Artículo II, el VI y el IX— eran
defectos del estado de entonces, no excepciones pedidas, y están cerrados. Qué eran y cómo se
cerraron, en *Lo que no cierra contra la spec firmada*, más abajo.

## Enfoque

La feature es **el mismo pipeline de la 001 con tres orígenes nuevos y una lectura más difícil**.
`portal` trae, `ingestion` tipa, `purchases` se queda con lo del negocio. No hay arquitectura nueva:
hay tres secciones más enchufadas en la que ya funcionaba.

**De dónde sale cada dato, que es lo propio de esta feature.** Los cuatro datos de cabecera —número,
fecha, proveedor y total— **están en la tabla renderizada de `/facturas`**, completos en las 100
filas, y además adentro del archivo. Se leen los dos y se comparan (`ingestion/service.py:452-458`,
`documents.py:85` `agrees_with`):

- **Coinciden** → el dato es certeza y la factura entra sin molestar a nadie (RF-27).
- **Difieren, o el archivo no se pudo leer** → la factura pasa a `PENDING` con el motivo y el
  recorte a la vista (`purchases/service.py:688-691`, RF-29, RF-30).

Eso da gratis la señal que RF-27 pide sin inventar un umbral de confianza del OCR. Dos precisiones
que el código fija y conviene no volver a averiguar: **un campo que el documento no trae no es un
desacuerdo** —es una confirmación menos—, y **un documento que no confirmó nada tampoco es acuerdo**
(`documents.py:96-105`).

**El padrón sale de `/estado-cuenta`**, la única pantalla del portal que lo publica: ocho filas y, al
expandir cada una, CUIT, correo, teléfono y condición de pago. No hay sección `/proveedores`, así que
el extractor hace los ocho clicks sobre la misma pantalla (`portal/client.py:253-278`). Del detalle
expandido, `ingestion` separa dos cosas en la misma pasada: las fichas van a `SuppliersNormalized`
(esta feature) y los movimientos de cuenta corriente a `PaymentsNormalized` (**005**); la pantalla se
lee una vez porque interpretarla dos veces serían dos verdades (`ingestion/service.py:494-545`).

**La identificación del proveedor tiene dos caminos y ningún tercero**
(`purchases/service.py:436-489`): primero una **grafía ya conocida** —exacta, sobre el nombre
normalizado por `shared/text.py`— y después una **comparación contra el padrón** con `rapidfuzz`. La
comparación identifica sólo si supera el umbral **y** le saca margen al segundo; cualquier cosa por
debajo va a una persona. Una grafía que coincidió con certeza se guarda como `OBSERVED`, así la
próxima factura escrita igual no paga la comparación.

**El camino por CUIT existe y no está en `resolve_supplier`, y la razón no es la trampa sino el
momento.** La tabla de `/facturas` **no publica CUIT** —se buscó y no está—, así que el único lugar
del que puede salir es el archivo, y el archivo llega después de la fila que lo nombra. Por eso RF-11
se resuelve en `_identify_by_tax_id`, dentro de `record_document`: una factura que quedó esperando
porque su nombre no resolvió se identifica sola cuando su documento trae un CUIT del padrón, sin que
una persona la mire.

La trampa que el relevamiento midió —el único CUIT impreso suele ser el de **Cordillera**, el
cliente— queda cerrada dos veces, y son dos reglas distintas y no una repetida: el lector descarta
todo CUIT que esté en la línea del cliente (`documents.py::_issuer_tax_id_in`), y el servicio sólo
identifica si el número coincide con uno de los **ocho del padrón**, donde Cordillera no está. Sobre
los cuatro documentos fijados de hoy ningún archivo trae CUIT del emisor: el requisito es un
condicional y su antecedente es falso en este corpus, que no es lo mismo que no estar implementado.

**Tres mecanismos de la 003 se reusan enteros y no se reescriben:**

- **`CorrectionColumns` de `app/shared/corrections.py`** → `core.purchase_correction`
  (`purchases/models.py:569`) es la misma forma en la tabla de este módulo, con `portal_value`
  guardado para poder deshacer.
- **`ManualChangeRecorded`** → `operations` guarda quién cambió qué, cuándo y con qué valor anterior.
  Es RF-18 sin tabla propia (`purchases/service.py:1946`).
- **`CorrectionConflicted`** → cuando el padrón vuelve a leerse y trae otro valor sobre un campo
  corregido, la corrección gana y el conflicto se marca (`purchases/service.py:270-325`). Es RF-19.

**El módulo es uno solo.** La spec dice que facturas y proveedores son el mismo problema mirado desde
dos lados; partirlo obligaría a que uno mantuviera una proyección del otro para poder listar las
facturas de un proveedor, que es la pantalla central. Cuando respetar la frontera duele así, la
frontera está mal trazada.

## Módulos afectados

| Módulo | Qué cambia | Nuevo |
|---|---|---|
| `portal` | Tres lecturas nuevas: `extract_invoices`, `extract_supplier_ledger` y `extract_invoice_file` (`portal/service.py:144,162,239`), con sus tasks (`portal/tasks.py:169,176,204`). Un handler nuevo, `bring_invoice_files` (`portal/handlers.py:38`), que encola una descarga por factura registrada, espaciadas | No |
| `ingestion` | Los parsers de la tabla de facturas y del padrón (`parsers.py`), el lector de archivos `documents.py` —`pypdf`, Tesseract, `openpyxl`— y tres tablas de `staging` (`ingestion/models.py:167,211,246`). Compara archivo contra tabla y publica el resultado | No |
| `purchases` | **Todo lo del negocio**: padrón, grafías, facturas, documento leído, correcciones de contacto, totales por período, cola de revisión | **Sí** |
| `operations` | Dos parámetros nuevos —`invoice_sync.interval_hours` y `supplier_match.threshold_pct` (`shared/parameters.py:270,286`)— y dos entradas en `SYNC_JOBS` que despachan las extracciones por nombre de task (`operations/service.py:145-165`). Recibe `ManualChangeRecorded` | No |
| `identity` | Nada propio: se monta su `dependencies.py` y se usan las secciones `SUPPLIERS` y `PURCHASE_INVOICES`, que ya existían con ventas en `NONE` (`identity/permissions.py:78-79`) | No |
| `notifications` | Nada propio de 004: ya escuchaba `CorrectionConflicted` (`notifications/handlers.py:93`) y avisa también los de proveedor, sin una línea nueva | No |
| `messaging` | Se suscribe a `SuppliersNormalized` para su propia proyección (`messaging/handlers.py:27`). Es **007** consumiendo un evento de esta feature, no un cambio de esta | No |
| `triage` | **Nada. Ni una línea.** La cola de excepciones no participa de esta feature: la revisión de facturas es `purchases`. Ver *Lo que no cierra*, D-1 | No |

**Por qué `purchases` y no `suppliers` + `invoices`.** Ver *Enfoque*. Consecuencia que hay que saber
al leer el módulo: `purchases` también aloja **005** (pagos y recibos), **006** (calendario) y
**007** (órdenes de compra), que llegaron en la misma pasada. `models.py` tiene doce clases y
`service.py` casi dos mil líneas; **de eso, 004 es lo que esta página nombra y nada más**.

## Eventos de dominio

Verificado uno por uno contra el `@events.subscribe` que lo escucha, no contra el catálogo. La
columna *Lo consume* dice **quién está suscripto hoy**, no quién debería.

| Evento | Lo publica | Lo consume | Qué lleva |
|---|---|---|---|
| `InvoiceListExtracted` | `portal/service.py:144` | `ingestion/handlers.py:72` | `raw_document_id`, `content` (la pantalla), `fetched_at`, `job_run_id` |
| `InvoiceFileExtracted` | `portal/service.py:239` | `ingestion/handlers.py:82` | `raw_document_id`, `invoice_number`, `content`, `content_type`, `file_kind` |
| `SupplierLedgerExtracted` | `portal/service.py:162` | `ingestion/handlers.py:96` | `raw_document_id`, `content` (la pantalla ya expandida), `job_run_id` |
| `SuppliersNormalized` | `ingestion/service.py:533` | `purchases/handlers.py:44` · `messaging/handlers.py:27` | Las ocho fichas: razón social, CUIT, correo, teléfono, plazo pactado, saldo |
| `InvoicesNormalized` | `ingestion/service.py:414` | `purchases/handlers.py:50` | `batch_id` y las filas tipadas de la tabla. Lleva también lo que lee **005** —pagado, saldo, estado de pago del portal, recibo emitido—: la pantalla se lee una vez |
| `InvoiceFileRead` | `ingestion/service.py:474` | `purchases/handlers.py:58` | Lo que dijo el archivo: `readable`, **`agrees`**, `excerpt`, `reason` y los cuatro campos leídos. Es la señal sobre la que descansa RF-27 |
| `InvoicesRegistered` | `purchases/service.py:555` | `portal/handlers.py:38` (baja los archivos) · `purchases/handlers.py:81` (imputa lo que esperaba, **005**) | `invoice_id`, `supplier_id`, número, fecha, total, vencimiento |
| `ManualChangeRecorded` | `purchases/service.py:1946` | `operations/handlers.py:57` | RF-18: quién, cuándo, qué campo, valor anterior y nuevo, motivo. Sin tabla propia |
| `CorrectionConflicted` | `purchases/service.py:304` | `notifications/handlers.py:93` | RF-19: la corrección gana y el conflicto se avisa por WhatsApp |
| `BusinessParameterChanged` | `operations` | `purchases/handlers.py:103` | Alimenta la proyección `core.purchase_setting` con `supplier_match.threshold_pct` |
| `InvoiceRowsQuarantined` | `ingestion/service.py:425` | `triage/handlers.py::open_unreadable_invoice_rows` | Filas de la tabla que no se pudieron tipar. Abre un caso de clase `unreadable_invoice_row` |
| `InvoicesNeedingReview` | `purchases/service.py:559` | `portal/handlers.py::bring_held_invoice_files` | Facturas apartadas. Cada caso dice si acaba de registrarse (`needs_document`), y sólo de ésas se baja el archivo |

**Los dos eventos que no tenían oyente ahora lo tienen, y no por la misma razón.**
`InvoiceRowsQuarantined` **era un agujero**: la única forma que tenía una fila incomprensible de
llegar a una persona, y no llegaba. Hoy abre un caso en `triage`, como sus dos hermanas del lado de
los precios desde la 001. `InvoicesNeedingReview` era inocuo —la cola de revisión no depende de él,
vive en `core.invoice.review_state`— y le llegó un oyente por otro motivo: es el único lugar desde
el que se sabe que una factura recién apartada todavía no tiene su archivo, y la apartada es
justamente la que más lo necesita (RF-30, y el CUIT de RF-11).

**Lo que un módulo NO consume, contra lo que un lector supondría:** `purchases` **no** está
suscripto a `QuarantineCaseResolved` ni a `QuarantineRuleRevoked` — esos dos los escuchan `ingestion`
y `catalog`, y son de la 001 y la 008. La retroactividad de una grafía (RF-49) y su reversión
(RF-53) están **enteramente dentro de `purchases`**: `_apply_alias` (`service.py:979`) y `drop_alias`
(`service.py:954`), sobre `core.invoice.resolved_by_alias_id`.

## Datos

El detalle está en **`data-model.md`**, alineado con el código. En una pantalla:

- **`raw`** — sin tabla nueva. Tres valores nuevos de `PortalSection`: `INVOICES`, `INVOICE_FILE` y
  `SUPPLIER_LEDGER` (`portal/models.py:28-30`). Una fila por archivo de factura, para poder releer
  una sola cuando cambie el motor de OCR.
- **`staging`** — `staging.invoice_row` (lo que dijo la tabla), `staging.invoice_file_read` (lo que
  dijo el archivo, con `agrees`) y `staging.supplier_row` (`ingestion/models.py:167,211,246`).
- **`core`** — `core.supplier`, `core.supplier_alias`, `core.invoice`, `core.invoice_document`,
  `core.purchase_correction` y `core.purchase_setting` (`purchases/models.py:118,154,185,262,569,546`).
- **Migración `0011_invoices_and_suppliers.py`**, que trae de una vez lo de 004, 005, 006 y 007
  porque las cuatro se construyeron juntas. Sus enums de esta feature: `invoice_review_state`
  (`OK`/`PENDING`/`RESOLVED`) y `supplier_alias_source` (`OBSERVED`/`LEARNED`).

**La clave de duplicado es *(proveedor, número)*, como se firmó**, y está implementada como índice
único parcial `uq_invoice_supplier_number` con `WHERE supplier_id IS NOT NULL`
(`purchases/models.py:196-207`): mientras el proveedor no está resuelto, el índice no la alcanza y la
factura no puede ser duplicada de nadie (RF-40).

## Contratos

Toda ruta declara su autorización con `require_section` de `identity.dependencies` (`PY-09`,
**Blocker**, verificado por `tests/architecture/test_route_authorization.py`). Ventas tiene
`Level.NONE` en las dos secciones que esta feature usa (`identity/permissions.py:78-79`), así que
**RF-06 y RF-36 no dependen de que ninguna ruta se acuerde de excluirlo**: la matriz lo hace.

Prefijo de la API: `API_PREFIX` de `app/main.py`. Los cuatro routers se registran en
`main.py:251-254`. Las rutas de pagos, recibos, calendario y órdenes que viven en el mismo
`routes.py` **no son de esta feature** y no están acá.

| Ruta | Sección · nivel | Quién entra | Requisitos | Dónde |
|---|---|---|---|---|
| `GET /invoices` | `PURCHASE_INVOICES` · READ | dueño · compras | RF-03, RF-05, RF-32, RF-39, RF-41 a RF-46 | `routes.py:86` |
| `GET /invoices/{id}` | `PURCHASE_INVOICES` · READ | dueño · compras | RF-03, RF-27, RF-32, RF-39 | `routes.py:130` |
| `GET /invoices/{id}/file` | `PURCHASE_INVOICES` · READ | dueño · compras | RF-04 — los bytes como llegaron, desde la copia propia del módulo | `routes.py:615` |
| `GET /suppliers` | `SUPPLIERS` · READ | dueño · compras | RF-08, RF-24 | `routes.py:205` |
| `GET /suppliers/{id}` | `SUPPLIERS` · READ | dueño · compras | RF-10, RF-15, RF-20 | `routes.py:215` |
| `PATCH /suppliers/{id}` | `SUPPLIERS` · **WRITE** | dueño · compras | RF-16, RF-17, RF-18, RF-19 | `routes.py:225` |
| `GET /suppliers/{id}/invoices` | `PURCHASE_INVOICES` · READ | dueño · compras | RF-21 | `routes.py:254` |
| `GET /suppliers/{id}/totals` | `SUPPLIERS` · READ | dueño · compras | RF-22, RF-23 | `routes.py:269` |
| `GET /invoice-review` | `PURCHASE_INVOICES` · **WRITE** | dueño · compras | RF-30, RF-34 | `routes.py:290` |
| `POST /invoice-review/{id}/resolve` | `PURCHASE_INVOICES` · **WRITE** | dueño · compras | RF-31, RF-32, RF-33, RF-36 | `routes.py:302` |
| `GET /supplier-aliases` | `SUPPLIERS` · READ | dueño · compras | RF-51 | `routes.py:328` |
| `POST /supplier-aliases/preview` | `SUPPLIERS` · **WRITE** | dueño · compras | RF-48 | `routes.py:338` |
| `POST /supplier-aliases` | `SUPPLIERS` · **WRITE** | dueño · compras | RF-47, RF-49, RF-50 | `routes.py:352` |
| `DELETE /supplier-aliases/{id}` | `SUPPLIERS` · **WRITE** | dueño · compras | RF-52, RF-53 | `routes.py:367` |

Esta tabla llevaba **⚠** en cuatro filas, y el símbolo quería decir algo muy preciso: *la ruta
cumple y la pantalla no la usa*. No queda ninguno. La lección que dejó vale más que los cuatro
casos y por eso está mecanizada:
`tests/architecture/test_invoice_screens_show_what_they_are_given.py` falla si un campo que un
requisito firmado necesita deja de leerse en la pantalla que ese requisito nombra.

**Dos decisiones de autorización que hay que ver.** `GET /invoice-review` pide **WRITE** aunque sea
una lectura: la cola es una lista de trabajo, y quien no puede resolver no tiene por qué mirarla
(RF-36). Y `RF-17` —no editar razón social ni CUIT— **no se defiende con una regla en el servicio**:
`SupplierContactWrite` (`schemas.py:89`) sólo tiene `email`, `phone` y `payment_term_days`, así que
el contrato no admite el campo. Es la forma más barata de sostenerlo y hay que saber que está ahí.

**Pantallas** (`frontend/app/(private)/`):

| Pantalla | Requisitos |
|---|---|
| `facturas/page.tsx` + `InvoiceFilters.tsx`, `InvoiceTable.tsx` | RF-03, RF-05, RF-39, RF-41 a RF-46 — los filtros van en la URL, para que una pantalla filtrada se comparta filtrada. La columna **Formato** marca las escaneadas, que son las que el lector acierta menos (RF-05) |
| `facturas/[invoiceId]/page.tsx` + `InvoicePanel.tsx` | RF-04, RF-27, RF-30, RF-32 — el recorte al lado de lo que informó la tabla, el enlace al archivo original, y quién resolvió la factura |
| `facturas/revision/page.tsx` + `ReviewQueue.tsx` | RF-30, RF-31, RF-33, RF-34, RF-48 — los tres datos de cabecera se confirman dejándolos como están o se corrigen escribiéndolos |
| `proveedores/page.tsx` | RF-08, RF-24 |
| `proveedores/[supplierId]/page.tsx` + `SupplierContact.tsx`, `SupplierCorrection.tsx`, `SupplierPeriod.tsx` | RF-10, RF-15, RF-16, RF-19, RF-20, RF-21, RF-22, RF-23. El período viaja en la URL como los filtros de facturas; el botón de corregir sólo aparece para quien la ruta dejaría escribir |
| `proveedores/grafias/page.tsx` + `SpellingList.tsx` | RF-51, RF-52 — el nombre de quien la decidió lo resuelve la ruta con `ActorDirectory` |

No hay carpeta `contracts/`: **ninguna spec de este repositorio la tiene**, y la plantilla admite la
tabla en línea. Esta es la tabla.

## Cobertura de los requisitos firmados

Los 53 requisitos y dónde vive cada uno. Es lo que `/converge` audita, así que nombra el lugar y no
la intención. **Los 53 cierran**; los que no cerraban llevaban su número de hallazgo, y esos
hallazgos están en la sección final con lo que se hizo en cada uno.

| Requisitos | Dónde viven |
|---|---|
| RF-01 | `operations/service.py:145-165` — `SYNC_JOBS` con `invoice_sync.interval_hours`, y `portal/tasks.py:169,176` |
| RF-02 | `portal/service.py:239` — el archivo se guarda en `raw.portal_document` con su hash. Se baja para **toda** factura recién registrada: `bring_invoice_files` escucha `InvoicesRegistered` y `bring_held_invoice_files` escucha `InvoicesNeedingReview`, que es la que faltaba — la apartada es la que más necesita su archivo |
| RF-03 | `GET /invoices` (`routes.py:86`) e `InvoiceTable.tsx` |
| RF-04 | `GET /invoices/{id}/file` — los bytes con su `content_type` y `Factura F-8411.pdf` de nombre, servidos desde `core.invoice_document.content`, la copia propia del módulo. Enlace en la ficha y en la cola de revisión, a través del proxy autenticado del frontend |
| RF-05 | `file_kind` sale de la columna *Tipo* del portal, se guarda y viaja en `InvoiceRead`; la columna **Formato** de `InvoiceTable.tsx` lo imprime y marca las escaneadas (`labels.ts::fileKindLabel`, `isScanned`) |
| RF-06, RF-36 | `identity/permissions.py:78-79` — ventas en `NONE`; verificado por `tests/architecture/test_route_authorization.py` |
| RF-07 | La primera corrida de `SYNC_JOBS` procesa lo que ya está; lo apartado no bloquea. La fila que no se pudo tipar abre un caso en `triage` (`open_unreadable_invoice_rows`) en vez de quedarse en `staging` |
| RF-08, RF-24 | `remember_suppliers` (`service.py:207`) desde `SuppliersNormalized`; `SupplierList.total` y `proveedores/page.tsx:37` |
| RF-09 | `core.invoice.supplier_id` + `InvoiceRead.supplier_name` (`schemas.py:206`) |
| RF-10 | `core.supplier_alias` (`models.py:154`), una fila por grafía observada o decidida; `SupplierRead.aliases`, renderizadas en la ficha del proveedor |
| RF-11 | `_identify_by_tax_id` (`purchases/service.py`), y **no** en `resolve_supplier`: la tabla del portal no publica CUIT, así que el número sólo existe dentro del archivo y el archivo llega después de la fila. El lector descarta el CUIT que está en la línea del cliente (`documents.py::_issuer_tax_id_in`) y el servicio sólo identifica contra los ocho del padrón, donde Cordillera no está |
| RF-12, RF-13 | `resolve_supplier` (`service.py:436-489`): grafía exacta, después `rapidfuzz` con umbral y margen; lo no concluyente devuelve `AMBIGUOUS_SUPPLIER` |
| RF-14 | La misma función devuelve `OUTSIDE_REGISTER` y **nada crea un proveedor**: `put_supplier` sólo corre desde `remember_suppliers` |
| RF-15, RF-20 | `GET /suppliers/{id}` con `SupplierRead.missing` (`service.py:409`) y `proveedores/[supplierId]/page.tsx:62` |
| RF-16 | `PATCH /suppliers/{id}` (`routes.py:225`), la server action `correctSupplier` y `SupplierCorrection.tsx`, el diálogo de la ficha — el mismo que corrige un precio, con el motivo obligatorio que sale de la API |
| RF-17 | `SupplierContactWrite` (`schemas.py:89`) sólo admite tres campos, así que el contrato no deja tocar razón social ni CUIT |
| RF-18 | `ManualChangeRecorded` → `operations` (`service.py:1946`) |
| RF-19 | `_corrections_holding` + `_check_supplier_conflict` (`service.py:240-325`) y `SupplierContact.tsx:56` |
| RF-21 | `GET /suppliers/{id}/invoices` (`routes.py:254`) |
| RF-22, RF-23 | `supplier_totals` con `since`/`until`, y `SupplierPeriod.tsx`, que los pone en la URL con un atajo al año en curso. Lo excluido se cuenta **por motivo** —`excluded_in_review`, `excluded_inconsistent`, `excluded_out_of_period`— porque RF-23 pregunta por uno solo de los tres |
| RF-25, RF-26 | `ingestion/documents.py` `read_invoice_document`, con los tres lectores y el orden por `file_kind`. El binario de Tesseract está en el Dockerfile y en el CI |
| RF-27 | `agrees` (`documents.py:85`), guardado en `core.invoice_document.agrees` y expuesto en `InvoiceDocumentRead` |
| RF-28 | `read_invoice_document` devuelve `readable=False` con motivo; cada lector falla en su propio `try` y no frena a los demás (`documents.py:117-124`) |
| RF-29, RF-30 | `record_document` (`service.py:641`) pasa la factura a `PENDING` con el recorte; `facturas/[invoiceId]/page.tsx:76-85` |
| RF-31, RF-33 | `resolve_invoice` (`service.py:850`) → `RESOLVED`, y sale de `GET /invoice-review` |
| RF-32 | `core.invoice.resolved_by_user_id` / `resolved_at`, expuestos en `InvoiceRead`; el nombre lo resuelve `routes.py::_name_whoever_resolved` con `ActorDirectory`, y la ficha de la factura lo imprime |
| RF-34 | `InvoiceList.total` de `GET /invoice-review` y `facturas/revision/page.tsx:41` |
| RF-35 | `number`, `issued_on` y `total` son `NOT NULL` (`models.py:203-205`), y `ingestion/service.py:406-410` no normaliza una fila sin los tres |
| RF-37, RF-38, RF-40 | `invoice_of` (`repository.py:152`) con las dos identidades, `_count_arrival` (`service.py:610`) y el índice parcial `uq_invoice_supplier_number` |
| RF-39 | `core.invoice.arrival_count` y la leyenda «llegó N veces» de `InvoiceTable.tsx`. Un arribo es el portal publicando la factura **dos veces en la misma lectura**: `_count_arrival` compara `last_batch_id` contra el lote que llega, así que releer la pantalla no suma nada |
| RF-41 a RF-46 | `list_invoices` (`service.py:699`) y `_search` (`repository.py:340-368`), que busca número, grafía, razón social y CUIT sin guiones; `InvoiceOrder` (`models.py:92`) da los cuatro órdenes |
| RF-47, RF-48, RF-49 | `save_alias` (`service.py:924`) y `preview_alias` (`service.py:904`), que cuenta con **la misma consulta** que después resuelve |
| RF-50 | `alias_for` es lo primero que mira `resolve_supplier`; `text_normalized` es `unique` |
| RF-51 | `GET /supplier-aliases`, con `created_by_name` resuelto en la ruta, y `SpellingList.tsx`, que imprime «La asignó Fulano · fecha». Una grafía que el sistema reconoció solo no tiene autor y lo dice así |
| RF-52, RF-53 | `drop_alias` (`service.py:954`) sobre `invoices_resolved_by_alias` (`repository.py:207`): el alcance es exactamente lo que esa grafía resolvió |

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Dos módulos, `suppliers` e `invoices` | Obligaría a una proyección entre ellos para la pantalla central de la feature. La frontera estaría mal trazada, no bien defendida |
| Leer **sólo** el archivo, como suponía el relevamiento | La tabla del portal trae los cuatro datos completos en las 100 filas. Ignorarla sería tirar una lectura determinista y quedarse con la difícil |
| Leer **sólo** la tabla y no abrir los archivos | Tienta, pero el archivo es la evidencia que la revisión le muestra a la persona (RF-30) y la única fuente si el portal deja de publicar una columna |
| Un servicio pago de OCR, o un LLM por API | El cliente respondió que **no** acepta costo por documento. Detalle y medición en `research.md` |
| Un LLM local para las planillas irregulares | Buscar las etiquetas por nombre alcanza (`documents.py:180-196`). Sería pagar hardware por un problema resuelto |
| `PyMuPDF` para el texto de los PDF | **AGPL**: contamina un producto propietario del cliente. `pypdf` hace lo mismo con licencia BSD |
| Renderizar la página del PDF escaneado para pasarle el OCR | Segunda dependencia de sistema (Poppler o similar) para nada: un escaneado del portal es un JPEG por página, y la imagen embebida **es** la página. Se extrae con `pypdf` (`documents.py:146-153`) |
| Un umbral de confianza del OCR como única señal de RF-27 | La doble lectura contra la tabla da la señal sin inventarla, y es verificable: `agrees` es booleano y trazable, una confianza de 0,71 no le dice nada a nadie |
| Identificar al proveedor por **el primer** CUIT impreso en la factura | Es el de Cordillera y le asignaría el mismo proveedor a las cien. Lo que se hace en cambio es descartar el de la línea del cliente y aceptar sólo un CUIT que esté en el padrón |
| Leer el CUIT dentro de `resolve_supplier`, junto a los otros dos caminos | Sería un parámetro que ningún llamador puede llenar: `register_invoices` corre sobre la tabla, y la tabla no publica CUIT. Superficie muerta que sugiere un camino que nunca se recorre |
| Servir el archivo leyendo `raw.portal_document` desde `purchases` | Es el import cruzado que el Artículo IV prohíbe. El módulo mantiene su propia copia, que es lo que la constitución prescribe para una lectura entre módulos |
| Guardar la cola de revisión en `triage` | Se evaluó y no se hizo: la resolución de una factura mueve columnas de `core.invoice` —proveedor, vencimiento, entrada del calendario— que `triage` no puede tocar sin importar `purchases`. Costo aceptado: dos colas de revisión en el producto, y `InvoiceRowsQuarantined` sin destino (D-1) |
| Dar de alta un proveedor desde la pantalla de revisión | El cliente lo descartó explícitamente en el `/clarify`: el padrón se amplía como decisión del negocio |
| Guardar el domicilio del proveedor, que el portal publica | La spec firmada pide cinco campos y no lo incluye. `staging.supplier_row` tampoco lo guarda |

## Riesgos

| Riesgo | Impacto | Cómo se mitiga |
|---|---|---|
| El motor de OCR deja de estar instalado en un entorno nuevo | Alto — el 46% de las facturas no se leería | Está en `backend/Dockerfile` y en `.github/workflows/ci.yml`, y el test del PDF escaneado lo verifica en cada corrida: si el binario falta, `assert reading.readable` rompe el build en vez de dejar pasar 46 facturas mudas |
| Un handler que encola trabajo queda sin interceptar en la suite | Alto — los tests pasarían en la máquina con broker y fallarían en CI | `conftest.py` tiene `queued_invoice_files`, y es **autouse** justamente porque la task se encola desde un handler que ningún test llama a mano: un recorder que hay que acordarse de pedir sólo protege a quien ya sabía que la task existía |
| El OCR se midió sobre imágenes sintéticas limpias; una foto real no se parece | Alto — es el 46% de las facturas | `raw` es inmutable: cambiar de motor y reprocesar las cien no le pide nada al portal. Y lo dudoso ya va a revisión, no a la base |
| 24 grafías para 8 proveedores, y `rapidfuzz` puede acertar de más | Alto — un proveedor mal resuelto rompe la deuda y los totales, y no se nota desde afuera | Umbral en 92 y margen de 6 puntos sobre el segundo (`service.py:463-476`). En la duda, a una persona. Una asignación se puede dejar sin efecto y devuelve exactamente lo que resolvió |
| El padrón exige expandir ocho filas con click; si el portal cambia ese control, se rompe | Medio | Fixture fijado `suppliers-ledger-page-2026-08-29.html` y test contra él (`TEST-03`); el fallo levanta `ExtractionError`, se reintenta dos veces y queda en `JobRunFailed`, nunca en silencio |
| El enlace de descarga del portal caduca | Medio — se pierde el archivo de una factura | Se descarga dentro del mismo contexto que lo genera (`client.py:284-310`). Si igual falla, la factura queda registrada sin documento y la revisión lo muestra como ilegible |
| Cien facturas el primer día, cada una una visita a un sistema ajeno con cuenta compartida | Medio | `bring_invoice_files` las encola espaciadas por `PORTAL_HISTORY_SPACING_SECONDS` (`portal/handlers.py:49-53`); la lista queda usable desde el primer momento |
| `purchases` acumula cuatro specs y ya tiene ~2000 líneas de servicio | Medio — a la quinta, encontrar algo cuesta | Hoy la frontera correcta sigue siendo una: partir el módulo pediría una proyección. Si aparece una quinta capacidad, se discute antes de escribirla |
| Los diagramas describen conducta que el código ya no hace | Bajo — documento, no código | Se regeneraron el 2026-08-31 contra el código de después del converge: el camino por CUIT que dibujaban ahora existe, la corrección del dato en duda también, y `estados-factura.mmd` tiene la vuelta `Registrada → Apartada` de RF-53 que le faltaba |

## Contexto de traspaso

**Para el Developer** — Entrá por `purchases/service.py`, y entrá sabiendo que **el archivo tiene
cuatro specs adentro**: 004 es `remember_suppliers`, `resolve_supplier`, `register_invoices`,
`record_document`, `list_invoices`, `supplier_totals`, la familia `*_alias` y `correct_supplier`.
Todo lo que diga *payment*, *receipt*, *due date* o *order* es de 005, 006 y 007 y no se toca desde
acá.

Lo que **ya está decidido y no se rediscute**: la lectura es `pypdf` + Tesseract + `openpyxl`, sin
ningún modelo de lenguaje (`research.md`); el módulo es uno solo; las correcciones reusan
`CorrectionColumns` y los eventos de la 003; y **la identificación por CUIT no vive en
`resolve_supplier`** —la tabla del portal no publica ninguno, así que el número sólo existe dentro
del archivo y el archivo llega después de la fila: identifica `_identify_by_tax_id` cuando el
documento llega, y sólo contra los ocho del padrón—.

Lo que **no toques**: `raw` no se actualiza nunca; ningún import cruzado desde `purchases` (la única
línea legal hacia afuera es `identity.dependencies`, y está fijada por nombre de archivo en el test);
y **no muevas la identidad de una factura sin proveedor** —`invoice_of` usa *(supplier_text, number)*
justamente para que dos apartadas con el mismo número no se fusionen (RF-40)—.

**Nada de la lista de defectos queda abierto** — los catorce están cerrados y su cierre está al final
de este documento. Lo que sí conviene que sepas antes de tocar nada:

- **Una factura apartada baja su archivo**, y eso es de lo que dependen RF-30 y RF-11. Si algún día
  cambiás cómo se registran las facturas, `bring_held_invoice_files` es lo que hay que no romper.
- **`arrival_count` se cuenta por lote.** `last_batch_id` no es contabilidad interna: es lo único que
  distingue «el portal la publicó dos veces» de «releímos la pantalla». Un cambio en `_extract` que
  toque el hasheo de la pantalla se siente acá.
- **La copia del archivo en `core.invoice_document.content` es duplicación a propósito.** `raw` es de
  `portal` y no se lee desde acá; borrar la copia para «no duplicar» rompe RF-04.
- **Antes de dar por cumplido un requisito, abrí el `.tsx`.** Seis de los catorce hallazgos fueron el
  mismo error: el backend devolvía el dato y ninguna pantalla lo usaba.
  `tests/architecture/test_invoice_screens_show_what_they_are_given.py` ahora lo frena, y **esa lista
  hay que ampliarla cuando entre un requisito nuevo con pantalla**: una regla que no está escrita no
  protege nada.

**Para el Tester** — Cuatro cosas se rompen de verdad.

1. **La identificación del proveedor.** Probá una grafía exacta del padrón, una variante que entra
   sola, y dos razones sociales parecidas entre sí que tienen que ir a revisión por margen y no por
   umbral. Los dos números —92 y 6— viven en lugares distintos: el umbral es un parámetro del negocio
   (`shared/parameters.py:286`) y el margen es una constante (`service.py:169`). Un test que sólo
   mueva el parámetro no prueba el margen.
2. **La retroactividad de una grafía.** El número que `preview_alias` promete tiene que ser el que
   `save_alias` resuelve —lo cuenta la misma consulta, y ese es el punto—. Y al dejarla sin efecto
   tienen que volver **exactamente** las que esa grafía resolvió: una factura que alguien decidió una
   por una no lleva `resolved_by_alias_id` y **no vuelve**. Un test que cuente el total de la cola en
   lugar de las facturas concretas pasa por accidente.
3. **El duplicado.** Mismo número y mismo proveedor conserva una y suma `arrival_count`; mismo número
   con otro total va a revisión; y dos facturas **sin proveedor identificado** con el mismo número
   siguen siendo dos. Ese último está fijado en
   `test_two_without_a_supplier_are_not_duplicates_of_each_other`.
   **Cuidado con el contador (D-12).** `test_the_same_invoice_twice_is_kept_once_and_counted`
   (`test_invoices_and_suppliers.py:267`) publica el mismo lote dos veces y espera
   `arrival_count == 2` — y eso pasa igual con la cuenta correcta y con la que hay. `_count_arrival`
   (`service.py:620`) suma uno cada vez que `register_invoices` **ve** una factura ya registrada, sin
   mirar de qué corrida viene la fila, y la pantalla se re-normaliza entera en cuanto cambia de hash
   (`portal/service.py:287-288`). Lo que hay que probar es lo que ese test no distingue: que la
   **segunda lectura de la misma pantalla** no debería sumar nada.
4. **El acuerdo archivo/tabla.** No alcanza con probar "coincide" y "no coincide". Faltan los dos
   casos que `agrees_with` decide por su cuenta: un documento que **no trae** un campo (no es
   desacuerdo) y un documento que **no confirmó nada** (tampoco es acuerdo). Y ojo: `agrees_with`
   **no compara el proveedor**, aunque el documento lo lea y se guarde.

Todo contra los fixtures de `backend/tests/fixtures/portal/` —`invoice-F-8411-text.pdf`,
`invoice-F-9936-scanned.pdf`, `invoice-F-7797.xlsx`, `invoices-page-*.html`,
`suppliers-ledger-page-*.html`—, **nunca contra el portal** (`TEST-03`).

**La suite corre entera y en verde**, y los dos motivos por los que no corría —el broker y
Tesseract— están cerrados. Lo que hay que probar ahora que antes no se podía:

- **El CUIT que identifica** (RF-11): un documento que trae uno del padrón resuelve la factura sin
  que nadie la mire; el de Cordillera no resuelve a nadie; y un CUIT no toca una factura apartada
  por un **número** en duda, porque contesta otra pregunta.
- **El archivo original** (RF-04): que vuelvan los bytes y no una transcripción, con su tipo, y que
  ventas siga sin llegar — un endpoint de archivo es una puerta de atrás fácil de dejar abierta.
- **Confirmar contra corregir** (RF-31): mandar el mismo valor **no** es una corrección y no deja
  línea de bitácora. Un test que sólo pruebe la corrección deja pasar el defecto contrario.

**Para el Code-Reviewer** — Mirá en este orden.

1. **Fronteras (`GEN-02`, `GEN-03`).** `purchases` es el módulo más grande y el que más tienta:
   revisá los imports de `service.py`, `handlers.py` y `routes.py` — la única línea legal hacia otro
   módulo es `from app.modules.identity.dependencies import …`. La tentación concreta acá es leer
   `triage` para la cola; no se hace.
2. **`PY-09` en las catorce rutas.** Que cada una declare `require_section`, y que la **sección y el
   nivel** sean los de la tabla de *Contratos* —no sólo que haya una dependencia—. `GET
   /invoice-review` pide WRITE a propósito.
3. **`GEN-08` y `GEN-09`.** Los eventos llevan identificadores y valores planos, nunca modelos de
   SQLAlchemy: mirá `RegisteredInvoice` y `NormalizedSupplier` en `catalog.py`. Y `bring_invoice_files`
   **encola y vuelve** (`portal/handlers.py:38`): cien visitas a un sistema ajeno no pueden quedar
   abiertas dentro de la transacción del publicador.
4. **El punto ciego propio de esta feature.** Que ningún dato dudoso termine en `core` sin haber
   pasado por una persona. Los dos lugares donde eso se decide son `record_document`
   (`service.py:688-691`) y `register_invoices` (`service.py:504-565`). El Artículo II es lo que esta
   feature promete a cada paso.
5. **Un `publish` sin suscriptor no falla y no se nota.** `InvoiceRowsQuarantined` llevaba así
   desde el primer día y costó una grieta en el Artículo II. Cuando revises un evento nuevo, buscá
   el `@events.subscribe` antes de darlo por conectado.
6. **Que la pantalla haga lo que el endpoint permite.** Seis de los catorce hallazgos fueron el
   mismo error de lectura: el dato viaja en la respuesta, el plan lo dio por cumplido, y ninguna
   pantalla lo usa. Ahora lo frena
   `tests/architecture/test_invoice_screens_show_what_they_are_given.py` — pero ese test **sólo
   cubre las reglas que están escritas en él**. Un requisito nuevo con pantalla necesita su fila, y
   pedirla es parte del review.
7. **La copia del archivo.** `core.invoice_document.content` duplica bytes que ya están en `raw`, y
   es deliberado: `raw` es de `portal` y leerlo desde `purchases` sería el import que el Artículo IV
   prohíbe. Si te tienta «desduplicar», la frontera es lo que se rompe.

---

## Lo que la implementación encontró

**Un duplicado sin proveedor identificado necesitaba una clave distinta.** El plan firmó *(proveedor,
número)* como clave de duplicado, y eso está, como índice único parcial. Lo que faltaba era la otra
mitad: cómo se reconoce la misma factura **mientras el proveedor no está resuelto**. Buscar sólo por
número fusionaba dos facturas distintas y perdía una, que es lo contrario de RF-40. La identidad de
una factura sin proveedor resuelto quedó en ***(el nombre tal como llegó escrito, número)***
(`repository.py:152-175`): dos facturas con el mismo número de dos proveedores que nadie identificó
no son duplicadas, y la segunda lectura de la misma pantalla sigue reconociendo la misma factura.

**El umbral alto tiene un costo visible, y es el correcto.** `supplier_match.threshold_pct` arranca
en 92 y además una coincidencia tiene que estar 6 puntos por delante de la segunda. Es deliberado:
en la duda va a una persona, porque un proveedor mal resuelto rompe la deuda y no se nota desde
afuera. El dueño puede bajar el umbral desde el panel de parámetros si el volumen de revisión molesta
más que el riesgo; el margen, no, y eso es una asimetría que conviene saber.

**El archivo de la factura se sirve tal cual, desde una copia propia.** `GET /invoices/{id}/file`
devuelve los bytes con su tipo. La objeción que la primera versión escribió —«`raw` es evidencia y no
se le sirve a un navegador»— era medio cierta: el Artículo III prohíbe **escribir** `raw`, no leerlo,
pero `raw` es de `portal` y leerlo desde `purchases` sí sería el import que el Artículo IV prohíbe.
La salida no era negarle el archivo a quien lo pide: es que el módulo mantenga su propia copia
alimentada por eventos, que es exactamente lo que la constitución prescribe para una lectura entre
módulos. `raw` sigue intacto y sigue siendo la evidencia.

**El acuerdo no es simétrico.** `agrees_with` decide tres cosas y sólo una es obvia: un campo ausente
no es desacuerdo, un documento vacío no es acuerdo, y **el proveedor no se compara** aunque se lea y
se guarde. Lo último es coherente con que la identificación sea de `purchases` contra el padrón, pero
significa que un archivo que nombra a otro proveedor no manda la factura a revisión por sí solo.

## Lo que no cerraba contra la spec firmada — cerrado el 2026-08-31

Trece puntos, y el `/converge` agregó un decimocuarto que este plan no había visto: **RF-31 no
tenía implementación** y tanto este documento como `tasks.md` lo daban por cumplido. El veredicto fue
**deriva mayor**, el humano decidió **implementar los catorce**, y los catorce están implementados.

La tabla se conserva **con su redacción original**, que describe el defecto en presente, y cada fila
lleva ahora su cierre. No se reescribe en pasado ni se borra: un hallazgo borrado es un hallazgo que
nadie vuelve a poder auditar, y la mitad del valor de esta tabla es que la próxima feature vea qué
clase de cosas se le escapan a un review.

**Lo que dejaron como lección.** D-6, D-8, D-10 y D-11 eran **el mismo error cuatro veces** —el
backend devuelve el dato, el plan da el requisito por cumplido, y ninguna pantalla lo muestra—, y con
D-7 y D-9 son seis. Es un defecto que no falla: suite verde, endpoint correcto, y sólo se descubre
abriendo el `.tsx`. Por eso la lección quedó mecanizada en
`tests/architecture/test_invoice_screens_show_what_they_are_given.py`, que rompe el build si un campo
que un requisito firmado necesita deja de leerse en la pantalla que ese requisito nombra.

### Cómo se cerró cada uno

| # | Cómo quedó |
|---|---|
| **D-1** | `triage/handlers.py::open_unreadable_invoice_rows` escucha `InvoiceRowsQuarantined` y abre un caso de clase `unreadable_invoice_row`. Lo único que se puede hacer con él es darlo por revisado: cargar una factura a mano está fuera del alcance firmado, y lo que faltaba era que la fila **existiera** para alguien |
| **D-2** | Cerrado por `8e40cf3`: `tesseract-ocr`, `-spa` y `-eng` en `backend/Dockerfile:16-18` y en `.github/workflows/ci.yml:60-64` |
| **D-3** | RF-11 implementado, y **no** donde este plan lo buscaba. La tabla del portal no publica CUIT —se verificó contra el fixture—, así que el número sólo existe dentro del archivo, que llega después de la fila: identifica `_identify_by_tax_id` cuando el documento llega, sobre una factura apartada por su proveedor. Dos barreras distintas contra la trampa medida: el lector descarta el CUIT de la línea del cliente, y el servicio sólo acepta uno de los ocho del padrón, donde Cordillera no está. Sobre el corpus de hoy ningún archivo trae CUIT del emisor: el requisito es un condicional y su antecedente es falso |
| **D-4** | `bring_held_invoice_files` escucha `InvoicesNeedingReview` y encola la descarga de las apartadas, espaciada igual que la de las registradas. `InvoiceReviewCase.needs_document` distingue la recién registrada de la que sólo volvió a llegar, para no pedirle al portal un archivo que ya está |
| **D-5** | `GET /invoices/{id}/file` devuelve los bytes con su `content_type` y `Factura F-8411.pdf` de nombre. **No lee `raw`** —es de `portal`, y sería el import que el Artículo IV prohíbe—: el módulo guarda su propia copia en `core.invoice_document.content`, alimentada por `InvoiceFileRead`, que es la proyección que la constitución prescribe. El proxy del frontend pasa el cuerpo como bytes; leerlo como texto entregaba un PDF corrupto |
| **D-6** | La ficha del proveedor lista las grafías, con la fuente de cada una en el `title` y un enlace a la pantalla de grafías guardadas |
| **D-7** | `SupplierPeriod.tsx` pone `since`/`until` en la URL, con atajo al año en curso. Y lo excluido se cuenta por motivo: `excluded_in_review` es el número que RF-23 pide, separado de lo inconsistente y de lo que cae fuera del período |
| **D-8** | `resolved_by_user_id`, `resolved_at` y `resolved_by_name` en `InvoiceRead`; el nombre lo resuelve la ruta con `ActorDirectory`, como hace la bitácora de `operations` |
| **D-9** | `created_by_name` en `SupplierAliasRead`, resuelto igual, y `SpellingList.tsx` imprime «La asignó Fulano». Una grafía que el sistema reconoció solo no tiene autor y lo dice así en vez de inventar uno |
| **D-10** | Columna **Formato** en `InvoiceTable.tsx`, con las escaneadas marcadas: son 46 de cada 100 y las que el lector acierta menos |
| **D-11** | `SupplierCorrection.tsx`, el mismo diálogo que corrige un precio, dentro de la ficha. El botón sólo aparece para quien la ruta dejaría escribir: ofrecerlo a quien va a recibir un 403 es mentirle a la persona |
| **D-12** | Un arribo es el portal publicando la factura **dos veces en la misma lectura**. `core.invoice.last_batch_id` (migración `0015`) es lo que distingue eso de releer la pantalla. El test que codificaba el defecto —publicaba el mismo lote dos veces y esperaba `2`— se corrigió y se le sumó el que faltaba: tres lecturas de la misma fila siguen siendo un arribo |
| **D-13** | Cerrado por `8e40cf3`: `conftest.py` tiene `queued_invoice_files`, y es **autouse**, porque la task se encola desde un handler que nadie llama a mano |
| **RF-31** | *(el que el converge agregó)* `InvoiceReviewResolution` lleva `number`, `issued_on` y `total`; mandarlos corrige y omitirlos confirma. Cada corrección publica `ManualChangeRecorded` con el valor anterior, recalcula el vencimiento y mueve la entrada del calendario. Confirmar **no** escribe en la bitácora: registrar el acuerdo con el portal la volvería inútil para encontrar en qué se lo contradijo. El campo muerto `action` se sacó del contrato |

| # | Qué | Dónde | RF |
|---|---|---|---|
| **D-1** | `InvoiceRowsQuarantined` se publica y **nadie está suscripto**. Una fila de `/facturas` que no se pudo tipar queda en `staging` en cuarentena y **no genera caso en `triage` ni factura en la cola**: no se cuenta, no se ve y nadie la decide. `InvoicesNeedingReview` también queda sin oyente, pero ahí es inocuo | `ingestion/service.py:425` · `triage/handlers.py` (sin handler) | RF-07, RF-34; **Artículo II** |
| **D-2** | `tesseract-ocr` y `tesseract-ocr-spa` **no están ni en la imagen ni en el CI**, y son dos líneas de `apt` en dos archivos. En el contenedor desplegado `_ocr` devuelve vacío para las 46 escaneadas y todas caen en revisión; el plan anterior afirmaba que entraban por el Dockerfile del worker, no entraron, y hay un solo Dockerfile para api, worker y beat. **En CI el efecto es otro y peor**: el job `backend` no instala ningún paquete de sistema, el fixture escaneado tiene **0 caracteres** extraíbles con `pypdf`, y `test_the_three_formats_are_read_and_agree_with_the_table[invoice-F-9936-scanned.pdf]` **falla** en `assert reading.readable` —no pasa por el camino de «ilegible»—. El 46% del corpus no está verificado en el pipeline | `backend/Dockerfile:7` · `.github/workflows/ci.yml:53-80` | RF-26; **Artículo VI** |
| **D-3** | **RF-11 no tiene implementación.** `resolve_supplier` no tiene camino por CUIT, y está documentado como deliberado porque el único CUIT impreso es el de Cordillera. La razón es buena; el requisito firmado sigue diciendo lo contrario | `purchases/service.py:436-489` · `ingestion/documents.py:20-25` | RF-11 |
| **D-4** | El archivo de una factura **sólo se descarga si la factura llegó a `InvoicesRegistered`**, es decir si su proveedor se resolvió sola. Una factura apartada por proveedor ambiguo o fuera del padrón **nunca baja su archivo**, y al resolverse después tampoco: `_attach` no publica `InvoicesRegistered` | `portal/handlers.py:38-53` · `purchases/service.py:546-557,991` | RF-02, RF-30 |
| **D-5** | `GET /invoices/{id}/file` devuelve **texto plano con el recorte**, no el archivo original. RF-04 pide abrir el PDF o la planilla como llegaron | `purchases/routes.py:615-630` | RF-04 |
| **D-6** | La ficha del proveedor **no muestra las grafías**. `SupplierRead.aliases` viaja en la respuesta y la pantalla no la renderiza; las grafías viven en `/proveedores/grafias`, que es otra pantalla. El criterio firmado dice "al abrir un proveedor se ven todas las formas" | `frontend/app/(private)/proveedores/[supplierId]/page.tsx` | RF-10 |
| **D-7** | El total por período: la API acepta `since`/`until` pero **la pantalla no ofrece elegir el período** —llama a `/totals` sin parámetros—. Y `excluded` **cuenta junto** lo apartado por revisión y lo que quedó fuera del rango de fechas, así que con período elegido el número que RF-23 pide deja de significar lo que dice | `frontend/…/proveedores/[supplierId]/page.tsx:42` · `purchases/service.py:1030-1040` | RF-22, RF-23 |
| **D-8** | `resolved_by_user_id` y `resolved_at` **se guardan y no se exponen**: no están en `InvoiceRead`, así que ninguna pantalla puede mostrar quién resolvió una factura ni cuándo | `purchases/schemas.py:190-225` | RF-32 |
| **D-9** | La pantalla de grafías muestra **de dónde salió y cuándo, pero no quién**. `created_by_user_id` viaja en la respuesta; falta resolverlo a un nombre —`ActorDirectory` de `identity.dependencies` existe justo para eso— y renderizarlo | `frontend/components/purchases/SpellingList.tsx:60-80` | RF-51 |
| **D-10** | **El formato de la factura no se muestra en ninguna pantalla.** `file_kind` se guarda (`core.invoice.file_kind`), viaja en `InvoiceRead` y muere ahí: las ocho columnas de `InvoiceTable.tsx` son Factura, Proveedor, Fecha, Vence, Monto, Pagado, Estado y Recibo, y la ficha de la factura tampoco lo imprime. En todo el frontend `file_kind` sólo aparece en los tipos generados (`lib/api/types.ts:2418`). El criterio firmado es «la lista distingue **a simple vista** cuáles llegaron como imagen escaneada» | `frontend/components/purchases/InvoiceTable.tsx` · `purchases/models.py:238` · `purchases/schemas.py:212` | RF-05 |
| **D-11** | **No hay desde dónde corregir un proveedor.** `PATCH /suppliers/{id}` existe y está bien autorizado (`routes.py:225`, `SUPPLIERS`·WRITE), y la server action `correctSupplier` está escrita — pero **ningún componente la importa**: `SupplierContact.tsx` es un `<dl>` que mapea `FIELDS` y no tiene un `input`, ni un `form`, ni un handler. El criterio firmado es «Marcela corrige el correo de un proveedor **desde su ficha**». Va junto con D-6 y D-7: las tres faltas son la misma pantalla | `frontend/components/purchases/SupplierContact.tsx` · `frontend/app/actions/purchases.ts:123` | RF-16 |
| **D-12** | **`arrival_count` no cuenta arribos, cuenta relecturas.** `_count_arrival` hace `existing.arrival_count += 1` en cuanto `register_invoices` encuentra una factura ya registrada, sin mirar de qué corrida viene la fila; y `_extract` sólo saltea la pantalla cuando el hash es **idéntico** a uno ya normalizado, así que una factura nueva —o que el portal actualice el pagado de una sola fila— cambia el hash, re-normaliza las cien filas y **le suma uno a todas**. Con `invoice_sync.interval_hours` en 12 son dos corridas por día. El criterio firmado es «una factura que llegó tres veces lo indica», y lo que indica es cuántas veces se releyó la pantalla | `purchases/service.py:610-620` · `portal/service.py:287-288` | RF-39 |
| **D-13** | **Siete tests de integración de 004 fallan en CI por el broker.** Todo test que llegue a `register_invoices` con un proveedor que resuelve dispara `InvoicesRegistered` → `bring_invoice_files` → `extract_invoice_file.apply_async`, que necesita un broker vivo; en CI sólo hay servicio de Postgres, y como el handler corre en la transacción del publicador y al fallar la aborta (`GEN-09`), el test se cae con `kombu.exceptions.OperationalError: [Errno 111] Connection refused`. Falta el fixture que intercepte la task, al lado de `queued_history` y `queued_alerts` —cuyo propio comentario dice que un caso así «pasa en la máquina que tiene el broker levantado y falla en CI»—. En una máquina con RabbitMQ arriba los siete pasan **y encolan tasks de verdad** | `backend/tests/conftest.py:249-291` · `portal/handlers.py:39-53` · `.github/workflows/ci.yml:38-50` | **Artículo VI**; los siete cubren RF-12, RF-13, RF-27, RF-29, RF-30, RF-37 a RF-39 y el vencimiento de 005 |

**Alcance que el código tiene y la spec de 004 no pide:** ninguno propio. Lo que sobra en
`purchases` —pagos, recibos, calendario, órdenes— pertenece a las specs **005, 006 y 007**, que se
construyeron en la misma pasada y tienen su propio plan. Dos rutas de esta feature devuelven además
campos de 005: `GET /suppliers/{id}/totals` agrega `paid`, `owed`, `aging` y `average_delay_days`, y
`InvoiceRead` agrega el estado de pago y el recibo. Está declarado acá para que `/converge` no lo lea
como derivación de 004.
