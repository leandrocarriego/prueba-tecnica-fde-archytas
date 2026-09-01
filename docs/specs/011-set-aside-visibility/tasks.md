# Lo apartado se ve — Tareas

<!--
  ARTEFACTO INTERNO. Cada tarea mapea a una skill de agents/skills/ y es lo bastante
  chica como para terminarse de una sentada.
-->

**Feature:** 011-set-aside-visibility · **Plan:** `plan.md`

## Estado de la implementación (2026-08-31)

✅ hecho

**H1, H2 y H4 están entregadas.** Los cuatro orígenes que apartaban en silencio
—padrón, comprobantes, buzón y ventas— abren caso, con su motivo, su recorte, de
qué pantalla salieron y cuándo se leyeron; la cola dice cuántos pendientes hay,
desde cuándo, y marca los demorados contra un parámetro que el dueño mueve.

**H3 estuvo frenada y el Lead la destrabó el 2026-08-31.** El fallo, y por qué:

Lo que se había escalado como «el plan contradice a la matriz de permisos» era
un síntoma. El plan implementaba fielmente lo que la spec decía; **la que se
había desviado era la spec**, en su tabla de actores, en el «cómo se prueba» de
H3 y en dos criterios de aceptación, todos poniendo los pendientes de precios
del lado de Julián.

`PROJECT_BRIEF.md` —el alcance acordado con el cliente— dice lo contrario, con
sus palabras, sobre Marcela: los precios de lista los ve para consultar, y
*«sobre esos precios sí puede pedir la lista sin esperar al próximo ciclo y
**resolver lo que el sistema haya apartado**»*. Y enumera lo de Julián sin los
precios: *«ventas duplicadas o con datos rotos, productos sin rubro»*.

Tres cosas apuntan al mismo lado y ninguna estaba en discusión: el brief, la
matriz (`Section.PRICES` es `WRITE` para compras) y `test_permissions.py`, que
la fija y rompe el build. Y `shared/sections.py` da la regla de desempate para
`BusinessSection`: cuando «de qué área es el dato» y «quién lo decide» divergen,
gana el segundo.

**Los siete `kind` que existían antes de esta feature son `PURCHASING`.** El
primero de ventas lo trae la 011 (`unreadable_sale_row`). Se enmendó `spec.md`
—cuatro lugares, con su fila en Enmiendas—, se corrigió la tabla de `plan.md`,
la migración `0018` y los handlers.

**H3 quedó construida bajo ese fallo.** `list_cases` recorta por
`visible_sections(user)` y acepta `section` como filtro explícito, que sólo
puede angostar y nunca ensanchar —pedir un área que no se alcanza es 403 y no
una lista vacía, porque una lista vacía dice «no hay nada ahí», que es otra
respuesta y es mentira—; `resolve` rechaza con 403 el caso de un área ajena, y
la comprobación vive en el servicio porque el área es un dato de la **fila** y
una `Depends` corre antes de leerla. Las dos rutas de casos pasan a exigir
sesión; las tres de `/rules` no se abren. Del lado del frontend: la entrada del
nav y la acción manual dejan de declarar sección, la pantalla pide `/triage/rules`
sólo si quien mira alcanza `PRICES`, y el filtro por área se dibuja con las
opciones que manda el backend —con una sola área no se dibuja, que es el caso de
Marcela y el de Julián, y lo deja donde sirve: en la pantalla del dueño—.

Consecuencia del fallo, y vale verla: **Marcela sigue viendo lo que ve hoy**
—los siete `kind` viejos más proveedores, pagos y mensajes—, y lo que la 011
agrega de verdad al reparto es que **Julián ve las ventas apartadas**, que es el
único origen de su lado. La feature no le saca una pantalla a nadie.

**Los tests están escritos** (`test_set_aside_visibility.py`, más los de rol en
`test_rbac.py` y los del frontend en `test_the_review_queue_is_reachable.py`).
Cubren cuatro de los cinco orígenes, el agrupamiento, el detalle, la demora, el
reparto por rol y el cierre automático. Se verificaron por mutación: sacarle el
filtro por área al servicio y volver a poner `section: 'PRICES'` en el menú
hacen fallar los tests que los cuidan.

