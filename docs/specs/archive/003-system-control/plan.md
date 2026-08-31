# Control propio del sistema — Plan técnico

<!--
  ARTEFACTO INTERNO. Acá van las decisiones técnicas que spec.md no puede llevar.
  No se exporta al cliente.
-->

**Feature:** 003-system-control · **Spec aprobada el:** 2026-08-29 · **Fecha:** 2026-08-29 · **Revisado contra el código:** 2026-08-30

## Constitution Check

| Artículo | Cumple | Cómo |
|---|---|---|
| I — El origen es ajeno y de sólo lectura | Sí | Una corrección manual vive en nuestra base y nunca sale hacia SIGProv. Esta feature **no agrega un solo acceso al portal**: la detección de conflicto ocurre sobre datos que `ingestion` ya trajo, dentro de la transacción que los aplica. Ningún módulo nuevo recibe credenciales. |
| II — Nada se descarta | Sí | Es la columna vertebral de la feature. El valor del portal se conserva en `portal_value` para siempre (RF-25), el historial es append-only con `UPDATE` y `DELETE` bloqueados por trigger (RF-16, RF-17), y un conflicto entre el portal y una corrección **se señala y se avisa**, nunca se resuelve solo (RF-28, RF-29). |
| III — Flujo unidireccional, `raw` inmutable | Sí | Las correcciones ocurren en `core`, que es el final del camino. **Nada de esta feature escribe en `raw` ni en `staging`**: `raw` sigue sin exponer `update` en su repositorio y una corrección no reescribe la fila normalizada que la originó. Reprocesar desde `raw` sigue siendo posible; las correcciones se reaplican encima porque viven en su propia tabla, no pisando la columna. |
| IV — Las fronteras entre módulos son reales | Sí | Cero imports cruzados. Dos eventos nuevos en el catálogo compartido, y una decisión deliberada: **la corrección la guarda el módulo dueño del dato, no `operations`**. Si la corrección viviera en `operations`, `catalog` tendría que leerle la tabla para detectar un conflicto, y eso es exactamente el import que la regla prohíbe. `operations` recibe el hecho por evento y guarda su propia bitácora. Lo único que cruza es `identity/dependencies.py`, la excepción fijada en el test. |
| V — Spec primero, y con firma | Sí | `spec.md` en `Estado: Aprobado`, firmada el 2026-08-29 por Leandro Carriego — FDE. Los 33 requisitos tienen lugar acá. Dos salvedades de **verificabilidad**, no de alcance, están declaradas abajo en *Riesgos*: hay criterios de aceptación que nombran facturas y avisos que todavía no existen como módulo. |
| VI — Lo que no está tipado y testeado no está terminado | Sí | `mypy --strict` (`PY-10`). La inmutabilidad del historial se prueba contra la base real, no contra el repositorio: un test de integración que intenta `UPDATE` y espera que la base lo rechace. Sin eso, `RF-16` y `RF-17` serían una promesa de código de aplicación. |
| VII — Las credenciales de terceros viven sólo en el entorno | Sí | Ninguna tabla, evento ni parámetro de esta feature toca credenciales. El catálogo de parámetros es explícitamente **para valores del negocio**: una clave nunca es un parámetro configurable, y el catálogo es una lista cerrada, así que no se puede agregar una por API. |
| VIII — Un idioma para cada audiencia | Sí | Plan y spec en español; código, eventos y commits en inglés. Las etiquetas de los parámetros y los motivos de corrección son **strings que ve el usuario** y van en español, siguiendo el precedente ya existente en `Parameter.description`. |
| IX — Las dependencias entran por la puerta | Sí | **Ninguna dependencia nueva**, ni en `uv` ni en `npm`. Todo se resuelve con lo que ya está en el proyecto. |

**Excepciones solicitadas:** ninguna.

## Enfoque

La feature son **tres mecanismos y una pantalla que los reúne**, y lo que decide su diseño es una
sola pregunta: quién es dueño de qué, cuando la regla es que los módulos no se importan.

