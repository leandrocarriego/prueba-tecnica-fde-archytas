# Rubros unificados — Plan técnico

<!--
  ARTEFACTO INTERNO. Acá van las decisiones técnicas que spec.md no puede llevar.
  No se exporta al cliente.
-->

**Feature:** 008-product-categories · **Spec aprobada el:** 2026-08-29 · **Fecha:** 2026-08-29

**Roles:** `Backend-Architect` (el grueso) · `Frontend-Architect` (las tres pantallas).

## Constitution Check

| Artículo | Cumple | Cómo |
|---|---|---|
| I — El origen es ajeno y de sólo lectura | Sí | La feature no toca SIGProv. Consume `category_raw` / `subcategory_raw` que `001` ya extrajo y guardó en `staging`. No agrega navegación ni una sola request al portal. |
| II — Nada se descarta | Sí | **Es el artículo que esta feature encarna.** Una forma escrita desconocida no va a un cajón de "otros": abre un caso en `triage` y espera a una persona. La decisión queda como regla reutilizable, que es la segunda mitad del artículo. Un producto sin categoría tampoco se pierde: «sin rubro» es una categoría visible que entra en los totales. |
| III — Flujo unidireccional, `raw` inmutable | Sí | `raw` no se toca. La clasificación ocurre de `staging` hacia `core`, en un solo sentido, y es reproducible: borrando `core.product.category_id` y volviendo a correr las reglas se reconstruye sin volver a extraer. |
| IV — Las fronteras entre módulos son reales | Sí | `catalog` y `triage` no se importan: hablan por `QuarantineCaseResolved`, `QuarantineRuleRevoked` y el nuevo `QuarantineRuleRedecided`. `catalog` mantiene su propia proyección de las equivalencias en vez de leer la tabla de `triage`, igual que `ingestion` ya hace con `ResolutionRuleProjection`. La única frontera que se cruza es `identity.dependencies`, la excepción fijada por nombre de archivo en el test. |
| V — Spec primero, y con firma | Sí | `spec.md` en `Aprobado`, firmada por Leandro Carriego — FDE el 2026-08-29. Este plan no agrega alcance: los 31 RF tienen lugar y no hay un requisito nuevo. |
| VI — Lo que no está tipado y testeado no está terminado | Sí | Tipos completos. La clasificación es lógica pura y se testea unitariamente contra el fixture ya fijado; los endpoints y las reglas, por integración. Nada se prueba contra el portal en vivo. |
| VII — Las credenciales de terceros viven sólo en el entorno | Sí | La feature no ve credenciales: no hay extracción. |
| VIII — Un idioma para cada audiencia | Sí | Código y eventos en inglés; los `reason` de los casos y los textos de las tres pantallas, en español. |
| IX — Las dependencias entran por la puerta | Sí | **Cero dependencias nuevas**, back y front. Todo sale de lo que ya está instalado. |

**Excepciones solicitadas:** ninguna.

## Enfoque

La feature se apoya en dos piezas que **ya existen y fueron construidas para esto**, y por eso
casi no agrega maquinaria nueva.

La primera es `staging`. `001` ya guarda `category_raw` y `subcategory_raw` de cada fila, con un
comentario en el modelo que dice literalmente que unificarlas es P7. El dato está desde el día
uno: lo que falta es que **viaje hasta `catalog`**, porque el evento `PriceListNormalized` no lo
lleva. Se le agregan los dos campos a `NormalizedPriceRow`, con default, y ese es todo el cambio
en `ingestion`.

La segunda es `triage`, que es una cola de excepciones **genérica con reglas aprendidas**, y cuyo
propio código anuncia que "the next problem will add its own" kind. 008 es ese próximo problema.
Una forma escrita que el sistema no conoce abre un caso `unknown_category`; resolverlo crea una
`ResolutionRule` —que es el registro de quién decidió y cuándo, o sea RF-27— y publica
`QuarantineCaseResolved`. Revocarla reabre sus casos sola, que es RF-31 sin escribir una línea.
El `fingerprint` de la cola da gratis que la misma forma escrita no se pregunte cien veces en un
lote de cien productos.

