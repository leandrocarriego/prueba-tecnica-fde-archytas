# Accesos por persona — Modelo de datos

<!-- ARTEFACTO INTERNO. Detalle de `plan.md` → Datos. No se exporta al cliente. -->

**Feature:** 002-access-control · **Fecha:** 2026-08-29

Todo vive en el **schema por defecto**, junto a las tablas que `identity` ya tiene. No entra en
`raw` → `staging` → `core`: eso es el pipeline del portal, y esto es la aplicación hablando de sí
misma. Cada tabla nueva entra con su migración de Alembic y su línea en `app/models.py`, en el
mismo commit (`DB-01`, Blocker).

```
  users ──┬─> user_passwords          la clave, hasheada, aparte de la persona
          ├─> sessions                lo que se puede revocar
          ├─> credential_token        invitación y recuperación, un solo uso
          └─> access_event            qué pasó: entró, no entró, no le tocaba

  operations.parameter ──BusinessParameterChanged──> access_setting   (proyección)
```

## `sessions` — lo que se puede apagar

Reemplaza al JWT. Existe porque cuatro requisitos firmados piden revocar algo que ya se emitió
(RF-20, RF-26, RF-53) o medir inactividad (RF-05), y un token firmado no admite ninguna de las dos.

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `int` PK | |
| `user_id` | `int` FK → `users.id` | `ON DELETE CASCADE`, aunque un usuario no se borra nunca (RF-21) |
| `token_hash` | `str(64)` **unique** | SHA-256 del token opaco. **La tabla no alcanza para entrar**: lo que viaja al cliente no está acá |
| `created_at` | `timestamptz` | Cuándo se abrió |
| `last_seen_at` | `timestamptz` **index** | Última actividad. Se refresca sólo si envejeció más de 60 segundos |
| `revoked_at` | `timestamptz \| None` | Cerrada explícitamente |
| `revoked_reason` | `enum \| None` | `LOGOUT`, `DEACTIVATION`, `PASSWORD_CHANGED`, `REACTIVATION` |

**Una sesión es válida si** `revoked_at IS NULL` y `last_seen_at + inactividad > now()`. La
inactividad sale de `access_setting`, no de `settings.ACCESS_TOKEN_EXPIRE_MINUTES`, que deja de
usarse.

> **Por qué SHA-256 y no bcrypt para el token.** El token lo genera el servidor con 32 bytes de
> `secrets`, así que no tiene entropía baja que proteger de una fuerza bruta offline: no es una
> clave elegida por una persona. Y se resuelve en **cada request**, donde bcrypt costaría cien
> milisegundos por consulta. Para las claves de las personas sigue siendo bcrypt, que es el caso
> contrario.

## `credential_token` — invitación y recuperación

Reemplaza a `password_reset_tokens`, que hoy guarda el token **en claro**. Un token en claro en la
base es una clave en la base.

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `int` PK | |
| `user_id` | `int` FK → `users.id` | |
| `token_hash` | `str(64)` **unique** | SHA-256. Lo que se manda por WhatsApp no queda guardado |
| `purpose` | `enum` | `INVITATION` (RF-42, RF-52) · `PASSWORD_RESET` (RF-38) |
| `expires_at` | `timestamptz` | Invitación: 7 días. Recuperación: 1 hora (RF-41) |
| `used_at` | `timestamptz \| None` | Se sella al canjearlo: **un solo uso** (RF-40) |
| `created_at` | `timestamptz` | |

**Emitir un token nuevo invalida los anteriores del mismo propósito.** Pedir la recuperación tres
veces deja un solo enlace vivo, el último: si no, el primer mensaje seguiría sirviendo días después.

## `access_event` — nada se descarta

