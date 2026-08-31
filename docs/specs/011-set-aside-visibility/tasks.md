# Lo apartado se ve — Tareas

<!--
  ARTEFACTO INTERNO. Cada tarea mapea a una skill de agents/skills/ y es lo bastante
  chica como para terminarse de una sentada.
-->

**Feature:** 011-set-aside-visibility · **Plan:** `plan.md`

## Orden

Las cinco historias van en el orden de prioridad de la spec. **Al terminar H1 hay algo entregable de
verdad**: los cinco orígenes que hoy apartan en silencio empiezan a abrir caso y el equipo los ve en
la pantalla que ya usa. Todo lo demás —el detalle, el filtro por área, la antigüedad, el cierre
automático— mejora una lista que a partir de H1 ya existe y ya sirve.

Dentro de cada historia el orden es el del plan: migración → backend → frontend → tests.

### H1 — Que nada quede apartado en silencio

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 1 | Migración de `operations.exception`: columna `section` (`BusinessSection`, no nula), índice `ix_exception_section_status`, y backfill por `kind` de los siete casos históricos según el mapa del plan. `alembic check` limpio | `add_database_migration` | Developer | RF-01…RF-05, RF-12 |
| 2 | `SupplierRowsQuarantined` y `PaymentRowsQuarantined` en `shared/events/catalog.py`, publicados desde `normalize_supplier_ledger` con el helper `_quarantined_of` que ya existe | `add_backend_feature` | Developer | RF-01, RF-02 |
| 3 | `MessageRowsQuarantined` en el catálogo, publicado desde `normalize_messages`. Ojo con el filtro `if row.external_id not in known`: una fila ilegible sin `external_id` no puede quedar afuera del evento | `add_backend_feature` | Developer | RF-03 |
| 4 | Cuatro suscripciones nuevas en `triage/handlers.py` —proveedores, pagos, mensajes y ventas— con sus `kind`, su `section` y `remember=False`. Reescribir el comentario de `normalize_sales` que justificaba no tener suscriptor | `add_backend_feature` | Developer | RF-01…RF-05, RF-07, RF-08 |
| 5 | Las cuatro `kind` nuevas en `CASE_KINDS` de `lib/triage/types.ts`, con su etiqueta en español, y el tipo regenerado del OpenAPI | `add_frontend_feature` | Developer | RF-06 |
| 6 | Tests de los cinco orígenes con HTML fijado: una fila rota de proveedores, una de pagos, una del buzón, una de órdenes —que ya anda desde la 007 y acá se verifica— y una de ventas, cada una abriendo su caso y ninguna contándose como buena | `add_tests` | Tester | RF-01…RF-06 |
| 7 | Tests del agrupamiento y del cierre a mano: cien filas rotas iguales son un caso con `occurrences=100`; dar por revisado deja nombre y fecha; un caso resuelto se sigue consultando con `status=RESOLVED` | `add_tests` | Tester | RF-07, RF-08, RF-23 |

### H2 — Entender un pendiente sin salir a buscar el dato

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 8 | El `payload` de las cuatro `kind` nuevas lleva `origin` —la pantalla del portal— y `read_at`, tomado del `occurred_at` del evento. El `reason` sigue en su columna | `add_backend_feature` | Developer | RF-09, RF-10, RF-11 |
| 9 | `CaseCard` muestra el recorte tal como llegó, de qué pantalla salió y cuándo se leyó, para las `kind` que lo traen | `add_frontend_feature` | Developer | RF-09, RF-10, RF-11 |
| 10 | Tests de que cada caso nuevo llega con motivo, recorte, origen y fecha de lectura legibles | `add_tests` | Tester | RF-09, RF-10, RF-11 |

### H3 — Cada uno ve lo suyo

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 11 | `list_cases` filtra por `visible_sections(user)` y acepta `section` como filtro explícito, validado contra las áreas visibles; `resolve` rechaza con 403 un caso de un área que la persona no ve | `add_backend_feature` | Developer | RF-12, RF-13, RF-14, RF-22 |
| 12 | Las dos rutas de `triage/routes.py` pasan de `require_section(PRICES, WRITE)` a exigir sesión, con el permiso fino en el servicio. Si el test de `PY-09` lo exige, se ajusta a propósito y en el mismo commit | `add_backend_feature` | Developer | RF-12, RF-13, RF-14 |
| 13 | Filtro por área en `/revision`, con las opciones que el rol de quien mira puede pedir | `add_frontend_feature` | Developer | RF-22 |
| 14 | Tests por rol en `test_rbac.py`: Julián no ve compras ni puede resolverla, Marcela no ve precios, el dueño ve todo, y el filtro por área recorta lo que muestra | `add_tests` | Tester | RF-12, RF-13, RF-14, RF-22 |

