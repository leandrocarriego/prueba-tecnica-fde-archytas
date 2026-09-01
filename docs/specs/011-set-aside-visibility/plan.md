# Lo apartado se ve — Plan técnico

<!--
  ARTEFACTO INTERNO. Acá van las decisiones técnicas que spec.md no puede llevar.
  No se exporta al cliente.
-->

**Feature:** 011-set-aside-visibility · **Spec aprobada el:** 2026-08-31 · **Fecha:** 2026-08-31

**Rol:** Backend-Architect **y** Frontend-Architect. La feature toca las dos puntas: el backend
tiene que abrir los casos que hoy no abre y saber de qué área es cada uno; el frontend tiene que
mostrar el filtro por área, la antigüedad y lo demorado en la pantalla «Revisar esto» que ya existe.

## Constitution Check

| Artículo | Cumple | Cómo |
|---|---|---|
| I — El origen es ajeno y de sólo lectura | Sí | No se agrega ninguna escritura al portal. Todo lo que esta feature hace es leer lo que ya está en `staging` y mostrarlo. Está además en *Fuera de alcance* de la spec |
| II — Nada se descarta | Sí | **Es exactamente el artículo que esta feature termina de cumplir.** Hoy hay cuatro orígenes que apartan a `staging` y no le avisan a nadie; después de esto, apartar y abrir caso son la misma acción en los siete |
| III — Flujo unidireccional, `raw` inmutable | Sí | No se toca `raw` ni se corrige hacia atrás. Los casos se abren desde eventos publicados en la transformación `raw` → `staging`, en el sentido que ya corre |
| IV — Las fronteras entre módulos son reales | Sí | Ningún import nuevo entre módulos. `ingestion` publica tres eventos nuevos de cuarentena, `triage` se suscribe; el cierre automático (RF-20) es otro evento, publicado por `purchases` y `sales`, que `triage` consume sin saber quién lo emitió. La única frontera que se cruza es `identity.dependencies`, la excepción ya fijada por el test |
| V — Spec primero, y con firma | Sí | `spec.md` está en `Estado: Aprobado`, firmada por Leandro Carriego (FDE) el 2026-08-31 |
| VI — Lo que no está tipado y testeado no está terminado | Sí | Tipos completos; unitarios de la antigüedad y del *fingerprint* por área; de integración de la ruta con sus tres roles; de parsers con HTML fijado — los cinco orígenes rotos que pide H1 salen de los fixtures que ya existen |
| VII — Las credenciales de terceros viven sólo en el entorno | Sí | La feature no toca credenciales. Cuidado sí en el `excerpt`: es un pedazo de HTML del portal y se muestra tal cual, pero es contenido de una página ya autenticada, nunca la credencial |
| VIII — Un idioma para cada audiencia | Sí | Código en inglés, `reason` y las etiquetas de la pantalla en español, como ya lo hace la cola |
| IX — Las dependencias entran por la puerta | Sí | Ninguna biblioteca nueva |

**Excepciones solicitadas:** ninguna.

## Enfoque

La cola de revisión ya existe, es genérica y aguanta esto sin cambiar de forma: un `kind`, un
`payload` libre, un `fingerprint` que agrupa y un contador de apariciones. La feature **no construye
una cola nueva**: le enchufa los cuatro orígenes que le faltan y le agrega las tres cosas que la spec
pide y hoy no tiene — de qué área es cada caso, cuánto hace que espera, y que se cierre solo cuando
el trabajo se hizo en otra pantalla.

