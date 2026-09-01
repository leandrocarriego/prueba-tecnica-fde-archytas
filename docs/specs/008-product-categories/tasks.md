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

- ✅ **31 de 31**, al 2026-09-01. Las 27 de la construcción original, más las cuatro que estaban
  en espera: **22 y 30 las cerró la 010** —firmada el 2026-08-31 y ya en `main`—, y **21 y 24 se
  cerraron en esta pasada**, en la rama `fix/008-close-converge-and-review`.

> **Ahora sí corrió la suite**, sobre `main` con estos cambios encima: 1659 pasan, 9 skipped,
> cobertura 93,11 % (`make test`). Las marcas ✅ de las 27 originales eran de inspección y no lo
> son más: los 29 tests de `test_product_categories.py` pasan, y a los 20 que había se les sumaron
> los de RF-26, RF-03, el circuito por HTTP y las decisiones que no se pueden aplicar.

> **De la cadena falta lo que sigue.** No hay `/analyze` —la feature se construyó sin `tasks.md`,
> así que no había qué analizar— y **`/converge` y `/review-feature` son el próximo paso**: esta
> pasada existe para que tengan algo coherente que mirar. Lo que le queda a `/converge` está en
> `plan.md` → *Deriva*, y son los puntos 6 a 11 y 13.

> **Decisión del humano (2026-08-30), y cómo terminó: los rubros pasan a compras.** El tercer
> hueco no era un defecto de implementación sino un desacuerdo sobre de quién es el trabajo, y se
> resolvió a favor de compras: el rubro es la categoría de lo que se compra para revender. Como la
> 008 está firmada y la 002 archivada —y una spec archivada no se edita—, el cambio fue a una spec
> nueva, **`010-category-ownership`, firmada el 2026-08-31 y construida entera** (12 de 12 tareas,
> `66913ff`). Las tareas 22 y 30 de acá son suyas y quedaron cerradas ahí; las otras 27 nunca las
> tocó, porque la 010 cambia **quién** mantiene los rubros, no **qué** hacen.

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
| ✅ 21 | `catalog`: `pending_review_count` en `CategoryList`, al lado de `unclassified_count`. No son el mismo número y por eso van los dos: se cuentan los productos sin rubro **cuya forma escrita todavía no tiene equivalencia** —los que la cola tiene preguntando—, y no los que llegaron sin ninguna categoría, que no esperan una decisión sino que se clasifican a mano. La normalización se aplica en el servicio con `collapse_written_form` y no en SQL: una segunda definición de «la misma forma escrita» es una que se desvía. `repository.unclassified_written_forms()`, `service.list_categories()`, y el número en `/rubros` con enlace a la cola. | `add_backend_feature` | Developer | RF-26 |
| ✅ 22 | **Cerrada por la 010** (su tarea 3 y su tarea 4, `66913ff`): `CaseCard.tsx` tiene la rama `unknown_category` con la forma escrita a la vista y el selector de rubro que resuelve el caso, y `CASE_KINDS` su etiqueta en español. La pantalla que la abre es la de **compras**, no la de ventas: eso es exactamente lo que la 010 dio vuelta. | `add_frontend_feature` | Developer | RF-23, RF-24, RF-26 |
| ✅ 23 | Tests de H4: que el matcher salga por `category_text` —**el primer test**, porque si sale por producto la equivalencia se aplica a uno solo y RF-25 falla en silencio—; un caso por forma escrita y no cien; y que la decisión sea retroactiva y se aplique sola después. | `add_tests` | Tester | RF-21 … RF-25 |
| ✅ 24 | Tests de lo que faltaba, los tres en `test_product_categories.py`: **el conteo de pendientes es el que la cola tiene abierto** (`TestHowManyAreWaitingOnAReview`, y el que llegó sin categoría no cuenta); **un caso se resuelve por HTTP y no sólo llamando al servicio** (`TestDecidingOneFromTheScreen`, el circuito entero: llega la forma escrita, aparece el caso con su `category_text`, compras nombra el rubro, los dos productos quedan clasificados y el conteo baja a cero); y **una decisión que no se puede aplicar no resuelve el caso** (`TestADecisionThatCannotBeApplied`). Quién puede hacerlo es **compras** y no ventas: lo fija `test_category_ownership.py` desde la 010. | `add_tests` | Tester | RF-23, RF-24, RF-26, RF-28, RF-30 |

