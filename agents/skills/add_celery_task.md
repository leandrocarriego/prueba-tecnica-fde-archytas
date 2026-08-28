# Skill — Agregar una task de Celery

Tags: [celery] [background] [async]

## Objetivo
Agregar trabajo en background dentro del módulo que lo necesita, con el puente async del
worker y garantía de idempotencia.

**IMPORTANTE**: las tasks viven junto al módulo dueño del trabajo,
en `backend/app/modules/<module>/tasks.py`, y Celery las **autodescubre**: agregar un módulo
nunca implica editar la configuración de Celery.

## Cuándo usarla
- Agregar una operación larga (extracción del portal, reprocesamiento, recálculo).
- Sacar trabajo del ciclo request/response.
- Agregar trabajo programado (beat).

## Precondiciones
- El módulo existe en `backend/app/modules/<module>/`.
- La lógica ya vive (o va a vivir) en el `service.py` del módulo: la task orquesta, no
  implementa reglas de negocio.
- Está definido qué hace idempotente al trabajo (hash de `raw`, clave natural, estado del job
  en `operations`).

## Reglas (ESTRICTO)
- Los workers de Celery son **sincrónicos** y el acceso a datos es **async**. El puente es
  **uno solo**: `app/worker/bridge.py` (`@async_task` / `run_async`).
- **Nunca** usar `asyncio.run()`, `asyncio.new_event_loop()` ni abrir un loop propio en una
  task: asyncpg ata las conexiones al loop que las creó y un loop nuevo por task rompe el pool.
- Toda task **debe ser idempotente**: re-ejecutarla no puede duplicar efectos.
- La task no lanza `HTTPException` ni conoce a FastAPI.

## Pasos (ORDEN OBLIGATORIO)

### 1) Crear `tasks.py` en el módulo
- Crear `backend/app/modules/<module>/tasks.py`.
- Importar `celery_app` desde `app.worker.celery_app` y el puente desde `app.worker.bridge`.
- No hace falta registrar nada: `celery_app` autodescubre las tasks de cada módulo.

### 2) Definir la task sobre el puente async
```python
from app.worker.bridge import async_task
from app.worker.celery_app import celery_app


@celery_app.task(name="<module>.<action>", bind=True, max_retries=3)
@async_task
async def <action>(self, entity_id: int) -> None:
    """Descripción corta del trabajo."""
    ...
```
- El decorador de Celery va **arriba** y `@async_task` **abajo**: el cuerpo queda async y el
  puente lo ejecuta en el loop único del proceso worker.
- Para una llamada async puntual dentro de código sincrónico, usar `run_async(...)` del mismo
  módulo.

### 3) Abrir la sesión dentro de la task
- La task no recibe la sesión de FastAPI: la abre con `SessionFactory` de `app.database` y la
  cierra al terminar.
- Con esa sesión instancia el repositorio y el servicio del módulo, y llama al **servicio**.
- Si otro módulo tiene que enterarse, la task publica un evento; nunca lo importa.

### 4) Garantizar la idempotencia
Elegir y documentar el mecanismo:
- **Hash de `raw`**: si el contenido ya está, no se vuelve a insertar (es el caso de la
  extracción del portal).
- **Clave natural + upsert**: la segunda corrida actualiza en lugar de duplicar.
- **Estado del job en `operations`**: si el job ya está `completado`, la task sale sin efecto.

Además: los argumentos deben ser serializables en JSON (IDs, no objetos de SQLAlchemy).

### 5) Manejar errores y reintentos
- Fallo técnico transitorio (red, portal caído, lock) → `self.retry(exc=exc, countdown=...)`,
  con backoff y `max_retries` explícito.
- Fallo de interpretación de un dato → **cuarentena** en `staging` + fila en `operations.exception`.
  Nunca cortar la corrida entera por una fila ilegible.
- Logging estructurado en el inicio, el fin y cada fallo. Nada de `print`.
- Registrar el resultado del job en `operations` para que la corrida sea auditable.

### 6) Disparar la task
- Desde un servicio o una ruta: `<action>.delay(entity_id)` o `.apply_async(...)`.
- Para trabajo programado, registrar la entrada de `beat_schedule` desde el módulo dueño de la
  task: `app/worker/celery_app.py` no conoce a los módulos.

### 7) Agregar tests
- Testear el cuerpo async directamente (sin worker de por medio).
- Test obligatorio de **idempotencia**: ejecutar dos veces con la misma entrada y verificar
  que el efecto sea el mismo que ejecutándola una vez.
- Testear los reintentos y el camino de cuarentena.

### 8) Documentar
- En la spec de la feature: qué hace la task, cómo se dispara, sus parámetros, su frecuencia,
  su política de reintentos y por qué es idempotente.

## Validación
- La task aparece en el registro del worker: `uv run celery -A app.worker.celery_app inspect registered`.
- No hay loops de eventos sueltos:
  ```bash
  cd backend && grep -rnE "asyncio\.(run|new_event_loop|get_event_loop)" app/modules
  ```
  (no debe devolver nada: el único loop lo administra `app/worker/bridge.py`)
- Ejecutar la task dos veces con la misma entrada no duplica efectos (test de idempotencia en verde).
- Los reintentos funcionan y quedan logueados.
- El resultado del job queda registrado en `operations`.
- Los tests pasan.

## Errores comunes (evitar)
- Usar `asyncio.run()` dentro de una task en vez del puente.
- Poner lógica de negocio en la task en lugar de en el `service.py`.
- Pasar objetos de SQLAlchemy como argumentos de la task.
- Tasks no idempotentes que duplican filas al reintentar.
- Reintentar infinitamente un error que no es transitorio.
- Tragarse las excepciones o usar `print` en lugar de logging estructurado.
- Editar la configuración de Celery para "registrar" la task (se autodescubre).

## Troubleshooting
- La task no se ejecuta → verificar que el worker esté levantado y que el módulo esté bajo
  `app/modules/` (la autodiscovery recorre esos paquetes).
- `attached to a different loop` / errores de asyncpg → hay un `asyncio.run()` suelto: pasar
  todo por `@async_task` / `run_async`.
- Los reintentos no ocurren → revisar `bind=True`, `max_retries` y el uso de `self.retry()`.
- La task duplica datos → falta el chequeo de idempotencia (hash de `raw` o clave natural).
- El trabajo programado no arranca → verificar que el módulo registre su entrada en
  `beat_schedule` y que el contenedor `celery_beat` esté corriendo.
