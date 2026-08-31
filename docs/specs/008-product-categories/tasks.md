# Rubros unificados — Tareas

<!--
  ARTEFACTO INTERNO. Cada tarea mapea a una skill de agents/skills/ y es lo bastante
  chica como para terminarse de una sentada. Si una tarea no tiene skill, o no
  corresponde al proyecto, o falta la skill: preguntá antes de inventarla.
-->

**Feature:** 008-product-categories · **Plan:** `plan.md` · **Tareas:** 31

## Estado

**Este documento se escribió después de la implementación**, el 2026-08-30. La 008 se construyó en
el commit `b759a37`, junto con las otras cinco specs pendientes, sin que existiera un `tasks.md`
que la desglosara. El desglose de abajo es el que `plan.md` implica; las marcas dicen qué encontré
en el árbol de trabajo al recorrer archivo por archivo.

- ✅ **27 de 31** — las tres pantallas, las ocho rutas, la migración con su siembra y los dos
  handlers nuevos.
- ⏸ **4 en espera**: los tres huecos de H4 y H5, más el test que ninguno de ellos tiene. Están
  abajo en **Los tres huecos**, con el requisito que cada una deja sin cubrir.

> **No corrí la suite.** Las marcas ✅ son de inspección: el archivo existe, la función existe, la
> ruta declara su autorización, el test tiene su caso. Que pase es del `Tester`, y falta.

> **La cadena tampoco corrió.** No hay `/analyze`, no hay `/converge` y no hay `/review-feature`
> sobre esta feature. Los tres huecos de abajo son exactamente la clase de cosa que `/converge`
> busca, y aparecieron sin él.

> **Decisión del humano (2026-08-30): los rubros pasan a compras.** El tercer hueco no era un
> defecto de implementación sino un desacuerdo sobre de quién es el trabajo, y se resolvió a favor
> de compras: el rubro es la categoría de lo que se compra para revender. Como la 008 está firmada
> y la 002 está archivada —y una spec archivada no se edita—, el cambio va en una spec nueva,
> **`010-category-ownership`, hoy en borrador y sin firmar**.
>
> Mientras esa firma no exista, **las tareas 21, 22, 24 y 30 quedan en espera**: su contenido
> depende de cuál de las dos specs gana, y planificarlas antes del gate sería resolver un alcance
> que nadie acordó (Artículo V). Las otras 27 no las toca: la 010 cambia **quién** mantiene los
> rubros, no **qué** hacen.

## Orden

Agrupadas por historia, en el orden de prioridad de la spec. Dentro de cada una:
migración → backend → frontend → tests.

> **Al terminar H1 hay algo entregable de verdad**: Julián abre `/rubros`, ve siete rubros y no
> dieciocho, cada uno con cuántos productos tiene y con todas las formas en que llega escrito, y
> puede agregar uno, renombrarlo o intentar borrarlo. Las cuatro historias siguientes agregan
> encima; ninguna es requisito para que la primera funcione.

> **Tres tareas de H1 son cimiento y no se ven en pantalla** —el evento, la normalización y la
> migración con su siembra—. Sin la siembra, la primera corrida manda los cien productos a
> revisión, que es lo contrario de lo que H1 promete.

