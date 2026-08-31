# Rubros unificados — Plan técnico

<!--
  ARTEFACTO INTERNO. Acá van las decisiones técnicas que spec.md no puede llevar.
  No se exporta al cliente.
-->

**Feature:** 008-product-categories · **Spec aprobada el:** 2026-08-29 · **Fecha:** 2026-08-31

**Roles:** `Backend-Architect` (el grueso) · `Frontend-Architect` (las tres pantallas).

> **Cuándo se escribió este documento, y contra qué.** La spec se firmó el 2026-08-29 y la feature
> se construyó el 2026-08-30, en el commit `b759a37`, junto con otras cinco. **Este plan se
> escribió después**, el 2026-08-31, recorriendo el código archivo por archivo: no es el plan que
> guió la construcción, es el plan que dice qué hay. Cada afirmación de acá abajo está verificada
> contra un archivo y una línea, y donde el código y la spec firmada no coinciden **no se escribe
> el código como si fuera lo acordado**: se anota en *Deriva contra la spec firmada*, que es
> material de `/converge`.
>
> El orden de la cadena sí se respetó donde importa: la spec estaba **firmada antes** de que
> existiera el código (Artículo V). Lo que llegó tarde es este documento.

## Constitution Check

| Artículo | Cumple | Cómo |
|---|---|---|
| I — El origen es ajeno y de sólo lectura | Sí | La feature no toca SIGProv. `catalog` consume `category_raw` / `subcategory_raw` que `001` ya extraía del `.xlsx` y guardaba en `staging.price_row` (`ingestion/parsers.py:196-208`, `ingestion/models.py:84-85`). No se agrega navegación ni una request al portal: `grep -rnE "httpx\|requests\." app/modules/portal` sigue vacío. |
| II — Nada se descarta | **Parcial** | **En la ingesta se cumple, y es el artículo que esta feature encarna.** Una forma escrita sin equivalencia no va a un cajón de «otros»: se acumula en `unresolved` y sale como `UnknownCategoryObserved` (`catalog/service.py:349-362`), que `triage` convierte en un caso pendiente (`triage/handlers.py:118-139`). Un producto sin categoría queda `category_id IS NULL` y **es** «sin rubro», contado en `CategoryList` y visible en la cola (`catalog/service.py:699-711`). **Donde no se cumple es en la resolución de un caso**: hay cuatro salidas mudas que resuelven el caso y no hacen nada, sin fila en `operations.exception` y sin que nadie se entere. Ver *Riesgos* y el punto 12 de *Deriva*. |
| III — Flujo unidireccional, `raw` inmutable | Sí | `raw` no se lee ni se escribe en esta feature. La clasificación va de `staging` (vía el evento) a `core`, en un solo sentido, y es reproducible: vaciar `core.product.category_id` y volver a aplicar el lote reconstruye el estado sin extraer de nuevo. `tests/architecture/test_raw_immutability.py` no cambia. |
| IV — Las fronteras entre módulos son reales | Sí | `catalog` y `triage` no se importan: hablan por `UnknownCategoryObserved`, `QuarantineCaseResolved`, `QuarantineRuleRevoked` y `QuarantineRuleRedecided`, todos en `app/shared/events/catalog.py`. `catalog` mantiene su **proyección** de las equivalencias (`core.category_alias`) en lugar de leer `operations.resolution_rule`, igual que `ingestion` con `staging.resolution_rule`. La única frontera cruzada es `identity.dependencies` (`catalog/routes.py:43-49`, `triage/routes.py:15`), la excepción fijada por nombre de archivo en `tests/architecture/test_module_boundaries.py`. |
| V — Spec primero, y con firma | Sí, con una salvedad | `spec.md` en `Aprobado`, firmada por Leandro Carriego — FDE el 2026-08-29, **antes** del commit que construyó la feature. La salvedad no es del código sino de la cadena: `plan.md` y `tasks.md` se escribieron después, y `/analyze`, `/converge` y `/review-feature` no corrieron. Este plan no agrega alcance; lo que el código hace de más o de menos está en *Deriva contra la spec firmada*. |
| VI — Lo que no está tipado y testeado no está terminado | Parcial | Tipos completos, `mypy` limpio sobre `app/`. La clasificación se testea en `tests/integration/features/test_product_categories.py` (20 tests en seis clases) contra el fixture fijado, nunca contra el portal (`TEST-03`). **Falta cobertura en dos puntos**, y están dichos: RF-26 no tiene ni implementación ni test, y las rutas de `/categories` no tienen test de integración HTTP propio ni fila en `tests/integration/api/test_rbac.py`. Ver *Deriva*. |
| VII — Las credenciales de terceros viven sólo en el entorno | Sí | La feature no ve credenciales: no hay extracción. |
| VIII — Un idioma para cada audiencia | Parcial | Código, eventos y modelos en inglés; los `reason` de los casos (`triage/service.py:45`), los mensajes de error (`catalog/service.py:120-122`) y las tres pantallas, en español. **La excepción real**: un caso `unknown_category` se dibuja en `/revision` con su `kind` crudo en inglés, porque `CASE_KINDS` no lo tiene (`frontend/lib/triage/types.ts:15-21`). Ver *Deriva*. |
| IX — Las dependencias entran por la puerta | Sí | **Cero dependencias nuevas**, back y front. `backend/pyproject.toml` y `frontend/package.json` no cambiaron por esta feature. |

**Excepciones solicitadas:** ninguna.

## Enfoque

La feature se apoya en dos piezas que **ya existían y fueron construidas para esto**, y por eso casi
no agrega maquinaria nueva.

La primera es `staging`. `001` ya guardaba `category_raw` y `subcategory_raw` de cada fila, con un
comentario en el modelo que dice literalmente que unificarlas es P7 (`ingestion/models.py:81-85`).
El dato estaba desde el día uno: lo que faltaba era que **viajara hasta `catalog`**, porque
`PriceListNormalized` no lo llevaba. Los dos campos se agregaron a `NormalizedPriceRow` **con
default** (`shared/events/catalog.py:184-185`) y `ingestion` los copia al construir la fila
normalizada (`ingestion/service.py:169-170`). Ése es todo el cambio en `ingestion`.

La segunda es `triage`, que es una cola de excepciones **genérica con reglas aprendidas** y cuyo
propio código anunciaba que «the next problem will add its own» kind. 008 es ese próximo problema:
suma `unknown_category` (`triage/service.py:39`) y nada más de la cola cambia. Una forma escrita que
el sistema no conoce abre un caso; resolverlo crea una `ResolutionRule` —que es el registro de quién
decidió y cuándo, o sea RF-27— y publica `QuarantineCaseResolved`. Revocarla reabre sus casos sola
(`triage/repository.py:111-130`), que es RF-31 sin escribir una línea. El `fingerprint` de la cola
da gratis que la misma forma escrita no se pregunte cien veces en un lote de cien productos: el
`ON CONFLICT` sobre el índice parcial de pendientes suma `occurrences` en vez de abrir otro caso
(`triage/repository.py:36-62`).

