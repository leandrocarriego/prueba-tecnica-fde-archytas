# Accesos por persona — Informe de convergencia

<!--
  ARTEFACTO DEL LEAD. No lo escribe ni lo edita ningún otro rol.
  Compara el código construido contra lo que el cliente firmó: spec, plan, tasks y diagramas.
  No juzga calidad de código: eso es `review_feature`.
-->

**Feature:** 002-access-control · **Fecha:** 2026-08-29 · **Rol:** Lead
**Spec:** `Aprobado`, firmada el 2026-08-29 por Leandro Carriego — FDE
**Suite:** `uv run pytest` → **520 passed**, cobertura **94,64 %** · `alembic check` → limpio
**Diagramas:** `scripts/diagrams/validate.sh` → los 7 compilan

---

## Veredicto: **Deriva menor**

Los 53 requisitos firmados tienen implementación localizable y 52 están completos. No hay
capacidad de negocio construida que ningún requisito pida. Lo que quedó fuera de lugar son
**artefactos que dejaron de describir el código**: el plan en tres puntos, `tasks.md` en dos
afirmaciones que ya no son ciertas, y un diagrama de estados al que le faltan dos transiciones que
el código sí hace.

**No bloquea el gate.** La feature pasa al `Code-Reviewer`, y los siete hallazgos se corrigen en
paralelo, cada uno con su rol dueño.

