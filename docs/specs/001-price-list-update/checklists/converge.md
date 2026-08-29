**Rol:** Lead · **Skill:** `agents/skills/converge.md`
**Rama:** `feat/001-price-list-update` · **Spec:** `Aprobado`, con tres refirmas del 2026-08-29

| Corrida | Suite | Veredicto |
|---|---|---|
| 1ª — 2026-08-29 | 411 en verde, 95.30% | 🔴 Deriva mayor — ocho hallazgos, `C1` a `C8` |
| **2ª — 2026-08-29** | **511 en verde, 1 xfail ajeno, 95.01%** | **🟡 Deriva menor — el gate se levanta** |

> `review_feature` pregunta *¿está bien escrito?*. Esto pregunta *¿es lo que se acordó?*.
> Acá no se juzga tipado, cobertura ni fronteras: eso es del `Code-Reviewer`.

---

## Veredicto

# 🟡 Deriva menor — pasa al `Code-Reviewer`

**Los 45 requisitos firmados están implementados, cada uno con evidencia localizable.** No queda
ninguno parcial, no hay capacidad de negocio que ningún requisito pida, las 49 tareas están
respaldadas, y los ocho diagramas describen lo que el código hace.

Los ocho hallazgos de la primera corrida están cerrados y **verificados contra el código**, no
contra el registro de que se cerraron. Queda **un hallazgo nuevo**, que no bloquea: la
inmutabilidad de `raw` se volvió más angosta y sigue sin test que la sostenga.

Esta corrida no heredó nada de la anterior. Entre las dos, el código cambió por dos motivos
distintos: los cinco arreglos de `C1` a `C8`, y la migración de la autorización de todas las rutas
de esta feature, que hizo `002-access-control` sobre el mismo árbol.

---

## El hallazgo nuevo

| # | Tipo | Qué dice la regla | Qué hace el código | Rol dueño | Acción |
|---|---|---|---|---|---|
| **D1** | Contradicción con una regla del dominio | Artículo III: *«`raw` … **nunca se sobrescribe ni se corrige**»*, y `plan.md` lo sostenía con *«su repositorio sólo expone `insert` y `get`»* | Cerrar `C8` agregó `mark_normalized`, la primera escritura sobre `raw` posterior al insert. **No pierde evidencia** —toca una columna de contabilidad nuestra y no alcanza el contenido, el hash ni la fecha— y está argumentada en `plan.md`. Pero la regla pasó de *«no hay escrituras»* a *«hay exactamente una, y es angosta»*, y **nada lo verifica**: `tests/architecture/` no dice una palabra sobre `raw` | `Backend-Architect` | Escribir el test que fija la regla nueva. La Constitución lo pide de frente: un artículo verificable por una prueba automática lleva su prueba, y *«cualquier principio que dependa sólo de que alguien lo lea es una aspiración, no una regla»* |

**Por qué no bloquea.** No hay requisito sin implementar ni alcance sin pedir, que es lo que define
una deriva mayor. La evidencia que el Artículo III protege está intacta —de hecho `C8` la protege
**mejor** que antes, porque hasta ayer un archivo ilegible se perdía entero—. Lo que falta es la
guarda, no el comportamiento.

**Por qué se reporta igual, y no se deja pasar.** La decisión fue del `Backend-Architect` en esta
misma sesión, o sea mía. Un desvío que roza la autoridad número uno no se archiva porque quien lo
introdujo esté conforme: se escribe, con su dueño, y lo mira alguien más.

## Los ocho hallazgos de la primera corrida, y cómo se cerraron

