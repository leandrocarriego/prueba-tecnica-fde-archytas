# Actualización de la lista de precios — Plan técnico

<!--
  ARTEFACTO INTERNO. Acá van las decisiones técnicas que spec.md no puede llevar.
  No se exporta al cliente.
-->

**Feature:** 001-price-list-update · **Spec aprobada el:** 2026-08-28 · **Fecha:** 2026-08-28

## Constitution Check

| Artículo | Cumple | Cómo |
|---|---|---|
| I — El origen es ajeno y de sólo lectura | Sí | La extracción es Playwright navegando la sección de precios como una persona. No se usa ningún endpoint JSON interno del portal, no se emite ninguna escritura contra SIGProv, y el módulo `portal` no expone forma de hacerlo: su único método público obtiene y devuelve bytes. |
| II — Nada se descarta | Sí | Es el corazón de la feature. Una fila que no se puede interpretar va a `staging.price_row` con `status = CUARENTENA` y abre una fila en `operations.exception`; un producto desconocido y uno que desapareció también. H8 agrega lo que el artículo pide además: la decisión humana se guarda como `operations.resolution_rule` y se reaplica sola. |
| III — Flujo unidireccional, `raw` inmutable | Sí | `raw.portal_document` guarda el archivo tal como llegó con su `content_hash`, sin `UPDATE` ni `DELETE`: el repositorio de `raw` sólo expone `insert` y `get`. Toda corrección ocurre al normalizar hacia `staging`, así que se puede reconstruir `core` desde `raw` sin volver a pedirle nada al portal. |
| IV — Las fronteras entre módulos son reales | Sí | Cinco módulos, cero imports cruzados: se hablan por dieciséis eventos nuevos del catálogo compartido. Las dos lecturas sincrónicas que la feature necesitaba —`ingestion` consultando las reglas aprendidas, y `catalog` sabiendo qué productos conoce— se resuelven con proyecciones propias alimentadas por eventos, que es el costo que el artículo dice que hay que aceptar. Detalle abajo en *Eventos de dominio*. |
| V — Spec primero, y con firma | Sí | `spec.md` está en `Estado: Aprobado`, firmada el 2026-08-28. Este plan no agrega alcance: los 45 requisitos tienen lugar acá y no hay nada acá que no salga de uno de ellos. |
| VI — Lo que no está tipado y testeado no está terminado | Sí | Tipos completos con `mypy --strict` (`PY-10`). El parser de la lista se testea contra **archivos fijados**, nunca contra el portal en vivo (`TEST-03`); la task de extracción tiene su test de idempotencia (`TEST-04`), apoyada en `content_hash`. |
| VII — Las credenciales de terceros viven sólo en el entorno | Sí | `SIGPROV_USER` y `SIGPROV_PASSWORD` se leen de `config.Settings` y no se persisten, no se loguean y no viajan en un traceback: el cliente del portal envuelve sus errores en una excepción de dominio propia antes de propagarlos. Ninguna tabla de este plan tiene una columna de credencial. |
| VIII — Un idioma para cada audiencia | Sí | Este plan y la spec en español; el código, los nombres de eventos y los commits en inglés; los strings de la UI en español. |
| IX — Las dependencias entran por la puerta | Sí | `uv add` con el lockfile en el mismo commit. La única dependencia candidata está justificada abajo en *Alternativas descartadas*, y puede terminar siendo ninguna. |

**Excepciones solicitadas:** ninguna.

## Enfoque

La feature se construye como un **pipeline de cinco pasos que no se conocen entre sí**, encadenados
por eventos. Celery beat dispara la task de extracción con la frecuencia que el dueño configuró (RF-01);
`portal` entra al portal con Playwright, descarga el archivo del día y lo guarda **verbatim** en
`raw` con su hash (RF-05); `ingestion` lo normaliza fila por fila hacia `staging`, marcando cada una
`VALIDO` o `CUARENTENA` sin que una fila rota frene a las demás (RF-06); `catalog` toma las válidas y registra el precio vigente de cada producto que conoce (RF-03),
decidiendo qué producto conoce y cuál no; `triage` recibe todo lo que quedó apartado y lo pone en una cola con
su motivo. Ningún paso llama al siguiente: publica un hecho y se olvida.

