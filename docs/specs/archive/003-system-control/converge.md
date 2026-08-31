# Informe de convergencia — 003-system-control

**Feature:** 003-system-control · **Fecha:** 2026-08-30 · **Rol:** `Lead`
**Spec:** `spec.md`, Aprobada el 2026-08-29 por Leandro Carriego — FDE
**Changeset:** commits `38ab165`, `519a8db`, `8df1c19`, mergeados a `main` en el PR #20 (`a2d7201`)

> `review_feature` pregunta *¿está bien escrito?*. Este informe contesta la otra:
> **¿es lo que se acordó?** No juzga calidad de código, ni tipado, ni cobertura. Juzga
> correspondencia entre lo firmado y lo que existe.

## Veredicto: 🔴 DERIVA MAYOR

Hay requisitos firmados cuya implementación está incompleta. Ninguno está ausente del todo —no
hay agujeros vacíos— pero **siete de los treinta y tres cumplen sólo una parte de lo que
prometen**, y en dos casos la parte que falta es la mitad del requisito, no un borde.

Por el procedimiento, una deriva mayor **bloquea el paso al `Code-Reviewer`**. Acá esa
consecuencia llega tarde: la feature ya está mergeada a `main`, por decisión tuya y con el
estado de los gates escrito en el PR. Así que lo que este veredicto cambia no es si entra —ya
entró— sino **qué hay que resolver antes de desplegar y archivar la spec**, que es el próximo
punto donde la 003 se declara terminada.

**La decisión de qué corregir —el código o el acuerdo— es tuya, no mía.** Cada hallazgo mayor
baja con sus dos salidas y lo que cuesta cada una.

## Cómo se verificó

Diez verificaciones en paralelo, todas de sólo lectura: cinco recorrieron los 33 requisitos
contra el código buscando evidencia localizable, y cinco fueron en sentido inverso —alcance que
ningún requisito pide, tareas marcadas completas sin respaldo, deriva respecto de `plan.md` y
`data-model.md`, los siete diagramas contra la conducta real, y las cinco reglas inviolables del
dominio.

Ninguna fila dice «Implementado» por el nombre de un método: la evidencia es el cuerpo del
método o el test que lo ejercita. **Que la suite pase no fue tomado como prueba de nada** — un
test verde que no ejercita la condición que el requisito pide deja al requisito en `Parcial`.

## Tabla de trazabilidad

