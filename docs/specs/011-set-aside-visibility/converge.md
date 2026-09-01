# Lo apartado se ve — Informe de convergencia

**Feature:** 011-set-aside-visibility · **Rol:** Lead · **Fecha:** 2026-08-31
**Skill:** `agents/skills/converge.md` · **Spec:** `Aprobado` (Leandro Carriego — FDE, 2026-08-31)

> `review_feature` pregunta «¿está bien escrito?». Este informe pregunta **«¿es lo que se
> acordó?»**. No juzga tipado, nombres ni cobertura.

## Veredicto

> ## ⛔ Deriva mayor — el gate queda bloqueado

El código y la spec **casi** describen el mismo producto, y lo que los separa no es cosmético: hay
un criterio de aceptación firmado que el código **no puede satisfacer** (RF-20 del lado de pagos) y
un requisito que dice «cada pendiente» y se cumplió en cinco de once clases (RF-11). Ninguno de los
dos es una omisión chica que se pueda anotar y seguir: los dos son promesas que el cliente firmó.

Lo demás es bueno y conviene decirlo: **21 de los 23 requisitos están implementados con evidencia
localizable**, los cinco orígenes de H1 abren caso contra HTML fijado, el reparto por área está
construido en el servicio y no en la puerta, y **69 tests pasan** (`test_set_aside_visibility.py`,
`test_the_review_queue_is_reachable.py`, `test_rbac.py`). Los seis diagramas compilan.

No hay **alcance no pedido**: ningún endpoint, pantalla ni capacidad visible que ningún requisito
pida. Lo que sí hay es **andamiaje que el plan no previó** —dos migraciones y un campo de
respuesta—, que no es alcance nuevo pero deja el plan describiendo un producto que no es el que
existe.

## Resolución (2026-08-31)

**Todos los hallazgos quedaron cerrados.** El humano eligió la **opción B** sobre H-01, firmó la
spec enmendada, decidió las tres preguntas abiertas y pidió corregir el resto.

| Hallazgo | Estado | Qué se hizo |
|---|---|---|
| **H-01** — RF-20 del lado de pagos | **Cerrado** | `spec.md`: H5 pasó a Julián y a una venta corregida, RF-20 dice a qué orígenes alcanza hoy, los criterios RF-20 y RF-21 usan la venta, y el pendiente del comprobante retenido quedó en *Fuera de alcance*. Re-firmada |
| **H-02** — RF-11 en seis `kind` | **Cerrado** | `origin` y `read_at` en las seis que faltaban. Las once lo dicen, con **una excepción escrita**: un rubro que volvió a la cola porque alguien revocó su regla no salió de ninguna lectura, así que dice de dónde salió y no dice cuándo se leyó — poner ahí el momento de la revocación sería llamar «cuándo se leyó» a cuándo alguien cambió de opinión |
| **H-03** — dos tareas ✅ sin respaldo | **Cerrado** | La 21 quedó saldada por la enmienda. La 8 se corrigió y se abrió la **8b**, que es lo que faltaba de verdad |
| **H-04** — `plan.md` describe una migración y hay tres | **Cerrado** | *Datos* documenta `0019` y `0020` con la razón de cada una; *Contratos* documenta `CaseList.sections`; el riesgo de la avalancha pasa a medirse contra `staging` de producción |
| **H-05** — tres diagramas | **Cerrado** | Los tres corregidos, más `estados-pendiente.mmd` con la transición nueva. Los seis compilan y el `README.md` se regeneró |
| **Nit** — el mensaje de error de `0018` apuntaba a `0017` | **Cerrado** | Apunta a su propia migración |
| **RF-24** — nuevo, decidido por el humano | **Construido y firmado** | `QuarantinedSourceReopened` en el catálogo, publicado por `sales.undo_resolution`, consumido por `triage`, que reabre **sólo** el caso que se había cerrado solo |

### Las tres preguntas abiertas, decididas