Ese encadenamiento es también la respuesta al **enlace de descarga que caduca a los 45 segundos**
(relevado en el portal): la task no genera el enlace para consumirlo después. Descarga dentro del
mismo contexto de Playwright, en el mismo flujo, y lo primero que hace con los bytes es escribirlos
en `raw`. Todo lo demás —parseo, normalización, actualización— ocurre después, sobre bytes que ya
están guardados, y por lo tanto es **reproducible sin volver al portal**. Si el parser resulta
equivocado, se corrige y se reprocesa el histórico; el portal no se entera.

**Las dos lecturas sincrónicas entre módulos que la feature parecía necesitar se resuelven con
proyecciones.** `ingestion` tiene que saber, al normalizar, si una fila ya fue resuelta antes por
una persona (RF-34) — pero no puede importar `triage`. Entonces mantiene su propia tabla
`staging.resolution_rule`, alimentada por los eventos que `triage` publica cuando alguien resuelve o
anula una regla. Del mismo modo `catalog` es dueño de qué productos conoce, así que no le pregunta a
nadie: decide él, y publica lo que no pudo resolver. Es exactamente el costo que el Artículo IV dice
que hay que aceptar, y acá es barato: las reglas son pocas y cambian sólo cuando una persona decide.

**El historial publicado se trae una vez por producto, y fuera de la transacción que lo descubrió.**
Cuando `catalog` registra un producto como conocido por primera vez (RF-38) publica el hecho, pero el
handler **no sale a navegar**: encola una task de Celery y vuelve enseguida. Es lo que la arquitectura
prescribe —un handler corre en la transacción del publicador, y una visita a un sistema de un tercero
no puede tenerla abierta—. La task visita la pantalla de historial de ese producto y guarda el HTML en
`raw`; de ahí en adelante recorre **exactamente el mismo pipeline que la lista** —`ingestion` tipa
cada punto hacia `staging.price_history_row` marcándolo `VALIDO` o `CUARENTENA`, y `catalog` toma los
válidos—. No es simetría por elegancia: es el Artículo III, y es lo único que le da a un historial
ilegible un lugar donde quedar apartado en vez de desaparecer (RF-39). Cien productos el primer día son cien visitas: van
encoladas y espaciadas, no en ráfaga, porque la cuenta del portal es compartida.

Del lado del frontend, tres pantallas bajo `(private)/`: la lista de precios con sus destacados, el
estado de la última actualización y el botón de traerla ahora; el detalle de un producto con su
evolución; y la cola de revisión. Los parámetros viven en una cuarta, sólo para el dueño. Todas
consumen el backend a través del proxy que ya existe: el navegador nunca le pega directo a la API.

## Módulos afectados

| Módulo | Qué cambia | Nuevo |
|---|---|---|
| `portal` | Cliente Playwright con login, navegación a la sección de precios, descarga del archivo del día y visita a la pantalla de historial de un producto. Sin `routes.py`: no tiene superficie HTTP, lo consumen las tasks. Es donde viven —y mueren— las credenciales. | Sí |
| `ingestion` | `raw` → `staging`: hash, tipado, normalización y cuarentena. Aplica las reglas aprendidas desde su proyección local. | Sí |
| `catalog` | Productos, precio vigente e historial en `core`, incluido el que el portal ya publica (RF-38 a RF-40). Decide conocido/desconocido, calcula destacados y la variación mensual. | Sí |
| `triage` | La cola de excepciones y las reglas aprendidas. H7 y H8 completos. | Sí |
| `operations` | Se le suma la detección de interrupción —dos consultas seguidas sin éxito— y los dos parámetros de la feature. `JobRun` y `Parameter` ya existen y no se tocan. | No |
| `notifications` | Envío del aviso por WhatsApp vía Evolution API. Deliberadamente mínimo: un canal, un destinatario, sin plantillas. Es la costura donde P8 va a crecer. | Sí |
| `identity` | Nada propio. Sólo se monta su `dependencies.py` para que cada ruta declare su autorización (`PY-09`), que es la única excepción a la frontera. | No |
| `frontend` | Cuatro rutas bajo `(private)/` y sus componentes. | — |

