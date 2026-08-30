# Facturas y proveedores — Plan técnico

<!--
  ARTEFACTO INTERNO. Acá van las decisiones técnicas que spec.md no puede llevar.
  No se exporta al cliente.
-->

**Feature:** 004-invoices-suppliers · **Spec aprobada el:** 2026-08-29 · **Fecha:** 2026-08-30
**Roles:** Backend-Architect (dueño) · Frontend-Architect (pantallas)

Insumos: `spec.md` firmada (RF-01 a RF-53), `research.md` (la decisión de lectura, medida), y el
relevamiento del portal del 2026-08-29 y 2026-08-30, cuyos fixtures están en
`backend/tests/fixtures/portal/`.

## Constitution Check

| Artículo | Cumple | Cómo |
|---|---|---|
| I — El origen es ajeno y de sólo lectura | ✅ | `portal` sólo navega y lee dos secciones nuevas, `/facturas` y `/estado-cuenta`, con Playwright. Ninguna escritura, ningún endpoint JSON interno. El padrón se lee expandiendo la fila de cada proveedor, que es lo que hace una persona |
| II — Nada se descarta | ✅ | Toda factura que no se pueda leer, cuyo proveedor no se resuelva, que venga de alguien fuera del padrón o que repita número con otro total, va a `staging` en cuarentena y genera un caso en `triage`, contado y visible (RF-13, RF-14, RF-28, RF-29, RF-38). Ningún dato se completa por suposición |
| III — Flujo unidireccional, `raw` inmutable | ✅ | `raw.portal_document` guarda la tabla, cada archivo de factura y la pantalla del padrón tal como llegaron, con su hash. Se lee y se vuelve a leer desde ahí; el reproceso al cambiar el motor de OCR no le pide nada al portal |
| IV — Las fronteras entre módulos son reales | ✅ | `purchases` no importa a nadie y nadie lo importa. Habla con `ingestion`, `triage` y `operations` por eventos del catálogo compartido. La única excepción sigue siendo `identity.dependencies` para autorizar rutas |
| V — Spec primero, y con firma | ✅ | `spec.md` en `Aprobado`, firmada por Leandro Carriego — FDE el 2026-08-29, con sus nueve historias y sus diagramas |
| VI — Lo que no está tipado y testeado no está terminado | ✅ | `mypy` sobre `app/`; unitarios de los tres parsers contra archivos fijados, integración del pipeline y de las rutas, y los cuatro fixtures de factura ya versionados (`TEST-03`) |
| VII — Las credenciales de terceros viven sólo en el entorno | ✅ | Se reusa el cliente de `portal`, que ya toma `PORTAL_USER` y `PORTAL_PASSWORD` del entorno y nunca los deja salir en un traceback |
| VIII — Un idioma para cada audiencia | ✅ | Código y eventos en inglés (`Invoice`, `Supplier`, `SupplierAlias`); pantallas, motivos de revisión y esta documentación, en español |
| IX — Las dependencias entran por la puerta | ✅ | `uv add pypdf pytesseract` con el lockfile en el mismo commit. `openpyxl` y `rapidfuzz` ya están. Tesseract y su idioma español entran por el `Dockerfile` del worker, no por `pip` |

**Excepciones solicitadas:** ninguna.

## Enfoque

La feature es **el mismo pipeline de la 001, con dos orígenes nuevos y una lectura más difícil**.
`portal` trae, `ingestion` interpreta, `purchases` guarda lo que es del negocio y `triage` se queda
con lo que necesita una persona. No hay una arquitectura nueva que inventar: hay que enchufar dos
secciones más en la que ya funciona.

Lo que sí es propio de esta feature es **de dónde sale cada dato**, y ahí el relevamiento cambió el
tamaño del problema. Los cuatro datos de cabecera —número, fecha, proveedor y total— **están en la
tabla renderizada de `/facturas`, completos y bien formados en las 100 filas**, y además adentro del
archivo. Se leen los dos y se comparan:

- **Coinciden** → el dato es certeza y la factura entra sin molestar a nadie (RF-27).
- **Difieren, o el archivo no se pudo leer** → la factura va a revisión con el recorte del archivo a
  la vista (RF-29, RF-30).

Eso da gratis la señal que RF-27 pide y que de otro modo habría que inventar como un umbral de
confianza del OCR. El umbral sigue existiendo para el caso en que la tabla no traiga el dato, pero
deja de ser lo único que separa un número bueno de uno inventado.

El **padrón sale de `/estado-cuenta`**, que es la única pantalla del portal que lo publica: ocho
filas —"cuenta corriente agrupada por proveedor real", lo dice el propio portal— y, al expandir cada
una, CUIT, correo, teléfono, domicilio y condición de pago. No hay una sección `/proveedores`: el
extractor tiene que hacer los ocho clicks. Del detalle expandido, esta feature toma sólo la ficha;
los movimientos de cuenta corriente que también aparecen ahí son **P5**, y no se cargan.

La identificación del proveedor tiene dos caminos, y el orden importa: **CUIT si está, nombre contra
el padrón si no** (RF-11, RF-12). Con una trampa medida: el único CUIT impreso en los archivos de
factura es el de **Cordillera**, el cliente, no el del emisor. Un parser que se quede con el primer
CUIT que encuentra le asigna el mismo proveedor a las cien facturas. Por eso el CUIT sólo se acepta
como identificador cuando **no** es el de Cordillera y coincide con uno del padrón; en la muestra
relevada eso significa que hoy se resuelve **siempre por nombre**, con `rapidfuzz` contra las ocho
razones sociales y sus grafías ya aprendidas, y lo que no sea concluyente va a revisión.

Tres mecanismos de la 003 se reusan enteros y no se reescriben:

- **`ManualChangeRecorded`** → `operations` ya guarda quién cambió qué, cuándo y con qué valor
  anterior. Es RF-18 sin escribir una tabla.
- **`CorrectionColumns` de `app/shared/corrections.py`** → el mixin existe justamente para esto; su
  docstring nombra a las facturas de compra. `purchases` se hace su propia tabla con esa forma, en
  su esquema, y conserva `portal_value` para poder deshacer.
- **`CorrectionConflicted`** → cuando el portal traiga un valor distinto del corregido a mano, la
  corrección gana y el conflicto se marca. Es RF-19, ya implementado para productos.

## Módulos afectados

| Módulo | Qué cambia | Nuevo |
|---|---|---|
| `portal` | Dos lecturas nuevas: la tabla de `/facturas` con la descarga de cada archivo, y `/estado-cuenta` con sus ocho filas expandidas. Publica lo extraído | No |
| `ingestion` | Tres parsers de archivo —PDF con texto, imagen escaneada, planilla—, el parser de la tabla de facturas y el del padrón. Compara tabla contra archivo y marca certeza o duda | No |
| `purchases` | **Todo lo del negocio**: padrón, grafías, facturas, correcciones de contacto, totales por período | **Sí** |
| `triage` | Dos `kind` nuevos de caso y sus reglas. Sin cambios de código: la cola ya es genérica | No |
| `operations` | Recibe el log de cambios manuales y publica la frecuencia de la consulta como parámetro | No |
| `identity` | Nada propio: sólo se monta su `dependencies.py` para que cada ruta declare su autorización (`PY-09`) | No |

**Por qué `purchases` y no `suppliers` + `invoices`.** La spec lo dice con todas las letras: son el
mismo problema mirado desde dos lados. Partirlo en dos módulos obligaría a que uno mantuviera una
proyección del otro por eventos —el costo que el Artículo IV manda aceptar— para poder listar las
facturas de un proveedor, que es la pantalla central de la feature. Cuando respetar la frontera
duele así, la frontera está mal trazada: son un módulo.