Sobre eso, `catalog` pone lo que es suyo: el **rubro** y la **equivalencia**. El rubro es una
entidad del negocio con nombre propio que el cliente edita (RF-05, RF-06, RF-07). La equivalencia
—forma escrita → rubro— es una proyección local alimentada por los eventos de `triage`, siguiendo el
precedente de `ingestion.ResolutionRuleProjection`: `catalog` no lee la tabla de `triage`, escucha
sus hechos. Clasificar un lote es entonces un diccionario en memoria construido de una sola consulta
a `core.category_alias` (`catalog/service.py:231-237`), no una llamada a nadie.

**El sistema no adivina en ningún punto.** El matcheo es contra la tabla de equivalencias, no contra
un normalizador ingenioso: `Pinturas/Adhesivos` y `PINTURAS Y ADHESIVOS` no se parecen lo suficiente
como para que ningún algoritmo honesto las una, y por eso las formas medidas entran **sembradas por
migración desde la tabla que el cliente firmó** (`alembic/versions/0010_product_categories.py:60-74`).
La normalización que sí se aplica es deliberadamente tonta —recortar, colapsar espacios internos,
`casefold`— y vive en `shared/text.py:68-83`; sólo colapsa los pares que difieren únicamente en
mayúsculas. Todo lo que no esté en la tabla va a revisión, que es RF-21 y RF-22.

La propuesta de rubro para un producto sin categoría (RF-14) **no se siembra**: se deriva en el
momento, consultando qué rubro tienen los productos ya clasificados que comparten esa subcategoría
(`catalog/repository.py:380-395`). Es más honesto que una tabla fija —la propuesta refleja el estado
real del catálogo y mejora sola a medida que se clasifica— y hace verdadera la frase de la spec: el
sistema propone sobre lo que ya está decidido. Si la subcategoría no resuelve a **exactamente un**
rubro entre los clasificados, se trata como no conocida y se cae en RF-17: se presenta sin propuesta
(`catalog/service.py:799-800`). Es la lectura fiel de «subcategoría conocida» y evita que el sistema
desempate por su cuenta.

**La propuesta se calcula y se muestra, nunca se guarda**, y ahí está RF-16 entero: no hay columna
donde escribirla, así que no existe el estado «propuesto pero sin confirmar» en el que un producto
podría quedar contando como clasificado sin que nadie lo haya decidido. Hasta que se confirma, el
producto tiene `category_id` nulo y es «sin rubro» a todos los efectos: aparece en los cortes, entra
en los totales y sigue en la cola. Confirmar la propuesta y corregirla son **la misma escritura**
—`PUT` con el rubro elegido—, y la única diferencia es qué rubro viaja (`catalog/service.py:814-864`).

Una decisión tomada a mano no se pisa después. `_classify` sale temprano si el producto tiene
`classified_by_user_id` (`catalog/service.py:676-677`): el lote de mañana vuelve a traer la misma
categoría escrita y no revierte lo que una persona decidió.

### Corregir una equivalencia: RF-28 y RF-29

Es la parte que más se piensa, porque toca una asimetría que no se ve a primera vista: **una
equivalencia sembrada no nace de una decisión humana y por lo tanto podría no tener regla en
`triage`**. Si las equivalencias se direccionaran por `rule_id`, las de fábrica no se podrían
corregir ni dejar sin efecto — y corregir una sembrada es justamente el caso probable, porque la
siembra sale de una medición y no de que alguien la haya pensado rubro por rubro.

La salida fue **hacerlas uniformes**: la migración siembra cada forma **dos veces**, como regla de
`triage` —`kind="unknown_category"`, `matcher={"kind", "category_text"}`, `decision={"category_id"}`—
y como fila de `core.category_alias` que la proyecta (`0010_product_categories.py:190-235`). Desde
ahí toda equivalencia, sembrada o aprendida, es una regla con su `rule_id`, y RF-27 a RF-31 se
resuelven todos por el mismo camino sin ninguna rama especial. Lo verifica
`test_product_categories.py::TestTheSignedTableIsAlreadyLoaded::test_every_equivalence_has_a_rule_behind_it`.

Con eso, RF-28 es una capacidad nueva y chica en `triage`: `redecide_rule`, que reapunta la
`decision` de una regla vigente y publica `QuarantineRuleRedecided` (`triage/service.py:213-251`).
**No es una violación del «se revoca, nunca se borra»**: no se pierde nada. La regla suma
`updated_by_user_id` y `updated_at` (`triage/models.py:110-111`), así que sigue constando quién la
creó y cuándo, y pasa a constar además quién la corrigió. Revocar y recrear, que sería la
alternativa purista, está descartada por la spec misma: revocar manda los productos de vuelta a
revisión (RF-31) y RF-29 pide exactamente lo contrario, que se **reasignen**. Una regla ya revocada
se rechaza con conflicto, para no revivir en silencio una equivalencia que alguien apagó
(`triage/service.py:231-232`).

RF-29 es entonces una sola operación en `catalog` cuando le llega el evento: reapuntar el alias y
mover los productos que esa regla había clasificado (`catalog/service.py:908-927`), acotado por
`WHERE classified_by_rule_id = :rule_id` (`catalog/repository.py:397-406`). Ese `classified_by_rule_id`
es lo que hace que la reasignación sea **exacta**: alcanza a lo que la equivalencia clasificó y no
toca lo que una persona decidió a mano producto por producto, que no depende de ella y tiene esa
columna en nulo (`catalog/service.py:836`).

### Y al revocar, RF-31 sin un camino especial

Al revocarse una equivalencia, `catalog` desasigna esos mismos productos y publica
`UnknownCategoryObserved` con la forma escrita que la equivalencia resolvía
(`catalog/service.py:929-962`). Es el **mismo evento** que produce un lote normal, así que `triage`
abre el caso por el camino de siempre y no por una rama de revocación. Como `revoke_rule` además
reabre los casos que esa regla había resuelto, y `open_case` hace `ON CONFLICT DO UPDATE` sobre el
fingerprint pendiente, las dos rutas convergen en **un** caso pendiente y no en dos.

Eso deja RF-30 y RF-31 funcionando también para las sembradas, que era el otro agujero: revocar la
equivalencia de `Ferreteria Gral.` manda sus productos a revisión igual que si la hubiera decidido
alguien.

## Módulos afectados

| Módulo | Qué cambia | Nuevo |
|---|---|---|
| `catalog` | Entidades `Category` y `CategoryAlias` (`models.py:199-263`); seis columnas en `Product` (`models.py:105-117`); `_classify` dentro de `apply_price_batch`; propuesta por subcategoría; los dos routers nuevos, `categories_router` y `products_router`, registrados en `main.py:248-249` | No |
| `triage` | Kind `unknown_category`; `_matcher_of` matchea por texto de categoría (`service.py:271-274`); `redecide_rule` con `updated_by_user_id` / `updated_at`; `created_by_user_id` pasa a nulo | No |
| `ingestion` | `NormalizedPriceRow` viaja con `category_raw` y `subcategory_raw` (`service.py:169-170`). Nada más: el parser ya los leía | No |
| `identity` | Sección `PRODUCT_CATEGORIES` en la matriz de `permissions.py:31,86` — dueño `WRITE`, ventas `WRITE`, compras `NONE`. **No** se agregó ningún `require_sales()` | No |
| `shared` | Dos campos en `NormalizedPriceRow`, dos eventos nuevos (`events/catalog.py:477-515`), `collapse_written_form` (`text.py:68-83`) | — |
| Frontend | `(private)/rubros/`, `rubros/sin-clasificar/`, `rubros/equivalencias/`; `components/categories/{CategoryList,UnclassifiedQueue,AliasList}.tsx`; `app/actions/categories.ts`; entrada de menú en `components/auth/Navigation.tsx:20` y acción pendiente en `lib/operations/actions.ts:140-146` | — |

