# Quién mantiene los rubros — Plan técnico

<!--
  ARTEFACTO INTERNO. Acá van las decisiones técnicas que spec.md no puede llevar.
  No se exporta al cliente.
-->

**Feature:** 010-category-ownership · **Spec aprobada el:** 2026-08-31 · **Fecha:** 2026-08-31
**Roles:** Backend-Architect (la matriz y las rutas) · Frontend-Architect (la pantalla de revisión)

Insumos: `spec.md` firmada (RF-01 a RF-14, dos historias), los diagramas de `diagrams/`, la
`008-product-categories` firmada que esta spec enmienda en nueve requisitos, y el código de
`catalog`, `triage`, `identity` y las tres pantallas de rubros.

> **Este plan sí es un pronóstico, y es el primero de la serie.** Las seis features anteriores se
> construyeron antes de tener plan y sus documentos son actas. Acá la cadena está en orden: la spec
> se firmó el 2026-08-31 y **nada de esta feature está construido todavía**. El Artículo V no
> necesita excepción por primera vez desde la 003.

## Constitution Check

| Artículo | Cumple | Cómo |
|---|---|---|
| I — El origen es ajeno y de sólo lectura | Sí | La feature no toca SIGProv: no hay extracción, ni parser, ni sección nueva del portal. Mueve quién decide sobre datos que ya están de este lado |
| II — Nada se descarta | Sí, y **lo mejora** | Hoy una forma escrita de categoría que nadie decidió abre un caso en `operations.exception` (`triage/handlers.py:119-139`) que **llega a una pantalla que no sabe dibujarlo**: `CaseCard.tsx` no tiene rama para `unknown_category`. El caso existe, se cuenta y no se puede resolver. RF-14 cierra eso, que es el Artículo II en su último tramo — apartar sin poder decidir es apartar a un pozo |
| III — Flujo unidireccional, `raw` inmutable | Sí | No hay ingesta en esta feature. Nada escribe en `raw` ni en `staging` |
| IV — Las fronteras entre módulos son reales | Sí | Cero imports nuevos. El único cruce sigue siendo `identity.dependencies`, la excepción fijada por nombre de archivo en `tests/architecture/test_module_boundaries.py`. Los rubros siguen en `catalog`, la cola sigue en `triage`, y se siguen hablando por `QuarantineCaseResolved`, `QuarantineRuleRevoked` y `QuarantineRuleRedecided` |
| **V — Spec primero, y con firma** | **Sí, y en orden** | `spec.md` en `Aprobado`, firmada por Leandro Carriego — FDE el 2026-08-31, **antes** de que exista una línea de código de esta feature y antes de este documento. Es la primera de las siete que no arrastra la inversión |
| VI — Lo que no está tipado y testeado no está terminado | **Pendiente, y es trabajo de esta feature** | La matriz tiene su test exhaustivo (`tests/unit/identity/test_permissions.py:34`) y hay que editarlo a propósito, que es como tiene que ser. Lo que **falta y hay que escribir** está en *Contexto de traspaso → Para el Tester*: hoy no existe ni un test que haga una request real como ventas contra `/categories` y espere 403 |
| VII — Las credenciales de terceros viven sólo en el entorno | Sí | Ninguna credencial entra en el alcance |
| VIII — Un idioma para cada audiencia | Sí | Los textos nuevos de la rama `unknown_category` van en español, como el resto de la pantalla. La etiqueta que hoy falta en `CASE_KINDS` (`frontend/lib/triage/types.ts:15-21`) hace que un caso de rubro se dibuje con su `kind` crudo en inglés: eso también se corrige acá |
| IX — Las dependencias entran por la puerta | Sí | Cero dependencias nuevas, backend y frontend |

**Excepciones solicitadas:** ninguna a la constitución.