**Lo que falta enchufar son cuatro, no cinco.** El relevamiento de la spec dice que las órdenes de
compra no llegan a la pantalla; el código sí las abre desde la 007
(`triage/handlers.py::open_unreadable_order_rows`). RF-04 ya está cumplido y esta feature sólo lo
verifica con un test. Los cuatro que faltan de verdad: **proveedores** y **pagos**, que se apartan a
`staging` en `normalize_supplier_ledger` sin publicar ningún evento de cuarentena; **mensajes**, que
se apartan en `normalize_messages` y tampoco lo publican; y **ventas**, que sí publican
`SaleRowsQuarantined` desde la 009 y **nadie escucha**. Así que `ingestion` gana tres eventos nuevos
—`SupplierRowsQuarantined`, `PaymentRowsQuarantined`, `MessageRowsQuarantined`— con la misma forma
que los cuatro que ya publica (`tuple[QuarantinedRow, ...]`, mismo helper `_quarantined_of`), y
`triage` gana cuatro suscripciones nuevas del mismo molde que las dos de la 004 y la 007: se ve el
recorte, se da por revisado, y no se aprende una regla — aprenderla está fuera de alcance.

El caso de **ventas** merece su párrafo porque es el único donde hay una decisión que revertir. La
009 dejó escrito, con todas las letras, que `SaleRowsQuarantined` no tiene suscriptor **a propósito**:
la venta rota ya tiene superficie humana en la pantalla de revisión de ventas, y abrir además un caso
mostraría el mismo registro en dos pantallas de dos personas distintas. La spec 011 decide otra cosa
y decide bien: la lista tiene que ser una sola (RF-06), y el argumento de la 009 —que dos pantallas
digan lo mismo— es justamente lo que RF-20 resuelve. Se abre el caso, y cuando la venta se corrige o
se resuelve en la pantalla de ventas, el caso **se cierra solo**. El comentario de
`ingestion/service.py` que explica la decisión vieja se reescribe: dejarlo sería dejar el código
explicando por qué no hace lo que ahora hace.

**El área de cada caso** se guarda en la fila, no se deduce al leer. `operations.exception` gana una
columna `section: BusinessSection` que el handler completa al abrir el caso, porque quién publicó es
lo único que sabe de qué área es y en el momento de leer ya no está. Con eso, RF-12, RF-13, RF-14 y
RF-22 son un filtro: la ruta deja de pedir `Section.PRICES` —que hoy le cierra la pantalla a Julián,
el dueño del quinto origen nuevo, las ventas— y pasa a exigir sesión, mientras el servicio
filtra por `visible_sections(user)`, el traductor de rol a áreas que `identity.dependencies` ya
expone y que `operations` ya usa para el historial. Resolver un caso de un área que no se ve es un
403, decidido en el servicio con el mismo conjunto.

**La puerta también se abre.** Abrir la ruta no alcanza si nadie de compras ve el link:
`components/auth/Navigation.tsx` declara hoy `{ href: '/revision', section: 'PRICES' }`, y
`lib/operations/actions.ts` repite esa sección en la acción manual `resolve-triage-case`. Las dos
**dejan de declarar sección**, que es el patrón que ese mismo archivo ya documenta para `/acciones` y
`/historial`: cualquier sesión alcanza la puerta y la pantalla recorta lo que *muestra* por
`visible_sections`, en vez de cerrarla. No se agrega una `Section.TRIAGE` —sería alcance nuevo:
catálogo de identity, matriz de roles y migración de permisos, para una pantalla que ya sabe
recortarse sola—, y menos se la mueve a una sección de compras, que resolvería a Marcela dejando
afuera a Julián.

**La antigüedad** no es una columna: es `created_at`, que ya está, leída contra un parámetro nuevo
`triage.stale_days` del catálogo de `app/shared/parameters.py` (entero, inicial 7, RF-19), que el
dueño mueve desde la pantalla de parámetros que ya existe (RF-18) sin migración ni pantalla nueva.
`CaseRead` gana `waiting_days` y `is_stale` calculados, y `CaseList` gana `oldest_at` y el total de
pendientes que RF-15 pide.