> Cinco módulos nuevos es mucho para una feature, y es a propósito: **P1 construye la columna
> vertebral del producto**. `portal`, `ingestion` y `triage` son los tres que P2 —las facturas— va a
> reusar tal cual. Si se los construyera recién en P2, P1 tendría que resolver lo mismo peor y a
> mano. Cada uno se justifica por una capacidad del negocio con lenguaje propio, no por acumulación
> de archivos.

**Consecuencia sobre la documentación:** `notifications` no figura en el mapa de módulos de
`ARCHITECTURE.md`, que hoy sólo lista `messaging/` para los mensajes internos del portal. Son cosas
distintas y el mapa hay que actualizarlo en el mismo commit que cree el módulo.

## Eventos de dominio

Dieciséis eventos nuevos en `app/shared/events/catalog.py`, todos en pasado, congelados, con
identificadores y valores planos (`GEN-08`). `JobRunFailed` ya existe y se reusa.

| Evento | Lo publica | Lo consume | Qué lleva |
|---|---|---|---|
| `PriceListExtracted` | `portal` | `ingestion` | `raw_document_id`, `content_hash`, `content`, `content_type`, `fetched_at`, `job_run_id` |
| `PriceListNormalized` | `ingestion` | `catalog` | `batch_id`, `raw_document_id`, `rows` — tupla de valores planos con `staging_row_id`, `product_code`, `description`, `price`—, `seen_codes`, `quarantined`, `job_run_id` |
| `PriceRowsQuarantined` | `ingestion` | `triage` | `batch_id`, `cases` — tupla con `staging_row_id`, `reason`, `excerpt` |
| `ProductPricesUpdated` | `catalog` | `operations` | `batch_id`, `updated`, `unchanged`, `highlighted`, `quarantined`, `job_run_id` |
| `UnknownProductsObserved` | `catalog` | `triage` | `batch_id`, `cases` — tupla con `staging_row_id`, `product_code`, `description`, `price` |
| `KnownProductsMissing` | `catalog` | `triage` | `batch_id`, `products` — tupla con `product_id`, `product_code` y `description` |
| `QuarantineCaseResolved` | `triage` | `catalog`, `ingestion` | `case_id`, `kind`, `decision`, `payload`, `rule_id`, `matcher`, `decided_by_user_id`, `decided_at` |
| `QuarantineRuleRevoked` | `triage` | `ingestion`, `catalog` | `rule_id`, `kind`, `matcher`, `decision` |
| `PriceUpdateStalled` | `operations` | `notifications` | `consecutive_failures`, `last_success_at`, `reason` |
| `PriceUpdateRecovered` | `operations` | `notifications` | `recovered_at` |
| `ProductsRegistered` | `catalog` | `portal` | `batch_id`, `products` — tupla con `product_id` y `product_code` |
| `ProductHistoryExtracted` | `portal` | `ingestion` | `raw_document_id`, `product_code`, `content_hash`, `content` |
| `JobRunSucceeded` | quien corrió la task | `operations` | `job_run_id`, `job_name` |
| `BusinessParameterChanged` | `operations` | `catalog` | `key`, `value` |
| `PriceHistoryNormalized` | `ingestion` | `catalog` | `product_code`, `points` — tupla con `staging_row_id`, `price` y `changed_at` |
| `PriceHistoryRowsQuarantined` | `ingestion` | `triage` | `product_code`, `cases` — tupla con `staging_row_id`, `reason` y `excerpt` |

Tres decisiones que conviene no rediscutir:

- **Un evento por lote, no uno por fila.** Con ~100 productos, cien publicaciones dentro de la misma
  transacción son cien despachos de handler sin ningún beneficio. El evento lleva una tupla de
  dataclasses planas —no modelos de SQLAlchemy—, que es lo que `GEN-08` pide.
- **`PriceUpdateStalled` lo publica `operations`, y sólo una vez por interrupción.** RF-13 dice que
  el aviso no se repite mientras la causa siga siendo la misma, y quien sabe si esta es la misma
  interrupción o una nueva es quien tiene el historial de `JobRun`. Poner la deduplicación en
  `notifications` sería ponerla donde no está el dato.