**El panel de parámetros se arma desde un catálogo declarado, no desde la tabla.** Hoy
`operations.parameter` es una tabla libre de clave y valor: sólo tiene filas de lo que alguien ya
guardó, cualquier clave entra, y ningún rango se verifica. Con eso no se pueden cumplir RF-01
—mostrar *todos* los parámetros—, RF-04 —el valor inicial de uno que nadie tocó—, RF-05 —qué cambia
si se lo modifica— ni RF-06 —el rango admitido—. Se agrega entonces
`app/shared/parameters.py`: un catálogo declarativo, congelado, con un `ParameterSpec` por
parámetro que lleva su clave, su valor inicial, su rango, su unidad y las dos frases en español que
el dueño lee. Vive en `shared/` **por la misma razón que el catálogo de eventos**: es vocabulario
compartido, cada funcionalidad agrega su línea, y ningún módulo es su dueño. La tabla pasa a guardar
únicamente los valores que el dueño cambió; el panel muestra el catálogo con el valor vigente
encima, y `PUT` rechaza una clave que no esté en el catálogo y un valor fuera de rango. Cada
`ParameterSpec` declara además qué funcionalidad lo consume, y la pantalla **señala los que todavía
no tienen efecto**: al cerrar esta feature, **cuatro** de los siete esperan a la feature que los
lea y **tres** ya tienen quién los lea —el intervalo y el umbral de la actualización de precios, y el
tiempo de sesión, que `identity` obedece desde 002—. La cuenta se corrige sola a medida que se
construye lo demás, porque la declara cada `ParameterSpec` y no este párrafo. Una perilla que no
mueve nada sin decirlo sería exactamente la clase de pantalla que miente.

**La bitácora la escribe `operations`, pero nunca se entera de quién editó.** Toda edición manual
—en cualquier módulo, sobre cualquier dato— publica `ManualChangeRecorded`, y el handler de
`operations` lo convierte en una fila de `operations.audit_entry`. El handler corre en la
transacción del publicador, así que **no existe un cambio sin su registro**: si el handler falla,
aborta la edición (`GEN-09`). Es el artículo IV usado a favor en lugar de sufrido — el módulo que
edita no conoce `operations`, y `operations` no conoce a nadie. La inmutabilidad no se delega al
código: la migración instala dos triggers que hacen fallar cualquier `UPDATE`, `DELETE` o
`TRUNCATE` sobre la tabla —dos, porque el trigger de fila que frena los dos primeros no se dispara
ante un `TRUNCATE`—, y el repositorio ni siquiera expone los métodos.

**La corrección la guarda el módulo dueño del dato.** Esta es la decisión que más consecuencias
tiene y conviene entender por qué no es la obvia. Lo natural sería una tabla central de correcciones
en `operations`. No se puede: RF-28 exige que, cuando el portal vuelva a informar un dato, el sistema
sepa si ese dato tiene una corrección encima y con qué valor original — y quien aplica el precio
nuevo es `catalog`, que tendría que leerle la tabla a `operations`. Eso es el import prohibido
disfrazado de consulta. Entonces cada módulo guarda **su** tabla de correcciones, con la forma que le
da un mixin de `shared/`, y la detección del conflicto es una comparación local dentro de la misma
transacción que aplica el dato nuevo. `operations` no participa: se entera por el evento, como todos.

**Lo único que hoy se puede corregir es lo que hoy existe.** El catálogo de productos y sus precios
son el único dato traído del portal que vive en `core`. La feature entrega el mecanismo completo
—mixin, motivos, conflicto, aviso, anulación— y lo cablea a `catalog`; facturas, pagos y recibos lo
cablean cuando se construyan, que es lo que la propia spec anticipa en *Fuera de alcance*
—*"cada una aparece en esta pantalla cuando se construye"*—. Esto tiene una consecuencia sobre los
criterios de aceptación y está declarada abajo, en *Riesgos*: no se tapa.

**El lugar único de acciones es una vista, no un permiso.** RF-20 y RF-21 piden reunir en una
pantalla todas las cargas y correcciones disponibles y mostrarle a cada uno sólo las suyas. Se
resuelve con un registro tipado en `frontend/lib/operations/actions.ts`: cada acción declara su
etiqueta, su destino y las secciones que la habilitan, y la página filtra por la sesión. **No es una
ruta del backend a propósito.** El brief exige permisos *"verificados en cada consulta y no sólo
escondiendo opciones del menú"*, y eso ya lo garantiza `PY-09` en cada endpoint: si la pantalla fuera
la que decide, la autorización real y la lista visible serían dos fuentes que se contradicen el día
que una se olvide. La pantalla es comodidad; la frontera sigue estando en la ruta. Cada feature
futura agrega su línea al registro, igual que agrega su parámetro al catálogo.

Del lado del frontend, tres rutas nuevas bajo `(private)/`: el panel de parámetros, el historial con
sus filtros y el lugar único de acciones. Y una consecuencia que hay que ejecutar y no olvidar:
`(private)/precios/configuracion/`, que 001 creó para sus dos parámetros, **desaparece**. La regla de
negocio firmada dice que no hay parámetros escondidos en la pantalla de la funcionalidad que los usa;
esa página es exactamente eso. Se reemplaza por una redirección al panel general.

## Módulos afectados

