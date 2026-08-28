# Skill — Agregar tests

Tags: [backend] [frontend] [testing] [calidad]

## Objetivo
Escribir los tests de una feature siguiendo las convenciones del proyecto:
- unitarios para servicios, parsers y lógica pura
- de integración para endpoints, repositorios y migraciones
- de extracción para los parsers del portal, contra **HTML fijado**
- cobertura que valide los criterios de aceptación de la spec (> 80%)

## Cuándo usarla
- Después de implementar una feature (backend o frontend).
- Al agregar funcionalidad a un módulo existente.
- Al corregir un bug (test de regresión primero).
- Al refactorizar (para asegurar que el comportamiento se preserva).

## Precondiciones
- El código de la feature está implementado y es importable.
- Las migraciones están aplicadas (`uv run alembic upgrade head`).
- Las dependencias están instaladas (`uv sync`).

## Reglas (ESTRICTO)
- El acceso a datos es async: los tests que tocan la base usan `pytest-asyncio` y `AsyncSession`.
- Los parsers del portal se testean **siempre** contra HTML fijado en fixtures, **nunca**
  contra SIGProv en vivo.
- Toda task de Celery nueva lleva un test de **idempotencia**.
- Cada test es independiente y se puede correr aislado.

## Pasos (ORDEN OBLIGATORIO)

### 1) Identificar el alcance
Determinar qué hay que testear:

| Componente | Tipo de test | Ubicación |
|-----------|--------------|-----------|
| Lógica de servicio | Unitario | `tests/unit/services/` |
| Parsers del portal | Unitario (con fixtures HTML) | `tests/unit/parsers/` |
| Normalización de `shared/` | Unitario | `tests/unit/shared/` |
| Repositorio | Integración | `tests/integration/repositories/` |
| Endpoints de la API | Integración | `tests/integration/api/` |
| Feature completa | Integración | `tests/integration/features/` |
| Flujos de usuario | E2E | `tests/e2e/` |

### 2) Crear el archivo de test
Convención de nombres: `test_<modulo>_<capa>.py`

```bash
# Ejemplo para el módulo suppliers
touch backend/tests/unit/services/test_suppliers_service.py
touch backend/tests/integration/api/test_suppliers_routes.py
```

### 3) Escribir la estructura del test
Organización por clase, con marcadores de pytest:

```python
"""Tests del servicio de <módulo>."""

import pytest

from app.modules.<module>.service import <Module>Service


@pytest.mark.unit
class Test<Module>Service:
    """<Descripción>."""

    @pytest.fixture
    def service(self, <dependencias>) -> <Module>Service:
        """Instancia del servicio con sus dependencias."""
        return <Module>Service(<dependencias>)

    async def test_<accion>_<resultado_esperado>(self, service) -> None:
        """<Qué verifica>."""
        # Arrange
        # Act
        # Assert
```

Los tests que tocan código async van marcados con `@pytest.mark.asyncio` (o con el modo
automático de `pytest-asyncio` configurado en el proyecto).

### 4) Seguir el patrón AAA
Todo test tiene sus tres secciones explícitas:

```python
async def test_create_supplier_success(self, client) -> None:
    """Alta de proveedor exitosa."""
    # Arrange
    payload = {"legal_name": "Metalurgica Sur SA", "tax_id": "30712345678"}

    # Act
    response = await client.post("/suppliers", json=payload)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["legal_name"] == payload["legal_name"]
    assert "id" in data
```

### 5) Usar los fixtures apropiados

**Tests unitarios** — dependencias mockeadas, sin base de datos:
```python
@pytest.fixture
def repository(self) -> AsyncMock:
    """Repositorio mockeado."""
    return AsyncMock(spec=SupplierRepository)
```
Un test unitario de servicio mockea **su propio repositorio**, y nada más. No hay servicios
ajenos que mockear: un módulo nunca importa otro módulo (Artículo IV). Lo que llega de afuera es
un evento, y se prueba publicándolo — no simulando al vecino.

**Tests de integración** — sesión async real de `conftest.py`:
```python
async def test_get_supplier(self, client, session) -> None:
    # `client` y `session` vienen de conftest.py; la transacción se revierte al final
    ...
```

### 6) Crear factories para los datos de prueba
Ubicación: `tests/factories/<entidad>_factory.py`

```python
"""Factory de <Entidad> para tests."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.<module>.models import <Entidad>


class <Entidad>Factory:
    """Factory de <Entidad>."""

    @staticmethod
    async def create(session: AsyncSession, **kwargs: object) -> <Entidad>:
        """Crear una instancia."""
        defaults: dict[str, object] = {"field1": "valor_por_defecto", "field2": 123}
        defaults.update(kwargs)

        instance = <Entidad>(**defaults)
        session.add(instance)
        await session.flush()
        return instance

    @staticmethod
    async def create_batch(session: AsyncSession, count: int, **kwargs: object) -> list[<Entidad>]:
        """Crear varias instancias."""
        return [await <Entidad>Factory.create(session, **kwargs) for _ in range(count)]
```

