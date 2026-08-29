# Actualización de la lista de precios — Tareas

<!--
  ARTEFACTO INTERNO. Cada tarea mapea a una skill de agents/skills/ y es lo bastante
  chica como para terminarse de una sentada.
-->

**Feature:** 001-price-list-update · **Plan:** `plan.md` · **Tareas:** 49

**Estado** — las 49 tareas ✅.

| Paso | Rol | Fecha | Resultado |
|---|---|---|---|
| `/implement` | Developer | 2026-08-29 | Las 49 tareas, con dos parciales (21 y 34) |
| `add_tests` | Tester | 2026-08-29 | **Las 49 completas.** Suite en 407 tests, cobertura 95.29% |

Lo que sigue abierto está en *Lo que falta*, y las dos preguntas que la suite le devolvió a la
spec, en [`checklists/tests.md`](checklists/tests.md).

## Orden

Agrupadas por historia, en el orden de prioridad de la spec. Dentro de cada una:
migración → backend → frontend → tests.

> **Al terminar H1 hay algo entregable de verdad**: el sistema entra al portal solo, trae la lista
> y la muestra en pantalla. Las siete historias siguientes agregan sobre eso, ninguna es requisito
> para que la primera funcione.


### H1 — Los precios se actualizan solos

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 1 ✅ | Relevar el login, la navegación a la sección de precios y cómo se genera el enlace de descarga que caduca a los 45 s. **El formato del archivo ya está relevado** y sus fixtures están en `backend/tests/fixtures/portal/`. | `inspect_portal` | Developer | — |
| 2 ✅ | Migración: schemas `raw`, `staging` y `core`; tablas `raw.portal_document` con `content_hash` único, `staging.price_row`, `core.product` y `core.product_price`. | `add_database_migration` | Developer | RF-02, RF-03, RF-05, RF-08 |
| 3 ✅ | Módulo `portal`: cliente Playwright con login y descarga del archivo del día. Credenciales sólo del entorno, sin `routes.py`. | `add_backend_feature` | Developer | RF-05 |
| 4 ✅ | Repositorio de `raw`: expone `insert` y `get`, **no** `update` ni `delete`. Publica `PriceListExtracted`. | `add_backend_feature` | Developer | RF-05 |
| 5 ✅ | Módulo `ingestion`: parser del archivo → `staging.price_row`, con cuarentena por fila. Publica `PriceListNormalized` y `PriceRowsQuarantined`. | `add_backend_feature` | Developer | RF-06 |
| 6 ✅ | Módulo `catalog`: siembra del padrón con la primera lista y precio vigente de cada producto conocido. | `add_backend_feature` | Developer | RF-02, RF-03 |
| 7 ✅ | `catalog`: apartar el producto desconocido y conservar el último precio del que dejó de figurar. Publica `UnknownProductsObserved` y `KnownProductsMissing`. | `add_backend_feature` | Developer | RF-07, RF-08 |
| 8 ✅ | Task de extracción programada y su entrada de beat, idempotente por `content_hash`. | `add_celery_task` | Developer | RF-01 |
| 9 ✅ | Endpoint `GET /prices` con autorización `OWNER` · `PURCHASING` · `SALES`. | `add_backend_feature` | Developer | RF-04 |
| 10 ✅ | Pantalla `(private)/precios`: código, descripción y precio vigente. | `add_frontend_feature` | Developer | RF-04 |
| 11 ✅ | Tests de H1: parser contra los dos fixtures, los seis casos de cuarentena, idempotencia por hash y la diferencia entre la primera y la segunda corrida. | `add_tests` | Tester | RF-01, RF-02, RF-03, RF-04, RF-05, RF-06, RF-07, RF-08 |

### H2 — Saber que la actualización sigue viva

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 12 ✅ | `operations`: detectar dos consultas programadas seguidas sin éxito y publicar `PriceUpdateStalled` / `PriceUpdateRecovered`, una sola vez por interrupción. | `add_backend_feature` | Developer | RF-10, RF-13 |
| 13 ✅ | Módulo `notifications`, mínimo: un canal, un destinatario. Actualiza el mapa de módulos de `ARCHITECTURE.md`. | `add_backend_feature` | Developer | RF-12 |
| 14 ✅ | Cliente de Evolution API para WhatsApp, con el envío **encolado como task**: su fallo no aborta la actualización. | `add_integration` | Developer | RF-12 |
| 15 ✅ | Endpoint `GET /price-updates/status`. | `add_backend_feature` | Developer | RF-09, RF-11 |
| 16 ✅ | Frontend: fecha y hora de la última actualización exitosa, y el aviso visible cuando quedó vieja. | `add_frontend_feature` | Developer | RF-09, RF-11 |
| 17 ✅ | Tests de H2: el aviso que no se repite, y la pantalla que avisa aunque WhatsApp falle. | `add_tests` | Tester | RF-09, RF-10, RF-11, RF-12, RF-13 |

