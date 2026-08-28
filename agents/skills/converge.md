# Skill — Converger el código con lo acordado

Tags: [specs] [review] [calidad]

## Objetivo
Verificar que el código ya implementado de una feature **corresponde a lo que el cliente firmó**:
que cada requisito de `spec.md` tenga implementación real y verificable, que no exista
implementación que ningún requisito pida, y que `plan.md`, `tasks.md` y `diagrams/` sigan
describiendo el producto que efectivamente existe.

> **`review_feature` pregunta "¿está bien escrito?". `converge` pregunta "¿es lo que se acordó?"**

Son dos gates distintos y ninguno cubre al otro. Un changeset puede pasar el review con nota
perfecta y no implementar lo que la spec prometía; y puede cumplir la spec al pie de la letra
mientras rompe una frontera entre módulos. `converge` no juzga la calidad del código: no mira
tipado, ni nombres, ni cobertura. Mira **correspondencia**.

Dónde encaja respecto de las otras verificaciones:

| Momento | Skill | Compara |
|---|---|---|
| Antes de implementar | `/analyze` | documento contra documento: spec ↔ plan ↔ tasks |
| Después de implementar y testear | `converge` | **código contra lo acordado**: spec, plan, tasks, diagramas |
| Antes del merge | `review_feature` | código contra los estándares y las fronteras |

El hueco que cierra es concreto: hasta acá nadie verificaba que el código terminado hiciera lo
que el cliente firmó.

## Cuándo usarla
- Después del `Tester` y antes del `Code-Reviewer` (`AGENTS.md` → "Cadena de un feature"), sobre
  toda feature que llegó al final de `/implement`.
- Cuando la implementación se repartió entre varias sesiones o varios agentes y nadie tuvo la
  feature entera a la vista.
- Cuando se reabre una feature ya entregada para extenderla: primero se verifica que lo que hay
  todavía corresponda a su spec.
- Antes de que `/ship` mueva la spec a `docs/specs/archive/`: lo que se archiva tiene que ser
  verdad.

Cuándo **no** usarla:
- Antes de implementar: ahí va `/analyze`, que compara documentos entre sí.
- Para revisar calidad, fronteras o tipado: eso es `review_feature`.

**Rol dueño: `Lead`** — el mismo que posee `/analyze`, y por la misma razón: es el único que ve
todos los artefactos y no escribe código, así que puede juzgar correspondencia sin haber sido
parte de la implementación.

## Precondiciones
- Existen `docs/specs/<NNN-feature>/spec.md`, `plan.md` y `tasks.md`.
- `spec.md` está en estado `Aprobado` (firma del cliente registrada por `/approve-spec`).
- La implementación se declara terminada: `tasks.md` tiene tareas marcadas como completas.
- El `Tester` ya corrió y la suite pasa: `cd backend && uv run pytest`.
- El agente opera como `Lead` (`agents/roles/lead.md`).

## Reglas (ESTRICTO)
- **Se verifica contra el código, no contra los documentos.** Un requisito se marca implementado
  sólo con evidencia localizable: archivo y símbolo
  (`backend/app/modules/<module>/service.py::<method>`), ruta registrada en `backend/app/main.py`,
  página bajo `frontend/app/(private)/<modulo>/`, o test que lo ejercita. "Debería estar en el
  servicio" no es evidencia.
- **Un requisito sin implementar es un hallazgo**, no una omisión aceptable ni una tarea futura.
- **El alcance no pedido es un hallazgo de la misma gravedad.** Se detecta menos porque nada
  falla: es funcionalidad que el cliente no pidió ni firmó, y que el equipo va a mantener para
  siempre.
- **Esta skill no arregla nada.** No toca código (`backend/`, `frontend/`, `backend/tests/`) ni
  los artefactos de otros roles (`spec.md`, `plan.md`, `tasks.md`, `diagrams/`). Lo único que el
  `Lead` escribe es el informe, dentro de `docs/specs/<NNN-feature>/`; cada hallazgo se devuelve
  con su rol dueño (`agents/roles/lead.md` → "Autoridad").
- **La deriva mayor bloquea el gate**: la feature no pasa al `Code-Reviewer` hasta resolverse.
- **La decisión entre implementar lo que falta y renegociar la spec es del humano.** El agente
  presenta las dos opciones con su costo; no elige.

## La regla que hace útil a esta skill

