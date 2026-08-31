# Control propio del sistema — Tareas

<!--
  ARTEFACTO INTERNO. Cada tarea mapea a una skill de agents/skills/ y es lo bastante
  chica como para terminarse de una sentada.
-->

**Feature:** 003-system-control · **Plan:** `plan.md` · **Tareas:** 30

## Estado

**Implementadas el 2026-08-30**, en la rama `feat/003-system-control`, y **mergeadas a `main` en el
PR #20** (`a2d7201`).

- ✅ **30 de 30** — 25 del `Developer` y 5 del `Tester`, las cinco historias completas.
- ✅ **10 defectos** que la suite destapó, todos arreglados. Están en **Los diez defectos que
  encontró la suite**, más abajo, con su arreglo.

La suite del día del merge: **879 passed · 1 skipped · 0 xfailed**, cobertura 95.25%.

> **Dónde quedó la cadena (reescrito el 2026-08-30, ya con los dos gates corridos).** Esta sección
> decía que faltaban los dos gates del final y que la rama no tenía ni un commit. Las dos cosas
> dejaron de ser ciertas el mismo día, y lo que sigue es lo que pasó después — que es la parte que
> le sirve a quien llegue mañana.
>
> - **`/converge`** (`Lead`) — corrió y dejó su informe en [`converge.md`](converge.md). Veredicto
>   **🔴 deriva mayor**: 45 hallazgos, 7 mayores y 38 menores, sobre una feature que **ya estaba
>   mergeada**, así que lo que el veredicto movió no fue si entraba sino qué había que resolver
>   antes de desplegar y archivar. Los siete mayores eran cuatro problemas; el humano eligió
>   implementar en vez de enmendar la spec, y los cerró `e5eb56f` junto con dos más que aparecieron
>   al cerrarlos.
> - **`/review-feature`** (`Code-Reviewer`) — corrió después del converge y devolvió **1 Blocker,
>   13 Major y 34 Minor**.
>   - El **Blocker** es el que más caro salía, y ningún test lo veía: `apply_correction` y
>     `revert_correction` flusheaban, publicaban y **nunca commiteaban**, así que las dos rutas de
>     escritura que existen para H4 y H5 contestaban 200 y no persistían nada. Lo cerró `c7c7f68`,
>     con el test estático que recorre todos los verbos de escritura del repositorio y falla si el
>     servicio detrás de uno escribe sin commitear.
>   - Los **13 Major** eran ocho defectos vistos por reviewers distintos. Los cerró `9d413fe`.
>   - Los **34 Minor** son el último tramo: hallazgos chicos, uno por uno, y es lo que cierran esta
>     página y los diagramas.
>
> Suite medida hoy con `make quality`, que es de donde sale `backend/app/quality.json` y la pantalla
> de estado: **1389 passed · 8 skipped**, cobertura 89.61% — más tests y menos cobertura que el día
> del merge porque el repositorio creció con las features que vinieron detrás, no porque la 003 haya
> perdido nada. `ruff`, `mypy`, `tsc` y `prettier`, limpios en `9d413fe`. El número describe el árbol
> de este momento, que varios frentes comparten: **se vuelve a medir antes de shippear, no se
> tipea**.

