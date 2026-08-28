# Skill — Aclarar una spec antes de la firma

Tags: [specs] [sdd] [gate]

Rol dueño: **Solution-Designer**.

## Objetivo
Bajar el riesgo de una `spec.md` resolviendo lo que quedó ambiguo, **antes** de que el cliente la
firme.

## Cuándo usarla
- Entre `specify` y `approve_spec`, siempre que la spec tenga preguntas abiertas.
- Cuando al releer una spec aparece un requisito que no se puede escribir en EARS.

## Precondiciones
- Existe `docs/specs/<NNN-feature>/spec.md`.
- La spec **no** está en `Estado: Aprobado`. Después de la firma, un cambio de alcance es una
  spec nueva, no una aclaración.

## Reglas (ESTRICTO)
- **No se resuelve una ambigüedad suponiendo.** Es la forma más común de que el cliente firme
  algo que nadie le preguntó.
- **No entran decisiones técnicas.** La respuesta a *"¿cómo lo hacemos?"* va en `plan.md`.
- **No se marca la spec como `Aprobado`.** Eso es `approve_spec`.
- Lo que el cliente decide dejar afuera va a **Fuera de alcance**; no se borra en silencio.

## Pasos (ORDEN OBLIGATORIO)
1. Leer la spec entera y juntar dos cosas:
   - los marcadores `[NECESITA ACLARACIÓN: …]` explícitos;
   - las ambigüedades **implícitas**, que son las peligrosas — un requisito que no se puede
     escribir en EARS, un criterio que no se puede observar, un actor que aparece en una historia
     y no en la tabla, un "y/o", un adjetivo sin medida.
2. Priorizar: primero lo que **cambia el alcance o la arquitectura**. Una duda de redacción no
   vale una pregunta al cliente.
3. Preguntar en tandas cortas, con opciones concretas cuando las haya. Es preferible *"¿el
   vencimiento se cuenta en días corridos o hábiles?"* que *"aclarar el tema de fechas"*.
4. Con cada respuesta, actualizar la spec: reescribir el requisito, borrar el marcador resuelto y
   dejar el criterio de aceptación correspondiente.

## Validación
- [ ] No queda ningún `[NECESITA ACLARACIÓN]` sin resolver; si no queda ninguno, la sección
      **Preguntas abiertas** se borra.
- [ ] Todo requisito nuevo o reescrito entra en un patrón EARS.
- [ ] Se informó cuántas preguntas se resolvieron y cuántas quedan.

## Errores comunes (evitar)
- Preguntar cosas de redacción y gastar la atención del cliente antes de llegar a lo que importa.
- Cerrar una pregunta con una respuesta que en realidad es una decisión técnica.
