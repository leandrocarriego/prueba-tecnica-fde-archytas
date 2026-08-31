# Tablero del negocio — Plan técnico

<!--
  ARTEFACTO INTERNO. Acá van las decisiones técnicas que spec.md no puede llevar.
  No se exporta al cliente.
-->

**Feature:** 009-business-dashboard · **Spec aprobada el:** 2026-08-31 · **Fecha:** 2026-08-31
**Roles:** Backend-Architect (el módulo, los cortes, los indicadores) · Frontend-Architect (las dos pantallas)

Insumos: `spec.md` firmada (RF-01 a RF-46, seis historias), los diagramas de `diagrams/`, y el código
construido en `backend/app/modules/{sales,catalog,ingestion,portal}/` y `frontend/`.

> **Este plan es un acta.** La feature se construyó el 2026-08-30, **antes** de que existiera este
> documento, y la spec se firmó el 2026-08-31 sobre código ya escrito. Lo que sigue describe **lo que
> hay**, verificado archivo por archivo. Lo que no hay no se disuelve en el cuerpo: tiene sección
> propia, *Lo que falta: la mitad de la H3*, y una *Deriva* al final.

## Constitution Check

| Artículo | Cumple | Cómo |
|---|---|---|
| I — El origen es ajeno y de sólo lectura | Sí | Una lectura nueva con automatización de navegador: `/ventas` (`portal/service.py:221-236`). Corregir una venta en el portal está declarado fuera de alcance en la spec, y no hay ninguna escritura |
| II — Nada se descarta | **Parcial, y es grave porque es la feature entera** | **Lo que se cumple:** una venta que repite otra con datos distintos, una que apunta a un producto inexistente y una con monto atípico quedan en `HELD`, contadas, visibles y con su motivo (`sales/service.py:90-97`, `:146-153`); una repetida idéntica queda `DISCARDED` y **no se borra** (`:81-87`). **Lo que no se cumple:** las cuatro anomalías que decide el parser —sin fecha, fecha inexistente, sin total, cantidad negativa— **nunca llegan a `core.sale`**: quedan en `staging.sale_row` en cuarentena, `SaleRowsQuarantined` se publica (`ingestion/service.py:760`) y **nadie está suscripto**. Doce de los registros que el relevamiento midió desaparecen de toda pantalla. **Decidido el 2026-08-31: se arregla dejándolas entrar como apartadas**, y con eso el artículo pasa a cumplirse entero. Ver *Lo que falta* |
| III — Flujo unidireccional, `raw` inmutable | Sí | `raw` → `staging.sale_row` → `core.sale`. Lo que informó el portal queda además en `core.sale.portal_values` aunque alguien corrija el registro (RF-02, RF-41), y esa columna es una **copia**, no una edición de `raw` |
| IV — Las fronteras entre módulos son reales | Sí | `sales` contesta «ese producto no existe» contra **su propia proyección** de los códigos del catálogo (`core.sales_product`), alimentada por `ProductsRegistered`. Los tres cortes que son del catálogo —precios, stock y altas— los sirve `catalog` por su propio endpoint, y el frontend compone los dos. Cero imports cruzados fuera de `identity.dependencies` |
| **V — Spec primero, y con firma** | **Fuera de orden** | Firmada el 2026-08-31, después de construir. Ver abajo |
| VI — Lo que no está tipado y testeado no está terminado | **Parcial** | Tipos completos, `mypy` limpio. 13 tests de integración (`tests/integration/features/test_business_dashboard.py`) y 5 unitarios de parser (`tests/unit/ingestion/test_section_parsers.py:195-240`). **El hueco que importa:** los cinco tests de parser verifican que una venta rota se aparta **en `staging`**, y ningún test verifica qué le pasa después — que es donde se rompe. Están verdes por la razón equivocada. Y el fixture de `/ventas` es derivado, no capturado |
| VII — Las credenciales de terceros viven sólo en el entorno | Sí | Se reusa el cliente de `portal`. Esta feature no manda avisos ni toca el canal |
| VIII — Un idioma para cada audiencia | Sí | Código y eventos en inglés; los motivos que lee una persona (`sales/service.py:45-48`) y las dos pantallas, en español |
| IX — Las dependencias entran por la puerta | Sí | Cero dependencias nuevas |

### Excepción al Artículo V, y quién la aprobó

El Artículo V dice que ninguna feature pasa a planificación técnica sin firma, y que una excepción
**la aprueba el humano y queda registrada en el plan**. Pasó en dos momentos, como en la 006 y la 007.

**Al construir, el 2026-08-30.** El humano pidió implementar las seis specs pendientes y, consultado
sobre las tres que estaban en borrador, respondió *"Las seis, igual"*.

**Al firmar, el 2026-08-31.** Una auditoría recorrió la spec contra el paso 1 de `approve_spec.md` y
lo que encontró se cerró escribiendo lo que ya estaba acordado en el brief, en otra spec firmada o en
el código —nunca con una decisión de producto nueva—. Cada elección quedó listada en la sección
**«Para confirmar al firmar»** de `spec.md`.

**Al firmar no creció el alcance.** RF-21 y RF-22 se reescribieron en su lugar para decir lo que el
sistema ya hace —el promedio de las ventas contadas de ese producto, sin ventana; diferencia
porcentual; tolerancia inicial de 300 %—. El requisito estaba vago; el código no. Los 46 requisitos
de la firma son los mismos 46 que había.

