# Skill — Agregar una migración de base de datos

Tags: [database] [migracion] [alembic]

## Objetivo
Crear y aplicar migraciones de Alembic cuando se modifican los modelos de SQLAlchemy.

**CRÍTICO**: los modelos DEBEN estar sincronizados con las tablas. Esta skill garantiza esa
sincronización.

## Cuándo usarla
- Agregar un modelo de SQLAlchemy nuevo.
- Modificar un modelo existente (agregar/quitar columnas, cambiar tipos, índices, constraints).
- Renombrar columnas o tablas.
- Cualquier cambio del esquema de base de datos.

## Precondiciones
- El modelo vive en el `models.py` de su módulo (`backend/app/modules/<module>/models.py`).
- La base de desarrollo está levantada (`make dev`) y `alembic upgrade head` corre sin cambios
  pendientes antes de empezar.

## Reglas (ESTRICTO)
- **NUNCA** modificar modelos sin crear la migración correspondiente.
- **NUNCA** modificar la base a mano sin migración.
- **SIEMPRE** verificar la sincronización después de aplicar.
- Los esquemas de PostgreSQL son `raw`, `staging`, `core` y `operations`; la identidad va en el **esquema
  por defecto**. Cada modelo declara el suyo en `__table_args__`.
- `raw` es inmutable: una migración nunca reescribe ni "corrige" datos de `raw`.
- El engine de Alembic es **async** (asyncpg), igual que el de la aplicación.

## Pasos (ORDEN OBLIGATORIO)

### 1) Modificar el modelo
- Actualizar el modelo en `backend/app/modules/<module>/models.py`.
- Sintaxis de SQLAlchemy 2.0: `Mapped[...]` + `mapped_column(...)`.
- Type hints correctos y explícitos.
- Verificar que el esquema declarado en `__table_args__` sea el que corresponde al dato
  (`raw` / `staging` / `core` / `operations`, o el esquema por defecto para identidad).

### 2) Generar la migración
```bash
cd backend
uv run alembic revision --autogenerate -m "Descripción del cambio"
```

### 3) Revisar la migración generada
- Abrir el archivo nuevo en `backend/alembic/versions/`.
- Verificar que las altas/bajas de columnas sean las esperadas.
- Verificar los tipos de datos y las constraints.
- Verificar que las operaciones apunten al **esquema correcto** (`schema="core"`, etc.):
  el autogenerate a veces omite el esquema o propone borrar tablas que no conoce.
- Descartar cambios inesperados (tablas de otros esquemas, índices que no se pidieron).

### 4) Editar la migración si hace falta
- Completar a mano lo que el autogenerate no detecta (renombres, cambios de tipo con `USING`,
  índices parciales).
- Agregar migraciones de datos si son necesarias (valores por defecto, backfill).
- Verificar que `downgrade()` sea coherente.

### 5) Aplicar la migración
```bash
cd backend
uv run alembic upgrade head
```

### 6) Verificar la sincronización
- Volver a correr `uv run alembic revision --autogenerate -m "check"`: si genera operaciones,
  el modelo y la base **no** están sincronizados. Corregir y **borrar** esa revisión de control.
- Correr los tests para confirmar que los modelos funcionan.
- Revisar que no haya errores en los logs de la aplicación.

### 7) Commitear
Commitear juntos:
- los cambios de `models.py`
- el archivo de migración (`backend/alembic/versions/...`)

## Validación
- La migración está creada y revisada.
- `uv run alembic upgrade head` se aplicó sin errores.
- Un `--autogenerate` de control no detecta diferencias (modelos sincronizados).
- `uv run alembic downgrade -1` seguido de `upgrade head` funciona.
- Los tests pasan con el esquema nuevo.
- Cada tabla quedó en el esquema que le corresponde.

## Errores comunes (evitar)
- Modificar modelos sin migración.
- Modificar la base a mano.
- No revisar la migración generada.
- Olvidarse del esquema en `__table_args__` (la tabla termina en `public`).
- Aplicar la migración y no commitear el archivo.
- Escribir una migración que corrija datos de `raw`.
- Dejar un `downgrade()` vacío o inconsistente.

## Troubleshooting
- La migración falla → revisar el estado de la base y hacer `alembic downgrade` si hace falta.
- Los modelos quedaron desincronizados → generar una migración de corrección.
- El autogenerate no detecta el cambio → editar la migración a mano (renombres y cambios de
  tipo casi nunca se detectan).
- El autogenerate propone borrar tablas ajenas → falta importar los modelos de algún módulo en
  el entorno de Alembic, o falta `include_schemas` en la configuración.
- `multiple heads` → hay dos ramas de migración: mergearlas con `alembic merge`.