**No alcanza con leer los documentos.** Que `tasks.md` diga que algo está hecho es exactamente la
afirmación que hay que auditar. Cada requisito se busca en `backend/app/` y en `frontend/` —con
`grep` y abriendo los archivos—, teniendo en cuenta que la documentación está en español y el
código en inglés: hay que buscar por el término traducido (`supplier`, `invoice`,
`purchase_order`, `quarantine`).

## Pasos (ORDEN OBLIGATORIO)

### 1) Resolver la feature y el changeset
```bash
ls docs/specs/
ls docs/specs/<NNN-feature>/
git rev-parse --abbrev-ref HEAD          # esperado: feat/<NNN-feature>
git diff main...HEAD --name-only
```
Si la rama no sigue la convención, o el repositorio todavía no tiene historia de git, el
changeset se arma con los archivos que nombran `plan.md` y `tasks.md`, y se completa con las
búsquedas del paso 3. Una feature ya entregada vive en `docs/specs/archive/<NNN-feature>/`.

---

### 2) Extraer el inventario de lo acordado
Antes de mirar una línea de código, armar la lista de lo que se prometió:

```bash
grep -nE "(RF|CA|US)[- ]?[0-9]+" docs/specs/<NNN-feature>/spec.md
sed -n '/Contexto de traspaso/,$p' docs/specs/<NNN-feature>/plan.md
grep -nE "^\s*-\s*\[[ xX]\]" docs/specs/<NNN-feature>/tasks.md
ls docs/specs/<NNN-feature>/diagrams/
```

- De `spec.md`: requisitos funcionales y criterios de aceptación, con su identificador.
- De `plan.md`: el enfoque técnico decidido y la sección **Contexto de traspaso** (decisiones y
  su porqué, alternativas descartadas).
- De `tasks.md`: las tareas y su estado declarado.
- De `diagrams/`: actores, pasos del flujo y estados de la entidad.

Si un requisito está redactado de forma que no se puede contrastar contra código (no dice qué
tiene que pasar), es un hallazgo del `Solution-Designer` — no una excusa para saltearlo.

---

### 3) Inventariar lo que el código realmente hace
```bash
ls backend/app/modules/
grep -rn "include_router" backend/app/main.py
grep -rnE "@router\.(get|post|put|patch|delete)" backend/app/modules/*/routes.py
grep -rn "def " backend/app/modules/<module>/service.py
ls backend/alembic/versions/
ls "frontend/app/(private)" frontend/components frontend/lib
```
La lista de endpoints, páginas, servicios, tasks y migraciones que existen es el otro extremo de
la comparación. Sin ella no se puede hacer el paso 5.

---

### 4) Cobertura de requisitos (spec → código)
Recorrer el inventario del paso 2 **de a un requisito**, y buscar su implementación. Como la
documentación va en español y el código en inglés, buscar por el término de dominio traducido
(`supplier`, `invoice`, `purchase_order`, `quarantine`, …):

```bash
grep -rni "<termino_del_dominio>" backend/app --include="*.py"
grep -rni "<termino_del_dominio>" frontend/app frontend/components frontend/lib --include="*.ts*"
grep -rni "<termino_del_dominio>" backend/tests
```

Volcarlo en la tabla de trazabilidad del informe, con un estado por requisito:

| Estado | Significado |
|---|---|
| Implementado | Hay código que lo cumple y evidencia que lo señala |
| Parcial | Existe el camino feliz, falta una condición, un rol o un caso de error que la spec pide |
| Ausente | No hay código que lo implemente |

`Parcial` y `Ausente` son hallazgos de tipo **Requisito sin implementar**.

---

### 5) Alcance no pedido (código → spec)
Recorrer el inventario del paso 3 en sentido inverso: por cada endpoint, página, tabla, task o
parámetro configurable, preguntar **qué requisito lo pide**. Si no hay ninguno, distinguir:

- **Andamiaje técnico que `plan.md` justifica** (repositorio base, migración de soporte, cliente
  del portal): no es hallazgo, es implementación de una decisión documentada.
- **Capacidad de negocio visible para el usuario que ningún requisito pide**: hallazgo de tipo
  **Alcance no pedido**. Es alcance que el cliente no firmó y que hay que mantener para siempre.

Si el andamiaje no está en el plan, es deriva del plan (paso 7), no alcance no pedido.

---

### 6) Tareas declaradas completas que no lo están
Por cada tarea marcada `[x]` en `tasks.md`, abrir el archivo que la tarea nombra y verificar que
exista lo que dice que hizo. Incluye los tests que la tarea promete:

```bash
grep -rn "<nombre_del_simbolo>" backend/app backend/tests frontend
```
Una tarea marcada completa cuyo código no aparece es un hallazgo de tipo **Tarea sin respaldo**,
y vuelve al `Developer`.