**No se creó ningún módulo.** Los rubros son vocabulario del catálogo —producto, precio, categoría
es la definición del módulo en `ARCHITECTURE.md`— y una cola de revisión con reglas aprendidas ya
tenía dueño. Un módulo `categories` sería acumulación de archivos, no una capacidad del negocio con
lenguaje propio.

## Eventos de dominio

Todos viven en `app/shared/events/catalog.py` (`GEN-08`), son `frozen` y llevan identificadores y
valores planos. Verificados contra el `handlers.py` de cada módulo, no sólo contra el catálogo.

| Evento | Lo publica | Lo consume | Qué lleva |
|---|---|---|---|
| `PriceListNormalized` *(modificado)* | `ingestion` (`service.py:158-173`) | `catalog.apply_batch` (`handlers.py:70-79`) | Cada `NormalizedPriceRow` suma `category_raw: str \| None` y `subcategory_raw: str \| None`, con default para no romper a quien ya lo construía en `001` |
| `UnknownCategoryObserved` *(nuevo)* | `catalog` — al aplicar un lote (`service.py:353-362`) y al revocar una equivalencia (`service.py:946-958`) | `triage.open_unknown_categories` (`handlers.py:118-139`) | `batch_id` y una tupla de `UnknownCategory(category_text, product_codes)`. Una entrada por forma escrita, no por producto. Es lo que abre el caso (RF-21, RF-22, RF-26, RF-31) |
| `QuarantineCaseResolved` *(existente)* | `triage` (`service.py:171-183`) | `catalog.apply_decision` (`handlers.py:90-139`) | Con `kind="unknown_category"`: `decision={"category_id": N}` y `matcher={"kind", "category_text"}`. `catalog` proyecta la equivalencia y la aplica retroactivamente (RF-24, RF-25) |
| `QuarantineRuleRevoked` *(existente)* | `triage` (`service.py:201-209`) | `catalog.undo_rule` (`handlers.py:142-154`) | `rule_id`, `kind`, `matcher`, `decision`. Con `kind="unknown_category"`, `catalog` baja la proyección, desasigna sus productos y republica `UnknownCategoryObserved` (RF-30, RF-31) |
| `QuarantineRuleRedecided` *(nuevo)* | `triage` (`service.py:238-248`) | `catalog.repoint_rule` (`handlers.py:157-172`) | `rule_id`, `kind`, `matcher`, `decision`, `previous_decision`, `decided_by_user_id`. `catalog` reapunta el alias y **reasigna sin mandar nada a la cola** (RF-28, RF-29) |
| `ManualChangeRecorded` *(existente, reutilizado)* | `catalog` — al clasificar un producto (`service.py:839-851`) y al tocar la lista de rubros (`service.py:981-992`) | `operations` (el log único de la plataforma, de 003) | `entity_type` (`catalog.product` o `catalog.product_category`), `entity_id`, `action`, `actor_user_id`, `section=SALES`, `field`, `old_value`, `new_value`. Es lo que hace verdadero RF-18 sin que `catalog` sepa que existe un log |

No hay ciclo (`GEN-05`): `catalog → triage` va por `UnknownCategoryObserved` y `triage → catalog`
por los tres eventos de decisión, y ninguno de esos handlers vuelve a publicar hacia el otro lado
dentro de la misma cadena. La única republicación —`forget_category_alias` publicando
`UnknownCategoryObserved` desde el handler de `QuarantineRuleRevoked`— termina en `triage.open_case`,
que no publica nada.

`catalog` **no** anuncia «producto clasificado» como evento propio: hoy nadie lo escucharía, y
publicar sin consumidor sería vocabulario compartido que nadie usa. Cuando P3 lo necesite, lo agrega
su plan.

## Datos

Todo en el esquema `core`, salvo los tres cambios de `operations.resolution_rule`. Detalle completo
en **`data-model.md`**.

Migración: **`0010_product_categories`**, sobre la cabeza `0009` — no `0003` sobre `0002`, como
decía la versión anterior de este documento; cuando la feature se construyó, la cabeza era `0009`.

- **`core.category`** — el rubro. `id`, `name` único (100), `created_at`. RF-01, RF-05, RF-06.
  RF-07 no es un `ON DELETE`: la FK va `RESTRICT` como red, pero la verificación vive en el servicio
  (`catalog/service.py:753-781`), porque el sistema tiene que poder **decir por qué** no se borra.
- **`core.category_alias`** — la equivalencia. `id`, `category_id` FK `RESTRICT`, `text_normalized`
  único (200), `text_original`, `rule_id` nulo indexado, `source` (`SEED` \| `LEARNED`),
  `created_at`. Es la proyección local de las reglas de `triage`.
- **`core.product`** — suma `category_id` nulo indexado, `category_raw`, `subcategory_raw`
  indexado, `classified_by_user_id`, `classified_at` (RF-18) y `classified_by_rule_id` indexado,
  este último siguiendo el precedente de `registered_by_rule_id`.
- **`operations.resolution_rule`** — `created_by_user_id` pasa a **nulo**, y entran
  `updated_by_user_id` y `updated_at`. Lo primero es lo que le permite a la siembra decir la verdad:
  una equivalencia que vino con el sistema **no la decidió nadie**, y ponerle el id del dueño sería
  mentir en un registro de auditoría. En la pantalla se lee como lo que es, «Sembrado en la puesta
  en marcha» (`0010:220`).

La migración **siembra los 7 rubros de la tabla firmada y sus formas escritas**, cada una dos veces
—como regla y como alias—. Sembrar no es que el sistema decida: es cargar el acuerdo. Sin la
siembra, la primera corrida mandaría los 100 productos a revisión, que es exactamente lo que la spec
promete evitar.

**Once alias para las dieciocho grafías firmadas.** La clave de matcheo es el texto con espacios
colapsados y en `casefold`, así que `ELECTRICIDAD` y `Electricidad` **son la misma clave** —que es
justamente lo que la normalización tiene que colapsar— y el índice único no admite las dos filas.
Las 18 grafías quedan cubiertas por 11 equivalencias, y las que difieren en algo más que mayúsculas
—`Ferreteria Gral.`, `Herram.`, `Pinturas/Adhesivos`, `Seg. Industrial`— siguen siendo filas propias
apuntando al mismo rubro.

**Qué se conserva, y qué no.** Las 18 formas **se resuelven** al rubro que les toca, que es RF-02:
cada grafía colapsa a una clave que la siembra dejó en la tabla, así que ninguna queda afuera. El
test lo fija para el par que la normalización colapsa y para el que no
(`test_a_written_form_that_only_differs_in_case_is_one_equivalence`); las quince restantes las
sostiene la estructura de la siembra, no una aserción.