| # | Pregunta | Decisión | Qué se hizo |
|---|---|---|---|
| 1 | El cierre automático no tenía vuelta atrás | **Reabrir el pendiente** | Se escribió como **RF-24** antes de construirlo — hacerlo callado lo habría dejado como capacidad que nadie pidió, y el próximo control lo marcaría como tal. Construido, testeado y verificado por mutación |
| 2 | Lo apartado antes de la feature no abre pendiente | **Que aflore solo** | No se construye backfill. Queda la **tarea 24** para el `Tester`: verificar la única pata de la decisión, que los cuatro orígenes se relean enteros. Si es falsa, la decisión es otra |
| 3 | El dry-run de la avalancha no se corrió | **Contra `staging` de producción** | `plan.md` corregido. Queda la **tarea 25**, antes de `/ship` |

### Verificación de las correcciones

| Chequeo | Resultado |
|---|---|
| Suite completa | **1650 pasan**, 9 skipped, cobertura **93%** (`TEST-05`) |
| Tipos y lint (`PY-10`) | `mypy` y `ruff` limpios en 103 archivos |
| `alembic check` (`DB-01`) | *No new upgrade operations detected* |
| Frontend | `tsc --noEmit` limpio, 33 tests pasan |
| Diagramas | los seis compilan |
| Mutación sobre RF-24 | sacando el anuncio de `undo_resolution`, el test que lo cuida falla |

### Veredicto tras las correcciones

> ## ✅ Converge

Todo requisito de la spec firmada tiene implementación con evidencia, no hay alcance sin requisito
—RF-24 se escribió antes de construirse, que es exactamente lo que este control existe para
forzar—, las tareas completas están respaldadas, y plan y diagramas describen lo que el código hace.
**Pasa al `Code-Reviewer`.**

Dos cosas quedan **antes de `/ship`**, y no son del gate de calidad: las tareas **24** y **25**, que
son las verificaciones de las decisiones 2 y 3.

## 1) Changeset## 1) Changeset

La rama es `feat/006-due-date-calendar` y **no sigue la convención para esta feature**: el trabajo
de la 011 está **sin commitear** en el árbol. Se armó el changeset con los archivos que nombran
`plan.md` y `tasks.md`, más las búsquedas del paso 3.

| Archivos de la 011 en el árbol | |
|---|---|
| Nuevos | `alembic/versions/0018_de_que_area_es_cada_pendiente.py`, `0019_lo_que_triage_lee_de_los_parametros.py`, `0020_de_que_lectura_salio_un_comprobante.py`, `tests/integration/features/test_set_aside_visibility.py`, `tests/architecture/test_the_review_queue_is_reachable.py` |
| Modificados | `ingestion/{parsers,service}.py`, `triage/{handlers,models,repository,routes,schemas,service}.py`, `purchases/{models,service}.py`, `sales/service.py`, `shared/events/{__init__,catalog}.py`, `shared/parameters.py`, `frontend/app/(private)/revision/page.tsx`, `frontend/components/{auth/Navigation,triage/CaseCard}.tsx`, `frontend/lib/triage/types.ts`, `frontend/lib/operations/actions.ts`, `tests/integration/api/test_rbac.py` |

**Nota para el `Release-Manager`, no es un hallazgo de esta skill:** el mismo árbol trae trabajo de
la **012-design-system** (`docs/specs/012-design-system/`, `docs/design/README.md`,
`frontend/tests/design-system.test.ts`, `frontend/lib/branding.ts`, `frontend/components/auth/*`,
`frontend/lib/catalog/format.ts`, `agents/*`, `AGENTS.md`, `CONVENTIONS.md`). Dos features en un
mismo commit contra `main` hacen irrevisable a las dos.

## 2) Tabla de trazabilidad