**El cierre automático** (RF-20, RF-21) es un evento y no una llamada: `purchases` y `sales` no
pueden tocar `triage`. Se agrega `QuarantinedSourceResolved(kind, key, resolved_where)` al catálogo
compartido; lo publica quien resuelve —`purchases` cuando un pago retenido se imputa o se reparte,
`sales` cuando el grupo de una venta se resuelve o la venta se corrige— y `triage` lo consume,
recalcula el mismo `fingerprint` y cierra el caso pendiente que coincida, si lo hay, dejando
`decision = {"action": "resolved_elsewhere", "where": …}` y sin nombre de persona: la constancia de
quién hizo el trabajo la tiene la pantalla donde se hizo, que es lo que la spec decidió. Si no hay
caso, no pasa nada: un evento que no encuentra nada que cerrar no es un error.

**La vuelta atrás** (RF-24, agregado el 2026-08-31) es el espejo exacto de lo anterior y existe
porque la regla firmada vale en las dos direcciones: `sales.undo_resolution` devuelve una venta a su
cola —la 009 lo prometió en su RF-35— y hasta acá el caso que se había cerrado solo se quedaba
cerrado, o sea que la lista decía que no había nada que revisar sobre un registro que estaba otra vez
en revisión. Se agrega `QuarantinedSourceReopened(kind, key, reopened_where)`, evento aparte y no un
flag del anterior: cerrar y reabrir son dos hechos, y un suscriptor al que sólo le importa uno no
tendría que leer el otro para enterarse.

Lo que hay que cuidar es **a cuál caso se reabre**, y es la única sutileza del cambio: la búsqueda
pide `status = RESOLVED`, `resolved_by_user_id IS NULL` y `decision->>'action' = 'resolved_elsewhere'`.
Un caso que cerró una persona lleva su nombre y su decisión (RF-08), y reabrirlo porque otro registro
coincidió en el `fingerprint` borraría las dos.

Nada se borra (RF-23): la cola ya conserva los resueltos y la única razón por la que no se ven es el
filtro `status` de la ruta, que ya acepta `RESOLVED`.

## Módulos afectados

| Módulo | Qué cambia | Nuevo |
|---|---|---|
| `ingestion` | Publica `SupplierRowsQuarantined`, `PaymentRowsQuarantined` y `MessageRowsQuarantined` desde `normalize_supplier_ledger` y `normalize_messages`, con el helper `_quarantined_of` que ya usa. Se reescribe el comentario de `normalize_sales` que justificaba no tener suscriptor | No |
| `triage` | Cuatro suscripciones nuevas (proveedores, pagos, mensajes, ventas) más las del cierre automático y su reapertura; `origin` y `read_at` en las seis `kind` que ya existían y no los traían (RF-11); columna `section` en `ExceptionCase`; filtro por áreas visibles en `list_cases`; chequeo de área en `resolve`; antigüedad y demora en los schemas; la ruta cambia de autorización | No |
| `purchases` | Publica `QuarantinedSourceResolved` cuando un pago retenido deja de estarlo (`impute_held_payments_for`, `split_payment`) | No |
| `sales` | Publica `QuarantinedSourceResolved` en `resolve_group` y `correct_sale`, y `QuarantinedSourceReopened` en `undo_resolution` (RF-24) | No |
| `shared` | Cinco eventos nuevos en `events/catalog.py` —los cuatro del plan original más `QuarantinedSourceReopened`—; el parámetro `triage.stale_days` en `parameters.py` | No |
| `frontend` | `/revision`: filtro por área, columna «espera hace», marca de demorado, total de pendientes, y las cuatro `kind` nuevas en `CASE_KINDS`. La entrada del nav y la acción manual dejan de declarar `section`; el bloque de reglas se pide sólo si quien mira alcanza `PRICES` | No |

Ningún módulo nuevo: no aparece ninguna capacidad del negocio con lenguaje propio. Es la cola que ya
existe, alcanzando lo que ya debía alcanzar.

## Eventos de dominio