Y **cada equivalencia** —cada una de las 11 filas— tiene su regla en `triage`, así que RF-28 a RF-31
alcanzan a todas; eso es lo que verifica `test_every_equivalence_has_a_rule_behind_it`, que recorre
`category_alias` y no la lista de grafías. Lo que **no** vale decir es que cada grafía tenga su
regla: el `seen` de `_seed` saltea la clave repetida (`0010_product_categories.py:198-206`), así que
`ELECTRICIDAD` y `Electricidad` comparten una sola `resolution_rule` y una sola fila. Son **11 reglas
para 18 formas**, y las 7 grafías que sólo difieren en mayúsculas no tienen regla propia.

Y lo que se **muestra** son 11, no 18: `CategoryRead.aliases` sale de `core.category_alias`
(`catalog/service.py:699-711`) y la pantalla imprime su `text_original`
(`frontend/components/categories/CategoryList.tsx:65`). Eso choca de frente con el criterio de
aceptación firmado de RF-03 —«Al abrir Pinturas y Adhesivos se ven las **tres** formas escritas que
le corresponden» (`spec.md:191`)—, porque ese rubro tiene dos filas, `PINTURAS Y ADHESIVOS` y
`Pinturas/Adhesivos`: la grafía en título se colapsó y no se ve en ninguna pantalla. RF-03 es un
requisito de **mostrar**, no de resolver, y por eso no lo salva que el matcheo funcione. Está anotado
como el punto 13 de *Deriva*.

`data-model.md` decía «18 filas», contradiciendo su propia regla de normalización dos párrafos antes,
y **quedó corregido en esta pasada**: es un artefacto técnico interno, no la spec firmada. La spec
sigue hablando de 18 grafías, que es lo correcto: son 18 formas escritas.

`category_id` nulo **es** «sin rubro». No hay fila centinela: un rubro llamado «Sin rubro» sería
borrable, renombrable y contable como los demás, y RF-07 no tendría sentido sobre él. El corte por
rubro lo agrega como grupo al proyectar (`catalog/repository.py:292-302` y `service.py:699-711`), que
es lo que RF-09 pide.

**Un detalle que hay que saber al leer los números**: los conteos —por rubro, sin rubro y total—
cuentan sólo productos `ACTIVE` (`repository.py:300`, `364`, `376`). Un producto discontinuado no
entra en ninguno de los tres, así que la suma sigue cerrando contra el total que la pantalla muestra,
que es el de productos vigentes.

**Índices efectivamente creados**: `category_alias(category_id)`, `category_alias(rule_id)`,
`product(category_id)`, `product(subcategory_raw)`, `product(classified_by_rule_id)`. **No** existe
el índice parcial sobre `category_id IS NULL` que la versión anterior de `data-model.md` prometía;
con cien productos no hace falta, y ese documento ya quedó corregido.

## Contratos

El detalle completo —cuerpos, respuestas de ejemplo, cada error con su código y su motivo, y el
contrato de eventos campo por campo— está en **[`contracts/README.md`](contracts/README.md)**. Acá
va el resumen que alcanza para decidir.

Toda ruta declara su autorización (`PY-09`, Blocker) y `tests/architecture/test_route_authorization.py`
lo verifica dos veces: que el árbol de dependencias la declare, y que un anónimo reciba 401. Ninguna
ruta de esta feature está en `PUBLIC_ROUTES`.

**La autorización no se resolvió con un `require_sales()`.** Se agregó la sección
`PRODUCT_CATEGORIES` a la matriz de `identity/permissions.py:86` —dueño `WRITE`, ventas `WRITE`,
compras `NONE`— y las rutas usan el `require_section()` genérico que ya existía desde la 003. Es
mejor que una función por rol: la matriz la recorre entera un test
(`tests/unit/identity/test_permissions.py:34`), y una sección nueva sin permiso decidido falla en vez
de defaultear.

### Rutas de `catalog`

| Método y ruta | Dependencia declarada | Quién entra | RF | Cuerpo / respuesta |
|---|---|---|---|---|
| `GET /categories` | `get_current_user` | los tres roles | RF-01, RF-03, RF-04, RF-09, RF-10, RF-11 | → `CategoryList{ items:[CategoryRead{id,name,product_count,aliases:[CategoryAliasRead]}], unclassified_count, total_products }` |
| `GET /categories/unclassified` | `get_current_user` | los tres roles | RF-11, RF-12, RF-14, RF-15, RF-17 | `?skip&limit` → `UnclassifiedList{ items:[UnclassifiedProduct{product_id,code,description,category_raw,subcategory_raw,proposed_category_id,proposed_category_name}], total, skip, limit }` |
| `GET /categories/aliases` | `get_current_user` | los tres roles | RF-27 (parcial: ver *Deriva*) | → `list[CategoryAliasRead{id,category_id,text_original,text_normalized,rule_id,source,created_at}]` |
| `POST /categories` | `require_section(PRODUCT_CATEGORIES, WRITE)` | dueño · ventas | RF-05 | `CategoryWrite{name:1..100}` → `201 CategoryRead`. `409` si el nombre ya existe |
| `PATCH /categories/{category_id}` | `require_section(PRODUCT_CATEGORIES, WRITE)` | dueño · ventas | RF-06 | `CategoryWrite` → `CategoryRead`. `404` si no existe, `409` si el nombre choca |
| `DELETE /categories/{category_id}` | `require_section(PRODUCT_CATEGORIES, WRITE)` | dueño · ventas | RF-07 | → `204`. `409` con el motivo si tiene productos, y también si tiene formas escritas |
| `PUT /products/{product_id}/category` | `require_section(PRODUCT_CATEGORIES, WRITE)` | dueño · ventas | RF-13, RF-15, RF-18, RF-19, RF-20 | `ProductCategoryWrite{category_id}` → `UnclassifiedProduct`. Quién decidió sale del token, nunca del cuerpo |

Las rutas literales `/unclassified` y `/aliases` se declaran **antes** de `/{category_id}` para que
no se lean como un id (`catalog/routes.py:151-184`).

### Rutas de `triage` que esta feature usa

| Método y ruta | Dependencia declarada | Quién entra | RF |
|---|---|---|---|
| `GET /triage/cases?kind=unknown_category` | `require_section(PRICES, WRITE)` | dueño · **compras** | RF-21, RF-23, RF-26 |
| `POST /triage/cases/{case_id}/resolution` | `require_section(PRICES, WRITE)` | dueño · **compras** | RF-24, RF-25 |
| `GET /triage/rules?kind=unknown_category` | `require_section(PRICES, WRITE)` | dueño · **compras** | RF-27 |
| `PATCH /triage/rules/{rule_id}` *(nueva en 008)* | `require_section(PRICES, WRITE)` | dueño · **compras** | RF-28, RF-29 |
| `DELETE /triage/rules/{rule_id}` *(ya existía)* | `require_section(PRICES, WRITE)` | dueño · **compras** | RF-30, RF-31 |

`PRICES` da a ventas sólo **lectura** (`permissions.py:75`), así que **ventas recibe 403 en las
cinco**. La spec firmada nombra a ventas en RF-28 y pone a Julián como el actor de H4 y H5. Eso es
una deriva, no una decisión de este plan: está en *Deriva contra la spec firmada* y es de `/converge`.