| # | Estado | Qué se hizo |
|---|---|---|
| **C1** | ✅ Cerrado | `_register_price` apaga el destacado cuando la lista trae el mismo precio, y `_flag_missing` cuando el producto deja de venir. Dos tests de regresión en `test_price_variation.py` |
| **C2** | ✅ Cerrado | `PriceUpdateStatusRead.last_quarantined`, tipado desde el backend para que la pantalla no lea un diccionario suelto (`TS-05`), y la línea en `UpdateStatus.tsx` con enlace a revisión. Dos tests en `test_price_update_feature.py` |
| **C3** | ✅ Cerrado como spec | El canal de WhatsApp quedó **confirmado por el cliente el 2026-08-29**, y el aviso de recuperación es ahora **RF-44**, con su criterio de aceptación, su regla de negocio y su nota en `estados-actualizacion.mmd`. El código no se tocó: ya existía y ya tenía test, que ahora cita el requisito. **Firmado el 2026-08-29** (`/approve-spec`) |
| **C4** | ✅ Cerrado como spec | RF-11 y RF-12 dicen ahora *"dos consultas seguidas… sean programadas o pedidas a mano"*, con su criterio de aceptación, su regla de negocio y la nota de `estados-actualizacion.mmd`. El código ya se comportaba así. **Firmado el 2026-08-29** |
| **C5** | ✅ Cerrado como código | `operations.exception` y `operations.resolution_rule` guardan el nombre de quien decidió, escrito **en el momento de la decisión** y no consultado después: una decisión es un hecho histórico, y una proyección ataría la pantalla al estado actual de otro módulo. Migración `0004`, y `RuleList.tsx` cae al id sólo para las reglas anteriores al cambio |
| **C6** | ✅ Cerrado como spec | El cuarto motivo es **RF-45**: un historial ilegible se puede dar por revisado. El botón ya existía; ahora hay requisito, criterio, regla de negocio y test. **Firmado el 2026-08-29** |
| **C7** | ✅ Cerrado | `plan.md` dice 45 requisitos y dieciséis eventos, su tabla describe las cargas útiles reales, la advertencia sobre `raw` refleja la única escritura que existe, y hay una sección nueva de *Decisiones posteriores a la convergencia*. `tasks.md` cubre RF-41 a RF-45 |
| **C8** | ✅ Cerrado como código | La evidencia se commitea **antes** de interpretarla, y `raw.portal_document.normalized_at` marca que el pipeline logró leerla. El salteo dejó de preguntar *"¿ya tengo este archivo?"* para preguntar *"¿ya lo leí?"*, que es lo que impide que el reintento cierre la corrida como exitosa sobre un archivo que nadie leyó. Migración `0005`, con backfill |

**Los ocho quedaron resueltos.** Lo verificado hasta acá: `ruff`, `ruff format`, `mypy --strict`
sobre los cinco módulos de la feature, `tsc --noEmit` y `prettier`, todos limpios. Los dos cambios
con riesgo real —C5 y C8— se comprobaron además contra la base:

```
caso  -> resolved_by_user_id=1 resolved_by_name='Marcela'
regla -> created_by_user_id=1 created_by_name='Marcela'

intento 1 -> falló: The daily file has no data rows
evidencia -> guardada, normalized_at=None
intento 2 -> falló: The daily file has no data rows
```

**La suite completa no se pudo correr**, y no por esta feature: `002-access-control` está
reemplazando la autorización por roles con secciones y niveles en este mismo árbol, y
`tests/conftest.py` y `app/modules/identity/` quedaron momentáneamente inconsistentes entre sí. Los
tests de C1, C2 y C5 llegaron a correr en verde antes de eso; los de C6 y C8 están escritos y sin
ejecutar.

**El veredicto sigue sin levantarse** hasta que la suite entera vuelva a pasar y `/converge` se
corra de nuevo. Las tres enmiendas de la spec ya están firmadas: lo único que falta es que el
refactor de `002-access-control` deje de romper `tests/conftest.py`.

## Hallazgos

