# Guía de Agentes — Plataforma Cordillera

**Este es el punto de entrada.** Todo lo que un agente necesita para trabajar en este repositorio está acá, o se delega desde acá al documento que corresponda.

## El proyecto

**Plataforma Cordillera** es la aplicación web a medida de **Ferretería Industrial Cordillera SRL**. Extrae la información del portal legacy **SIGProv**, la normaliza y la convierte en un sistema operativo propio del negocio.

Es un **producto único para un cliente único**, construido como **monolito modular**. El desarrollo se dirige por **Spec-Driven Development (SDD)**, con comandos y plantillas propios inspirados en GitHub Spec Kit.

## Orden de autoridad (OBLIGATORIO)

**La autoridad número uno se carga sola:**

@CONSTITUTION.md

> El import va acá y no en `.claude/CLAUDE.md` para que también lo levante cualquier herramienta
> que lea `AGENTS.md`. La ruta es relativa a **este** archivo, que vive en la raíz.

Cuando dos documentos se contradicen, gana el que está más arriba y se debe informar al usuario
**human in the loop**. Cuando un documento y un **test** se contradicen, gana el test: un test
rompe el build, un documento no.

1. **`CONSTITUTION.md`** - los principios no-negociables. Autoridad número uno; todo `plan.md` se valida contra él (Constitution Check). **Leerlo siempre**, antes de proponer cambios.

2. **`AGENTS.md`** - este archivo: reglas del dominio, fronteras entre módulos, selección de rol, protocolo de skills, flujo de git, Definition of Done e idioma. Se carga solo en toda sesión.

3. **`ARCHITECTURE.md`** - estructura del repositorio, mapa de módulos, fronteras entre módulos y flujo de datos. **No se importa**: solo leerlo al tocar la estructura, agregar un módulo o mover código de lugar.

4. **`CONVENTIONS.md`** - las convenciones de código, fuente única: cada una con su identificador estable (`PY-04`, `TS-02`, `ERR-01`, …), su severidad y el comando que la verifica. Tampoco se importa: lo abre el `Developer` al escribir y el `Code-Reviewer` al revisar.

5. **`agents/roles/` y `agents/skills/`** - el rol bajo el que operás y los procedimientos paso a paso (`add_*`) que hay que seguir durante la implementación. Índice en `agents/skills/README.md`.

6. **`docs/PROJECT_BRIEF.md`** - el alcance acordado con el cliente. Leerlo antes de definir o planificar una feature.

   **`docs/design/`** - el sistema de diseño acordado ("taller ordenado"): paleta, tipografía,
   estados, componentes y las pantallas de alta fidelidad. Es la fuente de **qué significa** cada
   señal visual; `frontend/app/globals.css` es su implementación y `CONVENTIONS.md` → `UI-*` su
   enforcement. Se abre antes de escribir o tocar cualquier pantalla.

7. **`docs/FDE_ASSESSMENT.md`** - el relevamiento técnico preliminar del FDE: hipótesis de solución
   por problema, decisiones transversales sin cerrar y orden sugerido de construcción. **No es
   autoridad**: es contexto útil antes de la primera spec de cada problema, y queda por debajo de
   todo lo anterior. Cada hipótesis muere cuando la feature que la toca tiene su `plan.md`.

**1 y 2 están siempre en contexto** — 1 porque este archivo la importa, 2 porque es este archivo.
Los demás se abren cuando el trabajo lo pide: leer el documento correcto en el momento correcto es
parte del trabajo, no un extra.

## Reglas del dominio (INVIOLABLES)

Son los artículos **I, II, III y VII** de la constitución, que está importada arriba y por lo tanto
**ya en contexto**. No se resumen acá: un resumen de la autoridad número uno es una segunda fuente
que deriva, y ya derivó una vez.

1. **SIGProv es solo lectura** y no se le escribe (Art. I).
2. **La extracción es automatización de navegador, no un cliente HTTP**: sus endpoints JSON
   internos **no se usan** (Art. I).