### H1 — Un rubro por rubro

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 1 | `app/shared/events/catalog.py`: `category_raw` y `subcategory_raw` en `NormalizedPriceRow` **con default**, para no romper a quien ya construye el evento en `001`; más `UnknownCategoryObserved` y `QuarantineRuleRedecided`. Todo lo demás cuelga de acá. | `add_backend_feature` | Developer | RF-02, RF-21, RF-28 |
| ✅ 2 | `app/shared/text.py`: `collapse_written_form` —recortar, colapsar espacios internos, `casefold`, y nada más—, con su test unitario en `tests/unit/shared/test_text.py`. **No quita acentos, no expande `/`, no corta abreviaturas**: un normalizador que adivine es lo que esta feature no hace. | `add_backend_feature` | Developer | RF-02 |
| ✅ 3 | Migración `0010_product_categories`: `core.category`, `core.category_alias`, las seis columnas de `core.product`, y `created_by_user_id` nulo más `updated_by_user_id` / `updated_at` en `operations.resolution_rule`. **Siembra los 7 rubros y las 11 equivalencias dos veces** —como regla en `operations.resolution_rule` y como fila que la proyecta—, para que no existan dos clases de equivalencia. Los modelos entran a `app/models.py` en el mismo commit. | `add_database_migration` | Developer | RF-01, RF-02, RF-18, RF-23, RF-27 |
| ✅ 4 | `ingestion`: `category_raw` y `subcategory_raw` se guardan en `staging.price_row` y viajan en cada `NormalizedPriceRow`. Es el único cambio en el módulo, y es el que hace que el dato que `001` ya extraía llegue hasta `catalog`. | `add_backend_feature` | Developer | RF-02, RF-08 |
| ✅ 5 | `catalog._classify`: al aplicar un lote, buscar la forma escrita normalizada en `category_alias`. Hay equivalencia → `category_id` y `classified_by_rule_id`. No hay → el producto queda sin rubro y la forma escrita se acumula para publicar `UnknownCategoryObserved`. | `add_backend_feature` | Developer | RF-02, RF-21, RF-22, RF-25 |
| ✅ 6 | `catalog.list_categories()`: cada rubro con su conteo y con todas sus formas escritas, en una sola consulta. | `add_backend_feature` | Developer | RF-01, RF-03, RF-04 |
| ✅ 7 | `catalog`: agregar, renombrar y borrar un rubro. RF-07 **se verifica en el servicio y no con un `ON DELETE`**: el sistema tiene que poder decir por qué no se puede, y un error de integridad de Postgres no es un mensaje para una persona. | `add_backend_feature` | Developer | RF-05, RF-06, RF-07 |
| ✅ 8 | Rutas `GET`, `POST`, `PATCH` y `DELETE /categories`, y la sección `PRODUCT_CATEGORIES` en la matriz de `identity/permissions.py` —dueño y ventas escriben, compras no—. La autorización quedó en la matriz y no en una función por rol; `plan.md` lo documenta así en *Contratos*: ver *Desvíos* 1. | `add_backend_feature` | Developer | RF-01, RF-03, RF-04, RF-05, RF-06, RF-07 |
| ✅ 9 | Pantalla `(private)/rubros` con `components/categories/CategoryList.tsx` y `app/actions/categories.ts`: los siete rubros con su conteo y sus formas escritas, y las tres acciones de mantenimiento sólo si la sesión las tiene. | `add_frontend_feature` | Developer | RF-01, RF-03, RF-04, RF-05, RF-06, RF-07, RF-08 |
| ✅ 10 | Tests de H1: que las 18 grafías firmadas resuelvan al rubro que les toca; que **cada equivalencia tenga su regla vigente detrás** —el hueco que se coló en el plan y dejaría a las sembradas sin poder corregirse—; que una sembrada no diga que la decidió nadie; y que borrar un rubro con productos se rechace con su motivo. | `add_tests` | Tester | RF-01 … RF-08 |

### H2 — Los que no tienen rubro, a la vista

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 11 | `catalog`: «sin rubro» como grupo más en `CategoryList` —`unclassified_count` y `total_products` al lado de los rubros—, **sin fila centinela**: un rubro llamado «Sin rubro» sería borrable, renombrable y contable como los demás, y RF-07 no tendría sentido sobre él. | `add_backend_feature` | Developer | RF-09, RF-10, RF-11 |
| ✅ 12 | `catalog.unclassified()` paginado y su ruta `GET /categories/unclassified`, autenticada: los tres roles la leen. | `add_backend_feature` | Developer | RF-11, RF-12 |
| ✅ 13 | Frontend: «sin rubro» con su conteo en `/rubros`, enlazado a la cola. | `add_frontend_feature` | Developer | RF-09, RF-11, RF-12 |
| ✅ 14 | Tests de H2: que la suma de todos los rubros **más** «sin rubro» dé el total general, y que siga dándolo después de revocar una equivalencia —el momento en que más fácil se pierde un producto—. | `add_tests` | Tester | RF-09, RF-10, RF-11, RF-12 |