**Una decisión de alcance, sí, y aprobada por el humano.** Esta feature agrega tres líneas que ningún
RF de la 010 pide —el `CATEGORY_SECTION`— para no romper RF-19 de la **003**, que sí está firmada. El
plan se frenó, lo preguntó y no lo resolvió por su cuenta; la decisión es del 2026-08-31 y está
registrada en *Lo que esta feature destapa, y qué decidió el humano*.

## Enfoque

**Casi toda la feature es una fila de una tabla.** La matriz de permisos es la fuente única de quién
llega a dónde (`backend/app/modules/identity/permissions.py:74-98`), y hoy dice:

```python
Section.PRODUCT_CATEGORIES: {_OWNER: Level.WRITE, _PURCHASING: Level.NONE, _SALES: Level.WRITE},
```

Lo que la spec firma es esa fila con los dos roles cambiados de lugar:

```python
Section.PRODUCT_CATEGORIES: {_OWNER: Level.WRITE, _PURCHASING: Level.WRITE, _SALES: Level.READ},
```

De ahí salen solos **RF-01 a RF-05, RF-09, RF-10, RF-11 y RF-12**, y salen solos porque el resto del
sistema ya lee la matriz en vez de repetirla:

- **El menú** (RF-09, y la mitad de RF-12) se dibuja filtrando `ENTRIES` por `canSee(permissions,
  section)` (`frontend/components/auth/Navigation.tsx:17-35`). La entrada «Rubros» ya declara
  `PRODUCT_CATEGORIES`: con la fila nueva le aparece a Marcela y le sigue apareciendo a Julián.
- **Los botones** (RF-12) están detrás de `canEdit(permissions, 'PRODUCT_CATEGORIES')` en las tres
  pantallas —`rubros/page.tsx:50`, `rubros/sin-clasificar/page.tsx:50`,
  `rubros/equivalencias/page.tsx:49`—. Con `READ`, Julián deja de verlos sin que ninguna pantalla
  aprenda qué es un rol.
- **El rechazo** (RF-11) lo hace `require_section(Section.PRODUCT_CATEGORIES, Level.WRITE)` en las
  cuatro rutas de escritura de `catalog` (`routes.py:190, 202, 217, 227`). Esconder el botón nunca
  fue el mecanismo; el 403 ya está declarado y pasa a decir lo que la spec quiere.

**La otra mitad ya era de compras, y nadie lo había notado.** RF-06, RF-07, RF-08 y RF-14 —asignar
una forma escrita a un rubro, repuntarla, dejarla sin efecto, y verla donde se resuelve lo apartado—
se ejecutan contra `triage`, y las cinco rutas de `triage` piden `Section.PRICES` en escritura
(`triage/routes.py:50, 69, 96, 111, 125`), que es dueño y compras. Es decir: **la 010 no mueve
nada ahí; hace que el resto coincida con lo que ahí ya pasaba.** Los tres primeros hallazgos de la
*Deriva* de la 008 —ventas no puede hacer lo que H4 y H5 le piden, la pantalla de equivalencias
ofrece lo que el backend rechaza, RF-27 se degrada en silencio para ventas— desaparecen sin que se
escriba una línea para ellos: eran el síntoma de esta spec faltando.

**Queda un hueco real, y es RF-14.** `CaseCard.tsx` tiene rama para cuatro `kind` y ninguna para
`unknown_category` (`frontend/components/triage/CaseCard.tsx:108-158`). Hoy un caso de rubro llega a
`/revision`, se dibuja con su `kind` en inglés, no muestra `category_text` y **no ofrece ningún
control para asignarle un rubro**. RF-14 pide exactamente que ese caso se resuelva ahí, así que esta
feature construye esa rama: mostrar la forma escrita que llegó, un selector con los rubros de
`GET /categories`, y un `POST /triage/cases/{id}/resolution` con `{"category_id": N}` y
`remember: true`. El backend de eso está entero y probado (`catalog/handlers.py:90-139`,
`catalog/service.py:882-913`): lo único que falta es la mitad que se ve.