| Evento | Lo publica | Lo consume | Qué lleva |
|---|---|---|---|
| `SupplierRowsQuarantined` | `ingestion` | `triage` | `raw_document_id`, `cases: tuple[QuarantinedRow, ...]` |
| `PaymentRowsQuarantined` | `ingestion` | `triage` | `batch_id`, `raw_document_id`, `cases: tuple[QuarantinedRow, ...]` |
| `MessageRowsQuarantined` | `ingestion` | `triage` | `batch_id`, `raw_document_id`, `cases: tuple[QuarantinedRow, ...]` |
| `SaleRowsQuarantined` *(ya existe)* | `ingestion` | `triage` **(nuevo suscriptor)** | `batch_id`, `cases` |
| `PurchaseOrderRowsQuarantined` *(ya existe y ya se consume)* | `ingestion` | `triage` | — |
| `QuarantinedSourceResolved` | `purchases`, `sales` | `triage` | `kind: str`, `key: str`, `resolved_where: str` — identificadores y una etiqueta, nunca la entidad |
| `QuarantinedSourceReopened` | `sales` | `triage` | `kind: str`, `key: str`, `reopened_where: str`. **Agregado el 2026-08-31 con RF-24**: la regla firmada vale en las dos direcciones, y la pantalla de ventas deja deshacer una resolución (RF-35 de la 009). Es un evento aparte y no un flag del anterior porque cerrar y reabrir son dos hechos, no uno con dirección |

Los tres primeros son en pasado, inmutables y llevan identificadores (`GEN-08`), y viajan dentro de
la transacción del publicador: si abrir el caso falla, la normalización falla con él, que es
precisamente lo que el Artículo II pide y `GEN-09` verifica.

**Ningún ciclo** (`GEN-05`): `ingestion` → `triage` y `purchases`/`sales` → `triage` son flechas de
ida; `triage` no publica nada que esos tres consuman como consecuencia de esto.

## Datos

- **`operations.exception.section`** — `Enum(BusinessSection)`, no nulo. Migración con backfill por
  `kind`. Los `kind` existentes son **siete**, y son los que abre `triage/handlers.py`; el mapa los
  enumera a todos y no deja ninguno al default:

  | `kind` existente | `section` |
  |---|---|
  | `unreadable_row` | `PURCHASING` |
  | `unknown_product` | `PURCHASING` |
  | `missing_product` | `PURCHASING` |
  | `unreadable_history` | `PURCHASING` |
  | `unreadable_invoice_row` | `PURCHASING` |
  | `unreadable_order_row` | `PURCHASING` |
  | `unknown_category` | `PURCHASING` |

  **Corregido por el Lead el 2026-08-31.** Los cuatro primeros decían `SALES`, y era un error
  heredado de la tabla de actores de la spec, enmendada el mismo día: la cola de precios es de
  **Marcela**. Lo dice `PROJECT_BRIEF.md` con las palabras del cliente —sobre los precios de lista
  «sí puede … resolver lo que el sistema haya apartado»—, lo implementa la matriz
  (`Section.PRICES` es `WRITE` para compras y `READ` para ventas) y lo fija `test_permissions.py`,
  que rompe el build. Es además lo que manda `shared/sections.py` cuando las dos lecturas de
  `BusinessSection` divergen: **gana quién decide**, no de qué habla el dato.

  Con eso los siete quedan en `PURCHASING`, que es correcto y no es sospechoso: los siete `kind`
  que existían antes de esta feature son de la ingesta del portal, y resolver lo que la ingesta
  aparta es trabajo de compras. El primer `kind` de ventas lo trae esta feature
  (`unreadable_sale_row`), y no necesita backfill porque nunca abrió un caso.

  `unknown_category` va a compras porque la 010 puso los rubros de ese lado y
  `catalog/service.py::CATEGORY_SECTION` ya lo dice así — se lee de ahí, no se reinventa. **No hay un `kind` `unknown_sale_row`**: las ventas apartadas no
  abrían caso, que es justamente lo que esta feature agrega, así que no hay nada histórico que
  backfillear por ese lado. Cualquier `kind` que apareciera fuera de esta lista es un error de la
  migración y el test lo tiene que hacer fallar, no absorberlo con un default. Índice
  `ix_exception_section_status` para el listado filtrado, que es la consulta de la pantalla.
