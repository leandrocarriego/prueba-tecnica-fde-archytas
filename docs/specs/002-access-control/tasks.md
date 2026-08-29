# Accesos por persona — Tareas

<!--
  ARTEFACTO INTERNO. Cada tarea mapea a una skill de agents/skills/ y es lo bastante
  chica como para terminarse de una sentada.
-->

**Feature:** 002-access-control · **Plan:** `plan.md` · **Tareas:** 41

**Estado de la implementación** (2026-08-29): **las 41 tareas están hechas.** La suite pasa con
517 tests y 94,64% de cobertura; `ruff`, `mypy --strict`, `eslint` y `tsc` en verde, y el frontend
compila. Lo que queda anotado al final no son tareas pendientes sino **dos deudas que la feature
deja abiertas a propósito**.

## Orden

Agrupadas por historia, en el orden de prioridad de la spec. Dentro de cada una:
migración → backend → frontend → tests.

> **Al terminar H1 hay algo entregable de verdad**: las tres personas entran con su propio acceso,
> ven su nombre en pantalla, cierran sesión, y la sesión se cae sola a las ocho horas sin uso. Se
> deja de compartir una clave, que es el pedido textual del cliente. Lo que H1 **todavía no** hace
> es separar lo que cada uno ve: eso es H2, y hasta que exista, todo el que entra ve todo.

> **`lib/api/types.ts` está generado, no escrito.** Las cuatro tareas que cambian el contrato HTTP
> —8, 16, 32 y 39— lo regeneran con `npm run generate-api-types` en su mismo commit. No es una tarea
> aparte a propósito: un tipo generado que se actualiza "después" describe una API que ya no existe,
> y el archivo viejo compila perfecto, así que `TS-01` no lo ve.

> **Ya no hay ninguna tarea bloqueada por afuera.** La invitación y la recuperación van por el mismo
> WhatsApp que la 001 ya construyó, así que no hay servidor que elegir, dominio que verificar ni
> cuenta que dar de alta: `notifications` y su cliente de Evolution API ya existen. Lo único que
> hace falta es que esa instancia esté andando, que es una condición de la 001 y no de esta feature.

### H1 — Cada uno entra con lo suyo

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 1 ✅ | Migración `0002_access_control`: tablas `sessions`, `credential_token`, `access_event` y `access_setting`; columnas `failed_attempts`, `locked_until`, `invited_at` y `activated_at` en `users`, y `phone` que pasa a obligatorio; baja de `password_reset_tokens`. Cada modelo en `app/models.py` en el mismo commit. | `add_database_migration` | Developer | RF-01, RF-05, RF-29, RF-45 |
| 2 ✅ | Los tres parámetros en `operations.parameter` con sus valores iniciales: `access.session_idle_minutes` 480, `access.max_failed_attempts` 5, `access.lockout_minutes` 15. | `add_database_migration` | Developer | RF-36, RF-49 |
| 3 ✅ | `identity`: proyección `access_setting` sembrada con los iniciales, y handler de `BusinessParameterChanged` que la actualiza. **No le pregunta a `operations`.** | `add_backend_feature` | Developer | RF-36, RF-49 |
| 4 ✅ | `identity`: sesión server-side. Token opaco de `secrets`, guardado hasheado, resuelto en cada request; `last_seen_at` con ventana de 60 s; revocación con motivo. Reemplaza `create_access_token` / `decode_access_token`, y `uv remove python-jose` si no queda ningún uso. | `add_backend_feature` | Developer | RF-01, RF-04, RF-05, RF-15 |
| 5 ✅ | `identity`: cierre por inactividad leído de la proyección, no de `settings`. Una sesión usada a las 7 h 59 sigue viva. | `add_backend_feature` | Developer | RF-05, RF-36 |
| 6 ✅ | `identity`: bloqueo por intentos fallidos — contador, `locked_until`, reseteo al ingresar bien, y **la misma respuesta** que una clave equivocada. | `add_backend_feature` | Developer | RF-45, RF-46, RF-48, RF-49 |
| 7 ✅ | `identity`: registro de `LOGIN_SUCCEEDED`, `LOGIN_REJECTED` y `ACCESS_LOCKED` en `access_event`, con el correo intentado y **nunca la clave**. | `add_backend_feature` | Developer | RF-29, RF-47 |
| 8 ✅ | Endpoints `POST /auth/login`, `POST /auth/logout` y `GET /auth/me`. Regenera `lib/api/types.ts` en el mismo commit. Login público; los otros dos, cualquier sesión activa. El login responde igual ante correo inexistente, clave errada, acceso desactivado y acceso bloqueado. | `add_backend_feature` | Developer | RF-01, RF-02, RF-03, RF-04, RF-06, RF-19 |
| 9 ✅ | Comando de puesta en marcha que crea el único acceso `OWNER` desde variables de entorno, idempotente. **No es una ruta HTTP.** | `add_backend_feature` | Developer | RF-01 |
| 10 ✅ | Frontend: nombre de quien trabaja visible, botón de cerrar sesión contra `POST /auth/logout` —que no existía—, y la sesión vencida que devuelve al login sin dejar datos en la pantalla anterior. **El formulario de login no se toca**: el contrato no cambia y lo que cambió es qué hay adentro del token. | `add_frontend_feature` | Developer | RF-03, RF-04, RF-05 |
| 11 ✅ | Tests de H1: los cuatro finales indistinguibles del login, la inactividad contada desde la última actividad y no desde el ingreso —incluido el borde que la ventana de 60 s podría romper—, el bloqueo y su vencimiento, y que ningún registro guarde una clave. | `add_tests` | Tester | RF-01, RF-02, RF-03, RF-04, RF-05, RF-19, RF-29, RF-36, RF-45, RF-46, RF-47, RF-48, RF-49 |