- **El handler de `ProductsRegistered` encola, no navega.** Es el único de la feature que no hace su
  trabajo en el acto: visitar cien pantallas del portal dentro de la transacción que registró los
  productos la tendría abierta minutos contra un sistema de un tercero. Encola una task por producto
  y vuelve; si la extracción falla, falla como `JobRun`, visible, sin arrastrar consigo el registro
  del producto, que ya es un hecho consumado.
- **`QuarantineCaseResolved` lo escuchan dos módulos y ninguno se entera del otro.** `catalog` actúa
  —da de alta el producto, fija el precio, marca discontinuado—; `ingestion` guarda la regla en su
  proyección. Es el caso de manual del Artículo IV.

## Datos

Cuatro schemas, en un solo sentido. El detalle —columnas, tipos, índices, estados— está en
[`data-model.md`](data-model.md). El resumen:

| Schema | Tablas | Dueño |
|---|---|---|
| `raw` | `portal_document` | `ingestion` escribe vía `portal`; **sólo `INSERT` y `SELECT`** |
| `staging` | `price_row`, `price_history_row`, `resolution_rule` *(proyección)* | `ingestion` |
| `core` | `product`, `product_price`, `price_point` | `catalog` |
| `operations` | `exception`, `resolution_rule`, `job_run` *(existe)*, `parameter` *(existe)* | `triage` las dos primeras, `operations` las dos últimas |

Dos advertencias que ahorran un bug:

- **El schema no es la frontera.** `triage` y `operations` escriben tablas en el mismo schema
  `operations` de Postgres, porque así lo fija `AGENTS.md` —la excepción vive en
  `operations.exception`—. Eso **no** los habilita a leerse las tablas entre sí: la frontera sigue
  siendo el módulo, y el test la verifica por import, no por schema.
- **`raw` no se corrige.** Su repositorio no expone `update` ni `delete`, y es la forma barata de
  que el Artículo III no dependa de que alguien se acuerde. La **única** escritura posterior al
  insert es `mark_normalized`, que toca una columna de contabilidad propia y no puede alcanzar ni
  el contenido, ni el hash, ni el momento en que el documento llegó. El porqué está abajo, en
  *Decisiones posteriores a la convergencia*.

**`staging.price_row` guarda la categoría y la subcategoría tal como vinieron, sin interpretarlas.**
No es alcance de P1 —el cliente no las ve en ninguna pantalla de esta feature, y por eso no hay
requisito— sino una comodidad para **P7 — El problema de los rubros**: el archivo ya las conserva
byte por byte en `raw`, así que P7 podría reconstruirlas reprocesando, pero llevarlas a `staging`
ahora le ahorra reparsear el archivo entero. Cuestan dos columnas nullable y ningún código: en esta
feature nadie las lee.

Los dos parámetros de H4 no necesitan tabla: entran en `operations.parameter`, que ya existe con
`value` en JSONB, bajo las claves `price_update.interval_hours` (inicial `12`) y
`price_update.highlight_threshold_pct` (inicial `10`).

## Contratos

Toda ruta declara su autorización con la dependencia de `identity` (`PY-09`, Blocker, verificado por
`tests/architecture/test_route_authorization.py`). Prefijo `/api/v1`.

| Método y ruta | Requisitos | Autorización |
|---|---|---|
| `GET /prices` | RF-04, RF-25 | `OWNER`, `PURCHASING`, `SALES` |
| `GET /prices/{product_id}/history` | RF-23, RF-24 | `OWNER`, `PURCHASING`, `SALES` |
| `GET /price-updates/status` | RF-09, RF-11 | `OWNER`, `PURCHASING`, `SALES` |
| `POST /price-updates` | RF-14, RF-15, RF-17 | `OWNER`, `PURCHASING` |
| `GET /price-updates/{job_run_id}` | RF-16 | `OWNER`, `PURCHASING` |
| `GET /price-updates/settings` | RF-20 | `OWNER` |
| `PUT /price-updates/settings` | RF-18, RF-19, RF-21 | `OWNER` |
| `GET /triage/cases` | RF-26, RF-27, RF-28 | `OWNER`, `PURCHASING` |
| `POST /triage/cases/{case_id}/resolution` | RF-29 a RF-33 | `OWNER`, `PURCHASING` |
| `GET /triage/rules` | RF-36 | `OWNER`, `PURCHASING` |
| `DELETE /triage/rules/{rule_id}` | RF-36, RF-37 | `OWNER`, `PURCHASING` |

