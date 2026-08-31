# Informe de convergencia — 004-invoices-suppliers

**Feature:** 004-invoices-suppliers · **Fecha:** 2026-08-31 · **Rol:** `Lead`
**Spec:** `spec.md`, Aprobada el 2026-08-29 por Leandro Carriego — FDE (RF-01 a RF-53)
**Changeset:** rama `feat/004-to-009-remaining-specs`, HEAD `8e40cf3`, más el árbol de trabajo sin
commitear (que es donde viven `InvoiceFilters.tsx`, `SupplierContact.tsx` y
`test_invoice_search_and_order.py`)
**Suite al momento de verificar:** `1397 passed · 8 skipped`, cobertura 89.60%

> **Hay una segunda corrida, y su veredicto es el vigente.** Está al final de este archivo:
> *Segunda corrida — 2026-08-31*. Lo que sigue acá es la primera, tal como se emitió.

> `review_feature` pregunta *¿está bien escrito?*. Este informe contesta la otra:
> **¿es lo que se acordó?** No juzga calidad de código, ni tipado, ni cobertura. Juzga
> correspondencia entre lo firmado y lo que existe.

> ## ⏩ Estado al 2026-08-31, después de este informe
>
> **El humano decidió implementar los catorce hallazgos, y los catorce están implementados.** Este
> informe **no se reescribe**: su valor es haber dicho lo que decía el día que lo dijo, y un
> hallazgo corregido sobre el papel es un hallazgo que nadie vuelve a poder auditar. Lo que sigue
> es el veredicto tal como se emitió.
>
> Qué se hizo con cada uno está en `plan.md` → *Cómo se cerró cada uno*, y el desglose del trabajo
> en `tasks.md` → tareas 43 a 47. En una línea: los tres ausentes se implementaron —RF-11 por donde
> el CUIT realmente existe, RF-04 con una copia propia del archivo, RF-31 con los tres datos de
> cabecera editables desde la cola—, los once parciales se completaron, y la lección de los seis
> que eran el mismo error quedó mecanizada en
> `backend/tests/architecture/test_invoice_screens_show_what_they_are_given.py`.
>
> **Esto no levanta el gate.** El converge lo corrió el `Lead` y lo implementó el `Developer`: que
> quien escribió el código diga que ya está no es el gate, es la parte que el gate audita. **Hace
> falta un `/converge` nuevo**, y después el `/review-feature`.

## Veredicto: 🔴 DERIVA MAYOR

**Tres requisitos firmados no tienen implementación** —RF-04, RF-11 y RF-31— y **once más cumplen
sólo una parte**. De los catorce, **nueve son el mismo error repetido**: el backend guarda el dato,
lo expone en la respuesta, y ninguna pantalla lo usa. El cliente firmó criterios de aceptación que
describen lo que ve una persona, no lo que devuelve un endpoint.

Por el procedimiento, una deriva mayor **bloquea el paso al `Code-Reviewer`**: la 004 no pasa al
gate de calidad hasta que se resuelva, y no puede archivarse con `/ship`.

**La decisión de qué corregir —el código o el acuerdo— es tuya, no mía** (Artículo V). Cada hallazgo
baja con sus dos salidas y lo que cuesta cada una.

**Alcance no pedido: ninguno.** Se recorrió el sentido inverso y no hay una sola capacidad de
negocio en la 004 que ningún requisito pida.

## Cómo se verificó

Contra el código, no contra los documentos. Cada fila `Implementado` sale de abrir el archivo o de
un `grep` sobre `backend/app/`, `frontend/` y `backend/tests/`, buscando por el término de dominio
en inglés (`supplier`, `invoice`, `alias`, `quarantine`). **Que la suite pase no fue tomado como
prueba de nada**: un requisito que ningún test ejercita queda `Parcial` aunque el código exista.

Dos aclaraciones sobre los insumos, porque cambian cómo hay que leer este informe:

1. **`plan.md` trae su propia lista de trece defectos (D-1 … D-13).** No se dio por buena: se
   verificó una por una. **Once se confirmaron. Dos ya están arreglados** —D-2 (Tesseract) y D-13
   (el fixture del broker), que resolvió el commit `8e40cf3`— y el plan quedó viejo ahí.
2. **Se encontró un requisito sin implementar que el plan no declara: RF-31.** Es el hallazgo más
   importante de esta corrida, porque `plan.md` y `tasks.md` lo dan por cumplido los dos.

## Tabla de trazabilidad

Los 53 requisitos firmados. Ninguno quedó sin fila.