Y hay algo que la spec firmada **dice de sí misma** y que este plan tiene que recoger, porque es la
primera vez que una spec de este proyecto declara su propia divergencia: sobre el «deshacer», la
sección «Para confirmar al firmar» dice que corregir una venta *«se aplica sin pasar por el mecanismo
común de P9 y no se puede dejar sin efecto, a diferencia de lo que ya funciona sobre los productos y
sobre las compras»*. Es exacto, está verificado, y está abajo como D-4.

Queda dicho: **se firmó sobre código ya construido**. Para esta feature el gate del Artículo V es un
registro, no un filtro. Lo que el gate sí puede hacer todavía es `/converge`.

**Excepciones solicitadas:** la del Artículo V, ya registrada. Ninguna otra.

## Lo que hay que saber antes de confiar en esto

> **El fixture de `/ventas` es derivado, no capturado**, igual que el de la bandeja de la 007. El
> relevamiento midió las 588 filas y sus anomalías pero **no guardó el DOM**;
> `scripts/fixtures/derive_portal_fixtures.py` reproduce esos números exactos con la estructura de
> tabla que sí se capturó en las otras pantallas, y el README lo declara
> (`backend/tests/fixtures/portal/README.md:20, 131-144`).
>
> Las columnas —`Codigo`, `Fecha`, `Total`, `Cantidad`, `Producto`— son una deducción. El día que
> alguien entre al portal hay que recapturar y volver a correr `test_section_parsers.py`. Si los
> nombres no coinciden, `parse_sales` levanta `ExtractionError` y el fallo queda visible en
> `operations`, que es lo que tiene que pasar — pero es una lectura que nunca se probó contra la
> realidad.

**El corte de stock depende de que el origen siga publicando el stock cada día.** Es el supuesto que
la spec declara, y tiene una consecuencia concreta en el modelo: `core.stock_point` guarda **una foto
por producto y por día** (`catalog/models.py:265-291`), escrita al aplicar la lista de precios
(`catalog/service.py:309-315`), y el corte compara la del principio del período con la del final. Un
producto del que la lista **nunca publicó stock** en la ventana no cuenta como cero: queda excluido y el corte lo
dice (`catalog/service.py:1895-1901`). Si el origen deja de publicar el stock, el corte no falla:
empieza a excluir todo, que es la forma honesta de romperse.

## Lo que falta: la mitad de la H3

> **Decidido el 2026-08-31 por Leandro Carriego — FDE: se construye la salida 1**, la que trae las
> ventas rotas a `core.sale` como apartadas. Deja de ser deriva a la espera de una decisión y pasa a
> ser el trabajo de esta feature.

**Las cuatro anomalías que decide el parser no llegan a ninguna pantalla.**

El camino es este. `parse_sales` marca la fila con su `reason` cuando le falta el código, la fecha,
el total, o la cantidad es negativa (`parsers.py:1049-1092`). `normalize_sales` la guarda en
`staging.sale_row` con `status=QUARANTINED`, y al publicar `SalesNormalized` **filtra**:

```python
for row in rows
if row.status is RowStatus.VALID and row.code and row.sold_on is not None and row.total is not None
```
`backend/app/modules/ingestion/service.py:743-750`

Así que esas filas **nunca se convierten en un `core.sale`**. Se publica `SaleRowsQuarantined`
(`:760`) y **no hay un solo suscriptor** en toda la plataforma. Consecuencia, requisito por requisito:

| RF | Lo que pide | Qué pasa hoy |
|---|---|---|
| RF-16, RF-17 | La venta sin fecha, y la del 31/02/2025, quedan apartadas | Quedan en `staging`. **No aparecen en `/ventas/revision`** |
| RF-18 | La venta sin total queda apartada | Ídem |
| RF-19 | La venta con cantidad negativa queda apartada | Ídem |
| RF-23 | Cada venta apartada muestra por qué | El motivo está en `staging.sale_row.reason` y ninguna pantalla lo lee |
| RF-25, RF-28 | Cuántos registros excluyó cada indicador, y cuántas hay apartadas en total | Los cuenta sobre `core.sale`: **estas doce no están en el número**. El tablero dice que excluyó menos de lo que excluyó |
| RF-38 | Cargar la fecha que faltaba y que la venta entre a los indicadores | **Imposible**: `PATCH /sales/{id}` necesita un `core.sale` que no existe |
| RF-39, RF-40 | Cargar un valor estimado y que el indicador lo declare | Ídem: es sobre esas mismas ventas que se estimaría |

Son **doce de los 588 registros** que midió el relevamiento —3 sin fecha, 3 con fecha inexistente, 3
sin total, 3 con cantidad negativa—, y son la mitad de la H3.

**Lo que hay que construir.** Hay dos salidas y no son equivalentes:

1. **Que `SalesNormalized` lleve también las filas en cuarentena**, y que `sales` las registre en
   `HELD` con el motivo del parser. Es la que hace verdaderos a RF-23, RF-25, RF-28, RF-38, RF-39 y
   RF-40 de una sola vez, porque los pone en la misma pantalla y el mismo mecanismo de corrección que
   ya funciona para el producto inexistente y el monto atípico. Cuesta relajar el modelo:
   `core.sale.sold_on` y `.total` ya son nulables, así que **el modelo ya lo admite** — lo que hay
   que quitar es el filtro del publicador. Es la salida barata y la que la spec describe.
2. **Un suscriptor en `triage`** que abra un caso por fila, como el que ya existe para los precios
   (`triage/handlers.py:34-51`). Cierra el Artículo II y **no** cierra la H3: la venta seguiría sin
   estar en el tablero, sin contarse entre las excluidas, y corregirle la fecha no la haría entrar a
   ningún indicador. Resuelve otro problema.