**Las rutas de lectura pasan a declarar su nivel.** Las tres de `/categories` piden hoy
`Depends(get_current_user)` —cualquier sesión autenticada— y no `require_section`
(`catalog/routes.py:157, 169, 180`). Con la matriz nueva los tres roles tienen `READ` o más, así que
declarar `require_section(Section.PRODUCT_CATEGORIES, Level.READ)` **no cambia el comportamiento de
nadie** y convierte RF-10 en una declaración verificable en vez de un permiso por omisión. Es lo que
pide `PY-09`, y es lo que hace que el test que recorre las rutas pueda afirmar algo sobre ellas.

**Y hay una consecuencia que la matriz sola no arregla.** Mover los rubros a compras deja a Marcela
sin ver en el historial los cambios que ella misma hace, porque un cambio de rubro se publica como un
hecho de **ventas**. No lo pide ningún RF de esta spec y rompe uno de la 003, así que este plan se
frenó y preguntó: la salida elegida —un `CATEGORY_SECTION` propio para los rubros— está abajo, en
*Lo que esta feature destapa, y qué decidió el humano*, con lo que se descartó y por qué.

## Módulos afectados

| Módulo | Qué cambia | Nuevo |
|---|---|---|
| `identity` | **Una fila de `MATRIX`** (`permissions.py:86`) y el comentario-guía de arriba, que hoy atribuye los rubros a ventas | No |
| `catalog` | Las tres rutas de lectura de `/categories` pasan de `get_current_user` a `require_section(PRODUCT_CATEGORIES, READ)`; los docstrings de las cinco rutas de escritura dicen «el dueño y compras» donde decían «el dueño y ventas»; el comentario de bloque `# --- The rubros of the catalog (008) ---` (`routes.py:145-150`) deja de afirmar que escribir es de ventas; y **un `CATEGORY_SECTION = BusinessSection.PURCHASING`** que usa sólo `_record_category_change` (`service.py:978-999`), por la decisión de abajo | No |
| `triage` | **Nada.** Sus cinco rutas ya son de dueño y compras, y el `kind` `unknown_category` ya existe. Se verifica y se deja quieto | No |
| `shared` | **Sólo el docstring de `sections.py`**: `BusinessSection` deja de significar «el área del dato» para significar «el área de quien decide», y esa es la única explicación que el archivo tiene | No |
| Frontend | La rama `unknown_category` de `components/triage/CaseCard.tsx`, su etiqueta en `lib/triage/types.ts:15-21`, y el texto de las tres pantallas de rubros donde hable de quién mantiene. El menú y los botones **no se tocan**: ya leen la matriz | No |

**Ningún módulo nuevo, ninguna tabla nueva, ningún evento nuevo.** Es la señal de que la spec dice la
verdad cuando dice que corrige el acuerdo y no agrega funcionalidad.

## Eventos de dominio

**Ninguno nuevo, y ninguno modificado.** El circuito de una forma escrita nueva ya viaja entero por
el catálogo compartido, y esta feature lo deja intacto:

| Evento | Lo publica | Lo consume | Qué lleva |
|---|---|---|---|
| `UnknownCategoryObserved` | `catalog` (`service.py:349-362`) | `triage` (`handlers.py:118-139`) | Las formas escritas que la lista trajo y nadie decidió |
| `QuarantineCaseResolved` | `triage` (`service.py:171-183`) | `catalog` (`handlers.py:90-139`) | Con `kind="unknown_category"`: la decisión, y `catalog` aprende la equivalencia y la aplica retroactivamente |
| `QuarantineRuleRedecided` | `triage` (`service.py`) | `catalog` (`repoint_category_alias`) | La equivalencia apunta a otro rubro (RF-07) |
| `QuarantineRuleRevoked` | `triage` (`service.py:201-209`) | `catalog` (`forget_category_alias`) | La equivalencia se deja sin efecto y sus productos vuelven a la cola (RF-08) |