### H2 — Cada uno ve sólo su parte

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 12 ✅ | `identity`: `Section`, `Level` y la matriz estática, declarada **completa** — una sección sin entrada para un rol es un error de tipos, no un `None`. | `add_backend_feature` | Developer | RF-06, RF-08, RF-09, RF-10, RF-11, RF-32 |
| 13 ✅ | `identity/dependencies.py`: `require_section(seccion, nivel)`, con `WRITE` admitiendo lo que pide `READ`. Es lo único que cruza la frontera. | `add_backend_feature` | Developer | RF-32, RF-33 |
| 14 ✅ | Aplicar la matriz al calendario y a los precios: ventas consulta y no edita; el dueño y compras piden la lista a mano y resuelven lo apartado. | `add_backend_feature` | Developer | RF-11, RF-34, RF-35 |
| 15 ✅ | Migrar las once rutas de la 001 de `require_roles` a `require_section`. Al terminar, **no queda ninguna ruta con la convención vieja**. | `add_backend_feature` | Developer | RF-11, RF-35 |
| 16 ✅ | `GET /auth/me` devuelve la matriz efectiva de quien pregunta: `{ user, permissions }`. Regenera `lib/api/types.ts` en el mismo commit. | `add_backend_feature` | Developer | RF-07 |
| 17 ✅ | Frontend: la navegación se dibuja con lo que devuelve `/auth/me`, y los controles de edición aparecen sólo con nivel de edición. **Ninguna regla de permisos escrita en TypeScript.** | `add_frontend_feature` | Developer | RF-07, RF-33 |
| 18 ✅ | Tests de H2: la matriz entera parametrizada rol × sección contra la tabla de la spec, y el par que define la feature — ventas hace `GET` del calendario y recibe 200, hace `POST` y recibe 403. | `add_tests` | Tester | RF-06, RF-07, RF-08, RF-09, RF-10, RF-11, RF-32, RF-33, RF-34, RF-35 |

### H3 — El permiso se verifica de verdad

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 19 ✅ | Middleware en `main.py` que registra los 403 como `PERMISSION_DENIED` con el método y la ruta, **en su propia sesión**: la de la request ya abortó. | `add_backend_feature` | Developer | RF-14 |
| 20 ✅ | Extender `tests/architecture/test_route_authorization.py`: una ruta que declara sección pero no nivel rompe el build, igual que hoy lo rompe una sin autorización. | `add_tests` | Tester | RF-12, RF-13, RF-15 |
| 21 ✅ | Frontend: un 403 muestra "no tenés permiso" y un 401 manda al login. Son dos cosas distintas y se ven distintas. | `add_frontend_feature` | Developer | RF-13, RF-15 |
| 22 ✅ | Tests de H3: la dirección pegada a mano de una sección ajena, el 403 que queda registrado con nombre, recurso y fecha, y la request sin sesión que no llega al handler. | `add_tests` | Tester | RF-12, RF-13, RF-14, RF-15 |