**Se eligió la primera**, que es la que corresponde a esta spec. La segunda **no se descartó**: es la
brecha transversal del Artículo II que comparten 004, 005 y 007, sigue abierta en los tres planes, y
resuelve otra cosa — que ninguna cuarentena de `staging` tenga superficie humana. Que la 009 haga la
suya no la cierra para las otras tres.

**Un matiz que importa al construir:** una venta sin código no puede agruparse ni deduplicarse, así
que esa sí es candidata legítima a la segunda salida. Las otras cuatro tienen código y sólo les falta
un dato: son exactamente lo que RF-38 promete poder corregir. **Es la única decisión de diseño que
esta salida tiene abierta**, y se cierra antes de escribir la primera línea.

### Cómo queda el recorrido, para que no haya que reconstruirlo

1. **`normalize_sales` deja de filtrar** (`ingestion/service.py:743-750`): `SalesNormalized` lleva
   también las filas `QUARANTINED`, con su `reason`. El evento gana un campo o las filas viajan con
   el suyo; lo que **no** puede pasar es que el motivo del parser se pierda en el camino, porque es
   lo que RF-23 muestra.
2. **`register_sales` las registra en `HELD`** con ese motivo, sin pasarlas por
   `_why_not_countable` —que contesta otra pregunta— y **sin agruparlas** cuando no tienen código.
3. **Nada más cambia.** `core.sale.sold_on` y `.total` ya son nulables; `held_groups()` ya manda a
   `broken` todo grupo de una sola venta; `Indicator.excluded` ya cuenta las `HELD`; `correct_sale`
   ya exige fecha y total para pasar a `COUNTED`. Los ocho requisitos se hacen verdaderos **por
   dejar entrar la fila**, no por escribir lógica nueva para cada uno.

`SaleRowsQuarantined` se sigue publicando y sigue sin oyente. Eso es correcto y hay que no
«arreglarlo» de paso: la fila ya tiene superficie humana por la cola de ventas, y abrirle además un
caso en `triage` la haría aparecer dos veces, en dos pantallas de dos dueños distintos.

## Enfoque

La frase del cliente es la especificación: *«que se nos avise cuáles son, no que se sumen como si
fueran válidas»*. Todo lo demás sale de ahí.

**Tres estados y no dos.** `SaleState` es `COUNTED` | `HELD` | `DISCARDED`
(`sales/models.py:32-42`). `HELD` no es un error: es un registro esperando a una persona, contado y
visible. `DISCARDED` es la copia de un registro que ya se contó una vez —guardada, nunca borrada, y
mostrada al lado del que se eligió (RF-34)—. Los indicadores suman **sólo `COUNTED`**, en un único
lugar (`repository._filtered`), y por eso RF-04 y RF-15 no tienen código propio: son la consecuencia
de que todas las agregaciones compartan el mismo filtro.

**Repetidas idénticas se cuentan una sola vez, sin preguntar** (RF-11): no hay nada que decidir. Con
**un dato distinto**, ninguna de las dos suma hasta que alguien elija (RF-13, RF-15) — y la pantalla
las muestra enfrentadas con los campos en que difieren señalados (`service.py:227-231`), que es lo que
convierte «estas dos no son iguales» en una decisión de un segundo. Los campos que se comparan son
cuatro y están declarados en un solo lugar: `COMPARED = ("sold_on", "product_code", "quantity",
"total")` (`service.py:56`), y **el código no está entre ellos** porque es lo que las agrupó.

**El código se compara sin sus diferencias de escritura** (RF-10), y ahí está el número que el
relevamiento midió: 17 grupos mirando el código tal cual, 27 normalizándolo. `sale_code_key` saca
espacios, guiones, guiones bajos y puntos, y baja a minúsculas (`parsers.py:1022-1027`). **Nada más**:
un código que difiere en un dígito es otra venta, y ninguna normalización puede tapar eso.

**El `code_key` se guarda, no se deriva al leer.** Está en `staging.sale_row` y en `core.sale`, con
índice en las dos. Así el agrupamiento es una búsqueda por índice y significa **siempre lo mismo que
significaba cuando la fila aterrizó** — si la regla de normalización cambiara, los grupos viejos no se
redibujarían solos, que es la propiedad que se quiere.

**Lo habitual para un producto se deriva de lo ya contado**, no de una tabla que alguien mantenga
(RF-21). `average_total_for` promedia los totales de las ventas `COUNTED` de ese producto, **sin
ventana de tiempo** (`repository.py:117-133`). Una cifra típica guardada es una segunda verdad sobre
las mismas ventas, y queda vieja la primera vez que se corrige una. Consecuencia que la spec declara:
mientras un producto no tenga ninguna venta contada no hay contra qué comparar, y ninguna venta suya
se aparta por su monto.

**La comparación se hace cuando la venta entra, y el motivo se guarda con ella.** Por eso mover la
tolerancia vale para las ventas que entren a partir de ahí y no reevalúa las 588 del histórico. Está
dicho en la spec, en «Para confirmar al firmar», porque es la clase de cosa que sorprende después.

**Cada indicador informa lo que excluyó, incluso cuando excluyó cero** (RF-25, RF-27). `Indicator`
lleva `value`, `sales`, `excluded` y `has_estimates` juntos, en un solo tipo, para que **no se pueda
devolver un número sin su exclusión**: el que agregue un indicador nuevo tiene que llenar los cuatro
campos. «Cero excluidos» es una respuesta; un silencio no.

**Los tres cortes del catálogo los sirve `catalog`.** Precios, stock y altas son del catálogo, y
`sales` tendría que proyectarse el historial de precios entero para dibujar una curva. Son dos
endpoints y el frontend compone: `/dashboard/sales` y `/dashboard/catalog`, cada uno con su ventana,
que es exactamente lo que RF-05 pide.