### H3 — Clasificar los que quedaron sueltos

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 15 | `catalog`: la propuesta por subcategoría, derivada de los productos ya clasificados y **sin tabla**. Exactamente un rubro → esa es la propuesta; cero o más de uno → sin propuesta. Desempatar sería el sistema decidiendo. | `add_backend_feature` | Developer | RF-14, RF-16, RF-17 |
| ✅ 16 | `catalog.set_product_category()` y su ruta `PUT /products/{product_id}/category`: confirmar la propuesta y corregirla son **la misma escritura**, y la única diferencia es qué rubro viaja. Quién decidió sale del token, nunca del cuerpo. | `add_backend_feature` | Developer | RF-13, RF-15, RF-18, RF-19, RF-20 |
| ✅ 17 | Pantalla `(private)/rubros/sin-clasificar` con `components/categories/UnclassifiedQueue.tsx`: cada producto con su subcategoría, su propuesta si la tiene, y el selector para confirmar o corregir. | `add_frontend_feature` | Developer | RF-12, RF-13, RF-14, RF-15, RF-17, RF-19, RF-20 |
| ✅ 18 | Tests de H3: la propuesta que sale de lo ya clasificado; una subcategoría que apunta a dos rubros cayendo en RF-17 **sin desempatar**; que un producto con propuesta sin confirmar siga contando como «sin rubro»; y que la asignación quede con nombre y fecha. | `add_tests` | Tester | RF-13 … RF-20 |

### H4 — Una forma escrita nueva se pregunta, no se adivina

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 19 | `triage`: el kind `unknown_category`, `_matcher_of` armando el matcher **por `category_text` y no por `product_code`**, y el handler de `UnknownCategoryObserved` que abre **un** caso por forma escrita —cien productos del mismo lote preguntan una vez, por el `fingerprint`—. | `add_backend_feature` | Developer | RF-21, RF-22, RF-23, RF-26 |
| ✅ 20 | `catalog.learn_category_alias()` sobre `QuarantineCaseResolved` con `kind="unknown_category"`: la decisión se proyecta como equivalencia y desde ahí se aplica sola. `catalog` **no lee la tabla de `triage`**, escucha su hecho. | `add_backend_feature` | Developer | RF-24, RF-25 |
| ⏸ 21 | `catalog`: exponer **cuántos productos están pendientes de revisión por su categoría**, al lado de `unclassified_count` y con la misma lógica de conteo. Hoy no existe: `CategoryList` lleva los sin rubro y el total, y nada cuenta los apartados. | `add_backend_feature` | Developer | RF-26 |
| ⏸ 22 | Frontend: la rama `unknown_category` en `components/triage/CaseCard.tsx` —su etiqueta en español, la forma escrita con la que llegó a la vista, y el selector de rubro que resuelve el caso—, sobre una pantalla que **ventas pueda abrir**. Hoy el caso se lista con su `kind` crudo en inglés, sin `category_text` y sin ningún botón. | `add_frontend_feature` | Developer | RF-23, RF-24, RF-26 |
| ✅ 23 | Tests de H4: que el matcher salga por `category_text` —**el primer test**, porque si sale por producto la equivalencia se aplica a uno solo y RF-25 falla en silencio—; un caso por forma escrita y no cien; y que la decisión sea retroactiva y se aplique sola después. | `add_tests` | Tester | RF-21 … RF-25 |
| ⏸ 24 | Tests de lo que falta: que el conteo de pendientes por categoría sea el que la cola tiene abierto —**RF-26 es el único de los 31 sin ningún test**—, que un caso `unknown_category` se resuelva desde la pantalla y no sólo desde el servicio, y que **ventas** pueda corregir y dejar sin efecto una equivalencia. Va después de las tareas 21, 22 y 30. | `add_tests` | Tester | RF-23, RF-24, RF-26, RF-28, RF-30 |