| Requisito | Qué promete la spec | Dónde está implementado | Estado |
|---|---|---|---|
| RF-01 | Traer del portal las facturas con la frecuencia configurada | `operations/service.py::SYNC_JOBS` (claves `invoices`, `supplier_ledger`, con `invoice_sync.interval_hours`) · `portal/tasks.py::extract_invoices` | ✅ Implementado |
| RF-02 | Conservar el archivo de cada factura tal como llegó | `portal/service.py::extract_invoice_file` → `raw.portal_document` con hash. **Sólo se dispara desde `portal/handlers.py::bring_invoice_files`, suscripto a `InvoicesRegistered`** | ⚠️ Parcial — H2 |
| RF-03 | Mostrar número, fecha, proveedor y total | `GET /invoices` (`routes.py:86`) · `components/purchases/InvoiceTable.tsx` | ✅ Implementado |
| RF-04 | Permitir abrir el archivo original de cualquier factura | `routes.py::invoice_file` devuelve `document.excerpt` como `text/plain`, no el archivo. Ninguna pantalla enlaza ni siquiera a eso | ❌ **Ausente** — H1 |
| RF-05 | Mostrar el formato en que llegó cada factura | `core.invoice.file_kind` (`models.py:239`), expuesto en `InvoiceRead.file_kind`. En todo el frontend aparece **sólo** en `lib/api/types.ts:2418` | ⚠️ Parcial — H4 |
| RF-06 | Impedir a ventas el acceso a las facturas de compra | `identity/permissions.py:78-79` (`Level.NONE`) · `tests/architecture/test_route_authorization.py` | ✅ Implementado |
| RF-07 | Procesar lo que ya está en el portal; lo irresoluble apartado sin frenar el resto | `register_invoices` (`service.py:504`) aparta sin bloquear. **La fila que ni siquiera se pudo tipar no llega a nadie** | ⚠️ Parcial — H11 |
| RF-08 | Mantener un padrón de proveedores del portal | `remember_suppliers` (`service.py:207`) desde `SuppliersNormalized` · `GET /suppliers` · `(private)/proveedores/page.tsx` | ✅ Implementado |
| RF-09 | Asociar la factura a un proveedor del padrón | `core.invoice.supplier_id` · `InvoiceRead.supplier_name` · `InvoiceTable.tsx` (columna Proveedor, con «sin identificar» cuando falta) | ✅ Implementado |
| RF-10 | Registrar todas las formas en que llegó escrito su nombre | `core.supplier_alias` (`models.py:154`) · `SupplierRead.aliases`. **La ficha del proveedor no las renderiza**: `aliases` sólo se usa en `/proveedores/grafias` | ⚠️ Parcial — H5 |
| RF-11 | Si la factura trae el CUIT, identificar al proveedor por ese CUIT | Nada. `resolve_supplier` (`service.py:436-489`) tiene dos caminos —grafía y `rapidfuzz`— y su docstring declara que **no hay un tercero por CUIT** | ❌ **Ausente** — H1 |
| RF-12 | Sin CUIT, identificar por el nombre contra el padrón | `resolve_supplier` con `fuzz.token_sort_ratio`, umbral `supplier_match.threshold_pct` · `test_a_variant_close_enough_is_identified_and_remembered` | ✅ Implementado |
| RF-13 | Si no se puede identificar con certeza, apartar | `AMBIGUOUS_SUPPLIER` por margen (`service.py:471`) · `test_a_name_that_is_nearly_two_suppliers_goes_to_a_person` | ✅ Implementado |
| RF-14 | Proveedor fuera del padrón: apartar con ese motivo, sin dar de alta | `OUTSIDE_REGISTER`; `put_supplier` sólo corre desde `remember_suppliers` · `test_an_invoice_from_outside_the_register_does_not_create_a_supplier` | ✅ Implementado |
| RF-15 | Mostrar razón social, CUIT, correo, teléfono y plazo pactado | `GET /suppliers/{id}` · `proveedores/[supplierId]/page.tsx:54-62` (razón social y CUIT) + `SupplierContact.tsx` (los otros tres) | ✅ Implementado |
| RF-16 | Permitir corregir correo, teléfono y plazo | `PATCH /suppliers/{id}` (`routes.py:227`) y la server action `correctSupplier` (`app/actions/purchases.ts:123`). **Ningún componente la importa**; `SupplierContact.tsx` es un `<dl>` sin `input`, sin `form` y sin handler | ⚠️ Parcial — H6 |
| RF-17 | Impedir editar razón social y CUIT | `SupplierContactWrite` (`schemas.py:89`) sólo admite `email`, `phone`, `payment_term_days`: el contrato no acepta el campo | ✅ Implementado |
| RF-18 | Registrar quién corrigió, cuándo y el valor anterior | `ManualChangeRecorded` (`service.py:1946`) → `operations/handlers.py:57` | ✅ Implementado |
| RF-19 | El portal no pisa lo corregido; la diferencia se señala | `_corrections_holding` + `_check_supplier_conflict` (`service.py:240-325`) · `SupplierContact.tsx:56-66` · diez tests en `test_invoices_and_suppliers.py:463-655` | ✅ Implementado |
| RF-20 | Un dato de contacto que falta se muestra como faltante | `SupplierRead.missing` (`service.py:409`) · `SupplierContact.tsx::shown` devuelve «falta» · `page.tsx:63-67` | ✅ Implementado |
| RF-21 | Mostrar, dentro de la ficha, todas sus facturas | `GET /suppliers/{id}/invoices` (`routes.py:256`) · `page.tsx:118` | ✅ Implementado |
| RF-22 | Total facturado para un proveedor y **un período elegido** | `supplier_totals` acepta `since`/`until` (`service.py:1015`). **La pantalla llama a `/totals` sin parámetros** y no ofrece elegir período | ⚠️ Parcial — H7 |
| RF-23 | Informar cuántas facturas quedaron excluidas **por estar en revisión** | `SupplierTotalsRead.excluded` (`service.py:1044`) **suma tres cosas distintas**: en revisión, inconsistentes y fuera del rango de fechas | ⚠️ Parcial — H7 |
| RF-24 | Mostrar la cantidad de proveedores del padrón | `SupplierList.total` · `proveedores/page.tsx:37` | ✅ Implementado |
| RF-25 | Extraer del archivo número, fecha, proveedor y total | `ingestion/documents.py::read_invoice_document` · `purchases/service.py::record_document` | ✅ Implementado |
| RF-26 | Extraer de PDF con texto, imagen escaneada y planilla | `documents.py` con `pypdf`, Tesseract y `openpyxl` · `test_the_three_formats_are_read_and_agree_with_the_table` · `backend/Dockerfile:16-18` y `ci.yml:60-64` ya instalan el binario | ✅ Implementado |
| RF-27 | Registrar, dato por dato, si se obtuvo con certeza o quedó en duda | `agrees_with` (`documents.py:85`) → `core.invoice_document.agrees` → `InvoiceDocumentRead` · `facturas/[invoiceId]/page.tsx:76-85` | ✅ Implementado |
| RF-28 | Archivo con forma no reconocida: apartar sin interrumpir el resto | `read_invoice_document` devuelve `readable=False` con motivo; cada lector falla en su propio `try` (`documents.py:117-124`) | ✅ Implementado |
| RF-29 | Un dato en duda aparta la factura en lugar de darlo por bueno | `record_document` (`service.py:641-691`) → `PENDING` · `test_a_document_that_disagrees_holds_it_with_the_excerpt` | ✅ Implementado |
| RF-30 | Mostrar, junto a cada dato en duda, la parte del archivo de la que salió | `facturas/[invoiceId]/page.tsx:82` y `ReviewQueue.tsx:95-99`. **Pero una factura apartada por su proveedor nunca baja su archivo**, así que en la cola de grafías no hay recorte que mostrar | ⚠️ Parcial — H2 |
| RF-31 | Cuando alguien confirme o corrija un dato en duda, registrarlo como el valor de ese dato | Nada. `InvoiceReviewResolution` (`schemas.py:237`) sólo lleva `supplier_id` y `remember`; `invoice.total` se escribe **únicamente** desde `row.total` en `_create_invoice` (`service.py:576`) | ❌ **Ausente** — H3 |
| RF-32 | Registrar qué se decidió, quién y cuándo | `core.invoice.resolved_by_user_id` / `resolved_at` se guardan (`service.py:869-870`, `1002-1003`) y **no están en `InvoiceRead`**: ninguna pantalla puede mostrarlos | ⚠️ Parcial — H8 |
| RF-33 | Una factura resuelta deja de aparecer entre las pendientes | `resolve_invoice` → `RESOLVED`; `GET /invoice-review` filtra por `PENDING` | ✅ Implementado |
| RF-34 | Mostrar cuántas facturas están pendientes de revisión | `InvoiceList.total` · `facturas/revision/page.tsx:41-44` | ✅ Implementado |
| RF-35 | Impedir una factura sin número, fecha, proveedor o total | `number`, `issued_on`, `total` son `NOT NULL` (`models.py:215-217`) y `ingestion/service.py:406-410` no normaliza una fila sin los tres | ✅ Implementado |
| RF-36 | Sólo dueño y compras resuelven y asignan grafías | `require_section(PURCHASE_INVOICES, WRITE)` y `(SUPPLIERS, WRITE)` en las seis rutas · matriz con ventas en `NONE` | ✅ Implementado |
| RF-37 | Misma factura repetida: conservar una sola | `invoice_of` (`repository.py:152`) + `_count_arrival` · `test_the_same_invoice_twice_is_kept_once_and_counted` | ✅ Implementado |
| RF-38 | Mismo número con otro total: apartar, no descartar | `DUPLICATE_WITH_ANOTHER_TOTAL` (`service.py:629-639`) · `test_the_same_number_with_another_total_goes_to_a_person` | ✅ Implementado |
| RF-39 | Mostrar, para una factura que llegó más de una vez, cuántas veces llegó | `core.invoice.arrival_count` · `InvoiceTable.tsx:52`. **Pero cuenta relecturas de la pantalla, no arribos de la factura** | ⚠️ Parcial — H9 |
| RF-40 | Sin proveedor identificado, ninguna factura es duplicada de otra | Índice único **parcial** `uq_invoice_supplier_number` con `WHERE supplier_id IS NOT NULL` (`models.py:196-207`) · `test_two_without_a_supplier_are_not_duplicates_of_each_other` | ✅ Implementado |
| RF-41 | Buscar facturas por CUIT del proveedor | `_search` (`repository.py:340-368`), con y sin guiones · `test_the_tax_id_finds_every_invoice_of_that_supplier`, `test_the_tax_id_is_found_without_its_dashes` · `InvoiceFilters.tsx` campo `q` | ✅ Implementado |
| RF-42 | Buscar por razón social | `_search` con join a `core.supplier` · `test_the_legal_name_finds_an_invoice_that_arrived_misspelled` | ✅ Implementado |
| RF-43 | Filtrar por rango de fechas | `issued_from`/`issued_to` (`service.py:709-710`) · `test_a_range_keeps_only_what_was_issued_inside_it`, `test_both_ends_are_included`, `test_it_is_not_the_due_date` · `InvoiceFilters.tsx` | ✅ Implementado |
| RF-44 | Filtrar por proveedor | `supplier_id` · `test_by_supplier` · `InvoiceFilters.tsx` selector | ✅ Implementado |
| RF-45 | Ordenar por fecha y por total | `InvoiceOrder` (`models.py:92`), cuatro órdenes · cuatro tests en `test_invoice_search_and_order.py:199-231` · `InvoiceFilters.tsx::ORDERS` | ✅ Implementado |
| RF-46 | Filtrar por estado de revisión | `review_state` en `list_invoices` · `test_by_review_state` · `facturas/page.tsx` acepta el parámetro en la URL, y `/facturas/revision` lista las pendientes | ✅ Implementado |
| RF-47 | Guardar la asignación de grafía como criterio | `save_alias` (`service.py:924`) con `SupplierAliasSource.LEARNED` | ✅ Implementado |
| RF-48 | Informar antes cuántas facturas apartadas resuelve | `preview_alias` (`service.py:904`), con la misma consulta que después resuelve · `ReviewQueue.tsx::look` · `test_the_preview_promises_the_number_that_then_happens` | ✅ Implementado |
| RF-49 | Aplicar la asignación a las facturas ya apartadas | `_apply_alias` (`service.py:979`) | ✅ Implementado |
| RF-50 | Una factura posterior con esa grafía entra sin apartarse | `alias_for` es lo primero que mira `resolve_supplier`; `text_normalized` es `unique` · `test_a_spelling_of_the_register_enters_straight` | ✅ Implementado |
| RF-51 | Mostrar las grafías guardadas, con quién las decidió y cuándo | `GET /supplier-aliases` devuelve `created_by_user_id`. **`SpellingList.tsx:66` imprime «Asignada por alguien»**: el nombre nunca se resuelve | ⚠️ Parcial — H10 |
| RF-52 | Dejar sin efecto una asignación guardada | `drop_alias` (`service.py:954`) · botón en `SpellingList.tsx:73-80` | ✅ Implementado |
| RF-53 | Volver a apartar las facturas que esa asignación resolvía | `invoices_resolved_by_alias` (`repository.py:207`), por `resolved_by_alias_id` · `test_dropping_it_gives_back_exactly_what_it_resolved` | ✅ Implementado |