Los HTML fijados de proveedores, pagos, mensajes y órdenes se capturaron un día
bueno —sólo el de ventas trae filas rotas, doce—, así que las variantes rotas se
**derivan** rompiendo una celda de la página fijada (`portal_factory`), igual que
`price_list_with()` deriva del xlsx real. Un `*-broken-*.html` aparte se
desactualiza el día que el portal cambia y nadie se entera.

**RF-01 estaba construido y era letra muerta; se arregló el 2026-08-31.** Un
`ParsedSupplier` nunca recibía un `reason`: en `parsers.py`, el
`balance, _ = _read_money(...)` del padrón **descartaba** el motivo, así que una
fila con saldo ilegible se guardaba como válida con `balance=None`, nunca iba a
cuarentena, y `SupplierRowsQuarantined` —que esta feature agregó al catálogo y
`triage` ya escuchaba— no se podía disparar jamás. Era el mismo Artículo II que
la 011 vino a cerrar, un nivel más abajo: la feature avisaba de todo salvo de
esto, que es justamente lo que prometía. El motivo ahora viaja.

Cambia la ingesta ya desplegada, y hay que decirlo: un saldo que hoy se guarda
en silencio como `None` pasa a abrir caso. Es lo que RF-01 promete, y el test
`test_a_readable_supplier_is_not_set_aside` cuida el borde de enfrente —siete de
los ocho proveedores del padrón siguen intactos— porque pasarse de largo con
esto inundaría la cola, que es el Artículo II al revés.

**RF-11 se cerró entero el 2026-08-31, en el segundo intento.** La tarea 8 lo
construyó para las cuatro `kind` nuevas y para la de órdenes (007), y se declaró
cerrado ahí: eran **cinco de once**. El `/converge` lo marcó como requisito sin
implementar, con razón — el requisito dice «para **cada** pendiente … de qué
sección del portal proviene y cuándo se leyó», y este mismo documento ya había
escrito por qué eso importa: uno solo que no lo diga obliga a quien mira la lista
a saber de antemano cuáles lo traen. Las seis que faltaban —`unreadable_row`,
`unknown_product`, `missing_product`, `unreadable_history`,
`unreadable_invoice_row` y `unknown_category`— lo dicen ahora (tarea 8b).

Con una excepción, deliberada y escrita en el handler: un rubro que vuelve a la
cola porque alguien **revocó su regla** (008) no salió de ninguna lectura —el
`batch_id` viene en cero por eso—, así que dice de dónde salió y no dice cuándo
se leyó. Poner ahí el momento de la revocación sería llamar «cuándo se leyó» a
cuándo alguien cambió de opinión.

**H5 está construida, y su alcance quedó acotado por el cliente.** `sales`
publica `QuarantinedSourceResolved` al resolver un grupo o corregir una venta, y
`triage` lo consume y cierra el caso. `purchases` también lo publica y hoy no
cierra nada: un comprobante ilegible **nunca llega a ser un `Payment`** —se
queda apartado en `staging`, que es justamente el silencio que esta feature
cierra abriéndole un caso—, así que los que se mueven por la pantalla de
comprobantes son los legibles, y ésos nunca tuvieron caso. Está escrito en el
código, en `UNREADABLE_PAYMENT_ROW`.

El `/converge` del 2026-08-31 lo marcó como deriva mayor, porque el criterio de
aceptación firmado usaba de ejemplo un comprobante repartido. **El cliente eligió
acotar la spec en vez de construirlo** (opción B): RF-20 pasó a decir a qué
orígenes alcanza hoy, el criterio usa una venta corregida, y el pendiente del
comprobante retenido quedó en *Fuera de alcance*. La spec se volvió a firmar.

**Y la vuelta atrás se agregó (RF-24).** El mismo control encontró que
`undo_resolution` devolvía la venta a su cola sin reabrir el caso, así que la
lista decía que no había nada que revisar sobre algo que sí estaba en revisión.
El cliente decidió construirlo, se escribió como requisito —no se construyó
callado— y la spec se firmó por tercera vez.

