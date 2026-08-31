# Control propio del sistema — Modelo de datos

<!-- ARTEFACTO INTERNO. Detalle de lo que plan.md resume. -->

**Feature:** 003-system-control · **Fecha:** 2026-08-29 · **Revisado contra el código:** 2026-08-30

Dos tablas nuevas, una tabla existente que cambia de rol, **una columna sobre dos tablas de `core`
que ya existían**, y un catálogo que deliberadamente **no** es una tabla. Nada de esta feature
escribe en `raw` ni en `staging`.

## `operations.audit_entry` — la bitácora

Una fila por cambio manual, de cualquier módulo, sobre cualquier dato. Es la tabla que contesta
*"quién editó qué, cuándo, qué decía antes y por qué"* (H2).

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `bigint` PK | |
| `entity_type` | `varchar(100)` | Qué clase de dato se tocó, en el vocabulario de quien publicó. Al cerrar esta feature: `catalog.product`, `catalog.product_price`, `operations.parameter`; la lista no es cerrada y cada módulo que agrega una edición manual suma el suyo — hoy ya están además `catalog.product_category` y `purchases.supplier`. Indexado junto a `entity_id`. |
| `entity_id` | `varchar(100)` | El identificador dentro de su módulo. Texto y no `int` porque no toda entidad tiene clave numérica, y no es una precaución sobre el futuro: el cambio de un parámetro (RF-08) escribe acá su clave, `price_update.interval_hours`. |
| `field` | `varchar(100)` NULL | El campo que se tocó. Nulo cuando el cambio no es de un campo de un registro: el del parámetro (RF-08) es de la clave entera, y ahí no hay campo que nombrar. |
| `action` | enum `audit_action` | `CREATED`, `UPDATED`, `CORRECTED`, `CORRECTION_REVERTED`. |
| `old_value` | `jsonb` NULL | Lo que decía antes (RF-10). Nulo cuando antes no había nada que decir. |
| `new_value` | `jsonb` NULL | Lo que dice ahora. Nulo cuando el dato deja de decir algo — hoy sólo la baja de un rubro (008). **La anulación no lo usa**, porque escribe el valor del portal que restituye, que es exactamente lo que el dato pasa a decir (RF-31). |
| `reason_code` | `varchar(50)` NULL | El motivo elegido de la lista (RF-11). |
| `reason_detail` | `text` NULL | El detalle escrito, siempre opcional. |
| `actor_user_id` | `int` | Quién lo hizo (RF-09). Sin FK a `users`: `identity` es otro módulo y una FK entre schemas de módulos distintos es acoplamiento de esquema. Se resuelve por proyección al mostrar. |
| `section` | enum `section` | `PURCHASING`, `SALES`, `SYSTEM`. Es lo que permite el filtro de RF-19. |
| `occurred_at` | `timestamptz` | Indexado. El historial se lee de más nuevo a más viejo (RF-13), pero el índice es ascendente — abajo, por qué. |

**Índices**: `(entity_type, entity_id)` para RF-15, `(occurred_at)` para RF-13,
`(actor_user_id, occurred_at)` para RF-14, `(section)` para RF-19.

**Los dos índices que ordenan por fecha son ascendentes, y no es un descuido.** Un btree se recorre
para atrás al mismo costo que para adelante, así que declararlos `DESC` no le compraría nada a la
consulta que lee de más nuevo a más viejo. Lo que sí costaría es `alembic check`: compara el índice
del modelo contra el de la base, y un `DESC` escrito de un lado y no del otro es una diferencia que
aparece en CI todas las mañanas sin que nadie haya tocado nada.

**Inmutabilidad (RF-16, RF-17).** La migración instala **dos** triggers sobre la misma función,
y los dos hacen falta: uno `BEFORE UPDATE OR DELETE ... FOR EACH ROW`, y otro
`BEFORE TRUNCATE ... FOR EACH STATEMENT`, porque **un trigger de fila no se dispara nunca ante un
`TRUNCATE`** — sin el segundo, una sola sentencia borra el historial entero sin una palabra.
Postgres sólo admite triggers a nivel sentencia sobre `TRUNCATE`, así que son dos y no un evento
más del primero.

No es defensa en profundidad decorativa: el requisito dice *"el sistema debe impedir"*, y un
método que el repositorio no expone sólo impide hasta que alguien lo agregue. El repositorio
expone `insert`, `list`, `count` y `list_for_entity`, y nada más: una escritura y tres lecturas.