## Eventos de dominio

| Evento | Lo publica | Lo consume | Qué lleva |
|---|---|---|---|
| `InvoiceListExtracted` | `portal` | `ingestion` | `raw_document_id`, contenido de la tabla, `fetched_at`, `job_run_id` |
| `InvoiceFileExtracted` | `portal` | `ingestion` | `raw_document_id`, `invoice_number`, contenido del archivo, `content_type`, `file_kind` |
| `SupplierLedgerExtracted` | `portal` | `ingestion` | `raw_document_id`, contenido de la pantalla del padrón ya expandida |
| `SuppliersNormalized` | `ingestion` | `purchases` | Las ocho fichas: razón social, CUIT, correo, teléfono, plazo pactado |
| `InvoicesNormalized` | `ingestion` | `purchases` | Por factura: los cuatro datos, su origen —tabla o archivo—, y si coincidieron |
| `InvoiceRowsQuarantined` | `ingestion` | `triage` | Lo que no se pudo leer, con su motivo y el recorte del archivo |
| `InvoicesNeedingReview` | `purchases` | `triage` | Proveedor ambiguo, proveedor fuera del padrón, o repetida con otro total |
| `InvoicesRegistered` | `purchases` | — *(hoy nadie; P5 abre la deuda con esto)* | `invoice_id`, `supplier_id`, número, fecha, total |
| `QuarantineCaseResolved` | `triage` | `purchases` | **Ya existe.** Lleva `matcher` y `decision`: es lo que hace que asignar una grafía resuelva las apartadas |
| `QuarantineRuleRevoked` | `triage` | `purchases` | **Ya existe.** Deshace exactamente lo que esa asignación resolvía (RF-53) |
| `ManualChangeRecorded` | `purchases` | `operations` | **Ya existe.** RF-18, sin tabla propia |
| `CorrectionConflicted` | `purchases` | `operations` | **Ya existe.** RF-19: la corrección gana y el conflicto se avisa |

`InvoicesRegistered` es el único que hoy no tiene consumidor. Se publica igual porque es el hecho
consumado que **P5** necesita para abrir la deuda, y un evento sin suscriptores no cuesta nada; si
en el review se decide que es alcance no pedido, se saca en una línea.

## Datos

El detalle está en **`data-model.md`**. En una pantalla:

- **`raw`** — tres `PortalSection` nuevas: `INVOICES`, `INVOICE_FILE`, `SUPPLIER_LEDGER`. Nada
  cambia de forma: la tabla ya existe y es inmutable.
- **`staging`** — `staging.invoice_row` (lo que dijo la tabla), `staging.invoice_file_read` (lo que
  dijo el archivo, campo por campo, con su certeza y el recorte) y `staging.supplier_row`.
- **`core`** — `core.supplier`, `core.supplier_alias`, `core.invoice`, `core.invoice_file` y
  `core.purchase_correction` con las columnas de `CorrectionColumns`.
- **Migración** `0009_invoices_and_suppliers.py`, con las tres tablas de `staging`, las cinco de
  `core` y los índices de búsqueda por CUIT, razón social, fecha y estado de revisión (`DB-01`).

La clave de duplicado es **(proveedor, número)**, como se firmó. Se implementa como índice único
parcial sobre las facturas con proveedor identificado: mientras el proveedor no esté resuelto, la
factura no puede ser duplicada de nadie (RF-40), y el índice no la alcanza.

## Contratos

Toda ruta declara su autorización con la dependencia de `identity` (`PY-09`, Blocker, verificado por
`tests/architecture/test_route_authorization.py`). Ventas no aparece en ninguna (RF-06).