## Módulos afectados

| Módulo | Qué cambia | Nuevo |
|---|---|---|
| `portal` | Una lectura: `extract_sales` (`service.py:221-236`) y su task (`tasks.py:196-199`) | No |
| `ingestion` | `staging.sale_row` (`models.py:378-...`), `parse_sales` y `sale_code_key` (`parsers.py:1015-1092`), y `normalize_sales` (`service.py:706-761`) | No |
| `operations` | Una entrada en `SYNC_JOBS` —`sales`, cada 24 h— y el parámetro de la tolerancia | No |
| `sales` | **Todo lo comercial**: registros, deduplicación, apartados, resolución, corrección e indicadores. Tres tablas, cinco rutas | **Sí** |
| `catalog` | `core.stock_point`, su escritura al aplicar la lista, los tres cortes (`service.py:1874-1932`) y `GET /dashboard/catalog` | No |
| `identity` | **Nada propio.** `Section.SALES` y `Section.DASHBOARD` los fija la 002, y esta feature los consume | No |
| Frontend | Dos pantallas (`/tablero`, `/ventas/revision`), un componente (`SalesReview.tsx`), `app/actions/sales.ts` y la entrada «Tablero» del menú | No |

**`sales` es un módulo nuevo y está justificado.** Una venta tiene lenguaje propio —el código, el
grupo repetido, la versión descartada, el valor estimado— que no es el de un producto ni el de una
factura, y lo único que necesita del resto del negocio es *qué códigos de producto existen*, que le
llega como proyección. La alternativa era meterlo en `catalog`, que ya es el módulo que aplica la
lista de precios, y habría mezclado «lo que el proveedor cobra» con «lo que la ferretería vende».

## Eventos de dominio

Todos del catálogo compartido (`backend/app/shared/events/catalog.py`), en pasado, `frozen`, con
identificadores y valores planos: `GEN-08` cumplido.

| Evento | Lo publica | Lo consume | Qué lleva |
|---|---|---|---|
| `SalesExtracted` (`:930`) | `portal` | `ingestion` | El documento crudo de `/ventas` |
| `SalesNormalized` (`:955`) | `ingestion` (`service.py:734`) | `sales` (`handlers.py:23`) | `batch_id`, las ventas **que se pudieron leer enteras**, y cuántas quedaron en cuarentena |
| `SaleRowsQuarantined` (`:966`) | `ingestion` (`service.py:760`) | **nadie** | Las filas que no se pudieron tipar. **Es el hallazgo central de esta feature**, ver *Lo que falta* y D-1 |
| `ProductsRegistered` (`:346`) | `catalog` | `sales` (`handlers.py:29`) y `triage` | Los códigos que el catálogo empezó a conocer. Es lo que hace posible RF-20 sin importar a nadie |
| `BusinessParameterChanged` (`:404`) | `operations` | `sales` (`handlers.py:36`), filtrado a **una** clave | La tolerancia de monto atípico (RF-22) |

**Esta feature no publica ningún evento propio de dominio.** No hay un `SaleHeld`, ni un
`SalesGroupResolved`, y es correcto: nadie más en la plataforma necesita enterarse de que una venta
quedó apartada. El día que P8 quiera avisar por WhatsApp que aparecieron ventas apartadas nuevas
—que la spec declara fuera de alcance, con nombre y apellido— ahí va a hacer falta el evento, y hoy
inventarlo sería un publicador sin audiencia y sin motivo.

**`SaleRowsQuarantined` sin oyente no es «legal y no rompe nada»**, a diferencia de los dos eventos
sin oyente de la 006. Acá el evento **es** la superficie humana de doce registros, y sin suscriptor
esos registros no existen para nadie.

## Datos

Tres tablas nuevas en `core` para `sales`, una en `core` para `catalog`, una en `staging`. **El
detalle completo —columnas, tipos, índices, qué se calcula y qué se guarda— está en
[`data-model.md`](./data-model.md).** Lo mínimo para orientarse:

- **`core.sale`** — un registro de venta y hasta dónde la plataforma responde por él: su estado, su
  motivo, lo que informó el portal (`portal_values`), si algún valor es estimado, de cuál otra venta
  es copia, y qué se decidió sobre él. Indexada por `code_key`, `state` y `sold_on`.
- **`core.sales_product`** — la proyección de los códigos que conoce el catálogo. Es el Artículo IV
  hecho tabla: sin ella, `sales` tendría que importar `catalog` para contestar RF-20.
- **`core.sales_setting`** — la proyección de la tolerancia.
- **`core.stock_point`** — una foto de stock por producto y por día, con
  `UNIQUE (product_id, observed_on)`, que es lo que hace que reprocesar la lista de un día no duplique
  el historial. Es de `catalog` y existe **por esta feature**.
- **`staging.sale_row`** — lo tipado, con su `code_key`, su `status` y su `reason`.

**Migraciones:** `0010_product_categories.py` trae `core.stock_point` y `staging.price_row.stock`
—que son de esta feature y viajaron en la migración de la 008, porque las seis se construyeron
juntas—; `0011_invoices_and_suppliers.py` trae `staging.sale_row`; `0012_messages_and_sales.py` trae
`core.sale`, `core.sales_product` y `core.sales_setting`. `DB-01` se cumple; el costo de tres
migraciones compartidas está en *Riesgos*.

## Contratos

Seis endpoints, todos con su autorización declarada (`PY-09`). **El detalle —query, cuerpos, errores
y códigos— está en [`contracts/sales-and-dashboard.md`](./contracts/sales-and-dashboard.md).**