**Sin FK a `users`, a propósito.** `identity` es un módulo y `operations` es otro; una FK sería una
dependencia de esquema entre dos módulos que no se conocen. El nombre de quien hizo el cambio se
resuelve en la capa HTTP, con la misma `dependencies.py` que ya cruza la frontera para autorizar.

## `core.correction` — la corrección, en el módulo dueño del dato

Una fila por campo corregido a mano sobre un dato que vino del portal. Vive en `core` porque la
escribe `catalog`; cuando 004 construya facturas, tendrá **su** tabla con la misma forma, dada por el
mixin de `shared/corrections.py`.

| Columna | Tipo | Nota |
|---|---|---|
| `id` | `int` PK | |
| `entity_type` | `varchar(100)` | `catalog.product`, `catalog.product_price`. |
| `entity_id` | `varchar(100)` | |
| `field` | `varchar(100)` | Qué campo se corrigió. `(entity_type, entity_id, field)` es único entre las vigentes. |
| `portal_value` | `jsonb` | **Lo que el portal informó.** No se toca nunca (RF-25). Es lo que se restituye al anular (RF-31). |
| `corrected_value` | `jsonb` | Lo que quedó. |
| `reason_code` | `varchar(50)` | De la lista (RF-11). |
| `reason_detail` | `text` NULL | |
| `corrected_by_user_id` | `int` | |
| `corrected_at` | `timestamptz` | |
| `status` | enum `correction_status` | `ACTIVE`, `CONFLICTED`, `REVERTED`. El tipo se declara **sin schema**, para que el próximo módulo que guarde correcciones lo reuse aunque su tabla viva en otro, en lugar de declarar un gemelo casi igual. |
| `conflict_value` | `jsonb` NULL | Lo que el portal informó después y contradice a la corrección (RF-28). Contra qué se lo compara **no es la misma columna para todos los campos**: ver *Contra qué se mide un conflicto*. |
| `conflict_detected_at` | `timestamptz` NULL | |
| `reverted_by_user_id` | `int` NULL | RF-32. |
| `reverted_at` | `timestamptz` NULL | |

**Índice único parcial** sobre `(entity_type, entity_id, field) WHERE status <> 'REVERTED'`: un dato
tiene a lo sumo una corrección vigente, y las anuladas se conservan porque nada se borra.

**La corrección no se borra al anularla.** Pasa a `REVERTED` con quién y cuándo (RF-32), y el valor
canónico vuelve a `portal_value`. Borrar la fila haría que el historial apuntara a algo inexistente.

## Contra qué se mide un conflicto

`conflict_value` se llena cuando el portal vuelve a informar un dato corregido y lo que trae no es
lo que la corrección da por válido. **«Lo que la corrección da por válido» no es la misma columna
para todos los campos**, y conviene entenderlo antes de leerlo como una inconsistencia: es una
regla sola mirada desde dos columnas distintas.

| Campo corregido | Lo entrante se compara contra | Por qué |
|---|---|---|
| `price` | `portal_value` | Que el portal repita su propio número no es novedad: es lo que viene informando desde antes de que alguien lo corrigiera. Sólo hay contradicción cuando cambia de opinión respecto de lo que él mismo dijo. |
| `currency` | `corrected_value` | El portal **nunca informa una moneda por su cuenta**: informa «1500 pesos», y la unidad viaja pegada al importe en cada fila que publica. Medida contra `portal_value`, una moneda corregida no podría ser contradicha jamás —el proveedor sigue cotizando en la moneda de siempre—, así que cada lista posterior le llevaría la contra a la persona en silencio y el dueño no se enteraría nunca. |
| `description` | `portal_value` | El mismo argumento que el importe: el texto que el portal repite es el suyo, y sólo contradice cuando cambia. Lo distinto no es contra qué se mide sino **dónde se pregunta**: ver abajo. |

La regla, entonces, no es «contra `portal_value`» sino **contra lo último que se sabe que el portal
dijo de ese campo**. Para el importe y para la descripción eso está escrito, y está en
`portal_value`. Para la moneda no existe: el portal nunca la dijo sola, así que el valor que dejó la
persona ocupa ese lugar por ser lo único contra lo que una moneda entrante se puede medir. El
argumento completo vive en el docstring de `CatalogService._check_conflict`, que es donde se aplica.