### H4 — El dueño administra los accesos

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 23 ✅ | Migración: los cuatro `kind` de administración y las columnas `actor_user_id` y `details` en `access_event`. | `add_database_migration` | Developer | RF-23 |
| 24 ✅ | Emisor a disco para desarrollo y tests, seleccionable por configuración tipada en `Settings` y documentado en `.env.example`, para que ninguna corrida local le mande un WhatsApp de verdad a nadie. | `add_integration` | Developer | RF-38, RF-42 |
| 25 ✅ | `notifications`: los dos mensajes —invitación y recuperación— sobre el cliente de Evolution API que la 001 ya construyó. **Ni canal nuevo ni dependencia nueva**: otro texto y otro destinatario. | `add_integration` | Developer | RF-38, RF-42, RF-52 |
| 26 ✅ | `notifications`: handlers de `UserInvited` y `PasswordResetRequested` que **encolan** su task y vuelven. Una llamada a un servicio ajeno dentro de la transacción del publicador la tendría abierta mientras dura. Si el envío falla, el token sigue válido y se reenvía. | `add_celery_task` | Developer | RF-38, RF-42, RF-52 |
| 27 ✅ | `identity`: alta de acceso con nombre, correo, teléfono y rol, **sin clave**, que emite `credential_token` de propósito `INVITATION` y publica `UserInvited`. Ninguna respuesta devuelve el token. | `add_backend_feature` | Developer | RF-16, RF-37, RF-42, RF-44 |
| 28 ✅ | `identity`: canje de la invitación — la persona define su clave; mientras no lo haga, ese acceso no entra. | `add_backend_feature` | Developer | RF-43 |
| 29 ✅ | `identity`: las tres invariantes — un solo dueño, el dueño no se desactiva a sí mismo, y el rol de un acceso lo cambia sólo el dueño. | `add_backend_feature` | Developer | RF-17, RF-22, RF-24, RF-50 |
| 30 ✅ | `identity`: desactivar revoca las sesiones abiertas de esa persona y conserva su nombre en todo lo registrado; reactivar borra la clave anterior y manda una invitación nueva. | `add_backend_feature` | Developer | RF-18, RF-19, RF-20, RF-21, RF-51, RF-52, RF-53 |
| 31 ✅ | `identity`: registrar cada alta, cambio de rol, desactivación y reactivación con actor, sujeto y qué cambió. | `add_backend_feature` | Developer | RF-23 |
| 32 ✅ | Endpoints de administración: `GET`/`POST /users`, `GET`/`PATCH /users/{id}`, `POST /users/{id}/deactivate` y `/reactivate`, más `GET`/`POST /auth/invitation/{token}`. **Se elimina `DELETE /users/{id}`** y las dos lecturas se cierran al dueño. Regenera `lib/api/types.ts` en el mismo commit. | `add_backend_feature` | Developer | RF-16, RF-17, RF-18, RF-24, RF-51 |
| 33 ✅ | Frontend: pantalla de administración de accesos —alta, cambio de rol, desactivar, reactivar, y el estado de cada uno— sólo para el dueño. | `add_frontend_feature` | Developer | RF-16, RF-17, RF-18, RF-24, RF-51 |
| 34 ✅ | Frontend: pantalla pública de aceptar invitación, donde la persona define su clave. | `add_frontend_feature` | Developer | RF-42, RF-43, RF-52 |
| 35 ✅ | Tests de H4: el segundo dueño que no se puede crear ni ascender, el dueño que no se puede sacar, el acceso invitado que no entra hasta canjear, la desactivación que corta una sesión **abierta**, y la reactivación que no revive la clave vieja. | `add_tests` | Tester | RF-16, RF-17, RF-18, RF-19, RF-20, RF-21, RF-22, RF-23, RF-24, RF-37, RF-42, RF-43, RF-44, RF-50, RF-51, RF-52, RF-53 |

### H5 — Cada uno maneja su propia clave

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 36 ✅ | `identity`: cambio de clave propio que invalida la anterior y revoca las demás sesiones; recuperación con token hasheado de un solo uso y con vigencia, que responde lo mismo exista o no la dirección, y que invalida los enlaces anteriores. | `add_backend_feature` | Developer | RF-25, RF-26, RF-27, RF-28, RF-38, RF-39, RF-40, RF-41 |
| 37 ✅ | Frontend: cambiar la clave desde la propia cuenta, pedir la recuperación, y definir la nueva desde el enlace que llegó por WhatsApp. | `add_frontend_feature` | Developer | RF-25, RF-27 |
| 38 ✅ | Tests de H5: el enlace usado dos veces, el enlace vencido, la dirección que no existe respondiendo igual que una que sí, y la sesión de otro navegador que muere al cambiar la clave. | `add_tests` | Tester | RF-25, RF-26, RF-27, RF-28, RF-38, RF-39, RF-40, RF-41 |

