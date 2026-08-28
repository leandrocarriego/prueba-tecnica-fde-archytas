# Skill — Agregar una feature full-stack

Tags: [feature] [fullstack]

## Objetivo
Implementar una feature completa (backend + frontend) sobre el monolito modular:
- backend dentro de `backend/app/modules/<module>/`
- páginas en `frontend/app/(private)/<modulo>/`
- componentes en `frontend/components/<modulo>/`
- contrato conectado por los tipos generados desde OpenAPI

## Cuándo usarla
- Agregar una capacidad que necesita API y UI.
- Poner en marcha un módulo de dominio nuevo de punta a punta.

## Precondiciones
- Existe `docs/specs/<NNN-feature>/spec.md` **aprobada** por el cliente y su `plan.md`.
- Está decidido a qué módulo pertenece la capacidad.
- Los modelos de base de datos y los requisitos de UI están identificados.

## Pasos (ORDEN OBLIGATORIO)

### 1) Construir el backend
Seguir `add_backend_feature`:
- ubicar la capacidad en un módulo existente o crear el módulo nuevo en
  `backend/app/modules/<module>/`
- definir `schemas.py`, `models.py`, `repository.py`, `service.py`, `routes.py`
- registrar el router en `backend/app/main.py`

### 2) Migrar la base de datos (si se tocaron modelos)
Seguir `add_database_migration`: generar la migración, revisarla, aplicarla y verificar la
sincronización. El backend tiene que estar funcionando antes de tocar el frontend.

### 3) Generar el contrato
```bash
cd frontend && npm run generate-api-types
```
Los tipos del frontend salen del schema de OpenAPI del backend: no se escriben a mano.

### 4) Construir el frontend
Seguir `add_frontend_feature`:
- página en `frontend/app/(private)/<modulo>/`
- componentes en `frontend/components/<modulo>/` (primitivas en `frontend/components/ui/`)
- acceso a datos en `frontend/lib/`, mutaciones por Server Actions

### 5) Agregar trabajo en background (si hace falta)
Seguir `add_celery_task`: `tasks.py` dentro del módulo, puente async y task idempotente.

### 6) Agregar tests
- Backend: unitarios del servicio + integración de endpoints y repositorio.
- Frontend: tests de componente y del flujo crítico.
- Ver `add_tests`.

### 7) Actualizar diagramas y documentación
- Refrescar los diagramas de la feature (`add_diagrams`) si cambiaron los flujos o los estados.
- Actualizar `ARCHITECTURE.md` / `AGENTS.md` si el módulo es nuevo o cambian sus fronteras.

## Validación
- Los endpoints responden lo esperado y aparecen en `/docs`.
- Las páginas renderizan e interactúan correctamente contra el backend real.
- Los tipos de TypeScript están generados desde OpenAPI y en uso.
- Las migraciones están aplicadas y los modelos sincronizados.
- Los tests pasan (backend y frontend).
- No hay violaciones de la frontera entre módulos.
- Los diagramas de la feature siguen coincidiendo con la spec.

## Errores comunes (evitar)
- Construir backend y frontend por separado y recién al final intentar integrarlos.
- No regenerar los tipos desde OpenAPI después de cambiar los schemas.
- Saltear las migraciones.
- Repartir la misma capacidad entre dos módulos "porque queda más cómodo".
- No manejar los estados de carga y error en el frontend.

## Troubleshooting
- Los tipos quedaron desfasados → regenerar desde el schema de OpenAPI.
- Los modelos quedaron desincronizados → `add_database_migration`.
- Problemas de integración → verificar el router registrado en `main.py`, el prefijo del
  endpoint y la configuración del cliente de API en `frontend/lib/`.
