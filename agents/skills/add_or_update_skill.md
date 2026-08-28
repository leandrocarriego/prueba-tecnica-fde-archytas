# Skill — Agregar o actualizar una skill

Tags: [skills] [review]

## Objetivo
Crear o modificar una skill para que sea consistente, descubrible y exigible por los agentes en
todo el repositorio.

## Cuándo usarla
- Agregar un archivo de skill nuevo.
- Actualizar el procedimiento o la convención de una skill existente.
- Cambiar el comportamiento esperado de los agentes (reglas, estándares, flujos de trabajo).
- Crear o actualizar triggers y su mapa.

## Precondiciones
- La skill representa un **procedimiento repetible**, no una instrucción puntual.
- Se conocen los roles, los triggers y las convenciones vigentes (`AGENTS.md`,
  `agents/roles/`).
- El procedimiento es coherente con la arquitectura actual: monolito modular, módulos en
  `backend/app/modules/`, frontera por eventos (`app/shared/events`).

## Pasos (ORDEN OBLIGATORIO)

### 1) Elegir un nombre claro
- **snake_case**.
- **verbo + objeto**.
- Sin prefijos numéricos.

Ejemplos:
- `add_backend_feature.md`
- `add_frontend_feature.md`
- `add_diagrams.md`
- `deploy.md`

El nombre del archivo es el identificador de la skill.

---

### 2) Ubicar el archivo
- Crear o actualizar el archivo en `agents/skills/`.

---

### 3) Respetar el orden de las secciones
Incluir las secciones en este orden exacto:
- Objetivo
- Cuándo usarla
- Precondiciones (opcional si es obvio)
- Reglas (ESTRICTO) (opcional, si hay restricciones duras)
- Pasos (ORDEN OBLIGATORIO)
- Validación
- Errores comunes (evitar)
- Troubleshooting

No reordenar las secciones.

---

### 4) Agregar tags
- Poner `Tags: [...]` al principio del archivo (opcional pero recomendado).
- Usar:
  - un tag principal (por ejemplo `[release]`, `[debug]`, `[review]`)
  - hasta dos secundarios
- Los tags son descriptivos: no reemplazan a los triggers.

---

### 5) Registrar los triggers en `AGENTS.md`
- Agregar una línea de trigger explícita en la categoría que corresponda.
- Actualizar el **Mapa de triggers de skills** usando el nombre de la skill.
- El lenguaje del trigger tiene que ser estricto y sin ambigüedad.

Si no hay trigger, la skill se considera incompleta.

---

### 6) Actualizar el índice de skills
- Agregar o quitar la skill de la lista de `agents/skills/README.md`.
- El índice, el mapa de triggers de `AGENTS.md` y los archivos existentes tienen que coincidir
  exactamente.

---

### 7) Actualizar las referencias de los roles (sólo si hace falta)
- Agregar la skill a las **skills obligatorias** de un rol SÓLO si ese rol debe aplicarla siempre.
- Si no, alcanza con los triggers.

No sobre-asignar skills a los roles.

---

### 8) Revisar la consistencia
Chequeo final:
- el archivo de la skill existe
- el nombre del archivo coincide con las referencias de `AGENTS.md` y del README
- existe el trigger
- el mapa de triggers incluye la skill
- no hay nombres duplicados ni ambiguos
- los pasos son concretos y exigibles
- el idioma es español y las rutas de archivo corresponden a la arquitectura actual

Si la skill afecta la ejecución o un quality gate, la sección **Validación** debe ser explícita
y verificable (comandos, no adjetivos).

---

## Validación
- La skill sigue la convención de `agents/skills/README.md`.
- `AGENTS.md` tiene el trigger y la entrada en el mapa.
- El índice del README lista exactamente las skills existentes:
  ```bash
  cd agents/skills && ls *.md
  ```
- No se usan identificadores numéricos.
- Un agente puede determinar sin ambigüedad cuándo aplicar la skill.
- La skill está escrita en español y no referencia estructuras que ya no existen.

## Errores comunes (evitar)
- Crear skills sin trigger.
- Usar prefijos numéricos u orden implícito.
- Escribir pasos vagos ("manejar errores", "asegurar la estabilidad").
- Dejar el README o el mapa de `AGENTS.md` desactualizados al agregar o borrar una skill.
- Documentar rutas o estructuras que ya no existen en el repositorio.

## Troubleshooting
- Los agentes ignoran la skill → verificar que exista un trigger estricto en `AGENTS.md`.
- Parecen aplicar varias skills → resolver por prioridad de trigger y contexto del rol
  (`safety/debug → fronteras → implementación`).
- El nombre no queda claro → renombrar la skill para que refleje mejor su intención, y
  actualizar `AGENTS.md` y el README en el mismo cambio.