| Requisito | Qué promete la spec | Dónde está implementado | Evidencia | Estado |
|---|---|---|---|---|
| RF-01 | Fila del padrón apartada → pendiente | `ingestion/parsers.py::parse_supplier_ledger`, `ingestion/service.py::normalize_supplier_ledger`, `triage/handlers.py::open_unreadable_supplier_rows` | `balance, balance_reason = _read_money(...)` (el motivo **viaja**; antes se descartaba y el evento no podía dispararse jamás) → `SupplierRowsQuarantined` → caso `unreadable_supplier_row` · `test_set_aside_visibility.py:149` | Implementado |
| RF-02 | Comprobante de pago apartado → pendiente | `ingestion/service.py::normalize_supplier_ledger`, `triage/handlers.py::open_unreadable_payment_rows` | `PaymentRowsQuarantined` (service.py:602) → `unreadable_payment_row` · test:180 | Implementado |
| RF-03 | Mensaje del buzón apartado → pendiente | `ingestion/service.py::normalize_messages`, `triage/handlers.py::open_unreadable_message_rows` | `MessageRowsQuarantined` (service.py:746), publicado **después** del filtro `known` y con `key` por `excerpt` para que las re-lecturas se agrupen · test:191 | Implementado |
| RF-04 | Orden de compra apartada → pendiente *(ya de la 007)* | `triage/handlers.py::open_unreadable_order_rows` | Suscripción viva a `PurchaseOrderRowsQuarantined` · test:206 | Implementado |
| RF-05 | Venta apartada → pendiente | `ingestion/service.py::normalize_sales`, `triage/handlers.py::open_unreadable_sale_rows` | `SaleRowsQuarantined` ahora **con suscriptor**; el comentario de la 009 fue reescrito explicando la reversión, como pedía el plan · test:221, test:268 | Implementado |
| RF-06 | Todo en un solo lugar | `triage/routes.py::list_cases`, `app/(private)/revision/page.tsx`, `lib/triage/types.ts::CASE_KINDS` | Una sola ruta y una sola pantalla; las once `kind` con etiqueta en español · test:236 · `test_the_review_queue_is_reachable.py` | Implementado |
| RF-07 | Lo repetido se agrupa con su contador | `triage/service.py::open_case` → `fingerprint_of` | Cien filas iguales = un caso con `occurrences=100` · test:292 | Implementado |
| RF-08 | Dar por revisado, con quién y cuándo | `triage/service.py::resolve` | `resolved_by_user_id`, `resolved_by_name`, `resolved_at`; `remember=False` en las cuatro `kind` nuevas · test:330 | Implementado |
| RF-09 | El motivo | `triage/models.py::ExceptionCase.reason`, `CaseCard.tsx` | `reason` en columna propia, renderizado · test:385 | Implementado |
| RF-10 | Lo que alcanzó a leer, tal como llegó | `payload["excerpt"]`, `CaseCard.tsx:193` | Test literal del recorte · test:405 | Implementado |
| **RF-11** | **De qué sección del portal viene y cuándo se leyó, «para cada pendiente»** | `triage/handlers.py` (5 de 11 `kind`) | `origin` + `read_at` en `unreadable_{supplier,payment,message,sale,order}_row`. **Faltan seis:** `unreadable_row`, `unknown_product`, `missing_product`, `unreadable_history`, `unreadable_invoice_row`, `unknown_category` | **Parcial** |
| RF-12 | Cada uno ve lo de su área | `triage/service.py::list_cases`, `identity/dependencies.py::visible_sections` | `visible` keyword-only y **sin default**; `ROLE_SECTIONS` da `SALES` a Julián · `test_rbac.py` | Implementado |
| RF-13 | No se resuelve lo ajeno | `triage/service.py::resolve` | 403 `NOT_YOUR_SECTION` decidido sobre `case.section`, no sobre la ruta · `test_rbac.py` | Implementado |
| RF-14 | El dueño ve todo | `identity/dependencies.py::ROLE_SECTIONS` | `"OWNER": frozenset(BusinessSection)` · `test_rbac.py` | Implementado |
| RF-15 | Cuántos pendientes hay | `triage/schemas.py::CaseList.pending_total` | Contado sobre **todo** lo pendiente de las áreas visibles, no sobre la página · test:485 | Implementado |
| RF-16 | Desde cuándo espera cada uno | `CaseRead.waiting_days`, `service.py::_read` | Calculado al leer, sin columna derivada · test:485 · `CaseCard.tsx:140` | Implementado |
| RF-17 | Señalado como demorado | `CaseRead.is_stale` | `waiting_days > stale_days` y sólo si sigue `PENDING` · test:450 | Implementado |
| RF-18 | El dueño define los días | `shared/parameters.py:366`, `triage/handlers.py::remember_parameter` | `ParameterSpec(triage.stale_days, …, consumed_by="triage")` + proyección por `BusinessParameterChanged` · test:464 | Implementado |
| RF-19 | Siete días por defecto | `shared/parameters.py` | `initial=7, minimum=1, maximum=365` · test:437 | Implementado |
| **RF-20** | **Al resolverse en otra pantalla, deja de contarse** | `sales/service.py::_announce_resolved` → `triage/service.py::close_resolved_elsewhere` | **Ventas: sí** (test:509). **Pagos: no cierra nada, y no puede.** `purchases/service.py:137-146` lo dice con todas las letras: un comprobante ilegible nunca llega a ser un `Payment`, así que el `staging_row_id` que abre el caso nunca coincide con el que la pantalla de comprobantes anuncia | **Parcial** |
| RF-21 | Queda registrado que se resolvió así, y consultable | `triage/service.py::close_resolved_elsewhere` | `decision = {"action": "resolved_elsewhere", "where": …}` y **sin nombre de persona**, como decidió la spec · test:530 | Implementado |
| RF-22 | Filtro por área | `triage/routes.py::SectionParam`, `service.py::list_cases`, `revision/page.tsx:110` | Sólo puede **angostar**: pedir un área no visible es 403, no lista vacía. `CaseList.sections` alimenta el filtro sin copiar la matriz de roles al browser | Implementado |
| RF-23 | Los resueltos se conservan y se consultan | `triage/service.py` (nada borra), `StatusParam` acepta `RESOLVED` | Un caso resuelto sale de la lista y se sigue leyendo · test:354 | Implementado |

