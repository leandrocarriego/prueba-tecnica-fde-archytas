# Tablero del negocio — Tareas

<!--
  ARTEFACTO INTERNO. Cada tarea mapea a una skill de agents/skills/ y es lo bastante
  chica como para terminarse de una sentada. Si una tarea no tiene skill, o no
  corresponde al proyecto, o falta la skill: preguntá antes de inventarla.
-->

**Feature:** 009-business-dashboard · **Plan:** `plan.md` · **Tareas:** 43

## Estado

**Este documento se escribió después de la implementación**, el 2026-08-31. La 009 se construyó en el
commit `b759a37`, junto con las otras cinco specs pendientes, sin que existiera un `tasks.md` que la
desglosara. El desglose de abajo es el que `plan.md` implica; las marcas dicen qué encontré en el
árbol de trabajo al recorrer archivo por archivo.

- ✅ **43 de 43**, al 2026-08-31. Las 29 que estaban construidas, más las 14 que faltaban: la mitad
  de la H3, los cuatro huecos de pantalla y los cuatro grupos de tests que no existían.
- **La suite queda en 1459 tests y 90,80 % de cobertura**, contra 1443 y 89,70 % antes de esta pasada.

> **Un defecto lo encontró un test escrito a propósito antes que el código.** La tarea 24 se escribió
> primero, en rojo, y al pasar a verde destapó que **todas las ventas sin código compartían el
> `code_key` vacío y se agrupaban como si fueran la misma venta repetida**: la pantalla le habría
> pedido a una persona que eligiera cuál de todas «vale». Está arreglado en `review_queue` y fijado
> por `test_a_record_without_a_code_is_held_on_its_own`.

> **Y un documento estaba mal, no el código.** `plan.md` y `data-model.md` decían que el corte de
> stock excluye un producto «sin foto en **alguno** de los dos extremos». Lo que el código hace —y
> documenta— es excluirlo cuando no hay foto **en ninguno**: con una sola observación dentro de la
> ventana, la misma foto es la de apertura y la de cierre y el producto se lee como «no se movió».
> Los dos documentos quedaron corregidos y el comportamiento quedó fijado por
> `test_a_single_observation_is_reported_at_both_ends`, con la pregunta que abre anotada ahí mismo.

> **La suite corrió entera y está en verde**: 1459 tests, 8 skips, 0 fallas, 90,80 % de cobertura.
> Lo que sigue faltando son las **pruebas de sistema del `Tester`** —abrir las pantallas a mano—, que
> ningún test automático reemplaza.

> **`/analyze` dio consistente** el 2026-08-31: los 46 RF tienen lugar en el plan y fila acá, las seis
> historias tienen tareas, y los 46 criterios de aceptación corresponden a un requisito. **Falta
> `/converge` y falta `/review-feature`**: los siete puntos de *Deriva* de `plan.md` son de `/converge`,
> y seis de ellos —D-1, D-2, D-3, D-5, D-6 y D-7— quedaron cerrados en esta pasada.

> **Decisión del humano (2026-08-31): las ventas rotas entran a `core.sale` como apartadas.** Es la
> tarea 18 y la 19, y es lo que hace verdaderos de una sola vez ocho requisitos firmados. Antes de esa
> decisión, RF-16 a RF-19 no tenían tarea posible: había dos salidas incompatibles y elegir una es del
> humano (`plan.md` → *Lo que falta: la mitad de la H3*).

## Orden

Agrupadas por historia, en el orden de prioridad de la spec. Dentro de cada una:
migración → backend → frontend → tests.

> **Al terminar H1 hay algo entregable de verdad**: Julián abre `/tablero` y lee cuánto se facturó,
> sobre cuántas ventas, cuántos registros quedaron afuera del número, y la facturación mes a mes desde
> que hay datos. Las cinco historias siguientes agregan encima; ninguna es requisito para que la
> primera funcione.

> **Cuatro tareas de H1 son cimiento y no se ven en pantalla** —el catálogo de eventos, el parser, la
> normalización y las migraciones—. Sin la tarea 4 no hay `code_key`, y sin `code_key` la H2 entera no
> tiene de dónde agarrarse.