Tres consecuencias que están en el código y no se deducen del cuadro:

- **La moneda se revisa antes de decidir nada sobre el importe, y aunque el importe no se mueva.**
  Una lista diaria repite el precio de ayer casi todas las mañanas. Si la pregunta se hiciera sólo
  donde se escribe un importe nuevo, la contradicción sobre la moneda se informaría el único día en
  que el número casualmente cambió, y se callaría todos los demás.
- **Sólo el portal contradice una corrección.** La misma escritura la usa una persona resolviendo
  una fila ilegible de la cola de revisión; decirle al dueño que «el portal contradijo una
  corrección» sobre un valor que escribió esta misma plataforma sería un aviso sobre nadie (RF-29).
  De ahí que la comparación esté condicionada a que la escritura entrante venga marcada como del
  portal (`source = PORTAL`) — la misma marca que después queda estampada en la fila, y que es la
  columna de la sección siguiente.
- **La descripción se pregunta en otro lado, porque el campo que el pipeline no pisa es el que se
  quedaría sin preguntar.** El importe y la moneda se comparan donde se escribe el precio; una
  corrida, en cambio, **nunca reescribe la descripción de un producto que ya conoce**, así que ahí
  no hay escritura de la cual colgar la pregunta. La comparación vive entonces en el recorrido de la
  lista, antes de tocar el precio de esa fila. Sin esa línea, el único campo corregible que el portal
  informa y la plataforma no aplica sería también el único que jamás se marcaría: la corrección no se
  pisa —eso ya lo garantiza que nadie la escriba— pero el dueño no se enteraría nunca de que el
  portal empezó a llamar al producto de otra manera.

## Máquina de estados de una corrección

```
                    corrige una persona
   (sin corrección) ────────────────────► ACTIVE
          ▲                                 │  el portal informa algo
          │                                 │  que la corrección niega
          │ anula el dueño                  ▼
          └──────────── REVERTED ◄──── CONFLICTED
                            ▲               │
                            └───────────────┘
                              anula el dueño
```

`CONFLICTED` vuelve a `ACTIVE` si una persona corrige otra vez: el conflicto se cierra donde vive el
dato, no en una bandeja aparte. El diagrama cara al cliente es
[`diagrams/estados-dato.mmd`](diagrams/estados-dato.mmd), que describe lo mismo sin nombrar estados
técnicos.

## `core.product` y `core.product_price` — de dónde vino el valor

Dos tablas que ya existían y que ganan una columna cada una. **No estaba en este documento ni en el
plan cuando se escribieron**: apareció implementando RF-33 —*«no se puede dejar sin efecto una
corrección sobre un dato que no fue traído del portal»*— cuando quedó a la vista que el código no
tenía con qué contestar esa pregunta. Es lo único de esta feature que modifica tablas anteriores, y
lo agrega la migración `0009`.

| Tabla | Columna | Tipo | Qué contesta |
|---|---|---|---|
| `core.product` | `source` | enum `core.price_source`, NOT NULL, `server_default 'PORTAL'` | Si hay una descripción que informó el portal debajo de la que está vigente. **Hoy vale `PORTAL` en todas las filas**: ver abajo. |
| `core.product_price` | `source` | ídem | Si hay un importe que informó el portal debajo del que está vigente. |

**La columna no dice quién escribió el valor vigente, dice si hay uno del portal debajo.** El matiz
decide si un lector futuro le hace la pregunta correcta: después de una corrección el valor vigente
es el de la persona y `source` sigue en `PORTAL` —`apply_correction` escribe el campo corregido y no
toca la bandera—, y es justamente eso lo que hace posible RF-31, devolver lo que el portal había
dicho. El docstring de `CatalogService._came_from_the_portal` lo enuncia con las mismas palabras,
que es donde se aplica.

**Reusa `core.price_source`**, el enum de dos valores —`PORTAL`, `SYSTEM`— que `core.price_point` ya
usaba desde `0002`, en lugar de declarar un segundo gemelo con otro nombre. Por eso `0009` lo declara
con `create_type=False`: el tipo ya está creado y la migración sólo lo referencia.