| Método · ruta | Sección · nivel | Quién | RF |
|---|---|---|---|
| `GET /sales` | `SALES` · `READ` | dueño · ventas | RF-04, RF-15 |
| `GET /sales/review` | `SALES` · `WRITE` | dueño · ventas | RF-13, RF-14, RF-23, RF-26, RF-28, RF-30 |
| `POST /sales/groups/{code_key}/resolution` | `SALES` · `WRITE` | dueño · ventas | RF-29, RF-31 a RF-34, RF-36, RF-37 |
| `DELETE /sales/groups/{code_key}/resolution` | `SALES` · `WRITE` | dueño · ventas | RF-35 |
| `PATCH /sales/{sale_id}` | `SALES` · `WRITE` | dueño · ventas | RF-38, RF-39, RF-41 |
| `GET /dashboard/sales` | `DASHBOARD` · `READ` | dueño · ventas | RF-03, RF-05 a RF-07, RF-25 a RF-28 |
| `GET /dashboard/catalog` | `DASHBOARD` · `READ` | dueño · ventas | RF-42 a RF-46 |

**Compras no llega a ninguna** (RF-08), y no porque estas rutas hagan nada: la matriz le da `NONE`
sobre `SALES` y sobre `DASHBOARD` (`permissions.py:83-84`).

**`GET /sales/review` pide `WRITE` y no `READ`**, a diferencia de `GET /sales`. Es deliberado y es
RF-29: la cola de revisión es donde se decide, y quien no puede decidir no tiene por qué mirar la lista
de lo que otro tiene que decidir. Nadie fuera de dueño y ventas alcanza `WRITE` sobre `SALES`, así que
la diferencia no cambia el resultado hoy; cambia lo que la ruta **declara**, y ese es su trabajo.

## Mapa de requisitos

Los 46 firmados. **`✗` significa que no hay implementación**; **`~` que está a medias**. Cada uno de
esos tiene su entrada en *Lo que falta* o en *Deriva*.

| RF | Dónde vive |
|---|---|
| RF-01 | `SyncJob(key="sales")` (`operations/service.py:175-181`), `sales_sync.interval_hours` inicial 24 |
| RF-02 | Tres capas: `raw` (inmutable), `staging.sale_row`, y `core.sale.portal_values` (`sales/service.py:127-132`) |
| RF-03 | `monthly_totals` con `date_trunc('month')` sobre las `COUNTED` (`repository.py:80-93`). El «desde 2023» sale de los datos, no de una constante |
| RF-04 | `_filtered(..., SaleState.COUNTED, ...)`, compartido por las tres agregaciones (`repository.py:68-77`) |
| RF-05 | Dos endpoints con su propia ventana. **`~` en la pantalla**: `/tablero` le manda el **mismo** `desde`/`hasta` a los dos y no ofrece ningún control para cambiarlo (D-2) |
| RF-06 | `Indicator.sales`, de `totals()` |
| RF-07 | `SalesDashboard.invoiced`, primera sección de la pantalla (`tablero/page.tsx:52-70`) |
| RF-08 | `permissions.py:83-84`, `_PURCHASING: Level.NONE` en las dos secciones |
| RF-09 | `with_code_key(code_key)` (`repository.py:29-34`) |
| RF-10 | `sale_code_key` (`parsers.py:1022-1027`), guardado en las dos tablas |
| RF-11 | `_identical_among` compara los cuatro campos de `COMPARED`; la copia se guarda `DISCARDED` (`service.py:81-87`) |
| RF-12 | ✗ **`merged` se cuenta y sólo se loguea** (`service.py:107-110`). Ningún schema lo expone, y `excluded` lo mezcla con las descartadas por decisión humana (D-3) |
| RF-13 | `siblings and reason is None` → todas a `HELD` con `DUPLICATE_WITH_DIFFERENCES` (`service.py:90-97`) |
| RF-14 | `ReviewQueue.pending_groups` |
| RF-15 | Sale de RF-04: `HELD` no entra en ninguna agregación |
| RF-16 a RF-19 | ✗ **Se apartan en `staging` y no llegan a ninguna pantalla.** Ver *Lo que falta* |
| RF-20 | `_why_not_countable` contra `known_products()`, la proyección (`service.py:146`) |
| RF-21 | `average_total_for` + `drift > threshold` (`service.py:148-153`) |
| RF-22 | `sales.outlier_threshold_pct`, inicial `300` (`parameters.py:353-359`), proyectado por `BusinessParameterChanged` |
| RF-23 | `sale.reason`, mostrado en la tabla de rotas (`SalesReview.tsx:149`). **Alcanza sólo a las que llegaron a `core.sale`** |
| RF-24 | El parser nunca completa: cada dato ausente vuelve como `None` con su `reason` |
| RF-25, RF-27 | `Indicator` con `excluded` siempre presente; la pantalla dice «no se excluyó ningún registro» cuando es cero (`tablero/page.tsx:56-62`) |
| RF-26 | `~` El enlace a `/ventas/revision`, **y sólo cuando `held_total > 0`**. Las `DISCARDED` no están en esa cola: no hay forma de ver qué excluyó por unificación (D-3) |
| RF-28 | `SalesDashboard.held_total`, sin ventana. **No cuenta las doce de `staging`** |
| RF-29 | `require_section(Section.SALES, Level.WRITE)` en las cuatro rutas de decisión |
| RF-30 | `SaleGroup.versions` + `differences`, de `_differences_among` (`service.py:227-231`) |
| RF-31 | `POST .../resolution` con `action="keep"` y `sale_id` |
| RF-32 | El mismo, con `action="distinct"`: todas pasan a `COUNTED` |
| RF-33 | Sale de RF-04: cambiar el estado cambia lo que suman las agregaciones, sin recalcular nada |
| RF-34 | La descartada queda con `duplicate_of_sale_id` y se sigue devolviendo en el grupo |
| RF-35 | `DELETE .../resolution` → `undo_resolution`; `409` si no hay decisión que deshacer |
| RF-36 | `sale.decision` (JSONB), `resolved_by_user_id`, `resolved_at`, con el usuario del token |
| RF-37 | Sale de RF-13 al revés: `held_groups()` sólo devuelve `HELD` |
| RF-38 | `~` `PATCH /sales/{id}` acepta los cuatro campos; **la pantalla sólo ofrece corregir el producto**, con un `window.prompt` (D-5) |
| RF-39 | `~` `sale.is_estimated` existe y viaja; **ninguna pantalla lo pone en `true`**: la única llamada manda `false` fijo (D-5) |
| RF-40 | `Indicator.has_estimates`, de `has_estimates()`, y la pantalla lo dice. Verdadero, y hoy **nunca puede ser `true`** por D-5 |
| RF-41 | `portal_values` se escribe al registrar y **nunca se toca al corregir** (`service.py:118-134`) |
| RF-42 | `price_curve` sobre `core.price_point` (`catalog/repository.py:432-449`) |
| RF-43 | `stock_at(since, latest=False)` contra `stock_at(until, latest=True)` |
| RF-44 | `StockCut.ran_out = (closing == 0)`, listado aparte en la pantalla |
| RF-45 | `products_first_seen_between` sobre `Product.first_seen_at` |
| RF-46 | `~` `price_curve_excluded` (fijo en `0`) y `stock_excluded` existen; **el corte de altas no tiene `excluded`** ni en el schema ni en la pantalla (D-6) |