## Orden

Las cinco historias van en el orden de prioridad de la spec. **Al terminar H1 hay algo entregable de
verdad**: los cuatro orígenes que hoy apartan en silencio empiezan a abrir caso, y el quinto —las órdenes, que ya andaba— queda con test que lo sostiene y el equipo los ve en
la pantalla que ya usa. Todo lo demás —el detalle, el filtro por área, la antigüedad, el cierre
automático— mejora una lista que a partir de H1 ya existe y ya sirve.

Dentro de cada historia el orden es el del plan: migración → backend → frontend → tests.

### H1 — Que nada quede apartado en silencio

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 1 ✅ | Migración de `operations.exception`: columna `section` (`BusinessSection`, no nula), índice `ix_exception_section_status`, y backfill por `kind` de los **siete** `kind` que existen hoy, según el mapa del plan —que los enumera a todos, sin default—. Un `kind` fuera de la lista hace fallar la migración. `alembic check` limpio | `add_database_migration` | Developer | RF-01…RF-05, RF-12 |
| 2 ✅ | `SupplierRowsQuarantined` y `PaymentRowsQuarantined` en `shared/events/catalog.py`, publicados desde `normalize_supplier_ledger` con el helper `_quarantined_of` que ya existe | `add_backend_feature` | Developer | RF-01, RF-02 |
| 3 ✅ | `MessageRowsQuarantined` en el catálogo, publicado desde `normalize_messages`. Ojo con el filtro `if row.external_id not in known`: una fila ilegible sin `external_id` no puede quedar afuera del evento | `add_backend_feature` | Developer | RF-03 |
| 4 ✅ | Cuatro suscripciones nuevas en `triage/handlers.py` —proveedores, pagos, mensajes y ventas— con sus `kind`, su `section` y `remember=False`. Reescribir el comentario de `normalize_sales` que justificaba no tener suscriptor | `add_backend_feature` | Developer | RF-01…RF-05, RF-07, RF-08 |
| 5 ✅ | Las cuatro `kind` nuevas en `CASE_KINDS` de `lib/triage/types.ts`, con su etiqueta en español, y el tipo regenerado del OpenAPI | `add_frontend_feature` | Developer | RF-06 |
| 6 ✅ | Tests de los cinco orígenes con HTML fijado: una fila rota de proveedores, una de pagos, una del buzón, una de órdenes —que ya anda desde la 007 y acá se verifica— y una de ventas, cada una abriendo su caso y ninguna contándose como buena | `add_tests` | Tester | RF-01…RF-06 |
| 7 ✅ | Tests del agrupamiento y del cierre a mano: cien filas rotas iguales son un caso con `occurrences=100`; dar por revisado deja nombre y fecha; un caso resuelto se sigue consultando con `status=RESOLVED` | `add_tests` | Tester | RF-07, RF-08, RF-23 |

### H2 — Entender un pendiente sin salir a buscar el dato

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 8 ✅ | El `payload` de las cuatro `kind` nuevas lleva `origin` —la pantalla del portal— y `read_at`, tomado del `occurred_at` del evento. El `reason` sigue en su columna | `add_backend_feature` | Developer | RF-09, RF-10, RF-11 |
| 9 ✅ | `CaseCard` muestra el recorte tal como llegó, de qué pantalla salió y cuándo se leyó, para las `kind` que lo traen | `add_frontend_feature` | Developer | RF-09, RF-10, RF-11 |
| 8b ✅ | `origin` y `read_at` en las **seis** `kind` que ya existían y no los traían. La de rubros lleva `read_at` sólo cuando vino de una lectura | `add_backend_feature` | Developer | RF-11 |
| 10 ✅ | Tests de que cada caso nuevo llega con motivo, recorte, origen y fecha de lectura legibles | `add_tests` | Tester | RF-09, RF-10, RF-11 |
| 10b ✅ | Test de que las once `kind` dicen de dónde salieron, y de que el rubro que volvió por una regla revocada no dice que se leyó | `add_tests` | Tester | RF-11 |