### Frontend

Tres pantallas bajo `(private)/rubros/`, Server Components que leen con `fetchFromApi` y escriben
por Server Actions (`app/actions/categories.ts`), como el resto del proyecto:

| Pantalla | Componente | Lee | Escribe |
|---|---|---|---|
| `/rubros` | `components/categories/CategoryList.tsx` | `GET /categories` | `POST` · `PATCH` · `DELETE /categories` |
| `/rubros/sin-clasificar` | `components/categories/UnclassifiedQueue.tsx` | `GET /categories/unclassified?limit=200`, `GET /categories` | `PUT /products/{id}/category` |
| `/rubros/equivalencias` | `components/categories/AliasList.tsx` | `GET /categories/aliases`, `GET /categories`, `GET /triage/rules?kind=unknown_category` | `PATCH` y `DELETE /triage/rules/{id}` |

Los botones de escritura se muestran con `canEdit(permissions, 'PRODUCT_CATEGORIES')`, que es una
conveniencia y nunca la restricción: el backend decide igual. La entrada de menú está en
`components/auth/Navigation.tsx:20`, gateada por la misma sección, y `/rubros/sin-clasificar` figura
entre las acciones pendientes del dueño (`lib/operations/actions.ts:140-146`).

**No se reusaron `components/triage/RuleList.tsx` ni `CaseCard.tsx`**, como decía la versión anterior
de este plan: `AliasList.tsx` es un componente propio, y `CaseCard.tsx` no tiene rama para
`unknown_category`. Lo segundo es un hueco, no una decisión: está en *Deriva*.

## Cobertura de los requisitos

Cada RF de la spec, con dónde vive y dónde se prueba. En **negrita**, lo que no está cerrado.

| RF | Dónde | Test |
|---|---|---|
| RF-01 | `core.category` + `GET /categories` + `/rubros` | `TestKeepingTheRubroList` |
| RF-02 | `_classify` (`service.py:651-685`) contra `category_alias` | `TestTheSignedTableIsAlreadyLoaded` |
| RF-03 | `CategoryRead.aliases` → `CategoryList.tsx:65` | **sin test propio: ninguna prueba abre un rubro y cuenta sus formas escritas. La clase que esta fila citaba, `TestTheSignedTableIsAlreadyLoaded`, verifica otras tres cosas — que todo alias tenga `rule_id` (`test_product_categories.py:87`), que las sembradas no se atribuyan a nadie (`:102`) y que dos grafías que sólo difieren en mayúsculas resuelvan al mismo rubro (`:114`). Y se muestran 11 formas, no 18: ver el punto 13 de *Deriva*** |
| RF-04 | `products_per_category()` | `TestRevokingAnEquivalence::test_the_cuts_still_add_up_to_the_total` |
| RF-05 | `create_category` + `POST /categories` | `test_a_rubro_can_be_added_and_renamed` |
| RF-06 | `rename_category` + `PATCH /categories/{id}` | `test_a_rubro_can_be_added_and_renamed` |
| RF-07 | `delete_category` (chequeo en el servicio) | `test_a_rubro_in_use_is_not_deleted_and_says_why` |
| RF-08 | `product.subcategory_raw` + `UnclassifiedProduct.subcategory_raw` | **sólo la mitad: se conserva y se prueba; «mostrar» sólo ocurre mientras el producto está sin rubro** |
| RF-09 | `unclassified_count` al lado de la lista + fila «Sin rubro» en `CategoryList.tsx` | `test_the_cuts_still_add_up_to_the_total` |
| RF-10 | `total_products = sum(counts.values())` | `test_the_cuts_still_add_up_to_the_total` |
| RF-11 | `count_unclassified()` | `TestTheQueueOfProductsWithoutARubro` |
| RF-12 | `GET /categories/unclassified` + `/rubros/sin-clasificar` | `TestTheQueueOfProductsWithoutARubro` |
| RF-13 | `set_product_category` + `PUT /products/{id}/category` | `test_confirming_takes_it_out_of_the_queue_and_says_who` |
| RF-14 | `rubro_of_subcategory()` + `unclassified()` | `test_a_known_subcategory_proposes_its_rubro` |
| RF-15 | la misma escritura para confirmar y corregir | `test_confirming_takes_it_out_of_the_queue_and_says_who` |
| RF-16 | la propuesta no tiene columna | `test_a_proposal_is_not_an_assignment` |
| RF-17 | cero o más de un rubro → sin propuesta | `test_a_subcategory_that_points_at_two_rubros_proposes_nothing` |
| RF-18 | `classified_by_user_id` / `classified_at` + `ManualChangeRecorded` | `test_confirming_takes_it_out_of_the_queue_and_says_who` |
| RF-19 | `unclassified()` filtra por `category_id IS NULL` | `test_confirming_takes_it_out_of_the_queue_and_says_who` |
| RF-20 | `PUT /products/{id}/category` sobre un producto ya clasificado | **la API lo permite; ninguna pantalla ofrece llegar a un producto ya clasificado** |
| RF-21 | `UnknownCategoryObserved` → `open_case` | `test_it_opens_one_case_for_a_hundred_products` |
| RF-22 | `_classify` deja `category_id` nulo | `test_the_products_are_left_without_a_rubro` |
| RF-23 | `payload["category_text"]` del caso | **el backend lo guarda; `CaseCard.tsx` no lo muestra** |
| RF-24 | `learn_category_alias` sobre `QuarantineCaseResolved` | `test_deciding_classifies_what_was_already_set_aside` (llama al servicio, no a la pantalla) |
| RF-25 | el alias se consulta en cada lote | `test_the_decision_matches_on_the_written_form` |
| RF-26 | — | **no existe: nadie cuenta los pendientes por categoría, y no hay test** |
| RF-27 | `GET /categories/aliases` + `GET /triage/rules` para el autor | **parcial: quién decidió sale de `triage`, que ventas no puede leer** |
| RF-28 | `redecide_rule` + `PATCH /triage/rules/{id}` | `TestCorrectingAnEquivalence` |
| RF-29 | `repoint_category_alias` | `test_it_reassigns_without_going_through_review` |
| RF-30 | `DELETE /triage/rules/{id}` | `TestRevokingAnEquivalence` |
| RF-31 | `forget_category_alias` → `UnknownCategoryObserved` | `test_the_products_go_back_to_review` |

## Alternativas descartadas

- **Un módulo `categories` propio.** Partiría en dos el lenguaje del catálogo: el producto quedaría
  en un módulo y su rubro en otro, y clasificar un lote —que hoy es un diccionario en memoria— pasaría
  a ser un ida y vuelta de eventos dentro de la misma transacción. La frontera estaría mal trazada, y
  la constitución dice que en ese caso se corrige la frontera.
- **La equivalencia como tabla exclusiva de `catalog`, sin regla de `triage`.** Obligaría a `catalog`
  a reabrir casos al revocar, y no puede hablarle a `triage` sin un evento nuevo. Se terminaría
  reconstruyendo, peor, lo que `triage` ya hace, y se perdería el registro de quién decidió que RF-27
  pide.