- **`operations.parameter`** — sin cambios de esquema: `triage.stale_days` es una fila más, con su
  `ParameterSpec` en el catálogo (entero, inicial 7, mínimo 1, máximo 365, `consumed_by="triage"`).

- **`operations.triage_setting`** — tabla nueva (migración `0019`). **Corrección al plan, hecha
  durante la implementación y confirmada por el `/converge`.** La frase de arriba —«leída contra un
  parámetro del catálogo de `shared/parameters.py`»— no se podía cumplir: `triage` no puede leer las
  tablas de `operations` (Artículo IV), así que el valor le llega por `BusinessParameterChanged` y
  vive en su propia proyección, del mismo molde que la que `sales` ya mantiene. El catálogo sigue
  siendo la declaración; esto es la copia que este módulo lee.

- **`core.payment.staging_row_id`** — columna nueva (migración `0020`). También corrección al plan:
  sin ella `purchases` no tiene con qué clave anunciar que un comprobante dejó de esperar, y el
  cierre automático de RF-20 no tendría cómo emparejar el caso.
- **`kind` nuevos**: `unreadable_supplier_row`, `unreadable_payment_row`, `unreadable_message_row`,
  `unreadable_sale_row`. Strings, como los siete que ya hay.
- **El `payload` de los cuatro nuevos** lleva lo que RF-09, RF-10 y RF-11 piden leer:
  `staging_row_id`, `excerpt`, `origin` —la pantalla del portal de la que salió, como string del
  handler: `"padrón de proveedores"`, `"comprobantes de pago"`, `"buzón"`, `"ventas"`— y `read_at`,
  que sale del `occurred_at` que todo `DomainEvent` ya trae. El `reason` va en su columna, como siempre.

`DB-01`: la migración se genera con Alembic y `alembic check` tiene que quedar limpio.

## Contratos

| Ruta | Autorización | Cambio |
|---|---|---|
| `GET /triage/cases` | **Sesión válida** (`CurrentUser`), y el servicio filtra por `visible_sections(user)` | Deja de exigir `Section.PRICES, WRITE`, que dejaba afuera a compras. Nuevo query param `section: BusinessSection \| None` (RF-22), validado contra las áreas visibles |
| `POST /triage/cases/{id}/resolution` | **Sesión válida**, y el servicio rechaza con 403 si `case.section` no está en `visible_sections(user)` (RF-13) | La comprobación pasa de la ruta al servicio porque depende del **caso**, no de la ruta |
| `GET /triage/rules` | sin cambios — `require_section(Section.PRICES, Level.WRITE)` | — |
| `DELETE`/`PATCH /triage/rules/{id}` | sin cambios | — |

**Sobre las reglas aprendidas.** Las tres rutas de `/triage/rules` **no se abren**, y la decisión es
deliberada (2026-08-31): toda regla aprendida es de precios —los cuatro `kind` nuevos van con
`remember=False` porque aprender está fuera de alcance—, así que las reglas siguen siendo de Julián y
abrir la ruta sólo agregaría una superficie más por donde filtrar un área. Lo que sí cambia es la
pantalla: hoy `app/(private)/revision/page.tsx` pide `/triage/rules` en el mismo `Promise.all` que
los casos, y para Marcela eso pasa a ser un 403 que el `rules ?? []` esconde. La página condiciona
ese fetch a que quien mira alcance `PRICES`, y el bloque de reglas no se renderiza para quien no la
alcanza. Un 403 amortiguado por accidente no es un comportamiento: es uno que nadie testea.