### H3 — Traer la lista ahora, sin esperar

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 18 ✅ | Endpoint `POST /price-updates`: advisory lock de Postgres, `409` si ya hay una en curso, `202` con el `job_run_id`, y registro de quién la pidió. | `add_backend_feature` | Developer | RF-14, RF-15, RF-17 |
| 19 ✅ | Endpoint `GET /price-updates/{job_run_id}`: el resultado de **esa** corrida, exitosa o fallida. Distinto de `/status`, que sólo informa la última exitosa. | `add_backend_feature` | Developer | RF-16 |
| 20 ✅ | Frontend: botón de actualizar ahora; consulta la corrida con su id hasta que termina y muestra si trajo la lista o falló. | `add_frontend_feature` | Developer | RF-14, RF-16 |
| 21 ✅ | Tests de H3, **con concurrencia real**: dos pedidos simultáneos, no en serie; y una corrida fallida que quien la pidió sí ve. | `add_tests` | Tester | RF-14, RF-15, RF-16, RF-17 |

### H4 — El dueño decide cada cuánto y qué es una suba grande

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 22 ✅ | Migración de datos: sembrar `price_update.interval_hours` en `12` y `price_update.highlight_threshold_pct` en `10`. | `add_database_migration` | Developer | RF-20 |
| 23 ✅ | Endpoints `GET` y `PUT /price-updates/settings`, sólo `OWNER`. | `add_backend_feature` | Developer | RF-18, RF-19 |
| 24 ✅ | Reprogramar la consulta siguiente cuando cambia la frecuencia. | `add_celery_task` | Developer | RF-21 |
| 25 ✅ | Frontend: pantalla de configuración de los dos parámetros. | `add_frontend_feature` | Developer | RF-18, RF-19 |
| 26 ✅ | Tests de H4: el valor inicial mientras no se cambió, y la frecuencia nueva rigiendo desde la consulta siguiente. | `add_tests` | Tester | RF-18, RF-19, RF-20, RF-21 |

### H5 — La evolución de cada producto

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 27 ✅ | Migración: `core.price_point` con `source` y única `(product_id, changed_at)`, y `staging.price_history_row`. | `add_database_migration` | Developer | RF-22, RF-38, RF-40 |
| 28 ✅ | `catalog`: un punto de historial por cambio de precio, no por consulta. Publica `ProductsRegistered`. | `add_backend_feature` | Developer | RF-22, RF-38 |
| 29 ✅ | `portal`: navegación y parser de la pantalla de historial de un producto → `raw`. Publica `ProductHistoryExtracted`. | `add_backend_feature` | Developer | RF-38 |
| 30 ✅ | `ingestion`: tipar cada punto hacia `staging.price_history_row` —el precio acá **viene como texto**, `$25.308`— y apartar el ilegible. Publica `PriceHistoryNormalized` y `PriceHistoryRowsQuarantined`. | `add_backend_feature` | Developer | RF-38, RF-39 |
| 31 ✅ | Task por producto recién registrado, **encolada y espaciada**, disparada desde el handler de `ProductsRegistered`. | `add_celery_task` | Developer | RF-38 |
| 32 ✅ | `catalog`: variación entre el precio vigente y el último precio del mes calendario anterior. | `add_backend_feature` | Developer | RF-24 |
| 33 ✅ | Endpoint `GET /prices/{product_id}/history` y pantalla de detalle del producto. | `add_feature` | Developer | RF-23, RF-24 |
| 34 ✅ | Tests de H5: importar dos veces deja los mismos puntos, un historial ilegible no borra el precio vigente, y la variación con un mes sin datos. | `add_tests` | Tester | RF-22, RF-23, RF-24, RF-38, RF-39, RF-40 |

### H6 — Las subas que hay que mirar

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 35 ✅ | `catalog`: destacar comparando contra `previous_price` y el umbral configurado. | `add_backend_feature` | Developer | RF-25 |
| 36 ✅ | Frontend: los destacados en la lista de precios. | `add_frontend_feature` | Developer | RF-25 |
| 37 ✅ | Tests de H6, **con el borde exacto**: al 10%, `$100 → $115` queda destacado y `$100 → $110` no. | `add_tests` | Tester | RF-25 |