- **Un normalizador que unifique las formas escritas solo** —quitar acentos, expandir `/` a `y`,
  cortar abreviaturas—. Es el camino corto a violar el Artículo II: acierta con `Herram.` y algún día
  une dos rubros que el negocio distingue, en silencio y sin que nadie lo decida. La tabla de
  equivalencias es explícita y auditable; un normalizador es una opinión escondida.
- **Sembrar también el mapa subcategoría → rubro.** Nace desactualizado. Derivarlo de los productos
  ya clasificados sale de una consulta y siempre dice la verdad.
- **Una fila `Sin rubro` en `core.category`.** Ver *Datos*.
- **Búsqueda difusa —`pg_trgm`, distancia de edición— para proponer el rubro de una forma escrita
  nueva.** Es una dependencia y una decisión automática donde la spec puso a una persona, y está
  explícitamente fuera de alcance.
- **`require_sales()` en `identity/dependencies.py`**, simétrico de un `require_purchasing()`. Se
  descartó en la implementación a favor de la sección `PRODUCT_CATEGORIES` en la matriz: la matriz la
  recorre un test entera, una función por rol no. (Y `require_purchasing()` nunca existió: la
  versión anterior de este plan lo daba por hecho.)
- **Revocar y recrear para corregir una equivalencia.** Es lo purista y lo que la spec prohíbe:
  revocar manda los productos a revisión (RF-31) y RF-29 pide reasignarlos.

## Riesgos

| Riesgo | Impacto | Cómo se mitiga |
|---|---|---|
| La siembra queda desincronizada de lo que el proveedor manda: aparece una decimonovena forma escrita | Bajo. Es el caso normal, no una falla | Va a revisión y alguien la decide una vez. Es literalmente H4 funcionando — **con la salvedad de que hoy esa decisión no se puede tomar desde ninguna pantalla** (ver *Deriva*) |
| Cambiar `NormalizedPriceRow` toca el contrato de `001`, que ya estaba construido | Medio: podía romper tests de `001` | Los dos campos entraron con default (`events/catalog.py:184-185`). Los tests que construyen el evento a mano siguen compilando |
| `_matcher_of` de `triage` armaba el matcher con `product_code`, y para 008 tiene que armarlo con el texto de la categoría | Alto si se pasa por alto: la equivalencia se aplicaría a un solo producto y RF-25 no andaría | Resuelto con una rama explícita (`triage/service.py:271-274`) y fijado por `test_the_decision_matches_on_the_written_form` |
| Sembrar sólo los alias y no las reglas: las equivalencias de fábrica quedarían sin `rule_id` y no se podrían ni corregir ni revocar | Alto, y silencioso: no falla nada, simplemente RF-28 y RF-30 no las alcanzan | `test_every_equivalence_has_a_rule_behind_it` recorre **todas** las equivalencias y exige regla vigente |
| `redecide_rule` sobre una regla ya revocada | Medio: reviviría una equivalencia que alguien apagó | Rechazado con `ConflictError` (`triage/service.py:231-232`), fijado por `test_a_revoked_equivalence_cannot_be_re_pointed` |
| Al revocar, un producto vuelve a revisión y su `category_id` queda colgado | Medio: los totales de RF-10 dejarían de cerrar | `forget_category_alias` desasigna por `classified_by_rule_id` y el producto vuelve a «sin rubro», que sigue contando. Fijado por `test_the_cuts_still_add_up_to_the_total` |
| `learn_category_alias` recorre la cola de sin clasificar con un tope de 5000 (`MAX_RECLASSIFIED`) | Bajo hoy —el catálogo tiene 100 productos— y creciente | El tope existe para que una decisión no se convierta en un scan sin límite. Si el catálogo crece, la reclasificación tiene que pasar a una task de Celery, no a subir el número |
| La pantalla de equivalencias muestra botones que el backend rechaza para ventas | **Alto y visible**: Julián ve «Corregir» y «Dejar sin efecto» y recibe 403 | **No mitigado.** Es la deriva de autorización de abajo, y es de `/converge` |
| Una decisión sobre un caso `unknown_category` que nombra un rubro inexistente —o a la que le falta el texto— **resuelve el caso y no hace nada** | Medio, y silencioso: el caso sale de la cola, la equivalencia no se crea, ningún producto se clasifica y no queda fila en `operations.exception`. `decision` es un dict libre desde la ruta (`triage/schemas.py:47-49`), así que la puerta está abierta | **No mitigado.** Cuatro salidas mudas: `catalog/service.py:884-888` (log y `return`), `catalog/service.py:916-918` (`return` sin log siquiera), y en `catalog/handlers.py` el `if category_id is not None and text:` de `:130` y el `if category_id is None: return` de `:168-169`, ninguno con `else`. `triage` ya escribió `case.status = RESOLVED` y commitea igual (`triage/service.py:164-184`) |
| Resolver un caso `unknown_category` con `remember: false` crea una equivalencia **sin regla**: `rule_id` queda nulo y RF-28 y RF-30 no la alcanzan | Bajo hoy —la pantalla siempre manda `remember: true`— y silencioso: la equivalencia se aplica igual, pero no se puede corregir ni apagar | **No mitigado.** El invariante «toda equivalencia tiene su regla» lo sostienen la siembra y el camino normal, no la base: `core.category_alias.rule_id` es nulable (`catalog/models.py:253`) |

## Contexto de traspaso

**Para el Developer** — El camino del dato es corto y conviene tenerlo entero antes de tocar nada:
`ingestion` copia `category_raw` / `subcategory_raw` a `NormalizedPriceRow`; `catalog.apply_price_batch`
carga las equivalencias **una vez** en un diccionario (`service.py:231-237`) y llama a `_classify` por
fila; lo que no resuelve se acumula en `unresolved` y sale como **un** `UnknownCategoryObserved` al
final del lote. Si vas a tocar la clasificación, tocá `_classify` y nada más: es una `@staticmethod`
pura sobre el producto y la fila, y por eso se puede testear sin base.

Cinco decisiones **ya tomadas, no las rediscutas**: los rubros van en `catalog` y no en un módulo
nuevo; las equivalencias son reglas de `triage` **proyectadas** en `catalog` (nunca un `SELECT` a
`operations.resolution_rule`); «sin rubro» es `category_id IS NULL` y no una fila; toda equivalencia
—sembrada o aprendida— tiene su `rule_id`, para que no haya dos clases; y la autorización de
`/categories` es la sección `PRODUCT_CATEGORIES` de la matriz, no un `require_sales()`.

Lo que **no** hay que tocar: `portal`, `raw`, y el parser de `001` —`category_raw` ya se extrae desde
el día uno—. Y lo que no hay que hacer bajo ningún concepto: resolver el matcheo con un normalizador
que adivine. `collapse_written_form` hace tres cosas y ninguna más. Si una forma escrita no está en
la tabla, va a revisión: **esa es la feature**.

Si venís a cerrar los huecos, están enumerados abajo en *Deriva* y desglosados como tareas 21, 22, 24
y 30 en `tasks.md`. Las tres primeras son frontend y backend chico; la cuarta —quién autoriza un caso
de `triage` según su `kind`— es una decisión de arquitectura y **está frenada a la espera de la firma
de la 010**: planificarla antes es resolver un alcance que nadie acordó (Artículo V).

