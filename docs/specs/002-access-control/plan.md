# Accesos por persona — Plan técnico

<!--
  ARTEFACTO INTERNO. Acá van las decisiones técnicas que spec.md no puede llevar.
  No se exporta al cliente.
-->

**Feature:** 002-access-control · **Spec aprobada el:** 2026-08-29 · **Fecha:** 2026-08-29

## Constitution Check

| Artículo | Cumple | Cómo |
|---|---|---|
| I — El origen es ajeno y de sólo lectura | Sí | La feature no toca SIGProv. No agrega ninguna navegación, ningún parser y ninguna escritura contra el portal. La cuenta compartida del proveedor sigue siendo una credencial de entorno que ningún acceso de esta feature puede ver ni cambiar, y la spec lo declara fuera de alcance. |
| II — Nada se descarta | Sí | Un intento rechazado y un bloqueo por intentos fallidos **no se pierden**: van a `identity.access_event`, que es la cuarentena de esta feature (RF-14, RF-30, RF-47). El registro es una pantalla del producto, no una línea de log que se rota a los siete días. |
| III — Flujo unidireccional, `raw` inmutable | Sí | No aplica al pipeline: las tablas de esta feature son de la aplicación, viven en el schema por defecto —donde `identity` ya está— y no entran en `raw` → `staging` → `core`. No se agrega, se mueve ni se corrige nada en `raw`. |
| IV — Las fronteras entre módulos son reales | Sí | Dos módulos tocados, cero imports cruzados. `identity` publica cuatro eventos nuevos y `notifications` reacciona. Las dos lecturas sincrónicas que la feature parecía necesitar —`identity` leyendo los parámetros de `operations`, y cada módulo consultando la matriz de permisos— se resuelven con una proyección propia (`identity.access_setting`, alimentada por `BusinessParameterChanged`) y con `dependencies.py`, que es la excepción que el artículo ya contempla. |
| V — Spec primero, y con firma | Sí | `spec.md` está en `Estado: Aprobado`, firmada el 2026-08-29. Los 53 requisitos tienen lugar acá, y no hay nada acá que no salga de uno de ellos. Lo que este plan **saca** de la spec —la sesión por JWT que ya existe— se saca porque contradice un requisito firmado, no por gusto. |
| VI — Lo que no está tipado y testeado no está terminado | Sí | Tipos completos con `mypy --strict` (`PY-10`) y TypeScript estricto (`TS-01`). La matriz de permisos se testea rol por rol y sección por sección contra la tabla de la spec, no a mano; el `test_route_authorization.py` que ya existe se extiende para exigir nivel, no sólo autenticación. |
| VII — Las credenciales de terceros viven sólo en el entorno | Sí | Las del portal no se tocan. Las de las personas del equipo son nuestras, se guardan con bcrypt y nunca en claro (RF-28), y los tokens de invitación y de recuperación se guardan **hasheados**: la tabla no alcanza para entrar. Ningún token viaja a un log, a un traceback ni a una respuesta de la API. |
| VIII — Un idioma para cada audiencia | Sí | Este plan y la spec en español; código, eventos y commits en inglés; los strings de la UI en español. |
| IX — Las dependencias entran por la puerta | Sí | El envío reusa el cliente de Evolution API que la 001 ya construyó en `notifications`: **cero dependencias nuevas**, y ni siquiera un cliente nuevo. La feature además probablemente **quite** una (`python-jose`), con `uv remove` y el lockfile en el mismo commit. |

**Excepciones solicitadas:** ninguna.

## Enfoque

La feature no se construye de cero: `identity` ya tiene usuarios, roles, bcrypt, login, cambio de
clave y recuperación, y el frontend ya tiene login, cookie `httpOnly` y proxy. Lo que este plan
hace es **cerrar la distancia entre eso y los 53 requisitos firmados**, y hay cuatro huecos que no
se tapan agregando rutas: la sesión, la matriz de permisos, la invitación y el registro de accesos.

