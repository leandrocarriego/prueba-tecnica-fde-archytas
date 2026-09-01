# Skill — Revisar una feature (Code Review)

Tags: [review] [calidad] [quality-gate]

## Objetivo
Revisar los cambios de una feature para asegurar fiabilidad, mantenibilidad, respeto de las
fronteras entre módulos y cumplimiento de las convenciones de `CONVENTIONS.md`.

> Las convenciones no se reproducen acá. `CONVENTIONS.md` es su fuente única: tiene el texto de
> cada una, si es **Blocker** y el comando que la verifica. Este checklist dice **en qué orden se
> recorren** y qué mirar además de ellas.

## Cuándo usarla
- Cualquier PR o conjunto de cambios que agregue o modifique:
  - features de backend o de frontend
  - módulos de dominio o sus fronteras
  - modelos de base de datos
  - endpoints de la API
  - componentes o páginas
  - integraciones con SIGProv o tasks de background


## Lo esencial (leer antes de arrancar)

- La pregunta de este gate es **"¿está bien escrito?"**. La pregunta *"¿es lo que se acordó?"* es
  de `converge`, y son gates distintos.
- Recorrer `CONVENTIONS.md` → *Índice de Blockers*: **18 hallazgos sobre 34 convenciones**. Citar
  por identificador (`"esto viola PY-06"`), sin copiar el texto de la regla.
- Siete convenciones ya las verifica un test que rompe el build (`GEN-02`, `GEN-03`, `GEN-09`,
  `PY-09`, `TEST-05`, `UI-01`, `UI-02`): si la suite corrió y pasó, no se revisan a ojo. **Si no
  corrió, el review no arranca.** Las dos del diseño están en la suite del frontend (`npm test`),
  así que "la suite" son las dos.
- Un Blocker frena el merge: se arregla, o el changeset no pasa. No hay excepción de agente.
- Terminar con un veredicto explícito —**aprobado** o **bloqueado**— y, si está bloqueado, la
  lista de Blockers por identificador.

Rol: `agents/roles/code_reviewer.md`. Sin argumento, se revisa la rama actual contra `main`.

## Precondiciones
- **La suite corrió y pasó**, la del backend y la del frontend. Siete convenciones las verifica un
  test que rompe el build (`GEN-02`, `GEN-03`, `GEN-09`, `PY-09`, `TEST-05`, `UI-01`, `UI-02`): si
  no corrió, el review no arranca.
- El `Tester` ya pasó: el reviewer verifica que existan tests, no los escribe.

## Pasos (ORDEN OBLIGATORIO) — el checklist de revisión

### 0) Contexto de traspaso
- `docs/specs/<NNN-feature>/plan.md` tiene su sección **Contexto de traspaso**, y sigue siendo
  verdad después de la implementación. Si el código tomó un camino distinto al que el plan
  decidió, el plan se actualiza: un plan que ya no describe lo construido no sirve para el
  próximo que lo lea.
- Empezá el review por su subsección *"Qué necesita mirar el Reviewer"*: dice dónde está el
  riesgo real del cambio y qué invariantes hay que verificar. No reemplaza al checklist, lo
  ordena.

### 1) Fronteras entre módulos
- `GEN-02` — ningún módulo importa otro módulo: la comunicación es **exclusivamente por eventos**.
  La única excepción es `dependencies.py` (autorización). Comando y detalle en `CONVENTIONS.md`.
- `GEN-08` / `GEN-09` — los eventos viven en el catálogo compartido, en pasado e inmutables; un
  handler que falla no se silencia.
- `GEN-03` — `app/shared/` no importa de `app/modules/` y no contiene reglas de negocio.
- `GEN-02` y `GEN-03` las verifica `backend/tests/architecture/test_module_boundaries.py`: si la
  suite pasó, están verificadas. Si no corrió, el review no arranca.
- `GEN-04` — el router del módulo nuevo está registrado explícitamente en `app/main.py`.
- `GEN-05` — sin dependencias circulares entre módulos.
- El código está en el módulo de la capacidad a la que pertenece; un módulo nuevo se justifica
  por lenguaje de negocio propio, no por cantidad de archivos (`ARCHITECTURE.md`).

---

### 2) Reglas del dominio (INVIOLABLES)
Las cinco reglas están en `AGENTS.md` → "Reglas del dominio (INVIOLABLES)". En el changeset se
verifican por sus convenciones:

- `GEN-06` — SIGProv es solo lectura, la extracción es automatización de navegador (no un cliente
  HTTP ni los endpoints JSON internos), el flujo va en un solo sentido y `raw` no se sobrescribe.
  El comando (`grep` sobre `app/modules/portal`) está en `CONVENTIONS.md`.
- `ERR-05` — el dato que no se puede interpretar va a cuarentena en `staging` y genera su fila en
  `operations.exception`; no se pierde ni corta la ingesta con un `raise`.
- `SEC-02` — las credenciales del portal viven sólo en el entorno: no están en el código, ni en la
  base, ni en un log.

Violar cualquiera de estas reglas es **Blocker**.

---

### 3) Cumplimiento de skills
- Feature de backend o módulo nuevo → se siguió `add_backend_feature`.
- Feature de frontend → se siguió `add_frontend_feature`.
- Feature full-stack → se siguió `add_feature`.
- Cambios en modelos → se siguió `add_database_migration`.
- Integración con un sistema externo → se siguió `add_integration`.
- Trabajo en background → se siguió `add_celery_task`.
- Cambió la spec o los flujos → se siguieron `/specify` + `/clarify` y `/diagram`.