Sobre eso, `catalog` pone lo que es suyo: el **rubro** y la **equivalencia**. El rubro es una
entidad del negocio con nombre propio que el cliente edita (RF-05, RF-06, RF-07). La equivalencia
—forma escrita → rubro— es una proyección local alimentada por los eventos de `triage`, siguiendo
exactamente el precedente de `ingestion.ResolutionRuleProjection`: `catalog` no lee la tabla de
`triage`, escucha sus hechos. Clasificar un lote es entonces un `JOIN` contra esa proyección, no
una llamada a nadie.

**El sistema no adivina en ningún punto.** El matcheo es contra la tabla de equivalencias, no
contra un normalizador ingenioso: `Pinturas/Adhesivos` y `PINTURAS Y ADHESIVOS` no se parecen lo
suficiente como para que ningún algoritmo honesto las una, y por eso las 18 formas medidas entran
**sembradas por migración desde la tabla que el cliente firmó**. La normalización que sí se aplica
es conservadora —recortar, colapsar espacios internos, `casefold`— y sólo colapsa los pares que
difieren únicamente en mayúsculas. Todo lo que no esté en la tabla va a revisión, que es RF-21 y
RF-22.

La propuesta de rubro para un producto sin categoría (RF-14) **no se siembra**: se deriva en el
momento, consultando qué rubro tienen los productos ya clasificados que comparten esa
subcategoría. Es más honesto que una tabla fija —la propuesta refleja el estado real del catálogo,
y mejora sola a medida que se clasifica— y hace verdadera la frase de la spec: el sistema propone
sobre lo que ya está decidido. Si la subcategoría no resuelve a **exactamente un** rubro entre los
clasificados, se trata como no conocida y se cae en RF-17: se presenta sin propuesta. Es la
lectura fiel de "subcategoría conocida" y evita que el sistema desempate por su cuenta.

**La propuesta se calcula y se muestra, nunca se guarda**, y ahí está RF-16 entero: si no hay
columna donde escribirla, no existe el estado "propuesto pero sin confirmar" en el que un producto
podría quedar contando como clasificado sin que nadie lo haya decidido. Hasta que ventas confirma,
el producto tiene `category_id` nulo y es «sin rubro» a todos los efectos: aparece en los cortes,
entra en los totales y sigue en la cola. Confirmar la propuesta y corregirla son **la misma
escritura** —`PUT` con el rubro elegido—, y la única diferencia es qué rubro viaja; el sistema no
tiene por qué distinguirlas, y no lo hace (RF-15).

Cuando la decisión es sobre una **forma escrita** y no sobre un producto suelto, resolver el caso
de `triage` la guarda como regla, `catalog` proyecta la equivalencia y desde ese momento se aplica
sola: eso es RF-24, y es la misma mecánica que RF-25.

### Corregir una equivalencia: RF-28 y RF-29

Es la parte que más se piensa, porque toca una asimetría que no se ve a primera vista: **las 18
equivalencias sembradas no nacen de una decisión humana y por lo tanto no tienen regla en
`triage`**. Si las equivalencias se direccionan por `rule_id`, las 18 de fábrica no se pueden
corregir ni dejar sin efecto — y corregir una sembrada es justamente el caso probable, porque la
siembra sale de una medición y no de que alguien la haya pensado rubro por rubro.

La salida es **hacerlas uniformes**: la migración siembra las 18 como reglas de `triage`
—`kind="unknown_category"`, `matcher={"category_text": …}`, `decision={"category_id": N}`— y
además las 18 filas de `category_alias` que las proyectan. Desde ahí toda equivalencia, sembrada o
aprendida, es una regla con su `rule_id`, y RF-27 a RF-31 se resuelven todos por el mismo camino
sin ninguna rama especial.

Con eso, RF-28 es una capacidad nueva y chica en `triage`: `redecide_rule`, que reapunta la
`decision` de una regla vigente y publica `QuarantineRuleRedecided`. **No es una violación del
"se revoca, nunca se borra"**: no se pierde nada. La regla suma `updated_by_user_id` y
`updated_at`, así que sigue constando quién la creó y cuándo, y pasa a constar además quién la
corrigió. Revocar y recrear, que sería la alternativa purista, está descartada por la spec misma:
revocar manda los productos de vuelta a revisión (RF-31) y RF-29 pide exactamente lo contrario,
que se **reasignen**.