### H7 — Lo que no se pudo resolver queda a la vista

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 38 ✅ | Migración: `operations.exception` con índice único parcial sobre `fingerprint` para los pendientes. | `add_database_migration` | Developer | RF-26 |
| 39 ✅ | Módulo `triage`: la cola, con `kind` y `payload` genéricos, y los handlers de los **cuatro** eventos que la alimentan. | `add_backend_feature` | Developer | RF-26, RF-28 |
| 40 ✅ | Endpoint `GET /triage/cases` y el conteo de apartadas al cerrar la corrida. | `add_backend_feature` | Developer | RF-26, RF-27 |
| 41 ✅ | Frontend: pantalla de revisión, cada caso con su motivo. | `add_frontend_feature` | Developer | RF-26, RF-27, RF-28 |
| 42 ✅ | Tests de H7: una lista con una fila rota y un producto desconocido no frena al resto, y los cuatro motivos llegan a la cola. | `add_tests` | Tester | RF-26, RF-27, RF-28 |

### H8 — Resolver lo apartado, y que no vuelva a preguntar lo mismo

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 43 ✅ | Migración: `operations.resolution_rule` y la proyección `staging.resolution_rule`. | `add_database_migration` | Developer | RF-34, RF-36 |
| 44 ✅ | `triage`: resolver los tres motivos, registrar qué se decidió, quién y cuándo, y sacar el caso de los pendientes. Publica `QuarantineCaseResolved`. | `add_backend_feature` | Developer | RF-29, RF-32, RF-33 |
| 45 ✅ | `catalog`: handler que incorpora el producto, le fija el precio o lo da por discontinuado según la decisión. | `add_backend_feature` | Developer | RF-30, RF-31 |
| 46 ✅ | `ingestion`: proyección de reglas, reaplicación automática y un solo pendiente por `fingerprint`. | `add_backend_feature` | Developer | RF-34, RF-35 |
| 47 ✅ | `triage`: reglas visibles con su autor y anulables por `OWNER` y `PURCHASING`. Publica `QuarantineRuleRevoked`, que devuelve los casos a la cola. | `add_backend_feature` | Developer | RF-36, RF-37 |
| 48 ✅ | Frontend: resolver un caso según su motivo, y la pantalla de reglas guardadas. | `add_frontend_feature` | Developer | RF-29, RF-30, RF-31, RF-32, RF-33, RF-36 |
| 49 ✅ | Tests de H8: el mismo caso tres veces deja un pendiente, y anular una regla devuelve sus casos a revisión. | `add_tests` | Tester | RF-29, RF-30, RF-31, RF-32, RF-33, RF-34, RF-35, RF-36, RF-37 |

## Cobertura de requisitos

<!-- Derivada de las tareas de arriba, no escrita a mano. -->

| Requisito | Tareas | Test |
|-----------|--------|------|
| RF-01 | 8 | 11 |
| RF-02 | 2, 6 | 11 |
| RF-03 | 2, 6 | 11 |
| RF-04 | 9, 10 | 11 |
| RF-05 | 2, 3, 4 | 11 |
| RF-06 | 5 | 11 |
| RF-07 | 7 | 11 |
| RF-08 | 2, 7 | 11 |
| RF-09 | 15, 16 | 17 |
| RF-10 | 12 | 17 |
| RF-11 | 15, 16 | 17 |
| RF-12 | 13, 14 | 17 |
| RF-13 | 12 | 17 |
| RF-14 | 18, 20 | 21 |
| RF-15 | 18 | 21 |
| RF-16 | 19, 20 | 21 |
| RF-17 | 18 | 21 |
| RF-18 | 23, 25 | 26 |
| RF-19 | 23, 25 | 26 |
| RF-20 | 22 | 26 |
| RF-21 | 24 | 26 |
| RF-22 | 27, 28 | 34 |
| RF-23 | 33 | 34 |
| RF-24 | 32, 33 | 34 |
| RF-25 | 35, 36 | 37 |
| RF-26 | 38, 39, 40, 41 | 42 |
| RF-27 | 40, 41 | 42 |
| RF-28 | 39, 41 | 42 |
| RF-29 | 44, 48 | 49 |
| RF-30 | 45, 48 | 49 |
| RF-31 | 45, 48 | 49 |
| RF-32 | 44, 48 | 49 |
| RF-33 | 44, 48 | 49 |
| RF-34 | 43, 46 | 49 |
| RF-35 | 46 | 49 |
| RF-36 | 43, 47, 48 | 49 |
| RF-37 | 47 | 49 |
| RF-38 | 27, 28, 29, 30, 31 | 34 |
| RF-39 | 30 | 34 |
| RF-40 | 27 | 34 |
| RF-41 | 5 | 11 |
| RF-42 | 5, 7 | 11 |
| RF-43 | 30 | 34 |
| RF-44 | 12, 13, 14 | 17 |
| RF-45 | 39, 44 | 49 |


## Lo que falta