**Sobre `PY-09`.** La convención pide que toda ruta declare su autorización, y estas dos la siguen
declarando: lo que cambia es que la declaración es «hay que estar identificado» y el permiso fino lo
resuelve el servicio, porque el área es un dato de la fila y una `Depends` no la conoce todavía. Es
la misma forma que ya tiene el historial de `operations`. Si el test de `PY-09` exige una
`require_section()` literal, se ajusta el test **a propósito y en el mismo commit**, nunca
debilitándolo: la ruta sigue sin ser pública.

`CaseRead` gana `section`, `waiting_days: int` y `is_stale: bool`. `CaseList` gana `oldest_at:
datetime | None`, `pending_total: int` y `sections: list[BusinessSection]` — esta última no estaba
en el plan y se agregó al implementar: es lo que deja a la pantalla dibujar el filtro de RF-22 **sin
guardar una segunda copia de la matriz de roles en el browser**, que sería una regla en dos lugares,
o sea una regla y un bug. Los tipos del frontend se regeneran del OpenAPI, no se
escriben a mano.

## Alternativas descartadas

- **Una cola por área.** Lo descartó la spec y por la razón cara: lo que hizo que nadie mirara el
  buzón del portal no fue que fuera largo, fue que era otro lugar más.
- **Deducir el área del `kind` al leer, en vez de guardarla.** Un `dict[kind, section]` en el
  servicio evitaba la migración, y pone la respuesta lejos de quien la sabe: el día que un `kind`
  cambie de dueño —que ya pasó con los rubros en la 010— la cola muestra el caso a la persona
  equivocada y nada falla. La columna la escribe quien publica, que es quien sabe.
- **Llamar a `TriageService` desde `purchases` para cerrar el caso.** Es un import entre módulos:
  Artículo IV, y el test lo frena.
- **Un `CaseStatus.RESOLVED_ELSEWHERE`.** Tentador, y parte en dos todas las consultas que hoy
  preguntan `status == RESOLVED` —incluido el índice parcial del `fingerprint`— para distinguir algo
  que RF-21 pide *registrar*, no *contar aparte*. Queda en el `decision`, que es el campo donde ya
  vive el qué se decidió.
- **Un job que marque los demorados.** Un `UPDATE` nocturno para calcular una resta entre dos fechas
  es un estado derivado que puede quedar viejo; se calcula al leer.
- **Aprender una regla de las decisiones nuevas.** Fuera de alcance por la spec. `remember=False` en
  los cuatro `kind` nuevos, y la razón escrita en el handler.

## Riesgos

| Riesgo | Impacto | Cómo se mitiga |
|---|---|---|
| La cola se inunda el primer día: cuatro orígenes que nunca abrieron un caso van a abrir todo lo que tengan pendiente | **Medido el 2026-08-31: cero.** Era Alto — una lista impracticable se abandona, que es el fracaso exacto que la spec quiere evitar | El agrupamiento por `fingerprint` ya existe y es lo que lo hace tolerable: cien filas rotas iguales son un caso con `occurrences=100`. Se mide **contra lo que ya hay apartado en `staging` de producción**, con una consulta de sólo lectura agrupada por el mismo criterio con el que la cola agrupa, antes de shipear; si el número sigue siendo grande es una conversación con el cliente, no un filtro escondido. **Corregido el 2026-08-31:** decía «contra los fixtures», y no sirve — los HTML fijados se capturaron un día bueno y sólo el de ventas trae filas rotas, así que medirían casi cero |
| El backfill de `section` en casos históricos deja alguno del lado equivocado | Medio — un caso viejo invisible para quien debería verlo | El mapeo es por `kind` y los `kind` existentes son siete y conocidos; el test de la migración los enumera |
| Cambiar la autorización de `/triage/cases` le abre a Julián casos que hoy no ve | Alto si el filtro falla — es exactamente RF-12 | El filtro por `visible_sections` va en el servicio, con test de integración por rol: Julián no ve compras, Marcela no ve precios, el dueño ve todo. `test_rbac.py` es donde vive esa prueba |
| El cierre automático cierra un caso que no correspondía, por un `fingerprint` que coincide de más | Medio — un pendiente desaparece sin que nadie lo resuelva | La clave del cierre es la misma que abrió el caso (`staging_row_id` para pagos y ventas), no una reconstrucción libre. Un test por cada publicador |