### H5 — Corregir una equivalencia mal puesta

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 25 | `triage.redecide_rule()` y su ruta `PATCH /triage/rules/{rule_id}`: reapunta la `decision` de una regla vigente, escribe `updated_by_user_id` y `updated_at` **sin perder quién la creó**, rechaza con conflicto si ya está revocada, y publica `QuarantineRuleRedecided`. | `add_backend_feature` | Developer | RF-28 |
| ✅ 26 | `catalog.repoint_category_alias()` sobre ese evento: reapunta el alias y mueve los productos con `WHERE classified_by_rule_id = :rule_id`. **Nadie vuelve a la cola** — si aparecen en revisión, se implementó RF-31 donde iba RF-29. | `add_backend_feature` | Developer | RF-29 |
| ✅ 27 | `catalog.forget_category_alias()` sobre `QuarantineRuleRevoked`: desasigna esos mismos productos y los vuelve a pasar por **el mismo paso de clasificación de cada lote**, que publica `UnknownCategoryObserved`. No es una rama de revocación: es el flujo normal. | `add_backend_feature` | Developer | RF-30, RF-31 |
| ✅ 28 | `catalog.list_aliases()` y su ruta `GET /categories/aliases`: cada equivalencia con quién la decidió y cuándo, y las sembradas diciendo que no las decidió nadie. | `add_backend_feature` | Developer | RF-27 |
| ✅ 29 | Pantalla `(private)/rubros/equivalencias` con `components/categories/AliasList.tsx`: las dos acciones separadas y explicadas, porque son toda la H5 —corregir reasigna, dejar sin efecto manda a revisión—. | `add_frontend_feature` | Developer | RF-27, RF-28, RF-30 |
| ⏸ 30 | **En espera de la firma de la 010.** El trabajo de los rubros no lo puede hacer entero ninguna de las dos personas: las cinco rutas de `triage` exigen `Section.PRICES` —dueño y compras— y las cuatro escrituras de `/categories` exigen `PRODUCT_CATEGORIES` —dueño y ventas—. Con la 010 firmada, lo que se mueve son las segundas y `triage` se queda como está; con la 008 sola, era al revés: un mapa kind → sección en `triage`. | `add_backend_feature` | Developer | RF-23, RF-24, RF-26, RF-28, RF-30 |
| ✅ 31 | Tests de H5: que el `PATCH` **reasigne sin pasar por revisión**; que alcance igual a una sembrada que a una aprendida; que **no** toque lo que alguien clasificó a mano —`classified_by_rule_id` nulo—; y que revocar sí los mande a la cola con los totales todavía cerrando. | `add_tests` | Tester | RF-27 … RF-31 |

## Los tres huecos

Los tres salieron de recorrer el código contra los 31 requisitos, no de un test que falle. Ninguno
rompe nada: por eso estaban.

### 1. RF-26 no tiene sobre qué pararse — tareas 21 y 24

*"El sistema debe mostrar cuántos productos están pendientes de revisión por su categoría."*

`CategoryList` lleva `unclassified_count` y `total_products`, y nada más. `triage` sabe contar sus
casos pendientes (`count_pending`), pero nadie le pregunta por `unknown_category`, y ninguna
pantalla lo muestra. **No hay implementación y no hay test**: es el único RF de los 31 sin ninguna
de las dos cosas.

### 2. Un caso de rubro llega a una pantalla que no sabe mostrarlo — tareas 22 y 24

El backend abre el caso bien: un caso por forma escrita, con `category_text` en el payload, y
resolverlo aprende la equivalencia. Pero `CaseCard.tsx` tiene rama para `unknown_product`,
`missing_product`, `unreadable_row` y `unreadable_history`, **y ninguna para `unknown_category`**.
El caso se dibuja con su `kind` crudo —`unknown_category`, en inglés, en una pantalla que lee el
cliente—, sin mostrar con qué categoría llegó escrito (RF-23) y sin ninguna forma de asignarla a un
rubro (RF-24).

Que RF-24 y RF-25 estén verdes en los tests no lo contradice: los tests resuelven el caso llamando
al servicio, que es la mitad que sí está construida.

### 3. La cola de revisión pasó a tener dos dueños, y la autorización sigue teniendo uno — tareas 30 y 24

Las cinco rutas de `triage` —`list_cases`, `resolve_case`, `list_rules`, `DELETE` y el `PATCH`
nuevo— exigen `Section.PRICES` en escritura, que es **dueño y compras**. Era correcto mientras la
cola tuvo un solo tipo de trabajo: los cuatro kinds que abrió la `001` salen de la lista de precios
y son de Marcela.

La 008 le agregó un quinto kind que **no es de ella**. Un rubro es la categoría del catálogo —lo
que el dueño compra para revender: una pinza es Herramientas—, y el catálogo lo mantiene ventas,
firmado en la `002` y repetido en las reglas de negocio de esta spec. En la matriz esto ya está
dicho con todas las letras: `PRICES` le da a ventas sólo lectura, y `PRODUCT_CATEGORIES` le da
escritura y a compras **nada**. Las dos secciones son casi disjuntas.

El resultado es que ventas no puede hacer **nada** de lo que H4 y H5 le piden:

- No puede ver un caso de rubro apartado ni con qué categoría llegó escrito (RF-23).
- No puede asignar esa forma escrita a un rubro (RF-24), que es la decisión entera de H4.
- No puede contar los pendientes por categoría (RF-26).
- No puede corregir ni dejar sin efecto una equivalencia (RF-28, RF-30).

