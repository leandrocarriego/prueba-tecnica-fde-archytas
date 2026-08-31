# Facturas y proveedores — Tareas

<!--
  ARTEFACTO INTERNO. Cada tarea mapea a una skill de agents/skills/ y es lo bastante
  chica como para terminarse de una sentada.
-->

**Feature:** 004-invoices-suppliers · **Plan:** `plan.md` · **Tareas:** 47

## Estado

**Escrito el 2026-08-30, después de la implementación.** Es una inversión del orden de la cadena y
conviene decirla de entrada: la 004 se construyó junto con la 005 a la 009 en un solo changeset
(rama `feat/004-to-009-remaining-specs`, PR #21) **sin que existiera este `tasks.md`**. Lo que sigue
no es un plan de trabajo por hacer: es el desglose que le faltaba al plan, reconstruido contra el
código que existe.

> ### Corregido el 2026-08-31, después del `/converge`
>
> **La versión anterior de esta sección decía «42 de 42 implementadas y verificadas» y que las nueve
> historias tenían su alcance construido. No era cierto**, y el `/converge` lo demostró abriendo los
> archivos que las tareas nombran: encontró **tres requisitos firmados sin implementar** —RF-04,
> RF-11 y RF-31— y **once a medias**. Seis tareas marcadas ✅ describían cosas que no existían.
>
> Eso es un hallazgo sobre **este documento**, no sólo sobre el código: un `tasks.md` que se escribe
> después de implementar y se marca entero contra el recuerdo de lo que se hizo no verifica nada.
> Las seis filas están abajo, en *Lo que estaba marcado y no estaba hecho*, con su redacción
> original — no se borran.
>
> **Lo que hay hoy**, verificado abriendo cada archivo:
>
> - Los **53 requisitos** tienen implementación con evidencia localizable, y los catorce hallazgos
>   del converge están cerrados (`converge.md`, y `plan.md` → *Cómo se cerró cada uno*).
> - **Cinco tareas nuevas**, 43 a 47, por el trabajo que faltaba. Están al final.
> - Suite: **1420 passed · 8 skipped**, cobertura sobre el umbral. `ruff`, `mypy`, `tsc`, `eslint` y
>   `prettier`, limpios.
>
> **Dónde queda la cadena.** El `/converge` corrió y dio deriva mayor; el humano eligió implementar,
> y lo implementado vuelve a necesitar **un converge nuevo** antes del `/review-feature`. Que la
> suite pase no lo reemplaza: el converge no pregunta si el código funciona, pregunta si es lo que el
> cliente firmó — y esta vez la respuesta la tiene que dar el gate, no quien escribió el código.

## Orden

Agrupadas por historia, en el orden de prioridad de la spec. Dentro de cada una:
migración → backend → frontend → tests.

> **Al terminar H1 hay algo entregable de verdad**: Marcela abre una pantalla y están las cien
> facturas con su número, su fecha, su proveedor y su total, traídas del portal sin que nadie las
> cargue, y ventas no puede entrar. Las ocho historias siguientes agregan sobre eso.

> **Tres tareas de H1 construyen cosas que son materia de H2 y de H5.** No es un error de
> agrupación: sin el padrón no hay proveedor que mostrar en la lista de facturas (RF-03), y sin la
> descarga del archivo no hay nada que abrir (RF-04). La migración, el padrón mínimo y la descarga
> tienen que existir antes de que H1 esté terminada; H2 y H5 construyen encima la identificación y
> la lectura.

### H1 — Todas las facturas en un solo lugar

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 1 | Migración `0011_invoices_and_suppliers`: las tres tablas de `staging` —`invoice_row`, `invoice_file_read`, `supplier_row`—, las cinco de `core` —`supplier`, `supplier_alias`, `invoice`, `invoice_document`, `purchase_correction` con las columnas de `CorrectionColumns`— y sus índices. El índice único de duplicado es **parcial sobre `(supplier_id, number)`**, así que no alcanza a una factura sin proveedor resuelto (RF-40). Los modelos entran a `app/models.py` en el mismo commit (`DB-01`). | `add_database_migration` | Developer | RF-35, RF-37, RF-40 |
| ✅ 2 | `portal`: tres `PortalSection` nuevas —`INVOICES`, `INVOICE_FILE`, `SUPPLIER_LEDGER`— y la navegación de `/facturas` con Playwright. Guarda la pantalla en `raw.portal_document` con su hash y publica `InvoiceListExtracted`. Sin endpoints JSON internos (Artículo I). | `add_integration` | Developer | RF-01, RF-02 |
| ✅ 3 | `portal`: la descarga del archivo de cada factura **dentro del mismo paso que genera el enlace**, porque caduca a los 45 s. Un documento por factura en `raw`, y `InvoiceFileExtracted` con su `content_type` y su `file_kind`. | `add_integration` | Developer | RF-02, RF-25 |
| ✅ 4 | `portal`: las tasks `extract_invoices`, `extract_invoice_file` y `extract_supplier_ledger`, con sus reintentos, y su registro en el planificador de `operations` para que corran con la frecuencia que el dueño configura. La primera corrida procesa lo que ya está en el portal sin bloquear la pantalla. | `add_celery_task` | Developer | RF-01, RF-07 |
| ✅ 5 | `ingestion`: `parse_invoices()` sobre el fixture fijado de `/facturas`. Lee los cuatro datos de cabecera de la tabla renderizada, y lo que no se pueda interpretar sale como fila de cuarentena, nunca descartado (Artículo II). | `add_backend_feature` | Developer | RF-03, RF-05 |
| ✅ 6 | `purchases`: el módulo nuevo —`models`, `repository`, `service`, `schemas`, `routes`, `handlers`— y el registro de facturas desde `InvoicesNormalized`. Ningún import de otro módulo (`GEN-02`). | `add_backend_feature` | Developer | RF-03, RF-35 |
| ✅ 7 | `GET /invoices` con paginación y `GET /invoices/{id}`, y `GET /invoices/{id}/file`, que devuelve **el recorte de lo que el lector entendió**, no los bytes de `raw`: `raw` es evidencia y no se le sirve a un navegador. **[Cerrada por la tarea 44: `/file` devuelve hoy los bytes tal como llegaron, desde la copia propia del módulo. La objeción era medio cierta —el Artículo III prohíbe *escribir* `raw`, no leerlo— y lo que impedía leerlo era el Artículo IV, porque `raw` es de `portal`.]** Las tres con la dependencia de autorización de `identity` (`PY-09`). | `add_backend_feature` | Developer | RF-03, RF-04, RF-05, RF-06, RF-44, RF-46 |
| ⚠️→✅ 8 | Pantalla `(private)/facturas`: la lista con número, fecha, proveedor, total y el formato en que llegó, y `(private)/facturas/[invoiceId]` con lo que dijo el archivo al lado de lo que dijo la tabla. | `add_frontend_feature` | Developer | RF-03, RF-04, RF-05 |
| ✅ 9 | Tests de H1: el parser de la tabla contra el fixture fijado (`TEST-03`), el registro de las cien facturas, y que **ventas no llega a ninguna de las rutas** — con `tests/architecture/test_route_authorization.py` verificando que las catorce declaran su autorización. | `add_tests` | Tester | RF-01, RF-03, RF-05, RF-06, RF-07 |

### H2 — Un proveedor por proveedor

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 10 | `ingestion`: `parse_supplier_ledger()` sobre el fixture de `/estado-cuenta` **con sus ocho filas ya expandidas**, del que toma sólo la ficha —razón social, CUIT, correo, teléfono, plazo—. Los movimientos de cuenta corriente que la misma pantalla publica son P5 y no se cargan. Publica `SuppliersNormalized`. | `add_backend_feature` | Developer | RF-08 |
| ✅ 11 | `purchases`: `remember_suppliers()` guarda el padrón y da de alta la grafía de cada razón social como grafía de sí misma, para que una factura escrita igual que el padrón entre sin preguntar. **El padrón es cerrado**: este es el único camino por el que nace un proveedor. | `add_backend_feature` | Developer | RF-08, RF-10 |
| ⚠️→✅ 12 | `purchases`: `resolve_supplier()` con sus dos caminos en orden —CUIT primero, nombre después— **[Cerrada por la tarea 43, y no como esta tarea la describe: el CUIT **no** entra en `resolve_supplier` ni va primero. La lista del portal no publica CUIT, así que el número sólo existe dentro del archivo, que llega después de la fila; RF-11 se contesta en `_identify_by_tax_id`, sobre una factura ya apartada. El criterio de la spec se corrigió y se volvió a firmar el 2026-08-31.]** y la trampa medida del relevamiento: el único CUIT impreso en los archivos es el de **Cordillera**, así que un CUIT sólo identifica si no es el suyo y coincide con uno del padrón. El nombre se compara con `rapidfuzz` contra las ocho razones sociales y sus grafías, con umbral parametrizado y margen sobre el segundo. | `add_backend_feature` | Developer | RF-09, RF-11, RF-12 |
| ✅ 13 | `purchases`: lo que no se resuelve con certeza abre un caso —`invoice_supplier_unresolved`— y lo que viene de alguien fuera del padrón abre otro —`invoice_supplier_not_in_register`—, los dos por `InvoicesNeedingReview`. **No se da de alta ningún proveedor**, ni desde el pipeline ni desde la revisión. | `add_backend_feature` | Developer | RF-13, RF-14 |
| ✅ 14 | `GET /suppliers` y pantalla `(private)/proveedores`: los ocho proveedores y no veinticuatro, con la cantidad del padrón a la vista y la aclaración de que el padrón sale del portal. | `add_frontend_feature` | Developer | RF-08, RF-24 |
| ✅ 15 | Tests de H2: el parser del padrón contra el fixture; una grafía ya asignada que entra directo; una variante cercana que se identifica y se recuerda; un nombre que se parece a dos proveedores que va a una persona; y una factura de fuera del padrón que **no** crea proveedor. | `add_tests` | Tester | RF-08, RF-09, RF-10, RF-12, RF-13, RF-14 |

### H3 — La ficha del proveedor, con lo que hoy está en la libreta

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 16 | `purchases`: `core.purchase_correction` con el mixin `CorrectionColumns` de `app/shared/`, en el esquema de este módulo. Tabla propia y no una compartida: `purchases` tiene que poder preguntar si un dato tiene corrección mientras aplica una lectura, y pedírselo a `operations` sería el import que la frontera prohíbe (Artículo IV). | `add_database_migration` | Developer | RF-18, RF-19 |
| ✅ 17 | `GET /suppliers/{id}`: la ficha con los cinco campos, y lo que el portal no publicó **marcado como falta** en lugar de en blanco — un espacio vacío se lee igual que un dato que nadie leyó. | `add_backend_feature` | Developer | RF-15, RF-20 |
| ✅ 18 | `PATCH /suppliers/{id}` sobre los tres campos corregibles —correo, teléfono, plazo—. Razón social y CUIT **no están en el contrato**, así que no hay forma de mandarlos. Guarda `portal_value` para poder deshacer y publica `ManualChangeRecorded`, que `operations` registra sin que este módulo sepa que existe una bitácora. | `add_backend_feature` | Developer | RF-16, RF-17, RF-18 |
| ✅ 19 | `purchases`: **la lectura del padrón no pisa lo corregido**. `remember_suppliers()` pregunta primero qué campos tienen corrección en pie, deja esos afuera de la escritura, y cuando el portal trae otro valor marca `CONFLICTED` y publica `CorrectionConflicted` — el mecanismo de la 003, reusado. La comparación va contra `portal_value` y no contra el valor corregido: el padrón publica el dato equivocado todas las mañanas, y avisar todos los días es no avisar nunca. | `add_backend_feature` | Developer | RF-19 |
| ✅ 20 | Pantalla `(private)/proveedores/[supplierId]`: la ficha con correo, teléfono y plazo, distinguiendo lo corregido a mano de lo que trajo el portal, y **señalando la diferencia** cuando una lectura posterior contradice una corrección. La corrección es la que se ve; lo que trae el portal se muestra al lado, nunca aplicado. | `add_frontend_feature` | Developer | RF-15, RF-19, RF-20 |
| ✅ 21 | Tests de H3: la ficha con lo faltante marcado; una corrección con su autor, su fecha y su valor anterior; y **los diez casos de RF-19** — el portal que no pisa, la diferencia que se señala, el aviso que sale, el padrón repitiendo lo de siempre que no es conflicto, la misma diferencia dos veces que avisa una, un tercer valor que vuelve a avisar, el silencio que no contradice, el campo sin corregir que sigue siendo del portal, y las dos formas de cerrar el conflicto. | `add_tests` | Tester | RF-15, RF-16, RF-17, RF-18, RF-19, RF-20 |

### H4 — Cuánto le compré a cada uno

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 22 | `GET /suppliers/{id}/invoices`: todas las facturas de un proveedor, paginadas, dentro de su ficha. | `add_backend_feature` | Developer | RF-21 |
| ⚠️→✅ 23 | `GET /suppliers/{id}/totals` con su período: el total facturado, y **cuántas facturas quedaron afuera** por estar en revisión. El número excluido viaja con el total y no aparte: un total que descarta filas en silencio es un total que el cliente desmiente la primera vez que lo suma a mano. | `add_backend_feature` | Developer | RF-22, RF-23 |
| ⚠️→✅ 24 | Pantalla: las facturas del proveedor y sus totales dentro de la ficha, con la frase de cuántas quedaron excluidas y por qué. | `add_frontend_feature` | Developer | RF-21, RF-22, RF-23 |
| ✅ 25 | Tests de H4: el total de un período contra la suma hecha a mano, y que una factura en revisión quede afuera **y se cuente**. | `add_tests` | Tester | RF-21, RF-22, RF-23 |

### H5 — Los datos salen del archivo de la factura

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 26 | `ingestion`: `read_invoice_document()` con los tres lectores según el formato —`pypdf` para el PDF con texto, Tesseract con `spa` para el escaneado, `openpyxl` para la planilla— y las etiquetas buscadas por nombre. Sin servicio pago ni modelo de lenguaje: el cliente no acepta costo por documento, y la medición de `research.md` dice que alcanza. `uv add` con el lockfile en el mismo commit (Artículo IX). | `add_backend_feature` | Developer | RF-25, RF-26 |
| ✅ 27 | `ingestion`: **la comparación de la tabla contra el archivo**, que es el corazón de la feature. Coinciden → el dato es certeza y la factura entra sola; difieren o el archivo no se pudo leer → la factura va a revisión con el recorte a la vista. Es lo que da la señal de RF-27 sin inventar un umbral de confianza del OCR. Un archivo de forma desconocida sale por `InvoiceRowsQuarantined` sin cortar el procesamiento de los demás. | `add_backend_feature` | Developer | RF-27, RF-28 |
| ✅ 28 | Tests de H5: los tres lectores contra los cuatro archivos fijados de `tests/fixtures/portal/` —PDF con texto, escaneado y planilla—, nunca contra el portal (`TEST-03`); un documento que coincide y deja la factura en paz, y uno que discrepa y la aparta con su recorte. | `add_tests` | Tester | RF-25, RF-26, RF-27, RF-28 |

### H6 — Lo dudoso se pregunta, no se adivina

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 29 | `purchases`: `GET /invoice-review` con la cola y su cuenta, y `POST /invoice-review/{id}/resolve`, que registra qué se decidió, quién y cuándo, y saca la factura de las pendientes. Las tres columnas de `core.invoice` son `NOT NULL` y el `supplier_id` sólo se completa al resolver: una factura sin número, fecha o total **no se puede guardar**, no es que no se guarde. Sólo dueño y compras (`PY-09`). | `add_backend_feature` | Developer | RF-29, RF-31, RF-32, RF-33, RF-34, RF-35, RF-36 |
| ⚠️→✅ 30 | Pantalla `(private)/facturas/revision`: la cola con el recorte del archivo al lado de cada dato en duda, la cuenta de pendientes, y el formulario que confirma o corrige. | `add_frontend_feature` | Developer | RF-30, RF-33, RF-34 |
| ✅ 31 | Tests de H6: una factura apartada que se resuelve y desaparece de la cola; el rechazo a ventas sobre las dos rutas de revisión; y que un dato en duda **nunca** termine escrito en `core` sin haber pasado por una persona — que es lo que el Artículo II promete a cada paso. | `add_tests` | Tester | RF-29, RF-31, RF-32, RF-33, RF-34, RF-35, RF-36 |

### H7 — Que no se duplique nada

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 32 | `purchases`: la detección de duplicado sobre `(proveedor, número)`, con `arrival_count` para decir cuántas veces llegó. Mismo número y proveedor con **otro total** va a revisión con el caso `invoice_duplicate`, no se descarta. Y mientras el proveedor no esté resuelto la identidad es *(el nombre tal como llegó escrito, número)*: dos facturas sin proveedor identificado no son duplicadas entre sí, porque nadie sabe todavía si son de la misma empresa. | `add_backend_feature` | Developer | RF-37, RF-38, RF-39, RF-40 |
| ✅ 33 | Tests de H7: la misma factura dos veces que queda una y se cuenta; el mismo número con otro total que va a una persona; y dos sin proveedor identificado que **no** son duplicadas. | `add_tests` | Tester | RF-37, RF-38, RF-39, RF-40 |

### H8 — Encontrar una factura sin recorrer la lista

> **La historia estaba vacía y se construyó el 2026-08-30.** Lo que había —la búsqueda por número
> y por el nombre tal como llegó escrito, el filtro por proveedor y el filtro por estado de
> revisión— construía RF-44 y RF-46 enteros y RF-42 a medias, y de los dos construidos ninguno
> tenía test. Las cuatro tareas de abajo cierran los seis requisitos.

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 34 | `purchases`: la búsqueda alcanza al **proveedor identificado** y no sólo al texto de la factura. `_matching()` suma un join izquierdo a `core.supplier` y busca en cuatro lugares: el número, el nombre tal como llegó escrito, la **razón social** del padrón (RF-42) y el **CUIT** (RF-41), este último comparando las dos formas sin puntuación —`30-70918273-4` y `30709182734` son el mismo número—. El join es izquierdo para que una factura que nadie pudo asignar siga apareciendo por su número, y sólo se agrega cuando hay algo que buscar. | `add_backend_feature` | Developer | RF-41, RF-42 |
| ✅ 35 | `purchases`: filtro por **rango de fechas de emisión**, `issued_from`/`issued_to`, que convive con el `due_from`/`due_to` de vencimiento sin reemplazarlo. Son dos preguntas distintas y el docstring del servicio lo dice: colapsarlas haría que «las facturas de mayo» signifique dos conjuntos distintos según quién pregunte. | `add_backend_feature` | Developer | RF-43 |
| ✅ 36 | **Ordenar por fecha y por total**, en los dos sentidos: el enum `InvoiceOrder` en `models.py` —vocabulario y no columna, para que el orden viaje `routes` → `service` → `repository` en un solo sentido y una pantalla no pueda pedir una columna que no existe—, con el `id` desempatando siempre para que la página dos no repita una fila de la uno. Y `components/purchases/InvoiceFilters.tsx`, que suma a la pantalla el buscador, el **selector de proveedor** (RF-44, que sólo existía por URL), el rango de emisión y el orden. Los filtros siguen viajando en la URL: una pantalla filtrada se comparte por chat y llega filtrada. | `add_frontend_feature` | Developer | RF-44, RF-45 |
| ✅ 37 | `tests/integration/features/test_invoice_search_and_order.py`: **17 tests sobre los seis requisitos**, no sólo sobre los cuatro nuevos. El CUIT con y sin guiones; la razón social encontrando una factura que llegó mal escrita —la mitad de RF-42 que la búsqueda por texto no cubría—; un CUIT que no es de nadie que no trae nada; el número que sigue encontrando una factura sin proveedor; el rango de emisión, sus dos extremos incluidos, y la prueba de que **no** es el de vencimiento; los cuatro órdenes; el orden conviviendo con un filtro; el desempate por id entre dos páginas; y los dos filtros que nadie probaba, más el contador que tiene que ser el de lo filtrado. | `add_tests` | Tester | RF-41, RF-42, RF-43, RF-44, RF-45, RF-46 |

### H9 — Que no me pregunten dos veces lo mismo

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 38 | `POST /supplier-aliases/preview`: cuántas facturas apartadas resuelve una asignación **antes** de guardarla. Es una tarea propia y no un detalle de la siguiente, porque el número que la pantalla promete tiene que ser el mismo que después ocurre — y eso sólo se sostiene si las dos preguntas comparten el mismo criterio. | `add_backend_feature` | Developer | RF-48 |
| ✅ 39 | `POST /supplier-aliases`: guarda la decisión como grafía `LEARNED` con su autor y su fecha, y **resuelve retroactivamente** las facturas ya apartadas que traían esa misma grafía. `GET /supplier-aliases` las lista con quién las decidió y cuándo. Una factura posterior con esa grafía entra directo. | `add_backend_feature` | Developer | RF-47, RF-49, RF-50, RF-51 |
| ✅ 40 | `DELETE /supplier-aliases/{id}`: deja la asignación sin efecto y **vuelve a apartar exactamente las facturas que esa asignación venía resolviendo** — ni más ni menos: las que alguien resolvió una por una no se tocan. | `add_backend_feature` | Developer | RF-52, RF-53 |
| ⚠️→✅ 41 | Pantalla `(private)/proveedores/grafias`: las asignaciones guardadas con su autor y su fecha, el aviso de cuántas resuelve antes de confirmar, y la acción de dejar una sin efecto. | `add_frontend_feature` | Developer | RF-48, RF-51, RF-52 |
| ✅ 42 | Tests de H9: que el número que la vista previa promete sea el que después ocurre, y que dejarla sin efecto devuelva exactamente lo que resolvió y no lo que decidió una persona. | `add_tests` | Tester | RF-47, RF-48, RF-49, RF-50, RF-52, RF-53 |

## Cobertura de requisitos

Los 53 requisitos firmados. Un `RF` sin tarea sería alcance que nadie se comprometió a hacer; un
`RF` sin test sería alcance que nadie verificó. **Las seis filas de H8 fueron las que este
desglose encontró vacías** —cuatro sin construir y dos construidas sin verificar—; las tareas 34 a
37 las cerraron.

**Y esta tabla se corrigió el 2026-08-31.** Tenía quince filas que apuntaban a una tarea que no
había hecho lo que decía —RF-04, RF-05, RF-11, RF-31 y las demás de la sección *Lo que estaba
marcado y no estaba hecho*—, así que una fila llena **no probaba nada**: probaba que alguien había
escrito un número. Las de abajo apuntan a las tareas 43 a 47.

| Requisito | Tareas | Test |
|-----------|--------|------|
| RF-01 | 2, 4 | 9 |
| RF-02 | 2, 3, 44 | 9, 47 |
| RF-03 | 5, 6, 7, 8 | 9 |
| RF-04 | 7, 44 | 47 |
| RF-05 | 5, 7, 44 | 47 |
| RF-06 | 7 | 9 |
| RF-07 | 4, 46 | 47 |
| RF-08 | 10, 11, 14 | 15 |
| RF-09 | 12 | 15 |
| RF-10 | 11, 45 | 15, 47 |
| RF-11 | 43 | 47 |
| RF-12 | 12 | 15 |
| RF-13 | 13 | 15 |
| RF-14 | 13 | 15 |
| RF-15 | 17, 20 | 21 |
| RF-16 | 18, 45 | 21, 47 |
| RF-17 | 18 | 21 |
| RF-18 | 16, 18 | 21 |
| RF-19 | 16, 19, 20 | 21 |
| RF-20 | 17, 20 | 21 |
| RF-21 | 22, 24 | 25 |
| RF-22 | 23, 24, 45 | 25, 47 |
| RF-23 | 23, 24, 45 | 25, 47 |
| RF-24 | 14 | 15 |
| RF-25 | 3, 26 | 28 |
| RF-26 | 26 | 28 |
| RF-27 | 27 | 28 |
| RF-28 | 27 | 28 |
| RF-29 | 29 | 31 |
| RF-30 | 30, 44 | 31, 47 |
| RF-31 | 46 | 47 |
| RF-32 | 29, 45 | 47 |
| RF-33 | 29, 30 | 31 |
| RF-34 | 29, 30, 46 | 31, 47 |
| RF-35 | 1, 6, 29 | 31 |
| RF-36 | 29 | 31 |
| RF-37 | 1, 32 | 33 |
| RF-38 | 32 | 33 |
| RF-39 | 32, 46 | 33, 47 |
| RF-40 | 1, 32 | 33 |
| RF-41 | 34 | 37 |
| RF-42 | 34 | 37 |
| RF-43 | 35 | 37 |
| RF-44 | 7, 36 | 37 |
| RF-45 | 36 | 37 |
| RF-46 | 7 | 37 |
| RF-47 | 39 | 42 |
| RF-48 | 38, 41 | 42 |
| RF-49 | 39 | 42 |
| RF-50 | 39 | 42 |
| RF-51 | 39, 41, 45 | 42, 47 |
| RF-52 | 40, 41 | 42 |
| RF-53 | 40 | 42 |

## El defecto de RF-19

**Encontrado y arreglado el 2026-08-30.** Vale anotarlo porque es exactamente la clase de cosa que
un `tasks.md` escrito a tiempo hubiera evitado, y porque el plan lo daba por hecho.

`plan.md` decía, en dos lugares distintos, que RF-19 estaba resuelto reusando `CorrectionConflicted`
de la 003 — *"ya existe"*, *"ya implementado para productos"*. Y era verdad a medias: **la
maquinaria existía y nadie la había enchufado al padrón**. `put_supplier()` escribía correo,
teléfono y plazo en cada lectura sin preguntar si alguien los había corregido, así que una
corrección duraba hasta la extracción siguiente y desaparecía sin que nadie se enterara.

Que un mecanismo exista en otro módulo no es que esté aplicado en éste. La tarea 19 existe por eso:
enchufarlo era trabajo, y sin fila nadie se comprometió a hacerlo.

**Un segundo defecto apareció al arreglarlo**: `correct_supplier()` insertaba siempre una corrección
nueva, así que corregir dos veces el mismo campo reventaba contra el índice único parcial
(`Key (purchases.supplier, 10, phone) already exists`). Ahora actualiza la que está en pie sin mover
`portal_value` — que es además la única forma de cerrar un conflicto, y por lo tanto parte de RF-19
y no un arreglo aparte.

## Lo que faltaba de H8

**Construido el 2026-08-30**, después de que este desglose encontrara la historia vacía. Vale
anotarlo porque es la razón por la que un `tasks.md` tardío se escribe igual.

`plan.md` daba H8 por cubierta en una línea —*"`GET /invoices` con sus filtros, y los índices de
`core.invoice` y `core.supplier` que los sostienen"*— y el listado efectivamente tenía filtros. Sólo
que no eran éstos:

| Requisito | Lo que había | Lo que faltaba |
|---|---|---|
| RF-41 buscar por CUIT | nada | La consulta comparaba contra `Invoice.number` y `Invoice.supplier_text`. **El CUIT vive en `core.supplier`**, y sin join no participaba de la búsqueda |
| RF-42 buscar por razón social | a medias | Buscaba la grafía con que llegó escrito el nombre. Una factura que entró como «ACEROS BELGANO S.A.» y se asignó igual no aparecía buscando «Belgrano» — que es justo lo que H2 dedicó una historia entera a unificar |
| RF-43 rango de fechas | otra fecha | `due_from`/`due_to` son de **vencimiento** y vienen de la 005. La fecha que la pantalla muestra es la de emisión |
| RF-45 ordenar | nada | El orden estaba fijo en `issued_on DESC, id DESC` dentro del repositorio, sin parámetro que lo moviera |
| RF-44 filtrar por proveedor | sin pantalla y sin test | El parámetro existía y sólo se podía usar escribiendo la URL a mano |
| RF-46 filtrar por revisión | sin test | Funcionaba, y nada avisaba si dejaba de funcionar |

**Lo que el arreglo decidió, y por qué.** El join a `core.supplier` es **izquierdo y condicional**:
izquierdo porque una factura que nadie pudo atribuir tiene que seguir encontrándose por su número
—si no, la cola de revisión se vuelve inbuscable justo cuando más se la mira—, y condicional porque
un listado sin búsqueda abierta no tiene por qué pagar un join que no usa. El CUIT se compara sin
puntuación en los dos lados, porque `30-70918273-4` y `30709182734` son el mismo número y cuál de
los dos se tipea depende de dónde se lo copió.

El orden es un enum —`InvoiceOrder`— y no un par de strings sueltos: así el nombre de la columna
nunca sale del backend, y una pantalla no puede pedir un orden que no existe. Lleva el `id` como
desempate siempre, que no es decoración: dos facturas del mismo día, o del mismo monto —un
proveedor que factura siempre el mismo servicio—, quedarían en el orden que la base tenga ganas, y
la página dos repetiría una fila que la página uno ya mostró.

## Notas para `/converge`

**H8 era la única historia con alcance sin construir, y se construyó.** El criterio de aceptación
de la spec —*"se escribe el CUIT de un proveedor y quedan sus facturas; se agrega un rango de
fechas y quedan sólo las de ese rango"*— ya se puede marcar, y lo verifican
`test_the_tax_id_finds_every_invoice_of_that_supplier` y
`test_a_range_keeps_only_what_was_issued_inside_it`.

**Dos criterios de la 003 se cierran acá**, y conviene verificarlos en este converge porque cuando
se escribieron no había módulo de facturas: corregir *"el número de comprobante de una factura
escaneada"* (RF-23 de la 003) y que *"Julián no puede corregir el total de una factura de compra"*
(RF-24 de la 003). Está anotado en `docs/specs/003-system-control/tasks.md` → *Notas para
`/converge`*.

**Dos preguntas del cliente siguen abiertas** y no son deuda de esta feature, pero un converge que
las ignore va a leer mal lo que encuentre:

- Los comprobantes de pago del portal referencian su propio recibo (`REC-####`) y no la factura, así
  que casi todos quedan esperando reparto manual. Es de la 005.
- Los fixtures de `/mensajes` y `/ventas` son **derivados**, no capturados. Los de esta feature
  —los cuatro de factura y el del padrón— **sí** están capturados del portal real, así que los
  tests de H1, H2 y H5 se apoyan en algo firme.

## Desvíos de la implementación

### 1. `purchases` terminó siendo más grande que la 004

El módulo que esta feature crea es el que después usaron la 005 (pagos y recibos), la 006
(calendario de vencimientos) y la 007 (órdenes y alertas). Sus `routes.py` y `service.py` llevan
hoy nueve routers y bastante más que facturas y proveedores.

No es un desvío del plan —el plan decía *"`purchases`: todo lo del negocio"*, y las tres features
que vinieron después son del mismo negocio y del mismo lenguaje—, pero cambia lo que hay que mirar
en el review: **la frontera que se defiende ya no es sólo la de la 004**, y el archivo más largo del
backend es de este módulo.

### 2. El archivo de la factura no se sirve tal cual

`GET /invoices/{id}/file` devuelve el recorte de lo que el lector entendió, no los bytes que guardó
`raw`. Está explicado en `plan.md` → *Lo que la implementación encontró*: `raw` es evidencia y no se
le sirve a un navegador, y lo que necesita quien revisa es lo que dijo el archivo al lado de lo que
dijo la tabla, que es lo que RF-30 pide mostrar.

### 3. El umbral alto tiene un costo visible, y es el correcto

`supplier_match.threshold_pct` arranca en 92, con 6 puntos de margen sobre el segundo. `Aceros
Belgano SA` —un error de tipeo— entra solo; `Aceros Belgrano Sociedad Anonima` va a revisión. Es
deliberado, está en el plan, y el dueño puede bajarlo desde el panel de parámetros de la 003 si el
volumen de revisión le molesta más que el riesgo.


## Lo que estaba marcado y no estaba hecho

Seis tareas llevaban ✅ y describían algo que no existía. Llevan **⚠️→✅** arriba: el ⚠️ es que
estaban mal marcadas, y la flecha, que hoy sí están. Su texto original no se toca — lo que hace útil
esta tabla es poder leer qué se creyó hecho.

| # | Lo que la tarea decía | Lo que había | Cerrada por |
|---|---|---|---|
| **8** | «la lista con número, fecha, proveedor, total **y el formato en que llegó**» | `file_kind` no aparecía en una sola pantalla: en todo el frontend estaba únicamente en los tipos generados | Tarea 44 |
| **12** | «`resolve_supplier()` con sus dos caminos en orden —**CUIT primero**, nombre después—» | No había ningún camino por CUIT, y el docstring de la función decía lo contrario de esta tarea | Tarea 43, **por otro lado**: el CUIT no entra en `resolve_supplier` ni va primero, porque la lista del portal no lo publica. Se contesta cuando llega el archivo |
| **23** | «cuántas facturas quedaron afuera **por estar en revisión**» | `excluded` sumaba en revisión, inconsistentes y fuera de rango, así que con período elegido dejaba de contestar RF-23 | Tarea 45 |
| **24** | «las facturas del proveedor y **sus totales** dentro de la ficha» | La pantalla llamaba a `/totals` sin `since` ni `until`: no había forma de pedir un período, que es lo que RF-22 pide | Tarea 45 |
| **30** | «la cola con el recorte del archivo al lado de cada dato en duda, la cuenta de pendientes, y **el formulario que confirma o corrige**» | La cola sólo dejaba asignar proveedor o aceptar la factura como estaba; ningún campo escribía un dato en duda, y el contrato tampoco lo aceptaba | Tarea 46 |
| **41** | «las asignaciones guardadas **con su autor** y su fecha» | La pantalla imprimía «Asignada por alguien»: el id viajaba y nunca se resolvía a un nombre | Tarea 45 |

**Lo que estas seis tienen en común**, y es lo que hay que llevarse: cinco de las seis no
necesitaban una línea de backend. El endpoint contestaba bien, el dato viajaba en la respuesta, y la
pantalla no lo usaba. Una tarea de frontend marcada contra el trabajo de backend que la habilita es
una tarea que nadie verificó.

## Las cinco tareas que faltaban

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 43 | **RF-11 por donde el CUIT existe.** El lector saca el CUIT del emisor descartando el de la línea del cliente (`_issuer_tax_id_in`); viaja en `InvoiceFileRead` y en `staging.invoice_file_read`; e `_identify_by_tax_id` resuelve con él una factura apartada por su proveedor, sólo si coincide con uno de los ocho del padrón. Migración `0014`. **No** entra en `resolve_supplier`: la tabla no publica CUIT, y un parámetro que nadie puede llenar es superficie muerta | `add_backend_feature` | Developer | RF-11 |
| ✅ 44 | **RF-04 y RF-05.** El módulo guarda su copia del archivo (`core.invoice_document.content`, migración `0014`) alimentada por el evento, porque leer `raw` sería el import que el Artículo IV prohíbe; `GET /invoices/{id}/file` la devuelve con su tipo y su nombre; el proxy del frontend pasa bytes en vez de texto; y la lista de facturas suma la columna **Formato**, con las escaneadas marcadas. Además, una factura **apartada** ahora baja su archivo (`bring_held_invoice_files`), que es de lo que dependen RF-30 y RF-11 | `add_feature` | Developer | RF-02, RF-04, RF-05, RF-30 |
| ✅ 45 | **Lo que la ficha del proveedor y las grafías no mostraban.** Las grafías en la ficha (RF-10); `SupplierCorrection.tsx`, el diálogo que corrige contacto desde la ficha con el motivo obligatorio (RF-16); `SupplierPeriod.tsx` y el desglose de lo excluido por motivo (RF-22, RF-23); y el nombre de quien resolvió una factura y de quien asignó una grafía, resuelto en la ruta con `ActorDirectory` (RF-32, RF-51) | `add_feature` | Developer | RF-10, RF-16, RF-22, RF-23, RF-32, RF-51 |
| ✅ 46 | **RF-31, RF-39 y el agujero del Artículo II.** Los tres datos de cabecera se confirman o se corrigen desde la cola, con `ManualChangeRecorded` por cada corrección y el vencimiento y el calendario recalculados (RF-31); `last_batch_id` hace que un arribo sea el portal publicando la factura dos veces en la misma lectura y no una relectura de la pantalla (RF-39, migración `0015`); y `triage` escucha `InvoiceRowsQuarantined`, que se publicaba sin oyente desde el primer día (RF-07, RF-34, Artículo II) | `add_feature` | Developer | RF-07, RF-31, RF-34, RF-39 |
| ✅ 47 | **Tests de las cuatro anteriores**, y el que mecaniza la lección: `test_invoice_identity_file_and_doubt.py` (19 casos sobre CUIT, archivo, corrección, cuarentena, excluidos y nombres) y `tests/architecture/test_invoice_screens_show_what_they_are_given.py`, que rompe el build si un campo que un requisito firmado necesita deja de leerse en la pantalla que ese requisito nombra. Y el test de duplicados que **codificaba el defecto** de RF-39 se corrigió y se le sumó el que faltaba | `add_tests` | Tester | RF-04, RF-05, RF-07, RF-10, RF-11, RF-16, RF-22, RF-23, RF-31, RF-32, RF-34, RF-39, RF-51 |