**La sesión pasa a vivir en la base.** Hoy es un JWT firmado de 8 horas, y un JWT no se puede
apagar: RF-20 exige que desactivar a una persona cierre sus sesiones abiertas, RF-26 que cambiar la
clave invalide lo anterior, RF-53 lo mismo al reactivar, y RF-05 que el cierre se cuente por
**inactividad** y no por antigüedad —un `exp` se fija al emitirse y no sabe si alguien siguió
trabajando—. Los cuatro requisitos piden lo mismo: que exista algo del lado del servidor que se
pueda revocar y tocar. Entonces el token deja de ser un JWT y pasa a ser un valor opaco
(`secrets.token_urlsafe`), guardado **hasheado** en `identity.session`, que se resuelve en cada
request y lleva su `last_seen_at`. Para no pagar un `UPDATE` por request, `last_seen_at` se refresca
sólo si envejeció más de 60 segundos: con tres personas la diferencia es invisible y la propiedad
que importa —la sesión muere a las ocho horas sin uso— se conserva exacta.

**El permiso deja de ser "qué rol sos" y pasa a ser "qué podés hacer en esta sección".** Hoy
`require_roles(...)` decide por rol y admite al dueño siempre; RF-32 a RF-35 piden un nivel más:
ventas **ve** el calendario y no lo edita, compras **ve** los precios y además pide la lista a mano
y resuelve lo apartado. Se resuelve con una **matriz estática** en `identity` —sección × rol →
`NONE | READ | WRITE`— y una dependencia nueva, `require_section(Section.CALENDAR, Level.WRITE)`,
que cada ruta declara. La matriz es código y no una tabla, a propósito: la spec fija los tres roles
y dice que no hay pantalla donde armar uno nuevo, así que una tabla sería configurabilidad que
nadie pidió y superficie que hay que defender. Sale de `dependencies.py`, que es el único archivo
que puede cruzar la frontera, y por eso ningún módulo necesita importar `UserRole` para declarar lo
suyo — que es la razón por la que `require_purchasing()` ya existía.

**El dueño nunca fija la clave de nadie.** RF-44 lo prohíbe y RF-42 dice cómo: el alta pide nombre,
correo, teléfono y rol, e `identity` publica `UserInvited`. `notifications` —que ya habla WhatsApp
por la 001— escucha ese evento y **encola una task**, porque una llamada a un servicio ajeno dentro
de la transacción del publicador la tendría abierta mientras dura. Es la misma decisión que en
la 001 tomó el handler de `ProductsRegistered`. La invitación y la recuperación son el mismo
mecanismo con distinto propósito: un token de un solo uso, con vigencia, guardado hasheado en
`identity.credential_token`, que la persona canjea definiendo su clave. Reactivar a alguien (RF-51)
es exactamente invitarlo de nuevo, y por eso el ciclo de estados vuelve a `Invitado` y no a
`Activo`: la clave vieja se invalida en el mismo movimiento (RF-53).

**Todo intento queda escrito.** `identity.access_event` guarda los ingresos (RF-29), los rechazos de
credenciales, los bloqueos por intentos fallidos (RF-47), los 403 de permiso (RF-14) y lo que el
dueño hizo sobre los accesos ajenos (RF-23) — para lo cual la fila distingue **quién lo hizo** de
**a quién le pasó**, que en un ingreso son la misma persona y en una desactivación no. Los tres
primeros los escribe el servicio de identidad, que es quien los vive. El 403 no: lo levanta una
dependencia, en cualquier ruta de cualquier módulo, y una excepción aborta la transacción que
tendría que guardarlo. Se resuelve con un **middleware** que ve la respuesta ya emitida y
escribe la fila en su propia sesión. La alternativa era que cada ruta se acordara de registrar su
propio rechazo, que es exactamente el tipo de regla que se olvida.

**El middleware vive en `identity/middleware.py`, y `main.py` sólo lo registra.** La distinción no
es cosmética: el test de fronteras recorre `app/modules/` y no alcanza a `main.py`, así que poner
ahí la lógica —resolver quién llamaba, abrir sesión, escribir en `access_event`— sería legal y aun
así convertiría al composition root en el primer lugar del proyecto con lógica de dominio afuera de
un módulo. Adentro de `identity` el middleware sólo importa lo suyo, y `main.py` sigue haciendo lo
único que la arquitectura le pide: registrar. Es la misma forma que ya tiene `dependencies.py`
—composición que vive en el módulo y se monta desde afuera—, y por la misma razón.