| Módulo | Qué cambia | Nuevo |
|---|---|---|
| `operations` | El corazón de la feature. Catálogo de parámetros con rango y valor inicial, bitácora de cambios manuales con su trigger de inmutabilidad, y las rutas del panel y del historial. `JobRun` no se toca. | No |
| `catalog` | Se le suma su tabla de correcciones, la detección de conflicto sobre lo que trae una lista —el importe y la moneda donde se escribe el precio, la descripción en el recorrido, porque una corrida nunca la reescribe y ahí no hay escritura de la cual colgar la pregunta— y las rutas para corregir y anular. Es el único consumidor del mecanismo en esta feature. | No |
| `identity` | Tres archivos, y ninguno es lógica de dominio ajena. `dependencies.py`: un `visible_sections()` que responde qué secciones puede ver quien llama —composición de autorización, la excepción ya fijada por el test—. `permissions.py`: la sección `MANUAL_CORRECTIONS`, porque *hacer* una corrección lo autoriza la sección del dato (RF-24) y *anularla* es del dueño sea cual sea el dato (RF-30), que es otra pregunta y no puede tomar prestada una sección cuyo nombre sería mentira. `service.py`: el tiempo de sesión deja de estar escrito ahí y sale del catálogo. | No |
| `notifications` | Un handler más: el aviso al dueño cuando el portal contradice una corrección (RF-29). Reusa el canal que ya existe. | No |
| `shared` | `parameters.py` (catálogo declarativo), `corrections.py` (mixin de columnas y catálogo de motivos), `sections.py` (el enum `BusinessSection`), `time.py` (la zona horaria del negocio, que necesita el filtro por rango de fechas de RF-14: una fecha escrita a mano significa ese día en Buenos Aires y no el que empieza a medianoche UTC) y dos eventos. | No |
| `frontend` | Tres rutas nuevas (RF-20), el registro de acciones por sección (RF-21), la baja de `precios/configuracion`, y los componentes de corrección sobre la tabla de precios. | — |

> **Ningún módulo nuevo.** La capacidad —el sistema operando sobre sí mismo— ya tiene dueño:
> `ARCHITECTURE.md` define `operations` como *"jobs, parámetros, auditoría"*. Crear un módulo
> `settings` o `audit` sería acumulación de archivos, no una capacidad con lenguaje propio.

## Eventos de dominio

Dos eventos nuevos en `app/shared/events/catalog.py`. `BusinessParameterChanged` ya existe y se reusa
tal cual.

| Evento | Lo publica | Lo consume | Qué lleva |
|---|---|---|---|
| `ManualChangeRecorded` | cualquier módulo que edite a mano — hoy `catalog` | `operations` | `entity_type`, `entity_id`, `field`, `action`, `old_value`, `new_value`, `reason_code`, `reason_detail`, `actor_user_id`, `section` |
| `CorrectionConflicted` | el módulo dueño del dato — hoy `catalog` | `notifications` | `entity_type`, `entity_id`, `field`, `correction_id`, `original_value`, `corrected_value`, `incoming_value` |

Cuatro decisiones que conviene no rediscutir:

- **Un solo evento para toda la bitácora, con un `action`.** Cuatro eventos —creado, modificado,
  corregido, corrección anulada— serían cuatro handlers escribiendo en la misma tabla. El `action` es
  un enum de `shared`, así que no se pierde tipado y la bitácora queda con una sola puerta de entrada.
- **Los valores viajan como JSON plano, no como `Decimal` ni como modelo.** Un evento lleva
  identificadores y valores planos (`GEN-08`). La bitácora guarda `old_value` y `new_value` en JSONB
  porque tiene que servir para un precio, una fecha y un texto sin una columna por tipo.
- **`ManualChangeRecorded` no lo publica `operations`.** Cuando el dueño cambia un parámetro (RF-08),
  `operations` escribe su fila de bitácora directamente: es su propio módulo, y publicar un evento
  para escucharse a sí mismo sería ceremonia. El evento existe para lo que viene de afuera.
- **El conflicto no va a `triage`.** La spec lo deja fuera de alcance con todas las letras: no hay una
  bandeja aparte. `CorrectionConflicted` sólo alimenta el aviso; la marca vive en la fila de la
  corrección y se resuelve en la pantalla del dato.

## Datos

Dos tablas nuevas, una columna sobre dos tablas que ya existían, y un catálogo que no es una tabla.
El detalle —columnas, tipos, índices, estados— está en [`data-model.md`](data-model.md). El resumen:

