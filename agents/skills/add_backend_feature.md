# Skill — Agregar una feature de backend

Tags: [backend] [feature] [modulo]

## Objetivo
Implementar una capacidad nueva del backend respetando el monolito modular:
- la feature vive **dentro de un módulo de dominio**: `backend/app/modules/<module>/`
- si la capacidad no tiene dueño, se crea un **módulo nuevo** con su anatomía completa
- sigue el flujo `routes.py` → `service.py` → `repository.py` → `models.py`
- respeta la frontera: ningún otro módulo lo importa — se enteran por eventos

## Cuándo usarla
- Agregar un endpoint o lógica de negocio nueva en el backend.
- Extender un módulo de dominio existente.
- Crear un módulo de dominio nuevo.

## Precondiciones
- Existe una `spec.md` aprobada en `docs/specs/<NNN-feature>/` y un `plan.md` con las decisiones técnicas.
- Está decidido a qué módulo pertenece la capacidad (ver la tabla de módulos en `AGENTS.md`).
- El nombre del módulo está acordado y es `snake_case`, en inglés y singular por concepto de negocio.
- Están identificados los modelos de base de datos y las integraciones que hagan falta.

## Reglas (ESTRICTO)
- Un módulo **nunca importa otro módulo**: se comunican por eventos de dominio.
  - ✅ `from app.shared.events import events, InvoiceRegistered`
  - ❌ `from app.modules.suppliers.service import SupplierService`
  - ❌ `from app.modules.suppliers.repository import SupplierRepository`
  - ❌ `from app.modules.suppliers.models import Supplier`
- El acceso a datos es **async** (SQLAlchemy 2.0 + asyncpg). No se abren sesiones sincrónicas.
- Los servicios **nunca** lanzan `HTTPException`: lanzan los errores de dominio de
  `app/shared/errors.py`, y `app/main.py` los mapea a códigos HTTP.
- `app/shared/` es transversal y **no importa** de `app/modules/`.
- Un módulo nuevo se justifica sólo cuando aparece una **capacidad del negocio con lenguaje
  propio**, no cuando un módulo existente acumula archivos.

## Pasos (ORDEN OBLIGATORIO)

### 1) Decidir el dueño de la capacidad
- Si la capacidad ya tiene dueño → trabajar dentro de ese módulo y saltar al paso 3.
- Si no lo tiene → crear un módulo nuevo (paso 2) y justificarlo en `plan.md`.
- Si la lógica es transversal y sin dominio (normalización de texto, dinero, paginación,
  errores) → va a `app/shared/`, no a un módulo.

### 2) Crear el módulo nuevo (sólo si hace falta)
Crear `backend/app/modules/<module>/` con su anatomía:
- `__init__.py`
- `routes.py` — endpoints de FastAPI
- `schemas.py` — schemas de Pydantic (contrato HTTP y contrato entre módulos)
- `service.py` — lógica de negocio · **privado del módulo**
- `handlers.py` — reacciones a eventos de otros módulos (sólo si escucha algo)
- `repository.py` — acceso a datos · **privado del módulo**
- `models.py` — modelos de SQLAlchemy · **privados del módulo**
- `tasks.py` — tasks de Celery (sólo si el módulo tiene trabajo en background)

No todos los módulos necesitan las siete piezas: un módulo sin superficie HTTP propia no
lleva `routes.py`, y uno sin trabajo en background no lleva `tasks.py`.

### 3) Definir los schemas (Pydantic)
- Escribir los modelos de request/response en `schemas.py`.
- Nombres descriptivos, tipos precisos y reglas de validación explícitas.
- Los schemas son el contrato hacia afuera: lo que otro módulo recibe del `service` son
  schemas, nunca modelos de SQLAlchemy.

### 4) Definir los modelos (SQLAlchemy 2.0, si hacen falta)
- Escribir los modelos en `models.py` con la sintaxis 2.0: `Mapped[...]` + `mapped_column(...)`.
- Declarar el esquema de PostgreSQL en `__table_args__`:
  - `raw` → lo extraído verbatim + hash · `staging` → tipado/normalizado · `core` → modelo canónico
    · `operations` → jobs, excepciones, parámetros y auditoría.
  - La identidad (usuarios, roles, sesión) va en el **esquema por defecto**.
