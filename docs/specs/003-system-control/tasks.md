# Control propio del sistema — Tareas

<!--
  ARTEFACTO INTERNO. Cada tarea mapea a una skill de agents/skills/ y es lo bastante
  chica como para terminarse de una sentada.
-->

**Feature:** 003-system-control · **Plan:** `plan.md` · **Tareas:** 30

## Orden

Agrupadas por historia, en el orden de prioridad de la spec. Dentro de cada una:
migración → backend → frontend → tests.

> **Al terminar H1 hay algo entregable de verdad**: el dueño abre una pantalla, ve los siete
> parámetros del sistema con su valor y su rango, cambia uno y queda registrado quién lo cambió. Las
> cuatro historias siguientes agregan sobre eso; ninguna es requisito para que la primera funcione.

> **Dos tareas de H1 construyen la bitácora, que es materia de H2.** No es un error de agrupación:
> RF-08 exige registrar el cambio de un parámetro, así que la tabla y su trigger tienen que existir
> antes de que H1 esté terminada. H2 construye encima la consulta, los filtros y la pantalla.

### H1 — El dueño ajusta los parámetros sin pedirle nada a nadie

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 1 | `app/shared/sections.py` y `app/shared/parameters.py`: el enum de secciones del negocio y el catálogo declarativo con los siete parámetros, su valor inicial, su rango, su unidad y las dos frases en español que el dueño lee. Con su test: claves únicas y cada valor inicial dentro de su propio rango. | `add_backend_feature` | Developer | RF-04, RF-05, RF-06 |
| 2 | Migración: `operations.audit_entry` con sus enums, sus cuatro índices y **el trigger que rechaza `UPDATE` y `DELETE`**. `AuditEntry` entra a `app/models.py` en el mismo commit. | `add_database_migration` | Developer | RF-08 |
| 3 | `operations`: repositorio de la bitácora con `insert`, `list` y `list_for_entity`, y **sin** `update` ni `delete`. | `add_backend_feature` | Developer | RF-08 |
| 4 | `operations`: `list_parameters()` devuelve el catálogo con el valor vigente encima —no las filas de la tabla— y `get_parameter_value()` cae al valor inicial del catálogo. Se eliminan `DEFAULT_INTERVAL_HOURS` y `DEFAULT_HIGHLIGHT_THRESHOLD` de `service.py`: el catálogo pasa a ser su fuente única. | `add_backend_feature` | Developer | RF-01, RF-04 |
| 5 | `operations`: `set_parameters()` valida contra el catálogo —clave desconocida y valor fuera de rango se rechazan, y el mensaje dice entre qué valores tiene que estar—, escribe su fila de bitácora y publica `BusinessParameterChanged`. | `add_backend_feature` | Developer | RF-02, RF-06, RF-07, RF-08 |
| 6 | Rutas `GET` y `PUT /operations/parameters`, sólo `OWNER`. | `add_backend_feature` | Developer | RF-01, RF-02, RF-03, RF-05 |
| 7 | Pantalla `(private)/configuracion`: los siete parámetros con su valor vigente, la frase de qué cambia y su rango, **señalando cuáles todavía no tienen efecto** —los cinco cuya funcionalidad no está construida— a partir de `ParameterSpec.consumed_by`. **Baja de `(private)/precios/configuracion/`**, reemplazada por una redirección al panel: la regla de negocio firmada prohíbe que un parámetro viva en la pantalla de la funcionalidad que lo usa. | `add_frontend_feature` | Developer | RF-01, RF-03, RF-05 |
| 8 | Tests de H1: el valor inicial de un parámetro que no tiene fila en la tabla, los bordes exactos de cada rango, una clave que no está en el catálogo, que compras y ventas reciben 403 en las dos rutas, y que la pantalla distingue los parámetros que todavía no tienen efecto. | `add_tests` | Tester | RF-01, RF-02, RF-03, RF-04, RF-05, RF-06, RF-07, RF-08 |