**Cierre:** 39 implementados · 11 parciales · **3 ausentes**.

## Hallazgos

| # | Tipo | Qué dice el artefacto | Qué hace el código | Rol dueño | Acción |
|---|---|---|---|---|---|
| **H1** | Requisito sin implementar | RF-11: «si una factura trae el CUIT, identificar por ese CUIT». RF-04: «abrir el archivo original» | No hay camino por CUIT y el lector no lee ninguno. `GET /invoices/{id}/file` devuelve texto plano y nadie lo enlaza | humano | Decidir: implementar o renegociar |
| **H2** | Requisito sin implementar | RF-02 y RF-30: el archivo se conserva y su recorte se ve junto al dato en duda | `bring_invoice_files` sólo escucha `InvoicesRegistered`, que **excluye a las apartadas**; y `_attach` no lo publica al resolverse | Developer | Encolar la descarga también para las apartadas |
| **H3** | Requisito sin implementar | RF-31: «cuando confirme o corrija un dato en duda, registrarlo como el valor». `plan.md` y `tasks.md` lo dan por cumplido | `InvoiceReviewResolution` no tiene campo de valor; `invoice.total` nunca se escribe desde una decisión humana. La cola sólo asigna proveedor o acepta como está | humano | **No estaba declarado.** Decidir: implementar o renegociar |
| **H4** | Requisito sin implementar | RF-05: «la lista distingue **a simple vista** cuáles llegaron como imagen escaneada» | `file_kind` viaja en la respuesta y muere ahí: las ocho columnas de `InvoiceTable.tsx` no lo incluyen | Developer | Una columna |
| **H5** | Requisito sin implementar | RF-10: «al abrir un proveedor se ven todas las formas en que llegó escrito su nombre» | `SupplierRead.aliases` viaja y la ficha no lo renderiza | Developer | Renderizar en la ficha |
| **H6** | Requisito sin implementar | RF-16: «Marcela corrige el correo de un proveedor **desde su ficha**» | `PATCH` y `correctSupplier` existen; **nadie importa la server action**. `SupplierContact.tsx` es sólo lectura | Developer | El formulario. No falta backend |
| **H7** | Requisito sin implementar | RF-22 «un período elegido» · RF-23 «excluidas **por estar en revisión**» | La pantalla llama a `/totals` sin `since`/`until`; `excluded` mezcla revisión, inconsistencia y fuera de rango | Developer | Selector de período; separar los motivos |
| **H8** | Requisito sin implementar | RF-32: «cada factura resuelta muestra qué se decidió, quién y cuándo» | Se guarda en `core.invoice` y no está en `InvoiceRead` | Developer | Exponer y mostrar |
| **H9** | Requisito sin implementar | RF-39: «una factura que llegó tres veces lo indica» | `_count_arrival` suma uno cada vez que `register_invoices` **ve** la fila, y la pantalla se re-normaliza entera al cambiar de hash: dos corridas por día le suman uno a las cien | Developer | Contar arribos, no relecturas |
| **H10** | Requisito sin implementar | RF-51: «cada una con **quién** y cuándo» | `SpellingList.tsx` imprime «Asignada por alguien» | Developer | Resolver el nombre con `ActorDirectory` |
| **H11** | **Contradicción con una regla del dominio** | Artículo II y RF-07/RF-34: nada se descarta, y lo ilegible se cuenta y se ve | `InvoiceRowsQuarantined` (`ingestion/service.py:426`) **no tiene un solo `@events.subscribe`**. Sus análogos `PriceRowsQuarantined` y `PriceHistoryRowsQuarantined` sí abren caso en `triage/handlers.py:34,92` | Developer | El handler que falta. **La regla no se negocia** |
| **H12** | Tarea sin respaldo | `tasks.md` declara **42 de 42 implementadas y verificadas** y los 53 requisitos cubiertos | Al menos seis tareas ✅ nombran cosas que no existen: **T-8** («y el formato en que llegó»), **T-12** («sus dos caminos en orden —CUIT primero»), **T-30** («el formulario que confirma o corrige»), **T-41** («con su autor»), **T-24** (el período), **T-11/T-20** (RF-10 y RF-16 sin tarea de frontend) | Backend-Architect | Reescribir el estado de `tasks.md` |
| **H13** | Diagrama desactualizado | Seis de los siete diagramas dibujan conducta que el código no tiene | `flujo-sistema.mmd:15-17` y `flujo-general.mmd` (rama por CUIT) · `flujo-marcela.mmd:6` (el formato) y `:12` («confirma o corrige el dato») · `flujo-dueno.mmd:10` («Pide un período») · `estados-factura.mmd` («una persona confirma el dato», y le falta la vuelta `Registrada → Apartada` de RF-53) · `estados-grafia.mmd` («queda a la vista con quién la decidió») | Solution-Designer | `/diagram` **después** de que se decida H1–H11 |
| **H14** | Deriva del plan | `plan.md` declara D-2 y D-13 como defectos abiertos y dice que «el CI está rojo» | Los dos están arreglados por `8e40cf3`: `backend/Dockerfile:16-18`, `ci.yml:60-64` y el fixture autouse `queued_invoice_files` (`conftest.py:293-306`). La suite corre **1397 passed · 8 skipped** | Backend-Architect | Actualizar `plan.md` |

