# Skill — Verificar la consistencia spec ↔ plan ↔ tasks

Tags: [specs] [sdd] [consistencia]

Rol dueño: **Lead**.

## Objetivo
Verificar que `spec.md`, `plan.md` y `tasks.md` describan la misma cosa, **antes** de escribir
código.

## Cuándo usarla
- Después de `tasks` y antes de `implement`.
- Cada vez que uno de los tres documentos cambia después de haberse alineado.

## Precondiciones
- Existen los tres artefactos.

## Reglas (ESTRICTO)
- **No se arregla en silencio.** Esta skill reporta; corregir es del rol dueño de cada documento.
  Un hallazgo tapado es un desacuerdo que reaparece en `converge`, más tarde y más caro.
- No se opina sobre el código: todavía no hay.

## Pasos (ORDEN OBLIGATORIO)
1. **Alcance**
   - Un `RF` que ningún plan resuelve ni ninguna tarea construye → se prometió y nadie lo tomó.
   - Una tarea o decisión del plan que no responde a ningún requisito → alcance que el cliente no
     firmó.
   - Una historia sin tareas.
2. **Trazabilidad** — la tabla de cobertura está completa: cada `RF` con tarea y con test; cada
   criterio de aceptación se corresponde con un requisito.
3. **Integridad de los documentos** — la spec sin `[NECESITA ACLARACIÓN]` y en `Estado:
   Aprobado`; el Constitution Check completo con sus excepciones justificadas; el **Contexto de
   traspaso** presente y útil; la spec sin decisiones técnicas.
4. **Coherencia con el proyecto** — los módulos del plan existen o su creación está justificada;
   nada contradice las reglas del dominio ni las fronteras entre módulos.

## Validación
- [ ] Veredicto explícito: **consistente** o **inconsistente**.
- [ ] Si es inconsistente, cada hallazgo dice qué documento hay que corregir y quién lo hace.

## Errores comunes (evitar)
- Corregir la spec para que coincida con las tareas. Es al revés: la spec es lo firmado.