### H2 — Cada cambio manual queda registrado

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 9 | Evento `ManualChangeRecorded` en `app/shared/events/catalog.py` con su enum `AuditAction`, y el handler de `operations` que lo convierte en fila. Corre en la transacción del publicador: si falla, aborta la edición (`GEN-09`). | `add_backend_feature` | Developer | RF-09, RF-10, RF-12 |
| 10 | `identity/dependencies.py`: `visible_sections()`, que responde qué secciones ve quien llama —el dueño, todas—. **Es el único archivo de `identity` que se toca en toda la feature.** | `add_backend_feature` | Developer | RF-19 |
| 11 | `operations`: consulta de la bitácora con filtro por persona, por rango de fechas y por sección, ordenada de más nueva a más vieja. | `add_backend_feature` | Developer | RF-13, RF-14, RF-18, RF-19 |
| 12 | Rutas `GET /operations/audit` y `GET /operations/audit/{entity_type}/{entity_id}`. Autenticadas y filtradas por sección, **no** de dueño: RF-19 dice lo contrario. | `add_backend_feature` | Developer | RF-13, RF-14, RF-15, RF-18, RF-19 |
| 13 | Pantalla `(private)/historial`: la lista con sus filtros, el motivo de cada cambio, y el acceso desde un dato corregido a su propio historial sin pasar por otra pantalla. | `add_frontend_feature` | Developer | RF-12, RF-13, RF-14, RF-15, RF-18, RF-19 |
| 14 | Tests de H2: **`UPDATE` y `DELETE` por SQL directo contra la base**, esperando que la rechace; el handler que falla y deja la edición sin efecto; y el filtro por sección con tres usuarios reales, uno por rol. | `add_tests` | Tester | RF-09, RF-10, RF-11, RF-12, RF-13, RF-14, RF-15, RF-16, RF-17, RF-18, RF-19 |

### H3 — Un solo lugar para cargar y corregir

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 15 | `frontend/lib/operations/actions.ts`: el registro tipado de acciones, cada una con su etiqueta, su destino y las secciones que la habilitan. **Nace con las acciones que ya existen, no sólo con las de esta feature**: pedir la lista de precios ahora y resolver un caso de la cola de revisión —las dos de compras, `POST /price-updates` y `POST /triage/cases/{case_id}/resolution`— más las dos que agrega la 003. Sin las dos primeras, compras entra a la pantalla y no ve nada. Cada feature futura agrega su línea acá. | `add_frontend_feature` | Developer | RF-20, RF-21 |
| 16 | Pantalla `(private)/acciones`: las acciones filtradas por la sesión, y el resultado de cada una —aplicada o fallida— visible para quien la ejecutó. | `add_frontend_feature` | Developer | RF-20, RF-21, RF-22 |
| 17 | Tests de H3: la misma pantalla vista por compras y por ventas devuelve conjuntos distintos **y ninguno de los dos vacío**, y una acción que falla se ve fallar. | `add_tests` | Tester | RF-20, RF-21, RF-22 |

### H4 — Corregir un valor sin borrar lo que decía

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 18 | `app/shared/corrections.py`: el mixin de columnas de corrección, el enum `CorrectionStatus` y el catálogo de los cinco motivos en español. | `add_backend_feature` | Developer | RF-11, RF-25 |
| 19 | Migración: `core.correction` con su índice único parcial sobre `(entity_type, entity_id, field)` para las no anuladas. `Correction` entra a `app/models.py` en el mismo commit. | `add_database_migration` | Developer | RF-25, RF-26, RF-27 |
| 20 | `catalog`: aplicar una corrección sobre **cualquier campo** de un producto o de su precio, exigiendo motivo, conservando `portal_value` sin tocar y publicando `ManualChangeRecorded`. | `add_backend_feature` | Developer | RF-11, RF-23, RF-25 |
| 21 | Ruta `POST /catalog/products/{product_id}/corrections`, `OWNER` y `SALES`: el catálogo y los precios son de ventas según el mapa de secciones. | `add_backend_feature` | Developer | RF-23, RF-24 |
| 22 | `catalog`: detectar el conflicto al aplicar un precio nuevo —comparar contra `portal_value`, **no** pisar la corrección, marcar `CONFLICTED`— y publicar `CorrectionConflicted`. | `add_backend_feature` | Developer | RF-28 |
| 23 | `notifications`: handler de `CorrectionConflicted` que avisa al dueño, con el envío encolado como task para que su fallo no aborte la actualización. | `add_backend_feature` | Developer | RF-29 |
| 24 | Ruta `GET /operations/corrections/reasons`: la lista sale de donde se valida, no del frontend. | `add_backend_feature` | Developer | RF-11 |
| 25 | Frontend: el diálogo de corrección con la lista de motivos y el detalle escrito, y el dato corregido señalado a simple vista con su valor original al lado en la tabla de precios. | `add_frontend_feature` | Developer | RF-11, RF-26, RF-27 |
| 26 | Tests de H4: las **tres corridas del conflicto** —el portal informa lo mismo, informa algo distinto, vuelve a informar lo distinto—; el motivo obligatorio; y corregir un campo que no es un importe. | `add_tests` | Tester | RF-11, RF-23, RF-24, RF-25, RF-26, RF-27, RF-28, RF-29 |

