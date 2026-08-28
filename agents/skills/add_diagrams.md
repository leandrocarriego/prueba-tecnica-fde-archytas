# Skill — Agregar diagramas

Tags: [specs] [diagramas] [mermaid] [cara-al-cliente]

## Objetivo
Generar o actualizar los **diagramas de flujo** (Mermaid) de una feature como vista derivada de
su spec: flujos por actor, un flujo cross-actor de punta a punta y la máquina de estados de la
entidad. La salida vive junto a la spec, se valida en CI y se puede exportar para compartir con
el cliente.

Convención completa: `docs/specs/DIAGRAMS.md`.

## Cuándo usarla
- Después de `/specify` (y de la firma): producir los flujos de negocio **cara al cliente** que
  acompañan a `spec.md` para la revisión.
- Después de `/plan`: actualizar la **máquina de estados** desde `data-model.md` y, si aporta,
  agregar una secuencia técnica (interna, en inglés) desde `contracts/`.
- Cada vez que cambian la spec o el data-model y los diagramas tienen que seguirlos.

## Precondiciones
- La feature existe en `docs/specs/<NNN-feature>/` con al menos `spec.md`.
- `mermaid-cli` disponible para validar y exportar (`$MMDC`, `mmdc` en el PATH, o `npx`).

## Pasos (ORDEN OBLIGATORIO)

### 1) Leer las fuentes autoritativas (derivar, nunca inventar)
- Actores y pasos ← `spec.md` (Historias de Usuario / Requisitos Funcionales).
- Estados y transiciones ← `data-model.md` (máquina de estados) o la lista de estados de la RF
  en `spec.md`.
- Endpoints y eventos (sólo para secuencias técnicas internas) ← `contracts/`.
> El diagrama es una **vista** de la spec. Si no coinciden, gana la spec: se arregla el diagrama.

### 2) Crear el set de diagramas
Escribir un `.mmd` por diagrama en `docs/specs/<NNN-feature>/diagrams/`:

| Archivo | Tipo de Mermaid | Qué muestra | Audiencia / idioma |
|---------|-----------------|-------------|--------------------|
| `flujo-general.mmd` | `sequenceDiagram` | flujo cross-actor de punta a punta (el flujo estrella) | cliente · español |
| `flujo-<rol>.mmd` | `flowchart TD` | uno por actor/rol | cliente · español |
| `estados-<entidad>.mmd` | `stateDiagram-v2` | ciclo de vida / máquina de estados | cliente · español |
| `sequence-<caso>.mmd` *(opcional)* | `sequenceDiagram` | flujo técnico a nivel endpoint | interno · inglés |

Reglas de escritura (fiabilidad):
- Los diagramas cara al cliente van en **español** y a nivel de negocio (sin endpoints, tablas
  ni rutas de archivo) — Constitution Art. VIII.
- Entrecomillar el texto de los nodos de flowchart (`A["texto: con puntuación"]`) y **evitar
  paréntesis dentro de las etiquetas** (los paréntesis son sintaxis de forma → rompen el parser).
- Un diagrama, una idea. Agregar un título en el frontmatter: `---\ntitle: …\n---`.

### 3) Validar
```bash
scripts/diagrams/validate.sh docs/specs/<NNN-feature>/diagrams
```
Todos los `.mmd` tienen que compilar. Arreglar los que fallen antes de seguir.

### 4) Generar los artefactos para compartir
```bash
scripts/diagrams/export.sh docs/specs/<NNN-feature>
```
Esto regenera `diagrams/README.md` —que se versiona y se renderiza en GitHub— y las imágenes en
`dist/diagramas/<NNN-feature>/` (PNG/PDF/SVG, gitignoradas: binario regenerable).

## Validación (antes de declarar terminado)
- [ ] `scripts/diagrams/validate.sh <feature>/diagrams` pasa (todos los `.mmd` compilan).
- [ ] Existe un `flujo-general`, un `flujo-<rol>` por cada actor de la spec y un
      `estados-<entidad>` por cada entidad con estados.
- [ ] Los diagramas cara al cliente están en español y sin detalle de implementación.
- [ ] Actores y estados coinciden con `spec.md` / `data-model.md` (sin pasos inventados).
- [ ] `diagrams/README.md` regenerado y commiteado; las imágenes quedaron en `dist/`, fuera de git.