Lo notable es lo que **no** hace falta: mover un permiso no es un hecho del negocio que otro módulo
necesite escuchar. La matriz es una constante que se lee en cada request, no un estado que se
propague.

## Datos

**No hay `data-model.md` para esta feature, y es una decisión, no un olvido.** No se crea ninguna
tabla, no se agrega ninguna columna y no se escribe ninguna migración: `DB-01` no tiene nada que
verificar acá. Las tres tablas que la feature toca —`core.category`, `core.category_alias`,
`operations.exception`— quedan como las dejó la 008, y su modelo está documentado en
[`../008-product-categories/data-model.md`](../008-product-categories/data-model.md).

Lo único que cambia de forma persistente es **quién aparece** en las columnas de autoría que ya
existen: `category.created_by_user_id`, `category_alias.created_by_user_id`,
`exception.decided_by_user_id`. A partir de esta feature son de Marcela y no de Julián, y ninguna de
las tres necesita migración para eso.

## Contratos

Ocho rutas que ya existen. **Ninguna se agrega, ninguna se borra**; cambia lo que cada una declara.

| Método · ruta | Autorización hoy | Autorización después | RF |
|---|---|---|---|
| `GET /categories` | `get_current_user` | `require_section(PRODUCT_CATEGORIES, READ)` | RF-10 |
| `GET /categories/unclassified` | `get_current_user` | `require_section(PRODUCT_CATEGORIES, READ)` | RF-10, RF-13 |
| `GET /categories/aliases` | `get_current_user` | `require_section(PRODUCT_CATEGORIES, READ)` | RF-10 |
| `POST /categories` | `require_section(PRODUCT_CATEGORIES, WRITE)` | **igual** | RF-01, RF-11 |
| `PATCH /categories/{id}` | `require_section(PRODUCT_CATEGORIES, WRITE)` | **igual** | RF-02, RF-11 |
| `DELETE /categories/{id}` | `require_section(PRODUCT_CATEGORIES, WRITE)` | **igual** | RF-03, RF-11 |
| `PUT /products/{id}/category` | `require_section(PRODUCT_CATEGORIES, WRITE)` | **igual** | RF-04, RF-05, RF-11, RF-13 |
| `GET`/`POST`/`PATCH`/`DELETE` de `/triage/*` | `require_section(PRICES, WRITE)` | **igual** | RF-06, RF-07, RF-08, RF-14 |

**Las cinco escrituras no cambian una letra y sin embargo cambian de dueño.** Eso es exactamente lo
que se busca de una matriz: la ruta declara qué necesita, y quién lo tiene se decide en un solo
lugar. Si esta feature exigiera tocar las rutas, la matriz no estaría haciendo su trabajo.

`GET /categories/aliases` merece una nota: la pantalla que la usa pide además
`/triage/rules?kind=unknown_category` para saber quién decidió cada equivalencia
(`rubros/equivalencias/page.tsx:25`). Hasta hoy, para ventas eso devolvía 403 y la lista caía a
`rules ?? []`, con lo que **todas** las equivalencias se mostraban como «Sembrado en la puesta en
marcha» (deriva 3 de la 008). Después de esta feature el que pierde ese dato es ventas y ya no le
corresponde tenerlo, y el que lo necesita —compras— lo obtiene. El degradado silencioso sigue ahí y
sigue siendo feo: está en *Riesgos*.

## Alternativas descartadas

- **Darle a compras una sección propia, `PURCHASE_CATEGORIES`.** Serían dos secciones sobre la misma
  tabla y la misma pantalla, y la primera pregunta sería cuál gana. La sección es «los rubros», no
  «los rubros de compras»: lo que cambió es quién entra, no qué hay adentro.
- **Dejar a ventas en `WRITE` y esconder los botones.** Es lo que la spec prohíbe con todas las
  letras —*«esconder el botón no alcanza»*— y es lo que 002 ya había decidido: el rechazo lo hace el
  backend. Además dejaría RF-11 sin implementación posible.