3. **Nada se descarta**: lo ilegible va a cuarentena en `staging` y genera una fila en
   `operations.exception` (Art. II).
4. **El flujo va en un solo sentido**, `raw` → `staging` → `core`, y `raw` es inmutable (Art. III).
5. **Las credenciales del portal viven sólo en el entorno** (Art. VII).

El enunciado completo de cada una, con su *por qué es no negociable*, está en `CONSTITUTION.md`.

## Fronteras entre módulos (ESTRICTO)

La modularidad del monolito se sostiene con una sola regla, y se verifica en cada review:

> **Un módulo nunca importa de otro, se comunica con otro exclusivamente a través de eventos.**

- ❌ `from app.modules.suppliers.service import SupplierService`
- ❌ `from app.modules.suppliers.repository import SupplierRepository`
- ❌ `from app.modules.suppliers.models import Supplier`
- ✅ `from app.shared.events import events, InvoiceRegistered`

Todo lo que hay dentro de un módulo es privado: `service.py`, `schemas.py`, `repository.py`,
`models.py`, `tasks.py`. La única excepción es `dependencies.py`, porque autorizar una request es
una pregunta síncrona que un evento no llega a contestar.

Esa excepción está fijada **por nombre de archivo** en
`backend/tests/architecture/test_module_boundaries.py`. Si este documento y ese test alguna vez se
contradicen, **gana el test**: un test rompe el build, un documento no.

Cómo se diseña un flujo por eventos —dónde vive el catálogo, qué transacción comparten los
handlers, cómo lee un módulo lo que es de otro— está en `ARCHITECTURE.md` → *Fronteras entre
módulos*.

### Dónde va el código

El mapa de los módulos de dominio, la estructura del repositorio y la anatomía de un
módulo viven en **`ARCHITECTURE.md`**: son su materia, y no se duplican acá. Lo que sí es una
decisión que se toma todo el tiempo, y por eso está siempre en contexto:

- pertenece a una capacidad del negocio → el módulo de esa capacidad
- es transversal y sin dominio (normalización de texto, dinero, paginación, errores) → `shared/`
- es composición HTTP (registro de routers, handlers de error) → `main.py`

Un módulo nuevo se justifica cuando aparece una **capacidad del negocio con lenguaje propio**,
no cuando un módulo existente acumula archivos (`ARCHITECTURE.md` → *Agregar un módulo o una
feature*).

### Estructura de las specs

Las specs viven en un **árbol único numerado**: `docs/specs/<NNN-feature>/`.

- **Numeración**: secuencia `NNN-` única y correlativa.

- **Nombre**: `<NNN-feature>` = `NNN-<short-name>` en kebab-case, **en inglés** (`001-portal-extraction`). Es un
  identificador técnico y la rama lo hereda tal cual. El **contenido** de los artefactos sigue
  yendo en español.