| Ruta | Quién | Requisitos |
|---|---|---|
| `GET /invoices` | dueño · compras | RF-03, RF-05, RF-39 a RF-46 |
| `GET /invoices/{id}` | dueño · compras | RF-03, RF-27, RF-39 |
| `GET /invoices/{id}/file` | dueño · compras | RF-04 |
| `GET /suppliers` | dueño · compras | RF-08, RF-24 |
| `GET /suppliers/{id}` | dueño · compras | RF-10, RF-15, RF-20 |
| `PATCH /suppliers/{id}` | dueño · compras | RF-16, RF-17, RF-18, RF-19 |
| `GET /suppliers/{id}/invoices` | dueño · compras | RF-21 |
| `GET /suppliers/{id}/totals` | dueño · compras | RF-22, RF-23 |
| `GET /invoice-review` | dueño · compras | RF-30, RF-34, RF-46 |
| `POST /invoice-review/{id}/resolve` | dueño · compras | RF-31, RF-32, RF-33, RF-36 |
| `GET /supplier-aliases` | dueño · compras | RF-51 |
| `POST /supplier-aliases/preview` | dueño · compras | **RF-48** — cuántas apartadas resuelve, antes de guardar |
| `POST /supplier-aliases` | dueño · compras | RF-47, RF-49, RF-50 |
| `DELETE /supplier-aliases/{id}` | dueño · compras | RF-52, RF-53 |

**Pantallas** (`frontend/app/(private)/`): `facturas/` con su lista, filtros y búsqueda;
`facturas/[id]/` con el archivo original; `proveedores/` y `proveedores/[id]/` con la ficha, sus
facturas y el total por período; `facturas/revision/` con la cola y el recorte a la vista;
`proveedores/grafias/` con las asignaciones guardadas.

## Cobertura de los requisitos

Los 53 requisitos firmados y dónde vive cada uno. Es la tabla que `/converge` va a auditar contra el
código cuando la feature esté implementada, así que nombra el lugar, no la intención.

| Requisitos | Dónde viven |
|---|---|
| RF-01, RF-07 | `operations`: la task programada con su parámetro de frecuencia, y la primera corrida que procesa lo que ya está en el portal sin bloquear el uso |
| RF-02, RF-25 | `portal`: descarga cada archivo y lo guarda en `raw.portal_document` con su hash, sección `INVOICE_FILE` |
| RF-26, RF-27, RF-28 | `ingestion`: los tres lectores —`pypdf`, Tesseract, `openpyxl`— y la comparación contra la tabla, que es lo que marca certeza o duda |
| RF-03, RF-04, RF-05 | `GET /invoices` y `GET /invoices/{id}/file`, más la pantalla `(private)/facturas` |
| RF-06, RF-36 | La dependencia de `identity` en las catorce rutas, verificada por `tests/architecture/test_route_authorization.py` |
| RF-08, RF-24 | `purchases`: `core.supplier`, alimentado por `SuppliersNormalized` desde `/estado-cuenta` |
| RF-09, RF-11, RF-12, RF-13 | `purchases`: la resolución del proveedor, CUIT primero y nombre después, con `rapidfuzz` contra el padrón y sus grafías |
| RF-10 | `core.supplier_alias`, una fila por grafía observada o decidida |
| RF-14 | La misma resolución, que aparta con motivo `supplier_not_in_padron` y **no** crea proveedores |
| RF-15, RF-20, RF-21 | `GET /suppliers/{id}` y la pantalla `(private)/proveedores/[id]`, con lo faltante marcado como *falta* |
| RF-16, RF-17, RF-18, RF-19 | `PATCH /suppliers/{id}` sobre `core.purchase_correction`, con `ManualChangeRecorded` y `CorrectionConflicted` reusados de la 003 |
| RF-22, RF-23 | `GET /suppliers/{id}/totals`, que excluye lo que está en revisión y devuelve cuántas excluyó |
| RF-29, RF-30, RF-31, RF-32, RF-33, RF-34 | `triage` con sus dos `kind` nuevos, `GET /invoice-review` y `POST /invoice-review/{id}/resolve` |
| RF-35 | Las tres columnas `NOT NULL` de `core.invoice`, más el `supplier_id` que sólo se completa al resolver |
| RF-37, RF-38, RF-39, RF-40 | El índice único parcial `(supplier_id, number)` y la columna `arrival_count` |
| RF-41, RF-42, RF-43, RF-44, RF-45, RF-46 | `GET /invoices` con sus filtros, y los índices de `core.invoice` y `core.supplier` que los sostienen |
| RF-47, RF-48, RF-49, RF-50, RF-51, RF-52, RF-53 | `POST /supplier-aliases` y su `preview`, sobre las reglas de `triage` y `core.supplier_alias` |

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Dos módulos, `suppliers` e `invoices` | Obligaría a una proyección entre ellos para la pantalla central de la feature. La frontera estaría mal trazada, no bien defendida |
| Leer **sólo** el archivo, como suponía el relevamiento | La tabla del portal trae los cuatro datos completos en las 100 filas. Ignorarla sería tirar una lectura determinista y quedarse con la difícil |
| Leer **sólo** la tabla y no abrir los archivos | Tienta, pero el archivo es la evidencia que la revisión le muestra a la persona (RF-30), y la única fuente si el portal deja de publicar una columna |
| Un servicio pago de OCR, o un LLM por API | El cliente respondió que **no** acepta costo por documento (brief 1.4.0). Detalle y medición en `research.md` |
| Un LLM local para las planillas irregulares | La medición mostró que buscar las etiquetas por nombre alcanza. Sería pagar hardware por un problema resuelto |
| `PyMuPDF` para el texto de los PDF | **AGPL**: contamina un producto propietario del cliente. `pypdf` hace lo mismo con licencia BSD |
| Dar de alta un proveedor desde la pantalla de revisión | El cliente lo descartó explícitamente en el `/clarify`: el padrón se amplía como decisión del negocio |
| Guardar el domicilio del proveedor, que el portal publica | La spec firmada pide cinco campos y no lo incluye. Sumar alcance en el plan es exactamente lo que la skill prohíbe |