### H1 — Cuánto facturamos, mes por mes

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 1 | `app/shared/events/catalog.py`: `SalesExtracted`, `NormalizedSale`, `SalesNormalized` y `SaleRowsQuarantined`. Todo lo demás cuelga de acá. | `add_backend_feature` | Developer | RF-01, RF-02 |
| ✅ 2 | `portal.extract_sales` con su task, más la entrada `SyncJob(key="sales")` en `operations` y el parámetro `sales_sync.interval_hours` (inicial 24). **Automatización de navegador, no el endpoint JSON del portal** (Artículo I). | `add_integration` | Developer | RF-01 |
| ✅ 3 | Migraciones: `staging.sale_row` en la `0011`, y `core.sale` + `core.sales_product` + `core.sales_setting` en la `0012`, con el enum `sale_state`. Los tres índices de `core.sale` —`code_key`, `state`, `sold_on`— son los que sostienen el agrupamiento y las agregaciones. | `add_database_migration` | Developer | RF-02, RF-09, RF-10 |
| ✅ 4 | `parse_sales` y `sale_code_key` en `ingestion/parsers.py`, con sus **cinco tests unitarios contra el fixture fijado** (`TEST-03`). El parser decide las cuatro anomalías de RF-16 a RF-19 y **nunca completa un dato por suposición** (RF-24). | `add_backend_feature` | Developer | RF-02, RF-10, RF-16, RF-17, RF-18, RF-19, RF-24 |
| ✅ 5 | `ingestion.normalize_sales`: tipar la pantalla a `staging.sale_row` y publicar el lote. | `add_backend_feature` | Developer | RF-01, RF-02 |
| ✅ 6 | Módulo `sales`: modelos, repositorio con **`_filtered` como único lugar donde vive «sólo lo contado»**, y `register_sales`. De ese filtro salen RF-04, RF-15 y RF-33 sin código propio. | `add_backend_feature` | Developer | RF-02, RF-04, RF-06, RF-15, RF-20, RF-33 |
| ✅ 7 | Rutas `GET /sales` y `GET /dashboard/sales`, más las secciones `SALES` y `DASHBOARD` en la matriz de `identity` con `_PURCHASING: NONE` en las dos. RF-08 es la matriz, no una comprobación en la ruta. | `add_backend_feature` | Developer | RF-03, RF-04, RF-05, RF-06, RF-07, RF-08 |
| ✅ 8 | Pantalla `(private)/tablero`: el facturado como **primer contenido**, con cuántas ventas sumó y cuántos registros excluyó, y la facturación mes a mes. | `add_frontend_feature` | Developer | RF-03, RF-06, RF-07 |
| ✅ 9 | **RF-05 en la pantalla.** Hoy `/tablero` le manda el **mismo** `desde`/`hasta` a los dos endpoints y no ofrece ningún control: el período se cambia editando la URL. El backend ya son dos endpoints con ventana independiente; falta el selector por corte, y que la leyenda «cada corte elige su propio período» deje de ser falsa. Es la deriva **D-2**. | `add_frontend_feature` | Developer | RF-05 |
| ✅ 10 | **Tests de permisos por comportamiento.** Hoy RF-08 y RF-29 están probados por construcción: no hay ni una request real como compras contra `/dashboard/sales` o `/sales` que espere 403, ni una como compras contra `/sales/review`. Sumar también que el job de ventas se dispara por su parámetro (RF-01) y que mover el período de un corte no mueve el del otro **desde la pantalla** (RF-05). | `add_tests` | Tester | RF-01, RF-05, RF-08, RF-29 |