## Contexto de traspaso

**Para el Developer** — Empezá por `ingestion/service.py`: los tres eventos nuevos son quince líneas
cada uno y el helper `_quarantined_of` ya hace el trabajo. Seguí por `triage/handlers.py`, donde las
cuatro suscripciones nuevas se copian de `open_unreadable_order_rows` casi tal cual. **No construyas
una cola nueva ni una pantalla nueva**: la spec dice explícitamente que se usa la que existe. **No
agregues aprendizaje de reglas** en los `kind` nuevos: está fuera de alcance y `remember=True` es el
default, así que hay que pasarlo en `False` a propósito. Tres decisiones están tomadas y no se
rediscuten: la lista es una sola, el cierre es automático y no manual, y lo resuelto se conserva para
siempre. La cuarta, que es de este plan: el área se **guarda** en la fila, no se deduce al leer.
Cuando reescribas el comentario de `normalize_sales`, decí por qué la decisión de la 009 se revirtió
— el próximo que lo lea va a buscar esa explicación.

**Para el Tester** — Lo que puede romperse de verdad es el filtro por área: es RF-12 y RF-13, y
fallar ahí muestra plata de compras a quien no la maneja. Probalo por rol en `test_rbac.py`, en las
dos rutas, y probá también el 403 al resolver. Lo segundo es la avalancha: un fixture con cien filas
rotas iguales tiene que dar **un** caso con `occurrences=100`, no cien. Lo tercero es el cierre
automático: abrí el caso de un pago retenido, imputalo desde su pantalla, y verificá que el caso
quedó `RESOLVED` con `resolved_elsewhere` y **sin nombre de persona**; y que el evento que no
encuentra caso no rompe nada. Los cinco orígenes de H1 se prueban con el HTML fijado que ya está en
`tests/fixtures/portal/` — nunca contra el portal en vivo (`TEST-03`). Casos borde de la demora: seis
días no está demorado, ocho sí, y el límite se mueve cambiando el parámetro, no el código.

**Para el Frontend-Developer** — Dos cosas se rompen en silencio si te las salteás, porque no dan
error: que la entrada del nav y la acción manual sigan declarando `section: 'PRICES'` —y entonces
Marcela tenga permiso sobre cuatro orígenes y ninguna puerta por donde entrar—, y que la página siga
pidiendo `/triage/rules` sin condición, que para ella es un 403 que `rules ?? []` disfraza de lista
vacía.

**Para el Code-Reviewer** — Las convenciones en juego son `GEN-02` y `GEN-03` (que el cierre
automático no se haya resuelto con un import), `GEN-08` y `GEN-09` (que los eventos nuevos lleven
identificadores y que un handler que falla aborte la transacción del publicador), `PY-09` (la
autorización de las dos rutas que cambian: si el test se tocó, tiene que estar justificado en el
mismo commit y la ruta seguir cerrada) y `DB-01` (`alembic check` limpio, con el backfill de
`section`). Mirá primero `triage/routes.py` y `triage/service.py::list_cases` y `resolve`: ahí está
todo lo que puede filtrar datos de un área a quien no le corresponde. Después, el comentario de
`normalize_sales`: si sigue diciendo que nadie escucha `SaleRowsQuarantined`, el código quedó
mintiendo. Y del lado del frontend, dos líneas concretas: que `Navigation.tsx` y
`lib/operations/actions.ts` ya no aten `/revision` a `PRICES`, y que el fetch de `/triage/rules` esté
condicionado. Las dos son RF-06 y RF-12 disfrazadas de detalle de UI.
