# Skill — Planificar la implementación de una feature

Tags: [specs] [sdd] [arquitectura]

Rol dueño: **Backend-Architect** · **Frontend-Architect**. Si la feature toca las dos puntas, se
cubren ambas y se dice.

## Objetivo
Traducir una spec firmada a un plan técnico: enfoque, módulos, eventos, datos y contratos. Es el
artefacto donde viven las decisiones que `spec.md` tiene prohibido llevar.

## Cuándo usarla
- Después de `approve_spec` y antes de `tasks`.
- Cuando una feature ya firmada cambia de enfoque técnico.

## Precondiciones
- **`spec.md` está en `Estado: Aprobado`**, con quién firmó y cuándo. Si está en `Borrador`, se
  frena: planificar antes de la firma resuelve un alcance que el cliente no acordó, y el gate
  deja de serlo (Artículo V).

## Reglas (ESTRICTO)
- **No se amplía el alcance.** Si algo hace falta y no está en la spec firmada, se frena y se
  dice: se vuelve a la spec, no se agrega en el plan.
- **El Constitution Check va primero**, antes de decidir nada. Un plan que no lo pasa no avanza
  aunque sea técnicamente correcto.
- Una excepción a la constitución **la aprueba el humano, no el agente**, y queda registrada con
  qué alternativa se descartó.
- Ninguna biblioteca nueva entra sin justificarse en *Alternativas descartadas*.

## Pasos (ORDEN OBLIGATORIO)
1. Copiar `docs/specs/plan.template.md` a `docs/specs/<NNN-feature>/plan.md`.
2. Completar el **Constitution Check**, artículo por artículo.
3. Escribir el enfoque y los módulos afectados.
4. Definir los **eventos de dominio**: los módulos no se importan entre sí (Artículo IV), así que
   todo lo que un módulo tenga que contarle a otro es un evento del catálogo compartido.
5. Datos y contratos. Toda tabla nueva necesita su migración; toda ruta declara su autorización.
6. Escribir el **Contexto de traspaso**: qué necesita saber el Developer, qué necesita saber el
   Tester, dónde tiene que mirar el Code-Reviewer.
7. Si la investigación previa o el modelo de datos son largos, sacarlos a `research.md` y
   `data-model.md` y dejar el puntero.

## Validación
- [ ] El Constitution Check está completo y toda excepción tiene su justificación.
- [ ] Cada requisito de la spec tiene un lugar en el plan.
- [ ] El plan no introduce alcance que la spec no pide.
- [ ] El **Contexto de traspaso** existe y dice algo útil, no un placeholder.

## Errores comunes (evitar)
- Empezar a planificar sobre una spec en `Borrador`.
- Resolver con un import entre módulos lo que corresponde a un evento.