### H2 — Las repetidas no se suman

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 11 | `code_key` **guardado** en `staging.sale_row` y en `core.sale`, con índice en las dos. No se deriva al leer: así el agrupamiento es una búsqueda por índice y significa siempre lo que significaba cuando la fila aterrizó. | `add_backend_feature` | Developer | RF-09, RF-10 |
| ✅ 12 | `_identical_among` sobre los cuatro campos de `COMPARED`: la repetida idéntica se guarda `DISCARDED` y se cuenta una sola vez, sin preguntarle a nadie. | `add_backend_feature` | Developer | RF-11 |
| ✅ 13 | Mismo código con algún dato distinto: **ninguna de las dos suma** hasta que alguien decida. Las hermanas ya contadas vuelven a `HELD`. | `add_backend_feature` | Developer | RF-13, RF-15 |
| ✅ 14 | `ReviewQueue.pending_groups` y su lugar en el tablero. | `add_backend_feature` | Developer | RF-14 |
| ✅ 15 | **RF-12: informar cuántas unificó solo.** El contador `merged` se calcula y **sólo se loguea**; ningún schema lo lleva, y `Indicator.excluded` mezcla lo que el sistema unificó con lo que una persona descartó. Exponerlo como campo propio, separado de lo descartado por decisión. Es la deriva **D-3**. | `add_backend_feature` | Developer | RF-12 |
| ✅ 16 | Tests de H2: `TestRepeatedSales` (6 casos) — idénticas contadas una vez, el código comparado sin su escritura, las que difieren apartadas, elegir una versión, declararlas distintas, y deshacer. | `add_tests` | Tester | RF-09, RF-10, RF-11, RF-13, RF-14, RF-15 |
| ✅ 17 | Test de RF-12: que el tablero informe cuántas repetidas idénticas unificó, y que ese número **no** incluya las descartadas por decisión de una persona. | `add_tests` | Tester | RF-12 |

### H3 — Las rotas tampoco

> **Es la historia con la decisión del 2026-08-31.** Las tareas 18 y 19 son esa decisión; sin ellas,
> doce de los 588 registros medidos quedan en `staging` y no existen para nadie: no se ven, no se
> cuentan entre las excluidas y no se les puede corregir la fecha.

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 18 | **`normalize_sales` deja de filtrar.** Hoy `SalesNormalized` sólo lleva las filas `VALID` con código, fecha y total (`ingestion/service.py:743-750`). Que lleve también las `QUARANTINED`, **con el `reason` del parser**, que es lo que RF-23 muestra. `SaleRowsQuarantined` se sigue publicando y sigue sin oyente: **no le agregues un suscriptor en `triage`**, o la misma venta aparece en dos pantallas de dos dueños distintos. | `add_backend_feature` | Developer | RF-16, RF-17, RF-18, RF-19 |
| ✅ 19 | **`register_sales` las registra en `HELD`** con el motivo del parser, sin pasarlas por `_why_not_countable` —que contesta otra pregunta— y **sin agruparlas cuando no tienen código**, porque sin código no hay `code_key` con qué agrupar. `core.sale.sold_on` y `.total` ya son nulables: el modelo no se toca. Con esto quedan verdaderos además RF-23, RF-25, RF-28 y RF-38 a RF-40 para estos registros. | `add_backend_feature` | Developer | RF-16, RF-17, RF-18, RF-19, RF-23, RF-28 |
| ✅ 20 | `_why_not_countable`: el producto que no existe, contra la **proyección** `core.sales_product` alimentada por `ProductsRegistered` (nunca importando `catalog`), y el monto que se aparta del promedio del producto. | `add_backend_feature` | Developer | RF-20, RF-21 |
| ✅ 21 | Parámetro `sales.outlier_threshold_pct` (inicial 300) y su proyección en `core.sales_setting`, alimentada por `BusinessParameterChanged` filtrado a esa única clave. | `add_backend_feature` | Developer | RF-21, RF-22 |
| ✅ 22 | `sale.reason` en la tabla de rotas de `/ventas/revision`, en las palabras que lee una persona. | `add_frontend_feature` | Developer | RF-23 |
| ✅ 23 | Tests de H3 existentes: `TestBrokenRecords` (3 casos) — producto inexistente, monto atípico, y que lo que informó el portal se conserva al corregir. | `add_tests` | Tester | RF-20, RF-21, RF-22, RF-23 |
| ✅ 24 | **El test punta a punta que hoy no existe.** Normalizar el fixture entero y verificar que las doce anomalías aparecen en `GET /sales/review` con su motivo y que `held_total` las cuenta. **Escribilo antes que las tareas 18 y 19**: hoy falla, y es lo único que demuestra que la deriva **D-1** se cerró de verdad. Los cinco tests de parser no lo reemplazan: miden `staging`, que es donde las ventas se quedan. Más el caso borde que la decisión abre: una fila **sin código** llega a `broken` y no rompe ningún grupo. | `add_tests` | Tester | RF-16, RF-17, RF-18, RF-19, RF-23, RF-28 |