| # | Tipo | Qué dice lo firmado | Qué hace el código | Rol dueño | Acción |
|---|---|---|---|---|---|
| **C1** | Requisito sin implementar (RF-25) | «El sistema debe destacar los productos cuyo precio vigente **subió más que el porcentaje configurado respecto del precio que tenían en la actualización anterior**.» Y `estados-precio.mmd` nombra la transición: *Destacado → Vigente: la actualización siguiente no supera el porcentaje* | El destacado **nunca se apaga** mientras el precio no vuelva a moverse. `catalog/service.py:383-386` sale temprano cuando el precio no cambió y no toca `is_highlighted` | `Developer`, después `Tester` | Recalcular el destacado también cuando el precio se repite (suba 0%), y fijarlo con un test |
| **C2** | Requisito sin implementar (RF-27) | «Cuando termine una actualización, el sistema debe informar cuántas filas quedaron apartadas.» CA-27: *al terminar una actualización **se puede ver** cuántas filas quedaron apartadas* | El número se calcula y se guarda (`operations/service.py::record_price_update_result`) y la API lo sirve (`GET /price-updates/{id}` y `/status.last_result`), pero **ninguna pantalla lo muestra**. En el momento exacto que el requisito nombra, `UpdateNowButton.tsx` dice sólo «Listo: se trajo la lista del portal». Ningún test lo verifica | `Developer` (frontend), después `Tester` | Mostrar el conteo al terminar la corrida, y un test que lo fije |
| **C3** | Alcance no pedido | Ningún RF pide un aviso de recuperación. RF-12 pide el aviso de interrupción y RF-13 que no se repita | `PriceUpdateRecovered` → `notifications/handlers.py::tell_the_owner_it_is_back` manda un WhatsApp al dueño: *«✅ Cordillera: la actualización de precios volvió a funcionar»* | **Humano** | Aceptarlo y agregarle su RF, o quitarlo. Es un mensaje al teléfono del cliente que el cliente no pidió |
| **C4** | Requisito sin implementar (RF-11, RF-12) | Los dos requisitos, sus criterios de aceptación y `estados-actualizacion.mmd` dicen **«dos consultas programadas seguidas»** | `operations/service.py::_consecutive_failures` cuenta **cualquier** corrida fallida de `extract_price_list`, incluidas las pedidas a mano. Dos clics en «Actualizar ahora» con el portal caído marcan la actualización como interrumpida y disparan el WhatsApp | **Humano** → `Developer` o `Solution-Designer` | O se filtra por corrida programada (`payload.requested_by_user_id is None`), o se corrige la redacción del requisito |
| **C5** | Requisito sin implementar (RF-32, RF-36) | «…**quién lo decidió** y cuándo», «…junto con **quién las tomó** y cuándo» | La pantalla muestra `usuario #3`: `RuleList.tsx` renderiza `created_by_user_id`. El dato está registrado, pero un número no le dice a Marcela quién fue | `Solution-Designer` con el `Backend-Architect` | Decidir cómo llega el nombre sin romper el Artículo IV: proyección de nombres alimentada por `UserRegistered`, o aceptar el id |
| **C6** | Alcance no pedido (menor) | Los tres motivos que la spec nombra son fila ilegible (RF-29), producto desconocido (RF-30) y producto que dejó de figurar (RF-31) | Existe un cuarto: `unreadable_history`, con su botón *«Dar el historial por revisado»* (`CaseCard.tsx`). Es la consecuencia necesaria de RF-39 + RF-33 —sin él ese caso no se vacía nunca de la cola—, pero ningún requisito lo nombra | `Solution-Designer` | Agregarle su RF. No hay que tocar código |
| **C8** | Contradicción con una regla del dominio | RF-05: «Cuando el sistema obtenga una lista de precios, debe **conservarla tal como llegó del portal**», y el Artículo III existe para que quede *«la única evidencia de qué dijo el portal»* | Con RF-41, una lista vacía **no se conserva**. `portal/service.py` publica dentro de su propia transacción y commitea después, así que cuando el parser corta, el `INSERT` en `raw.portal_document` se va con el rollback: del día que falló no queda el archivo que el portal entregó. `portal/tasks.py:64-67` lo dice como decisión —*«one run either lands whole or does not land at all»*— pero es anterior a RF-41 | **Humano** con el `Backend-Architect` | Confirmar que se acepta, o commitear `raw` antes de normalizar. Ninguna de las dos es obvia: la segunda parte la corrida en dos transacciones |
| **C7** | Deriva del plan | `plan.md` dice «los **37** requisitos» (son 40), «**nueve** eventos nuevos» en el Constitution Check contra «**Catorce**» en su propia tabla, y esa tabla describe cargas útiles que la implementación cambió | El código es correcto y los cambios están justificados en `tasks.md` → *Decisiones tomadas durante la implementación*, pero **`plan.md` no se actualizó**: quien lo lea después va a leer un catálogo de eventos que no existe | `Backend-Architect` | Actualizar `plan.md` para que describa lo que el código hace |

