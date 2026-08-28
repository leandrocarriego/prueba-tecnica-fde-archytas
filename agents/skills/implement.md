# Skill — Implementar una feature desde sus tareas

Tags: [implementación] [sdd]

Rol dueño: **Developer**.

## Objetivo
Construir la feature ejecutando su `tasks.md`, cada tarea por la skill que tiene asignada.

## Cuándo usarla
- Después de que `analyze` dio **consistente**.
- Nunca antes: implementar sobre documentos inconsistentes multiplica el retrabajo.

## Precondiciones
- `analyze` dio consistente.
- Se trabaja en una rama de feature, nunca en `main` (`GIT-01` es Blocker).

## Reglas (ESTRICTO)
- **Ningún import a otro módulo.** Los módulos se comunican por eventos (Artículo IV); lo
  verifica `test_module_boundaries.py`.
- **No se debilita un test para pasar** (`TEST-06`). Si un test molesta, o el código está mal o el
  test está mal: las dos cosas se arreglan, ninguna se silencia.
- **No se amplía el alcance.** Si `tasks.md` es ambiguo o contradice la spec, se frena y se escala
  al `Lead`.
- **No se commitea.** Eso es del `Release-Manager`, con `ship_changes`, y después del quality gate.

## Pasos (ORDEN OBLIGATORIO)
1. Leer el **Contexto de traspaso** del plan antes de tocar nada: dice por dónde empezar, qué no
   tocar y qué decisión ya está tomada.
2. Ejecutar las tareas **en el orden de `tasks.md`**, historia por historia. Al terminar las de H1
   tiene que haber algo que funcione de punta a punta.
3. Para cada tarea, abrir su skill y seguir sus pasos **en orden**, incluida su validación.
   Saltearse una skill existente es un error.
4. Escribir los tests unitarios de la propia lógica a medida que se avanza (`TEST-01`).
5. Antes de dar una tarea por terminada, correr lo que la verifica:
   ```bash
   cd backend && uv run ruff format app tests && uv run ruff check app tests && uv run mypy app && uv run pytest
   cd frontend && npm run lint && npm run type-check
   ```
6. Marcar en `tasks.md` lo que va quedando hecho.

## Validación
- [ ] La suite pasa y la cobertura no bajó.
- [ ] Los tests de arquitectura siguen en verde.
- [ ] Se informó qué tareas quedaron hechas, cuáles no y por qué.
- [ ] Siguen los tests de sistema del `Tester`, después `converge` y `review_feature`.

## Errores comunes (evitar)
- Marcar una tarea como hecha sin haber corrido su validación.
- Resolver una ambigüedad de `tasks.md` decidiendo por cuenta propia.
