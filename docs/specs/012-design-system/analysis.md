# Sistema de diseño — Análisis de consistencia

**Feature:** 012-design-system · **Rol:** Lead · **Fecha:** 2026-08-31
**Veredicto de la primera corrida:** **Inconsistente** — ocho hallazgos.
**Veredicto tras las correcciones:** **Consistente** — se habilita `/implement`.

> **El piso se movió durante el análisis.** La primera corrida se hizo sobre el árbol de
> `feat/006-due-date-calendar`; en el medio entró el **PR #29** (`45f8942`, squash), que llevó a
> `main` la 006, la 011 y **los cimientos de la 012 juntos**. Todo lo que sigue está verificado
> contra ese `origin/main`, no contra los documentos. Dos hallazgos se cerraron solos y apareció
> uno nuevo.

## 1. Alcance

- Las **28 pantallas** de `app/(private)/` y las **4** de `app/(auth)/` tienen tarea, verificado
  archivo por archivo. Ninguna quedó afuera.
- Los **24 requisitos** tienen tarea, o un "ya cumplido" explícito **con test** (`RF-04`, `RF-20`).
- Las **seis historias** tienen tareas. Las 44 tareas están numeradas sin huecos y sus olas
  coinciden con las cinco del plan.
- **Una tarea sin requisito**, y era la única: la 8 (sacar la pantalla de bienvenida). Se cerró
  con el alta de `RF-24` — ver H-6.

## 2. Trazabilidad

Los 24 requisitos tienen sus 24 criterios de aceptación, sin huérfanos en ninguna dirección. La
tabla de cobertura de `tasks.md`, en cambio, dejó de coincidir con la columna "Cubre" de las
tareas — ver H-5.

## 3. Integridad de los documentos

- `spec.md` en **Estado: Aprobado**, firmada el 2026-08-31 y **enmendada dos veces el mismo día**,
  las dos con re-firma porque las dos cambian el alcance: el alta de `RF-24` y la excepción de la
  ventana de confirmación en `RF-11`/`RF-21`. Sin `[NECESITA ACLARACIÓN]` y sin decisiones
  técnicas.
- El **Constitution Check** recorre los nueve artículos y no pide excepciones. La advertencia de
  la fila IX —las devDependencies sin commitear— quedó vieja: ver H-2.
- El **Contexto de traspaso** está, dividido por rol, y es útil: le dice al Tester que `RF-16` y
  `RF-23` son opuestos y que hay que probar los dos con datos que den cero.

## 4. Coherencia con el proyecto

Cero cambios en `backend/`, así que las fronteras entre módulos no entran en juego. Las premisas
duras del plan, verificadas contra el código de hoy:

| Afirmación del plan | Verificado |
|---|---|
| El menú lista **quince** entradas y falta Ventas | Sí — `components/auth/Navigation.tsx`, quince `href` en cuatro grupos |
| La ruta `/ventas` no existe; sólo `/ventas/revision` | Sí |
| **Veintiocho** pantallas privadas y **cuatro** de sesión | Sí |
| Los dos hex sueltos de `globals.css` | Sí — `#8a8e93` en `:189`, `#c6c0b4` en `:243` |
| **Catorce** archivos importan `money`/`decimal`/`day` de `@/lib/format` | Sí |
| Cero `dark:` y cero `prefers-color-scheme` | Sí |
| `design-system.test.ts` tiene **tres** casos, y están verdes | Sí — `npm test`: 5 archivos, 35 casos |
| **Cero usos de `<Badge>` y de `<Notice>`** | **Ya no.** `components/purchases/CalendarGrid.tsx` usa los dos: los estrenó la 006 |
| **Cero `variant="brand"`** | **Ya no.** Hay uno, y cae en una ruta prohibida — ver H-8 |

## 5. Hallazgos