Los siete diagramas **compilan**: `bash scripts/diagrams/validate.sh docs/specs/004-invoices-suppliers/diagrams/` pasa. H13 es sobre su contenido, no su sintaxis.

## Lo que este converge miró y **no** es hallazgo

- **Alcance no pedido: no hay.** Se recorrieron las catorce rutas, las seis pantallas, las seis
  tablas de `core` y las tres de `staging`, y cada una tiene un requisito que la pide o es
  andamiaje que `plan.md` justifica. Los campos de pagos, recibos, calendario y órdenes que
  aparecen en `InvoiceRead` y en `/suppliers/{id}/totals` **son de 005, 006 y 007**, que se
  construyeron en la misma pasada y tienen su propio plan.
- **`purchases` con cuatro specs adentro** no es deriva de la 004: el plan lo decide y lo explica.
- **`InvoiceReviewResolution.action`** (`schemas.py:248`) es un campo que nadie lee: no llega al
  servicio ni aparece en ningún test. Es superficie de contrato muerta, demasiado chica para ser
  hallazgo. Se anota para el `Code-Reviewer`.
- **Las cinco reglas del dominio.** Cuatro se cumplen y se verificaron: `portal` no tiene un solo
  `httpx`/`requests` (Art. I y la extracción por navegador), no hay ninguna escritura sobre
  `raw.portal_document` (Art. III), y las credenciales sólo se leen de `settings` en
  `client.py:346-347` (Art. VII). **La quinta —Artículo II— es H11.**