RF-29 es entonces una sola sentencia en `catalog`, cuando le llega el evento: reapuntar el alias y
mover los productos que esa regla había clasificado.

```
UPDATE core.product SET category_id = :nuevo
WHERE classified_by_rule_id = :rule_id
```

El `classified_by_rule_id` es lo que hace que la reasignación sea **exacta**: alcanza a lo que la
equivalencia clasificó y no toca lo que una persona decidió a mano producto por producto, que no
depende de ella y no tiene por qué moverse.

### Y al revocar, RF-31 sin un camino especial

Al revocarse una equivalencia, `catalog` desasigna esos mismos productos y los vuelve a pasar por
**el mismo paso de clasificación que corre en cada lote**: no encuentran equivalencia, y por lo
tanto `catalog` publica `UnknownCategoryObserved`, que es lo que hace que `triage` abra el caso.
Es el mismo código que el flujo normal, no una rama de revocación, y el evento es simétrico del
`UnknownProductsObserved` que `catalog` ya publica hoy.

Eso deja RF-30 y RF-31 funcionando también para las sembradas, que era el otro agujero: revocar la
equivalencia de `Ferreteria Gral.` manda sus once productos a revisión igual que si la hubiera
decidido alguien.

## Módulos afectados

| Módulo | Qué cambia | Nuevo |
|---|---|---|
| `catalog` | Entidades `Category` y `CategoryAlias`; clasificación al aplicar un lote; propuesta por subcategoría; rutas de rubros, sin clasificar y equivalencias | No |
| `triage` | Kind `unknown_category`; `_matcher_of` aprende a matchear por texto de categoría; `redecide_rule` con `updated_by_user_id` / `updated_at`; `created_by_user_id` pasa a nulo | No |
| `ingestion` | `PriceListNormalized` viaja con `category_raw` y `subcategory_raw` | No |
| `identity` | `require_sales()`, simétrico al `require_purchasing()` que ya existe | No |
| `shared/events` | Dos campos en `NormalizedPriceRow` y un evento nuevo | — |
| Frontend | `/rubros`, `/rubros/sin-clasificar`, `/rubros/equivalencias` | — |

**No se crea ningún módulo.** Los rubros son vocabulario del catálogo —producto, precio,
categoría es la definición del módulo en `ARCHITECTURE.md`— y una cola de revisión con reglas
aprendidas ya tiene dueño. Un módulo `categories` sería acumulación de archivos, no una capacidad
del negocio con lenguaje propio.

## Eventos de dominio

| Evento | Lo publica | Lo consume | Qué lleva |
|---|---|---|---|
| `PriceListNormalized` *(modificado)* | `ingestion` | `catalog` | Cada `NormalizedPriceRow` suma `category_raw: str \| None` y `subcategory_raw: str \| None`, con default para no romper a quien ya lo construye |
| `QuarantineCaseResolved` *(existente)* | `triage` | `catalog` | Con `kind="unknown_category"`: `decision={"category_id": N}`, `matcher={"kind", "category_text"}` |
| `QuarantineRuleRevoked` *(existente)* | `triage` | `catalog` | `catalog` desasigna los productos que esa equivalencia resolvía y baja la proyección (RF-31) |
| `QuarantineRuleRedecided` *(nuevo)* | `triage` | `catalog` | `rule_id`, `kind`, `matcher`, `decision` nueva. `catalog` reapunta la equivalencia y reasigna sus productos (RF-28, RF-29) |
| `UnknownCategoryObserved` *(nuevo)* | `catalog` | `triage` | Las formas escritas sin equivalencia y qué productos afectan. Simétrico del `UnknownProductsObserved` que ya existe. Es lo que abre el caso, tanto en un lote normal como después de revocar (RF-21, RF-31) |

No se publica ningún evento sin consumidor (`GEN-08`): `catalog` no anuncia "producto
clasificado" porque hoy nadie escucharía. Cuando P3 necesite ese hecho, lo agrega su plan.

## Datos

Tres cambios en el esquema `core`, con su migración `0003_product_categories` sobre la cabeza
`0002`. Detalle en **`data-model.md`**.

- **`core.category`** — el rubro. `id`, `name` único, `created_at`. RF-01, RF-05, RF-06. RF-07 no
  es un `ON DELETE`: es una verificación explícita en el servicio, porque el sistema tiene que
  poder **decir por qué** no se borra.