**Ninguno de los ocho se arregló durante esta corrida.** El `Lead` no edita código ni artefactos de
otros roles: arreglar sobre la marcha destruye el hallazgo.

---

## Trazabilidad — los 45 requisitos contra el código

| Requisito | Dónde está | Evidencia | Estado |
|---|---|---|---|
| RF-01 | `operations/tasks.py::tick_price_update` | Latido de 15 min en `beat_schedule["price-update-tick"]`; `due_for_update()` decide contra `interval_hours` | Implementado |
| RF-02 | `catalog/service.py::apply_price_batch` | `seeding = await self.catalog.count_products() == 0`: sólo la primera lista da de alta | Implementado |
| RF-03 | `catalog/service.py::_register_price` | Escribe `core.product_price` por cada producto conocido del lote | Implementado |
| RF-04 | `GET /prices` · `(private)/precios/page.tsx` | `catalog/routes.py:43` + `PriceTable.tsx`: código, descripción y precio | Implementado |
| RF-05 | `portal/service.py::extract_price_list` | `insert` guarda los bytes tal cual con su `sha256`, y desde `C8` se **commitea antes** de intentar interpretarlos | Implementado |
| RF-06 | `ingestion/service.py::normalize_price_list` | Cada fila sale `VALID` o `QUARANTINED`; el bucle no corta | Implementado |
| RF-07 | `catalog/service.py::apply_price_batch` | `if product is None and not seeding` → `UnknownProductsObserved`, sin alta | Implementado |
| RF-08 | `catalog/service.py::_flag_missing` | `price.is_stale = True` conservando precio y `effective_at`; badge «No vino en la última lista» | Implementado |
| RF-09 | `GET /price-updates/status` | `last_successful(PRICE_UPDATE_TASK)` → `UpdateStatus.tsx` | Implementado |
| RF-10 | `operations/service.py::record_price_update_failure` | Guarda `status=FAILED` y `error` en `JobRun` | Implementado |
| RF-11 | `price_update_status.is_stalled` | `failures >= STALL_THRESHOLD` → recuadro rojo en `UpdateStatus.tsx`. El requisito ya no dice «programadas», que es lo que el código hacía | Implementado |
| RF-12 | `notifications/handlers.py::warn_the_owner` | `PriceUpdateStalled` → `send_whatsapp.delay(...)` | Implementado |
| RF-13 | `record_price_update_failure` | `if failures == STALL_THRESHOLD`: publica en la transición exacta, una sola vez | Implementado |
| RF-14 | `POST /price-updates` | `operations/routes.py:154` + `UpdateNowButton.tsx` | Implementado |
| RF-15 | `request_price_update` | `pg_try_advisory_xact_lock` → `ConflictError` 409; fijado en `test_price_update_concurrency.py` | Implementado |
| RF-16 | `GET /price-updates/{job_run_id}` | Ruta aparte de `/status` a propósito; `UpdateNowButton.follow()` la sigue hasta el final | Implementado |
| RF-17 | `request_price_update` | `payload={"requested_by_user_id": ...}` sobre el `JobRun` | Implementado |
| RF-18 | `PUT /price-updates/settings` | `require_roles()` (sólo OWNER) + `SettingsForm.tsx` | Implementado |
| RF-19 | idem | `highlight_threshold_pct` en el mismo endpoint | Implementado |
| RF-20 | `DEFAULT_INTERVAL_HOURS` · `DEFAULT_HIGHLIGHT_THRESHOLD` | 12 y 10, sembrados además en `0002_price_update.py` | Implementado |
| RF-21 | `operations/service.py::due_for_update` | Lee el parámetro en cada latido: la frecuencia nueva rige desde la consulta siguiente | Implementado |
| RF-22 | `catalog/service.py::_register_price` | `add_point` sólo cuando el precio cambió | Implementado |
| RF-23 | `GET /prices/{id}/history` · `precios/[productId]/page.tsx` | Tabla de puntos con fecha, precio y origen | Implementado |
| RF-24 | `catalog/service.py::_variation` + `last_point_before(_start_of_month())` | Criterio fijado en `data-model.md:170`: el último punto anterior al primer día del mes corriente | Implementado |
| RF-25 | `catalog/service.py::_register_price` | `is_highlighted = variation > threshold`, y **se apaga** cuando el precio se repite o el producto deja de venir. Borde y apagado fijados en `test_price_variation.py` | Implementado |
| RF-26 | `GET /triage/cases` · `(private)/revision/page.tsx` | `CaseCard.tsx` muestra `reason`, el extracto y el payload | Implementado |
| RF-27 | `PriceUpdateStatusRead.last_quarantined` · `UpdateStatus.tsx` | Tipado desde el backend y en pantalla, con enlace a revisión; sirve la corrida programada tanto como la pedida a mano | Implementado |
| RF-28 | `_flag_missing` → `KnownProductsMissing` | `triage/handlers.py:70` abre el caso; el badge lo señala en la lista | Implementado |
| RF-29 | `catalog/service.py::set_price_by_code` | Handler de `QuarantineCaseResolved`; el precio queda vigente | Implementado |
| RF-30 | `catalog/service.py::incorporate_product` | `incorporate` da de alta; `ignore` deja la fila fuera por regla | Implementado |
| RF-31 | `discontinue` · `keep_active` | Las dos decisiones que el caso admite | Implementado |
| RF-32 | `triage/service.py::resolve` | `resolved_by_user_id`, **`resolved_by_name`**, `resolved_at` y `decision`, escritos en el momento de la decisión | Implementado |
| RF-33 | `triage/service.py::resolve` | `status = RESOLVED`; el listado filtra `PENDING` por defecto | Implementado |
| RF-34 | `ingestion/service.py::_apply_unreadable_rule` y `_rules_by_code` | La proyección `staging.resolution_rule` se reaplica al normalizar | Implementado |
| RF-35 | `triage/repository.py::open_case` | Índice único parcial `uq_exception_pending_fingerprint … WHERE status = 'PENDING'` | Implementado |
| RF-36 | `GET /triage/rules` · `RuleList.tsx` | Regla, decisión, **nombre** del autor y fecha, con botón de anular | Implementado |
| RF-37 | `triage/service.py::revoke_rule` | `reopen_by_rule` + `QuarantineRuleRevoked` → `ingestion.forget_rule` y `catalog.undo_rule` | Implementado |
| RF-38 | `portal/handlers.py::bring_published_history` | `ProductsRegistered` encola una visita por producto, espaciada | Implementado |
| RF-39 | `ingestion/service.py::normalize_product_history` | El punto ilegible va a `staging` y abre caso; el precio vigente no se toca | Implementado |
| RF-40 | `catalog/repository.py:157` | `on_conflict_do_nothing(constraint="uq_price_point_product_changed")` | Implementado |
| RF-41 | `ingestion/parsers.py::parse_price_list` | `if not parsed: raise ExtractionError("The daily file has no data rows")`; `portal/tasks.py::_report_failure` cierra la corrida como `FAILED` con su motivo, en una sesión propia | Implementado |
| RF-42 | idem | Al cortar antes de publicar, `catalog` nunca recibe el lote y `_flag_missing` no corre. Fijado en `test_price_pipeline.py:233` | Implementado |
| RF-43 | `ingestion/parsers.py::parse_product_history` | Distingue *no hay tabla* (falla técnica) de *la tabla no publica precios* (`return []`, sin puntos y sin caso) | Implementado |
| RF-44 | `notifications/handlers.py::tell_the_owner_it_is_back` | `PriceUpdateRecovered` se publica sólo al salir de una interrupción; `test_coming_back_is_reported_too` fija que la corrida exitosa siguiente no manda nada | Implementado |
| RF-45 | `triage/service.py::resolve` · `CaseCard.tsx` | El caso `unreadable_history` se da por revisado y sale de los pendientes; fijado en `test_triage_feature.py` | Implementado |