## 3) Alcance no pedido (código → spec)

Se recorrió el sentido inverso: las dos rutas de `/triage/cases` (sin endpoints nuevos), la pantalla
`/revision` (sin pantallas nuevas), las tres migraciones, el parámetro y las cuatro `kind`.

**No hay una sola capacidad de negocio visible que ningún requisito pida.** La feature hizo lo que
el plan mandó y no hizo de más: no construyó cola nueva, no construyó pantalla nueva, y las cuatro
`kind` nuevas pasan `remember=False` a propósito, que era la trampa que el plan avisó (aprender está
fuera de alcance y `remember=True` es el default).

Lo que sí apareció es **andamiaje que `plan.md` no previó** — no es alcance no pedido, es deriva del
plan, y va abajo como H-04.

## 4) Tareas declaradas completas

Las 21 tareas están marcadas ✅. Se abrió el archivo que nombra cada una. **Diecinueve están
respaldadas.** Dos no lo están del todo, y en los dos casos el desvío está *narrado* en `tasks.md`
—lo cual habla bien de quien lo escribió— pero el estado quedó en ✅ igual:

- **Tarea 8** — «RF-11 se cerró entero». Construyó `origin` y `read_at` para las cuatro `kind`
  nuevas y le agregó los dos a la de órdenes. Quedan seis `kind` sin ellos, y el requisito dice
  «cada pendiente». El propio `tasks.md` argumenta por qué eso importa —«uno solo que no lo diga
  obliga a quien mira la lista a saber de antemano cuáles lo traen»— y después cierra con cinco.
- **Tarea 21** — promete el test «repartido el comprobante, el caso deja de figurar». Ese test no
  existe: los tres de `TestClosedByTheScreenThatOwnedTheWork` son de ventas. No podía existir, por
  lo mismo que hace parcial a RF-20.

## 5) Deriva respecto del plan

`plan.md` → *Datos* declara **un** cambio de esquema (`operations.exception.section`) y dice de
`operations.parameter` que va «sin cambios de esquema». El código trae **tres** migraciones:

| Migración | Qué hace | Estado en el plan |
|---|---|---|
| `0018` | `exception.section` + backfill de los siete `kind` + `ix_exception_section_status` | Documentada ✅ |
| `0019` | Tabla `operations.triage_setting` (proyección propia del parámetro) | **No está** |
| `0020` | Columna `core.payment.staging_row_id` | **No está** |

Las dos son **correcciones acertadas**, no desvíos caprichosos: `triage` no puede leer las tablas de
`operations` (Artículo IV), así que el parámetro tiene que llegarle por evento y vivir en una
proyección propia — el plan escribió «leída contra un parámetro del catálogo de `shared/parameters.py`»
sin advertir que eso, sin proyección, sería un import entre módulos. Y sin `payment.staging_row_id`
no hay clave con la que anunciar el cierre. **El código está bien y el plan quedó viejo.**