---

### 7) Deriva respecto del plan
Comparar las decisiones de `plan.md` (y de su "Contexto de traspaso") contra lo que el código
hizo: módulo elegido, forma de la frontera entre módulos, esquema de base de datos usado,
estrategia de trabajo en background, y los contratos de `contracts/` contra las rutas y schemas
reales.

Una divergencia no es necesariamente un error — pero el plan tiene que reflejar la realidad o
deja de servirle al próximo que lo lea. Clasificar cada una:
- el código está bien y el plan quedó viejo → actualizar `plan.md`, vuelve al arquitecto
  (`Backend-Architect` / `Frontend-Architect`);
- el código se fue del plan sin motivo registrado → vuelve al `Developer`.

---

### 8) Los diagramas siguen siendo verdad
```bash
bash scripts/diagrams/validate.sh docs/specs/<NNN-feature>/diagrams/
```
Que un diagrama compile no significa que sea verdad. Recorrer `flujo-general.mmd` paso por paso
contra el código (¿ese paso existe? ¿en ese orden? ¿lo hace ese actor?) y
`estados-<entidad>.mmd` contra las transiciones que el servicio realmente permite. Un diagrama
que describe un flujo que el código ya no hace es un hallazgo de tipo **Diagrama desactualizado**
y vuelve al `Solution-Designer` (`/diagram`, convención en `docs/specs/DIAGRAMS.md`).

---

### 9) Contradicción con una regla del dominio
Releer las cinco reglas inviolables de `AGENTS.md` → "Reglas del dominio (INVIOLABLES)" y
verificar que lo que la feature promete no obligue a violarlas:

1. SIGProv es solo lectura.
2. La extracción es automatización de navegador, no un cliente HTTP.
3. Nada se descarta: lo ilegible va a cuarentena en `staging` y a `operations.exception`.
4. El flujo va en un solo sentido `raw` → `staging` → `core`, y `raw` nunca se sobrescribe.
5. Las credenciales del portal viven sólo en el entorno.

```bash
grep -rnE "httpx|requests\." backend/app/modules/portal
grep -rniE "quarantine|exception" backend/app/modules/ingestion
grep -rniE "update .*\braw\b|delete .*\braw\b" backend/app --include="*.py"
```

El ángulo acá es distinto del de `review_feature`: no se busca la violación en el código —esa la
bloquea el reviewer— sino que **lo prometido** en `spec.md` o `plan.md` no se pueda cumplir sin
violarla. Si un requisito firmado sólo es satisfacible rompiendo una regla inviolable, el
hallazgo es de la spec y sube al humano: la regla no se negocia, el requisito sí.

---

### 10) Emitir el veredicto
Escribir el informe con el formato de abajo. Un converge sin veredicto explícito no está
completo, y el `Code-Reviewer` no puede arrancar sin él.

## Validación
- [ ] Todo requisito de `spec.md` aparece en la tabla de trazabilidad con su estado. Ninguno quedó sin fila.
- [ ] Ninguna fila dice `Implementado` sin evidencia localizable (archivo + símbolo, ruta, página o test).
- [ ] Se recorrió el sentido inverso: cada endpoint, página, tabla y task tiene un requisito que lo pide, o quedó reportado.
- [ ] Cada tarea marcada `[x]` en `tasks.md` se verificó contra el archivo que nombra.
- [ ] Las decisiones de `plan.md` (incluido el "Contexto de traspaso") se compararon contra el código.
- [ ] `bash scripts/diagrams/validate.sh docs/specs/<NNN-feature>/diagrams/` pasa, y los diagramas se leyeron contra el código.
- [ ] Las cinco reglas del dominio se contrastaron contra lo que la feature promete.
- [ ] Hay un veredicto escrito, y cada hallazgo tiene tipo, rol dueño y acción concreta.
- [ ] No se modificó código ni artefactos de otros roles durante la corrida: lo único escrito es el informe.

## Formato de salida (informe de convergencia)

Un veredicto, uno solo, y explícito:

- **Converge** — todo requisito tiene implementación con evidencia, no hay alcance sin
  requisito, las tareas completas están respaldadas, y plan y diagramas describen lo que el
  código hace. Pasa al `Code-Reviewer`.
- **Deriva menor** — el código y la spec describen el mismo producto, pero algún artefacto
  quedó desactualizado (el plan documenta un enfoque que el código cambió con motivo, un
  diagrama muestra un paso que se movió, una tarea quedó sin marcar). **No bloquea el gate**: se
  actualiza el artefacto desactualizado, con su rol dueño, y la feature sigue.