Escrito por el `Developer` al terminar `/implement` y actualizado por el `Lead` cuando el `Tester`
cerró su parte. Nada de lo que queda bloquea el gate.

| Qué | Estado |
|---|---|
| **Tarea 21** — dos pedidos simultáneos con concurrencia real | **Cerrado.** `tests/integration/features/test_price_update_concurrency.py` abre sus propias conexiones, commitea de verdad y limpia lo que creó. Además del `gather`, fija el mecanismo de forma determinista: con el lock tomado y **sin fila `RUNNING` todavía visible**, el segundo llamador recibe `409` igual — que es la ventana por la que un `SELECT ... WHERE status = RUNNING` pasaría de largo |
| **Tarea 34** — variación mensual con un mes sin datos | **Cerrado.** `tests/integration/features/test_price_variation.py`, con el criterio que fija `data-model.md`: el último punto anterior al primer día del mes corriente, así que un mes vacío usa el precio que el producto venía cargando, y sólo la ausencia total de puntos devuelve `None` |
| **Cuerpos de las tasks de Celery** | **Cerrado.** `tests/integration/features/test_price_tasks.py` los ejercita por su cuerpo async, que es lo que prescribe `add_celery_task`: idempotencia (`TEST-04`), el fallo que se registra recién al agotar los reintentos, y el archivo duplicado que **igual cierra la corrida** |
| **Cliente Playwright** (`portal/client.py`, 39%) | **Abierto a propósito.** Lo no cubierto es navegación real contra SIGProv, y `TEST-03` lo prohíbe. Lo que sí está fijado es la garantía del Artículo VII: un error de Playwright nunca sale del módulo con la URL de login ni la credencial adentro |
| **Dos métodos sin llamadores** en `ingestion/repository.py` | **Abierto** — `rows_of_batch` y `history_rows_of_product` no los usa nadie. Lo mira el `Code-Reviewer`; no se testearon a propósito |

## Decisiones tomadas durante la implementación

Las que se apartan de lo que dice `plan.md`, con su motivo. Ninguna cambia el alcance.

1. **`PriceListExtracted` y `ProductHistoryExtracted` llevan también el contenido del documento.**
   El plan les daba `raw_document_id` y `content_hash`. `raw.portal_document` es de `portal`, y
   `ingestion` no puede importarlo para leer los bytes (Artículo IV): el evento los lleva como valor
   plano. La fila en `raw` sigue siendo la evidencia (Artículo III); el payload es cómo el paso
   siguiente recibe su entrada sin cruzar la frontera.
2. **`PriceListNormalized` lleva `seen_codes`.** Sin eso, `catalog` no puede distinguir un producto
   que dejó de venir (RF-28) de uno cuya fila vino ilegible: las filas en cuarentena no viajan en
   `rows`, y el producto quedaba reportado dos veces, como fila rota y como faltante.
3. **`KnownProductsMissing` lleva código y descripción, no sólo `product_ids`.** `triage` no puede
   preguntarle a `catalog` qué producto es un id, y la pantalla de revisión tiene que mostrar el
   caso con su motivo (RF-26).
4. **`QuarantineCaseResolved` y `QuarantineRuleRevoked` llevan `matcher` y `decision`.** Es lo que
   permite que anular una regla deshaga exactamente lo que hizo (RF-37) sin que `catalog` le lea la
   tabla a `triage`.
5. **`JobRunSucceeded` es un evento nuevo**, simétrico del `JobRunFailed` que ya existía. La task de
   extracción es la única que sabe que llegó al final, y no puede llamar a `operations` para
   decirlo. Con esto una corrida también se cierra cuando el archivo del día resultó duplicado.
6. **`BusinessParameterChanged` es un evento nuevo**, y `catalog` mantiene su proyección
   `core.catalog_setting`. El umbral de destacado es un parámetro de `operations`, y `catalog` es
   quien lo aplica: es el costo que el Artículo IV dice que hay que aceptar.
7. **`core.product` tiene `registered_by_rule_id`.** Es lo que hace exacto el deshacer de RF-37: se
   des-registra el producto que esa regla incorporó, y ninguno más.
8. **La consulta programada es un latido fijo cada 15 minutos** (`operations.tick_price_update`) que
   lee `price_update.interval_hours` y decide si corresponde consultar. Es lo que hace que un cambio
   de frecuencia rija desde la consulta siguiente (RF-21) sin reescribir el schedule de beat.
9. **`operations` dispara la extracción por nombre de task**, no importando `portal`. Un string
   sobre el broker es el mismo tipo de contrato que un evento.
10. **`autodiscover_tasks` dejó de ser `force=True`.** Con descubrimiento eager, un servicio que
    pide `celery_app` para despachar una task por nombre volvía a importar el `tasks.py` de su
    propio módulo a medio inicializar.