> **La autorización de estas rutas la reescribió 002-access-control.** La columna de arriba dice
> qué rol tiene que poder hacer cada cosa, que es la decisión de esta feature y no cambió. El
> mecanismo sí: 002 reemplazó los roles por secciones y niveles (`require_section`), y las rutas de
> 001 ya están migradas. La intención por rol es la misma; dónde se declara, no.

`POST /price-updates` es **single-flight**: toma un lock consultivo de Postgres
(`pg_try_advisory_lock`) y devuelve `409` con el id de la corrida en curso si ya hay una (RF-15). No
se resuelve con un `SELECT ... WHERE status = RUNNING`, que tiene carrera entre el chequeo y el
insert. La respuesta `202` lleva el `job_run_id`, y el frontend consulta con él
`GET /price-updates/{job_run_id}` hasta que la corrida termina (RF-16). Es una ruta distinta de
`GET /price-updates/status` a propósito: esa informa la última actualización **exitosa**, así que una
corrida que falló nunca aparecería ahí y quien la pidió no se enteraría de que falló.

## Alternativas descartadas

- **Un cliente HTTP contra los endpoints JSON del portal, en lugar de Playwright.** Sería más rápido
  y más simple. Está **prohibido por el Artículo I** y no se evalúa: es un contrato que nadie nos
  prometió y que puede desaparecer sin aviso.
- **Escribir directo a `core` desde el parser, sin `raw` ni `staging`.** Menos tablas y menos código.
  Se descarta: viola el Artículo III y deja el sistema sin forma de explicar una diferencia con el
  portal, que es justamente lo que el cliente pide cuando dice *"que si algo no se puede resolver
  solo, nos avise"*.
- **Un solo módulo `prices` con todo adentro.** Tentador para una feature sola. Se descarta porque
  `portal`, `ingestion` y `triage` son capacidades que P2 en adelante reusan íntegras: encapsularlas
  en `prices` obligaría a extraerlas después, con las tablas ya en producción.
- **Parsear la tabla HTML de la sección de precios, en lugar de descargar el Excel.** La página
  sirve los cien productos server-rendered, con código, descripción y precio, sin paginar: alcanzaría
  para P1 y evitaría tanto el enlace que caduca a los 45 segundos como cualquier dependencia nueva.
  **Se descarta por decisión del FDE**: el archivo del día es lo que el negocio usa y lo que el
  cliente describe como la vía —*"navegar hasta la sección de precios y descargar el archivo del
  día"*—, y una exportación es un artefacto más estable que el HTML de una pantalla, que cambia cada
  vez que el proveedor toca la interfaz. La tabla renderizada queda como **plan de contingencia** si
  la descarga resulta inviable, y no cuesta nada tenerla identificada.
- **Un evento por fila.** Descartado arriba, en *Eventos de dominio*.
- **`pandas` para leer el archivo del día.** Se descarta: arrastra `numpy` y decenas de megas para
  leer cien filas.
- **`openpyxl` es la biblioteca prevista, todavía sin confirmar.** La sección de precios ofrece un
  botón *"Descargar planilla completa (Excel)"*, así que el formato es casi con seguridad `.xlsx` y
  entra `openpyxl` —sin dependencias transitivas pesadas, es el lector de facto— con `uv add` y su
  lockfile en el mismo commit (`DEP-01`). Si el archivo resultara `.csv` o `.xls` viejo, se usa el
  módulo `csv` de la stdlib o `xlrd` respectivamente. **Nada se agrega a `pyproject.toml` hasta que
  `/portal` baje el archivo y confirme qué es.**

## Riesgos