### H3 — Cada uno ve lo suyo

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 11 ✅ | `list_cases` filtra por `visible_sections(user)` y acepta `section` como filtro explícito, validado contra las áreas visibles; `resolve` rechaza con 403 un caso de un área que la persona no ve | `add_backend_feature` | Developer | RF-12, RF-13, RF-14, RF-22 |
| 12 ✅ | Las dos rutas de `triage/routes.py` pasan de `require_section(PRICES, WRITE)` a exigir sesión, con el permiso fino en el servicio. Si el test de `PY-09` lo exige, se ajusta a propósito y en el mismo commit | `add_backend_feature` | Developer | RF-12, RF-13, RF-14 |
| 13 ✅ | Filtro por área en `/revision`, con las opciones que el rol de quien mira puede pedir | `add_frontend_feature` | Developer | RF-22 |
| 13b ✅ | La entrada `/revision` de `components/auth/Navigation.tsx` y la acción `resolve-triage-case` de `lib/operations/actions.ts` dejan de declarar `section`, como ya lo hacen `/acciones` y `/historial`. Abrir la ruta sin abrir la puerta no le sirve a nadie | `add_frontend_feature` | Developer | RF-06, RF-12, RF-14 |
| 13c ✅ | `app/(private)/revision/page.tsx` pide `/triage/rules` **sólo** si quien mira alcanza `PRICES`, y no renderiza `RuleList` si no. Hoy ese fetch es un 403 que `rules ?? []` disfraza de lista vacía | `add_frontend_feature` | Developer | RF-06, RF-12 |
| 14 ✅ | Tests por rol en `test_rbac.py`: Julián no ve compras ni puede resolverla, Marcela no ve precios, el dueño ve todo, y el filtro por área recorta lo que muestra | `add_tests` | Tester | RF-12, RF-13, RF-14, RF-22 |
| 14b ✅ | Test de que la navegación ofrece «Revisar esto» a los tres roles, y de que la pantalla no pide las reglas cuando quien mira no alcanza `PRICES` | `add_tests` | Tester | RF-06, RF-12, RF-14 |

### H4 — Saber cuánto hace que algo espera

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 15 ✅ | `triage.stale_days` en `shared/parameters.py`: entero, inicial 7, mínimo 1, máximo 365, `consumed_by="triage"`. Aparece solo en la pantalla de parámetros | `add_backend_feature` | Developer | RF-18, RF-19 |
| 16 ✅ | `CaseRead` gana `waiting_days` e `is_stale`, calculados al leer contra el parámetro; `CaseList` gana `oldest_at` y `pending_total` | `add_backend_feature` | Developer | RF-15, RF-16, RF-17 |
| 17 ✅ | `/revision` muestra el total de pendientes, el más viejo, «espera hace N días» por caso y la marca de demorado | `add_frontend_feature` | Developer | RF-15, RF-16, RF-17 |
| 18 ✅ | Tests de la demora: seis días no, ocho sí, y el límite se mueve cambiando el parámetro y no el código | `add_tests` | Tester | RF-17, RF-18, RF-19 |