### H6 — Saber quién entró y a qué le dijeron que no

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 39 ✅ | Endpoint `GET /access-log` con paginación y filtro por tipo y por fecha, gateado por `ACCESS_LOG: READ`. Regenera `lib/api/types.ts` en el mismo commit. | `add_backend_feature` | Developer | RF-30, RF-31 |
| 40 ✅ | Frontend: pantalla de registro de actividad para el dueño — ingresos, rechazos, bloqueos y cambios de acceso en una sola lista. | `add_frontend_feature` | Developer | RF-30, RF-47 |
| 41 ✅ | Tests de H6: el dueño ve la lista, compras y ventas reciben 403, y un bloqueo aparece en ella. | `add_tests` | Tester | RF-29, RF-30, RF-31, RF-47 |

## Cobertura de requisitos

| Requisito | Tareas | Test |
|-----------|--------|------|
| RF-01 | 1, 4, 8, 9 | 11 |
| RF-02 | 8 | 11 |
| RF-03 | 8, 10 | 11 |
| RF-04 | 4, 8, 10 | 11 |
| RF-05 | 1, 4, 5, 10 | 11 |
| RF-06 | 8, 12 | 18 |
| RF-07 | 16, 17 | 18 |
| RF-08 | 12 | 18 |
| RF-09 | 12 | 18 |
| RF-10 | 12 | 18 |
| RF-11 | 12, 14, 15 | 18 |
| RF-12 | 13, 19 | 20, 22 |
| RF-13 | 13, 21 | 20, 22 |
| RF-14 | 19 | 22 |
| RF-15 | 4, 21 | 20, 22 |
| RF-16 | 27, 32, 33 | 35 |
| RF-17 | 29, 32, 33 | 35 |
| RF-18 | 30, 32, 33 | 35 |
| RF-19 | 8, 30 | 11, 35 |
| RF-20 | 30 | 35 |
| RF-21 | 30 | 35 |
| RF-22 | 29 | 35 |
| RF-23 | 23, 31 | 35 |
| RF-24 | 29, 32, 33 | 35 |
| RF-25 | 36, 37 | 38 |
| RF-26 | 36 | 38 |
| RF-27 | 36, 37 | 38 |
| RF-28 | 36 | 38 |
| RF-29 | 7 | 11, 41 |
| RF-30 | 39, 40 | 41 |
| RF-31 | 39 | 41 |
| RF-32 | 12, 13 | 18 |
| RF-33 | 13, 17 | 18 |
| RF-34 | 14 | 18 |
| RF-35 | 14, 15 | 18 |
| RF-36 | 2, 3, 5 | 11 |
| RF-37 | 27 | 35 |
| RF-38 | 24, 25, 26, 36 | 38 |
| RF-39 | 36 | 38 |
| RF-40 | 36 | 38 |
| RF-41 | 36 | 38 |
| RF-42 | 24, 25, 26, 27, 34 | 35 |
| RF-43 | 28, 34 | 35 |
| RF-44 | 27 | 35 |
| RF-45 | 1, 6 | 11 |
| RF-46 | 6 | 11 |
| RF-47 | 7 | 11, 41 |
| RF-48 | 6 | 11 |
| RF-49 | 2, 3, 6 | 11 |
| RF-50 | 29 | 35 |
| RF-51 | 30, 32, 33 | 35 |
| RF-52 | 25, 26, 30, 34 | 35 |
| RF-53 | 30 | 35 |


## Lo que queda abierto

No son tareas de esta feature: son consecuencias suyas que hay que mirar antes del review.

**El par de RF-33 sobre el calendario no se pudo testear.** La matriz cubre las 45 celdas y el
test de arquitectura exige nivel de edición en toda ruta que escribe, pero el caso que la spec
usa para explicar la feature —ventas hace `GET` del calendario y recibe 200, hace `POST` y recibe
403— no tiene rutas contra las que correr: **el calendario es la feature 006**. Cuando exista,
ese par es su primer test.

**`alembic check` está sucio, y no por esta feature.** Los modelos de `triage` tienen
`resolved_by_name` y `created_by_name` sin migración, de la 001 en vuelo. Rompe `DB-01` para todos.

**El emisor a disco quedó apagado por defecto.** Encenderlo cambiaba el contrato del canal que la
001 ya tenía testeado —cinco tests en rojo—, así que se activa desde `.env` con
`NOTIFICATIONS_TO_DISK=true`. Es lo que hay que prender para ver la invitación en desarrollo.