Del lado del frontend, **el menú no decide nada**: `GET /auth/me` devuelve la matriz efectiva de
quien pregunta —qué secciones ve y con qué nivel— y la navegación se dibuja con eso. Es lo que
impide que el menú y el backend se desincronicen, y lo que evita duplicar en TypeScript una regla
que ya vive en el servicio. Pantallas nuevas: administración de accesos y registro de actividad
(las dos sólo para el dueño), aceptar invitación, y la propia cuenta. Un 403 del backend muestra
una pantalla de "no tenés permiso", no una redirección al login: la diferencia entre *no entraste* y
*no te toca* es visible para quien la sufre y para quien la audita.

## Módulos afectados

| Módulo | Qué cambia | Nuevo |
|---|---|---|
| `identity` | El grueso. Sesiones en base con inactividad, matriz de permisos y `require_section`, invitación y reactivación por token, bloqueo por intentos fallidos, registro de accesos, invariantes de dueño único y de no auto-desactivación, y la proyección de los tres parámetros. Deja de emitir JWT. | No |
| `notifications` | Dos handlers nuevos que encolan su task. **No aprende un canal nuevo**: reusa el cliente de Evolution API de la 001, con otro texto y otro destinatario. Es la costura donde el módulo deja de servir a una sola feature. | No |
| `operations` | Tres parámetros nuevos en `operations.parameter`: inactividad de sesión, intentos permitidos y minutos de bloqueo. Ninguna tabla nueva. | No |
| `main.py` | Registra el middleware de `identity` y el router de accesos. **Sólo registra**: el middleware no se escribe acá. | — |
| `frontend` | Cuatro rutas nuevas y la navegación por permisos. | — |

> **Ningún módulo nuevo, y es una señal buena.** Los accesos no son una capacidad del negocio con
> lenguaje propio que no existiera: son la que `identity` ya tenía a medias. Un módulo `permissions`
> aparte habría necesitado leer usuarios y roles todo el tiempo, que es la definición de dos módulos
> que en realidad son uno.

## Eventos de dominio

Cuatro eventos nuevos en `app/shared/events/catalog.py`, en pasado, congelados, con identificadores
y valores planos (`GEN-08`). `UserRegistered` y `UserDeactivated` ya existen y se reusan;
`BusinessParameterChanged` también, y acá gana su primer consumidor.

| Evento | Lo publica | Lo consume | Qué lleva |
|---|---|---|---|
| `UserInvited` | `identity` | `notifications` | `user_id`, `email`, `token`, `expires_at`, `reason` — `NEW_ACCESS` o `REACTIVATION` |
| `PasswordResetRequested` | `identity` | `notifications` | `user_id`, `email`, `token`, `expires_at` |
| `UserReactivated` | `identity` | — (por ahora) | `user_id` |
| `UserRoleChanged` | `identity` | — (por ahora) | `user_id`, `previous_role`, `role` |
| `BusinessParameterChanged` *(existe)* | `operations` | `identity` | `key`, `value` |

Tres decisiones que conviene no rediscutir:

- **El token viaja en el evento, y es deliberado.** Un mensaje sin el token no sirve, y
  `notifications` no puede pedírselo a `identity` sin importarlo. El bus es en proceso, el evento no
  se persiste y la publicación no se loguea: el token vive en memoria entre el servicio que lo
  generó y la task que lo manda. **Consecuencia operativa: ningún log del bus puede volcar el
  payload de un evento.** Si alguna vez se agrega ese log, este es el evento que lo prohíbe.
- **`UserReactivated` y `UserRoleChanged` se publican sin oyentes.** Publicar sin audiencia es legal
  y acá es barato: son los dos hechos que el resto del negocio va a querer escuchar primero —el
  tablero de P3, los avisos de P8— y declararlos ahora cuesta dos dataclasses.