Lo mismo con `CaseList.sections`, que el plan no menciona (declara sólo `oldest_at` y
`pending_total`) y que existe por una buena razón escrita en el schema: que la pantalla dibuje el
filtro sin guardar una segunda copia de la matriz de roles en el browser.

## 6) Los diagramas

`bash scripts/diagrams/validate.sh docs/specs/011-set-aside-visibility/diagrams/` → **los seis
compilan** ✓. Se leyeron contra el código:

- `estados-pendiente.mmd` — corresponde. `Pendiente → Revisado` es `resolve`, `Pendiente → Resuelto`
  es `close_resolved_elsewhere`, y «Demorado» como estado calculado y reversible al mover el plazo
  es exactamente `is_stale`.
- `flujo-sistema.mmd`, `flujo-dueno.mmd` — corresponden.
- **`flujo-general.mmd`, `flujo-julian.mmd` y `flujo-marcela.mmd` no corresponden**: los tres siguen
  poniendo los pendientes de **precios del lado de Julián**. Es exactamente lo que la enmienda del
  2026-08-31 corrigió en `spec.md`, en `plan.md`, en la migración `0018` y en los handlers — y los
  diagramas quedaron afuera de esa pasada. Hoy los siete `kind` viejos, precios incluidos, son
  `PURCHASING`, y `flujo-julian.mmd` le dibuja a Julián un área que el código no le muestra.

## 7) Reglas del dominio (INVIOLABLES)

Ninguna de las cinco resulta violada por lo que la feature **promete**, que es el ángulo de esta
skill:

| Regla | Verificación |
|---|---|
| SIGProv es de sólo lectura | Ninguna escritura al portal. La spec lo pone además en *Fuera de alcance* |
| La extracción es navegador, no HTTP | `grep -rE "httpx\|requests\." app/modules/portal` → sin resultados |
| Nada se descarta | **Es el artículo que esta feature termina de cumplir.** Y el arreglo del parser del padrón lo cierra un nivel más abajo: un saldo ilegible se guardaba como `None` en silencio |
| `raw` → `staging` → `core`, `raw` inmutable | Nada toca `raw`; los eventos salen de la transformación que ya corre |
| Credenciales sólo en el entorno | La feature no las toca. El `excerpt` es HTML de una página ya autenticada, no una credencial |

## 8) Hallazgos

| # | Tipo | Qué dice el artefacto | Qué hace el código | Rol dueño | Acción |
|---|---|---|---|---|---|
| H-01 | **Requisito sin implementar** | RF-20 y su criterio de aceptación: *«Repartido un comprobante desde su pantalla, su pendiente deja de contarse»*. H5 lo repite en su «cómo se prueba» | `purchases` publica `QuarantinedSourceResolved`, y **no cierra nada ni puede**: un comprobante ilegible nunca llega a ser un `Payment`, así que el caso que se abre con un `staging_row_id` de cuarentena nunca se cruza con el `staging_row_id` de un pago legible. Del lado de ventas sí funciona | **Humano** decide (ver abajo) | Elegir entre las dos salidas |
| H-02 | **Requisito sin implementar** | RF-11: *«para **cada** pendiente … de qué sección del portal proviene y cuándo se leyó»* | Seis de las once `kind` no llevan `origin` ni `read_at`: `unreadable_row`, `unknown_product`, `missing_product`, `unreadable_history`, `unreadable_invoice_row`, `unknown_category`. `CaseCard` los renderiza condicionados, así que no falla nada: simplemente no lo dicen | `Developer` | Agregar `origin` + `read_at` a los seis handlers restantes, y un test que recorra las once |
| H-03 | **Tarea sin respaldo** | `tasks.md`: «**RF-11 se cerró entero**» (tarea 8 ✅) y tarea 21 ✅ prometiendo el test del comprobante repartido | RF-11 quedó en 5 de 11; el test de pagos no existe | `Developer` · `Tester` | Desmarcar las dos hasta que H-01 y H-02 se resuelvan |
| H-04 | **Deriva del plan** | `plan.md` → *Datos* declara una sola migración y dice que `operations.parameter` va «sin cambios de esquema». *Contratos* declara que `CaseList` gana `oldest_at` y `pending_total` | Existen `0019` (tabla `operations.triage_setting`) y `0020` (`core.payment.staging_row_id`), y `CaseList` además gana `sections`. **El código está bien**: la proyección es lo que evita el import entre módulos que el propio plan prohíbe | `Backend-Architect` | Actualizar `plan.md` (*Datos* y *Contratos*) para que describa el producto que existe. **No bloquea** |
| H-05 | **Diagrama desactualizado** | `flujo-general.mmd:28`, `flujo-julian.mmd:5`, `flujo-marcela.mmd:12` ponen los precios del lado de Julián | La enmienda del 2026-08-31 los pasó a compras, y así está en `spec.md`, `plan.md`, la migración `0018`, los handlers y `test_permissions.py` | `Solution-Designer` | `/diagram 011` sobre los tres. **No bloquea** |