Y en `/rubros/equivalencias` se ve entero: la pantalla muestra los botones con
`canEdit(..., 'PRODUCT_CATEGORIES')`, donde ventas **sí** escribe, y las acciones pegan contra
`triage`, donde **no**. Julián ve los botones y recibe 403. La misma página pide
`/triage/rules?kind=unknown_category` para saber de qué regla viene cada alias: para ventas
responde nulo y la lista cae a `rules ?? []`.

**Por eso el arreglo no es abrirle `triage` a ventas**, que la dejaría resolver también los casos de
precios que son de compras. La autorización tiene que depender del **kind del caso**, que es lo que
dice de quién es ese trabajo. Es lo que pide la tarea 30, y es una decisión de arquitectura que la
008 destapó: `triage` dejó de ser la cola de la lista de precios y pasó a ser la cola del sistema.

> **Lo único que sigue siendo del humano** es si esa lectura es la correcta: toda la evidencia
> firmada dice que los rubros los mantiene ventas —la `002`, las reglas de negocio de esta spec, la
> tabla de actores donde Marcela sólo consulta—. Si el negocio quiere que los mantenga compras,
> entonces el código está bien y lo que hay que enmendar es la spec, que es un documento firmado.

> **Cerrado el 2026-08-30 por decisión del humano:** los rubros pasan a **compras**, y por lo tanto
> `triage` se queda como está y lo que se mueve son las cuatro escrituras de `/categories` y su fila
> de permisos. Como la 008 está firmada y la 002 archivada, el cambio no se parcha acá: vive en
> `docs/specs/010-category-ownership/spec.md`, en borrador, a la espera de firma.

## Desvíos de la implementación

Cuatro, ninguno de alcance.

### 1. La autorización no es `require_sales()`, es una sección de la matriz

Se consideró un `require_sales()` en `identity/dependencies.py` y se descartó: la implementación
agregó `PRODUCT_CATEGORIES` a `identity/permissions.py` con su fila en la matriz —dueño `WRITE`,
compras `NONE`, ventas `WRITE`— y usa el `require_section()` genérico que la 003 ya había dejado. La
autorización queda en la matriz, que un test recorre entera
(`tests/unit/identity/test_permissions.py:34`), en vez de en una función por rol.

**Corregido en `plan.md` el 2026-08-31:** el plan ya no pide un `require_sales()` — lo documenta como
alternativa descartada y describe la matriz, que es lo que hay. Y la versión anterior de este párrafo
decía que había un `require_purchasing()` «que ya existía»: **nunca existió**.
`identity/dependencies.py` sólo define `get_current_user` (`:77`) y `require_section` (`:95`). Esto
deja de ser un desvío del plan y queda como la decisión de diseño que fue.

### 2. La migración es la `0010`, no la `0003`

La versión anterior de `plan.md` y de `data-model.md` la llamaba `0003_product_categories` sobre la
cabeza `0002`. Cuando la 008 se construyó, la cabeza era la `0009`. El nombre y el número cambiaron;
el contenido, no. **Corregido en los dos documentos el 2026-08-31**, verificado contra
`backend/alembic/versions/0010_product_categories.py:41-42`.

### 3. La `0010` trae también `core.stock_point`

No es de esta feature: es de la **009**, y entró en la misma migración porque las seis specs se
construyeron juntas. Funciona, pero una migración que hace dos cosas se lee peor que dos que hacen
una, y `data-model.md` de la 008 no la menciona.

### 4. Once equivalencias, no dieciocho

Está anotado en `plan.md` → *Datos* y *Deriva contra la spec firmada*, y la migración lo explica en
su docstring. Las 18 grafías firmadas **se resuelven** igual; lo que cambia es cuántas filas hacen
falta, porque la clave de matcheo colapsa los pares que sólo difieren en mayúsculas
(`backend/alembic/versions/0010_product_categories.py:198-206`).

**Corregido en `plan.md` y en `data-model.md` el 2026-08-31**, que decían 18. Los dos son artefactos
técnicos internos, no la spec firmada, así que se corrigen sin pedirle permiso a nadie; **la
`spec.md` no se tocó**, y sigue hablando de 18 grafías, que es correcto: son 18 formas escritas.

Lo que la corrección destapó y **sí es del humano**: se resuelven 18 pero se **muestran** 11, y el
criterio de aceptación firmado de RF-03 pide tres formas para Pinturas y Adhesivos donde se ven dos.
Es el punto 13 de *Deriva* en `plan.md`, y no tiene tarea.

## Cobertura de requisitos