- **La invitación y la reactivación son el mismo evento con distinto `reason`.** No son dos
  mecanismos: son el mismo token con otro texto en el mensaje. Partirlo en dos eventos obligaría a
  `notifications` a saber por qué se invitó a alguien, que no es asunto suyo.

## Datos

Tres tablas nuevas, una tabla renombrada y cuatro columnas nuevas, todas en el schema por defecto,
junto a las de `identity`. El detalle —columnas, tipos, índices, estados— está en
[`data-model.md`](data-model.md). El resumen:

| Tabla | Dueño | Para qué |
|---|---|---|
| `sessions` | `identity` | La sesión revocable con su `last_seen_at`. Reemplaza al JWT |
| `credential_token` | `identity` | Invitación y recuperación: un solo uso, con vigencia, hasheado. **Reemplaza a `password_reset_tokens`** |
| `access_event` | `identity` | Ingresos, rechazos, bloqueos, 403 de permiso y los cambios de acceso del dueño (RF-23), con actor y sujeto distinguidos |
| `access_setting` | `identity` | Proyección de los tres parámetros de `operations` |
| `users` *(existe)* | `identity` | Se le suman `failed_attempts`, `locked_until`, `invited_at` y `activated_at` |

Los tres parámetros entran en `operations.parameter`, que ya existe con `value` en JSONB:
`access.session_idle_minutes` (inicial `480`), `access.max_failed_attempts` (inicial `5`) y
`access.lockout_minutes` (inicial `15`). Los dos últimos son el supuesto que la spec declara sin
confirmar; que sean parámetros y no constantes es lo que hace que confirmarlos después no cueste un
deploy.

**La migración es `0002_access_control`, no una edición de `0001_initial`.** `0001_initial` está sin
commitear todavía, así que la tentación de editarla existe; se descarta porque la 001 se está
implementando sobre ella y reescribir una migración que otro ya aplicó localmente es la clase de
cosa que rompe el entorno de al lado sin dejar rastro. Cada tabla nueva entra con su línea en
`app/models.py` en el mismo commit (`DB-01`, Blocker).

## Contratos

Toda ruta declara su autorización (`PY-09`, Blocker). Prefijo `/api/v1`. `require_section(...)`
sustituye a `require_roles(...)` en todo lo que no sea la sesión propia.

| Método y ruta | Requisitos | Autorización |
|---|---|---|
| `POST /auth/login` | RF-01, RF-02, RF-19, RF-29, RF-45, RF-46 | Pública |
| `GET /auth/me` | RF-03, RF-06, RF-07 | Cualquier sesión activa |
| `POST /auth/logout` | RF-04 | Cualquier sesión activa |
| `POST /auth/password/change` | RF-25, RF-26 | Cualquier sesión activa, sólo sobre sí mismo |
| `POST /auth/password-reset/request` | RF-27, RF-38, RF-39 | Pública |
| `POST /auth/password-reset/confirm` | RF-40, RF-41 | Pública — el token es la credencial |
| `GET /auth/invitation/{token}` | RF-43 | Pública — sólo dice si el token sirve |
| `POST /auth/invitation/{token}` | RF-42, RF-43, RF-52 | Pública — la persona define su clave |
| `GET /users` | RF-24 | `ACCESS_ADMIN: READ` → sólo dueño |
| `POST /users` | RF-16, RF-23, RF-37, RF-42, RF-44, RF-50 | `ACCESS_ADMIN: WRITE` |
| `GET /users/{user_id}` | RF-24 | `ACCESS_ADMIN: READ` |
| `PATCH /users/{user_id}` | RF-17, RF-23, RF-50 | `ACCESS_ADMIN: WRITE` |
| `POST /users/{user_id}/deactivate` | RF-18, RF-20, RF-22, RF-23 | `ACCESS_ADMIN: WRITE` |
| `POST /users/{user_id}/reactivate` | RF-51, RF-52, RF-53, RF-23 | `ACCESS_ADMIN: WRITE` |
| `GET /access-log` | RF-30, RF-31, RF-47 | `ACCESS_LOG: READ` → sólo dueño |