Es el Artículo II aplicado a los accesos: un intento rechazado es información del negocio, y por eso
es una tabla del producto y no una línea de log que se rota.

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `int` PK | |
| `occurred_at` | `timestamptz` **index** | |
| `kind` | `enum` **index** | Accesos: `LOGIN_SUCCEEDED` (RF-29) · `LOGIN_REJECTED` (RF-02) · `ACCESS_LOCKED` (RF-47) · `PERMISSION_DENIED` (RF-14). Administración: `ACCESS_GRANTED` · `ACCESS_ROLE_CHANGED` · `ACCESS_DEACTIVATED` · `ACCESS_REACTIVATED` (RF-23) |
| `user_id` | `int \| None` FK → `users.id` | **A quién le pasó.** `None` cuando el correo no corresponde a nadie: no hay a quién atribuirlo, y el intento igual se guarda |
| `actor_user_id` | `int \| None` FK → `users.id` | **Quién lo hizo.** El dueño, en los cuatro `kind` de administración. `None` en los de acceso, donde el actor y el sujeto son la misma persona |
| `attempted_email` | `str(255) \| None` | Con qué correo se intentó. **Nunca la clave intentada** |
| `resource` | `str(255) \| None` | Para `PERMISSION_DENIED`: el método y la ruta que se quiso abrir. Es el *"qué quiso ver"* de RF-14 |
| `reason` | `str(100) \| None` | Motivo interno: `INVALID_CREDENTIALS`, `INACTIVE`, `LOCKED`, `SECTION_FORBIDDEN`, `LEVEL_FORBIDDEN` |
| `details` | `JSONB \| None` | El *"qué cambió"* de RF-23: `{"role": {"from": "SALES", "to": "PURCHASING"}}`. Valores planos, nunca una clave ni un token |

> **Una tabla y no dos.** RF-23 —el registro de las altas, los cambios de rol, las desactivaciones
> y las reactivaciones— vive acá y no en una tabla aparte, porque es la misma pregunta que RF-30 con
> otro verbo: *quién le hizo qué a qué acceso, y cuándo*. Partirla obligaría a la pantalla del dueño
> a unir dos historias que se leen juntas. Lo que sí hacía falta era distinguir **actor** de
> **sujeto**: en un ingreso son la misma persona, en una desactivación no.
>
> **El motivo se guarda, pero no se devuelve.** RF-02 exige que el que falla no sepa cuál de los dos
> datos erró; el dueño, mirando el registro, sí tiene que poder distinguir un olvido de clave de un
> acceso desactivado insistiendo. La asimetría es deliberada: adentro se sabe, afuera no.

## `access_setting` — la proyección

`identity` necesita tres valores que son de `operations` (RF-36, RF-49). No se los pregunta: los
recibe. Es lo mismo que hace `ingestion` con las reglas de `triage` en la 001, y lo que el catálogo
de eventos prescribe para `BusinessParameterChanged`.

| Columna | Tipo | Notas |
|---|---|---|
| `key` | `str(100)` PK | `access.session_idle_minutes` · `access.max_failed_attempts` · `access.lockout_minutes` |
| `value` | `JSONB` | |
| `updated_at` | `timestamptz` | |

Arranca sembrada con los valores iniciales, así que **el sistema funciona antes de que nadie toque
un parámetro** y no depende de haber recibido un evento para saber cuánto dura una sesión.

| Parámetro | Inicial | De dónde sale |
|---|---|---|
| `access.session_idle_minutes` | `480` | Ocho horas, decidido por el cliente en la aclaración (RF-36) |
| `access.max_failed_attempts` | `5` | Supuesto declarado en la spec, sin confirmar |
| `access.lockout_minutes` | `15` | Supuesto declarado en la spec, sin confirmar |

## `users` — cuatro columnas nuevas y una que deja de ser opcional

| Columna | Tipo | Notas |
|---|---|---|
| `phone` *(existe)* | `str(20)` | **Pasa de nullable a obligatorio** (RF-37): es por donde llega la invitación, así que un acceso sin teléfono es un acceso que nadie puede usar. La migración lo exige y el alta lo pide |
| `failed_attempts` | `int` default `0` | Fallos seguidos. Vuelve a cero con cada ingreso exitoso |
| `locked_until` | `timestamptz \| None` | Bloqueo temporal (RF-45, RF-48) |
| `invited_at` | `timestamptz \| None` | Cuándo se mandó la invitación vigente |
| `activated_at` | `timestamptz \| None` | Cuándo definió su clave. `None` = invitado sin canjear (RF-43) |