- **`core.category_alias`** — la equivalencia. `id`, `category_id`, `text_normalized` único,
  `text_original` (lo que RF-03 y RF-23 muestran), `rule_id` nulo, `source` (`SEED` o `LEARNED`),
  `created_at`. Es la proyección local de las reglas de `triage`.
- **`core.product`** — suma `category_id` nulo, `category_raw`, `subcategory_raw`,
  `classified_by_user_id`, `classified_at` (RF-18) y `classified_by_rule_id`, este último
  siguiendo el precedente de `registered_by_rule_id`: es lo que permite deshacer exactamente lo
  que una equivalencia hizo cuando se la revoca.

La migración **siembra los 7 rubros y las 18 formas escritas de la tabla firmada**, y siembra cada
forma escrita **dos veces**: como regla en `operations.resolution_rule` y como fila en
`core.category_alias` que la proyecta. Sembrar no es que el sistema decida: es cargar el acuerdo.
Sin la siembra, la primera corrida mandaría los 100 productos a revisión, que es exactamente lo
que la spec promete evitar.

Para eso `resolution_rule.created_by_user_id` pasa a ser nulo. Una equivalencia sembrada **no la
decidió nadie**: vino con el sistema, desde una tabla que se firmó. Ponerle el id del dueño sería
más cómodo y sería mentir en un registro de auditoría, que es el único lugar donde una mentira
cómoda no se puede permitir. RF-27 la muestra como lo que es, sembrada en la puesta en marcha.

`category_id` nulo **es** «sin rubro». No hay una fila centinela: un rubro llamado "Sin rubro"
sería borrable, renombrable y contable como los demás, y RF-07 no tendría sentido sobre él. El
corte por rubro lo agrega como grupo al proyectar, que es lo que RF-09 pide.

## Contratos

Rutas nuevas bajo `catalog`. Toda ruta declara su autorización (`PY-09`) y el test de arquitectura
la verifica dos veces, declarada y efectiva.

| Método y ruta | Quién | RF |
|---|---|---|
| `GET /categories` | autenticado | RF-01, RF-03, RF-04 |
| `POST /categories` | ventas | RF-05 |
| `PATCH /categories/{category_id}` | ventas | RF-06 |
| `DELETE /categories/{category_id}` | ventas | RF-07 |
| `GET /categories/unclassified` | autenticado | RF-11, RF-12, RF-14, RF-15, RF-17 |
| `PUT /products/{product_id}/category` | ventas | RF-13, RF-15, RF-18, RF-19, RF-20 |
| `GET /categories/aliases` | autenticado | RF-27 |

Las dos escrituras sobre una equivalencia van contra `triage`, que es donde vive la regla, y no
se duplican en `catalog`:

| Método y ruta | Quién | RF |
|---|---|---|
| `PATCH /triage/rules/{rule_id}` *(nueva)* | ventas | RF-28, RF-29 |
| `DELETE /triage/rules/{rule_id}` *(ya existe)* | ventas | RF-30, RF-31 |

`DELETE` ya está construido y ya revoca: no se toca. La única ruta nueva es el `PATCH`. Como
ahora **toda** equivalencia tiene su regla, las dos alcanzan por igual a las 18 sembradas y a las
aprendidas.

Lectura para los tres roles, escritura sólo ventas: es la regla de negocio de la spec, y coincide
con lo firmado en `002`. `require_sales()` se agrega a `identity.dependencies` por simetría con
`require_purchasing()`; como el dueño entra en todos lados, `require_roles()` ya lo contempla.

**Frontend** — tres pantallas bajo `/rubros`, con Server Actions como el resto: la lista de rubros
con su conteo y sus formas escritas, la cola de sin clasificar con la propuesta y los botones de
confirmar o corregir, y la lista de equivalencias. Se reusan `components/triage/RuleList.tsx` y
`CaseCard.tsx`, que ya resuelven esta forma de pantalla.

## Alternativas descartadas

- **Un módulo `categories` propio.** Partiría en dos el lenguaje del catálogo: el producto
  quedaría en un módulo y su rubro en otro, y clasificar un lote —que hoy es un `JOIN`— pasaría a
  ser un ida y vuelta de eventos dentro de la misma transacción. La frontera estaría mal trazada,
  y la constitución dice que en ese caso se corrige la frontera.