- **Sacarle a ventas también la lectura (`NONE`).** Es la alternativa que el supuesto de la spec pone
  sobre la mesa para que el cliente la descarte al firmar, y la descartó: Julián vende desde ese
  catálogo y necesita saber en qué rubro cae cada producto. `READ` es el mismo trato que ya tiene con
  los precios de lista y con el calendario.
- **Una pantalla de rubros aparte para compras.** La spec la nombra y la descarta: sería una pantalla
  más, con la misma cola partida en dos. Una sola cola con un solo dueño es la regla de negocio.
- **Mover los rubros de `catalog` a un módulo propio.** El rubro es una columna de `core.product` y
  las equivalencias se aplican al normalizar la lista de precios: separarlo obligaría a `catalog` a
  leer al otro en cada corrida. Quien compra decide el rubro; el rubro sigue viviendo con el producto.
- **Convertir `MATRIX` en una tabla configurable.** Ya estaba descartado en la 002 y sigue estándolo:
  la spec fija tres roles y ninguna pantalla para inventar otros. Una fila mal editada abre una
  sección; una constante tipada y revisada, no.

## Riesgos

| Riesgo | Impacto | Cómo se mitiga |
|---|---|---|
| **La matriz es un solo punto, y toca las tres pantallas de rubros a la vez.** Un error en esa fila abre o cierra tres pantallas de golpe, y el frontend no tiene forma de notarlo: hace lo que la matriz diga | Alto, y de detección tardía | El test que recorre **todo** el producto de roles por secciones (`tests/unit/identity/test_permissions.py`) hay que editarlo a propósito para que pase: es el mismo mecanismo que hace imposible agregar una sección sin decidir sus tres permisos. Sumar el test de comportamiento que hoy no existe (403 real de ventas contra `POST /categories`) es lo que cierra el riesgo |
| **Marcela no vería en el historial los cambios que ella misma haga sobre los rubros.** Un cambio de rubro se publica con `section=BusinessSection.SALES` (`catalog/service.py:189, 989`) y `ROLE_SECTIONS` le da a compras sólo `PURCHASING` (`identity/dependencies.py:53-54`) | Medio, y **rompería RF-19 de la 003** | **Resuelto el 2026-08-31** con un `CATEGORY_SECTION` propio. El riesgo que queda es de comprensión y no de comportamiento: `BusinessSection` pasa a tener dos lecturas, y si el docstring de `shared/sections.py` no se corrige, la excepción queda sin motivo escrito. Ver *Lo que esta feature destapa* |
| **`GET /triage/rules` degradado en silencio.** `fetchFromApi` devuelve `null` ante un 403 y la pantalla cae a `rules ?? []` sin decir que le faltó un dato. Después de esta feature le pasa a ventas en vez de a compras | Bajo hoy —ventas ya no necesita ese dato— y peligroso como patrón | No lo arregla esta feature. Queda anotado para que el próximo `403` que caiga en un `?? []` no se dé por bueno |
| **La rama `unknown_category` de `CaseCard` es la primera que necesita cargar datos de otro dominio** para dibujarse: el selector de rubros sale de `GET /categories`, y `CaseCard` es un componente de `triage` | Bajo | Los rubros los pasa la pantalla (`/revision/page.tsx`) como prop, igual que `AliasList` recibe `categories`. El componente no fetchea; la página compone |
| **Cero cobertura de comportamiento sobre los permisos de rubros.** Hoy RF-10, RF-11 y RF-12 quedarían «probados por construcción» | Medio | Es lo primero de la lista del Tester, abajo |

## Lo que esta feature destapa, y qué decidió el humano

**Un cambio de rubro se registra como un hecho de ventas, y después de esta spec lo hace compras.**