Lo que se desvió de lo planificado y por qué está en **Desvíos de la implementación**, al final.

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
| ✅ 1 | `app/shared/sections.py` y `app/shared/parameters.py`: el enum de secciones del negocio y el catálogo declarativo con los siete parámetros, su valor inicial, su rango, su unidad y las dos frases en español que el dueño lee. Con su test: claves únicas y cada valor inicial dentro de su propio rango. | `add_backend_feature` | Developer | RF-04, RF-05, RF-06 |
| ✅ 2 | Migración: `operations.audit_entry` con sus enums, sus cuatro índices y **el trigger que rechaza `UPDATE` y `DELETE`**. `AuditEntry` entra a `app/models.py` en el mismo commit. | `add_database_migration` | Developer | RF-08 |
| ✅ 3 | `operations`: repositorio de la bitácora con `insert`, `list` y `list_for_entity`, y **sin** `update` ni `delete`. | `add_backend_feature` | Developer | RF-08 |
| ✅ 4 | `operations`: `list_parameters()` devuelve el catálogo con el valor vigente encima —no las filas de la tabla— y `get_parameter_value()` cae al valor inicial del catálogo. Se eliminan `DEFAULT_INTERVAL_HOURS` y `DEFAULT_HIGHLIGHT_THRESHOLD` de `service.py`: el catálogo pasa a ser su fuente única. | `add_backend_feature` | Developer | RF-01, RF-04 |
| ✅ 5 | `operations`: `set_parameters()` valida contra el catálogo —clave desconocida y valor fuera de rango se rechazan, y el mensaje dice entre qué valores tiene que estar—, escribe su fila de bitácora y publica `BusinessParameterChanged`. | `add_backend_feature` | Developer | RF-02, RF-06, RF-07, RF-08 |
| ✅ 6 | Rutas `GET` y `PUT /operations/parameters`, sólo `OWNER`. | `add_backend_feature` | Developer | RF-01, RF-02, RF-03, RF-05 |
| ✅ 7 | Pantalla `(private)/configuracion`: los siete parámetros con su valor vigente, la frase de qué cambia y su rango, **señalando cuáles todavía no tienen efecto** —los cinco cuya funcionalidad no está construida— a partir de `ParameterSpec.consumed_by`. **Baja de `(private)/precios/configuracion/`**, reemplazada por una redirección al panel: la regla de negocio firmada prohíbe que un parámetro viva en la pantalla de la funcionalidad que lo usa. | `add_frontend_feature` | Developer | RF-01, RF-03, RF-05 |
| ✅ 8 | Tests de H1: el valor inicial de un parámetro que no tiene fila en la tabla, los bordes exactos de cada rango, una clave que no está en el catálogo, que compras y ventas reciben 403 en las dos rutas, y que la pantalla distingue los parámetros que todavía no tienen efecto. | `add_tests` | Tester | RF-01, RF-02, RF-03, RF-04, RF-05, RF-06, RF-07, RF-08 |

### H2 — Cada cambio manual queda registrado

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 9 | Evento `ManualChangeRecorded` en `app/shared/events/catalog.py` con su enum `AuditAction`, y el handler de `operations` que lo convierte en fila. Corre en la transacción del publicador: si falla, aborta la edición (`GEN-09`). | `add_backend_feature` | Developer | RF-09, RF-10, RF-12 |
| ✅ 10 | `identity/dependencies.py`: `visible_sections()`, que responde qué secciones ve quien llama —el dueño, todas—. **Es el único archivo de `identity` que se toca en toda la feature.** | `add_backend_feature` | Developer | RF-19 |
| ✅ 11 | `operations`: consulta de la bitácora con filtro por persona, por rango de fechas y por sección, ordenada de más nueva a más vieja. | `add_backend_feature` | Developer | RF-13, RF-14, RF-18, RF-19 |
| ✅ 12 | Rutas `GET /operations/audit` y `GET /operations/audit/{entity_type}/{entity_id}`. Autenticadas y filtradas por sección, **no** de dueño: RF-19 dice lo contrario. | `add_backend_feature` | Developer | RF-13, RF-14, RF-15, RF-18, RF-19 |
| ✅ 13 | Pantalla `(private)/historial`: la lista con sus filtros, el motivo de cada cambio, y el acceso desde un dato corregido a su propio historial sin pasar por otra pantalla. | `add_frontend_feature` | Developer | RF-12, RF-13, RF-14, RF-15, RF-18, RF-19 |
| ✅ 14 | Tests de H2: **`UPDATE` y `DELETE` por SQL directo contra la base**, esperando que la rechace; el handler que falla y deja la edición sin efecto; y el filtro por sección con tres usuarios reales, uno por rol. | `add_tests` | Tester | RF-09, RF-10, RF-11, RF-12, RF-13, RF-14, RF-15, RF-16, RF-17, RF-18, RF-19 |

### H3 — Un solo lugar para cargar y corregir

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 15 | `frontend/lib/operations/actions.ts`: el registro tipado de acciones, cada una con su etiqueta, su destino y las secciones que la habilitan. **Nace con las acciones que ya existen, no sólo con las de esta feature**: pedir la lista de precios ahora y resolver un caso de la cola de revisión —las dos de compras, `POST /price-updates` y `POST /triage/cases/{case_id}/resolution`— más las dos que agrega la 003. Sin las dos primeras, compras entra a la pantalla y no ve nada. Cada feature futura agrega su línea acá. | `add_frontend_feature` | Developer | RF-20, RF-21 |
| ✅ 16 | Pantalla `(private)/acciones`: las acciones filtradas por la sesión, y el resultado de cada una —aplicada o fallida— visible para quien la ejecutó. | `add_frontend_feature` | Developer | RF-20, RF-21, RF-22 |
| ✅ 17 | Tests de H3: la misma pantalla vista por compras y por ventas devuelve conjuntos distintos **y ninguno de los dos vacío**, y una acción que falla se ve fallar. | `add_tests` | Tester | RF-20, RF-21, RF-22 |