### Observaciones que no son hallazgos

- **`sales/service.py::undo_resolution`** devuelve una venta a `HELD` y **no publica nada**, así que
  un caso que se cerró solo no vuelve a abrirse. Ningún requisito pide la vuelta atrás, así que no
  es un requisito sin implementar; pero la regla de negocio dice *«hay una sola verdad sobre si algo
  sigue pendiente»*, y acá hay un camino por el que las dos verdades se separan. **Es una pregunta
  para el humano**, no un defecto que el agente pueda decidir.
- `alembic/versions/0018_…py:97` — el mensaje de error de la migración dice «Add them to
  `SECTION_OF_KIND` in migration **0017**» y el archivo es el `0018`. Una línea, para el
  `Code-Reviewer`.

## 9) Las dos salidas de H-01 — decide el humano

La spec firmada promete el cierre automático **con un comprobante repartido**, y esa es la frase que
el cliente leyó. El código no lo hace por una razón estructural, no por un olvido. Las dos salidas,
con lo que cuesta cada una:

**Opción A — implementar lo que falta.** Que un comprobante **retenido** abra su propio caso, para
que la pantalla de comprobantes tenga algo que cerrar. Vuelve al `Developer` y después otra vez al
`Tester`. Es alcance que el plan no previó y no es de una tarde: hay que decidir con qué `kind` y
con qué clave se abre, si el caso se cierra al imputar o también al anular, y **cuidar el riesgo que
el propio plan anotó** —la avalancha: todos los comprobantes retenidos de hoy abrirían caso el
primer día—.

**Opción B — corregir la spec.** RF-20 se cumple hoy del lado de ventas, que es el único origen
donde el pendiente y la pantalla que lo resuelve hablan del mismo registro. Se reescribe el criterio
de aceptación con ese ejemplo, se anota por qué el de pagos no aplica todavía, y **el cliente vuelve
a firmar** (`/approve-spec`): el gate de la firma se reabre. Vuelve al `Solution-Designer`.

**A favor de B**, y no lo decido yo: el argumento técnico está escrito en el código *antes* de este
informe (`purchases/service.py:137-146`), lo que sugiere que se entendió durante la implementación y
no se ocultó. **A favor de A:** el comprobante es el ejemplo que el cliente leyó y firmó, y es la
pantalla de Marcela, que es quien más usa la cola.

H-02 no tiene dos salidas: RF-11 dice «cada pendiente», seis no lo dicen, y completarlo es agregar
dos claves a seis payloads.

## Validación de la skill

- [x] Los 23 requisitos tienen fila con estado. Ninguno quedó afuera
- [x] Ninguna fila `Implementado` sin archivo + símbolo, ruta o test
- [x] Se recorrió el sentido inverso: endpoints, pantalla, migraciones, parámetro y `kind`
- [x] Las 21 tareas ✅ se verificaron contra el archivo que nombran
- [x] Las decisiones de `plan.md` y su *Contexto de traspaso* se compararon contra el código
- [x] `validate.sh` pasa sobre los seis diagramas, y los seis se leyeron contra el código
- [x] Las cinco reglas del dominio se contrastaron contra lo que la feature promete
- [x] Hay veredicto, y cada hallazgo tiene tipo, rol dueño y acción
- [x] No se modificó código ni artefactos de otros roles: lo único escrito es este informe