## Riesgos

| Riesgo | Impacto | Cómo se mitiga |
|---|---|---|
| El OCR mide 100% sobre imágenes sintéticas limpias; una foto real no se parece a eso | Alto — es el 46% de las facturas | `raw` es inmutable: cambiar de motor y reprocesar las cien no le pide nada al portal. Y lo dudoso ya va a revisión, no a la base |
| El enlace de descarga del portal caduca a los 45 s | Medio — se pierde el archivo de una factura | Se descarga dentro del mismo paso que lo genera, como ya hace la extracción de precios |
| El padrón exige expandir ocho filas con click; si el portal cambia ese control, se rompe | Medio | Fixture fijado de la pantalla expandida y test contra él (`TEST-03`); el fallo levanta `ExtractionError` y queda visible, no en silencio |
| 24 grafías para 8 proveedores, y `rapidfuzz` puede acertar de más | Alto — un proveedor mal resuelto rompe la deuda y los totales | El umbral se calibra alto: en la duda va a revisión. Una asignación guardada se puede dejar sin efecto y devuelve las facturas a la cola |
| El CUIT impreso es el de Cordillera | Alto — asignaría el mismo proveedor a las cien | El CUIT sólo identifica si **no** es el de Cordillera y coincide con uno del padrón. Con test que lo fija |
| Cien facturas el primer día, 46 con OCR | Medio — la primera corrida es lenta | La lectura corre como task por factura, espaciada; la lista queda usable desde el primer momento y lo apartado se cuenta |

## Contexto de traspaso