| Schema | Tabla | Dueño | Nota |
|---|---|---|---|
| `operations` | `audit_entry` | `operations` | Append-only, con dos triggers que rechazan `UPDATE`, `DELETE` y `TRUNCATE` |
| `operations` | `parameter` *(existe)* | `operations` | Pasa a guardar sólo lo que el dueño cambió; el catálogo declara el resto |
| `core` | `correction` | `catalog` | El valor del portal, el corregido, el motivo y la marca de conflicto |
| `core` | `product` *(existe)* | `catalog` | Gana `source`: si hay una descripción que informó el portal debajo de la vigente |
| `core` | `product_price` *(existe)* | `catalog` | Gana `source`, por la fila y no por el producto — es lo que hace contestable RF-33 |

**Salieron cuatro migraciones, no una.** Este plan anticipó una sola porque las dos tablas nuevas
eran todo lo que había que crear, y esa cuenta se quedó vieja al implementar. Las otras tres —limpiar
las filas que `0003` había sembrado en dos tablas, y darle a RF-33 la columna con la que contestar—
están enumeradas y argumentadas en `data-model.md` → *Migraciones*.

La columna `source` merece una línea acá porque **es la única parte de esta feature que modifica
tablas anteriores**, y no estaba prevista. Sin ella, el código contestaba *«¿este dato vino del
portal?»* con `registered_by_rule_id`, que contesta otra pregunta —qué regla aprendida incorporó un
producto (`001/RF-37`: calificado porque es de la 001, y toda `RF-` sin calificar de este documento
es de la 003)— y leía como cargado a mano a todo producto que hubiera llegado en una lista común:
justo las filas donde una corrección más necesita conservar lo que el portal dijo (RF-25, RF-28).

**Los siete parámetros y su valor inicial** quedan declarados en `app/shared/parameters.py`:

| Clave | Inicial | Rango | Lo consume |
|---|---|---|---|
| `price_update.interval_hours` | 12 | 1–168 | `operations` — **hoy** |
| `price_update.highlight_threshold_pct` | 10 | 0–1000 | `catalog` — **hoy** |
| `access.session_idle_minutes` | 60 | 5–1440 | `identity` — **hoy** |
| `due_date.notice_days` | 3 | 0–90 | P11 — cuando se construya |
| `purchase_order.stalled_days` | 15 | 1–365 | P6 — cuando se construya |
| `receipt.notice_days` | 3 | 0–90 | P12 — cuando se construya |
| `daily_digest.time` | `"08:00"` | hora del día | P8 — cuando se construya |

La columna de la derecha es la foto del día en que se cierra esta feature. Cada spec que se
construya después le pone consumidor a alguno de los cuatro que esperan y suma los suyos al mismo
catálogo y a la misma pantalla, sin migración: la fuente de esa columna es el `consumed_by` de cada
`ParameterSpec`, no esta tabla.

**El intervalo lo lee `operations`, no `catalog`, y su etiqueta dice lo otro.** `interval_hours()`
decide con ese número si la extracción está vencida; el handler de `catalog` que escucha
`BusinessParameterChanged` se queda **sólo** con el umbral. O sea que el `consumed_by` del intervalo
declara un consumidor equivocado. No es una perilla muerta —que es justamente lo que el campo existe
para señalar, y el intervalo sí mueve algo—, así que el daño es leve y el arreglo es una palabra;
queda anotado para que nadie lo copie al declarar el próximo parámetro.

**`operations` suelta las dos constantes que duplicaban a los dos primeros** —`DEFAULT_INTERVAL_HOURS`
y `DEFAULT_HIGHLIGHT_THRESHOLD` ya no están en `operations/service.py`, que en el lugar donde
estaban deja escrito por qué—, y `PUT /price-updates/settings` de 001 sigue funcionando igual porque
escribe las mismas claves.

**El umbral, en cambio, sigue teniendo dos declaraciones, y esta es la deuda que queda.**
`catalog/service.py` conserva su propio `DEFAULT_HIGHLIGHT_THRESHOLD = Decimal("10")` como valor de
respaldo, y `highlight_threshold()` cae ahí cuando no hay fila guardada o cuando la que hay no es un
número. O sea que el 10 vive en dos lugares y el catálogo **no** es todavía su fuente única: el día
que alguien mueva el `initial` del catálogo, la plataforma que nadie configuró va a seguir
destacando por el 10 viejo. El arreglo es de una línea, y es exactamente el que `identity` ya usa
para `DEFAULT_IDLE_MINUTES`:

```python
DEFAULT_HIGHLIGHT_THRESHOLD = Decimal(str(initial_value(HIGHLIGHT_THRESHOLD_KEY)))
```

Queda anotado acá y no sólo en un informe, porque es el documento el que tiene que decir la verdad
sobre el estado del código.