**RF-12, RF-13 y RF-15 no son filas de esta tabla: son propiedades de todas.** Que el permiso se
verifique antes de responder, que un rechazo se informe y que una request sin sesión activa no pase
no son endpoints, son la condición de cada uno. Por eso no se implementan una vez por ruta sino en
la dependencia que todas declaran, y por eso lo que los sostiene no es la revisión sino
`tests/architecture/test_route_authorization.py`, que ya falla por cada endpoint que responde sin
decidir quién lo llama. Esta feature le agrega el segundo nivel: una ruta que declara sección pero
no nivel también tiene que romper el build.

Cuatro precisiones que son contrato y no detalle:

- **`GET /auth/me` devuelve la matriz efectiva** del que pregunta: `{ user, permissions: {section:
  level} }`. Es lo que dibuja el menú (RF-07) y lo que impide que la UI invente un permiso.
- **`DELETE /users/{user_id}` desaparece.** Hoy existe y desactiva: un `DELETE` que no borra miente
  sobre lo único que RF-21 no permite hacer, y con la reactivación al lado hacen falta dos verbos
  simétricos. Nadie lo consume todavía.
- **`GET /users` y `GET /users/{user_id}` se cierran al dueño.** Hoy los ve cualquier rol
  autenticado. RF-24 dice que la administración de accesos es del dueño y RF-31 que el resto no ve
  la actividad ajena; que compras pueda listar los correos y roles del equipo no lo pide ningún
  requisito.
- **`POST /users` responde `201` sin cuerpo de credencial.** Nunca devuelve token ni clave: el token
  sale por WhatsApp o no sale.

## Alternativas descartadas

- **Mantener el JWT y agregarle una `token_version` en `users`.** Revocaría en masa al desactivar y
  al cambiar la clave, sin tabla de sesiones. Se descarta porque no resuelve RF-05: la inactividad
  necesita saber cuándo fue la última actividad, y eso es estado del servidor con cualquier nombre
  que se le ponga. Media solución con la misma escritura por request.
- **JWT corto más refresh token.** Es el patrón estándar cuando hay muchos clientes y escala. Acá
  hay tres personas y un frontend propio: duplica el camino de autenticación para ahorrar una
  consulta por request en una base que atiende tres usuarios.
- **La matriz de permisos en una tabla configurable.** Permitiría cambiar quién ve qué sin deploy.
  Se descarta porque la spec fija tres roles y declara fuera de alcance armar uno nuevo: sería
  construir la pantalla que el cliente decidió no tener, con el riesgo de que una fila mal editada
  abra una sección.
- **Un módulo `authorization` separado de `identity`.** Se descarta: necesitaría leer usuarios y
  roles en cada request, y dos módulos que se leen todo el tiempo son uno solo mal partido.
- **Registrar los 403 desde cada ruta.** Se descarta: es una regla que depende de que 40 rutas se
  acuerden. El middleware lo hace una vez y no se olvida.
- **Registrar los 403 desde un `exception_handler` de FastAPI.** Más cerca del error que un
  middleware, pero corre dentro del contexto de la request cuya transacción ya está abortada. El
  middleware ve la respuesta terminada y abre su propia sesión.
- **Correo por SMTP, que fue el primer diseño de este plan.** Se descarta por una razón operativa y
  no técnica: **Cordillera no tiene dominio propio**, y sin dominio verificado ningún proveedor deja
  mandarle a Marcela ni a Julián — los que permiten remitentes de dominios gratuitos reescriben la
  dirección del remitente, así que el mensaje llega firmado por otro. Comprar un dominio costaba
  poco pero es una decisión del cliente, y WhatsApp ya estaba construido.
- **Un canal de correo además de WhatsApp, como respaldo.** Se descarta: dos canales para el mismo
  mensaje es el doble de configuración y de fallos posibles para un equipo de tres personas, y el
  respaldo real cuando WhatsApp no entrega es que el dueño está en la misma oficina.