### H4 — Corregir un valor sin borrar lo que decía

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 18 | `app/shared/corrections.py`: el mixin de columnas de corrección, el enum `CorrectionStatus` y el catálogo de los cinco motivos en español. | `add_backend_feature` | Developer | RF-11, RF-25 |
| ✅ 19 | Migración: `core.correction` con su índice único parcial sobre `(entity_type, entity_id, field)` para las no anuladas. `Correction` entra a `app/models.py` en el mismo commit. | `add_database_migration` | Developer | RF-25, RF-26, RF-27 |
| ✅ 20 | `catalog`: aplicar una corrección sobre **cualquier campo** de un producto o de su precio, exigiendo motivo, conservando `portal_value` sin tocar y publicando `ManualChangeRecorded`. | `add_backend_feature` | Developer | RF-11, RF-23, RF-25 |
| ✅ 21 | Ruta `POST /catalog/products/{product_id}/corrections`, `OWNER` y `SALES`: el catálogo y los precios son de ventas según el mapa de secciones. | `add_backend_feature` | Developer | RF-23, RF-24 |
| ✅ 22 | `catalog`: detectar el conflicto al aplicar un precio nuevo —comparar contra `portal_value`, **no** pisar la corrección, marcar `CONFLICTED`— y publicar `CorrectionConflicted`. | `add_backend_feature` | Developer | RF-28 |
| ✅ 23 | `notifications`: handler de `CorrectionConflicted` que avisa al dueño, con el envío encolado como task para que su fallo no aborte la actualización. | `add_backend_feature` | Developer | RF-29 |
| ✅ 24 | Ruta `GET /operations/corrections/reasons`: la lista sale de donde se valida, no del frontend. | `add_backend_feature` | Developer | RF-11 |
| ✅ 25 | Frontend: el diálogo de corrección con la lista de motivos y el detalle escrito, y el dato corregido señalado a simple vista con su valor original al lado en la tabla de precios. | `add_frontend_feature` | Developer | RF-11, RF-26, RF-27 |
| ✅ 26 | Tests de H4: las **tres corridas del conflicto** —el portal informa lo mismo, informa algo distinto, vuelve a informar lo distinto—; el motivo obligatorio; y corregir un campo que no es un importe. | `add_tests` | Tester | RF-11, RF-23, RF-24, RF-25, RF-26, RF-27, RF-28, RF-29 |

### H5 — Deshacer una corrección equivocada

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| ✅ 27 | `catalog`: anular una corrección restituyendo `portal_value`, marcando la fila `REVERTED` con quién y cuándo —no se borra— y publicando `ManualChangeRecorded`. Rechaza el pedido sobre un dato que no vino del portal. | `add_backend_feature` | Developer | RF-30, RF-31, RF-32, RF-33 |
| ✅ 28 | Ruta `DELETE /catalog/corrections/{correction_id}`, sólo `OWNER`. | `add_backend_feature` | Developer | RF-30, RF-33 |
| ✅ 29 | Frontend: la acción de anular, alcanzable desde el historial y **ausente** sobre un dato cargado enteramente a mano. | `add_frontend_feature` | Developer | RF-30, RF-33 |
| ✅ 30 | Tests de H5: que restituya el valor del portal y **no** el anterior después de dos correcciones seguidas, y que anular sobre un dato sin corrección falle limpio. | `add_tests` | Tester | RF-30, RF-31, RF-32, RF-33 |

> **La tarea 29 planificó una pantalla y la implementación eligió otra.** El ✅ es de la acción, no
> del lugar: anular existe y está restringida al dueño, pero **no** se llega desde el historial —se
> llega desde la pantalla del dato corregido, que es donde está el valor que se restituye—. El texto
> planificado se deja como está, porque es lo que se planificó; `diagrams/flujo-dueno.mmd` ya dice
> dónde quedó. La spec firmada sigue pidiendo «desde el historial» en el criterio de aceptación de
> RF-30, y por eso [`converge.md`](converge.md) marca ese requisito **🟡 Parcial**: la deriva está
> abierta y la cierra el humano —moviendo la acción o enmendando la spec—, no esta página.

## Los diez defectos que encontró la suite