- **Deriva mayor** — el código y la spec **no describen el mismo producto**: hay requisitos
  firmados sin implementar, o capacidades implementadas que nadie pidió. **Bloquea el gate**: la
  feature no pasa al `Code-Reviewer`.

Ante una **deriva mayor** hay dos salidas, y la salida por defecto **no** es "arreglar el código":

1. **Implementar lo que falta** (o quitar lo que sobra) → vuelve al `Developer`, y después otra
   vez al `Tester`.
2. **Corregir la spec** para que refleje lo que de verdad se acordó → vuelve al
   `Solution-Designer`, y **el cliente la vuelve a firmar** con `/approve-spec`: el gate de la
   firma se reabre.

A veces la spec estaba mal y lo correcto es renegociarla. **Esa decisión es del humano, no del
agente**: el agente presenta las dos opciones con lo que cuesta cada una y espera. Elegir por el
cliente es exactamente lo que el gate de firma existe para impedir.

### Tabla de trazabilidad
| Requisito | Qué promete la spec | Dónde está implementado | Evidencia | Estado |
|---|---|---|---|---|

### Hallazgos
| # | Tipo | Qué dice el artefacto | Qué hace el código | Rol dueño | Acción |
|---|---|---|---|---|---|

Tipos de hallazgo: **Requisito sin implementar** · **Alcance no pedido** · **Tarea sin respaldo**
· **Deriva del plan** · **Diagrama desactualizado** · **Contradicción con una regla del dominio**.

## Errores comunes (evitar)

### 1) Leer documentos en lugar de verificar código
Confirmar que `tasks.md` dice que la tarea está hecha no es verificar nada: es repetir la
afirmación que hay que auditar. Toda fila `Implementado` sale de un `grep` o de abrir el archivo.

### 2) Aceptar el nombre como evidencia
Que exista `SupplierService.resolve_alias` no prueba que resuelva alias. Si el requisito define
un comportamiento, la evidencia es el cuerpo del método o el test que lo ejercita.

### 3) Tratar el alcance no pedido como un extra
"Ya que estábamos, agregamos el filtro por fecha" es alcance que el cliente no pidió, no firmó y
va a mantener para siempre. Se reporta igual que un requisito faltante.

### 4) Hacer el trabajo del `review_feature`
Tipado, fronteras, cobertura y formato no son de esta skill. Si aparece una violación de
frontera, se anota en una línea y se escala al `Code-Reviewer`; no se convierte el converge en
un review.

### 5) Arreglar durante el converge
El `Lead` no edita código ni los artefactos de otros roles. Arreglar sobre la marcha destruye el
hallazgo: nadie vuelve a saber que la spec y el código se habían separado.

### 6) Degradar una deriva mayor para no bloquear
Un requisito firmado sin implementar es deriva mayor aunque sea chico y aunque la fecha apriete.
El estado del gate no se negocia contra el calendario.

### 7) Decidir por el cliente
Concluir "la spec pedía de más, la sacamos" es reescribir el alcance firmado sin el cliente. Se
presentan las dos opciones y decide el humano.

## Troubleshooting

### `spec.md` no tiene requisitos identificables
Sin inventario no hay converge. No inventar los requisitos faltantes: se reporta como hallazgo
del `Solution-Designer` y se frena (`AGENTS.md` → "Enforcement").

### No existe `plan.md` o `tasks.md`
La cadena se salteó un paso. Se detiene el converge y se escala al humano: no se puede verificar
correspondencia contra artefactos que no se escribieron.

### No se encuentra la implementación de un requisito
Antes de declararlo `Ausente`, buscar por el término de dominio **en inglés** (`supplier`,
`invoice`, `purchase_order`, `quarantine`) en `backend/app/`, `frontend/` y `backend/tests/`.
La documentación está en español y el código no.

### La rama no dice cuál es la feature
Si `git rev-parse --abbrev-ref HEAD` no devuelve `feat/<NNN-feature>` —o no hay repositorio git—,
pedir la feature como argumento y listar `docs/specs/`. No adivinar.

### `scripts/diagrams/validate.sh` no encuentra mermaid-cli
La resolución es `$MMDC` → `mmdc` en el PATH → `npx -y @mermaid-js/mermaid-cli`
(`docs/specs/DIAGRAMS.md`). Si no se puede validar, se reporta como no verificado en el informe;
no se da por bueno.