**Para el Tester** — Lo que puede romperse de verdad, en orden:

1. **El matcher de `triage`.** Si sale por `product_code` en vez de por `category_text`, la
   equivalencia se aplica a un producto y no a una forma escrita, y RF-25 falla en silencio mientras
   todo lo demás parece andar. Es el primer test y ya existe; no lo debilites.
2. **Corregir contra revocar.** Que el `PATCH` **reasigne sin pasar por revisión** —si los productos
   aparecen en la cola, se implementó RF-31 donde iba RF-29—; que alcance igual a una **sembrada** que
   a una aprendida; y que **no** toque los productos que alguien clasificó a mano, que tienen
   `classified_by_rule_id` nulo.
3. **Los totales después de revocar.** Es el momento en que más fácil se pierde un producto: la suma
   de los rubros más «sin rubro» tiene que seguir dando el total. Ojo con que el conteo es sobre
   productos `ACTIVE`: un test que discontinúe un producto y espere que el total no se mueva está
   escrito contra otra cosa.
4. **Un caso, no cien.** Cien productos del mismo lote con la misma forma desconocida abren un solo
   caso con `occurrences=100`, por el `fingerprint` y el índice parcial de pendientes.
5. **La propuesta que empata.** Una subcategoría que apunta a dos rubros entre los clasificados tiene
   que caer en RF-17 —sin propuesta—, no desempatar.

**Tests que hoy pasan por la razón equivocada, y que hay que mirar:** RF-24 y RF-25 están verdes
porque los tests resuelven el caso **llamando al servicio**, que es la mitad construida. Desde la
pantalla no se puede resolver un caso `unknown_category`: no hay control. Un test de UI o de ruta que
lo intente es lo que falta, y es la tarea 24 de `tasks.md`. Lo mismo con RF-28 y RF-30: los tests los
ejercen desde el servicio, y por HTTP con un usuario de ventas darían 403.

**Y RF-03 no tiene test.** La tabla de cobertura lo atribuía a `TestTheSignedTableIsAlreadyLoaded`, y
esa clase no lo prueba: sus tres pruebas verifican `rule_id`, atribución y matcheo, ninguna abre un
rubro y cuenta sus formas escritas. Si escribís ese test, escribilo contra lo que el sistema hace —
`Pinturas y Adhesivos` muestra **dos** formas, no tres— y no contra el criterio firmado, que hoy no
se cumple (punto 13 de *Deriva*). Un test que espere tres está probando el acuerdo, no el sistema, y
uno que espere dos fija una deriva que el humano todavía no resolvió: dejá dicho en su docstring cuál
de las dos cosas estás fijando.

Todo contra el fixture ya fijado, `tests/fixtures/portal/price-list-page-2026-08-28.html` y su
`.xlsx`, que tiene los números exactos de la spec: 18 formas, 7 rubros, 8 sin categoría, 100
productos. **Nunca contra el portal en vivo** (`TEST-03`, Blocker). Y ojo con el número de filas de
`category_alias`: son **11**, no 18 — un test que espere 18 está probando el documento, no el
sistema.

**Para el Code-Reviewer** — Por dónde empezar, y qué convención está en juego en cada lugar:

- **`GEN-02` / `GEN-03`, primero.** La tentación de esta feature es que `catalog` importe
  `triage.models` para leer las reglas en vez de proyectarlas. Hoy no lo hace: el único cruce es
  `identity.dependencies`. `grep -rnE "^from app\.modules\." backend/app/modules/catalog backend/app/modules/triage`
  y que todo resultado sea del propio módulo o un `dependencies`.
- **`GEN-08` / `GEN-09`, por los dos eventos nuevos.** `UnknownCategoryObserved` y
  `QuarantineRuleRedecided` están en `shared/events/catalog.py`, en pasado, `frozen`, con
  identificadores y no entidades. Ningún handler de `catalog/handlers.py` atrapa su excepción, y si
  aparece un `try/except` alrededor de `learn_category_alias` o `repoint_category_alias` es Blocker.
  **Pero el camino silencioso ya está adentro, no alrededor**, y es donde hay que mirar: los `return`
  tempranos de `learn_category_alias` (`catalog/service.py:884-888`) y de `repoint_category_alias`
  (`:916-918`), y los dos `if` sin `else` de `catalog/handlers.py:130` y `:168-169`. En los cuatro el
  caso ya quedó `RESOLVED` y commiteado (`triage/service.py:164-184`): el trabajo desaparece sin
  excepción y sin fila en `operations.exception`, que es exactamente lo que el Artículo II prohíbe.
  Es el punto 12 de *Deriva* y la fila sin mitigar de *Riesgos*.
- **`GEN-05`, por el rebote.** `forget_category_alias` publica `UnknownCategoryObserved` desde dentro
  del handler de `QuarantineRuleRevoked`. Verificá que la cadena termina en `triage.open_case`, que no
  publica nada. Si alguien agrega un `publish` ahí, hay ciclo.
- **`PY-09`, en las siete rutas de `catalog` y la nueva de `triage`.** Las cuatro escrituras de
  `/categories` piden `PRODUCT_CATEGORIES, WRITE`; las tres lecturas, `get_current_user`. Y mirá la
  fila `Section.PRODUCT_CATEGORIES` de `permissions.py:86` contra
  `tests/unit/identity/test_permissions.py:34`: la matriz es la autorización, no las rutas.
- **`DB-01`, en la `0010`.** Modelos y tablas sincronizados, siembra incluida. Dos cosas que la
  migración hace y conviene ver con los ojos abiertos: **también crea `core.stock_point` y
  `staging.price_row.stock`, que son de la 009 y no de esta feature**; y el `_key()` de la migración
  duplica a propósito `collapse_written_form` en lugar de importarla, porque una migración es un
  registro histórico y tiene que seguir significando lo mismo si esa función cambia.
- **`ERR-04`**, en `catalog/service.py` y `triage/service.py`: los errores son de dominio
  (`ConflictError`, `NotFoundError`), no `HTTPException`. Está bien hoy.
- **Dónde mirar último, que es donde está lo flojo**: `frontend/components/triage/CaseCard.tsx` y
  `frontend/lib/triage/types.ts`. Ahí falta la mitad de H4, y no hay ningún test que lo diga.

---

## Deriva contra la spec firmada

Lo que sigue **no es alcance de este plan y no legitima nada**: es la lista de dónde el código y la
`spec.md` firmada no describen el mismo producto. Es material de `/converge`, y qué se corrige —el
código o el acuerdo— **lo decide el humano** (Artículo V). Los cinco primeros están además
desglosados como tareas 21, 22, 24 y 30 en `tasks.md`; del 6 al 13 salieron de esta auditoría y no
tienen todavía tarea.

1. **Ventas no puede hacer nada de lo que H4 y H5 le piden.** Las cinco rutas de `triage` exigen
   `Section.PRICES` en escritura —dueño y compras— y ventas ahí sólo lee. Alcanza a RF-23, RF-24,
   RF-26, RF-28 y RF-30, y RF-28 nombra al rol ventas con todas las letras.
   `backend/app/modules/triage/routes.py:50,69,96,111,125` contra `permissions.py:75`.