Ninguno lo encontró una revisión de código: los diez los encontró **escribir el test que el
requisito pedía**. El `Tester` no arregló ninguno —su rol no le permite tocar `app/` ni
`frontend/`— y los dejó demostrados con `@pytest.mark.xfail(strict=True)`. `strict` es lo que hizo
que el traspaso funcionara solo: cuando el `Developer` arregló cada uno, el test pasó, y un `xfail`
que pasa **rompe la suite** hasta que alguien le saca el marcador. El aviso no dependió de que
nadie se acordara.

Los cuatro primeros salieron al escribir la suite; los del medio, al corregirla; los dos últimos no
los encontró ningún test que falle, sino la pregunta de completitud contra los 33 requisitos.

**Todos arreglados el 2026-08-30**, antes del merge. La suite de ese día: **879 passed · 1 skipped ·
0 xfailed**, cobertura 95.25%.

| # | Defecto | Arreglo | Requisitos |
|---|---------|---------|------------|
| 1 | La bitácora no resistía un `TRUNCATE`: el trigger era `FOR EACH ROW` y un trigger de fila no se dispara ante un `TRUNCATE`. Una sola sentencia borraba el historial entero sin una palabra. | Segundo trigger `BEFORE TRUNCATE ... FOR EACH STATEMENT` sobre la misma función, en `operations/models.py` **y** en la migración `0006` — Postgres sólo admite triggers de sentencia sobre `TRUNCATE`. | RF-17 |
| 2 | `nan` y `snan` como valor de un parámetro decimal terminaban en un 500: `Decimal('nan')` pasaba el chequeo de tipo y la comparación de rango lanzaba `InvalidOperation` fuera del bloque protegido. | El no-finito se rechaza dentro de `_as_number`, que es donde ya se decide qué es un número guardable. | RF-06 |
| 3 | Corregir un texto a `null` escribía el literal «None» en el dato: `str(None)` es truthy y la guarda de vacío no disparaba nunca. | La guarda pasó a mirar el valor antes de convertirlo a texto. | RF-23 |
| 4 | `_came_from_the_portal` leía `registered_by_rule_id` —*qué regla incorporó el producto*, no *quién tipeó el valor*— y su docstring afirmaba lo contrario. **La lista siguiente pisaba la corrección manual en silencio.** | Migración `0009`: `Product.source` y el `source` de la fila de precio responden la pregunta por campo. | RF-25, RF-27, RF-28, RF-29, RF-30, RF-31 |
| 5 | RF-33 no tenía sobre qué pararse: nada en el modelo registraba que *ese valor* lo tipeó una persona. Las dos formas de llegar dejaban la misma columna en `None`. | Mismo arreglo que el 4: la columna que faltaba. | RF-33 |
| 6 | La moneda corregida la pisaba la lista siguiente: la guarda buscaba la corrección vigente del **precio**, así que una corrección de **moneda** sola no protegía nada — y la pantalla seguía mostrando la marca de una corrección que ya no regía. | La guarda pregunta por el campo corregido, no por el precio. | RF-25, RF-28, RF-29 |
| 7 | El 404 de un producto inexistente contestaba en inglés, y ese texto salía tal cual a una pantalla que lee el cliente. | Mensaje en español, con la voz de los demás errores del módulo. | Art. VIII, `GEN-07` |
| 8 | El aviso de conflicto no decía **de qué dato** hablaba: dos conflictos en la misma corrida nocturna llegaban como dos mensajes idénticos. | El aviso nombra el dato, sin importar de `catalog` — la identificación viaja en el evento. | RF-29 |
| 9 | La migración `0008` limpiaba `operations.parameter` y se olvidaba de `access_settings`, donde la `0003` sembró el mismo parámetro. **En una base migrada el panel decía 60 minutos y la sesión se cerraba a las 8 horas.** | La `0008` limpia las dos tablas, con el mismo criterio: sólo la fila que todavía tiene el valor que `0003` escribió. | RF-04, RF-07 |
| 10 | El mensaje de éxito de una corrección era código inalcanzable: el camino feliz ponía el mensaje y acto seguido cerraba el diálogo. Sólo se veía el fracaso. | El resultado sobrevive al cierre del diálogo. | RF-22 |

El **9** merece leerse dos veces: no lo encontró un test que falle, sino la pregunta de si cada
requisito tiene quien lo demuestre. No lo veía nadie porque la suite arma el esquema con
`Base.metadata.create_all()` y **no ejecuta alembic en ningún lado**, así que el hueco de test
tapaba un defecto de producción. El test que lo cierra lee el fuente de las migraciones y lo
compara contra el catálogo.