| Requisito | Tareas | Test |
|-----------|--------|------|
| RF-01 | 3, 6, 8, 9 | 10 |
| RF-02 | 1, 2, 4, 5 | 10 |
| RF-03 | 6, 8, 9 | **ninguno** |
| RF-04 | 6, 8, 9 | 10 |
| RF-05 | 7, 8, 9 | 10 |
| RF-06 | 7, 8, 9 | 10 |
| RF-07 | 7, 8, 9 | 10 |
| RF-08 | 3, 4, 9 | 10 |
| RF-09 | 11, 13 | 14 |
| RF-10 | 11 | 14 |
| RF-11 | 11, 12, 13 | 14 |
| RF-12 | 12, 13, 17 | 14 |
| RF-13 | 16, 17 | 18 |
| RF-14 | 15, 17 | 18 |
| RF-15 | 16, 17 | 18 |
| RF-16 | 15 | 18 |
| RF-17 | 15, 17 | 18 |
| RF-18 | 3, 16 | 18 |
| RF-19 | 16, 17 | 18 |
| RF-20 | 16, 17 | 18 |
| RF-21 | 1, 5, 19 | 23 |
| RF-22 | 5, 19 | 23 |
| RF-23 | 3, 19, **22**, **30** | 23, **24** |
| RF-24 | 20, **22**, **30** | 23, **24** |
| RF-25 | 5, 20 | 23 |
| RF-26 | **21**, **22**, **30** | **24** |
| RF-27 | 3, 28, 29 | 31 |
| RF-28 | 1, 25, 29, **30** | 31, **24** |
| RF-29 | 26 | 31 |
| RF-30 | 27, 29, **30** | 31, **24** |
| RF-31 | 27 | 31 |

En negrita, lo pendiente. **Todo RF tiene al menos una tarea**, pero RF-23, RF-24 y RF-26 sólo los
cierran tareas que todavía no se hicieron, y **RF-26 no tiene hoy ni una línea construida ni un test
que lo mire**.

**Dos RF no tienen test**, y esta tabla lo decía al revés hasta el 2026-08-31: RF-26, y **RF-03**. La
tarea 10 le estaba atribuida y no lo prueba — sus tres tests verifican que todo alias tenga su regla,
que las sembradas no se atribuyan a nadie y que dos grafías que sólo difieren en mayúsculas resuelvan
al mismo rubro (`tests/integration/features/test_product_categories.py:87,102,114`); ninguno abre un
rubro y cuenta sus formas escritas. Escribir ese test es lo que destapa el punto 13 de *Deriva* en
`plan.md`, así que la tarea que lo cubra tiene que decidirse después de que el humano resuelva RF-03.

## Notas para `/converge`

**La lista completa de deriva vive en `plan.md` → *Deriva contra la spec firmada*, y son trece
puntos.** Acá van sólo las cinco cosas que se ven desde este documento y conviene que el converge
encuentre ya escritas:

- **Los tres huecos de arriba** son los tres que separan el código de lo firmado. Ninguno es
  interpretación: RF-26 no existe, RF-23 y RF-24 no tienen pantalla, y cinco requisitos no alcanzan
  al rol que la spec nombra porque `triage` autoriza por router y no por kind de caso.
- **La spec habla de 18 equivalencias y hay 11.** Las 18 grafías se **resuelven** igual: ahí el
  número cambió y el comportamiento no. Pero se **muestran** 11, y el criterio de aceptación de RF-03
  pide tres formas escritas para Pinturas y Adhesivos donde la pantalla enseña dos. Eso sí es deriva,
  es el punto 13 de *Deriva* en `plan.md`, y **no tiene tarea**.
- **Resolver un caso de rubro tiene cuatro salidas mudas.** Una decisión que nombra un rubro
  inexistente resuelve el caso y no hace nada: sin equivalencia, sin producto clasificado y sin fila
  en `operations.exception`. Punto 12 de *Deriva* en `plan.md`; tampoco tiene tarea.
- **Los criterios de aceptación se verifican contra el fixture fijado**, `price-list-2026-08-28.xlsx`,
  que tiene los números de la spec: 18 formas, 7 rubros, 8 sin categoría, 100 productos. Nunca
  contra el portal en vivo (`TEST-03`, Blocker).
- **El gasto por rubro no está y no tiene que estar**: la spec lo saca de alcance en su primer
  párrafo, porque no hay fuente que ligue lo gastado con el producto. Un converge que lo busque
  está leyendo el pedido original, no la spec firmada.