> **El correo se queda, y sigue siendo único.** No es un canal: es el nombre de usuario con el que
> la persona entra y lo que distingue un acceso de otro. El sistema no le manda nada ahí. Se
> mantiene como identificador en vez de pasar al teléfono porque es lo que la gente sabe escribir,
> lo que el login ya usa, y porque un teléfono cambia más seguido que una dirección.

### El estado del acceso no es una columna

Los cuatro estados del diagrama de la spec salen de las columnas que ya existen. No hay un `status`
que mantener en acuerdo con `is_active` y `locked_until`: dos fuentes para el mismo hecho terminan
discrepando, y la que miente es siempre la que se lee.

| Estado | Cómo se deriva |
|---|---|
| **Invitado** | `is_active` y `activated_at IS NULL` |
| **Activo** | `is_active`, `activated_at` no nulo, y sin bloqueo vigente |
| **Bloqueado** | `is_active`, `activated_at` no nulo, y `locked_until > now()` |
| **Desactivado** | `not is_active` |

**Reactivar es volver a Invitado, no a Activo** (RF-51 a RF-53): pone `is_active = true`, borra
`activated_at`, borra la fila de `user_passwords` y emite una invitación nueva. La clave anterior
deja de existir, no deja de servir — que es la versión fuerte del requisito.

## La matriz de permisos

No es una tabla: es una constante de `identity`, y la razón está en `plan.md` → *Alternativas
descartadas*. Se declara **completa** —cada sección tiene una entrada para cada uno de los tres
roles— para que agregar una sección sin decidir su permiso sea un error de tipos y no un `None` que
alguien interpreta.

| Sección | Dueño | Compras | Ventas | De dónde sale |
|---|---|---|---|---|
| `PRICES` | Edita | Edita | Consulta | RF-11, RF-35 |
| `CALENDAR` | Edita | Edita | Consulta | RF-34 |
| `SUPPLIERS` | Edita | Edita | — | RF-10 |
| `PURCHASE_INVOICES` | Edita | Edita | — | RF-10 |
| `PAYMENTS` | Edita | Edita | — | RF-10 |
| `PURCHASE_ORDERS` | Edita | Edita | — | Regla de negocio: órdenes es de compras |
| `RECEIPTS` | Edita | Edita | — | Regla de negocio: recibos es de compras |
| `SALES` | Edita | — | Edita | RF-09 |
| `DASHBOARD` | Consulta | — | Consulta | RF-09. Nadie *edita* un tablero: no tiene nivel de escritura |
| `STOCK` | Edita | — | Edita | Regla de negocio: stock es de ventas |
| `PRODUCT_CATEGORIES` | Edita | — | Edita | Regla de negocio: rubros es de ventas |
| `PRODUCT_CATALOG` | Edita | — | Edita | Regla de negocio: catálogo es de ventas |
| `ACCESS_ADMIN` | Edita | — | — | RF-24 |
| `ACCESS_LOG` | Consulta | — | — | RF-30, RF-31 |
| `SYSTEM_PARAMETERS` | Edita | — | — | RF-08. Gatea las rutas de parámetros que la 001 ya tiene |

**"Edita" implica "consulta".** Un nivel es un orden, no un conjunto de banderas:
`NONE < READ < WRITE`, y `require_section(X, READ)` admite a quien tenga `WRITE`.

> **Cinco secciones salen de la regla de negocio y no de un RF que las nombre.** La spec enumera qué
> trabaja cada rol y RF-07 dice que cada uno ve únicamente lo habilitado para el suyo; lo que no
> está en la lista de un rol queda en `NONE`. Está anotado acá porque es la clase de derivación que
> conviene que `/converge` pueda revisar contra la spec en vez de descubrir.
>
> **`PRICES: WRITE` gatea hoy tres cosas de la 001**: pedir la actualización a mano, resolver lo
> apartado y anular una regla aprendida. Cuando P2 traiga las facturas a la misma cola de revisión,
> esa cola va a necesitar su propia sección: una fila de facturas no la resuelve quien puede tocar
> precios porque comparten pantalla.