### H4 — Cada número dice qué dejó afuera

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 25 | El tipo `Indicator`, con `value`, `sales`, `excluded` y `has_estimates` **juntos**. Es lo que hace que no se pueda devolver un número sin su exclusión: quien agregue un indicador tiene que llenar los cuatro campos. | `add_backend_feature` | Developer | RF-25, RF-27, RF-40 |
| ✅ 26 | `SalesDashboard.held_total`, sin ventana: es el estado de la cola entera, que es lo que RF-28 pide. | `add_backend_feature` | Developer | RF-28 |
| ✅ 27 | **RF-26: llegar, desde el indicador, a los registros que excluyó.** Hoy hay un enlace a `/ventas/revision` y sólo si `held_total > 0`; las `DISCARDED` **no están en esa cola**, así que la mitad de lo excluido no se puede ver desde ningún lado. Es la otra mitad de la deriva **D-3**. | `add_frontend_feature` | Developer | RF-26 |
| ✅ 28 | Tests de H4: `TestTheIndicators` (4 casos) — que cada indicador informe lo que dejó afuera, que lo diga también cuando no dejó ninguno, que la curva mensual sume sólo lo contado, y que una ventana cambie un número y no el otro. | `add_tests` | Tester | RF-03, RF-04, RF-05, RF-06, RF-07, RF-25, RF-27 |
| ✅ 29 | Test de RF-26: que desde el número excluido se llegue a la lista de esos registros, **incluidas las descartadas por unificación**. | `add_tests` | Tester | RF-26 |

### H5 — Decidir sobre las repetidas

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 30 | `review_queue`: los grupos con sus versiones enfrentadas y `differences` —los campos en que difieren—, más las rotas aparte. Es lo que convierte «estas dos no son iguales» en una decisión de un segundo. | `add_backend_feature` | Developer | RF-14, RF-30, RF-37 |
| ✅ 31 | `resolve_group` con `keep` y `distinct`: la elegida a `COUNTED`, las otras a `DISCARDED` y **nunca borradas**, con qué se decidió, quién y cuándo. Los indicadores se recalculan **por no hacer nada**: las agregaciones filtran por `COUNTED`. | `add_backend_feature` | Developer | RF-31, RF-32, RF-33, RF-34, RF-36 |
| ✅ 32 | `undo_resolution`: el grupo vuelve a `HELD` y los números vuelven solos. `409` cuando no hay decisión que deshacer — lo que el sistema unificó por ser idéntico no tiene resolución que revertir, y la firma lo dejó explícito. | `add_backend_feature` | Developer | RF-35, RF-37 |
| ✅ 33 | `correct_sale`: los cuatro campos, el valor estimado como acumulativo, y **`portal_values` escrito una vez y nunca tocado**, que es RF-41 y es la evidencia. | `add_backend_feature` | Developer | RF-38, RF-39, RF-41 |
| ✅ 34 | Rutas de decisión con `require_section(SALES, WRITE)` —`/sales/review`, las dos de `/sales/groups/{code_key}/resolution` y `PATCH /sales/{id}`— y la pantalla `(private)/ventas/revision` con `SalesReview.tsx`. | `add_backend_feature` | Developer | RF-29, RF-30, RF-31, RF-32, RF-34, RF-35 |
| ✅ 35 | **La pantalla de corrección, completa.** Hoy sólo ofrece corregir el **código de producto**, con un `window.prompt`, y manda `is_estimated: false` fijo. La fecha, el total y la cantidad no se pueden corregir desde ninguna pantalla aunque el endpoint las acepte, y **no hay forma de marcar un valor como estimado** — con lo que `has_estimates` nunca puede ser `true` y RF-40 está cumplido sobre algo que no puede ocurrir. Es la deriva **D-5**. | `add_frontend_feature` | Developer | RF-38, RF-39, RF-40 |
| ✅ 36 | **El motivo de una descartada por decisión humana dice otra cosa.** `resolve_group` deja `reason = "Repetida idéntica: se cuenta una sola vez"` en las versiones que una persona descartó, lo cual es falso: se descartaron porque alguien eligió otra. Lo decidido está bien guardado en `decision`; el texto que lee la persona miente. Es la deriva **D-7**. | `add_backend_feature` | Developer | RF-36 |
| ✅ 37 | Tests de H5: los cuatro casos de `TestRepeatedSales` que cubren elegir, declarar distintas y deshacer, más el de `TestBrokenRecords` que verifica que lo que informó el portal se conserva al corregir. | `add_tests` | Tester | RF-30, RF-31, RF-32, RF-33, RF-34, RF-35, RF-36, RF-37, RF-41 |
| ✅ 38 | Tests de RF-38 a RF-40 desde la pantalla: corregir una fecha y que la venta entre a los indicadores; cargar un total **estimado** y que el mes que la incluye avise que uno de sus valores lo es. Hoy el segundo no puede pasar de rojo a verde sin la tarea 35. | `add_tests` | Tester | RF-38, RF-39, RF-40 |