| # | Qué | Documento | Rol dueño | Estado |
|---|---|---|---|---|
| **H-1** | El gate de la tarea 6 no puede estar verde antes de la tarea 7 | `plan.md` · `tasks.md` | Frontend-Architect | ✅ Cerrado — lista sembrada |
| **H-2** | Los cimientos no estaban donde decían los documentos | `plan.md` · `tasks.md` | — | ✅ Cerrado por el PR #29 |
| **H-3** | Las cuentas del enforcement no cierran entre secciones del plan | `plan.md` | Frontend-Architect | ✅ Cerrado |
| **H-4** | "Las nueve rutas de la ola 3" son ocho | `tasks.md` | Frontend-Architect | ✅ Cerrado |
| **H-5** | La tabla de cobertura no coincide con la columna "Cubre" | `tasks.md` | Frontend-Architect | ✅ Cerrado y verificado |
| **H-6** | La tarea 8 sacaba una pantalla sin requisito que la respaldara | `spec.md` | Solution-Designer | ✅ Cerrado — alta de `RF-24`, firmada |
| **H-7** | `RF-08` tiene una válvula que puede dejarlo incumplido en parte | — | Lead → `/converge` | 🟡 A vigilar |
| **H-8** | Hay un botón naranja en `/calendario`, ya mergeado a `main` | `spec.md` · `plan.md` · `tasks.md` | Solution-Designer · Frontend-Architect | ✅ Cerrado — enmienda firmada y chequeo excluyente |

### H-1 · El gate de la tarea 6 no puede estar verde antes de la tarea 7

`tasks.md` dice: *"Los cinco chequeos estáticos tienen que estar verdes antes de que se toque la
primera pantalla"*. Tres no pueden estarlo hoy:

- **(c) `.pill*` fuera de `badge.tsx`** — lo escriben a mano `app/(private)/accesos/actividad/page.tsx`
  (nueve líneas) y `components/access/AccessTable.tsx` (cuatro). Se migran en la **tarea 37, ola 4**.
- **(d) la plata pasa por el envoltorio** — hoy la importan **catorce** archivos. El último se
  migra en la **tarea 41**, la anteúltima de todas.
- **(b) cero naranja en las rutas de decisión** — ver H-8.

La regla "el test antes que la migración" es correcta, pero **existir no es estar verde**: escrita
así, la tarea 6 bloquea las 38 tareas siguientes. Hay que elegir una: los chequeos nacen con lista
de excepciones que se achica ola por ola, o se escriben en la tarea 6 y se activan al cerrar la
ola 4.

### H-2 · Cerrado por el PR #29

El plan daba los cimientos por varados y sin commitear en `fix/extractions-were-wedged`, y la
tarea 1 corregía a medias. Hoy está todo en `main`: `vitest.config.ts`, `tests/setup.ts`,
`design-system.test.ts`, `docs/design/README.md`, `badge.tsx`, `notice.tsx`, el bloque
`UI-01`…`UI-10` de `CONVENTIONS.md` y las devDependencies de test con su lock.

**Consecuencia:** la **tarea 1 se elimina** —no le queda nada que hacer—, y con ella el riesgo #1
del plan y la advertencia de la fila IX del Constitution Check.

### H-3 · Las cuentas del enforcement

Tres números para la misma cosa: el Constitution Check dice *"cuatro chequeos estáticos nuevos"*,
el *Enfoque* dice *"pasa de verificar dos reglas a verificar seis"*, y la tabla del propio Enfoque
más la tarea 6 dicen **cinco** ("de 3 a 8 casos", que es lo correcto). Lo mismo con los tests de
render: el Enfoque dice tres y entre las tareas 12, 13 y 42 son cuatro.

### H-4 · La ola 3 son ocho rutas, no nueve

La tabla de olas dice *"Ola 3 · las nueve rutas donde el naranja tiene prohibido aparecer | 22 –
30"*. `calendario` es la novena y se migra en la **tarea 20, ola 2**. La cobertura de `RF-21` sí lo
dice bien (20, 22–29).

### H-5 · La tabla de cobertura dejó de coincidir

No hay alcance perdido, pero la tabla ya no sirve como control:

- `RF-15` cita la tarea 22, que no lo declara. `RF-23` cita las tareas 18, 19, 34 y 41, y ninguna
  lo declara: la única es la 16.
- Al revés: `RF-10` no cita la 15, `RF-06` no cita la 22, `RF-19` no cita la 11, y las tres lo
  declaran.
- `RF-01` usa el rango *"todas las de pantalla (14–41)"*, que barre adentro tareas de test.
- Falta la fila de **`RF-24`**, que hoy sólo lo construye la tarea 8.

### H-6 · Cerrado con el alta de `RF-24`