Y la simetría, que se escribe acá para que la página no se lea como que la suite alcanzó: **la
revisión de código encontró después lo que la suite no veía** —el Blocker de las dos rutas que
contestaban 200 sin commitear, y los ocho defectos detrás de los 13 Major—. Están en **Estado**,
arriba, con el commit que cerró cada grupo. Ninguna de las dos formas de mirar reemplaza a la otra.

## Lo que quedó anotado para después

Nada de esto bloquea la entrega. Son cosas que los agentes vieron desde adentro y no les
correspondía arreglar, anotadas acá para que no se pierdan.

**Deuda que ya tiene nombre y lugar**

- **Mensajes de dominio en inglés fuera de `catalog`** (`GEN-07`, Artículo VIII): cuatro «User not
  found» en `identity/service.py`, «Rule not found» y «Case not found» en `triage/service.py`, y
  «Job run not found» en `operations/service.py`. Salen por la API igual que salía el 404 del
  defecto 7. Es un barrido de una tarde, y es de otra feature.
- **La suite nunca corre alembic.** `conftest.py` arma el esquema con `Base.metadata.create_all()`.
  Por eso el defecto 9 vivió sin que nadie lo viera, y el test que lo cierra tuvo que leer las
  migraciones como texto en vez de aplicarlas. Que la cadena corra de verdad contra una base
  descartable es la clase de test que devuelve lo que cuesta.
- **`access_settings` es una segunda copia de los parámetros de acceso**, que `identity` mantiene
  por evento pero que nada reconcilia con el catálogo: sus filas existían sólo porque la `0003` las
  sembró. Que la proyección se siembre sola desde el catálogo —o que no se siembre— es una decisión
  de arquitectura pendiente.
- **`catalog/handlers.py::apply_decision` colapsa** «el precio que tipeó la persona» y «el precio
  que traía la fila del portal» en un solo `or`, así que `incorporate_product` tiene que inferir la
  intención de `rule_id`. Hoy falla del lado conservador, pero pasarle la intención explícita es
  más honesto que inferirla.
- **`catalog/repository.py::add_product` no recibe `source`**, así que el servicio lo escribe justo
  después y vuelve a flushear: una fila se inserta y se actualiza en el camino de una sola
  decisión humana.
- **`CorrectionConflicted` no lleva `code` ni `description`**, así que el aviso del defecto 8
  identifica el producto por su id interno y no como lo lee el dueño. Ampliar el evento es la
  salida correcta; leer la tabla de `catalog` desde `notifications` no lo es (Artículo IV).
- **`diagrams/flujo-general.mmd` deja abierta la ambigüedad que `flujo-dueno.mmd` cerró.** Pone
  «Deja sin efecto una corrección» inmediatamente después de «Abre el historial y filtra por persona
  y fechas», que es la vecindad que sugiere que se anula desde el historial. No nombra una pantalla,
  así que no afirma nada falso, pero ahora los dos diagramas de la misma feature no dicen lo mismo.
  **Queda para el frente que lo tenga asignado**: no se tocó acá porque es archivo de otro.
- **`npx next lint` ya no existe en Next 16.** El comando quedó viejo en la documentación; lo que
  corre el repositorio es `npm run lint`.

**Dos preguntas que son del humano, no del agente**

- **Reenviar el valor que un parámetro ya tenía** responde 200 y escribe una línea de bitácora con
  `old_value == new_value`. La spec no resuelve el caso. El test lo deja enunciado sin avalarlo.
- **Una escritura del sistema sobre un importe con corrección vigente queda frenada** — hoy se
  registra y no se aplica. Si el negocio quiere que una persona pueda pisar su propia corrección
  desde la cola de revisión, eso exige un motivo (RF-11) y por lo tanto es una decisión de alcance.

**Un error de cuenta que se repite en tres lugares**

La tarea 7 de este documento y el docstring de `app/shared/parameters.py` dicen «cinco de estos
esperan la funcionalidad que los va a leer». Son **cuatro**: `due_date.notice_days`,
`purchase_order.stalled_days`, `receipt.notice_days` y `daily_digest.time`. Los que sí tienen
consumidor son **tres**, no dos — se contaban los dos de `catalog` y se olvidaba
`access.session_idle_minutes`, que lo lee `identity`. Ese olvido no fue cosmético: es exactamente
lo que dejó al parámetro sin observar, y debajo estaba el defecto 9.

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