### H6 — Cómo se movieron los precios, el stock y las altas

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 39 | `core.stock_point` —una foto por producto y por día, con `UNIQUE (product_id, observed_on)` que hace idempotente reprocesar la lista— y su escritura al aplicar la lista de precios. Es de `catalog` y existe por esta feature. | `add_database_migration` | Developer | RF-43, RF-44 |
| ✅ 40 | Las tres consultas del catálogo: `price_curve` sobre los puntos del historial, `stock_at` con la foto **más cercana** al borde de la ventana, y `products_first_seen_between`. Un producto sin foto en algún extremo **queda excluido, no en cero**. | `add_backend_feature` | Developer | RF-42, RF-43, RF-44, RF-45 |
| ✅ 41 | `GET /dashboard/catalog` con su propia ventana, y los tres cortes en la pantalla del tablero. Que sean dos endpoints y no uno es lo que hace posible RF-05. | `add_backend_feature` | Developer | RF-42, RF-43, RF-44, RF-45, RF-46 |
| ✅ 42 | **RF-46 completo.** El corte de **altas** no informa cuántos registros excluyó —no existe `new_products_excluded` ni en el schema ni en la pantalla— y `price_curve_excluded` está **fijo en `0`**, no calculado: dice «cero excluidos» sin haber contado. Es la deriva **D-6**. | `add_backend_feature` | Developer | RF-46 |
| ✅ 43 | **Tests de H6 — hoy no hay ninguno.** Ni uno solo toca `price_curve`, `stock_at`, `products_first_seen_between` ni `GET /dashboard/catalog`. Lo que hay que fijar: que el stock compare la foto de apertura con la de cierre; que un producto sin foto en un extremo quede **excluido y no en cero**; que los que terminaron en cero salgan señalados; y el caso que sorprende — **sin `since` no hay apertura y el corte sale vacío con todos excluidos**. | `add_tests` | Tester | RF-42, RF-43, RF-44, RF-45, RF-46 |

## Cobertura de requisitos