- **La equivalencia como tabla exclusiva de `catalog`, sin regla de `triage`.** Obligaría a
  `catalog` a reabrir casos al revocar, y `catalog` no puede hablarle a `triage` sin un evento
  nuevo. Se terminaría reconstruyendo, peor, lo que `triage` ya hace, y se perdería el registro de
  quién decidió que RF-27 pide.
- **Un normalizador que unifique las formas escritas solo** —quitar acentos, expandir `/` a `y`,
  cortar abreviaturas—. Es el camino corto a violar el Artículo II: acierta con `Herram.` y
  algún día une dos rubros que el negocio distingue, en silencio y sin que nadie lo decida. La
  tabla de equivalencias es explícita y auditable; un normalizador es una opinión escondida.
- **Sembrar también el mapa subcategoría → rubro.** Nace desactualizado. Derivarlo de los
  productos ya clasificados sale de la misma consulta y siempre dice la verdad.
- **Una fila `Sin rubro` en `core.category`.** Ver *Datos*.
- **Búsqueda difusa —`pg_trgm`, distancia de edición— para proponer el rubro de una forma escrita
  nueva.** Es una dependencia y una decisión automática donde la spec puso a una persona, y está
  explícitamente fuera de alcance.

## Riesgos

| Riesgo | Impacto | Cómo se mitiga |
|---|---|---|
| La siembra queda desincronizada de lo que el proveedor manda: aparece una decimonovena forma escrita | Bajo. Es el caso normal, no una falla | Va a revisión y alguien la decide una vez. Es literalmente H4 funcionando |
| El relevamiento dice 19 formas y el archivo medido tiene 18 | Bajo, pero ensucia la verificación | La siembra sale de la tabla firmada, no del relevamiento. `FDE_ASSESSMENT.md:193` quedó desactualizado y es del humano corregirlo |
| Cambiar `NormalizedPriceRow` toca el contrato de `001`, que ya está construido | Medio: puede romper tests de `001` | Los dos campos entran con default. Los tests de `001` que construyen el evento a mano siguen compilando, y hay que correrlos: es el chequeo más barato de esta feature |
| `_matcher_of` de `triage` hoy arma el matcher con `product_code`, y para 008 tiene que armarlo con el texto de la categoría | Alto si se pasa por alto: la equivalencia se aplicaría a un solo producto y RF-25 no andaría | Es el primer test a escribir. Un caso `unknown_category` resuelto tiene que producir un matcher por `category_text`, nunca por producto |
| Sembrar sólo los alias y no las reglas: las 18 equivalencias de fábrica quedan sin `rule_id` y no se pueden ni corregir ni revocar | Alto, y silencioso: no falla nada, simplemente RF-28 y RF-30 no alcanzan a las 18 | Un test que recorra **todas** las equivalencias y verifique que cada una tiene regla vigente. Es la asimetría que ya se coló una vez en este plan |
| `redecide_rule` sobre una regla ya revocada | Medio: reviviría una equivalencia que alguien apagó, sin que nadie lo decida | Rechazar con conflicto si `revoked_at` no es nulo, igual que `revoke_rule` ya rechaza revocar dos veces |
| Al revocar, un producto vuelve a revisión y su `category_id` queda colgado | Medio: los totales de RF-10 dejarían de cerrar | `undo_rule` desasigna por `classified_by_rule_id` y el producto vuelve a «sin rubro», que sigue contando en el total |

## Contexto de traspaso

**Para el Developer** — Empezá por `shared/events/catalog.py`: los dos campos en
`NormalizedPriceRow` y el evento `QuarantineRuleRedecided`. Todo lo demás cuelga de ahí. Después
la migración `0003` con la siembra, después `catalog`, y `triage` al final, que es lo más chico.

Cuatro decisiones **ya tomadas, no las rediscutas**: los rubros van en `catalog` y no en un módulo
nuevo; las equivalencias son reglas de `triage` proyectadas en `catalog`; «sin rubro» es
`category_id IS NULL` y no una fila; y **las 18 sembradas se siembran también como reglas**, para
que no haya dos clases de equivalencia. Lo que **no** tenés que tocar: `portal`, `raw`, y el parser
de `001` —`category_raw` ya se extrae, sólo hay que dejarlo viajar—.