- **Archivos**: `spec.md` (cara al cliente) más `plan.md`, `tasks.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `checklists/`, `diagrams/`.

- **Traspaso**: `plan.md` lleva una sección obligatoria de **Contexto de traspaso** que leen el Developer, el Tester y el Code-Reviewer.

- **Diagramas**: cada feature lleva sus diagramas de flujo en Mermaid (`diagrams/`) — por actor, cross-actor y máquina de estados — derivados de la spec, validados en CI y exportables para compartir con el cliente. Convención: `docs/specs/DIAGRAMS.md`.

- **Archivo**: al entregarse, la carpeta pasa a `docs/specs/archive/`, y su número **no se reutiliza nunca**.

- Detalle: `docs/specs/README.md`.

## Roles de agente (OBLIGATORIO)

Este repositorio define roles explícitos en `agents/roles/`.

### Rol por defecto

Si el usuario no especifica un rol, el agente DEBE asumir:
- **Lead**

Definido como alias en `agents/roles/default.md`. Consecuencia deliberada: por defecto el
agente **orquesta y delega**, no escribe código. Para trabajar directamente sobre el código hay
que asumir un rol que lo permita.

### Selección automática de rol

El agente DEBE disparar agentes en segundo plano con el rol que corresponda según la tarea y supervisarlos:

- Orquestar el trabajo, delegar a subagentes, verificar consistencia spec ↔ plan ↔ tasks y correspondencia código ↔ spec → `Lead`.

- Crear o actualizar la definición funcional de la solución (requerimientos, alcance, user stories, diagramas) →  `Solution-Designer`.

- Arquitectura de backend, fronteras entre módulos o decisiones de FastAPI → `Backend-Architect`
- Arquitectura de frontend o decisiones de Next.js/React → `Frontend-Architect`
- Implementar features nuevas o cambios del cliente → `Developer`
- Diseñar o extender la suite de tests, cobertura, casos borde. Ejecutar los tests y realizar pruebas manuales con Playwright → `Tester`
- Revisar cambios / review de PR / quality gate → `Code-Reviewer`
- Commitear/pushear un cambio testeado y abrir un PR, preparar un deploy → `Release-Manager`

### Cadena de un feature

Los roles no son intercambiables: tienen un orden, y dos de sus pasos son gates.

```
                    ┌─────────────── Lead ───────────────┐
                    │   orquesta · delega · /analyze      │
                    └─────────────────┬──────────────────┘
  docs/PROJECT_BRIEF.md  ─── el alcance acordado con el cliente
  Solution-Designer   ──►  /specify · /clarify · /diagram   →  spec.md
                           ✍️  GATE: firma del cliente (/approve-spec)
  Architect (back/front) ──►  /plan · /tasks   →  plan.md (Constitution Check) · tasks.md
  Developer           ──►  /implement + tests unitarios de su lógica
  Tester              ──►  integración · E2E · casos borde · cobertura
  Lead                ──►  /converge: ¿el código es lo que se firmó?
  Code-Reviewer       ──►  🚦 GATE de calidad (/review-feature)
  Release-Manager     ──►  /ship → PR contra `main`, y la spec pasa a archive/