El mecanismo: `_record_category_change` publica `ManualChangeRecorded` con
`section=CATALOG_SECTION`, que es `BusinessSection.SALES` (`catalog/service.py:189, 978-999`). El
historial le muestra a un rol distinto del dueño únicamente los cambios de las secciones a las que
tiene acceso, que es **RF-19 de la 003 firmada**, y la traducción rol → secciones vive en
`identity/dependencies.py:53-54`, donde compras sólo alcanza `PURCHASING`.

Consecuencia exacta a partir de esta feature: Marcela agrega un rubro, y ese cambio **no aparece en
su historial**; aparece en el de Julián, que ya no puede hacerlo. RF-19 de la 003 deja de ser verdad
para los rubros.

**Ningún requisito de la 010 habla del historial**, y la spec dice explícitamente que corrige el
acuerdo sin agregar funcionalidad. Así que este plan se frenó y preguntó, en vez de resolverlo por su
cuenta — que es lo que manda `agents/skills/plan.md`.

### La decisión

**Tomada el 2026-08-31 por Leandro Carriego — FDE.** Se implementa un
`CATEGORY_SECTION = BusinessSection.PURCHASING`, usado **sólo** por `_record_category_change`, y los
precios y los productos siguen publicándose con `CATALOG_SECTION = BusinessSection.SALES`.

Se descartaron, y por qué:

- **Agregar `SALES` a lo que lee compras** en `ROLE_SECTIONS` (`identity/dependencies.py:53-54`).
  Resolvía el caso de los rubros y le abría a Marcela el historial entero de ventas, que nadie pidió y
  que la 002 le había cerrado a propósito.
- **Dejarlo como está** y aceptar que los cambios de rubro los vean sólo el dueño y ventas. Era
  defendible —el rubro sigue siendo un dato del catálogo— pero deja RF-19 de la 003 falsa para los
  rubros y sin nada escrito que lo advierta.

**Por qué esto no es ampliar el alcance, y conviene que quede dicho.** RF-19 de la 003 —*«mostrar a
los roles distintos de dueño únicamente los cambios manuales de las secciones a las que tienen
acceso»*— está firmada y hoy es verdad. Mover los rubros a compras la vuelve falsa **para los
rubros**. Estas tres líneas no agregan una capacidad: mantienen viva una promesa ya firmada que esta
feature, sin ellas, rompería. Es la diferencia entre construir algo nuevo y no romper algo viejo.

**Lo que sí cuesta, y hay que escribirlo.** `BusinessSection` deja de significar «el área del dato»
para significar «el área de quien decide», y eso contradice el docstring de `shared/sections.py`, que
hoy dice *«what part of the business a fact belongs to»*. **La corrección de ese docstring es parte de
esta tarea**, no un detalle: es la única explicación que el archivo tiene, y una excepción sin motivo
escrito es la que alguien «limpia» seis meses después.

**Al cliente no hay que volver a pedirle nada**, porque no cambia lo que el sistema hace ni quién
puede hacerlo: cambia dónde aparece un registro que ya existía. Si aun así se quiere que la 010 lo
diga con todas las letras en su documento firmado, eso es `/clarify` y una firma nueva, y **no es lo
que se decidió acá**.

## Mapa de requisitos

Los 14 firmados, y de dónde va a salir cada uno. **`nuevo`** marca lo único que hay que construir de
cero.