---

## Sentido inverso — ¿qué pide cada cosa que existe?

| Superficie | Qué requisito la pide |
|---|---|
| `GET /prices`, `GET /prices/{id}/history` | RF-04, RF-23 |
| `GET /price-updates/status`, `POST /price-updates`, `GET /price-updates/{id}` | RF-09/RF-11, RF-14/RF-15/RF-17, RF-16 |
| `GET` y `PUT /price-updates/settings` | RF-18, RF-19 |
| `GET /triage/cases`, `POST …/resolution`, `GET /triage/rules`, `DELETE /triage/rules/{id}` | RF-26, RF-29 a RF-33, RF-36, RF-37 |
| Cuatro pantallas bajo `(private)/` | RF-04, RF-23, RF-18/RF-19, RF-26 |
| `raw.portal_document`, `staging.*`, `core.*`, `operations.exception`, `operations.resolution_rule` | RF-05, RF-06, RF-02/RF-03/RF-22, RF-26, RF-34 |
| `portal.extract_price_list`, `portal.extract_product_history`, `operations.tick_price_update`, `notifications.send_whatsapp` | RF-01, RF-38, RF-21, RF-12 |
| Filtro `?highlighted=true` y solapa «Solo los que subieron fuerte» | H6 — *«mirar sólo lo que se salió de lo normal en lugar de recorrer los cien productos»* |
| Aviso de recuperación por WhatsApp | RF-44 |
| Caso `unreadable_history` y su botón | RF-45 |