**Tres de los siete se leen hoy, no dos, y la corrección de esa cuenta no es cosmética.** Este plan
decía «cinco esperan» y nombraba la clave del tiempo de sesión como `session.idle_timeout_minutes`,
una clave que no existe. Las dos cosas venían del mismo error: **dar por no construida a la 002**,
que está entregada y archivada. `identity` lee `access.session_idle_minutes` en cada request para
decidir si la sesión venció, y la lee **primero de su propia proyección `access_settings`**, donde
`0003` había sembrado 480 minutos.

Contarlo entre los que «todavía no mueven nada» fue lo que dejó a este parámetro sin nadie
observándolo, y debajo había algo peor que un número mal escrito: un choque entre dos specs firmadas
que `/analyze` no podía ver, porque este plan afirmaba que la funcionalidad no existía. Declarar 60
en el catálogo no hubiera alcanzado —la proyección gana—, así que `0008` borra la fila sembrada de
las dos tablas y `DEFAULT_IDLE_MINUTES` pasa a salir del catálogo. El catálogo adopta la clave tal
cual la venía usando `identity`, para que el parámetro que el dueño mueve sea el parámetro que la
plataforma obedece.

**Dos claves de `0003` quedan deliberadamente fuera del catálogo**: `access.max_failed_attempts` y
`access.lockout_minutes` siguen siendo constantes de `identity` y dejan de ser configurables por API
hasta que una feature las agregue. Al cerrar esta feature el panel lleva exactamente estos siete.

## Contratos

Toda ruta declara su autorización con la dependencia de `identity` (`PY-09`, Blocker, verificado por
`tests/architecture/test_route_authorization.py`). Prefijo `/api/v1`.

| Método y ruta | Requisitos | Autorización |
|---|---|---|
| `GET /operations/parameters` | RF-01, RF-04, RF-05 | `SYSTEM_PARAMETERS` · lectura — hoy sólo el dueño |
| `PUT /operations/parameters` | RF-02, RF-03, RF-06, RF-07, RF-08 | `SYSTEM_PARAMETERS` · escritura — hoy sólo el dueño |
| `GET /operations/audit` | RF-12, RF-13, RF-14, RF-18, RF-19 | autenticado · filtrado por sección |
| `GET /operations/audit/{entity_type}/{entity_id}` | RF-15 | autenticado · filtrado por sección |
| `GET /operations/corrections/reasons` | RF-11 | autenticado |
| `POST /catalog/products/{product_id}/corrections` | RF-11, RF-22 a RF-27 | `PRODUCT_CATALOG` · escritura — dueño y ventas |
| `DELETE /catalog/corrections/{correction_id}` | RF-30 a RF-33 | `MANUAL_CORRECTIONS` · escritura — sólo el dueño |

Tres cosas sobre esta tabla:

- **`GET /operations/audit` no es una ruta de dueño.** RF-19 dice que los demás ven los cambios de
  *su* sección, así que la ruta es para todo autenticado y el filtro por sección lo aplica el
  repositorio, no el router. `identity.dependencies.visible_sections()` responde qué secciones ve
  quien llama —el dueño, todas— y llega a la ruta como `VisibleSections`, así que `operations` filtra
  sin nombrar un solo rol: lo que cruza la frontera es vocabulario del negocio, y `UserRole` se queda
  del lado de `identity`, que es el único módulo que tiene por qué conocerlo.
- **Corregir un producto es del dueño y de ventas; anular es sólo del dueño.** Lo primero sale de
  RF-24 más el mapa de secciones del brief —el catálogo y los precios son de ventas—; lo segundo es
  RF-30 tal cual. La asimetría es deliberada y está firmada. **Ninguna ruta nombra un rol**: la
  columna dice la sección que la ruta exige, que es lo único que el código declara (`PY-09`), y quién
  llega hasta ahí lo decide la matriz de `identity`. Por eso anular tiene sección propia,
  `MANUAL_CORRECTIONS`, y no toma prestada la del dato: corregir un precio lo autoriza el catálogo,
  pero anular es del dueño **sea cual sea el dato**, y una sección que dijera «catálogo» mentiría
  sobre esa segunda pregunta el día que exista una corrección sobre una factura.
- **La lista de motivos la sirve el backend.** Es el backend el que valida el `reason_code`
  (RF-11), así que la lista sale de la misma fuente que la validación. Si viviera en el frontend,
  serían dos listas que se desincronizan.

## Alternativas descartadas

- **Una tabla central de correcciones en `operations`.** Es la forma obvia y es la que rompe la
  arquitectura: `catalog` necesita saber, al aplicar un precio nuevo, si ese dato tiene corrección y
  cuál era el original (RF-28). Con la tabla en `operations` eso es leerle la tabla a otro módulo, o
  mantener una proyección de correcciones dentro de `catalog` — que es la tabla que ahora tiene, sólo
  que con un viaje de ida y vuelta por el bus y una ventana de inconsistencia en el medio. La
  proyección directa es la misma solución sin el rodeo.