| RF | Dónde vive |
|---|---|
| RF-01 | `POST /categories` (`catalog/routes.py:187-198`) + la fila de `MATRIX` |
| RF-02 | `PATCH /categories/{id}` (`routes.py:200-212`) + la fila |
| RF-03 | `DELETE /categories/{id}` (`routes.py:214-223`) + la fila. El rechazo con motivo cuando el rubro tiene productos ya existe (`catalog/service.py:767-781`) |
| RF-04 | `PUT /products/{id}/category` (`routes.py:225-244`) + la fila |
| RF-05 | La misma ruta que RF-04: confirmar, corregir y reclasificar son la misma llamada |
| RF-06 | `POST /triage/cases/{id}/resolution` → `QuarantineCaseResolved` → `catalog.learn_category_alias` (`service.py:882-913`). **Ya es de compras**; le faltaba la pantalla, que es RF-14 |
| RF-07 | `PATCH /triage/rules/{id}` → `QuarantineRuleRedecided` → `repoint_category_alias` (`service.py:915-934`) |
| RF-08 | `DELETE /triage/rules/{id}` → `QuarantineRuleRevoked` → `forget_category_alias` (`service.py:936-950`) |
| RF-09 | `Navigation.tsx:20`, filtrado por `canSee`. Sale de la fila de `MATRIX` |
| RF-10 | Las tres `GET` de `/categories`, con `require_section(PRODUCT_CATEGORIES, READ)` declarado |
| RF-11 | `require_section(..., WRITE)` en las cuatro escrituras de `catalog`, más las cinco de `triage` |
| RF-12 | `canEdit(permissions, 'PRODUCT_CATEGORIES')` en las tres pantallas de rubros. Sale de la fila |
| RF-13 | `GET /categories/unclassified`, que ya devuelve cada producto con su propuesta, y `PUT /products/{id}/category` para confirmarla o corregirla |
| RF-14 | **nuevo** — la rama `unknown_category` de `CaseCard.tsx` y su etiqueta en `lib/triage/types.ts`. El backend está entero |

**Nueve requisitos de la 008 quedan enmendados** —RF-05, RF-06, RF-07, RF-13, RF-15, RF-20, RF-24,
RF-28 y RF-30 de aquella spec—, y la tabla de correspondencia está en `spec.md`. El
`plan.md` de la 008 está escrito contra la 008 firmada tal como está y **su nota final quedó vieja
el día que se firmó ésta**: los hallazgos 1, 2, 3 y 4 de su *Deriva* dejan de ser deriva y pasan a
ser el trabajo de esta feature.

## Contexto de traspaso

**Para el Developer** — Empezá por la fila de la matriz y **parás ahí a correr los tests**: es el
cambio más chico del repositorio con el radio de acción más grande, y lo que se rompa se rompe
enseguida. `tests/unit/identity/test_permissions.py:34` tiene la fila duplicada a propósito para
que editar la matriz obligue a editar la expectativa; no la generes desde `MATRIX`, que es
exactamente lo que ese test existe para no hacer.

Lo que **no** hay que tocar, porque ya es lo que la spec quiere:

- **Las cinco rutas de `triage`.** Piden `Section.PRICES` en escritura y eso ya es dueño y compras.
  Se ve como una incoherencia —«¿qué hace la cola de revisión colgada de precios?»— y no lo es: la
  sección `PRICES` es la que 002 le dio a quien resuelve lo que la actualización aparta. Cambiarla
  «para que quede prolijo» le saca la cola a compras y rompe RF-14.
- **`Navigation.tsx` y los tres `canEdit`.** Ya leen la matriz. Si te dan ganas de agregar un
  `if role === ...` en una pantalla, la fila está mal.
- **El backend de RF-06, RF-07 y RF-08.** Está construido y probado en la 008. Lo único que falta es
  la mitad que se ve.

Lo que sí hay que construir es **una sola cosa**: la rama `unknown_category` de `CaseCard.tsx`. El
caso trae `payload["category_text"]` (`triage/handlers.py:132`) y espera una decisión con forma
`{"category_id": N}` (`triage/schemas.py:83`). Los rubros se los pasa la página como prop —el
componente no fetchea—, y el flag `remember` va en `true`, que es lo que convierte la decisión en
equivalencia y dispara la retroactividad de RF-25 de la 008.

Y hay **una segunda cosa** que construir, chica y fácil de olvidar: el `CATEGORY_SECTION` de *Lo que
esta feature destapa*, aprobado por el humano el 2026-08-31. Son tres líneas en `catalog/service.py`
y un docstring en `shared/sections.py`, y sin ellas Marcela deja de ver en el historial los cambios
que ella misma hace.