### H5 — Corregir una equivalencia mal puesta

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 25 | `triage.redecide_rule()` y su ruta `PATCH /triage/rules/{rule_id}`: reapunta la `decision` de una regla vigente, escribe `updated_by_user_id` y `updated_at` **sin perder quién la creó**, rechaza con conflicto si ya está revocada, y publica `QuarantineRuleRedecided`. | `add_backend_feature` | Developer | RF-28 |
| ✅ 26 | `catalog.repoint_category_alias()` sobre ese evento: reapunta el alias y mueve los productos con `WHERE classified_by_rule_id = :rule_id`. **Nadie vuelve a la cola** — si aparecen en revisión, se implementó RF-31 donde iba RF-29. | `add_backend_feature` | Developer | RF-29 |
| ✅ 27 | `catalog.forget_category_alias()` sobre `QuarantineRuleRevoked`: desasigna esos mismos productos y los vuelve a pasar por **el mismo paso de clasificación de cada lote**, que publica `UnknownCategoryObserved`. No es una rama de revocación: es el flujo normal. | `add_backend_feature` | Developer | RF-30, RF-31 |
| ✅ 28 | `catalog.list_aliases()` y su ruta `GET /categories/aliases`: cada equivalencia con quién la decidió y cuándo, y las sembradas diciendo que no las decidió nadie. | `add_backend_feature` | Developer | RF-27 |
| ✅ 29 | Pantalla `(private)/rubros/equivalencias` con `components/categories/AliasList.tsx`: las dos acciones separadas y explicadas, porque son toda la H5 —corregir reasigna, dejar sin efecto manda a revisión—. | `add_frontend_feature` | Developer | RF-27, RF-28, RF-30 |
| ✅ 30 | **Cerrada por la 010**, que se firmó: la fila `PRODUCT_CATEGORIES` de la matriz pasó a `{dueño: WRITE, compras: WRITE, ventas: READ}` (`identity/permissions.py:99`) y `triage` se quedó como estaba, porque ahora las dos puntas piden lo mismo. Ya no hay una pantalla que ofrezca botones que el backend rechaza, y las lecturas de `/categories` declaran su sección en vez de permitir por omisión. | `add_backend_feature` | Developer | RF-23, RF-24, RF-26, RF-28, RF-30 |
| ✅ 31 | Tests de H5: que el `PATCH` **reasigne sin pasar por revisión**; que alcance igual a una sembrada que a una aprendida; que **no** toque lo que alguien clasificó a mano —`classified_by_rule_id` nulo—; y que revocar sí los mande a la cola con los totales todavía cerrando. | `add_tests` | Tester | RF-27 … RF-31 |

## Los tres huecos, y cómo se cerraron

Los tres salieron de recorrer el código contra los 31 requisitos, no de un test que falle. Ninguno
rompía nada: por eso estaban. **Los tres están cerrados** —el primero acá, el 2026-09-01; el segundo
y el tercero por la 010—, y el diagnóstico queda escrito porque es lo que explica cómo un requisito
puede estar verde en una tabla y no existir en el producto.

### 1. RF-26 no tenía sobre qué pararse — tareas 21 y 24 · **cerrado el 2026-09-01**

*"El sistema debe mostrar cuántos productos están pendientes de revisión por su categoría."*

`CategoryList` lleva `unclassified_count` y `total_products`, y nada más. `triage` sabe contar sus
casos pendientes (`count_pending`), pero nadie le pregunta por `unknown_category`, y ninguna
pantalla lo muestra. **No había implementación y no había test**: era el único RF de los 31 sin
ninguna de las dos cosas.

**Cómo se cerró.** `CategoryList` lleva ahora `pending_review_count`, y `/rubros` lo muestra en dos
lugares: en la fila «Sin rubro», que es donde se ve que los dos números no son el mismo, y como
enlace a la cola de revisión, que es donde se resuelve. El conteo sale de `catalog` y de nadie más:
son los productos sin rubro cuya forma escrita todavía no tiene equivalencia. Preguntárselo a
`triage` habría sido un import cruzado (Artículo IV) y además la respuesta equivocada — la cola
cuenta **casos**, uno por forma escrita, y RF-26 pide **productos**.

### 2. Un caso de rubro llegaba a una pantalla que no sabía mostrarlo — tareas 22 y 24 · **cerrado por la 010**

El backend abre el caso bien: un caso por forma escrita, con `category_text` en el payload, y
resolverlo aprende la equivalencia. Pero `CaseCard.tsx` tiene rama para `unknown_product`,
`missing_product`, `unreadable_row` y `unreadable_history`, **y ninguna para `unknown_category`**.
El caso se dibuja con su `kind` crudo —`unknown_category`, en inglés, en una pantalla que lee el
cliente—, sin mostrar con qué categoría llegó escrito (RF-23) y sin ninguna forma de asignarla a un
rubro (RF-24).

Que RF-24 y RF-25 estén verdes en los tests no lo contradice: los tests resuelven el caso llamando
al servicio, que es la mitad que sí está construida.