Andamiaje que `plan.md` justifica y por lo tanto no es hallazgo: el cliente Playwright sin superficie
HTTP, las proyecciones `staging.resolution_rule` y `core.catalog_setting`, `JobRunSucceeded`,
`BusinessParameterChanged` y `core.product.registered_by_rule_id`.

`GET /operations/jobs` y `GET`/`PUT /operations/parameters` **no son de esta feature**: son la
superficie que `plan.md` declara preexistente (*«`JobRun` y `Parameter` ya existen y no se tocan»*).
Viajan en el mismo changeset por lo que está más abajo.

---

## Tareas declaradas completas

Las **49 de `tasks.md` están respaldadas**: cada una nombra un archivo o un símbolo que existe y
hace lo que la tarea dice. No hubo ninguna *Tarea sin respaldo*.

Dos que valía la pena abrir porque se declaran solas: la 13 («actualiza el mapa de módulos de
`ARCHITECTURE.md`») está cumplida —`ARCHITECTURE.md:101` lista `notifications/`—, y la 22 (semilla de
los dos parámetros) está en `0002_price_update.py`, con `alembic check` limpio.

La cobertura declarada en `tasks.md` sí quedó optimista en un punto: la tabla dice que **RF-27** lo
cubre el test 42, y ningún test verifica el conteo por corrida (C2).

---

## Diagramas

`bash scripts/diagrams/validate.sh` pasa: los **ocho compilan**. Leídos contra el código:

- `flujo-general.mmd` — el orden de los pasos es el que el pipeline hace, actor por actor. ✅
- `estados-fila.mmd` — las transiciones existen, incluidas las notas sobre la primera lista y el
  único pendiente por caso repetido. ✅
- `estados-precio.mmd` — la transición *Destacado → Vigente* que el diagrama dibujaba y el código
  no hacía **ahora ocurre**: era el diagrama el que tenía razón. ✅
- `estados-actualizacion.mmd` — ya no dice «programadas», y su nota sobre `Exitosa` menciona el
  aviso de recuperación. Coincide con el código. ✅