| Requisito | Qué promete la spec | Dónde está implementado | Estado |
|---|---|---|---|
| RF-01 | Una sola pantalla lista todos los parámetros configurables con su valor vigente. | backend/app/shared/parameters.py::PARAMETERS (7 specs) · backend/app/modules/operations/service.py::OperationsService.list_parameters · routes.py::list_parameters (GET /operations/parameters) ·… | ✅ Implementado |
| RF-02 | El dueño puede cambiar el valor de un parámetro configurable. | backend/app/modules/operations/service.py::OperationsService.set_parameters · routes.py::update_parameters (PUT /operations/parameters) · frontend/app/actions/parameters.ts::saveParameter ·… | ✅ Implementado |
| RF-03 | Los roles distintos de dueño no pueden cambiar un parámetro. | backend/app/modules/operations/routes.py (dependencies=[require_section(Section.SYSTEM_PARAMETERS)] y (…, Level.WRITE)) · backend/app/modules/identity/permissions.py::MATRIX[Section.SYSTEM_PARAMETERS] ·… | ✅ Implementado |
| RF-04 | Mientras el dueño no lo haya cambiado, el sistema usa el valor inicial del parámetro. | backend/app/shared/parameters.py::ParameterSpec.initial / stored_initial · service.py::get_parameter_value · identity/service.py::DEFAULT_IDLE_MINUTES = int(initial_value(IDLE_MINUTES_KEY)) | ✅ Implementado |
| RF-05 | Junto a cada parámetro se muestra qué cambia en el sistema cuando se lo modifica. | backend/app/shared/parameters.py::ParameterSpec.effect (una frase en español por spec) · operations/schemas.py::ParameterRead.effect · frontend/components/operations/ParameterRow.tsx | ✅ Implementado |
| RF-06 | Un valor fuera del rango admitido se rechaza informando el rango. | backend/app/shared/parameters.py::ParameterSpec.coerce / _as_number / _as_time_of_day / range_text · spec_for() para la clave desconocida · frontend ParameterRow muestra el mensaje del backend | ✅ Implementado |
| RF-07 | El valor nuevo se aplica sin ninguna intervención adicional. | backend/app/modules/operations/service.py::due_for_update / interval_hours / highlight_threshold (leen el parámetro en cada uso) · catalog/handlers.py::remember_parameter · identity/service.py::_setting + resolve_session | ✅ Implementado |
| RF-08 | Cada cambio de parámetro registra valor anterior, valor nuevo, quién y cuándo. | backend/app/modules/operations/service.py::set_parameters → record_manual_change (ManualChangeRecorded con old_value/new_value/actor_user_id/section=SYSTEM) · repository.py::AuditEntryRepository.insert · migración… | ✅ Implementado |
| RF-09 | Cuando una persona cargue o modifique un dato a mano, el sistema registra quién lo hizo y cuándo. | backend/app/modules/operations/handlers.py::write_the_log · backend/app/modules/operations/service.py::OperationsService.record_manual_change · backend/app/modules/operations/models.py::AuditEntry (actor_user_id,… | 🟡 Parcial |
| RF-10 | Al modificar a mano un dato existente, el sistema conserva el valor que tenía antes. | backend/app/modules/operations/models.py::AuditEntry.old_value · backend/app/shared/corrections.py::CorrectionColumns.portal_value · backend/app/modules/catalog/service.py::CatalogService.apply_correction | ✅ Implementado |
| RF-11 | Toda modificación manual de un dato existente exige un motivo elegido de una lista, y admite un detalle escrito. | backend/app/shared/corrections.py::CorrectionReason y REASON_LABELS (cinco motivos) · backend/app/modules/catalog/schemas.py::CorrectionWrite · backend/app/modules/catalog/service.py::CatalogService._reason ·… | ✅ Implementado |
| RF-12 | El historial muestra el motivo de cada cambio. | backend/app/modules/operations/service.py::OperationsService._audit_read (reason_label) · backend/app/shared/corrections.py::label_for · frontend/components/operations/AuditTable.tsx (columna «Por qué») | ✅ Implementado |
| RF-13 | El historial de cambios manuales se muestra ordenado por fecha. | backend/app/modules/operations/repository.py::AuditEntryRepository.list y .list_for_entity (order_by(AuditEntry.occurred_at.desc(), AuditEntry.id.desc())) · frontend/app/(private)/historial/page.tsx | ✅ Implementado |
| RF-14 | Se puede filtrar el historial por persona y por rango de fechas. | backend/app/modules/operations/repository.py::AuditEntryRepository._filtered · backend/app/modules/operations/routes.py::list_audit (params actor_user_id, since, until) · backend/app/shared/time.py::as_business_time ·… | ✅ Implementado |
| RF-15 | Desde cualquier dato modificado a mano se llega a su historial de cambios. | backend/app/modules/operations/routes.py::audit_for_entity (GET /operations/audit/{entity_type}/{entity_id}) · frontend/app/(private)/precios/[productId]/page.tsx (dos Link a /historial?entidad=…&id=…) ·… | 🟡 Parcial |
| RF-16 | El sistema impide que un registro del historial se modifique. | backend/alembic/versions/0006_manual_change_log.py (APPEND_ONLY_FUNCTION + APPEND_ONLY_TRIGGER, op.execute en :118-119) · backend/app/modules/operations/models.py (mismos statements colgados del metadata) ·… | ✅ Implementado |
| RF-17 | El sistema impide que un registro del historial se elimine. | backend/alembic/versions/0006_manual_change_log.py (APPEND_ONLY_TRIGGER + NO_TRUNCATE_TRIGGER, op.execute en :118-120) · backend/app/modules/operations/models.py::NO_TRUNCATE_TRIGGER ·… | ✅ Implementado |
| RF-18 | El dueño ve el historial de cambios manuales de todas las personas. | backend/app/modules/identity/dependencies.py::ROLE_SECTIONS / visible_sections (OWNER → frozenset(BusinessSection)) · backend/app/modules/operations/routes.py::list_audit ·… | ✅ Implementado |
| RF-19 | Los roles distintos de dueño ven únicamente los cambios manuales de las secciones a las que tienen acceso. | backend/app/modules/identity/dependencies.py::ROLE_SECTIONS, visible_sections, VisibleSections · backend/app/modules/operations/repository.py::AuditEntryRepository._filtered (section.in_(...)) ·… | ✅ Implementado |
| RF-20 | Reunir en una sola pantalla las acciones de carga y corrección disponibles (CA: «hay una sola pantalla desde la que se llega a todas las cargas y correcciones»). | frontend/app/(private)/acciones/page.tsx::ActionsPage · frontend/lib/operations/actions.ts::MANUAL_ACTIONS (línea 40) · frontend/components/auth/Navigation.tsx (enlace «Acciones») ·… | ✅ Implementado |
| RF-21 | Mostrar a cada persona únicamente las acciones habilitadas para su rol (CA: «esa pantalla le muestra a Marcela acciones distintas de las que le muestra a Julián»). | frontend/lib/operations/actions.ts::actionsFor (línea 148) · frontend/lib/auth/permissions.ts::canEdit/canSee · backend/app/modules/identity/permissions.py::MATRIX/level_for ·… | ✅ Implementado |
| RF-22 | Cuando una acción manual termine, informar a quien la ejecutó si se aplicó o si falló (CA: «ejecutada una acción, quien la ejecutó ve si se aplicó o si falló»). | Mitad que falla: frontend/lib/api/write.ts::callApi + backend/app/main.py::_error_body/handle_domain_error + backend/tests/integration/api/test_action_outcomes.py. Mitad que se aplica:… | 🟡 Parcial |
| RF-23 | Se puede corregir a mano cualquier dato traído del portal: importes, fechas, números de comprobante y nombres de proveedor. | backend/app/modules/catalog/service.py::CORRECTABLE_FIELDS y ::CatalogService.apply_correction (+ ::_as_text, ::_as_number, ::_length_of) · POST /api/v1/catalog/products/{product_id}/corrections | ✅ Implementado |
| RF-24 | Sólo corrige un dato quien tiene acceso a la sección a la que ese dato pertenece. | backend/app/modules/catalog/routes.py::correct_product (dependencies=[require_section(Section.PRODUCT_CATALOG, Level.WRITE)]) · backend/app/modules/identity/permissions.py::MATRIX[Section.PRODUCT_CATALOG] | ✅ Implementado |
| RF-25 | Al corregir un dato traído del portal, lo que el portal había informado se conserva sin cambios. | backend/app/modules/catalog/service.py::CatalogService._store_correction · backend/app/modules/catalog/models.py::Correction (mixin app/shared/corrections.py::CorrectionColumns) ·… | ✅ Implementado |
| RF-26 | Todo dato que difiera de lo que informó el portal queda señalado como corregido a mano. | backend/app/modules/catalog/service.py::CatalogService._marks y ::_price_read · backend/app/modules/catalog/schemas.py::CorrectionMark · frontend/components/catalog/PriceTable.tsx ·… | 🟡 Parcial |
| RF-27 | Junto a un dato corregido a mano se muestra el valor que había informado el portal. | frontend/app/(private)/precios/[productId]/page.tsx (encabezado «Descripción corregida a mano · el portal decía …», bloque «Precio vigente · Corregido a mano · el portal decía …», lista de correcciones al pie) ·… | ✅ Implementado |
| RF-28 | Si una actualización posterior del portal trae un valor distinto del original sobre un dato corregido, se señala para revisión en la pantalla de ese dato en lugar de pisar la… | backend/app/modules/catalog/service.py::CatalogService._check_conflict y ::_register_price · frontend/app/(private)/precios/[productId]/page.tsx (banner «El portal informa otro valor») ·… | 🟡 Parcial |
| RF-29 | Ese mismo conflicto le llega al dueño como aviso, sin que tenga que mirar la pantalla. | backend/app/modules/notifications/handlers.py::warn_about_a_contradicted_correction · backend/app/modules/notifications/service.py::conflict_message y ::NotificationService.notify_owner ·… | 🟡 Parcial |
| RF-30 | El dueño —y sólo el dueño— puede dejar sin efecto una corrección manual; su criterio de aceptación agrega que lo hace «desde el historial». | backend/app/modules/catalog/service.py::CatalogService.revert_correction (línea 877) · backend/app/modules/catalog/routes.py::revert_correction (DELETE /api/v1/catalog/corrections/{correction_id}, línea 126) ·… | 🟡 Parcial |
| RF-31 | Anulada la corrección, el dato vuelve a mostrar el valor que informó el portal —no el valor anterior. | backend/app/modules/catalog/service.py::CatalogService.revert_correction (líneas 903-914) y ::_store_correction (líneas 1004-1013) | ✅ Implementado |
| RF-32 | La anulación queda registrada: quién la anuló y cuándo, y figura en el historial. | backend/app/modules/catalog/service.py::revert_correction (líneas 918-937) · backend/app/shared/corrections.py:122-123 (reverted_by_user_id, reverted_at) · backend/alembic/versions/0007_manual_corrections.py:67-68 | ✅ Implementado |
| RF-33 | No se puede dejar sin efecto una corrección sobre un dato que no fue traído del portal. | backend/app/modules/catalog/service.py::_came_from_the_portal (línea 1180) · ::_store_correction (líneas 987-993) · ::revert_correction (líneas 884-891) · backend/app/modules/catalog/models.py::PriceSource +… | ✅ Implementado |
**26 Implementado · 7 Parcial · 0 Ausente.**

## Hallazgos

45 en total: **7 mayores** y 38 menores. Por tipo: 20 deriva del plan, 16 requisito sin
implementar, 4 tarea sin respaldo, 3 contradicción con una regla del dominio, 2 diagrama
desactualizado.

Los siete mayores son en realidad **cuatro problemas**: tres agentes distintos, mirando
historias distintas, llegaron por su cuenta al mismo hallazgo sobre RF-09. Esa coincidencia es
la parte que más conviene creerle.

### M1 · La bitácora no cubre la carga manual, y RF-09 dice «cargue»

**Qué dice lo firmado.** RF-09: *«Cuando una persona **cargue** o modifique un dato a mano, el
sistema debe registrar quién lo hizo y cuándo»*, con su criterio *«Después de que Marcela carga
algo a mano, ese dato muestra su nombre y la fecha»*. La regla de negocio firmada lo repite:
*«Toda edición manual deja rastro… **Sin excepciones** y sin importar quién la haga»*. La
historia se titula «Cada cambio manual queda registrado».

**Qué hace el código.** Sólo la mitad «modifique». `ManualChangeRecorded` se publica en
exactamente tres lugares: corregir, anular y cambiar un parámetro. `AuditAction.CREATED` está
declarado en el catálogo de eventos y **no lo publica nadie** — ningún test lo menciona tampoco.
El único camino de carga manual que hoy existe —resolver un caso de la cola de revisión— no
escribe una sola línea de bitácora. Y no es un camino teórico: es una de las cuatro acciones que
**esta misma feature** publica en la pantalla de RF-20 como acción manual.

**Las dos salidas.**
1. **Implementarlo** — publicar `ManualChangeRecorded` con `AuditAction.CREATED` desde el camino
   de resolución de casos. Vuelve al `Developer` y después al `Tester`. Arrastra una decisión de
   alcance: ¿una carga exige motivo, como RF-11 pide para toda modificación?
2. **Acotar la spec** — reescribir RF-09 y la regla «sin excepciones» para que digan qué cargas
   cubre la bitácora. Vuelve al `Solution-Designer`, **y la spec se vuelve a firmar**: el gate
   de la firma se reabre.

### M2 · El conflicto del portal sólo se detecta sobre el precio, no sobre la descripción

**Qué dice lo firmado.** RF-28: *«Si una actualización posterior del portal trae para un dato
corregido a mano un valor distinto del original, el sistema debe señalarlo para revisión en la
pantalla de ese dato, en lugar de pisar la corrección»*. RF-29: ese conflicto le llega al dueño.
El diagrama `estados-dato.mmd` dibuja «Corregido → En conflicto» **sin distinguir campos**.

**Qué hace el código.** La detección corre sobre la fila de precio: `price` y `currency`. Para
`description` —el tercer campo corregible, y el único texto que el portal informa— el pipeline
nunca reescribe la descripción de un producto ya conocido, así que la comparación **no se invoca
jamás**. La corrección no se pisa, pero tampoco se marca en conflicto ni se avisa: si el portal
cambia la descripción de un producto cuya descripción alguien corrigió, nadie se entera.

**Las dos salidas.**
1. **Implementarlo** — comparar la descripción entrante contra la corrección vigente y publicar
   el conflicto como ya se hace con precio y moneda. `Developer`, después `Tester`.
2. **Acotar RF-28/RF-29** en la spec a los datos que el portal reinforma. `Solution-Designer` y
   nueva firma.

Antes de eso hay una pregunta que sólo vos podés contestar: **¿un valor que el portal informa y
el pipeline nunca aplica cuenta como «una actualización posterior que trae un valor distinto»?**

### M3 · RF-22 quedó a medias en una de las dos acciones que la feature agregó

Es exactamente el defecto 10 que el `Tester` encontró y el `Developer` arregló en
`CorrectionDialog` — **sobrevivido en el otro botón**. `RevertCorrectionButton` sólo tiene estado
de error: en el camino feliz refresca la pantalla sin decir nada. El dueño aprieta «Volver al
valor del portal», el botón desaparece, y nunca lee que se aplicó.

No hay dos salidas acá: el estándar ya lo fijó el propio proyecto al arreglar el otro botón.
Vuelve al `Developer`, y después al `Tester` para generalizar el test estático que ya existe.

### M4 · `data-model.md` no conoce la migración `0009`

`data-model.md` declara «dos tablas nuevas, una que cambia de rol» y «una sola migración».
Salieron cuatro, y la última —`0009`— agrega la columna `source` a **dos tablas existentes** de
`core`. Sobre esa columna se apoya la corrección de uno de los defectos más graves que encontró
la suite.

El código está bien; el artefacto quedó viejo. Vuelve al `Backend-Architect`. Lo mismo con la
regla de comparación de `conflict_value`, que el código aplica distinto según el campo por un
motivo argumentado que el documento no registra.

## Tres cosas que el converge miró y **no** son hallazgos de esta feature

- **La regla del motivo obligatorio se cumple sin excepción en la 003.** Pero código posterior ya
  la viola: las operaciones de categorías publican su línea de bitácora **sin motivo**. Es de otra
  feature, y conviene saberlo antes de que se multiplique.
- ~~**Una escritura del sistema sobre un importe con corrección vigente queda frenada y sólo se
  registra en el log.**~~ **Resuelto el 2026-08-31.** Era lo que decía este bullet: la carga se
  salteaba, no dejaba línea de bitácora y la pantalla igual contestaba «Caso resuelto». Rozaba el
  Artículo II —«un sistema que descarta en silencio le miente a quien lo mira»— y estaba anotado
  también en `tasks.md` como decisión de negocio pendiente.

  **Quién y qué decidió.** El *human in the loop*, el **2026-08-31**, entre tres salidas —aplicar
  y pisar la corrección, **rechazar avisando**, o aceptar así y dejar de decir «resuelto»— eligió
  la del medio.

  **Qué hace el sistema ahora.** Un importe que **contradice** la corrección vigente se rechaza
  con un `ConflictError` (409): `CatalogService._register_price` levanta, el handler de
  `QuarantineCaseResolved` propaga, y como un handler que falla aborta a quien publicó (`GEN-09`),
  `triage` nunca llega a su `commit()` — el caso **sigue pendiente** en vez de cerrarse en falso.
  El mensaje dice desde cuándo está corregido el precio, cuánto dice, que el caso sigue en la cola
  y las dos salidas que sí lo vacían: cargar ese mismo importe, o cambiar la corrección en la
  ficha del producto y volver a cargarlo. El `details` lleva `product_id`, `correction_id`,
  `corrected_value` y `corrected_by_user_id`; el nombre de quien corrigió lo resuelve
  `triage/routes.py` con `ActorDirectory` —`catalog` no puede nombrar a nadie sin violar el
  Artículo IV—, y la tarjeta de `/revision` imprime «La corrección la hizo Julián» con los enlaces
  para verla o cambiarla, o dice quién puede cambiarla cuando quien lee no puede.

  **Un importe igual al corregido no es una contradicción**: pasa sin escribir nada y cierra el
  caso, con su línea de bitácora. Sin eso el rechazo dejaba en la cola una fila que nadie podía
  vaciar nunca —`TriageService.resolve` es el único camino a `RESOLVED` y pasa por esa escritura—,
  que es el defecto opuesto y del mismo tamaño.
- **Ninguna credencial se guarda hoy**, y está verificado: el catálogo de parámetros es cerrado y
  los campos corregibles son tres. Pero la bitácora es un canal genérico con texto libre; el
  riesgo es de diseño futuro, no de este código.

## Qué NO se encontró

- **Ningún requisito ausente.** Los 33 tienen implementación.
- **Ningún alcance no pedido.** Todo lo que se construyó lo pide un requisito o lo justifica el
  plan.
- **Ninguna violación de las reglas inviolables del dominio** en el código de esta feature.

## Qué hacer con esto

Antes de desplegar y archivar la spec, resolver M1 y M2 —las dos preguntas que son tuyas— y M3,
que no tiene pregunta. M4 y los 38 menores son actualización de artefactos: no bloquean nada,
pero el que los deje viejos le está mintiendo al próximo que los lea.
