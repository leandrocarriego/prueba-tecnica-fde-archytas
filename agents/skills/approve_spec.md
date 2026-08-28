# Skill — Registrar la firma del cliente sobre una spec

Tags: [specs] [sdd] [gate]

Rol dueño: **Solution-Designer**.

## Objetivo
Registrar la aprobación del cliente sobre una `spec.md` y habilitar la planificación técnica.

## Cuándo usarla
- Cuando el cliente revisó la spec y la aprueba. **Es un gate**: sin esto no arranca `plan`
  (`CONSTITUTION.md`, Artículo V).

## Precondiciones
- La spec no tiene marcadores `[NECESITA ACLARACIÓN]` sin resolver.
- El cliente efectivamente la revisó.

## Reglas (ESTRICTO)
- **No se aprueba en nombre del cliente.** La firma es de una persona; esta skill sólo la
  registra.
- **No se aprueba una spec con decisiones técnicas adentro**: eso mueve el gate de lugar.
- La fecha se pide, no se inventa.

## Pasos (ORDEN OBLIGATORIO)
1. Abrir `docs/specs/<NNN-feature>/spec.md` y verificar que esté lista para firmar:
   - sin `[NECESITA ACLARACIÓN]` ni secciones vacías;
   - **sin decisiones técnicas** — nada de stack, endpoints, schemas ni rutas de archivo;
   - en español y comprensible sin conocer el código;
   - si la feature tiene `diagrams/`, sus diagramas cara al cliente están en español y a nivel de
     negocio.
2. Si algo de lo anterior falla, **no registrar la firma**: informar qué falta y proponer
   `clarify`.
3. Si está lista, actualizar el encabezado: `Estado: Aprobado`, `Aprobada por: <quien firma>`,
   `Fecha de aprobación: <YYYY-MM-DD>`.

## Validación
- [ ] El encabezado tiene estado, firmante y fecha.
- [ ] Se confirmó qué quedó registrado y cuál es el paso siguiente (`plan`).

## Errores comunes (evitar)
- Registrar la firma para "destrabar" el trabajo cuando el cliente todavía no la vio.
