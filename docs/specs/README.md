# `docs/specs/` — Specs por feature

Cada feature de la Plataforma Cordillera vive acá, en una carpeta propia dentro de un
**árbol único numerado**. Este repositorio es un solo producto hecho a medida para un solo cliente.

```
docs/specs/
├── README.md
├── DIAGRAMS.md
├── 001-<short-name>/        ← activa: en definición, planificada o en construcción
├── 002-<short-name>/
└── archive/                 ← entregadas: mergeadas a main y desplegadas
    └── 000-<short-name>/
```

## Convenciones

- **Numeración**: secuencia `NNN-` única y correlativa (`001-`, `002-`, …). El número se
  toma como el siguiente al mayor **entre las activas y las archivadas**, y una vez usado
  no se reutiliza nunca: la rama y el PR de esa feature lo referencian para siempre.
- **Nombre**: `NNN-<short-name>` en kebab-case, por ejemplo `001-portal-extraction`.
  El `<short-name>` va **en inglés**, dos o tres palabras, sin tildes ni `ñ`. Es un identificador
  técnico, no prosa: la rama lo hereda tal cual (`feat/001-portal-extraction`) y de ahí viaja por
  git, CI y URLs de PR, donde todo el resto ya está en inglés (`GIT-03`).
  `001-portal-extraction`, no `001-extraccion-portal`.

  **El nombre es lo único en inglés.** El contenido de `spec.md` y del resto de los artefactos va
  en español, incluido el título del documento: el cliente lee la spec, no la ruta del archivo.
- **Idioma**: **todo en español**, incluidos los artefactos internos.

## Archivos de una feature

| Archivo | Qué es | Quién lo lee |
|---|---|---|
| `spec.md` | Definición funcional: qué hace la feature y para quién | **El cliente** (revisión + firma) |
| `plan.md` | Plan técnico: stack, decisiones, estructura | El equipo |
| `tasks.md` | Tareas ejecutables, cada una mapeada a una skill `add_*` | El equipo |
| `research.md` | Investigación previa y alternativas descartadas | El equipo |
| `data-model.md` | Entidades, campos, relaciones y máquinas de estado | El equipo |
| `contracts/` | Contratos de API (OpenAPI, eventos) | El equipo |
| `quickstart.md` | Cómo probar la feature | El equipo |
| `checklists/` | Checklists de validación | El equipo |
| `diagrams/` | Diagramas de flujo en Mermaid (ver `DIAGRAMS.md`) | Cliente y equipo |

**`spec.md` es el único artefacto cara al cliente.** No lleva decisiones técnicas: nada de
stack, endpoints, schemas ni rutas de archivo. Todo eso va en `plan.md`.

## Plantillas

Los tres artefactos que se escriben a mano tienen plantilla propia, en español y calzadas con los
gates de este proyecto:

| Plantilla | Para | Se completa con |
|---|---|---|
| `spec.template.md` | `spec.md` — cara al cliente | `/specify`, después `/clarify` |
| `plan.template.md` | `plan.md` — técnico | `/plan` |
| `tasks.template.md` | `tasks.md` — ejecutable | `/tasks` |

Llevan sus instrucciones como comentarios HTML. **No salen en el PDF del cliente**: el exportador
los descarta antes de renderizar.

### Historias de usuario **y** requisitos EARS

`spec.md` lleva los dos formatos porque responden preguntas distintas, y con uno solo se pierde
algo:

- **Historias de usuario** — *para quién y por qué*. Priorizadas y **entregables de forma
  independiente**: si sólo se construye H1, el cliente ya tiene algo que usar. Ese corte es lo que
  permite entregar por partes.
- **Requisitos funcionales en EARS** — *qué exactamente*. Atómicos, sin ambigüedad, verificables.

Los cinco patrones EARS, en español:

| Cuándo aplica | Forma |
|---|---|
| Siempre | El sistema **debe** \<respuesta\>. |
| Ante un evento | **Cuando** \<disparador\>, el sistema **debe** \<respuesta\>. |
| Durante un estado | **Mientras** \<estado\>, el sistema **debe** \<respuesta\>. |
| Ante un problema | **Si** \<condición\>, **entonces** el sistema **debe** \<respuesta\>. |
| Condicional | **Donde** \<la opción esté activada\>, el sistema **debe** \<respuesta\>. |

Un requisito por línea, un solo *debe*, sin "y/o", sin adjetivos sin medida ("rápido",
"amigable"). **Si un requisito no se puede escribir así, todavía no está claro** — y eso es un
hallazgo, no un problema de redacción.

La cadena que esto habilita es la razón de usarlo: **cada `RF-xx` tiene un criterio de aceptación,
al menos una tarea que lo construye y al menos un test que lo verifica.** `tasks.md` lo hace
explícito en su tabla de cobertura, y es lo que `/converge` contrasta contra el código: un
requisito firmado sin test es alcance que nadie se comprometió a cumplir.

## Gate de aprobación

Ninguna feature pasa a `/plan` sin la firma del cliente sobre `spec.md`. El comando
`/approve-spec` registra la aprobación y deja el estado en `Aprobado`.

## Archivado

Una feature entregada —mergeada a `main` y desplegada— se mueve entera a
`docs/specs/archive/`. Lo hace el Release-Manager como último paso de `/ship`.

Sin esto, el árbol de specs crece sin límite y deja de distinguir lo que está por construirse de
lo que ya está en producción. Detalle en [`archive/README.md`](./archive/README.md).

## Contexto de traspaso

Cada rol de la cadena recibe el trabajo del anterior. Si ese traspaso es implícito —"leé el
plan y arreglate"— cada agente reconstruye el razonamiento desde cero, y las decisiones que
costaron pensarse se pierden entre un paso y el siguiente.