## Alternativas descartadas

- **Un solo endpoint de tablero.** RF-05 pide que cada corte elija su período **por separado**, y un
  endpoint único obligaría a mandar cuatro ventanas o a compartir una. Se descartó, y hay que decir
  que el frontend hoy hace exactamente lo que se descartó: manda una ventana a los dos (D-2).
- **Que `sales` calcule los cortes de precios, stock y altas.** Son del catálogo. `sales` tendría que
  proyectarse el historial de precios entero para dibujar una curva, y una proyección de esa longitud
  no es una proyección: es una copia de la tabla de otro.
- **Un valor «típico» por producto guardado en una tabla.** Es una segunda verdad sobre las mismas
  ventas y queda vieja la primera vez que se corrige una. Se deriva de lo contado.
- **Recortar el promedio de RF-21 a una ventana de tiempo** —los últimos doce meses, por ejemplo—.
  La spec lo pone sobre la mesa en «Para confirmar al firmar» y el cliente firmó sin ventana: todo lo
  que se sabe del producto entra en la comparación.
- **Reevaluar el histórico cuando el dueño mueve la tolerancia.** Está declarado en la spec como algo
  que **no** pasa. Habría convertido un cambio de parámetro en un reprocesamiento de 588 registros con
  motivos que cambian retroactivamente.
- **Elegir automáticamente la versión «más completa» de una repetida con diferencias.** Es lo que la
  regla de negocio prohíbe con todas las letras: cuando no hay forma honesta de elegir, el sistema no
  elige.
- **Borrar la versión descartada.** RF-34 pide lo contrario. `DISCARDED` es un estado, no un `DELETE`.
- **Deducir el stock movimiento por movimiento.** Declarado fuera de alcance: el origen no publica los
  movimientos, y deducirlos daría un número que nadie puede verificar. La foto diaria es lo que hay.

## Riesgos

| Riesgo | Impacto | Cómo se mitiga |
|---|---|---|
| **Doce registros rotos no llegan a ninguna pantalla**, y los indicadores dicen que excluyeron menos de lo que excluyeron | **Alto — es la promesa central de la feature.** Un tablero que subdeclara sus exclusiones es exactamente lo que la spec existe para evitar | **Se arregla dejando entrar la fila** (decidido el 2026-08-31). El riesgo que queda es el inverso: que al dejar de filtrar ingrese una fila sin código y rompa el agrupamiento por `code_key`. Es el punto 1 de la lista del Tester |
| **La deduplicación es lo que falla en silencio.** Si una repetida con datos distintos se contara, el tablero daría un número más alto y nadie lo notaría hasta que el cliente lo verifique a mano | Alto | Tres tests de integración lo fijan (`test_business_dashboard.py:61-107`). Es el bloque que nunca hay que debilitar |
| **El promedio de RF-21 se mueve solo.** `average_total_for` promedia las `COUNTED` de ese producto: cada venta que entra cambia el umbral para la siguiente, y resolver un grupo también | Medio | Es deliberado y está firmado. El efecto raro a conocer: **el orden en que llegan las ventas puede cambiar cuáles se apartan**, y ningún test lo fija |
| **El fixture de `/ventas` es derivado.** Las columnas son una deducción | Medio | El parser levanta `ExtractionError` si faltan. Recapturar en cuanto se pueda entrar al portal |
| **`stock_at` toma la foto *más cercana*, no la del día exacto.** Sin `since` no hay foto de apertura y **todos** los productos quedan excluidos del corte (`catalog/service.py:1889-1890`) | Medio | Es correcto —la lista se publica los días que se publica— y es sorprendente: abrir el tablero sin período muestra el corte de stock vacío con «N quedaron afuera». La pantalla no explica por qué |
| **Tres migraciones compartidas.** `core.stock_point` viaja en la `0010`, que es de la 008 | Medio | Se acepta: las seis se entregan juntas. Un rollback de la 009 sola no existe |
| **`TEST-05` mide 80 % sobre `app/` entera**, así que esta feature puede quedar floja sin que el umbral se entere | Medio | Está en la lista del Tester, con los casos concretos |