- **Guardar los tokens de invitación en claro**, como hoy hace `password_reset_tokens`. Se descarta:
  un token en claro en la base es una clave en la base. Se guarda el hash y se compara.

## Riesgos

| Riesgo | Impacto | Cómo se mitiga |
|---|---|---|
| **Sacar el JWT toca el camino de autenticación entero**, que es lo único que ya funciona de punta a punta. | Un error deja a todo el mundo afuera, incluida la 001 que se está construyendo encima. | El contrato HTTP no cambia —`POST /auth/login` sigue devolviendo `access_token` y el frontend sigue guardándolo en la cookie `httpOnly`—: lo que cambia es qué hay adentro del string y cómo se resuelve. Ninguna pantalla se entera. |
| **Entrar al sistema pasa a depender de WhatsApp.** Hasta ahora el canal sólo llevaba avisos: si fallaba, alguien no se enteraba de un vencimiento. Ahora, si falla, **nadie puede entrar por primera vez ni recuperar su clave**. | Un canal caído deja a una persona afuera del sistema. | El envío vive en una task: si falla, falla visible como `JobRun` y **el token sigue siendo válido**, así que se reenvía sin regenerar nada. Y el dueño puede volver a disparar la invitación desde su pantalla. Para desarrollo y tests, un emisor que escribe el mensaje en disco en vez de mandarlo. |
| **El primer acceso del dueño no existe todavía**, y con la invitación por WhatsApp nadie puede crearlo desde la aplicación. | El sistema arranca sin nadie adentro. | Un comando de puesta en marcha que crea el único acceso `OWNER` a partir de variables de entorno, idempotente, y que exige cambiar la clave en el primer ingreso. Es puesta en marcha, no una ruta HTTP: una ruta que crea dueños es una puerta trasera. |
| **Un `UPDATE` de `last_seen_at` por request** contra la tabla de sesiones. | Escritura en el camino más caliente de la aplicación. | Se refresca sólo si envejeció más de 60 segundos. Con tres personas es irrelevante; queda escrito para que nadie lo "optimice" quitando la ventana y rompa RF-05. |
| **El bloqueo por intentos fallidos se puede usar para dejar a alguien afuera** conociendo su correo. | Denegación de servicio contra una persona concreta. | El bloqueo es temporal y corto —quince minutos— y no lo levanta un humano, así que el ataque cuesta más de lo que rinde. Cada bloqueo queda en el registro que ve el dueño (RF-47), que es cómo se entera de que está pasando. |
| **La matriz de permisos crece con cada feature.** Nueve secciones hoy, y P2 a P12 van a sumar. | Una sección nueva sin fila en la matriz es una sección sin permiso, o peor, con el de otra. | La matriz se declara completa: un `Section` sin entrada para un rol es un error de tipos, no un `None` silencioso. El test recorre el producto cartesiano rol × sección contra la tabla de la spec. |
| **La 001 se está implementando en paralelo** y sus once rutas declaran `require_roles(...)`. | Dos convenciones de autorización conviviendo. | `require_roles` se mantiene hasta que las rutas de la 001 migren a `require_section`, y la migración es una tarea explícita de esta feature, no un "después". Las dos conviven sin romperse: la nueva es más fina, no incompatible. |

## Contexto de traspaso

**Para el Developer** — Empezá por la sesión: es lo que más cosas rompe y lo que todo lo demás
asume. El orden que menos duele es `identity.session` → `require_section` y la matriz →
invitación y `credential_token` → bloqueo → `access_event` y el middleware → los dos handlers de
`notifications` → frontend. Cada paso deja la aplicación funcionando.

**Lo que NO tenés que tocar:** `operations.Parameter` y `JobRun` ya existen y alcanzan;
`app/shared/errors.py` ya tiene `AuthenticationError` y `ConflictError`, no agregues excepciones
nuevas para esto; el proxy del frontend y la cookie `httpOnly` funcionan y no cambian.

