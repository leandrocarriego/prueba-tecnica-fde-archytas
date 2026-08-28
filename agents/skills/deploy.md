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
- El navegador de Playwright está disponible en la imagen del worker.

## Servicios desplegados
`frontend` (Next.js) · `backend` (FastAPI) · `postgres` · `rabbitmq` · `celery_worker` ·
`celery_beat`.

## Pasos (ORDEN OBLIGATORIO)

### 1) Verificar las migraciones
- Confirmar que todas las migraciones están aplicadas en desarrollo y que un
  `alembic revision --autogenerate` de control no detecta diferencias.
- Revisar los archivos de migración pensando en producción: volumen de datos, locks, orden.
- Planificar el orden si hay varias migraciones pendientes.

### 2) Revisar las variables de entorno
- Verificar que estén todas las requeridas por `Settings`.
- Confirmar las credenciales del portal SIGProv, la URL de PostgreSQL y la de RabbitMQ.
- Las credenciales viven **sólo** en el entorno: nunca en la base, nunca en el repositorio,
  nunca en un log.

### 3) Construir las imágenes
```bash
docker compose --profile full build
```

### 4) Aplicar las migraciones
```bash
docker compose --profile full run --rm backend alembic upgrade head
```
Las migraciones se aplican **antes** de levantar la aplicación.

### 5) Levantar los servicios
```bash
docker compose --profile full up -d      # o `make full`
```
`full` es el profile que levanta el stack completo en contenedores. Sin él, Compose sólo levanta
Postgres y RabbitMQ, que es el modo de desarrollo.

### 6) Verificar el despliegue
- Todos los contenedores en estado `running` (`docker compose --profile full ps`).
- El backend responde su health check y expone `/docs`.
- El frontend renderiza el login y el dashboard.
- El worker registró sus tasks y `celery_beat` está corriendo.
- Sin errores críticos en los logs.

### 7) Verificar la extracción
- Disparar una corrida de extracción controlada y verificar que deja filas en `raw`.
- Revisar `operations` para confirmar que el job quedó registrado y que la cola de excepciones no
  explotó.

### 8) Monitorear
- Logs de la aplicación y del worker.
- Tasa de errores y de excepciones en `operations.exception`.
- Conexiones a la base y profundidad de las colas de RabbitMQ.

## Validación
- Todos los servicios están corriendo.
- Las migraciones se aplicaron correctamente y los modelos están sincronizados.
- La API y el frontend responden.
- El worker ejecuta tasks y `beat` dispara la extracción programada.
- Los logs no muestran errores críticos.
- Los flujos críticos funcionan de punta a punta.

## Errores comunes (evitar)
- Levantar los servicios antes de aplicar las migraciones.
- Faltar variables de entorno (el arranque falla tarde y de forma confusa).
- Desplegar sin verificar después.
- Dejar credenciales del portal en la imagen o en un log.
- Olvidarse de `celery_beat`: la extracción programada deja de correr sin que nada falle.

## Troubleshooting
- Un servicio no arranca → `docker compose --profile full logs <servicio>` y
  revisar las variables de entorno.
- Falla una migración → revisar la conexión a la base y el archivo de migración; hacer
  `downgrade` si hace falta.
- Errores 5xx en la API → revisar los logs del backend y el estado de PostgreSQL.
- Las tasks no se ejecutan → verificar RabbitMQ y que el worker haya registrado las tasks.
- La extracción falla en producción y no en desarrollo → verificar que el navegador de
  Playwright esté instalado en la imagen del worker.