## Deriva contra la spec firmada (para `/converge`)

**Esto no es alcance nuevo ni una lista de tareas: es lo que no cierra entre el código y lo que se
firmó.** Se anota, no se arregla acá: qué corregir —el código o el acuerdo— lo decide el humano
(Artículo V).

| # | RF | Qué no cierra | Dónde |
|---|---|---|---|
| **D-1** | **RF-16 a RF-19, RF-23, RF-25, RF-28, RF-38, RF-39, RF-40** | Las cuatro anomalías del parser nunca llegan a `core.sale`: el publicador las filtra y `SaleRowsQuarantined` no tiene suscriptor. **Ya no es material de `/converge`: el 2026-08-31 se decidió arreglarlo**, y el recorrido está en *Lo que falta* | `ingestion/service.py:743-750`, `:760`; ningún handler |
| **D-2** | RF-05 | **La pantalla hace lo contrario de lo que se diseñó.** El backend son dos endpoints con ventana independiente, y `/tablero` le pasa el mismo `desde`/`hasta` a los dos —y no ofrece ningún control para elegirlos: se cambian editando la URL a mano—. RF-05 dice «cada corte elige su período **por separado**», y la propia pantalla imprime «Cada corte elige su propio período» debajo del título, que hoy es falso | `frontend/app/(private)/tablero/page.tsx:26-32, 47-49` |
| **D-3** | RF-12, RF-26 | **Cuántas repetidas unificó solo no se informa.** El contador `merged` se calcula y se loguea (`service.py:74`, `:87`, `:110-113`), y ningún schema lo lleva; `Indicator.excluded` suma `held + discarded`, mezclando lo que el sistema unificó con lo que una persona descartó. Y desde el indicador no se llega a las `DISCARDED`: `held_groups()` sólo devuelve `HELD`, así que **la mitad de lo excluido no se puede ver** | `sales/service.py:110-113`; `schemas.py:106-114`; `repository.py:134-142` |
| **D-4** | RF-41, y **RF-24 de la 003** | Corregir una venta **no pasa por el mecanismo común de correcciones manuales**: no publica `ManualChangeRecorded`, no crea fila en `operations.correction`, no aparece en `/historial` y **no se puede dejar sin efecto**, a diferencia de lo que ya funciona sobre productos (`catalog`) y sobre compras (`purchases`). `portal_values` conserva el original, así que RF-41 se cumple; lo que no se cumple es la promesa de la 003. **La propia spec firmada lo declara** en «Para confirmar al firmar» | `sales/service.py:317-373`, sin publicación; comparar con `purchases/service.py:1946-1960` |
| **D-5** | RF-38, RF-39, RF-40 | La pantalla ofrece corregir **sólo el código de producto**, con un `window.prompt`, y manda `is_estimated: false` fijo. La fecha, el total y la cantidad **no se pueden corregir desde ninguna pantalla** aunque el endpoint las acepte, y **no hay forma de marcar un valor como estimado**, con lo que `has_estimates` nunca puede ser `true` y RF-40 está cumplido sobre algo que no puede ocurrir | `frontend/components/sales/SalesReview.tsx:153-168` |
| **D-6** | RF-46 | El corte de **altas** no informa cuántos registros excluyó: `CatalogDashboard` lleva `price_curve_excluded` y `stock_excluded` y no un `new_products_excluded`. Además `price_curve_excluded` está **fijo en `0`** (`catalog/service.py:1920`), no calculado: dice «cero excluidos» sin haber contado | `catalog/schemas.py:230-244`, `service.py:1913-1932` |
| **D-7** | RF-36 | Al resolver un grupo eligiendo una versión, las descartadas quedan con `reason = DUPLICATE_IDENTICAL` —«Repetida idéntica: se cuenta una sola vez»—, que **es falso**: se descartaron porque una persona eligió otra, no por ser idénticas. Lo decidido está bien guardado en `decision`; el texto que lee la persona miente | `sales/service.py:290` |

### Código sin requisito firmado

Ninguno. `GET /sales` no tiene pantalla que lo consuma —el listado de ventas no existe como
pantalla— pero responde a RF-04 y RF-15 y es la superficie por la que se verifica el total a mano,
que es el criterio de aceptación de RF-04. No es código de más; es una pantalla de menos, y ningún
requisito la pide.

### Requisitos cumplidos que conviene no dar por obvios

- **RF-04, RF-15 y RF-33 no tienen código propio.** Los tres salen de que todas las agregaciones
  compartan `_filtered(..., COUNTED, ...)`. Un refactor que le dé a un indicador su propia consulta
  puede romper los tres sin tocar nada que se llame como ellos.
- **RF-08 sale de la matriz de la 002.** La 009 declaró niveles; no agregó permisos.
- **RF-02 se cumple tres veces** —`raw`, `staging.sale_row`, `portal_values`— y sólo la tercera es la
  que RF-41 usa. Las otras dos son el Artículo III.

## Contexto de traspaso

**Para el Developer** — Empezá por **D-1**, que es lo único que rompe la promesa central de la
feature, y arrancá por el lugar más chico: el filtro de `ingestion/service.py:743-750`. `core.sale` ya
tiene `sold_on` y `total` nulables, así que el modelo **ya admite** una venta rota; lo que hay que
decidir con el arquitecto antes de tocar nada es **qué hace `register_sales` con una fila sin
código**, porque sin código no se puede agrupar ni deduplicar y es la única de las cinco anomalías que
no encaja en la cola de ventas.