- **Guardar la corrección como columnas en la propia fila** (`price`, `portal_price`,
  `corrected_by`…). Menos tablas. Se descarta: RF-23 pide corregir *cualquier* campo, y eso son tres
  columnas nuevas por cada campo corregible, en cada tabla. Una fila por corrección escala sola.
- **Un evento por tipo de cambio.** Descartado arriba, en *Eventos de dominio*.
- **Un módulo nuevo `audit` o `settings`.** Descartado arriba: la capacidad ya tiene dueño.
- **Hacer inmutable la bitácora sólo desde el repositorio**, sin trigger. Es lo que hizo 001 con
  `raw` y ahí alcanzaba, porque `raw` lo escribe una task y nadie más. Acá no: RF-16 y RF-17 dicen
  *"el sistema debe impedir"*, y un método que no existe sólo impide mientras nadie lo agregue. El
  trigger lo impide también para una consola de `psql`, y cuesta seis líneas de migración.
- **Que el frontend arme el panel de parámetros con su propia lista.** Se descarta: el backend valida
  el rango, así que la lista de parámetros y sus límites tienen que salir de donde se validan. El
  frontend renderiza lo que el backend declara.
- **Servir la lista de acciones de RF-20 desde el backend.** Sería coherente con el catálogo de
  parámetros. Se descarta porque no es lo mismo: un parámetro necesita al backend porque ahí se
  valida su rango, mientras que una acción es un enlace a una ruta que ya declara su propia
  autorización. Una lista de enlaces servida por la API sería un segundo lugar donde se decide quién
  puede qué, y el día que discrepe del decorador de la ruta gana el decorador — con lo cual la lista
  sólo puede mentir.
- **Resolver el conflicto de RF-28 mandándolo a `triage`.** Sería reusar una cola que ya existe y
  funciona. Está **fuera de alcance por decisión firmada**: la spec dice que no hay una bandeja aparte
  y que el caso se cierra en la pantalla del dato.

## Riesgos