La tarea 8 reemplazaba la pantalla de bienvenida por el tablero, declarando `RF-01` y `RF-02`, que
son de aspecto. No es aspecto: cambia dónde cae una persona al entrar, y la spec ponía
*"reorganizar el contenido de las pantallas"* fuera de alcance con una sola excepción firmada
(`RF-14`). Se agregó `RF-24` con su criterio, el *fuera de alcance* pasó a nombrar las dos
excepciones, y la spec se volvió a firmar.

### H-7 · La válvula de `RF-08`, para `/converge`

*"Si al migrar aparece una entidad que no trae ninguna de esas señales, no se inventa: se deja sin
punteado y se anota."* Es la decisión correcta —agregar el campo sería backend, fuera de alcance—,
pero el requisito está firmado sin excepciones. Lo que se anote tiene que quedar escrito en el
plan y llegar a `/converge`, no en un comentario de código.

### H-8 · El naranja que la 006 dejó en `/calendario`

Apareció el primer `variant="brand"` del repositorio, en `components/ui/confirm-dialog.tsx:115`.
Sólo lo usa `CalendarGrid.tsx`, que sólo lo usa `app/(private)/calendario/page.tsx` — **una de las
nueve rutas donde `RF-21` exige cero naranja**. O sea: código ya mergeado a `main` incumplía un
requisito firmado antes de que la 012 escribiera una línea.

**Decidido el 2026-08-31 por el humano, y ya bajado a la spec:** la ventana de confirmación **no
cuenta**. Confirmar no es una acción nueva, es la misma preguntada de nuevo. `RF-11` y `RF-21` lo
dicen ahora, con sus criterios, y la spec se volvió a firmar.

**Lo que falta**, y es del `Frontend-Architect`: los chequeos (a) y (b) de la tarea 6 tienen que
**excluir las ventanas de confirmación** al recorrer el árbol de imports. Sin eso, el test cuenta
el naranja del diálogo, `/calendario` da uno en vez de cero y el gate se traba contra una regla que
la spec ya no exige.

## Validación

- [x] Veredicto explícito.
- [x] Cada hallazgo dice qué documento hay que corregir y qué rol lo hace.
- [x] Nada se corrigió en silencio: `analyze` reporta, y corregir es del rol dueño de cada
      documento. Las dos correcciones de `spec.md` las hizo el `Solution-Designer` con decisión
      del humano, y quedaron registradas como enmiendas con re-firma.

## 6. Segunda corrida — qué se corrigió, y quién

Los cinco hallazgos abiertos se cerraron el 2026-08-31, cada uno en su artefacto y por su rol
dueño. Ninguno se cerró bajando la vara.

| # | Corrección | Dónde |
|---|---|---|
| **H-1** | Los chequeos de la píldora y de la plata **nacen con su lista de excepciones sembrada** con los dieciséis archivos que hoy los violan, y **cada tarea de pantalla saca los suyos en el mismo commit en que migra**. La lista es el mapa de lo que falta y tiene que terminar vacía. Los otros tres chequeos nacen verdes de verdad. Ninguna excepción se agrega después de la tarea 6 | `plan.md` → *Enfoque* y *Contexto de traspaso* · `tasks.md` → *Orden* y tarea 6 |
| **H-2** | La tarea 1 se eliminó y el hueco quedó explicado; el riesgo #1 y la fila IX del Constitution Check se reescribieron sobre lo que hay en `main`. La numeración **no se corrió**: las referencias cruzadas apuntan a estos números | `plan.md` · `tasks.md` |
| **H-3** | Cinco chequeos nuevos y cuatro tests de render, dicho igual en las cuatro secciones que lo mencionaban | `plan.md` |
| **H-4** | La ola 3 son **ocho** rutas; la novena, `calendario`, va en la tarea 20 | `tasks.md` |
| **H-5** | Las nueve filas que no coincidían, corregidas, más la fila nueva de `RF-24`. **Verificado a máquina**: no queda ninguna tarea de construcción declarada en su columna "Cubre" que falte en su fila de cobertura | `tasks.md` |
| **H-8** | La spec exceptúa la ventana de confirmación (`RF-11`, `RF-21`), firmada; los chequeos (a) y (b) dejan `confirm-dialog.tsx` fuera del recorrido; la tarea 20 dice que ese naranja se queda | `spec.md` · `plan.md` · `tasks.md` |

**Estado para arrancar:** las 43 tareas —2 a 44— están numeradas sin huecos salvo el declarado,
los 24 requisitos tienen tarea y test, y los tres documentos dicen lo mismo. `/implement` puede
correr desde la tarea 2.