**Decisiones ya tomadas, no las rediscutas:** la sesión es server-side y opaca, no un JWT; la
matriz de permisos es código en `identity`, no una tabla; el dueño nunca fija la clave de otro, ni
siquiera una inicial; los 403 los registra un middleware, no cada ruta; `identity` no le pregunta
sus parámetros a `operations`, mantiene su proyección. Si alguna te resulta incómoda de
implementar, **es señal de que la frontera está mal trazada y hay que escalar al Backend-Architect**,
no de que convenga un import.

**Para el Tester** — Lo que puede romperse de verdad no es el login: es todo lo que tiene que dejar
de funcionar en un momento exacto. Los casos borde que importan:

- **Desactivar a alguien que está trabajando** (RF-20): su próxima request tiene que dar 401, no la
  siguiente hora. Probalo con la sesión abierta, no con una recién creada.
- **Cambiar la clave no puede dejar viva la sesión vieja de otro navegador** (RF-26), y **reactivar
  no puede revivir la clave anterior** (RF-53).
- **La inactividad se cuenta desde la última actividad, no desde el login** (RF-05, RF-36): una
  sesión usada a las 7 horas 59 sigue viva a las 9. Es el caso que la ventana de 60 segundos podría
  romper.
- **Los tres finales de un login fallido son indistinguibles** (RF-02, RF-19, RF-46): correo que no
  existe, clave equivocada, acceso desactivado y acceso bloqueado tienen que devolver el mismo
  status, el mismo cuerpo y —en lo posible— el mismo tiempo.
- **La misma indistinguibilidad en la recuperación** (RF-39): una dirección que no existe responde
  lo mismo que una que sí.
- **El token de un solo uso, usado dos veces** (RF-40), y **vencido** (RF-41). Los dos, para
  invitación y para recuperación.
- **El dueño único** (RF-50): crear un segundo dueño y ascender a alguien a dueño tienen que fallar
  las dos, y **el dueño no puede desactivarse** (RF-22).
- **La matriz completa**, rol por rol y sección por sección, contra la tabla de la spec. Es un test
  parametrizado, no nueve tests escritos a mano: lo que importa es que **ninguna combinación quede
  sin probar**.
- **El nivel, no sólo la sección** (RF-33): ventas hace `GET` del calendario y le responde 200; hace
  `POST` y le responde 403. Ese par es la feature entera.
- **El 403 queda registrado** (RF-14) **y el bloqueo también** (RF-47). Verificá que el middleware
  escriba la fila aunque la transacción de la request haya abortado: es su única razón de existir.

**Para el Code-Reviewer** — Las convenciones en juego, por orden de riesgo:

- **`PY-09`** — es la feature que define la autorización de todo el proyecto. Revisá que cada ruta
  declare `require_section` con el nivel correcto contra la tabla de *Contratos*, y que el
  `PUBLIC_ROUTES` del test crezca sólo con las dos rutas de invitación, cada una con su razón
  escrita.
- **`GEN-02`, `GEN-08`** — `notifications` no puede importar nada de `identity`, y el token viaja en
  el evento. Mirá que ningún handler reciba un modelo de SQLAlchemy y que ningún log imprima un
  evento entero.
- **`SEC-01`, `SEC-03`, `SEC-05`** — no hay variables nuevas de canal: las de Evolution API ya
  existen. Lo que sí hay que mirar es que el emisor por defecto sea el que escribe a disco, no uno
  que le mande un WhatsApp de verdad a alguien desde una máquina de desarrollo.
- **Artículo VII, por analogía** — buscá tokens y claves en logs, en `detail` de excepciones y en
  respuestas de la API. `POST /users` no devuelve token; `password-reset/request` responde siempre
  lo mismo; el `access_event` guarda el correo intentado, **nunca la clave intentada**.
- **`DB-01`** — cuatro tablas y cuatro columnas nuevas: `alembic check` limpio y cada modelo en
  `app/models.py` en el mismo commit.
- **Lo que hay que buscar por ausencia** — que no haya quedado ninguna ruta con `require_roles` una
  vez migradas las de la 001, y que `password_reset_tokens` no siga existiendo al lado de
  `credential_token`. Dos mecanismos para lo mismo es cómo se cuela el que nadie mantiene.