**Una sola bandera para toda la fila de precio, importe y moneda juntos.** No es que la fila no pueda
mezclar: `_register_price` estampa `source = PORTAL` cuando el que escribe es el pipeline de precios
y aun así conserva la moneda que una persona corrigió —«a unit a person ruled out is not written,
whoever is writing» (RF-28)—, así que un precio del portal con una moneda de la plataforma existe y
es deliberado. La bandera es una sola porque contesta otra cosa: **quién escribió la fila por el
camino del pipeline de precios**. Lo que dice que un campo vigente es de la persona no es `source`,
es la corrección vigente en `core.correction`, que se guarda por campo y es la que la pantalla
muestra al lado del valor.

### Por qué la pregunta se le hace a la fila que tiene el valor, y no al producto

Porque RF-33 habla de **un dato**, no de un producto, y las dos respuestas se separan enseguida.

Está en el código de hoy: cuando alguien resuelve una fila ilegible, el producto queda marcado
`PORTAL` —la descripción salió de la fila que el portal publicó, la persona sólo decidió
conservarla— mientras que el precio queda `SYSTEM` si lo escribió ella. Un solo producto, dos
respuestas distintas. Una bandera colgada del producto tendría que elegir una de las dos y mentir
sobre la otra, justo en el momento en que RF-33 se pregunta si hay un valor del portal debajo del
que se está por anular.

**Con eso dicho, hoy `core.product.source` vale `PORTAL` en todas las filas**, y conviene que el
documento lo diga en lugar de sugerir una distinción que la columna no hace. No es un olvido: la
descripción de un producto siempre sale de la fila que el portal publicó —el único alta a mano que
existe es incorporar un producto desde la cola de revisión, y ahí la persona decide si lo incorpora,
no cómo se llama—, así que `incorporate_product` la marca `PORTAL` a propósito. La columna existe
para que un camino de escritura futuro —un producto que alguien invente entero— pueda decir otra
cosa, no porque hoy distinga. La que sí distingue desde el primer día es la de `core.product_price`,
que es la que RF-33 consulta cuando se anula una corrección sobre un importe.

Con la columna en su lugar, `CatalogService._came_from_the_portal` es una línea: `source is PORTAL`
sobre la fila que se está corrigiendo.

### Por qué no alcanzaba con `registered_by_rule_id`

Era lo que el código usaba antes, y contesta otra pregunta: **qué regla aprendida incorporó un
producto** (RF-37). Un producto que llegó en una lista diaria común tampoco tiene regla, así que esa
columna leía como «cargado a mano» a la enorme mayoría del catálogo — precisamente las filas donde
una corrección más necesita conservar lo que el portal dijo. Fue uno de los defectos más graves que
encontró la suite, y no era un descuido de tipeo: eran dos preguntas parecidas que nadie había
distinguido por escrito. Queda distinguido acá.

### El criterio con que se rellenaron las filas que ya existían

Ambas columnas nacen en `PORTAL`, y el `server_default` alcanza a todo lo que ya estaba. Es la
decisión que más conviene dejar argumentada, porque **la opción prudente es la peligrosa**.

A favor de `PORTAL`: todo producto de esta base llegó en una lista —el catálogo lo sembró una
(RF-02) y después sólo crece por una decisión humana—, así que no es una conjetura para la enorme
mayoría; y `registered_by_rule_id` no sirve para señalar al resto, por lo mismo que lo descalificó
arriba: es nulo tanto para el producto que trajo una lista como para el que alguien incorporó sin
guardar regla.

En contra de `SYSTEM` «por las dudas»: le diría a la plataforma que **ningún** valor del catálogo
fue informado nunca por el portal. Con eso, ninguna corrección conservaría lo que el portal dijo
(RF-25) y la lista siguiente pisaría en silencio todas las correcciones manuales (RF-28). Errar
hacia el lado tímido acá no es ser cuidadoso: es apagar dos requisitos.

Los precios además se acomodan solos dentro del día, porque la lista de mañana estampa cada fila con
la verdad. La escritura en vivo también erra hacia el lado seguro: si una persona acepta una fila de
la cola sin cambiar el precio, la fila queda `SYSTEM` y la plataforma se niega a ofrecer una
reversión que podría haber ofrecido, en lugar de inventar un valor del portal que nadie informó
(Artículo III).

Con una excepción que no es una concesión sino la misma regla leída bien: cuando el que incorpora la
fila es una **regla guardada**, el importe queda `PORTAL`. Una regla no escribe un número —repite la
fila que el portal publicó—, así que lo que incorpora sigue siendo palabra del portal aunque el
producto haya entrado por la cola de revisión. La pregunta nunca fue por qué puerta entró el dato,
sino si hay un valor del portal debajo.

