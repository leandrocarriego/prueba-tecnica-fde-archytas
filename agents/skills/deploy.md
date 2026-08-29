# Skill — Desplegar la aplicación

Tags: [deploy] [produccion] [release]

## Objetivo
Preparar y desplegar la Plataforma Cordillera en producción con Docker Compose.

## Cuándo usarla
- Desplegar a producción.
- Preparar una release.
- Actualizar el despliegue existente.

## Precondiciones
- El cambio está mergeado en `main`, con tests y `/review-feature` pasados.
- Las migraciones están creadas y probadas en desarrollo.
- Las variables de entorno de producción están configuradas (`.env` a partir de `.env.example`).
- El navegador de Playwright está en la imagen del worker (`backend/Dockerfile`, `playwright install --with-deps chromium`). Sin él la extracción falla en el primer `chromium.launch()`, con la corrida ya abierta.

## Servicios desplegados
`frontend` (Next.js) · `backend` (FastAPI) · `postgres` · `rabbitmq` · `celery_worker` ·
`celery_beat` · `evolution_api` con su `evolution_postgres` y su `evolution_redis` (la salida a
WhatsApp).

## Pasos (ORDEN OBLIGATORIO)

### 1) Verificar las migraciones
- Confirmar que todas las migraciones están aplicadas en desarrollo y que un
  `alembic revision --autogenerate` de control no detecta diferencias.
- Revisar los archivos de migración pensando en producción: volumen de datos, locks, orden.
- Planificar el orden si hay varias migraciones pendientes.

### 2) Revisar las variables de entorno
- Verificar que estén todas las requeridas por `Settings`, comparando contra `.env.example`.
- Confirmar las credenciales del portal SIGProv, la URL de PostgreSQL y la de RabbitMQ.
- Las credenciales viven **sólo** en el entorno: nunca en la base, nunca en el repositorio,
  nunca en un log.
- **Tres grupos hacen que la plataforma sea usable y no sólo que arranque.** Sin ellos levanta,
  sirve el login y no deja entrar a nadie —en silencio, porque ninguno falla ruidosamente—:
  - `OWNER_EMAIL` · `OWNER_NAME` · `OWNER_PHONE` — a quién se le entrega la plataforma. El paso 6
    no tiene a quién crear sin esto.
  - `EVOLUTION_*` y `NOTIFICATIONS_WHATSAPP_TO` — el canal por el que viaja la invitación. Vacías,
    el mensaje sólo se escribe en el log. `NOTIFICATIONS_TO_DISK=true` lo escribe en un archivo,
    que sirve para leer el enlace del dueño sin mandarle un WhatsApp a nadie.
  - `FRONTEND_URL` — a dónde apunta el enlace que va dentro de esa invitación. En el servidor,
    `https://$DOMAIN`. Es la única que no se puede fijar en `docker-compose.yml`.
- En el servidor, además, `DOMAIN`: sin ella el router de Traefik queda sin regla.

### 3) Levantar los servicios

Dos destinos, dos profiles. No se mezclan: `full` no existe en el servidor —ahí sólo el frontend
se publica, detrás de Traefik— y `deploy` no funciona en una laptop, donde no está la red
`traefik`.

```bash
make full      # esta máquina: todo en contenedores, sin reverse proxy
make deploy    # el servidor: trae los cambios con git pull y reconstruye
```

`make deploy` **se corre en el VPS**, nunca desde una laptop, y despliega lo que está en git: si
encuentra cambios sin commitear, se detiene.

### 4) Aplicar las migraciones
```bash
make db-migrate
```
El target detecta si el stack está en contenedores y entra por el camino que corresponde. En el
servidor no hay `uv`: todo corre adentro.

### 5) Verificar el despliegue
- Todos los contenedores en estado `running` (`docker compose --profile deploy ps`).
- El backend responde su health check y expone `/docs`.
- El frontend renderiza el login.
- `celery_beat` está corriendo, y el worker registró sus tasks **y sus handlers**: en el log de
  arranque tiene que aparecer `Handlers discovered`. Un worker con tasks y sin handlers publica
  eventos que nadie escucha, y eso no falla — la extracción guarda en `raw` y ahí se termina.
- Sin errores críticos en los logs.

### 6) Vincular el WhatsApp (sólo la primera vez)

Evolution API sostiene una sesión de WhatsApp, y una sesión la abre una persona con su teléfono.
La instancia se llama como `EVOLUTION_INSTANCE` y **no se publica**: se la alcanza por el túnel
SSH que ya te trae al servidor.