### 7) Fijar el HTML del portal (tests de extracción)
- Guardar el HTML capturado en `tests/fixtures/portal/<seccion>_<fecha>.html`.
- El parser se testea como función pura: HTML → filas tipadas.
- Casos obligatorios por sección:
  - listado con varias filas
  - listado vacío
  - paginación de más de una página
  - fila con un dato ilegible → tiene que ir a **cuarentena**, no lanzar excepción
  - HTML con la estructura cambiada → error de extracción explícito
- **Nunca** abrir un navegador contra SIGProv dentro de la suite.

### 8) Testear los casos de error
Siempre incluir los casos negativos:

```python
async def test_get_supplier_not_found(self, client) -> None:
    """Proveedor inexistente."""
    response = await client.get("/suppliers/99999")

    assert response.status_code == 404


async def test_create_supplier_invalid_tax_id(self, client) -> None:
    """CUIT inválido."""
    response = await client.post("/suppliers", json={"legal_name": "X", "tax_id": "123"})

    assert response.status_code == 422
```
Los servicios lanzan errores de dominio (`NotFoundError`, `ConflictError`, …): en los tests
unitarios se verifica el error de dominio; en los de integración, el código HTTP al que
`main.py` lo mapea.

### 9) Testear permisos (si aplica)
Para las features con control de acceso por rol (módulo `identity`):

```python
async def test_operator_cannot_delete_supplier(self, client, session) -> None:
    """Un operador no puede eliminar proveedores."""
    # Arrange
    supplier = await SupplierFactory.create(session)

    # Act — autenticado como operador
    response = await client.delete(f"/suppliers/{supplier.id}")

    # Assert
    assert response.status_code == 403
```

### 10) Testear la idempotencia de las tasks
Toda task nueva lleva este test:

```python
async def test_extract_section_is_idempotent(self, session) -> None:
    """Ejecutar la extracción dos veces no duplica filas en raw."""
    await extract_section(section="invoices")
    await extract_section(section="invoices")

    assert await count_raw_rows(session, section="invoices") == 1
```

### 11) Correr los tests
```bash
# Todos
cd backend && uv run pytest

# Un archivo
uv run pytest tests/unit/services/test_suppliers_service.py

# Con coverage
uv run pytest --cov=app --cov-report=html

# Por marcador
uv run pytest -m unit
uv run pytest -m integration
```

### 12) Verificar la cobertura
Objetivo: > 80% sobre el código nuevo.

```bash
uv run pytest --cov=app/modules/<module> --cov-report=term-missing
```

## Validación
- [ ] Todos los tests pasan: `uv run pytest`
- [ ] Los tests siguen el patrón AAA (Arrange/Act/Assert)
- [ ] Están cubiertos los casos de éxito **y** los de error
- [ ] Los parsers del portal se testean contra HTML fijado, con el caso de cuarentena incluido
- [ ] Las tasks nuevas tienen test de idempotencia
- [ ] Se usan fixtures y factories en lugar de datos hardcodeados
- [ ] Los tests son independientes y no comparten estado
- [ ] Cobertura > 80% sobre el código nuevo
- [ ] La suite corre con SIGProv apagado

## Errores comunes (evitar)

### 1) Testear la implementación en lugar del comportamiento
```python
# Mal — testea el detalle interno
def test_uses_correct_query(self) -> None:
    assert "SELECT" in service.query

# Bien — testea el comportamiento
async def test_returns_active_suppliers_only(self, service) -> None:
    result = await service.list_active()
    assert all(supplier.is_active for supplier in result)
```

### 2) Dejar datos en la base
```python
# Mal — inserta y no limpia
async def test_create(self, session) -> None:
    session.add(Supplier(legal_name="Test"))
    await session.commit()

# Bien — el fixture de sesión revierte la transacción al terminar
@pytest.fixture
async def supplier(self, session):
    return await SupplierFactory.create(session)
```

### 3) Testear parsers contra el portal en vivo
El test se vuelve lento, frágil y depende de una credencial. Siempre HTML fijado.

### 4) Saltear los casos de error
Siempre: no encontrado, error de validación, permiso denegado, dato ilegible → cuarentena.

### 5) Usar `print` para depurar
Usar `pytest -v` o `pytest --capture=no`.

### 6) Tests que dependen del orden de ejecución
Cada test debe poder correrse aislado.

## Troubleshooting

### Errores de import
- Verificar que existan los `__init__.py` en los directorios de tests.
- Verificar que el módulo sea importable (`uv run python -c "import app.modules.<module>"`).

### Fallan los tests de base de datos
- Aplicar las migraciones: `uv run alembic upgrade head`.
- Verificar que la base de test esté levantada y que `conftest.py` cree los esquemas
  `raw`, `staging`, `core` y `operations`.

### `RuntimeError: no running event loop` o corrutina sin await
- Falta el marcador async o el `await` sobre la llamada al servicio/repositorio.

### No se encuentra un fixture
- Verificar que esté en `conftest.py` o en el mismo archivo, y que el scope coincida.

### Los tests son lentos
- Marcar los lentos con `@pytest.mark.slow` y correr `pytest -m "not slow"` en el bucle corto.
- Revisar los fixtures: un fixture de scope `function` que podría ser `session` se paga en cada
  test.
- **No cambiar un test de integración por uno con mocks para ganar tiempo.** Si la conducta es la
  interacción con la base, el mock no la prueba: sólo prueba que el mock coincide con lo que
  suponés. Se marca lento y se corre en CI.