### H5 — Deshacer una corrección equivocada

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 27 | `catalog`: anular una corrección restituyendo `portal_value`, marcando la fila `REVERTED` con quién y cuándo —no se borra— y publicando `ManualChangeRecorded`. Rechaza el pedido sobre un dato que no vino del portal. | `add_backend_feature` | Developer | RF-30, RF-31, RF-32, RF-33 |
| 28 | Ruta `DELETE /catalog/corrections/{correction_id}`, sólo `OWNER`. | `add_backend_feature` | Developer | RF-30, RF-33 |
| 29 | Frontend: la acción de anular, alcanzable desde el historial y **ausente** sobre un dato cargado enteramente a mano. | `add_frontend_feature` | Developer | RF-30, RF-33 |
| 30 | Tests de H5: que restituya el valor del portal y **no** el anterior después de dos correcciones seguidas, y que anular sobre un dato sin corrección falle limpio. | `add_tests` | Tester | RF-30, RF-31, RF-32, RF-33 |

## Cobertura de requisitos

| Requisito | Tareas | Test |
|-----------|--------|------|
| RF-01 | 4, 6, 7 | 8 |
| RF-02 | 5, 6 | 8 |
| RF-03 | 6, 7 | 8 |
| RF-04 | 1, 4 | 8 |
| RF-05 | 1, 6, 7 | 8 |
| RF-06 | 1, 5 | 8 |
| RF-07 | 5 | 8 |
| RF-08 | 2, 3, 5 | 8 |
| RF-09 | 9 | 14 |
| RF-10 | 9 | 14 |
| RF-11 | 18, 20, 24, 25 | 26 |
| RF-12 | 9, 13 | 14 |
| RF-13 | 11, 12, 13 | 14 |
| RF-14 | 11, 12, 13 | 14 |
| RF-15 | 12, 13 | 14 |
| RF-16 | 2, 3 | 14 |
| RF-17 | 2, 3 | 14 |
| RF-18 | 11, 12, 13 | 14 |
| RF-19 | 10, 11, 12, 13 | 14 |
| RF-20 | 15, 16 | 17 |
| RF-21 | 15, 16 | 17 |
| RF-22 | 16 | 17 |
| RF-23 | 20, 21 | 26 |
| RF-24 | 21 | 26 |
| RF-25 | 18, 19, 20 | 26 |
| RF-26 | 19, 25 | 26 |
| RF-27 | 19, 25 | 26 |
| RF-28 | 22 | 26 |
| RF-29 | 23 | 26 |
| RF-30 | 27, 28, 29 | 30 |
| RF-31 | 27 | 30 |
| RF-32 | 27 | 30 |
| RF-33 | 27, 28, 29 | 30 |

## Notas para `/converge`

**Decidido por el humano el 2026-08-29.** Dos criterios de aceptación **no se van a poder marcar con
su letra** al cerrar esta feature, y no es alcance incumplido:

- **RF-23** se verifica en la spec corrigiendo *"el número de comprobante de una factura escaneada"*.
- **RF-24**, con *"Julián no puede corregir el total de una factura de compra"*.

No hay módulo de facturas: es la **004**, todavía en borrador. La tarea 20 construye el mecanismo
genérico —cualquier campo, no sólo importes— y la 26 lo verifica con el dato equivalente que sí
existe: la **descripción** de un producto, que no es un importe, y un usuario de compras al que se le
niega corregir un producto. Los dos criterios con su redacción literal se cierran en la 004.

La otra ausencia deliberada: **cinco de los siete parámetros no los lee ninguna funcionalidad
todavía** —P8, P11, P12, P6 y la 002—. El panel los muestra, se validan y se guardan; el efecto
llega con su feature. Por decisión del 2026-08-29 la pantalla **los señala como todavía sin efecto**,
a partir de `ParameterSpec.consumed_by`: el dueño los puede fijar desde el día uno sin creer que ya
mueven algo.

Y el actor: **H2 y H4 están narradas desde Marcela, que en esta feature no tiene nada que corregir**
—los precios son de ventas—. Se decidió seguir con la 003 y anotarlo en la spec; las dos historias se
verifican con el dueño y con Julián, y Marcela las usa sobre sus propios datos con la 004.