## `operations.parameter` — la tabla existente, con otro rol

No cambia de forma. Cambia de significado: **deja de ser la lista de parámetros y pasa a ser la lista
de valores que el dueño cambió**. Un parámetro que nadie tocó no tiene fila, y su valor sale del
catálogo (RF-04).

Consecuencia sobre lo que ya existe: `list_parameters()` deja de devolver filas y pasa a devolver el
catálogo con los valores vigentes encima; `set_parameters()` valida contra el catálogo antes de
escribir (RF-06) y rechaza una clave desconocida. `get_parameter_value()` cae al valor inicial del
catálogo en lugar de devolver `None` con un warning, que es lo que hacía.

`description` sigue existiendo y `set_parameters()` le escribe la `label` del catálogo, para que una
sesión de `psql` lea la misma frase que el dueño. **Nadie la lee de vuelta**: la fuente sigue siendo
el catálogo, y esta columna es una cortesía para quien mire la tabla, no una segunda declaración.

**Cambiar de significado obliga a limpiar lo que sembró el significado anterior**, y eso lo hace la
migración `0008`. Cuando una fila era la única forma de que un parámetro existiera, `0003` sembró
tres —el tiempo de sesión, el límite de intentos fallidos y el bloqueo—, y las escribió en **dos**
tablas: `operations.parameter`, que es la que lee el panel, y `access_settings`, que es la
proyección propia de `identity`. Las tres se borran, y sólo si todavía tienen el valor que `0003`
escribió: un valor que alguien eligió es una decisión, y una migración no está para revocarla. Dos
de las tres claves ni siquiera están en el catálogo —siguen viviendo como constantes de `identity`,
porque no se ofrecen en el panel—; la tercera sí está, y es la que hace que borrar de las dos tablas
no sea prolijidad sino corrección. Está contado en *Migraciones*.

## `app/shared/parameters.py` — el catálogo, que no es una tabla

```python
@dataclass(frozen=True, slots=True)
class ParameterSpec:
    key: str
    label: str                       # español: lo que el dueño lee
    effect: str                      # español: qué cambia si se lo modifica (RF-05)
    kind: ParameterKind              # INTEGER | DECIMAL | TIME_OF_DAY
    initial: Any
    minimum: Any | None = None       # sin mínimo ni máximo: una hora del día
    maximum: Any | None = None
    unit: str | None = None
    consumed_by: str = ""            # qué funcionalidad lo lee; vacío mientras no exista

    # Derivados, y por eso no son campos:
    #   has_effect      -> si hoy alguien lo lee, que es lo que la pantalla señala
    #   stored_initial  -> el inicial en la forma en que lo llevan JSONB y la API
    #   range_text      -> la frase del rango, en español
    #   coerce(value)   -> el valor a guardar, o la excepción que dice por qué no
```

Congelado, en una tupla, con tests que verifican que las claves son únicas, que cada valor inicial
cae dentro de su propio rango, que todo parámetro numérico declara sus dos extremos y que ninguno se
queda sin la etiqueta y la frase que el dueño lee. Está en `shared/` por la misma razón que el
catálogo de eventos: es vocabulario compartido y **ningún módulo es su dueño**. Que sea una lista
cerrada es también lo que impide que una credencial entre como parámetro por API (Artículo VII).

**`coerce()` y `range_text` viven en el mismo objeto a propósito.** RF-06 pide rechazar el valor *y*
decir entre qué límites tiene que estar; si el mensaje se escribiera en otro lado, el día que un
límite se mueva la frase seguiría diciendo el anterior. Por lo mismo, `stored_initial` no repite el
valor inicial en formato de base: lo hace pasar por el mismo `coerce()` que atravesaría un `PUT` con
ese valor, y así los dos caminos no pueden discrepar. Un `Decimal` viaja a JSONB como texto para no
convertirse en `float` a la ida y perder los centavos a la vuelta.

**`consumed_by` no es documentación, se ve en la pantalla.** De los siete parámetros que declara esta
feature, **tres** tienen quién los lea al cerrarla —el intervalo y el umbral de la actualización de
precios, y el tiempo de sesión, que `identity` obedece desde 002— y **cuatro** esperan a la feature
que los use; la pantalla lo dice en lugar de ofrecer una perilla que no mueve nada.