Lo que **no** hay que tocar, porque es una decisión tomada y testeada:

- **`code_key` se guarda, no se deriva.** Está en las dos tablas con índice, y significa siempre lo
  que significaba cuando la fila aterrizó. Derivarlo al leer «para no duplicar la regla» hace que
  cambiar la normalización redibuje los grupos viejos.
- **`COMPARED` son cuatro campos y el código no está entre ellos** (`service.py:56`). Es lo que
  decide si dos ventas con el mismo código son la misma venta. Agregar un campo cambia cuántos grupos
  necesitan a una persona; sacarlo, cuántos se unifican solos.
- **`average_total_for` no tiene ventana de tiempo.** Está firmado así, y la spec dice qué cambia si
  el cliente prefiere otra referencia.
- **`portal_values` se escribe una vez y nunca se toca.** Es RF-41 y es la evidencia.
- **`_filtered` es el único lugar donde vive «sólo lo contado».** Si un indicador nuevo no lo usa,
  RF-04 deja de valer para ese indicador y para ningún otro, que es la forma más difícil de notarlo.

**Para el Tester** — Hay 13 tests de integración (`test_business_dashboard.py`) y 5 de parser. Los de
parser **están verdes por la razón equivocada**: verifican que una venta rota se aparta en `staging`,
que es exactamente donde se queda. En orden de lo que puede romperse de verdad:

1. **El recorrido completo de una venta rota, de punta a punta.** Normalizar el fixture entero y
   verificar que las doce anomalías aparecen en `GET /sales/review` con su motivo, y que
   `held_total` las cuenta. **Escribilo antes de que el Developer saque el filtro**: hoy falla, y
   es exactamente lo que tiene que pasar de rojo a verde. Es el único test que demuestra que D-1
   se cerró de verdad, y los cinco de parser que hay no lo reemplazan porque miden `staging`.
   Y el caso borde que la decisión abrió: **una fila sin código** no se puede agrupar por
   `code_key`; verificá que llega a `broken` y no rompe ningún grupo.
2. **La deduplicación, que es lo que falla en silencio.** Si una repetida con datos distintos se
   contara, el número saldría más alto y nadie lo notaría hasta que el cliente lo verifique a mano
   — que es exactamente lo que la feature existe para evitar. Los tres tests que hay
   (`:61-107`) son los que nunca se debilitan.
3. **Los 27 grupos contra los 17.** El criterio de aceptación de RF-10 es un número medido:
   normalizando el código aparecen 27 grupos y sin normalizar 17. Hay un test de parser que lo mira
   (`test_normalising_the_code_finds_the_repetitions_the_raw_code_hides`); falta el de punta a punta,
   sobre `core.sale`.
4. **El orden de llegada y el promedio.** `average_total_for` se mueve con cada venta contada: dos
   corridas con las mismas 588 ventas en distinto orden **pueden apartar ventas distintas por monto
   atípico**. Ningún test lo fija, y es la clase de cosa que aparece como «el tablero da distinto» sin
   que nadie sepa por qué. Decidí con el Lead si eso es aceptable antes de escribir el assert.
5. **Deshacer.** Que `DELETE .../resolution` devuelva el grupo a `HELD` **y que el total del mes
   vuelva a su valor anterior** (RF-35). Hay un test (`:153-175`); verificá que compare el total y no
   sólo el estado.
6. **Lo que el sistema unificó solo no se puede deshacer.** `undo_resolution` da `409` cuando no hay
   `decision`, que es lo que la spec dice. Es la distinción que la firma dejó explícita.
7. **Los permisos por comportamiento.** No hay ningún test que haga una request real como compras
   contra `/dashboard/sales` o `/sales/review` y espere 403. RF-08 y RF-29 están probados por
   construcción.

El fixture de `/ventas` es **derivado**: un test que pase contra él no dice nada sobre el portal real.
`TEST-03` se cumple en la forma —nunca se prueba contra el portal en vivo— y no en la evidencia.

**Para el Code-Reviewer** — Cinco lugares, en este orden:

1. **`ingestion/service.py:743-750`.** El filtro del publicador. Son cuatro condiciones en un
   `if` dentro de un generador, y ahí se pierde la mitad de la H3. Es la línea más importante de la
   feature y la que menos parece serlo.
2. **`sales/repository.py:68-77` (`_filtered`).** Es donde vive «sólo lo contado», y de ahí salen
   RF-04, RF-15 y RF-33. Cualquier consulta nueva sobre `Sale` que no pase por acá es un indicador que
   suma lo que no debe.
3. **`GEN-02` sobre `sales`.** La tentación es importar `catalog` para saber si un producto existe, o
   para dibujar la curva de precios. Si aparece ese import, el diseño se rompió — y el test de
   fronteras lo va a decir, pero conviene entender por qué está la proyección antes de aprobar un
   cambio ahí.
4. **`sales/service.py:317-373` (`correct_sale`).** No publica `ManualChangeRecorded` y no es
   reversible, a diferencia de las correcciones de `catalog` y `purchases`. Es D-4, y **la spec firmada
   lo declara**: no es un hallazgo nuevo, es uno que hay que no perder de vista.
5. **`catalog/service.py:1913-1932`.** `price_curve_excluded=0` está escrito a mano, no calculado, y
   `new_products` no lleva su exclusión. Es D-6, y roza `GEN-07` en espíritu: un número que dice «cero»
   sin haber contado es peor que no mostrarlo.
