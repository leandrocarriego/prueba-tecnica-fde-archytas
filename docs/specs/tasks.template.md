# [Nombre de la feature] — Tareas

<!--
  ARTEFACTO INTERNO. Cada tarea mapea a una skill de agents/skills/ y es lo bastante
  chica como para terminarse de una sentada. Si una tarea no tiene skill, o no
  corresponde al proyecto, o falta la skill: preguntá antes de inventarla.
-->

**Feature:** [NNN-feature-slug] · **Plan:** `plan.md`

## Orden

<!-- Las tareas se agrupan por historia de usuario, en orden de prioridad, para que al terminar H1 haya algo entregable de verdad. -->

### H1 — [Título de la historia]

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 1 | | `add_database_migration` | Developer | RF-01 |
| 2 | | `add_backend_feature` | Developer | RF-01, RF-02 |
| 3 | | `add_frontend_feature` | Developer | RF-02 |
| 4 | | `add_tests` | Tester | RF-01, RF-02 |

### H2 — [Título de la historia]

| # | Tarea | Skill | Rol | Cubre |
|---|-------|-------|-----|-------|
| 5 | | | | |

## Cobertura de requisitos

<!--
  Todo requisito funcional de la spec tiene al menos una tarea que lo construye y
  al menos un test que lo verifica. Un RF sin fila acá es alcance firmado que nadie
  se comprometió a hacer — y es exactamente lo que /converge va a encontrar.
-->

| Requisito | Tareas | Test |
|-----------|--------|------|
| RF-01 | 1, 2 | |
| RF-02 | 2, 3 | |
| RF-03 | | |