La cuenta se mueve sola, y por eso vive en el `ParameterSpec` y no en este párrafo: cada feature que
se construye le pone consumidor a alguno de los que esperaban y declara los suyos, así que el
catálogo de hoy es más largo que estos siete y la pantalla se entera sin que nadie edite un
documento. Lo que este documento fija es de dónde sale la respuesta, no cuál es esta semana.

**El tiempo de sesión conserva su clave anterior, `access.session_idle_minutes`.** No es un nombre
elegido acá: 002 ya lo usaba, `identity` lo lee todos los días, y renombrarlo hubiera dejado al dueño
moviendo un parámetro que la plataforma no obedece. Que la clave del catálogo sea exactamente la que
el módulo ya consultaba es lo que hace que RF-07 —el valor nuevo se aplica sin intervención— sea
cierto para éste desde el primer día.

## `app/shared/sections.py` — las secciones del negocio

```python
class BusinessSection(enum.StrEnum):
    PURCHASING = "PURCHASING"   # proveedores, facturas, pagos, órdenes, recibos, calendario
    SALES = "SALES"             # ventas, precios, catálogo, rubros
    SYSTEM = "SYSTEM"           # parámetros y operación de la plataforma
```

Sale del mapa de roles del brief. Es vocabulario del negocio y no de `identity`: por eso vive en
`shared/` y no dentro del módulo, y por eso `operations` puede filtrar por sección sin importar
`UserRole`. `identity.dependencies.visible_sections()` es la única traducción entre rol y sección, y
vive donde ya vive la excepción de autorización.

**Se llama `BusinessSection` y no `Section`**, por dos razones que se acumulan. La primera es que
`identity.permissions.Section` ya existe y contesta otra pregunta: ésa dice **a qué pantalla llega
un rol**, ésta dice **a qué parte del negocio pertenece un hecho**; llamarlas igual invitaría a
confundirlas justo donde se cruzan. La segunda es mecánica y no se ve venir: con dos enums llamados
`Section`, FastAPI resuelve el choque en el documento OpenAPI poniéndoles a **las dos** su nombre
completo, y renombra en silencio un tipo que el frontend ya estaba leyendo.

El tipo en la base sigue llamándose `section` —`operations.section`—, que es lo que dice la columna
de la tabla de arriba: el nombre de Python evita una colisión de Python, y la base no tiene esa
colisión.

## Migraciones

**Cuatro, no una.** Este documento anticipó una sola porque las dos tablas nuevas eran todo lo que
había que crear, y esa cuenta se quedó vieja apenas la feature se implementó. Las otras tres no son
un desprolijo: cada una hace algo que las anteriores no podían hacer sin mezclar dos cosas en la
misma sentencia, y las dos últimas no diseñan nada nuevo — corrigen defectos que aparecieron
implementando, y que este documento no podía anticipar porque nacieron de leer el código que ya
había.

| Revisión | Qué hace |
|---|---|
| `0006_manual_change_log` | Los enums `operations.audit_action` y `operations.section`, la tabla `operations.audit_entry` con sus cuatro índices, y la función y los **dos** triggers que la dejan append-only. |
| `0007_manual_corrections` | El enum `correction_status` —sin schema, para que lo reuse el próximo módulo—, la tabla `core.correction` y su índice único parcial. |
| `0008_parameters_come_from_the_catalog` | Borra, de `operations.parameter` **y** de `access_settings`, las tres filas que `0003` había sembrado, y sólo si nadie las cambió. |
| `0009_where_a_value_came_from` | Agrega la columna `source` a `core.product` y a `core.product_price`, reusando `core.price_source`. |

`AuditEntry` y `Correction` entran a `app/models.py` en el mismo commit que su migración (`DB-01`;
`alembic check` corre en CI).

### Qué se rellena y qué no

**La bitácora y las correcciones arrancan vacías, a propósito.** No existen correcciones previas, e
inventar filas de un pasado que nadie registró sería exactamente lo contrario de lo que esta feature
promete.

**Las filas sembradas por `0003` se borran, no se migran.** El detalle y el porqué de las dos tablas
están arriba, en `operations.parameter`.

**Las columnas `source` sí se rellenan, y con `PORTAL`.** Es el único backfill de la feature, lo hace
el `server_default` sin una sentencia aparte, y el criterio —por qué `PORTAL` y no `SYSTEM`, que es
la opción que parece prudente y apaga dos requisitos— está argumentado arriba, en *El criterio con
que se rellenaron las filas que ya existían*.