```bash
KEY=$(grep ^EVOLUTION_API_KEY= .env | cut -d= -f2)
curl -s -X POST http://127.0.0.1:8080/instance/create -H "apikey: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"instanceName":"cordillera","qrcode":true,"integration":"WHATSAPP-BAILEYS"}'

# Un código de ocho caracteres para el número que va a MANDAR los mensajes:
curl -s -H "apikey: $KEY" \
  "http://127.0.0.1:8080/instance/connect/cordillera?number=<549...>"
```

En ese teléfono: WhatsApp → **Dispositivos vinculados** → **Vincular con número de teléfono** →
el código. Vence en pocos minutos, así que conviene pedirlo con la pantalla ya abierta; pedir otro
es repetir el segundo comando.

Queda vinculado cuando el estado es `open`:

```bash
curl -s -H "apikey: $KEY" http://127.0.0.1:8080/instance/connectionState/cordillera
```

Recién entonces `NOTIFICATIONS_TO_DISK=false`. Antes de eso los mensajes se escriben a disco, que
es lo correcto: un canal a medio configurar que dice haber mandado algo es peor que uno apagado.

### 7) Crear el primer acceso (sólo la primera vez)
```bash
make db-owner
```
Es idempotente: correrlo dos veces deja un dueño, no dos. Verificar que la invitación **salió**,
no que el comando lo dijo: el log del worker tiene que decir `WhatsApp message sent` y la task
terminar en `{'sent': True}`. Con `NOTIFICATIONS_TO_DISK=true` el mensaje queda como archivo en el
worker, y ahí se lee el enlace.

### 8) Verificar la extracción
- Disparar una corrida de extracción controlada y verificar que deja filas en `raw`.
- Revisar `operations` para confirmar que el job quedó registrado y que la cola de excepciones no
  explotó.

### 9) Monitorear
- Logs de la aplicación y del worker.
- Tasa de errores y de excepciones en `operations.exception`.
- Conexiones a la base y profundidad de las colas de RabbitMQ.

## Validación
- Todos los servicios están corriendo.
- Las migraciones se aplicaron correctamente y los modelos están sincronizados.
- La API y el frontend responden.
- El worker ejecuta tasks, registró sus handlers y `beat` dispara la extracción programada.
- La instancia de WhatsApp está en `open` y un mensaje real salió (`WhatsApp message sent`).
- Hay un dueño, y el enlace que le llegó **se abre sin sesión**: una invitación detrás del guard
  de rutas redirige a un login que esa persona todavía no puede pasar.
- Los logs no muestran errores críticos.
- Los flujos críticos funcionan de punta a punta.

## Errores comunes (evitar)
- Levantar los servicios antes de aplicar las migraciones.
- Faltar variables de entorno (el arranque falla tarde y de forma confusa).
- Desplegar sin verificar después.
- Dejar credenciales del portal en la imagen o en un log.
- Olvidarse de `celery_beat`: la extracción programada deja de correr sin que nada falle.
- Dar por buena una verificación que sólo lee lo que el sistema dice de sí mismo. Los tres
  defectos del primer deploy —el worker sin handlers, la invitación que nunca salió, el enlace
  que rebotaba al login— pasaron todos los tests y todos los health checks.
- Desplegar encima de una extracción en curso: el worker muere en el medio y la corrida queda
  abierta. El latido la cierra, pero recién pasado el límite duro de la task.

## Troubleshooting
- Un servicio no arranca → `docker compose --profile deploy logs <servicio>` en el servidor,
  `--profile full` en esta máquina, y revisar las variables de entorno.
- Falla una migración → revisar la conexión a la base y el archivo de migración; hacer
  `downgrade` si hace falta.
- Errores 5xx en la API → revisar los logs del backend y el estado de PostgreSQL.
- Las tasks no se ejecutan → verificar RabbitMQ y que el worker haya registrado las tasks.
- La extracción corre, deja el documento en `raw` y no pasa nada más → el worker no registró sus
  handlers. Buscar `Handlers discovered` en su log de arranque.
- El latido contesta siempre `requested: False` → hay una corrida `RUNNING` que nadie cerró.
  Mirar `operations.job_run`: si su `started_at` es viejo, el próximo latido pasado el límite la
  cierra solo.
- El enlace de la invitación redirige a `/login` → la ruta no está en `publicPaths` de
  `frontend/proxy.ts`.
- La instancia de WhatsApp no sale de `connecting` y nunca emite un QR, con el log repitiendo
  `Baileys version env` cada dos segundos → la versión de WhatsApp Web que el socket presenta está
  vencida. Ver el comentario de `evolution_api` en `docker-compose.yml`.
- Las tasks de notificación terminan en `{'sent': False}` → mirar `connectionState`: si alguien
  desvinculó el dispositivo desde el teléfono, la sesión se cerró y hay que vincular de nuevo.
- La extracción falla en producción y no en desarrollo → verificar que el navegador de
  Playwright esté instalado en la imagen del worker.