- **Escalado al `Code-Reviewer`, no es de este gate:** las pantallas de la 004 usan `fetchFromApi`,
  que colapsa un 403, un timeout y un 500 en `null`, y renderizan `<NoPermission>` para los tres —
  exactamente el defecto que la 003 corrigió con `readFromApi` y fijó en
  `tests/architecture/test_screen_reads.py`, cuya lista `SCREENS` cubre sólo las pantallas de la
  003.
- **El CI no se pudo verificar desde acá.** La suite corre verde en esta máquina, que **tiene
  `tesseract` instalado** (`/opt/homebrew/bin/tesseract`). Que `ci.yml:60-64` lo instale está
  leído, no observado corriendo.

## Qué hacer con esto

**Nueve de los catorce hallazgos son la misma pieza faltante: la pantalla.** H4, H5, H6, H7, H8 y
H10 no necesitan una línea de backend — el dato ya viaja en la respuesta y, en el caso de H6, la
server action ya está escrita. Tres de ellos caen en la **misma ficha de proveedor**. Es el trabajo
más barato de este informe y cierra seis requisitos firmados.

**Tres hallazgos exigen una decisión tuya antes de tocar código** (Artículo V):

| Hallazgo | Implementar lo que falta | Corregir la spec |
|---|---|---|
| **H1 · RF-11 (CUIT)** | Habría que leer un CUIT que **no es el del emisor**: el único impreso es el de Cordillera. Implementarlo tal como está firmado asignaría el mismo proveedor a las cien facturas | La razón técnica es sólida y está documentada. Sacar RF-11 de la spec exige que el cliente **vuelva a firmar** (`/approve-spec`) |
| **H1 · RF-04 (archivo original)** | Servir los bytes de `raw` a un navegador, contra la decisión escrita de que `raw` es evidencia. Es implementable — con una descarga autenticada, no exponiendo `raw` — pero es diseño nuevo | Renegociar RF-04 a «ver lo que el archivo decía», que es lo que hay. También reabre la firma |
| **H3 · RF-31 (confirmar un dato en duda)** | Sumar el valor al contrato de resolución y el campo a la cola. Es la mitad de la promesa de H6 de la spec: hoy una factura con el total borroso **sólo se puede aceptar como está o dejar apartada para siempre** | Difícil de sostener: es el corazón de «lo dudoso se pregunta, no se adivina» |

**H11 no admite las dos salidas.** El Artículo II no se negocia: una fila que nadie pudo interpretar
tiene que llegar a una persona. El requisito puede cambiar; la regla no.

**Orden sugerido:** H11 primero (es constitucional y el patrón ya existe en `triage`), después las
seis de frontend, después H2 y H9, y H13 y H12 **al final** —los diagramas y el `tasks.md` se
corrigen contra lo que quede decidido, no antes—. H14 se puede hacer ya.

Hasta que H1, H3 y H11 estén resueltos o renegociados, **la 004 no pasa al `Code-Reviewer` ni se
archiva**.

---

# Segunda corrida — 2026-08-31

**Feature:** 004-invoices-suppliers · **Rol:** `Lead` · **Fecha:** 2026-08-31
**Spec:** `spec.md`, Aprobada el 2026-08-29 por Leandro Carriego — FDE (RF-01 a RF-53)
**Changeset:** rama `feat/004-to-009-remaining-specs`, HEAD `890918f`, **más el árbol de trabajo sin
commitear**, que es donde viven las migraciones `0014` y `0015`, `SupplierCorrection.tsx`,
`SupplierPeriod.tsx`, `SupplierContact.tsx`, `test_invoice_identity_file_and_doubt.py` y
`tests/architecture/test_invoice_screens_show_what_they_are_given.py`
**Suite verificada acá:** `uv run pytest` → **1531 passed · 9 skipped**, cobertura **91.11 %**
**Diagramas:** `bash scripts/diagrams/validate.sh docs/specs/004-invoices-suppliers/diagrams/` → los
siete compilan

> Esta corrida existe porque la anterior la implementó el `Developer` y la corrió el `Lead`: que
> quien escribió el código diga que ya está no es el gate, es lo que el gate audita. **La corrida
> anterior no se reescribe**: queda arriba tal como se emitió.

## Veredicto: 🟠 DERIVA MAYOR — cerrada el 2026-08-31

> **Estado al cierre.** El único punto que bloqueaba —N-1, el criterio de RF-11— se resolvió por la
> salida que el Artículo V reserva al humano: **corregir la spec**. El criterio y la regla del CUIT
> se reescribieron, y el cliente volvió a firmar el 2026-08-31. **No se tocó una línea de código.**
> Quedan N-2, N-3 y N-4, que no bloquean, y la 004 pasa al `Code-Reviewer`.
>
> El veredicto se conserva tal como se emitió; lo que sigue es lo que decía el día que lo dijo.