Por eso **`plan.md` lleva una sección obligatoria de traspaso**, que se escribe una vez y leen
todos los que vienen después:

```markdown
## Contexto de traspaso

### Decisiones tomadas
Qué se decidió y **por qué**. La razón importa más que la decisión: sin ella, el próximo que
lea esto no sabe si sigue siendo válida cuando cambien las circunstancias.

### Alternativas descartadas
Qué se evaluó y no se eligió, con el motivo. Evita que alguien vuelva a proponer lo mismo
dentro de tres semanas, y deja claro qué ya se pensó.

### Qué necesita saber el Tester
Los casos borde que el plan anticipa, los caminos de error que hay que ejercitar, y qué NO
hace falta testear porque quedó fuera de alcance.

### Qué necesita mirar el Reviewer
Dónde está el riesgo real de este cambio, y qué invariantes hay que verificar que no se
rompieron. No es la lista de archivos tocados: eso lo da el diff.
```

Esta sección la escribe el arquitecto durante `/plan`, y la leen el Developer, el Tester y el
Code-Reviewer. `/review-feature` verifica que exista y que siga siendo verdad.

## Ciclo de vida

```
/specify → spec.md
/clarify → preguntas que bajan el riesgo de la spec
/approve-spec → ✍️ firma del cliente (gate)
/plan → plan.md + research.md + data-model.md + contracts/
/tasks → tasks.md
/analyze → consistencia spec ↔ plan ↔ tasks
/implement → código
/converge → el código implementado corresponde a lo que se firmó
/review-feature → quality gate
/ship → commit + push + PR, y la spec se mueve a archive/
```

`/diagram` se puede correr después de `/specify` (flujos de negocio, para acompañar la firma)
y otra vez después de `/plan` (refrescar la máquina de estados).

## Cómo se resuelve la feature activa

Los comandos reciben la feature **por argumento** (`/plan 001-portal-extraction`). Sin argumento,
la infieren de la rama actual —convención `feat/<NNN-feature>`— y **dicen cuál infirieron** antes
de seguir. Si la rama no sigue la convención, listan `docs/specs/` y preguntan: ninguno adivina.

Es el mismo mecanismo en los trece comandos, sin estado compartido en disco que se pueda quedar
viejo apuntando a una feature que ya se archivó.

## El entregable para el cliente

El cliente no recibe el repositorio: recibe lo que tiene que leer y firmar.

```bash
make client-docs                                    # todo
make client-docs FEATURE=001-portal-extraction      # una feature
```

Deja en `dist/cliente/` (gitignoreado, se regenera):

```
dist/cliente/
├── Plataforma-Cordillera.pdf       # todo junto, con índice
├── brief/PROJECT_BRIEF.pdf
├── <NNN-feature>/
│   ├── spec.pdf                    # la spec con sus diagramas embebidos
│   └── diagramas/*.svg             # vectorial: se amplía sin pixelarse
└── entregadas/<NNN-feature>/       # las que ya están en producción
```

**Dos entregables, dos momentos.** El PDF **por spec** es la unidad que se firma: `/approve-spec`
es un gate sobre *una* spec, y un documento firmado tiene que ser autocontenido — no se firma la
página 47 de un dossier. El PDF **combinado** es el estado del proyecto, para una reunión de
avance o para poner a alguien al día. Nadie lo firma.

### Estado de cada spec

Cada documento lleva una chapa y un aviso, porque un borrador, un alcance aprobado y una
funcionalidad entregada no se leen igual:

| Dónde está | Chapa | Qué dice el aviso |
|---|---|---|
| `archive/` | **Implementada** (verde) | Funcionalidad entregada; describe lo acordado en su momento, no cómo funciona el sistema hoy |
| activa, `Estado: Aprobado` | **En desarrollo** (ámbar) | Alcance aprobado, en construcción: no es algo que ya se pueda usar |
| activa, cualquier otro caso | **Borrador** (gris) | En revisión, sin aprobar; el alcance puede cambiar |

La ubicación gana sobre el texto: una spec en `archive/` está entregada aunque su encabezado
siga diciendo `Aprobado`. Y en el árbol activo, **todo lo que no está explícitamente aprobado se
trata como borrador** — es la dirección segura para equivocarse, porque promete de menos.

En el combinado, **las implementadas van al final**, detrás de un separador: sólo se acumulan
con el tiempo, y quien abre el paquete quiere ver lo que se está construyendo ahora.

Cada PDF lleva portada, encabezado con el nombre de la feature y numeración de páginas. Los
diagramas van embebidos como vectores, así que también se pueden ampliar dentro del PDF; los
`.svg` sueltos acompañan para quien prefiera abrirlos en el navegador.

**Lo que se exporta es una lista blanca, no "todo menos lo excluido".** Sólo salen
`PROJECT_BRIEF.md`, los `spec.md` y los diagramas `flujo-*` y `estados-*`. Quedan afuera
`FDE_ASSESSMENT.md`, `plan.md`, `tasks.md`, `research.md`, `data-model.md`, `contracts/`,
`checklists/`, `quickstart.md` y los `sequence-*.mmd` internos: llevan stack, endpoints y rutas
de archivo. `FDE_ASSESSMENT.md` además son hipótesis sin acordar, y una hipótesis que el cliente
lee en un PDF con su logo deja de leerse como hipótesis.
Un artefacto nuevo queda **excluido por defecto** — para que llegue al cliente hay que agregarlo
a mano a `CLIENT_FACING_DOCS` en `scripts/docs/export_client.py`, que es una decisión sobre qué
se le pide leer al cliente, no una conveniencia.