```

`/converge` y `/review-feature` no se solapan: **`review_feature` pregunta "¿está bien escrito?";
`converge` pregunta "¿es lo que se acordó?"**. Un cambio puede pasar el review con nota perfecta y
no implementar lo que la spec prometía — o cumplir la spec al pie de la letra y violar la
arquitectura.

Dos inversiones que son errores, no variantes:

- El **Solution-Designer va antes que el arquitecto**. La spec es el input del `/plan`; al revés se
  estaría resolviendo técnicamente un alcance que el cliente no firmó, y el gate deja de serlo.

- El **Tester va antes que el Code-Reviewer**. El reviewer verifica que existan tests: si el tester
  corre después, el gate aprueba código sin cobertura y los hallazgos llegan tarde.

`debug` es transversal: se dispara en cualquier paso, bajo el rol del área afectada.

### Qué comandos existen hoy

| Paso de la cadena | Comandos |
|---|---|
| Definir el alcance | `/specify` · `/clarify` · `/diagram` · `/approve-spec` |
| Planificar | `/plan` · `/tasks` · `/analyze` |
| Construir | `/implement` |
| Cerrar | `/converge` · `/review-feature` · `/ship` |
| Transversales | `/status` (radiografía del proyecto) · `/portal` (el origen SIGProv) |

**Ningún comando contiene su procedimiento.** Los trece son punteros de una línea a una skill de
`agents/skills/`, que es donde vive el procedimiento y que **cualquiera puede seguir a mano**.

Está hecho así a propósito: un procedimiento del proyecto no le pertenece a la herramienta con la
que se ejecuta. Integrar otro proveedor de IA es escribir trece punteros en su formato, no
reescribir trece procedimientos. Es la misma razón por la que este archivo vive en la raíz y
`.claude/CLAUDE.md` sólo lo importa.

Consecuencia práctica: **una regla nueva va en la skill, nunca en el comando.**

### Regla de invocación del rol

Antes de planificar o editar código, el agente DEBE:

1. Seleccionar el rol (por defecto o auto-seleccionado),
2. Seguir las prioridades y restricciones del rol,
3. Aplicar el Protocolo de Skills y sus triggers.

## Gestión de dependencias (ESTRICTO)

Backend con **uv**, frontend con **npm**, sin excepciones. Las reglas y sus comandos están en `CONVENTIONS.md` → `DEP-01` a `DEP-04`. Violarlas es **Blocker** en el review.

## Skills (OBLIGATORIO)

Las skills están definidas en `agents/skills/` y se identifican por **nombre**, no por orden
numérico. Para cualquier tarea, el agente DEBE:

1. Identificar la categoría de la tarea.
2. Verificar si existe una skill que aplique — el mapa de abajo es la fuente.
3. Seguir los pasos de la skill en orden.
4. Ejecutar la "Validación" de la skill antes de declararla completa.
5. Desviarse sólo si se lo indican explícitamente.

Si aplican varias skills, la prioridad es **safety/debug → fronteras → implementación**.

**Enforcement:** cuando se dispara una skill, sus pasos DEBEN seguirse en orden y su validación
DEBE completarse antes de declarar el éxito. Si un paso no se puede ejecutar, el agente se
detiene y pide aclaración. Saltearse una skill existente se considera un error.

### Mapa de triggers

Toda skill tiene un rol dueño. Una skill sin dueño está incompleta y no se puede disparar.

| Situación | Skill | Comando | Rol dueño |
|---|---|---|---|
| Definir la spec funcional / alcance / historias de una feature | `specify` | `/specify` | Solution-Designer |
| Resolver las ambigüedades de una spec antes de la firma | `clarify` | `/clarify` | Solution-Designer |
| Generar/actualizar los diagramas de flujo de una feature | `add_diagrams` | `/diagram` | Solution-Designer |
| Registrar la firma del cliente sobre la spec (gate) | `approve_spec` | `/approve-spec` | Solution-Designer |
| Planificar la implementación | `plan` | `/plan` | Backend-Architect · Frontend-Architect |
| Desglosar el plan en tareas | `tasks` | `/tasks` | Backend-Architect · Frontend-Architect |
| Verificar consistencia spec ↔ plan ↔ tasks | `analyze` | `/analyze` | Lead |
| Ejecutar las tareas de una feature | `implement` | `/implement` | Developer |
| Agregar una feature de backend o un módulo nuevo | `add_backend_feature` | — | Developer |
| Agregar una feature de frontend | `add_frontend_feature` | — | Developer |
| Agregar una feature full-stack | `add_feature` | — | Developer |
| Agregar una integración con un servicio externo | `add_integration` | — | Developer |
| Agregar trabajo en background | `add_celery_task` | — | Developer |
| Modificar modelos de base de datos | `add_database_migration` | — | Developer |
| Agregar o extender tests | `add_tests` | — | Tester |
| Verificar que el código corresponde a lo firmado | `converge` | `/converge` | Lead |
| Revisar cambios / PR / quality gate | `review_feature` | `/review-feature` | Code-Reviewer |
| Commitear/pushear una feature testeada, abrir PR | `ship_changes` | `/ship` | Release-Manager |
| Preparar un deploy o una release | `deploy` | — | Release-Manager |
| Ver el estado real del proyecto | `project_status` | `/status` | Lead |
| Verificar la estructura de una sección de SIGProv | `inspect_portal` | `/portal` | Developer |
| Agregar o actualizar skills/convenciones | `add_or_update_skill` | — | Backend-Architect |
| Diagnosticar y corregir un fallo (transversal, en cualquier paso) | `debug` | — | el rol del área afectada |

Una skill sin comando se sigue a mano: son procedimientos, no atajos de una herramienta.

Las skills deben seguir la convención documentada en `agents/skills/README.md`.

## Reglas de código (ESTRICTO)

Las convenciones de código viven en **`CONVENTIONS.md`**, que es su fuente única: ahí está cada
regla con su identificador estable (`PY-04`, `TS-02`, `ERR-01`, …), su severidad y el comando que
la verifica. Si una convención no está ahí, no es una convención del proyecto.

Lo que gobierna este documento es el enforcement:
- Violar una convención marcada como **Blocker** frena el review: se arregla o el changeset no pasa
  (`agents/skills/review_feature.md`).
- Siete convenciones no dependen de que alguien las lea, porque las verifica un test que rompe el
  build: `GEN-02` y `GEN-03` (fronteras entre módulos), `GEN-09` (un handler que falla no se
  silencia), `PY-09` (autorización de rutas), `TEST-05` (cobertura) y `UI-01` y `UI-02` (ningún
  color escrito a mano en la UI). Las cuatro primeras las frena el pre-commit; la cobertura, las
  dos del diseño y la suite completa, el CI. El resto depende del `Developer` que las aplica y del
  `Code-Reviewer` que las recorre.
- Las reglas del dominio (INVIOLABLES) de más arriba y las fronteras entre módulos siguen siendo de
  este documento y de `ARCHITECTURE.md`; `CONVENTIONS.md` las referencia, no las reemplaza.

## Flujo de Git (ESTRICTO)

`main` es la rama estable y desplegable. Rama por feature (`feat/<NNN-feature>`), quality gate
antes del merge, y el PR lo abre `/ship`. **NUNCA commitear directo a `main`.**

La convención de ramas y el formato de los mensajes están en `CONVENTIONS.md` → `GIT-01` a `GIT-04`.

## Definition of Done

- El código compila y pasa los chequeos de tipos (`PY-10`, `TS-01`).
- Existen tests unitarios de la lógica pura y de integración de endpoints y base de datos
  (`TEST-01`, `TEST-02`), y la cobertura no bajó (`TEST-05`).
- Los parsers del portal tienen tests contra HTML fijado, nunca contra el portal en vivo (`TEST-03`).
- No hay violaciones de las fronteras entre módulos: ningún import cruzado (`GEN-02`), `shared/`
  no importa de `modules/` (`GEN-03`), no hay ciclos de eventos (`GEN-05`), y los eventos nuevos
  respetan el catálogo y la transacción del publicador (`GEN-08`, `GEN-09`).
- Los modelos de base de datos están sincronizados con las tablas (`DB-01`).
- **Toda pantalla nueva o tocada aplica el sistema de diseño** (`UI-*`): los colores salen de los
  tokens y no se escriben a mano (`UI-01`, `UI-02`, verificadas por test), los estados usan la
  píldora (`UI-03`), la plata va en mono tabular (`UI-04`) y hay una sola acción de acento por
  pantalla (`UI-05`).
- Las tasks nuevas son idempotentes (`PY-07`, `TEST-04`).
- Ninguna convención de `CONVENTIONS.md` marcada como **Blocker** quedó violada.
- `plan.md` tiene su sección de **Contexto de traspaso** y sigue siendo verdad.
- La documentación está actualizada si hacía falta.

## Comandos

La puesta en marcha y los comandos de backend, frontend e infraestructura están en `README.md`,
y el `Makefile` es su fuente ejecutable (`make help`). No se duplican acá.

Los comandos que **verifican una convención** viven en `CONVENTIONS.md`, junto a la convención
que verifican.

## Idioma (Artículo VIII)

- **El contenido de la documentación va en español**: gobernanza, roles, skills y **todos** los
  artefactos de spec (`spec.md`, `plan.md`, `tasks.md`, `research.md`, `data-model.md`,
  `contracts/`, `checklists/`, `diagrams/`). La única excepción son los **nombres**: la carpeta de
  una spec y su rama son identificadores técnicos y van en inglés (`001-portal-extraction`).
- **Código en inglés**: nombres, comentarios, docstrings y mensajes de commit. Excepción: los
  strings que ve el usuario en la UI van en español.
- **Las respuestas en el chat, en español.**

`spec.md` es además el artefacto **cara al cliente**: no lleva decisiones técnicas —nada de
stack, APIs, schemas ni rutas de archivo—. Eso va en `plan.md`.