**Los catorce hallazgos de la primera corrida están cerrados**, y se verificaron abriendo los
archivos, no leyendo los documentos que dicen que se cerraron. Los tres ausentes —RF-04, RF-11,
RF-31— tienen implementación con evidencia localizable; los once parciales están completos; el
agujero del Artículo II tiene su handler; `plan.md` y `tasks.md` describen lo que el código hace, y
los siete diagramas volvieron a ser verdad —tres porque se corrigieron, y **cuatro porque el código
alcanzó a lo que ya dibujaban**.

**Queda un punto, y no se puede cerrar escribiendo código:** el criterio de aceptación de RF-11 dice
*«una factura que trae CUIT queda asociada a su proveedor **sin pasar por revisión**»*, y lo que el
sistema hace es apartarla primero y resolverla sola después, cuando llega su archivo. La razón es
sólida y está documentada; el criterio firmado, en cambio, no describe eso. **Es exactamente la
decisión que el Artículo V le reserva al humano**, así que el gate queda frenado hasta que decidas,
no hasta que alguien programe algo.

**Alcance no pedido: ninguno.** Se recorrió el sentido inverso otra vez, incluida toda la superficie
nueva —cinco columnas de `0014` y `0015`, la ruta del archivo, los tres campos del contrato de
resolución, los cuatro componentes nuevos—: cada una tiene un requisito firmado que la pide. Y una
superficie muerta **se sacó**: el campo `action` de `InvoiceReviewResolution`, que la corrida
anterior había anotado para el `Code-Reviewer`, ya no está en el contrato.

## Cómo se verificó esta vez

Contra el código. Los catorce cierres se auditaron uno por uno, buscando el símbolo que el
`plan.md` dice que lo cierra y **abriendo el archivo para leer qué hace**, no sólo comprobando que
el nombre exista. Además se corrió la suite entera y se validaron los siete diagramas leyéndolos
paso por paso contra el servicio.

## Los catorce hallazgos de la primera corrida

| # | Cerrado | Evidencia leída en esta corrida |
|---|---|---|
| **H1 · RF-04** | ✅ | `purchases/routes.py:705-718` devuelve `Response(content=document.content, media_type=…)` con `Content-Disposition`; `service.py:973-989` sirve desde `core.invoice_document.content` (migración `0014`) y contesta 404 si el archivo todavía no bajó; el enlace «Abrir el archivo original» está en `facturas/[invoiceId]/page.tsx:88` y en `ReviewQueue.tsx:158`. **No lee `raw`**: la copia la alimenta `InvoiceFileRead.content` (`shared/events/catalog.py:663`). Tests `TestTheOriginalFile` (4 casos, uno de ellos que ventas no llega) |
| **H1 · RF-11** | ⚠️ | Implementado, y con dos barreras: `_issuer_tax_id_in` (`ingestion/documents.py:246`) descarta la línea del cliente, y `_identify_by_tax_id` (`purchases/service.py:797`) sólo acepta un CUIT de los ocho del padrón. Cinco tests en `TestTheTaxIdIdentifies`. **Lo que no cierra es el criterio de aceptación** — hallazgo N-1 abajo |
| **H2 · RF-02, RF-30** | ✅ | `portal/handlers.py::bring_held_invoice_files`, suscripto a `InvoicesNeedingReview`, con `case.needs_document` para no pedirle al portal un archivo que ya está |
| **H3 · RF-31** | ✅ | `InvoiceReviewResolution` lleva `number`, `issued_on` y `total` (`schemas.py`); `resolve_invoice` los aplica **antes** de asignar proveedor y `_correct_invoice_fields` publica `ManualChangeRecorded` sólo cuando el valor cambia, recalcula el vencimiento y mueve el calendario. En la pantalla, `HEADER_FIELDS` de `ReviewQueue.tsx:16-40` son tres `input` con «El archivo dice …» debajo. Seis tests en `TestConfirmingOrCorrectingWhatIsInDoubt` |
| **H4 · RF-05** | ✅ | Columna **Formato** en `InvoiceTable.tsx:36,68-75`, con las escaneadas marcadas aparte |
| **H5 · RF-10** | ✅ | `proveedores/[supplierId]/page.tsx:100-127`: «Llega escrito de N formas», cada grafía con su fuente en el `title` |
| **H6 · RF-16** | ✅ | `SupplierCorrection.tsx` importa `correctSupplier` y es un `<form>` con motivo obligatorio; `SupplierContact.tsx:81-83` lo monta y sólo cuando `canCorrect` |
| **H7 · RF-22, RF-23** | ✅ | `SupplierPeriod.tsx` manda `since`/`until` por la URL con atajo al año en curso; `service.py:1354-1357` cuenta `excluded_in_review`, `excluded_inconsistent` y `excluded_out_of_period` por separado y la página los imprime por motivo. Test `test_the_three_reasons_are_counted_apart` |
| **H8 · RF-32** | ✅ | `resolved_by_name` en `InvoiceRead`, resuelto en `routes.py:164-168` con `ActorDirectory`, impreso en `facturas/[invoiceId]/page.tsx:116` |
| **H9 · RF-39** | ✅ | `core.invoice.last_batch_id` (migración `0015`): `_count_arrival` sólo suma si la factura vuelve **en el mismo lote**. La migración no corrige hacia atrás los contadores inflados, y dice por qué |
| **H10 · RF-51** | ✅ | `created_by_name` en `SupplierAliasRead`; `SpellingList.tsx:72` imprime «La asignó …», y una grafía que reconoció el sistema lo dice en vez de inventar un autor |
| **H11 · Artículo II** | ✅ | `triage/handlers.py:125-155`: `open_unreadable_invoice_rows` escucha `InvoiceRowsQuarantined` y abre un caso `unreadable_invoice_row`, que se ve en `/revision` (`CaseCard.tsx:264`) y se puede dar por revisado. Test `test_it_opens_a_case_instead_of_stopping_in_quarantine` |
| **H12 · `tasks.md`** | ✅ | La sección *Estado* se reescribió, las seis tareas mal marcadas llevan ⚠️→✅ con su texto original, y la tabla de cobertura apunta a las tareas 43-47. *(Dos textos quedaron viejos: hallazgo N-4)* |
| **H13 · Diagramas** | ✅ | `flujo-sistema`, `flujo-general` y `estados-factura` se corrigieron; `flujo-marcela`, `flujo-dueno` y `estados-grafia` **no hizo falta tocarlos**: describían el producto firmado y hoy el código los alcanzó. Los siete compilan y se leyeron contra el servicio. *(El README que los embebe quedó viejo: hallazgo N-3)* |
| **H14 · `plan.md`** | ✅ | D-2 y D-13 figuran cerrados por `8e40cf3`, y se agregó *Cómo se cerró cada uno* sin borrar la redacción original de los trece defectos |