---

### 4) Convenciones de código (`CONVENTIONS.md`)

Se recorre el documento **entero**, por área, y cada hallazgo se cita por su identificador
(`"esto viola PY-06"`). No hace falta copiar el texto de la regla en el comentario del review.

Primero, lo que ya está verificado y no se revisa a ojo:

```bash
cd backend && uv run ruff format --check app tests && uv run ruff check app tests  # GEN-01, PY-08
cd backend && uv run mypy app                                                      # PY-10
cd backend && uv run pytest                                # GEN-02, GEN-03, PY-09, TEST-05
cd frontend && npx tsc --noEmit                                                    # TS-01
cd frontend && npm run lint && npm run format:check                        # TS-02, TS-06
cd frontend && npm test                                                    # UI-01, UI-02
```

Si algo de eso está en rojo, el review se frena ahí: son Blockers que el `Developer` tenía que
resolver antes de pedirlo.

Después, área por área — el detalle y el comando de cada una están en `CONVENTIONS.md`:

| Área | Recorrer | Los Blockers del área |
|---|---|---|
| Python | `PY-01` … `PY-10` | `PY-01`, `PY-02`, `PY-04`, `PY-05`, `PY-06`, `PY-08`, `PY-09`, `PY-10` |
| TypeScript y frontend | `TS-01` … `TS-09` | `TS-01`, `TS-02`, `TS-06` |
| Diseño de interfaz | `UI-01` … `UI-10` | `UI-01`, `UI-02` |
| Manejo de errores | `ERR-01` … `ERR-07` | `ERR-03`, `ERR-04`, `ERR-05` |
| Configuración y secretos | `SEC-01` … `SEC-05` | `SEC-01`, `SEC-02` |
| Dependencias | `DEP-01` … `DEP-04` | `DEP-01`, `DEP-02`, `DEP-03` |
| Git y commits | `GIT-01` … `GIT-04` | `GIT-01`, `GIT-03` |

En el frontend, `UI-01` y `UI-02` las decide la suite; el resto de los `UI-*` se mira a ojo y son
justamente los que sostienen el sistema: una sola acción de acento por pantalla (`UI-05`), los
estados dibujados con la píldora (`UI-03`), la plata en mono tabular (`UI-04`) y el aviso arriba
del número que califica (`UI-07`). **Si el changeset toca una pantalla, se abre `docs/design/` y se
compara.**

Los que más se escapan porque **ninguna herramienta los detecta**, y por eso hay que mirarlos a
mano: `PY-03` (imports dentro de funciones — el `select` de Ruff no lo cubre), `PY-04` (mypy corre
con `disallow_untyped_defs = false`, así que una función sin anotar pasa), `PY-07` (idempotencia),
`ERR-01` (excepciones tragadas) y `SEC-04` (valores hardcodeados).

Testing y base de datos tienen sección propia más abajo.

---

### 5) Testing
- `TEST-01` y `TEST-02` — hay tests unitarios de la lógica (servicios, parsers, normalización) y de
  integración de endpoints y repositorios.
- `TEST-03` — los parsers del portal se testean contra HTML fijado, **nunca** contra SIGProv en
  vivo; la suite corre con el portal apagado.
- `TEST-04` — las tasks nuevas tienen test de idempotencia.
- `TEST-05` — la cobertura no bajó del 80% (`--cov-fail-under=80`: lo verifica la corrida).
- `TEST-06` — no se debilitó ningún test para pasar el gate. Mirá el diff de `tests/`, no sólo el
  resultado en verde.

---

### 6) Sincronización de base de datos
- `DB-01` y `DB-02` — los modelos están sincronizados con las tablas; no hay cambios en la base sin
  su migración de Alembic.
- `DB-03` — cada tabla declara el esquema que le corresponde (`raw` / `staging` / `core` / `operations`).
- `DB-04` — la migración autogenerada fue leída antes de commitearse.

---

### 7) Diagramas de flujo
- La feature tiene su set en `diagrams/` (por actor + cross-actor + máquina de estados),
  derivado de la spec (`docs/specs/DIAGRAMS.md`).
- `scripts/diagrams/validate.sh` pasa; actores y estados coinciden con `spec.md` /
  `data-model.md`.
- Los diagramas cara al cliente están en español y sin detalle de implementación (Art. VIII).

---

## Validación
- `CONVENTIONS.md` se recorrió entero y cada hallazgo cita su identificador.
- El revisor puede trazar el recorrido: request → ruta → servicio → repositorio → respuesta.
- Un desarrollador nuevo puede entender la feature leyendo el código, correr los tests y
  desplegar sin sorpresas.
- No quedan Blockers sin resolver.

## Formato de salida (comentarios del review)
- Citar la convención por su identificador (`PY-06`, `ERR-04`, …). Es lo que hace el hallazgo
  discutible sin ambigüedad y verificable por el `Developer`.
- Clasificar los hallazgos con la severidad que `CONVENTIONS.md` le da a cada convención:
  - **Blocker**: frena el merge
  - **Major**: mantenibilidad, manejo de errores, tasks no idempotentes o falta de tests
  - **Minor**: nombres, formato, claridad
- Dar sugerencias de arreglo concretas y accionables.
- Si un hallazgo no corresponde a ninguna convención existente, decilo: o es una preferencia
  personal (y entonces no bloquea), o falta una convención y hay que agregarla a `CONVENTIONS.md`
  vía `add_or_update_skill`.