- `estados-fila.mmd` no cambió y sigue siendo verdad: RF-45 resuelve un caso de **historial**, que
  no es una fila de la lista del día. ✅

---

## Reglas del dominio

Ninguna de las cinco resulta violada, y ningún requisito firmado obliga a violarlas.

| Regla | Verificación |
|---|---|
| SIGProv es sólo lectura | El módulo `portal` no expone forma de escribir: sus dos métodos descargan y devuelven bytes |
| Automatización de navegador, no cliente HTTP | `grep -rnE "httpx\|requests\.\|aiohttp" app/modules/portal/` → sin resultados |
| Nada se descarta | Cuarentena en `staging` + fila en `operations.exception`, visible en la pantalla de revisión |
| Flujo unidireccional, `raw` inmutable | El historial pasa por `staging` igual que la lista, y el repositorio no expone `update` ni `delete`. La **única** escritura posterior al insert es `mark_normalized`, que no alcanza el contenido → **D1** |
| Credenciales sólo en el entorno | `PortalClient._unreadable` envuelve todo error de Playwright antes de propagarlo |

---

## Antes de `/ship` — el changeset arrastra otras features

No es un hallazgo de convergencia, pero le toca al `Lead` decirlo porque `/ship` viene después.

`main` no tiene ningún módulo (`git ls-tree main backend/app/modules/` devuelve sólo `__init__.py`),
así que **todo lo que está sin commitear viaja junto**. Y no todo es de 001:

- `backend/app/modules/identity/` y el frontend de autenticación — son **002-access-control**.
- La base de `operations` (`JobRun`, `Parameter`, `/health`) — preexistente según `plan.md`.
- Las specs **002 a 009** enteras, sin commitear.
- Cuatro fixtures de **004-invoices-suppliers** (`invoices-page-2026-08-29.html`, dos PDF y una
  planilla) que ningún test usa todavía, más las ediciones de `PROJECT_BRIEF.md` y
  `FDE_ASSESSMENT.md`.

El PR de 001 los incluiría a todos. Separarlos o no es decisión del humano con el
`Release-Manager`; queda dicho antes de que el commit lo decida solo.

---

## Cómo se cerraron los ocho, y qué enseña

Ante una deriva mayor las salidas eran dos, y la elección fue del humano. Se usaron **las dos**, y
el reparto es la parte que conviene recordar:

- **Se arregló el código** en los que el requisito tenía razón: `C1` el destacado que no se apagaba,
  `C2` el conteo que existía y no se veía, `C5` el `usuario #3`, `C8` la evidencia que se perdía.
- **Se corrigió la spec** en los que el código tenía razón y la letra no: `C3` el aviso de
  recuperación, que existía sin requisito, y `C4` la interrupción, que la spec limitaba a las
  consultas programadas cuando el negocio quiere enterarse igual. `C6` fue un requisito que faltaba
  para una capacidad necesaria.
- **`C7` no era ninguna de las dos**: un plan desactualizado no se negocia con el cliente, se
  actualiza.

Tres refirmas en un día, ninguna silenciosa: `spec.md` lleva la tabla con fecha y firmante de cada
una. Que la mitad de los hallazgos se resolvieran cambiando el acuerdo y no el código es el
resultado sano — significa que el gate encontró desacuerdos reales y no sólo bugs.

---

## Lo que este informe no mira

Tipado, cobertura, fronteras entre módulos, nombres y formato: eso es `/review-feature`, y va
después. Va con tres cosas anotadas para el `Code-Reviewer`:

1. **D1** — el test que fije la escritura angosta sobre `raw`.
2. El **H3** de [`tests.md`](tests.md): `rows_of_batch` y `history_rows_of_product` siguen sin
   llamadores. Las otras dos preguntas de ese informe ya están cerradas y verificadas acá.
3. `002-access-control` tiene **14 de sus 41 tareas abiertas** y comparte árbol con esta feature.
   Su `xfail` —el 403 que todavía no se registra— es suyo y está documentado con su dueño, pero el
   review de 001 corre sobre un working tree que se mueve.