### H4 — Saber cuánto hace que algo espera

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 15 | `triage.stale_days` en `shared/parameters.py`: entero, inicial 7, mínimo 1, máximo 365, `consumed_by="triage"`. Aparece solo en la pantalla de parámetros | `add_backend_feature` | Developer | RF-18, RF-19 |
| 16 | `CaseRead` gana `waiting_days` e `is_stale`, calculados al leer contra el parámetro; `CaseList` gana `oldest_at` y `pending_total` | `add_backend_feature` | Developer | RF-15, RF-16, RF-17 |
| 17 | `/revision` muestra el total de pendientes, el más viejo, «espera hace N días» por caso y la marca de demorado | `add_frontend_feature` | Developer | RF-15, RF-16, RF-17 |
| 18 | Tests de la demora: seis días no, ocho sí, y el límite se mueve cambiando el parámetro y no el código | `add_tests` | Tester | RF-17, RF-18, RF-19 |

### H5 — Que la lista no mienta cuando el trabajo se hizo en otra pantalla

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 19 | `QuarantinedSourceResolved(kind, key, resolved_where)` en el catálogo, publicado por `purchases` cuando un pago retenido se imputa o se reparte, y por `sales` en `resolve_group` y `correct_sale` | `add_backend_feature` | Developer | RF-20 |
| 20 | `triage` lo consume: recalcula el `fingerprint`, cierra el caso pendiente que coincida con `decision = {"action": "resolved_elsewhere", "where": …}` y sin nombre de persona. Un evento que no encuentra caso no es un error | `add_backend_feature` | Developer | RF-20, RF-21 |
| 21 | Tests del cierre automático: repartido el comprobante, el caso deja de figurar entre los pendientes sin que nadie lo cierre; queda diciendo que se resolvió así y se lo sigue consultando; y el evento sin caso no rompe nada | `add_tests` | Tester | RF-20, RF-21, RF-23 |

## Cobertura de requisitos

| Requisito | Tareas | Test |
|-----------|--------|------|
| RF-01 — proveedores apartados abren caso | 1, 2, 4 | 6 |
| RF-02 — pagos apartados abren caso | 1, 2, 4 | 6 |
| RF-03 — mensajes apartados abren caso | 1, 3, 4 | 6 |
| RF-04 — órdenes apartadas abren caso *(ya construido en la 007; acá sólo se verifica)* | 4 | 6 |
| RF-05 — ventas apartadas abren caso | 1, 4 | 6 |
| RF-06 — todo en un solo lugar | 4, 5 | 6 |
| RF-07 — lo repetido se agrupa con su contador | 4 | 7 |
| RF-08 — dar por revisado, con quién y cuándo | 4 | 7 |
| RF-09 — el motivo | 8 | 10 |
| RF-10 — lo que se alcanzó a leer, tal como llegó | 8, 9 | 10 |
| RF-11 — de qué pantalla salió y cuándo se leyó | 8, 9 | 10 |
| RF-12 — cada uno ve lo de su área | 1, 11, 12 | 14 |
| RF-13 — no se resuelve lo ajeno | 11, 12 | 14 |
| RF-14 — el dueño ve todo | 11, 12 | 14 |
| RF-15 — cuántos pendientes hay | 16, 17 | 18 |
| RF-16 — desde cuándo espera cada uno | 16, 17 | 18 |
| RF-17 — señalado como demorado | 16, 17 | 18 |
| RF-18 — el dueño define los días | 15 | 18 |
| RF-19 — siete días por defecto | 15 | 18 |
| RF-20 — deja de contarse al resolverse en otra pantalla | 19, 20 | 21 |
| RF-21 — queda registrado que se resolvió así, y consultable | 20 | 21 |
| RF-22 — filtro por área | 11, 13 | 14 |
| RF-23 — los resueltos se conservan y se consultan | 4 *(nada borra)*, 20 | 7, 21 |