## Tabla de trazabilidad — lo que cambió de estado

Los 53 requisitos se recorrieron de nuevo. **Cincuenta y dos están `Implementado`** con evidencia
localizable; abajo van sólo los catorce que la corrida anterior no daba por cumplidos, más el que
queda abierto. Los otros treinta y nueve conservan el estado y la evidencia de la tabla de arriba, y
se volvieron a comprobar contra la suite.

| Requisito | Antes | Ahora | Evidencia |
|---|---|---|---|
| RF-02 | ⚠️ Parcial | ✅ | `bring_held_invoice_files` (`portal/handlers.py`) |
| RF-04 | ❌ Ausente | ✅ | `routes.py:705` · `service.py::invoice_file` · `TestTheOriginalFile` |
| RF-05 | ⚠️ Parcial | ✅ | `InvoiceTable.tsx:36,68` |
| RF-07 | ⚠️ Parcial | ✅ | `triage/handlers.py::open_unreadable_invoice_rows` |
| RF-10 | ⚠️ Parcial | ✅ | `proveedores/[supplierId]/page.tsx:100-127` |
| RF-11 | ❌ Ausente | ⚠️ **Parcial** | `_identify_by_tax_id` (`service.py:797`) — el requisito sí; el criterio «sin pasar por revisión», no |
| RF-16 | ⚠️ Parcial | ✅ | `SupplierCorrection.tsx` · `SupplierContact.tsx:81` |
| RF-22 | ⚠️ Parcial | ✅ | `SupplierPeriod.tsx` · `page.tsx:47-52` |
| RF-23 | ⚠️ Parcial | ✅ | `service.py:1355` · `page.tsx:163-175` |
| RF-30 | ⚠️ Parcial | ✅ | `bring_held_invoice_files` · `ReviewQueue.tsx:152-169` |
| RF-31 | ❌ Ausente | ✅ | `InvoiceReviewResolution` · `_correct_invoice_fields` · `ReviewQueue.tsx::HEADER_FIELDS` |
| RF-32 | ⚠️ Parcial | ✅ | `schemas.py:248-250` · `routes.py:164` · `page.tsx:116` |
| RF-34 | ⚠️ Parcial | ✅ | `review_queue` · `facturas/revision/page.tsx` · caso de `triage` |
| RF-39 | ⚠️ Parcial | ✅ | `last_batch_id` · `_count_arrival` (`service.py:703-705`) |
| RF-51 | ⚠️ Parcial | ✅ | `SpellingList.tsx:72` · `SupplierAliasRead.created_by_name` |

**Cierre: 52 implementados · 1 parcial · 0 ausentes.**

## Hallazgos

| # | Tipo | Qué dice el artefacto | Qué hace el código | Rol dueño | Acción |
|---|---|---|---|---|---|
| **N-1** | Requisito sin implementar | **RF-11**, criterio firmado: «una factura que trae CUIT queda asociada a su proveedor **sin pasar por revisión**» | La tabla del portal no publica CUIT, así que el número sólo existe dentro del archivo, y el archivo llega **después** de la fila. La factura se registra `PENDING`, entra en la cola y se cuenta entre las pendientes; su archivo se encola con 20 s de separación por factura (`PORTAL_HISTORY_SPACING_SECONDS`), o sea hasta ~33 min para la última de cien; recién ahí `_identify_by_tax_id` la resuelve sola. **Nadie la mira, pero pasa por revisión** | **humano** | Decidir: implementar o renegociar (abajo) |
| **N-2** | Deriva del plan | `data-model.md` es el mapa de las tablas de esta feature | Le faltan **cinco columnas nuevas**: `core.invoice_document.content`, `.content_type` y `.read_supplier_tax_id`; `core.invoice.last_batch_id`; y `staging.invoice_file_read.tax_id`. Las tres primeras son RF-04 y RF-11, la cuarta es RF-39. Están en `models.py:273,313,315,316` y en `ingestion/models.py:257` | Backend-Architect | Agregar las cinco filas |
| **N-3** | Diagrama desactualizado | `diagrams/README.md` embebe una copia de cada diagrama para leerlos sin abrir los `.mmd` | Las tres copias que se corrigieron —`estados-factura`, `flujo-general`, `flujo-sistema`— **quedaron viejas en el README**: sigue mostrando `Obtenida --> Dudosa` y el resto de la versión anterior. `scripts/diagrams/validate.sh` las vuelve a sincronizar solo, y esta corrida lo comprobó y **deshizo el cambio**, porque el `Lead` no edita artefactos de otro rol | Solution-Designer | Correr `validate.sh` y commitear el README |
| **N-4** | Tarea sin respaldo | Dos tareas de `tasks.md` marcadas hechas describen algo que sigue sin existir: **T-12** («`resolve_supplier()` con sus dos caminos en orden —**CUIT primero**, nombre después—») y **T-7** («`GET /invoices/{id}/file`, que devuelve **el recorte de lo que el lector entendió**») | La tarea 43 decidió a propósito **no** meter el CUIT en `resolve_supplier` —y el docstring de la función lo explica—, y la 44 cambió `/file` para que devuelva los bytes. El ⚠️→✅ de T-12 y el ✅ de T-7 dicen otra cosa | Backend-Architect | Anotar el cierre real al lado, sin borrar el texto original |

**No son hallazgos, pero conviene saberlos:**