> **Una decisión es del humano y no la tomé yo.** RF-34 es el único requisito que no quedó
> `Implementado` (ver hallazgo #1). Si se lee RF-34 como "la matriz habilita el calendario", está
> hecho y testeado. Si se lee como su criterio de aceptación —*"Marcela mueve un vencimiento;
> Julián lo ve movido y no puede moverlo"*— **no se puede ejercer, porque el calendario es la
> feature 006 y no existe todavía**. En la segunda lectura esto es **deriva mayor** y el gate se
> cierra. Elegí la primera para el veredicto porque ninguna cantidad de trabajo dentro del alcance
> de 002 cambia el resultado, pero la lectura correcta la fija el humano, no el agente.

---

## Tabla de trazabilidad

| Requisito | Qué promete la spec | Dónde está implementado | Evidencia | Estado |
|---|---|---|---|---|
| RF-01 | Entrar sólo con un acceso individual | `identity/service.py::authenticate` (252), `dependencies.py::get_current_user` (54), `bootstrap.py::create_first_owner` | `test_identity_feature.py::test_a_successful_login_opens_a_session` | Implementado |
| RF-02 | Rechazar sin decir cuál dato falló | `service.py::_reject` (285), constante `REJECTED` | `test_every_failure_looks_the_same` | Implementado |
| RF-03 | Mostrar el nombre de quien trabaja | `frontend/components/auth/Navigation.tsx` (bloque `RF-03`), `GET /auth/me` | `routes.py::read_current_user` | Implementado |
| RF-04 | Cerrar la sesión | `POST /auth/logout`, `service.py::logout` (345), botón en `Navigation.tsx` | `test_logging_out_ends_that_session_only` | Implementado |
| RF-05 | Cerrar la sesión inactiva | `service.py::resolve_session` (320) | `test_a_session_left_idle_past_the_window_is_gone` | Implementado |
| RF-06 | Exactamente uno de los tres roles | `identity/models.py::UserRole`, `UserRead.role` | `test_rbac.py::test_every_role_can_authenticate` | Implementado |
| RF-07 | Mostrar sólo las secciones del rol | `permissions.py::permissions_for` (85) → `/auth/me` → `Navigation.tsx` | `test_permissions.py::test_the_map_of_a_role_covers_every_section` | Implementado |
| RF-08 | El dueño llega a todo | `permissions.py::MATRIX` (61) | `test_the_owner_reaches_every_section` | Implementado |
| RF-09 | Compras sin ventas ni tablero | `MATRIX[SALES]`, `MATRIX[DASHBOARD]` → `PURCHASING: NONE` | `test_marcela_does_not_see_the_sales_dashboard` | Implementado |
| RF-10 | Ventas sin proveedores, facturas ni pagos | `MATRIX[SUPPLIERS/PURCHASE_INVOICES/PAYMENTS]` → `SALES: NONE` | `test_julian_does_not_reach_the_supplier_accounts` | Implementado |
| RF-11 | Los tres consultan precios | `MATRIX[PRICES]`, `catalog/routes.py::list_prices` | `test_permissions.py` (celdas `PRICES-*`) | Implementado |
| RF-12 | Verificar el permiso antes de responder | `dependencies.py::require_section` (72) | `test_route_authorization.py::test_endpoint_declares_its_authorization` | Implementado |
| RF-13 | Rechazar e informar | `require_section` → 403 `"No tenés permiso para esta sección"`; `components/common/SinPermiso.tsx` | `test_rbac.py::TestPurchasing` | Implementado |
| RF-14 | Registrar el intento rechazado | `identity/middleware.py::record_refusals` (34), montado en `main.py:222` | `test_access_log.py::test_being_refused_a_section_is_recorded` | Implementado |
| RF-15 | Rechazar una consulta sin sesión | `dependencies.py::get_current_user` → 401 | `test_route_authorization.py::test_protected_endpoint_rejects_an_anonymous_caller` | Implementado |
| RF-16 | Alta con persona, correo, teléfono y rol | `POST /users`, `schemas.py::UserCreate`, `service.py::create_user` (107) | `test_the_access_is_created_without_a_credential` | Implementado |
| RF-17 | Cambiar el rol de un acceso | `PATCH /users/{id}`, `service.py::update_user` (179) | `test_rbac.py::test_can_change_a_role` | Implementado |
| RF-18 | Desactivar un acceso | `POST /users/{id}/deactivate`, `service.py::deactivate_user` (210) | `test_rbac.py::test_cannot_deactivate_a_user` | Implementado |
| RF-19 | Rechazar el ingreso de un acceso desactivado | `authenticate` → `_reject(user, email, "INACTIVE")` | `test_every_failure_looks_the_same` | Implementado |
| RF-20 | Cerrar las sesiones al desactivar | `repository.py::revoke_sessions_of(DEACTIVATION)` | `test_deactivating_closes_the_open_sessions`, `test_rbac.py::test_the_token_of_a_deactivated_user_is_401` | Implementado |
| RF-21 | Conservar el nombre de quien se desactiva | La fila no se borra; `triage/models.py::resolved_by_name`, `created_by_name` | `test_deactivating_keeps_the_person` | Implementado |
| RF-22 | El dueño no se desactiva a sí mismo | `service.py::deactivate_user` (211) | `test_the_owner_cannot_deactivate_themselves` | Implementado |
| RF-23 | Registrar qué cambió, quién y cuándo | `repository.py::record_event` con `actor_user_id` y `details` | `test_the_change_is_recorded_with_actor_and_subject`, `test_a_role_change_is_recorded_with_what_changed` | Implementado |
| RF-24 | Sólo el dueño administra accesos | `require_section(ACCESS_ADMIN, …)` en los 6 endpoints de `/users` | `test_rbac.py::test_cannot_create_a_user`, `test_cannot_list_users` | Implementado |
| RF-25 | Cambiar la propia clave | `POST /auth/password/change`, `service.py::change_password` (354), `app/(private)/mi-cuenta/page.tsx` | `test_changing_it_replaces_the_credential` | Implementado |
| RF-26 | Invalidar la clave anterior | `repository.py::set_password` + `revoke_sessions_of(PASSWORD_CHANGED)` | `test_changing_it_closes_the_other_sessions` | Implementado |
| RF-27 | Recuperar sin el dueño | `POST /auth/password-reset/request`, `app/(auth)/reset-password/page.tsx` | `test_a_recovery_issues_a_token_and_queues_the_message` | Implementado |
| RF-28 | Ninguna clave legible | `security.py::hash_password` (31) — bcrypt | `test_no_password_is_ever_written_to_the_log` | Implementado |
| RF-29 | Registrar quién ingresó y cuándo | `authenticate` → `LOGIN_SUCCEEDED` | `test_a_successful_login_is_recorded` | Implementado |
| RF-30 | Mostrar ingresos y rechazos al dueño | `GET /access-log`, `app/(private)/accesos/actividad/page.tsx` | `test_access_log.py::test_the_owner_reads_it` | Implementado |
| RF-31 | Los demás roles no los ven | `require_section(ACCESS_LOG)` | `test_purchasing_cannot`, `test_sales_cannot` | Implementado |
| RF-32 | Consulta, o consulta y edición | `permissions.py::Level` (`NONE`/`READ`/`WRITE`) | `test_writing_implies_reading` | Implementado |
| RF-33 | Rechazar el cambio si sólo consulta | `require_section(sección, WRITE)` | `test_route_authorization.py::test_a_route_that_writes_demands_the_level_to_write` | Implementado |
| RF-34 | Calendario: dueño y compras editan, ventas consulta | `permissions.py:63` — `CALENDAR: {OWNER: WRITE, PURCHASING: WRITE, SALES: READ}` | `test_julian_sees_the_calendar_without_moving_it` | **Parcial** |
| RF-35 | Sólo dueño y compras piden la lista y resuelven lo apartado | `operations/routes.py:158` y `triage/routes.py:44,63,90,104` → `require_section(PRICES, WRITE)`; `MATRIX[PRICES][SALES] = READ` | `test_permissions.py` (celda `PRICES-SALES`) | Implementado |
| RF-36 | Ocho horas de inactividad por defecto | `service.py::DEFAULT_IDLE_MINUTES = 480`; semilla en `0003_access_control.py:205` | `test_idleness_is_counted_from_the_last_use_not_the_login` | Implementado |
| RF-37 | Un teléfono propio por acceso | `users.phone` `NOT NULL` (`0003:201`), `UserCreate.phone` | `test_identity_feature.py` (alta) | Implementado |
| RF-38 | Enlace de recuperación por WhatsApp | `PasswordResetRequested` → `notifications/handlers.py::deliver_recovery` → `tasks.send_access_link` | `test_a_recovery_issues_a_token_and_queues_the_message` | Implementado |
| RF-39 | Misma respuesta si el correo no existe | `service.py::request_password_reset` (382) + `PASSWORD_RESET_ACK` | `test_a_recovery_answers_the_same_for_an_address_that_does_not_exist` | Implementado |
| RF-40 | Invalidar el enlace al usarlo | `redeem_token` (410) → `stored.used_at` | `test_a_token_works_once` | Implementado |
| RF-41 | Rechazar el enlace vencido | `repository.py::get_usable_token` → `expires_at > now()` | `test_an_expired_token_is_refused` | Implementado |
| RF-42 | Invitación por WhatsApp al dar de alta | `service.py::invite` (141) → `UserInvited` → `handlers.py::deliver_invitation` | `test_the_invitation_is_queued_to_the_person` | Implementado |
| RF-43 | No entra hasta definir la clave | `authenticate` → `_reject(user, email, "NOT_ACTIVATED")` | `test_an_invited_access_cannot_log_in_yet` | Implementado |
| RF-44 | El dueño no define ni ve la clave de otro | `UserCreate` y `UserUpdate` sin campo de clave; `POST /users` devuelve `UserRead`, nunca el token | `test_the_access_is_created_without_a_credential` | Implementado |
| RF-45 | Bloquear tras los intentos configurados | `service.py::_count_failure` (296) | `test_the_access_locks_after_the_configured_attempts` | Implementado |
| RF-46 | Rechazar el bloqueado aun con la clave correcta | `authenticate` verifica `locked_until` **antes** de la clave (262) | `test_a_locked_access_is_refused_even_with_the_right_password` | Implementado |
| RF-47 | Registrar el bloqueo entre los rechazos | `AccessEventKind.ACCESS_LOCKED` | `test_access_log.py::test_a_lockout_appears_among_the_rejected_attempts` | Implementado |
| RF-48 | Volver a permitir al vencer el bloqueo | `locked_until > now` | `test_the_lock_lets_go_when_it_expires` | Implementado |
| RF-49 | Quince minutos tras cinco intentos | `DEFAULT_MAX_ATTEMPTS = 5`, `DEFAULT_LOCKOUT_MINUTES = 15`; semilla en `0003:205` | `test_locking_is_recorded_for_the_owner` | Implementado |
| RF-50 | Un solo dueño | `repository.py::count_owners`, chequeado en `create_user` y `update_user` | `test_a_second_owner_is_refused`, `test_promoting_a_second_owner_is_refused` | Implementado |
| RF-51 | Reactivar un acceso | `POST /users/{id}/reactivate`, `service.py::reactivate_user` (227) | `test_reactivating_invites_again` | Implementado |
| RF-52 | Invitación nueva al reactivar | `reactivate_user` → `invite(user, INVITE_REACTIVATION)` | `test_reactivating_invites_again` | Implementado |
| RF-53 | Invalidar la clave anterior al reactivar | `repository.py::clear_password` | `test_reactivating_removes_the_old_password` | Implementado |

**52 Implementado · 1 Parcial · 0 Ausente.**

---

## Sentido inverso: alcance no pedido

Se recorrió cada endpoint, cada pantalla, cada tabla y cada task preguntando qué requisito la
pide. **No hay ningún hallazgo de tipo *Alcance no pedido*.**

- **15 endpoints nuevos o modificados** — los 15 figuran en la tabla de *Contratos* de `plan.md`,
  salvo `GET /auth/password-reset/{token}` (hallazgo #4).
- **6 pantallas nuevas** — `/accesos` (RF-16 a RF-24, RF-51), `/accesos/actividad` (RF-30),
  `/mi-cuenta` (RF-25), `/invitacion/[token]` (RF-42, RF-43), `/recuperar/[token]` (RF-40, RF-41),
  `/reset-password` (RF-27).
- **4 tablas nuevas** — `sessions`, `credential_tokens`, `access_events`, `access_settings`: las
  cuatro están en `plan.md` → *Datos* y en `data-model.md`.
- **2 handlers nuevos en `notifications`** — `deliver_invitation` (RF-42, RF-52) y
  `deliver_recovery` (RF-38).
- **Andamiaje justificado por el plan**, no hallazgo: el comando de puesta en marcha
  (`bootstrap.py`, riesgo declarado), el emisor a disco (`NOTIFICATIONS_TO_DISK`, tarea 24), la
  proyección `access_settings` (Art. IV), el parámetro `q` de `GET /users`.
- **Una sola observación menor**: `PATCH /users/{id}` acepta también `name`, `last_name` y `phone`,
  y ningún requisito pide más que cambiar el rol (RF-17). **No es alcance no pedido** porque la UI
  no lo expone: `TablaAccesos.tsx` sólo ofrece cambiar el rol, desactivar y reactivar. Queda
  anotado, no reportado.

---

## Hallazgos

| # | Tipo | Qué dice el artefacto | Qué hace el código | Rol dueño | Acción |
|---|---|---|---|---|---|
| 1 | Requisito sin implementar (parcial) | RF-34 y su CA: *"Marcela mueve un vencimiento del calendario; Julián lo ve movido y no puede moverlo él"* | La celda `CALENDAR` de la matriz existe y está testeada (`permissions.py:63`), pero **no hay ninguna ruta ni pantalla de calendario**: es la feature 006. El criterio firmado no se puede ejercer | **Humano** (y `Solution-Designer` si se corrige la spec) | Decidir entre las dos salidas de abajo |
| 2 | Deriva del plan | `plan.md` → *Contratos*: *"`require_section(...)` sustituye a `require_roles(...)` en todo lo que no sea la sesión propia"*, y tarea 15: *"no queda ninguna ruta con la convención vieja"* | `require_roles` desapareció, pero **cuatro rutas quedaron con `Depends(get_current_user)` a secas**, sin sección ni nivel: `catalog/routes.py:45` (`GET /prices`), `catalog/routes.py:61` (`GET /prices/{id}/history`), `operations/routes.py:87` (`GET /jobs`), `operations/routes.py:143` (`GET /price-updates/status`). Autentican, no autorizan. Además el docstring de `operations/routes.py:12` sigue describiendo `require_roles()`, que ya no existe | `Backend-Architect` (elegir la sección) → `Developer` | Para las dos de precios, `require_section(Section.PRICES)` es equivalente hoy (RF-11). Para `/jobs` y `/price-updates/status` hay que decidir la sección; si la respuesta es "cualquier rol autenticado", que quede escrito en el plan y no en el silencio |
| 3 | Tarea sin respaldo (parcial) | Tarea 39: *"Endpoint `GET /access-log` con paginación y **filtro por tipo y por fecha**"* | `routes.py::list_access_events` acepta `skip`, `limit` y `kind`. **No hay filtro por fecha**, ni en la ruta, ni en `repository.py::list_events`. Ningún RF lo exige, así que no es un hueco de la spec | `Developer` | Agregar el filtro, o bajar la tarea a lo que realmente se construyó |
| 4 | Deriva del plan | `plan.md` → *Contratos* lista `POST /auth/password-reset/confirm` y no lista ningún `GET` de recuperación | El código sirve `POST /auth/password-reset/{token}` (el token es un recurso, no un cuerpo) y además `GET /auth/password-reset/{token}` para que la pantalla no pida una clave contra un enlace muerto. **El código está bien; el plan quedó viejo** | `Backend-Architect` | Actualizar la tabla de *Contratos* |
| 5 | Deriva del plan | `plan.md` → *Eventos de dominio*: `UserInvited` y `PasswordResetRequested` llevan `email` | `catalog.py:69` y `:88` llevan `phone` y `name`, que es lo que WhatsApp necesita; el `email` habría sido inútil. **El código está bien; el plan quedó viejo.** Menor, en la misma tabla: la migración es `0003_access_control`, no `0002` (el `0002` se lo llevó la 001) | `Backend-Architect` | Actualizar la tabla de eventos y el número de migración en `plan.md` y en la tarea 1 |
| 6 | Tarea sin respaldo | `tasks.md` → *Lo que queda abierto*: *"`alembic check` está sucio, y no por esta feature"*, y *"la suite pasa con 517 tests"* | `uv run alembic check` → **`No new upgrade operations detected`**: lo arregló `0004_decision_author.py`. Y la suite corre **520**, no 517. Dos afirmaciones que el `Code-Reviewer` va a leer como estado actual y ya no lo son | `Backend-Architect` | Corregir las dos líneas de `tasks.md` |
| 7 | Diagrama desactualizado | `diagrams/estados-sesion.mmd` muestra tres formas de cerrar una sesión: logout, inactividad y desactivación | `SessionRevocation` tiene **cuatro**: falta `PASSWORD_CHANGED` (RF-26, cambiar la clave cierra las demás sesiones) y `REACTIVATION` (RF-53). Son dos transiciones que dos requisitos firmados exigen y el diagrama no muestra | `Solution-Designer` | `/diagram` sobre `estados-sesion.mmd` |
| 8 | Diagrama desactualizado | `diagrams/estados-acceso.mmd`: `Bloqueado --> Activo: vence el tiempo del bloqueo` | En la pantalla de accesos el estado se deriva de `locked_until != null` sin compararlo con el momento actual (`TablaAccesos.tsx:20`), así que un acceso **sigue mostrándose "Bloqueado" después de que el bloqueo venció**, hasta que esa persona entra bien. El backend sí deja entrar (RF-48 se cumple): lo que miente es la pantalla | `Developer` | Comparar `locked_until` con el momento actual al derivar el estado |

### Dos líneas que escalan al `Code-Reviewer`

No son de esta skill —`converge` no juzga calidad—, pero aparecieron al recorrer el código y el
plan las anticipa por nombre:

- **`schemas.py::UserRead.state` (57) es código muerto.** Es un `@property` de Pydantic sin
  `@computed_field`, así que **nunca se serializa**: no está en `lib/api/types.ts` y ningún test lo
  toca. La regla de los cuatro estados quedó reimplementada en TypeScript
  (`TablaAccesos.tsx:20`), cuyo comentario dice —incorrectamente— *"derived on the backend"*. Es la
  duplicación que el hallazgo #8 convirtió en bug.
- **Dos mecanismos para confirmar una recuperación.** `/recuperar/[token]` es el canónico, el que
  apunta el mensaje de WhatsApp; y la rama `confirm` de `ResetPasswordForm.tsx` hace lo mismo desde
  `/reset-password?token=`, llamando al backend por `NEXT_PUBLIC_API_URL` en vez del proxy. Es
  literalmente lo que `plan.md` → *Contexto de traspaso* mandó buscar por ausencia: *"dos
  mecanismos para lo mismo es cómo se cuela el que nadie mantiene"*.

---

## Reglas del dominio (INVIOLABLES)

Ninguna de las cinco resulta violada por lo que esta feature promete.

| Regla | Verificación |
|---|---|
| I — SIGProv es sólo lectura | La feature no toca el portal. `grep -rnE "httpx\|requests\." app/modules/portal` → sin resultados |
| II — La extracción es navegador, no cliente HTTP | Sin cambios en `portal/`; ningún endpoint JSON nuevo |
| III — Nada se descarta | Es el eje de la feature: cada rechazo, cada bloqueo y cada 403 va a `access_events`, que es una **pantalla del producto** (`/accesos/actividad`), no un log que rota |
| IV — Flujo unidireccional, `raw` inmutable | No aplica: las cuatro tablas nuevas son de aplicación y viven en el schema por defecto. `grep -rniE "update.*\braw\b\|delete.*\braw\b"` → sin resultados |
| V — Credenciales de terceros sólo en el entorno | La cuenta del portal no se toca. Las claves de las personas son nuestras: bcrypt, y los tokens de invitación y recuperación **hasheados** con SHA-256 (`security.py:50`) — la tabla no alcanza para entrar. `OWNER_EMAIL/NAME/PHONE` viven en `.env`, no en la base |

Fronteras entre módulos, verificadas de paso: `identity` no importa **nada** de otro módulo (la
proyección `access_settings` es lo que lo evita) y `notifications` tampoco importa `identity` — el
token viaja en el evento, como el plan decidió.

---

## Si el humano lee RF-34 como bloqueante

Las dos salidas, con lo que cuesta cada una. **La decisión no es del agente.**

1. **Implementar lo que falta.** Adelantar de la feature 006 lo mínimo para ejercer el par —una
   ruta de calendario que lea y otra que escriba— para que el CA de RF-34 se pueda correr. Cuesta
   abrir 006 a medias dentro de 002 y vuelve al `Developer` y después otra vez al `Tester`.
2. **Corregir la spec.** Mover el criterio de aceptación de RF-34 a la spec de 006, dejando en 002
   la habilitación de la matriz —que es lo que 002 sí construye—. Vuelve al `Solution-Designer` y
   **el cliente vuelve a firmar** con `/approve-spec`: el gate de la firma se reabre.

Mi lectura, para que quede escrita y no para reemplazar la decisión: la opción 2 describe mejor lo
que pasó. RF-34 es una regla de permisos, y la regla está construida, completa y testeada celda por
celda; lo que no existe es la pantalla sobre la que se aplica, y construirla nunca estuvo en el
alcance de esta feature.