- **CRÍTICO**: después de crear o modificar modelos, generar la migración de Alembic
  (ver `add_database_migration`).

### 5) Implementar el repositorio
- `repository.py` recibe una `AsyncSession` y concentra todo el acceso a datos del módulo.
- Todos los métodos son `async` y están tipados.
- El repositorio no aplica reglas de negocio ni conoce a FastAPI.

### 6) Implementar el servicio (lógica de negocio)
- `service.py` recibe su repositorio por inyección de dependencias. **No recibe servicios de
  otros módulos**: lo que pasa afuera llega como evento a `handlers.py`.
- Cuando ocurre un hecho que otro módulo podría necesitar, publica:
  `await events.publish(InvoiceRegistered(...), session)`.
- Lanza errores de dominio (`NotFoundError`, `ConflictError`, `ValidationError`,
  `PermissionDeniedError`, …) desde `app/shared/errors.py`.
- Un dato que no se puede interpretar **no** se descarta ni corta la ingesta: va a cuarentena
  en `staging` y genera una fila en `operations.exception`.

### 7) Implementar las rutas (endpoints)
- `routes.py` define un `APIRouter` con `prefix` y `tags` propios del módulo.
- La sesión llega por dependencia: `Depends(get_session)` desde `app.database`.
- Las rutas sólo traducen HTTP ↔ servicio: sin lógica de negocio, sin consultas a la base.

### 8) Registrar el router en `main.py`
El registro es **explícito**: agregar en `backend/app/main.py`
```python
from app.modules.<module>.routes import router as <module>_router

app.include_router(<module>_router)
```
Un módulo nuevo no queda expuesto hasta que su router está registrado acá.

### 9) Agregar tasks de Celery (si hacen falta)
- Crear `tasks.py` dentro del módulo y seguir `add_celery_task` (puente async + idempotencia).
- Las tasks se autodescubren por módulo: no hay que editar la configuración de Celery.

### 10) Agregar tests
- Unitarios para la lógica del servicio (dependencias mockeadas).
- De integración para endpoints y repositorio.
- Si la feature toca parsers del portal, los tests van contra HTML fijado (fixtures), nunca
  contra el portal en vivo.
- Ver `add_tests`.

### 11) Actualizar la documentación
- Si el módulo es nuevo o cambian sus fronteras → actualizar `ARCHITECTURE.md` y la tabla de
  módulos de `AGENTS.md`.
- Documentar los endpoints y el contrato en la spec de la feature.

## Validación
- El módulo importa y su router está registrado en `app/main.py`.
- Los endpoints responden lo esperado (`/docs` los muestra con su tag).
- No hay violaciones de frontera. Verificar:
  ```bash
  cd backend && grep -rnE "from app\.modules\.[a-z_]+\.(repository|models) import" app/modules \
    | grep -v "app/modules/<module>/"
  ```
  (no debe devolver nada: sólo el propio módulo importa su repositorio y sus modelos)
- Ningún servicio lanza `HTTPException`:
  ```bash
  cd backend && grep -rn "HTTPException" app/modules/*/service.py
  ```
- Los tests unitarios y de integración pasan (`uv run pytest`).
- Hay migración creada y aplicada si se tocaron modelos.
- Los type hints están completos; `uv run ruff format app && uv run ruff check --fix app` sin errores.
- Sin dependencias circulares entre módulos.

## Errores comunes (evitar)
- Poner lógica de negocio en `routes.py` (va en `service.py`).
- Importar el `repository.py` o los `models.py` de otro módulo.
- Lanzar `HTTPException` desde un servicio.
- Abrir sesiones sincrónicas o usar la API vieja de SQLAlchemy (`Column`, `declarative_base`).
- Crear modelos sin migración de Alembic.
- Crear un módulo nuevo para algo que es una feature de un módulo existente.
- Olvidarse de registrar el router en `main.py`.
- Hardcodear valores (usar `Settings` o parámetros configurables en `operations`).

## Troubleshooting
- Los modelos quedaron desincronizados → `add_database_migration`.
- Hace falta leer del portal SIGProv → `add_integration`.
- Hace falta trabajo en background → `add_celery_task`.
- Dos módulos necesitan el mismo modelo → el modelo pertenece a uno solo y el otro lo pide por
  servicio. Si eso resulta incómodo, la frontera está mal trazada: se corrige la frontera, no
  la regla.