**Cómo se cerró.** La rama existe desde la 010 (`CaseCard.tsx:256`), con la forma escrita a la vista
y el selector que resuelve el caso, y `CASE_KINDS` tiene su etiqueta en español. Lo que la 010 no
dejó fue el test del circuito, aunque su tarea 7 lo pedía: **ninguna prueba resolvía un caso de
rubro por HTTP**, ni acá ni allá. Lo agrega la tarea 24 de esta feature, y es el que hace que RF-24
y RF-25 dejen de estar verdes por la mitad.

### 3. La cola de revisión pasó a tener dos dueños, y la autorización tenía uno — tareas 30 y 24 · **cerrado por la 010**

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

> **Cerrado el 2026-08-30 por decisión del humano, y construido:** los rubros pasan a **compras**,
> y por lo tanto `triage` se queda como está y lo que se movió fue la fila `PRODUCT_CATEGORIES` de la
> matriz. Como la 008 está firmada y la 002 archivada, el cambio no se parchó acá: vive en
> `docs/specs/010-category-ownership/`, firmada el 2026-08-31 y entera en `main`. La lectura que
> quedaba en manos del humano —¿ventas o compras?— la resolvió esa firma, y al revés de lo que este
> documento suponía: **el código estaba bien, y lo que había que enmendar era el acuerdo**.

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
| RF-03 | 6, 8, 9 | 10 *(fija lo que el sistema hace: dos formas, no tres — ver el punto 13 de* Deriva *en `plan.md`)* |
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
| RF-23 | 3, 19, 22, 30 | 23, 24 |
| RF-24 | 20, 22, 30 | 23, 24 |
| RF-25 | 5, 20 | 23 |
| RF-26 | 21, 22, 30 | 24 |
| RF-27 | 3, 28, 29 | 31 |
| RF-28 | 1, 25, 29, 30 | 31, 24 |
| RF-29 | 26 | 31 |
| RF-30 | 27, 29, 30 | 31, 24 |
| RF-31 | 27 | 31 |

**Los 31 requisitos tienen tarea y test**, al 2026-09-01. Hasta el 2026-08-31 esta tabla tenía
negritas —lo que cerraban tareas sin hacer— y dos casilleros vacíos, RF-26 y RF-03.

**RF-03 tiene test, y hay que leerlo antes de creerle.** La tarea 10 lo tenía atribuido y no lo
probaba: sus tres pruebas verifican que todo alias tenga su regla, que las sembradas no se atribuyan
a nadie y que dos grafías que sólo difieren en mayúsculas resuelvan al mismo rubro. El test nuevo sí
abre un rubro y cuenta sus formas escritas, y **fija las dos que el sistema muestra, no las tres que
el criterio firmado pide**: es el punto 13 de *Deriva* en `plan.md`, sigue siendo del humano, y el
test lo dice en su docstring para que nadie lo tome por conformidad.

## Notas para `/converge`

**La lista completa de deriva vive en `plan.md` → *Deriva contra la spec firmada*, y son trece
puntos, de los cuales quedan abiertos siete: el 6 al 11 y el 13.** Acá van las cinco cosas que se
ven desde este documento y conviene que el converge encuentre ya escritas:

- **Los tres huecos de arriba están cerrados**, y ninguno lo cerró este documento sin dejar rastro:
  RF-26 se construyó, la pantalla del caso vino con la 010, y la autorización dejó de tener dos
  dueños cuando la matriz movió los rubros a compras. Lo que le queda al converge no es esta lista.
- **La spec habla de 18 equivalencias y hay 11**, y esto **sigue abierto**. Las 18 grafías se
  **resuelven** igual: ahí el número cambió y el comportamiento no. Pero se **muestran** 11, y el
  criterio de aceptación de RF-03 pide tres formas escritas para Pinturas y Adhesivos donde la
  pantalla enseña dos. Es el punto 13 de *Deriva* en `plan.md`, **es del humano**, y ahora tiene un
  test que fija las dos que se muestran — deliberadamente, y dicho en su docstring.
- **Resolver un caso de rubro ya no tiene salidas mudas.** Una decisión que nombra un rubro
  inexistente, o que no nombra ninguno, **se rechaza**: la transacción en la que `triage` estaba
  resolviendo el caso se aborta, el caso sigue en la cola y la persona recibe el motivo. Era el
  punto 12 de *Deriva* y era el Artículo II al revés.
- **Los criterios de aceptación se verifican contra el fixture fijado**, `price-list-2026-08-28.xlsx`,
  que tiene los números de la spec: 18 formas, 7 rubros, 8 sin categoría, 100 productos. Nunca
  contra el portal en vivo (`TEST-03`, Blocker).
- **El gasto por rubro no está y no tiene que estar**: la spec lo saca de alcance en su primer
  párrafo, porque no hay fuente que ligue lo gastado con el producto. Un converge que lo busque
  está leyendo el pedido original, no la spec firmada.