## Desvíos de la implementación

Cinco decisiones que no estaban en el plan y se tomaron al construir. Las tres primeras las decidió
el humano el **2026-08-30**; las otras dos son consecuencias mecánicas que no cambian el alcance.

### 1. El parámetro de inactividad de sesión ya existía, y la 002 ya está construida

El plan declara `session.idle_timeout_minutes` con valor inicial 60 y anota *"002 — cuando se
construya"*. La 002 **está construida y archivada**: `identity` lee hoy `access.session_idle_minutes`
y la migración 0003 lo sembró en 480, que es lo que su RF-36 firmada promete ("ocho horas").

El riesgo que el plan registró comparaba los 60 minutos contra el **brief**, no contra una spec
firmada y entregada.

> **Decisión del humano (2026-08-30):** gana la 003. El catálogo declara
> **`access.session_idle_minutes` con valor inicial 60** —la clave que `identity` ya lee, para que el
> parámetro que el dueño mueve sea el que la plataforma obedece—, la migración `0008` borra la fila
> sembrada y `identity` toma su valor inicial del catálogo en vez de su propia constante.
>
> **Queda pendiente para el humano:** enmendar `docs/specs/archive/002-access-control/spec.md`, cuya
> RF-36 y cuyo criterio de aceptación siguen diciendo ocho horas. Es una spec firmada: no se toca sin
> decisión explícita.

### 2. Los otros dos parámetros de acceso quedan fuera del panel

`access.max_failed_attempts` (5) y `access.lockout_minutes` (15) también los sembró la 0003 y también
los consume `identity`. Con el catálogo cerrado, un parámetro que no está en él no se puede escribir
por API.

> **Decisión del humano (2026-08-30):** quedan fuera. El panel lleva exactamente los siete del plan.
> Los dos siguen funcionando desde las constantes de `identity/service.py` y dejan de ser
> configurables hasta que una feature futura los agregue al catálogo. La migración `0008` borra sus
> filas sembradas **sólo si nadie las cambió**.

### 3. Una sección nueva en la matriz de permisos: `MANUAL_CORRECTIONS`

`DELETE /catalog/corrections/{id}` es sólo del dueño (RF-30), y ninguna sección existente daba
"dueño y nadie más" sin mentir sobre lo que es. Se agregó `MANUAL_CORRECTIONS` a
`identity/permissions.py`, con su fila en la matriz y en el test que la recorre entera.

Corregir sigue autorizándose por la sección del dato —`PRODUCT_CATALOG`, que es dueño y ventas
(RF-24)—. La asimetría entre corregir y deshacer es la que firmó la spec.

### 4. `Section` de `shared/` se llama `BusinessSection`

`data-model.md` la nombra `Section`, pero `identity.permissions` ya tiene una clase con ese nombre.
Dos clases homónimas hacen que FastAPI publique **las dos** con su nombre completo en el OpenAPI, lo
que renombra un tipo que el frontend ya lee (`lib/auth/permissions.ts`). El enum vive igual en
`app/shared/sections.py`; sólo cambia el nombre de la clase.

### 5. Dos migraciones más de las que decía el modelo de datos

`data-model.md` habla de una sola migración. Salieron tres, una por tarea, como pide `tasks.md`:
`0006` la bitácora con su trigger, `0007` las correcciones, `0008` la limpieza de los parámetros
sembrados. Cada una hace una cosa y se puede leer sola.

### Además, dos cosas que el plan pedía y se hicieron

- **`frontend/app/(private)/precios/configuracion/`** dejó de tener pantalla: es una redirección a
  `/configuracion`. Con ella se fueron `components/catalog/SettingsForm.tsx` y
  `savePriceUpdateSettings`, que no tenían otro llamador. La ruta `PUT /price-updates/settings` del
  backend sigue existiendo y sigue funcionando igual.
- **`AuditEntry` y `Correction`** entraron a `app/models.py` en el mismo commit que su migración, y
  `alembic check` no detecta diferencias.

### Un detalle del trigger que conviene saber

La función y el trigger de inmutabilidad están **dos veces**: en la migración `0006`, que es lo que
los instala en una base real, y colgados del metadata en `operations/models.py`, porque la suite
construye su esquema con `Base.metadata.create_all()` y un invariante que sólo existe en producción
no lo puede probar ningún test. Son seis líneas de SQL, y una migración es un registro histórico que
no debe importar código de la aplicación.