| Riesgo | Impacto | Cómo se mitiga |
|---|---|---|
| **Dos criterios de aceptación nombran datos que todavía no existen.** RF-23 se verifica corrigiendo *"el número de comprobante de una factura escaneada"* y RF-24 con *"Julián no puede corregir el total de una factura de compra"*. No hay módulo de facturas: es 004, todavía en borrador. | Dos de los 33 criterios no se pueden marcar en verde al cerrar esta feature. | El mecanismo se construye completo y genérico, y se verifica **con los datos que existen**: corregir la descripción de un producto —que no es un importe— prueba lo mismo que RF-23 quiere probar, y que compras no pueda corregir un producto prueba lo mismo que RF-24. Los dos criterios con su redacción literal se cierran en 004, y eso queda anotado en `tasks.md` para que `/converge` no lo lea como un requisito incumplido. **Decidido por el humano el 2026-08-29: se acepta la verificación por analogía.** |
| **Cuatro de los siete parámetros no los lee nadie todavía.** El panel los muestra, el dueño los puede cambiar y el valor se guarda, pero la funcionalidad que los usa no está construida. | El dueño puede mover una perilla que hoy no mueve nada, y RF-07 —*"aplicar el valor nuevo sin intervención adicional"*— no se puede observar para esos cuatro. | Se declaran igual, porque son la decisión firmada y el catálogo es su única fuente: cuando P8, P11, P12 y P6 se construyan, encuentran el valor que el dueño ya eligió, sin migración ni cambio de pantalla. `ParameterSpec` lleva un campo con el módulo que lo consume. **Decidido por el humano el 2026-08-29: se muestran los siete y la pantalla señala cuáles todavía no tienen efecto**, para que el dueño los pueda fijar desde el día uno sin creer que ya mueven algo. **Corrección posterior:** esta fila decía «cinco» y contaba entre ellos al tiempo de sesión, que 002 ya lee. La fila de abajo cuenta lo que costó. El cuatro es la cuenta al cerrar esta feature y baja sola: cada spec que se construya después le pone consumidor a alguno de ellos. |
| **La lista de motivos de corrección la inventa este plan.** La spec dice *"una lista corta"* y no la enumera. | Una lista mal elegida se vuelve inútil: si todos eligen *"otro"*, contar los motivos no sirve para nada, que era el punto de tener lista. | Se arranca con cinco —el portal lo informó mal, se leyó mal del documento escaneado, se cargó mal a mano, el proveedor lo corrigió después, otro— y el campo de detalle escrito queda siempre disponible. Son un enum de `shared`, así que agregar uno es una línea y una migración de nada. **Decidido por el humano el 2026-08-29: se implementan los cinco y el cliente los valida en `/converge`**, mientras todavía no haya correcciones etiquetadas. |
| **El handler de bitácora aborta la edición si falla** (`GEN-09`). Es lo que queremos, pero significa que un error escribiendo la bitácora hace fallar una corrección que el usuario ya confirmó. | Una corrección que "no anda" sin motivo visible. | Es la decisión correcta y no se cambia: un cambio sin registro es exactamente lo que el Artículo II prohíbe. Se mitiga con el mensaje: el error de dominio sube como `ERR-01` con su detalle, y RF-22 obliga a que la pantalla diga que falló. |
| **H2 y H4 están narradas desde Marcela, y en esta feature Marcela no tiene nada que corregir.** El único dato del portal que existe son los precios, que según el mapa de roles son de ventas. | El actor que protagoniza las dos historias de corrección no las puede ejercer hasta la 004. | **Decidido por el humano el 2026-08-29: se sigue con la 003 y se anota en la spec.** El mecanismo se entrega completo; las dos historias se verifican con el dueño y con Julián, y Marcela las usa sobre sus propios datos —las facturas— cuando llegue la 004. Se descartó reordenar 003 y 004 porque la 004 todavía no tiene spec firmada. |
| **`access.session_idle_minutes` arranca en 60, y las ocho horas están firmadas dos veces: en el brief y en la RF-36 de la 002.** | No son dos fuentes que discrepan en el papel: **002 está entregada y archivada**, así que hay código corriendo que obedece una de las dos. Este plan no lo vio porque daba a 002 por construir, y `/analyze` heredó ese error. | Gana la 003: el cliente eligió 60 minutos en el `/clarify` del 2026-08-29, después del brief. **Decidido por el humano el 2026-08-30.** Declararlo en el catálogo no alcanza —`identity` mira primero su proyección `access_settings` y sólo cae al catálogo si no hay fila—, así que `0008` borra la fila con 480 de esa tabla **y** de `operations.parameter`, y sólo si nadie la cambió: un valor elegido es una decisión y una migración no está para revocarla. Sin ese borrado el panel muestra 60, el dueño cree que eligió, y la plataforma sigue cerrando sesiones a las ocho horas. Anotado también en el traspaso. **Queda pendiente, y es del humano:** enmendar `docs/specs/archive/002-access-control/spec.md`, cuya RF-36 y cuyo criterio de aceptación siguen prometiendo ocho horas. Es una spec firmada, y una spec firmada no la corrige un agente. |
| **La página `precios/configuracion` de 001 queda contradiciendo una regla de negocio firmada.** | Dos lugares para cambiar el mismo parámetro, que es exactamente lo que la regla prohíbe. | Se elimina en esta feature y se reemplaza por una redirección al panel general. No es opcional ni "si da el tiempo": es una regla de negocio de la spec que se está firmando. |

## Contexto de traspaso

**Para el Developer** — Empezá por `app/shared/`: los archivos nuevos —`parameters.py`,
`sections.py`, `corrections.py` y `time.py`, que es la zona horaria del negocio y la necesita el
filtro por fechas de RF-14— y los dos eventos. Todo lo demás depende de ellos y ninguno tiene
dependencias propias, así que se pueden escribir y testear solos. Después `operations` (catálogo +
bitácora + rutas), después `catalog` (correcciones + conflicto), y el frontend al final.

**Lo que NO tenés que tocar:** `operations.JobRun` y todo lo que 001 construyó alrededor del
`price_update` —status, request, settings— sigue funcionando igual; el único cambio es que sus dos
constantes por defecto se mudan al catálogo compartido. `raw` y `staging` no se tocan en toda la
feature: si te encontrás escribiendo ahí, algo se entendió mal.

**Decisiones ya tomadas, no las rediscutas:** la corrección la guarda el módulo dueño del dato y no
`operations`; la bitácora se escribe por evento en la transacción del publicador; la inmutabilidad es
un trigger y no una convención; el catálogo de parámetros es una lista cerrada y `PUT` rechaza lo que
no esté en ella. Si alguna te resulta incómoda de implementar, **es señal de que la frontera está mal
trazada y hay que escalar al Backend-Architect**, no de que convenga un import.

**Tres cosas que tenés que ejecutar y son fáciles de olvidar:** borrar
`frontend/app/(private)/precios/configuracion/` y dejar la redirección; agregar `AuditEntry` y
`Correction` a `app/models.py` en el mismo commit que su migración (`DB-01`, `alembic check` corre en
CI); y **limpiar las filas que `0003` sembró para el acceso, en las dos tablas donde las escribió**.