### H5 — Que la lista no mienta cuando el trabajo se hizo en otra pantalla

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 19 ✅ | `QuarantinedSourceResolved(kind, key, resolved_where)` en el catálogo, publicado por `purchases` cuando un pago retenido se imputa o se reparte, y por `sales` en `resolve_group` y `correct_sale` | `add_backend_feature` | Developer | RF-20 |
| 20 ✅ | `triage` lo consume: recalcula el `fingerprint`, cierra el caso pendiente que coincida con `decision = {"action": "resolved_elsewhere", "where": …}` y sin nombre de persona. Un evento que no encuentra caso no es un error | `add_backend_feature` | Developer | RF-20, RF-21 |
| 22 ✅ | `QuarantinedSourceReopened(kind, key, reopened_where)` en el catálogo, publicado por `sales` en `undo_resolution`; `triage` lo consume y reabre **sólo** el caso que se había cerrado solo —`resolved_by_user_id IS NULL` y `action = resolved_elsewhere`—, nunca uno que cerró una persona | `add_backend_feature` | Developer | RF-24 |
| 23 ✅ | Tests de la vuelta atrás: deshecha la resolución el caso vuelve a figurar sin decisión y sin `resolved_at`; el caso que cerró una persona **no** se reabre y conserva su nombre; el evento sin caso no rompe nada. Verificado por mutación: sacando el anuncio de `undo_resolution`, el primero falla | `add_tests` | Tester | RF-24 |
| 24 ⬜ | **Verificar que lo ya apartado antes de la feature aflora solo** en la próxima lectura, que es la única pata de la decisión del cliente de no backfillear. Si es falsa, la decisión es otra | `add_tests` | Tester | RF-01…RF-05 |
| 25 ✅ | **Medida el 2026-08-31, contra `staging` de producción**, con `scripts/dry-run/011_avalancha.sql`. **El resultado es cero**: ni una fila en cuarentena en ninguno de los cuatro orígenes —padrón, comprobantes, buzón y ventas—, así que la cola no se inunda el primer día: nace vacía. El riesgo «Alto» del plan queda descartado por medición y no por confianza. Vale para **este** despliegue: el número mide lo que hay apartado hoy, y una extracción que empiece a apartar lo mueve. Consulta de sólo lectura, agrupada por el mismo criterio con el que la cola agrupa. Contra los fixtures no sirve: se capturaron un día bueno | `add_tests` | Tester | — *(riesgo del plan)* |
| 21 ✅ | Tests del cierre automático: repartido el comprobante, el caso deja de figurar entre los pendientes sin que nadie lo cierre; queda diciendo que se resolvió así y se lo sigue consultando; y el evento sin caso no rompe nada | `add_tests` | Tester | RF-20, RF-21, RF-23 |

## Cobertura de requisitos

| Requisito | Tareas | Test |
|-----------|--------|------|
| RF-01 — proveedores apartados abren caso | 1, 2, 4 | 6 |
| RF-02 — pagos apartados abren caso | 1, 2, 4 | 6 |
| RF-03 — mensajes apartados abren caso | 1, 3, 4 | 6 |
| RF-04 — órdenes apartadas abren caso *(ya construido en la 007; acá sólo se verifica — ver Enmiendas de la spec)* | — *(nada que construir)* | 6 |
| RF-05 — ventas apartadas abren caso | 1, 4 | 6 |
| RF-06 — todo en un solo lugar | 4, 5, 13b, 13c | 6, 14b |
| RF-07 — lo repetido se agrupa con su contador | 4 | 7 |
| RF-08 — dar por revisado, con quién y cuándo | 4 | 7 |
| RF-09 — el motivo | 8 | 10 |
| RF-10 — lo que se alcanzó a leer, tal como llegó | 8, 9 | 10 |
| RF-11 — de qué pantalla salió y cuándo se leyó | 8, 8b, 9 | 10, 10b |
| RF-12 — cada uno ve lo de su área | 1, 11, 12, 13b, 13c | 14, 14b |
| RF-13 — no se resuelve lo ajeno | 11, 12 | 14 |
| RF-14 — el dueño ve todo | 11, 12, 13b | 14, 14b |
| RF-15 — cuántos pendientes hay | 16, 17 | 18 |
| RF-16 — desde cuándo espera cada uno | 16, 17 | 18 |
| RF-17 — señalado como demorado | 16, 17 | 18 |
| RF-18 — el dueño define los días | 15 | 18 |
| RF-19 — siete días por defecto | 15 | 18 |
| RF-20 — deja de contarse al resolverse en otra pantalla | 19, 20 | 21 |
| RF-21 — queda registrado que se resolvió así, y consultable | 20 | 21 |
| RF-22 — filtro por área | 11, 13 | 14 |
| RF-23 — los resueltos se conservan y se consultan | 4 *(nada borra)*, 20 | 7, 21 |
| RF-24 — deshecho el trabajo, el pendiente vuelve | 22 | 23 |