2. **La pantalla de equivalencias ofrece lo que el backend rechaza.** Los botones se muestran con
   `canEdit(..., 'PRODUCT_CATEGORIES')`, donde ventas escribe, y pegan contra `triage`, donde no.
   `frontend/components/categories/AliasList.tsx:81-110`.
3. **RF-27 se degrada en silencio para ventas.** `/rubros/equivalencias` pide
   `/triage/rules?kind=unknown_category` para saber quién decidió cada equivalencia; para ventas
   responde 403, `fetchFromApi` devuelve `null` y la lista cae a `rules ?? []`, así que **todas** las
   equivalencias se muestran como «Sembrado en la puesta en marcha», incluidas las aprendidas.
   `frontend/app/(private)/rubros/equivalencias/page.tsx:25,49`.
4. **Un caso de rubro llega a una pantalla que no sabe mostrarlo.** `CaseCard.tsx` tiene rama para
   cuatro kinds y ninguna para `unknown_category`: el caso se dibuja con su `kind` crudo en inglés,
   sin mostrar `category_text` (RF-23) y **sin ningún control para asignarle un rubro** (RF-24).
   `frontend/components/triage/CaseCard.tsx:108-158`, `frontend/lib/triage/types.ts:15-21`.
5. **RF-26 no existe.** Nada cuenta cuántos productos están pendientes de revisión por su categoría:
   `CategoryList` lleva `unclassified_count` y `total_products` y nada más. Es el único de los 31 sin
   implementación **y** sin test. `backend/app/modules/catalog/service.py:699-711`.
6. **RF-20 no tiene camino en la UI.** `PUT /products/{id}/category` acepta un producto ya
   clasificado, pero la única pantalla que llega a esa ruta lista sólo productos con `category_id IS
   NULL`. `backend/app/modules/catalog/repository.py:360-370`.
7. **RF-08 se cumple a medias.** La subcategoría se conserva y se muestra **mientras el producto está
   sin rubro**; una vez clasificado, ninguna pantalla la enseña: ni `PriceRead` ni `PriceHistoryRead`
   la llevan. `backend/app/modules/catalog/schemas.py:63-83`.
8. **`delete_category` rechaza además por formas escritas.** RF-07 sólo habla de productos asignados;
   el servicio rechaza también si el rubro tiene alias, con otro mensaje. Es defendible y no está
   pedido. `backend/app/modules/catalog/service.py:767-775`.
9. **`data-model.md` afirmaba dos cosas que la migración no hace — *corregido en esta pasada*.**
   Decía «18 filas» de `category_alias` —son 11, y el comportamiento es el mismo—, un índice parcial
   sobre `category_id IS NULL` que no existe, y la migración `0003` sobre `0002`. Es un artefacto
   técnico interno, no la spec firmada, así que se corrigió acá mismo en lugar de dejarlo anotado.
   Queda listado para que `/converge` sepa que el número cambió respecto de lo que dice la spec.
10. **Una equivalencia puede nacer sin regla.** `POST /triage/cases/{id}/resolution` con
    `remember: false` publica `QuarantineCaseResolved` con `rule_id=None`, y `catalog` igual crea el
    alias — permanente y con `rule_id` nulo, así que ni `PATCH` ni `DELETE` de `/triage/rules` la
    alcanzan (RF-28, RF-30). La pantalla nunca manda ese flag, así que hoy no ocurre; la puerta está
    abierta igual. `backend/app/modules/triage/service.py:153-161`,
    `backend/app/modules/catalog/service.py:875-906`.
11. **La `0010` trae carga que no es de esta feature.** `core.stock_point` y `staging.price_row.stock`
    son de la 009 y entraron en la misma migración porque las seis specs se construyeron juntas.
    Funciona; una migración que hace dos cosas se lee peor que dos que hacen una.
    `backend/alembic/versions/0010_product_categories.py:119-131,167`.

12. **Una decisión sobre un caso de rubro puede resolverse en silencio y no hacer nada.** Si la
    `decision` nombra un `category_id` que no existe, `learn_category_alias` loguea un `warning` y
    hace `return` (`backend/app/modules/catalog/service.py:884-888`); si al reapuntar falta el alias
    o el rubro, `repoint_category_alias` hace `return` sin log siquiera (`:916-918`); y en
    `backend/app/modules/catalog/handlers.py` el `if category_id is not None and text:` de `:130` y el
    `if category_id is None: return` de `:168-169` no tienen `else`. En los cuatro casos `triage` ya
    puso `case.status = RESOLVED`, publicó y commiteó (`backend/app/modules/triage/service.py:164-184`):
    **el caso sale de la cola, la equivalencia no se crea, ningún producto se clasifica y no queda
    fila en `operations.exception`**. Es el Artículo II al revés, y `decision` es un dict libre desde
    la ruta (`backend/app/modules/triage/schemas.py:47-49`), así que la puerta no depende de un bug
    de otro módulo. Hoy la pantalla no puede llegar acá —no hay control para resolver un caso
    `unknown_category`, punto 4 de esta lista—, lo que lo hace latente, no inexistente.

13. **RF-03 no se cumple como está escrito su criterio de aceptación.** La spec firmada dice «Al
    abrir Pinturas y Adhesivos se ven las **tres** formas escritas que le corresponden»
    (`docs/specs/008-product-categories/spec.md:191`) y se ven **dos**: `PINTURAS Y ADHESIVOS` y
    `Pinturas/Adhesivos`. La causa no es un bug sino la clave de matcheo colapsada: `_seed` saltea la
    grafía repetida (`backend/alembic/versions/0010_product_categories.py:198-206`), así que
    `Pinturas y Adhesivos` en título no tiene fila propia, y la pantalla imprime el `text_original` de
    las filas que hay (`backend/app/modules/catalog/service.py:699-711`,
    `frontend/components/categories/CategoryList.tsx:65`). Lo mismo pasa en los otros seis rubros con
    par de mayúsculas. Qué se corrige —el código, sembrando también las variantes de mayúsculas con su
    propia fila y un índice que las admita, o el acuerdo, que hoy cuenta grafías donde el sistema
    guarda equivalencias— **lo decide el humano** (Artículo V). `spec.md:131,191`.

> **La 010 se firmó, y esta nota cambió de signo.**
> `docs/specs/010-category-ownership/spec.md` quedó **Aprobada el 2026-08-31**: enmienda nueve
> requisitos de esta spec —RF-05, RF-06, RF-07, RF-13, RF-15, RF-20, RF-24, RF-28 y RF-30— y mueve
> los rubros de ventas a compras. Este plan sigue escrito contra la **008 firmada tal como está**, y
> ahí está la diferencia con lo que decía antes: los puntos **1, 2, 3 y 4** de arriba ya no son
> deriva que alguien tenga que decidir, son **el trabajo de la 010**, planificado en
> [`../010-category-ownership/plan.md`](../010-category-ownership/plan.md). Los tres primeros se
> cierran solos con la fila de la matriz; el cuarto —`CaseCard.tsx` sin rama para
> `unknown_category`— es lo único que la 010 construye de cero, y es su RF-14.
>
> Los puntos 5 a 11 **no los toca la 010** y siguen siendo deriva de esta feature.