Y lo que no hay que hacer bajo ningún concepto: resolver el matcheo con un normalizador que
adivine. Si una forma escrita no está en la tabla, va a revisión. Esa es la feature.

**Para el Tester** — Lo que puede romperse de verdad es el matcher de `triage`: si sale por
`product_code` en vez de por `category_text`, la equivalencia se aplica a un producto y no a una
forma escrita, y RF-25 falla en silencio mientras todo lo demás parece andar. Es el primer test.

Los casos borde que importan: una subcategoría que apunta a dos rubros entre los clasificados
—tiene que caer en RF-17, sin propuesta, no desempatar—; cien productos del mismo lote con la
misma forma escrita desconocida —un solo caso, no cien, por el `fingerprint`—; revocar una
equivalencia y verificar que los productos vuelven a revisión **y** que la suma de RF-10 sigue
dando el total.

Y los tres de corregir una equivalencia, que es lo más nuevo: que el `PATCH` **reasigne sin pasar
por revisión** —si los productos aparecen en la cola, se confundió RF-29 con RF-31—; que alcance
igual a una **sembrada** que a una aprendida; y que **no** toque los productos que alguien
clasificó a mano, que tienen `classified_by_rule_id` nulo y no dependen de esa equivalencia.

Todo contra el fixture ya fijado, `price-list-2026-08-28.xlsx`, que tiene los números exactos de
la spec: 18 formas, 7 rubros, 8 sin categoría, 100 productos. Nunca contra el portal en vivo
(`TEST-03`, Blocker).

**Para el Code-Reviewer** — Mirá primero `GEN-02` y `GEN-03`: la tentación de esta feature es que
`catalog` importe `triage.models` para leer las reglas en vez de proyectarlas. Si aparece ese
import, el diseño se rompió. Después `GEN-08` y `GEN-09`, por el evento nuevo: en pasado,
inmutable, con identificadores y no entidades, y su handler no puede tragarse una excepción.
`PY-09` en las ocho rutas nuevas, con `require_sales()` en las cuatro de escritura, y `DB-01` en
la migración `0003` —modelos y tablas sincronizados, siembra incluida—.

---

## Lo que la implementación encontró

**Once equivalencias, no dieciocho.** Este plan y `data-model.md` dicen que las 18 grafías firmadas
producen 18 filas en `core.category_alias`, y dos párrafos antes dicen que la clave de matcheo
colapsa los pares que difieren sólo en mayúsculas — que `ELECTRICIDAD` y `Electricidad` **son la
misma clave**. Las dos cosas no pueden ser ciertas a la vez con un índice único sobre la clave.

Gana la regla de normalización, que es la que tiene una razón detrás. Las 18 grafías quedan
cubiertas por **11 equivalencias**:

| Rubro | Grafías firmadas | Filas |
|---|---|---|
| Electricidad | `ELECTRICIDAD` · `Electricidad` | 1 |
| Ferretería General | `FERRETERIA GENERAL` · `Ferreteria General` · `Ferreteria Gral.` | 2 |
| Herramientas | `HERRAMIENTAS` · `Herramientas` · `Herram.` | 2 |
| Instrumental | `INSTRUMENTAL` · `Instrumental` | 1 |
| Pinturas y Adhesivos | `PINTURAS Y ADHESIVOS` · `Pinturas y Adhesivos` · `Pinturas/Adhesivos` | 2 |
| Sanitarios | `SANITARIOS` · `Sanitarios` | 1 |
| Seguridad Industrial | `SEGURIDAD INDUSTRIAL` · `Seguridad Industrial` · `Seg. Industrial` | 2 |

Las que difieren en algo más que mayúsculas —`Ferreteria Gral.`, `Herram.`, `Pinturas/Adhesivos`,
`Seg. Industrial`— siguen siendo filas propias apuntando al mismo rubro, que es exactamente para lo
que existe una tabla de equivalencias.

**Nada del comportamiento cambia**: las 18 formas se resuelven igual, y cada equivalencia tiene su
regla en `triage`, así que RF-28 a RF-31 alcanzan a todas. Lo que cambia es el número que la
documentación afirma. `data-model.md` sigue diciendo 18 y hay que corregirlo — queda anotado acá
porque corregir un documento firmado es del humano.