- **Las referencias de línea de `plan.md` → *Contratos* quedaron viejas** (`GET /invoices` dice
  `routes.py:86` y está en `:94`; `/file` dice `:615` y está en `:705`). Es ruido de un archivo que
  creció, no una afirmación falsa sobre el producto.
- **El changeset se movió mientras se lo verificaba, y hay que decirlo.** Se corrió la suite
  entera tres veces: la primera erró en los 1501 tests que llegó a juntar, la segunda juntó 1540 y
  pasó **1531 · 9 skipped** con 91.11 % de cobertura, y la tercera juntó 1544 y falló dos
  —`TestTheInbox`, con `FileNotFoundError` sobre `messages-page-2026-08-29.html`—. **No es una suite
  inestable**: es que el árbol de trabajo cambió entre corridas. Ese fixture es de la **007** y se
  renombró a `messages-page-2026-08-31.html` en el medio; corridos de nuevo, los dos tests pasan.
  Nada de eso toca a la 004, cuyos fixtures y tests no se movieron — **pero el veredicto de arriba
  describe un árbol que otra tarea sigue editando**: lo que se verificó es el estado del 2026-08-31,
  y el `/review-feature` va a mirar otro si ese trabajo sigue.
- **`fetchFromApi` sigue colapsando 403, timeout y 500 en `null`** en las pantallas de proveedores y
  facturas, y `test_screen_reads.py` cubre sólo las pantallas de la 003. Ya estaba escalado al
  `Code-Reviewer` en la corrida anterior y sigue abierto.
- **Las cinco reglas del dominio se volvieron a contrastar y las cinco se cumplen.** `portal` no
  tiene un solo `httpx`/`requests`; ninguna escritura sobre `raw`; `purchases` **no lee** `raw` —
  mantiene su propia copia alimentada por `InvoiceFileRead`, que es lo que el Artículo IV prescribe;
  las credenciales sólo se leen de `settings` en `client.py:346-347`; y el Artículo II, que era H11,
  tiene su handler.

## Qué hacer con N-1

Es una sola decisión, y es tuya (Artículo V). Las dos salidas, con lo que cuesta cada una:

| Implementar lo que dice el criterio | Corregir el criterio |
|---|---|
| Habría que conocer el CUIT **antes** de registrar la fila, y el portal no lo publica en la tabla: el único lugar donde el número existe es dentro del archivo. Bajar el archivo de las cien facturas **antes** de registrarlas invierte el orden del pipeline, atrasa la pantalla de facturas hasta que termine la última descarga, y contradice la decisión escrita de que «la lista de facturas es usable desde el primer momento». No es una línea de código: es otro diseño | Cambiar el criterio de RF-11 por lo que el sistema hace —*«una factura que trae CUIT queda asociada a su proveedor sin que nadie la resuelva a mano»*—. Es lo que el negocio pedía: que el CUIT mande y que nadie tenga que mirarla. **Reabre el gate de la firma**: la spec vuelve al `Solution-Designer` y el cliente la firma de nuevo con `/approve-spec` |

Mi lectura, para que la tengas y no para reemplazar la tuya: **el código está bien y el criterio está
mal redactado**. Se escribió antes de saber que la tabla del portal no publica CUIT, y describe una
imposibilidad del origen, no una decisión del equipo. Pero corregir un criterio firmado sin el
cliente es exactamente lo que el gate de la firma existe para impedir, así que no lo toco.

> **Decidido el 2026-08-31: salida B, corregir el criterio.** El `Solution-Designer` reescribió el
> criterio de RF-11 y la regla *«El CUIT manda cuando está»* para decir dónde está escrito el CUIT y
> cuándo llega esa certeza, y el encabezado de `spec.md` volvió a `Borrador` con la firma del
> 2026-08-29 registrada como reabierta. **No se tocó una línea de código.** Falta que el cliente
> vuelva a firmar con `/approve-spec 004-invoices-suppliers`.
>
> **Firmada el 2026-08-31 por Leandro Carriego — FDE, y con eso N-1 queda cerrado.** El código y la
> spec vuelven a describir el mismo producto, y los 53 requisitos quedan `Implementado`.

**N-2, N-3 y N-4 no bloquean**: son artefactos desactualizados, van a su rol dueño y la feature sigue.

> **Los tres cerrados el 2026-08-31.**
>
> - **N-2** (`Backend-Architect`) — `data-model.md` documenta las cinco columnas, cada una en su
>   tabla, y las tres migraciones en vez de una. Al escribirlo aparecieron **dos afirmaciones que ya
>   eran falsas y este converge no había marcado**: que `resolved_by_user_id` y `resolved_at` «se
>   guardan y no se exponen» —hoy viajan en la respuesta, es H8—, y que la feature no toca `triage`,
>   cuando el caso `unreadable_invoice_row` es justamente lo que cerró H11. Las dos corregidas.
> - **N-3** (`Solution-Designer`) — `diagrams/README.md` regenerado. **Y el hallazgo estaba mal
>   escrito**: quien sincroniza el README es `scripts/diagrams/export.sh`, no `validate.sh`, que sólo
>   compila. Esta corrida había revertido esa sincronización creyendo lo contrario; queda hecha.
> - **N-4** (`Backend-Architect`) — T-12 y T-7 llevan entre corchetes cómo cerraron de verdad, sin
>   tocar su texto original. La 12 mantiene su ⚠️→✅ y la tabla de abajo aclara que cerró **por otro
>   lado**; la 7 vuelve a ✅ simple, porque no estaba mal marcada: describía lo que existía, y lo que
>   cambió después fue el producto.
>
> Con esto la 004 no tiene hallazgos abiertos de este gate y pasa al `Code-Reviewer`.

## Dónde queda la cadena

Resuelto N-1 —implementado o renegociado y vuelto a firmar—, y actualizados `data-model.md`, el README de
`diagrams/` y las dos filas de `tasks.md`, la 004 pasa al **`Code-Reviewer`** (`/review-feature`). Hasta entonces **no
pasa el gate de calidad y no se archiva**.