| Riesgo | Impacto | Cómo se mitiga |
|---|---|---|
| **El contenido del archivo del día no está relevado.** Se confirmó que existe el botón *"Descargar planilla completa (Excel)"*, pero no qué columnas trae ni si coinciden con las de la tabla. | Bloquea el parser y la elección de la biblioteca. | Correr `/portal` sobre la sección de precios **antes** de la tarea del parser: bajar el archivo, fijarlo como fixture y comparar sus columnas con las de la tabla HTML. Es la primera tarea del `/tasks`, no una nota al pie. |
| **El enlace de descarga caduca a los 45 segundos**, y se confirmó que el botón no lleva `href`: el enlace lo genera el JS al hacer clic. | La extracción falla de forma intermitente y difícil de reproducir. | Generar y consumir el enlace en el mismo contexto de Playwright, sin pasos intermedios, y escribir los bytes en `raw` antes de parsear nada. |
| **La cuenta del portal es compartida.** Una persona puede estar usándola cuando corre el job; la sesión se corta por inactividad a las 8 horas. | Extracción fallida sin causa aparente. | La task es idempotente y reintenta; el fallo se registra con su motivo (RF-10) y recién dos seguidos avisan (RF-12). Ningún reintento escribe nada en el portal. |
| **El supuesto de que la lista sólo cambia precios puede ser falso.** | Si fuera falso y el sistema diera de alta solo, ensuciaría el catálogo en silencio. | Ya está mitigado por diseño: lo desconocido se aparta, no se crea. El primer día se ve en la cola de revisión. **No hace falta ninguna decisión técnica adicional.** |
| **La primera corrida visita cien pantallas de historial**, una por producto, contra una cuenta compartida de un tercero. | El proveedor puede leerlo como abuso, o la sesión puede cortarse a mitad. | Las visitas van encoladas de a una y espaciadas, no en paralelo; cada una es idempotente por `content_hash`, así que reanudar no repite trabajo. Es un costo que se paga **una sola vez**: RF-38 corre cuando un producto se registra por primera vez, no en cada actualización. |
| **`triage` es el módulo más grande de la feature** —10 de los 45 requisitos— y es transversal: P2 lo va a necesitar igual. | Sobre-ajustarlo a precios obliga a rehacerlo. | Los casos se modelan con un `kind` y un `payload` JSONB desde el principio, no con columnas de precios. La cola no sabe qué es un precio. |
| **Evolution API es un servicio gratuito de terceros.** | Un aviso que no llega es un aviso que no existe. | El fallo del envío **no aborta** la actualización: `notifications` encola su envío como task en lugar de hacerlo en el handler, y su fallo queda como `JobRun` fallido visible. El aviso también se muestra en pantalla (RF-11), que no depende de WhatsApp. |

## Decisiones posteriores a la convergencia

`/converge` encontró ocho desvíos entre lo firmado y el código
([`checklists/converge.md`](checklists/converge.md)). Dos de ellos se resolvieron con decisiones de
arquitectura, y quedan acá porque el próximo que lea este plan las va a encontrar en el código:

1. **Quién tomó una decisión se guarda con la decisión, no se consulta después** (C5). RF-32 y
   RF-36 prometen "quién lo decidió", y la pantalla mostraba `usuario #3`. `operations.exception` y
   `operations.resolution_rule` ganan `resolved_by_name` y `created_by_name`, que la ruta completa
   con el nombre que trae el token. **No** se resuelve con una proyección de usuarios: una decisión
   es un hecho histórico —quien la tomó no deja de haberla tomado cuando cambia de apellido o se
   va— y una proyección haría que la pantalla dependiera del estado actual de otro módulo. El
   nombre cruza la frontera como string por `dependencies.py`, que es la excepción que el Artículo
   IV ya admite.

2. **La evidencia se commitea antes de interpretarla** (C8). `portal` guardaba el documento y
   publicaba el evento en la misma transacción, así que un archivo que el parser no podía leer se
   iba con el rollback: **toda falla de interpretación destruía su propia evidencia**, justo el día
   —el del cambio de formato del portal— en que esa evidencia es lo único que sirve. Ahora
   `raw.portal_document` se commitea solo, y `normalized_at` marca que el pipeline logró leerlo.

   La consecuencia que obliga a la marca es el reintento: si el salteo siguiera preguntando *"¿ya
   tengo este archivo?"*, el segundo intento encontraría el documento guardado, no haría nada y
   **cerraría la corrida como exitosa sobre un archivo que nadie leyó** — exactamente el silencio
   que RF-41 existe para romper. El salteo pregunta *"¿ya lo leí?"*.

   Se evaluó poner la marca en `staging`, que es de quien normaliza. Se descartó porque `portal` no
   puede leer una tabla de `ingestion` para decidir si saltea, y porque la marca registra un hecho
   que `portal` **sí** observa: su propio `publish` volvió sin excepción, que es el contrato del
   bus (`GEN-09`).