| Requisito | Tareas | Test |
|-----------|--------|------|
| RF-01 | 1, 2, 5 | **10** |
| RF-02 | 3, 4, 5, 6 | 4 |
| RF-03 | 6, 7, 8 | 28 |
| RF-04 | 6, 7 | 28 |
| RF-05 | 7, **9** | 28, **10** |
| RF-06 | 6, 7, 8 | 28 |
| RF-07 | 7, 8 | 28 |
| RF-08 | 7 | **10** |
| RF-09 | 3, 11, 12 | 16 |
| RF-10 | 4, 11 | 4, 16 |
| RF-11 | 12 | 16 |
| RF-12 | **15** | **17** |
| RF-13 | 13 | 16 |
| RF-14 | 14, 30 | 16 |
| RF-15 | 6, 13 | 16 |
| RF-16 | 4, **18**, **19** | 4, **24** |
| RF-17 | 4, **18**, **19** | 4, **24** |
| RF-18 | 4, **18**, **19** | 4, **24** |
| RF-19 | 4, **18**, **19** | 4, **24** |
| RF-20 | 6, 20 | 23 |
| RF-21 | 20, 21 | 23 |
| RF-22 | 21 | 23 |
| RF-23 | **19**, 22 | 23, **24** |
| RF-24 | 4 | 4 |
| RF-25 | 25 | 28 |
| RF-26 | **27** | **29** |
| RF-27 | 25 | 28 |
| RF-28 | **19**, 26 | 28, **24** |
| RF-29 | 34 | **10** |
| RF-30 | 30, 34 | 37 |
| RF-31 | 31, 34 | 37 |
| RF-32 | 31, 34 | 37 |
| RF-33 | 6, 31 | 37 |
| RF-34 | 31, 34 | 37 |
| RF-35 | 32, 34 | 37 |
| RF-36 | 31, **36** | 37 |
| RF-37 | 30, 32 | 37 |
| RF-38 | 33, **35** | **38** |
| RF-39 | 33, **35** | **38** |
| RF-40 | 25, **35** | **38** |
| RF-41 | 33 | 37 |
| RF-42 | 40, 41 | **43** |
| RF-43 | 39, 40, 41 | **43** |
| RF-44 | 40, 41 | **43** |
| RF-45 | 40, 41 | **43** |
| RF-46 | **42** | **43** |

En negrita, lo pendiente. **Los 46 requisitos tienen tarea y tienen test**, pero conviene leer la
tabla por dónde está la negrita:

- **Cuatro requisitos no tienen hoy ni una línea construida**: RF-12, RF-26, RF-46 y el tramo
  RF-16 a RF-19 en su mitad de producto. Los cierran las tareas 15, 27, 42, 18 y 19.
- **Cinco requisitos están hoy probados por construcción y no por comportamiento**: RF-01, RF-05,
  RF-08 y RF-29 —la tarea 10— y RF-22, que sólo se verifica por el panel de parámetros y no por su
  efecto sobre qué venta se aparta.
- **La H6 entera no tiene un solo test.** Cinco requisitos construidos y verdes por lectura.
- **RF-40 está cumplido sobre algo que no puede ocurrir.** `has_estimates` funciona; nada puede
  ponerlo en `true` mientras la tarea 35 no exista.

## Notas para `/converge`

**La lista completa de deriva vive en `plan.md` → *Deriva contra la spec firmada*, y son siete
puntos.** Acá van las cuatro cosas que se ven desde este documento y conviene que el converge
encuentre ya escritas:

- **D-1 tiene tarea desde el 2026-08-31 y antes no podía tenerla.** Había dos salidas incompatibles
  —traer las filas a `core.sale`, o abrirles un caso en `triage`— y elegir entre ellas es del humano,
  no de un agente. Eligió la primera. Si el converge encuentra un suscriptor de `SaleRowsQuarantined`
  en `triage`, alguien hizo las dos.
- **D-4 no tiene tarea, y es a propósito.** Corregir una venta no pasa por el mecanismo común de
  correcciones manuales de la 003: no publica `ManualChangeRecorded`, no aparece en `/historial` y no
  se puede dejar sin efecto. **La propia `spec.md` firmada lo declara** en «Para confirmar al firmar»
  y dice que no lo cierra. Qué se corrige —el sistema o el acuerdo— es del humano; darle una tarea
  sería decidirlo por él.
- **El fixture de `/ventas` es derivado, no capturado.** Las 588 filas y sus anomalías son las que la
  spec enumera, pero **las columnas son una deducción**: el relevamiento midió esa pantalla y no
  guardó el DOM. Un test verde contra ese fixture no dice nada sobre el portal real. `TEST-03` se
  cumple en la forma —nunca se prueba contra el portal en vivo— y no en la evidencia.
- **Cinco cosas están fuera de alcance y un converge que las busque está leyendo el pedido original y
  no la spec firmada**: el precio de venta de la empresa y su comparación con el del proveedor, el
  detalle de movimientos de stock, el gasto por rubro, la deuda con proveedores, y avisar por fuera
  del sistema cuando aparecen ventas apartadas nuevas — eso último es P8 y P12, y prometerlo acá sería
  comprometer dos veces lo mismo.