**Para el Developer** — Empezá por `portal`: las dos secciones nuevas son navegación, y sin ellas no
hay nada que interpretar. Lo que **ya está decidido y no se rediscute**: la lectura es `pypdf` +
Tesseract 5 con `spa` + `openpyxl`, sin ningún modelo de lenguaje (`research.md`); el módulo nuevo es
uno solo, `purchases`; y las correcciones manuales reusan `CorrectionColumns` y los eventos de la
003 en lugar de una tabla propia. Lo que **no toques**: `raw` no se actualiza nunca —el reproceso
lee de ahí—, y ningún import cruzado entre `purchases` y otro módulo, ni siquiera "para leer". La
comparación tabla contra archivo es el corazón de la feature: es lo que decide si una factura entra
o va a revisión.

**Para el Tester** — Lo que se rompe de verdad son tres cosas. **La identificación del proveedor**:
probá el CUIT de Cordillera —tiene que ser ignorado—, dos grafías que se parecen entre sí, y una
grafía ya asignada que tiene que entrar directo. **La retroactividad de una asignación**: al
guardarla, las facturas apartadas con esa grafía se resuelven, y al dejarla sin efecto vuelven; el
número que la pantalla informa antes de guardar tiene que ser el mismo que después resuelve. **El
duplicado**: mismo número y proveedor conserva una sola, con otro total va a revisión, y dos
facturas sin proveedor identificado con el mismo número **no** son duplicadas. Todo contra los
fixtures de `backend/tests/fixtures/portal/` —los cuatro de factura y el del padrón—, nunca contra
el portal (`TEST-03`).

**Para el Code-Reviewer** — Mirá primero las **fronteras**: `purchases` es nuevo y es donde más fácil
aparece el import cruzado, sobre todo hacia `triage` para leer la cola. Después, **`PY-09`** en las
catorce rutas: ventas no puede llegar a ninguna, y RF-36 exige que sólo dueño y compras resuelvan.
Después, **`GEN-08`**: los eventos nuevos llevan identificadores y valores planos, nunca modelos.
Y el punto ciego propio de esta feature: que ningún dato dudoso termine escrito en `core` sin haber
pasado por una persona — Artículo II es lo que esta feature promete a cada paso.

---

## Lo que la implementación encontró

**Un duplicado sin proveedor identificado necesitaba una clave distinta.** El plan dice que la clave
de duplicado es *(proveedor, número)*, implementada como índice único parcial sobre las facturas con
proveedor resuelto — y eso está. Lo que faltaba era la otra mitad: **cómo se reconoce la misma
factura mientras el proveedor no está resuelto**. Buscar sólo por número fusionaba dos facturas
distintas y perdía una, que es justo lo contrario de RF-40.

La identidad de una factura sin proveedor resuelto es ***(el nombre tal como llegó escrito,
número)***. Así, dos facturas con el mismo número de dos proveedores que nadie identificó todavía no
son duplicadas —nadie sabe aún si son de la misma empresa—, y la segunda lectura de la misma
pantalla sigue reconociendo la misma factura en vez de duplicarla. Está fijado en
`test_two_without_a_supplier_are_not_duplicates_of_each_other`.

**El umbral alto tiene un costo visible, y es el correcto.** `supplier_match.threshold_pct` arranca
en 92 y además una coincidencia tiene que estar 6 puntos por delante de la segunda. Con eso,
`Aceros Belgano SA` —un error de tipeo— entra solo, y `Aceros Belgrano Sociedad Anonima` va a
revisión. Es deliberado: el plan dice que en la duda va a una persona, porque un proveedor mal
resuelto rompe la deuda y no se nota desde afuera. El dueño puede bajar el umbral desde el panel de
parámetros si el volumen de revisión molesta más que el riesgo.

**El archivo de la factura no se sirve tal cual.** `GET /invoices/{id}/file` devuelve el **recorte**
de lo que el lector entendió, no los bytes que guardó `raw`. `raw` es evidencia y no se le sirve a
un navegador; y lo que necesita quien revisa es lo que dijo el archivo al lado de lo que dijo la
tabla, que es precisamente lo que RF-30 pide mostrar.