## Contexto de traspaso

**Para el Developer** — Empezá por `/portal` sobre la sección de precios: sin saber el formato del
archivo no se puede escribir el parser, y todo lo demás depende de él. Después construí de abajo
hacia arriba —`portal` → `ingestion` → `catalog` → `triage` → `notifications`—, porque cada uno
publica lo que el siguiente consume y así podés probar cada eslabón contra un evento a mano.

**Lo que NO tenés que tocar:** `operations.JobRun` y `operations.Parameter` ya existen y alcanzan;
el composition root sólo se toca para registrar routers y handlers.

**Decisiones ya tomadas, no las rediscutas:** los módulos se hablan sólo por los dieciséis eventos de la
tabla de arriba; `ingestion` y `catalog` mantienen proyecciones propias en vez de leerle las tablas a
nadie; el single-flight de RF-15 es un advisory lock, no un `SELECT` de estado; los dos parámetros
van en `operations.parameter`, no en una tabla nueva. Si alguna de las cuatro te resulta incómoda de
implementar, **es señal de que la frontera está mal trazada y hay que escalar al Backend-Architect**,
no de que convenga un import.

**Para el Tester** — Lo que puede romperse de verdad no es el camino feliz: es la cuarentena y la
reaplicación de reglas. Los casos borde que importan:

- El **historial importado y el acumulado se pisan en el borde** (RF-40): traer dos veces el historial
  de un producto tiene que dejar la misma cantidad de puntos. Probalo corriendo la importación dos
  veces seguidas.
- La **primera** lista carga el padrón (RF-02) y la **segunda** ya aparta lo desconocido (RF-07). Es
  una diferencia de comportamiento entre dos corridas consecutivas y es fácil de romper sin notarlo.
- El **mismo caso en tres consultas seguidas deja un pendiente, no tres** (RF-35).
- **Anular una regla devuelve a la cola lo que esa regla venía resolviendo** (RF-37): es el único
  requisito que corre para atrás.
- **Dos actualizaciones simultáneas**: una a mano mientras corre la programada (RF-15). Probalo con
  concurrencia real, no en serie.
- **La variación mensual con mes sin datos** y el destacado en el borde exacto del umbral: 10% no es
  "más del 10%".

El parser se testea **contra archivos fijados** —el ejemplo que traiga `/portal`— y nunca contra
SIGProv en vivo (`TEST-03`, Blocker). La task de extracción necesita su test de idempotencia
apoyado en `content_hash` (`TEST-04`): correrla dos veces con el mismo archivo no puede duplicar
nada.

**Para el Code-Reviewer** — Las convenciones en juego, por orden de riesgo:

- **`GEN-02`, `GEN-03`, `GEN-08`, `GEN-09`** — cinco módulos nuevos es la mayor superficie de riesgo
  de frontera que tuvo el proyecto. Mirá primero los imports de cada `service.py` y de cada
  `handlers.py`, y que ningún evento lleve un modelo de SQLAlchemy.
- **`PY-09`** — diez rutas nuevas, todas con autorización declarada. El test lo frena, pero revisá
  que el rol declarado sea el que la spec dice: `POST /price-updates` es `OWNER` y `PURCHASING`,
  **no** `SALES`, porque le golpea la puerta a un sistema de un tercero.
- **`DB-01`** — tablas en cuatro schemas; que `alembic check` quede limpio y que cada modelo nuevo
  esté en `app/models.py` en el mismo commit que su migración.
- **Artículo III** — la escritura sobre lo extraído ya la frena `tests/architecture/test_raw_immutability.py`; lo que sí hay que mirar a ojo es que
  **el historial pase por `staging` igual que la lista**: es el camino que ya se saltó una vez en
  este mismo plan, y saltárselo no rompe ningún test, sólo deja sin lugar a la cuarentena de RF-39. Es una
  ausencia, y las ausencias son lo que un review no ve si no las busca.
- **Artículo VII** — que las credenciales no aparezcan en ningún log ni en el `detail` de ninguna
  excepción que salga del módulo `portal`.