**Para el Tester** — Lo que puede romperse de verdad, en orden:

1. **El 403 de ventas, de verdad.** Hoy **no existe ningún test que haga una request como ventas
   contra `/categories` y espere 403**: RF-11 y RF-12 estarían probados por construcción, que es la
   misma trampa que el plan de la 006 anotó para el calendario. Un test por cada una de las cuatro
   escrituras de `catalog`, y uno que verifique que las tres lecturas siguen devolviendo 200 para los
   tres roles (RF-10).
2. **Que la matriz no haya abierto de más.** El test exhaustivo cubre el producto entero de roles por
   secciones, pero el que hay que mirar a mano es `PRODUCT_CATALOG`: sigue siendo `SALES: WRITE` y
   `PURCHASING: NONE`, porque el catálogo **no** se mueve. Si alguien «acompañó» el cambio moviendo
   también esa fila, rompió el alcance sin que nada se ponga rojo.
3. **El circuito completo de una forma escrita nueva, desde la pantalla.** Llega una categoría que
   nadie conoce → aparece caso en `/revision` → Marcela le asigna un rubro → la equivalencia queda
   guardada → los productos que estaban esperando esa forma quedan clasificados. Hoy los tests de la
   008 llaman al **servicio** y saltean la pantalla (`test_deciding_classifies_what_was_already_set_aside`),
   que es justamente el tramo que faltaba: RF-24 y RF-25 de la 008 están verdes por la razón
   equivocada.
4. **El caso `unknown_category` como lo ve compras.** Que muestre `category_text`, que ofrezca los
   rubros existentes, y que después de resolverlo el caso salga de la cola.
5. **Lo que se rompe sin ruido:** que Julián siga viendo el conteo y las formas escritas (RF-10). Es
   fácil que, al declarar `require_section` en las tres lecturas, alguien ponga `WRITE` por simetría
   con las escrituras y le cierre la pantalla a ventas sin que ningún test lo note.

Nada de esto necesita el portal ni HTML fijado: la feature **no extrae nada**. Si un test de rubros
pide un fixture del portal, está probando otra cosa.

**Para el Code-Reviewer** — Cinco lugares, en este orden:

1. **`identity/permissions.py:86` y el comentario-guía de `:56-73`.** El comentario nombra los RF de
   la 002 que justifican cada fila y hoy dice que las pantallas de rubros son de ventas. Un cambio de
   permiso que no actualice ese comentario deja la única explicación del archivo mintiendo.
2. **`catalog/routes.py:145-244`.** El bloque `# --- The rubros of the catalog (008) ---` afirma
   *«Reading is for the three roles, writing is sales alone»*. Ahí y en los cinco docstrings de ruta
   está todo lo que hay que reescribir; `GEN-07` y `PY-09` son las convenciones en juego.
3. **`components/triage/CaseCard.tsx`.** Que la rama nueva no fetchee, que el texto esté en español
   (`VIII`), y que `CASE_KINDS` tenga su entrada: un `kind` sin etiqueta se dibuja crudo, en inglés,
   en una pantalla que lee una persona.
4. **`catalog/service.py:189` y el docstring de `shared/sections.py`.** El `CATEGORY_SECTION` nuevo es
   la única cosa de este changeset que no sale de un RF de la 010: la aprobó el humano el 2026-08-31
   para no romper RF-19 de la 003, y está registrada en *Lo que esta feature destapa*. Verificá que lo
   usa **sólo** `_record_category_change` —los precios y los productos siguen en `CATALOG_SECTION`— y
   que el docstring de `sections.py` explica por qué hay dos.
5. **Que no haya aparecido más alcance que ése.** Esta feature no crea tablas, no crea eventos, no
   crea rutas y no escribe migraciones. Un `alembic/versions/0014_*.py` en el changeset es una señal de
   que se amplió el alcance, y hay que preguntar por qué antes de leerlo.