La tercera es la que más fácil se pasa por alto y la que más caro sale, así que va con su porqué:
`access.session_idle_minutes` **no espera a ninguna feature futura**, `identity` la lee en cada
request, y la lee primero de su proyección `access_settings` antes de caer al catálogo. Si la fila
con 480 sobrevive, el panel muestra 60 y la plataforma sigue cerrando sesiones a las ocho horas — un
número en pantalla que el sistema no obedece, que es exactamente lo que esta feature promete que no
va a pasar. Las otras dos claves que `0003` sembró —intentos fallidos y bloqueo— **no** entran al
catálogo: siguen siendo constantes de `identity` porque no se ofrecen en el panel, y sus filas se
borran por lo mismo, porque ya no hay forma de llegar a ellas.

**Para el Tester** — Lo que puede romperse de verdad no es corregir un valor: es todo lo que pasa
alrededor.

- **La bitácora tiene que ser inmutable contra la base, no contra el repositorio.** El test que
  importa es un `UPDATE` y un `DELETE` por SQL directo sobre `operations.audit_entry`, esperando que
  la base los rechace. Un test que sólo compruebe que el repositorio no tiene el método no prueba
  RF-16 ni RF-17.
- **Un handler que falla aborta la edición.** Probá que una corrección cuya bitácora falla **no deja
  el valor corregido**: es `GEN-09` y es el único lugar donde un rollback es el comportamiento correcto.
- **El conflicto de RF-28 es el caso borde de la feature.** Tres corridas: el portal informa lo mismo
  que el original —sin novedad—, informa algo distinto —conflicto, corrección intacta, aviso al
  dueño—, y vuelve a informar lo distinto una segunda vez —no se duplica el aviso ni se pisa nada—.
  Y las tres **sobre los tres campos corregibles**, no sólo sobre el importe: la moneda se mide contra
  lo que dejó la persona y no contra el portal, y la descripción se compara en el recorrido de la
  lista y no donde se escribe el precio. Un test que sólo mueva el número deja los otros dos caminos
  sin ejercitar y pasa igual.
- **Anular una corrección restituye el valor del portal, no el anterior.** Son distintos si hubo dos
  correcciones seguidas, y es fácil implementarlo mal.
- **RF-33 al revés**: pedir la anulación sobre un dato sin corrección tiene que fallar limpio.
- **RF-33 de frente, y esto lo aprendimos implementando**: «¿vino del portal?» se le pregunta a la
  fila que tiene el valor, y la respuesta vive en su columna `source`. El caso que separa lo bueno de
  lo aparente es un producto cargado a mano al que la lista del día siguiente le pone precio: el
  producto sigue sin ser del portal y el importe ya lo es, así que corregir la descripción y corregir
  el precio tienen que dar respuestas distintas sobre la misma pantalla.
- **El filtro por sección de RF-19** se prueba con tres usuarios reales, uno por rol, no con mocks:
  es autorización, y la autorización se prueba end-to-end.
- **RF-06 en los bordes exactos** de cada rango, y una clave que no está en el catálogo, que tiene que
  ser rechazada.

**Para el Code-Reviewer** — Las convenciones en juego, por orden de riesgo:

- **`GEN-02` y `GEN-03`** — el diseño entero se juega en que la corrección viva en el módulo dueño.
  Mirá primero los imports de `catalog/service.py` y de `operations/service.py`: si alguno de los dos
  nombra al otro, el diseño se rompió y hay que volver acá, no parchear.
- **`GEN-08` y `GEN-09`** — que `ManualChangeRecorded` no lleve un modelo de SQLAlchemy ni un
  `Decimal` crudo, y que el handler de bitácora **no** capture su propia excepción para "no molestar".
- **`PY-09`** — siete rutas nuevas. Revisá que `GET /operations/audit` **no** sea sólo del dueño
  —RF-19 dice lo contrario— y que `DELETE /catalog/corrections/{id}` **sí** lo sea.
- **`DB-01`** — dos tablas nuevas, sus modelos en `app/models.py`, y los **dos** triggers dentro de
  la migración y no en un script suelto. Están además colgados del metadata en `operations/models.py`,
  porque la base de tests se arma con `create_all()` y una invariante que sólo existe en producción es
  una invariante que ningún test prueba.
- **Artículo III** — que nada de esta feature escriba en `raw` ni en `staging`. Es una ausencia, y
  las ausencias son lo que un review no ve si no las busca.
- **La regla de negocio de la pantalla única** — que `precios/configuracion` haya desaparecido de
  verdad. Es la clase de tarea que se cae del final de una feature y deja el producto contradiciendo
  su propia spec.
