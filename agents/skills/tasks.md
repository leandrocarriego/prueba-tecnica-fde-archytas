# Skill — Desglosar un plan en tareas ejecutables

Tags: [specs] [sdd]

Rol dueño: **Backend-Architect** · **Frontend-Architect**, el mismo que escribió el plan.

## Objetivo
Convertir un plan técnico en tareas ejecutables, cada una mapeada a la skill que la ejecuta y al
requisito que cubre.

## Cuándo usarla
- Después de `plan` y antes de `analyze`.
- Cuando el plan cambia y las tareas dejan de reflejarlo.

## Precondiciones
- Existe `plan.md` y su Constitution Check pasó. Sin plan no hay tareas: se estarían inventando
  decisiones técnicas en una tabla.

## Reglas (ESTRICTO)
- **No se inventa una skill que no existe.** Si ninguna aplica, se frena y se dice: puede faltar
  una skill (se agrega con `add_or_update_skill`) o el trabajo puede no corresponder al proyecto.
- **Ningún requisito queda sin fila** en la tabla de cobertura. Un `RF` sin tarea es alcance
  firmado que nadie se comprometió a hacer, y `converge` lo encuentra al final, cuando ya cuesta
  caro.
- Una tarea se termina de una sentada. Si no entra, son dos.

## Pasos (ORDEN OBLIGATORIO)
1. Copiar `docs/specs/tasks.template.md` a `docs/specs/<NNN-feature>/tasks.md`.
2. Agrupar las tareas **por historia de usuario, en orden de prioridad**. Al terminar las de H1
   tiene que haber algo entregable de verdad.
3. Anotar en cada tarea: qué hace, **la skill** que la ejecuta, el rol dueño y qué requisitos
   cubre. El mapa está en `AGENTS.md` → *Mapa de triggers*.
4. Ordenar dentro de cada historia: migración → backend → frontend → tests. Las migraciones
   primero porque todo lo demás depende del esquema.
5. Completar la **tabla de cobertura de requisitos**.

## Validación
- [ ] Toda tarea nombra una skill que existe.
- [ ] Todo `RF` de la spec tiene al menos una tarea y al menos un test.
- [ ] Terminar las tareas de H1 deja algo que el cliente puede usar.

## Errores comunes (evitar)
- Tareas del tamaño de una feature ("implementar el módulo de compras").
- Dejar los tests como una única tarea final, en vez de por historia.
