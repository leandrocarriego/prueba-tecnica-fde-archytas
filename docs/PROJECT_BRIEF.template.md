# Project Brief — [Nombre del Cliente/Proyecto]

## Propósito
Este documento captura el acuerdo inicial entre el **Forward Deployed Engineer** y el cliente sobre las necesidades y el desarrollo planificado del proyecto. Este brief sirve como base para generar la documentación de diseño de solución.

No hay un analista que releve y después alguien distinto que construya: el Forward Deployed Engineer acompaña el trabajo **de punta a punta** —del pedido del cliente a la funcionalidad en producción— y por eso este brief y el código que sale de él responden a la misma persona.

- **Versión**: 1.0.0 · **Fecha**: [YYYY-MM-DD]
- **Creado por**: [Nombre del Forward Deployed Engineer]
- **Cliente**: [Nombre del Cliente]
- **Proyecto**: [Nombre del Proyecto]

---

## Contexto del Cliente

### Resumen del Negocio
Breve descripción del negocio y contexto del cliente.

### Situación Actual
- ¿Qué problemas o necesidades tiene el cliente?
- ¿Qué están haciendo actualmente (procesos manuales, sistemas existentes, etc.)?

---

## Objetivos del Proyecto

### Objetivos Principales
- [Objetivo 1]
- [Objetivo 2]
- [Objetivo 3]

### Criterios de Éxito
- [Criterio 1]
- [Criterio 2]

---

## Alcance Inicial (Alto Nivel)

### En Alcance
- [Funcionalidad/Capacidad 1]
- [Funcionalidad/Capacidad 2]
- [Funcionalidad/Capacidad 3]

### Fuera de Alcance (por ahora)
- [Elemento excluido 1]
- [Elemento excluido 2]

---

## Requisitos Clave

### Requisitos Funcionales
- [Requisito 1]
- [Requisito 2]
- [Requisito 3]

### Requisitos No Funcionales
- Rendimiento: [expectativas]
- Seguridad: [requisitos]
- Escalabilidad: [necesidades]

---

## Integraciones y Automatizaciones

### Servicios/APIs Externos
- [Servicio 1]: [Propósito]
- [Servicio 2]: [Propósito]

### Automatizaciones Necesarias
- [Automatización 1]: [Descripción]
- [Automatización 2]: [Descripción]

### Tareas en Background
- [Tarea 1]: [Descripción]
- [Tarea 2]: [Descripción]

---

## Restricciones Conocidas

### Restricciones Técnicas
- [Restricción 1]
- [Restricción 2]

### Restricciones de Negocio
- [Restricción 1]
- [Restricción 2]

### Restricciones de Tiempo
- [Información de timeline]

---

## Supuestos

- [Supuesto 1]
- [Supuesto 2]
- [Supuesto 3]

---

## Próximos Pasos

1. El Forward Deployed Engineer escribe este brief a partir de la reunión con el cliente.
2. Para cada funcionalidad se redacta una **especificación**: qué va a hacer el sistema, para
   quién y en qué casos. Va en español y sin detalle técnico, para que se pueda leer y discutir
   sin conocer el sistema por dentro.
3. Se repasa con el cliente hasta sacarle las ambigüedades, y **el cliente la aprueba**. Ese
   acuerdo es el que después se verifica contra lo construido.
4. Recién con la especificación aprobada arranca la construcción: primero se decide cómo se
   resuelve, después se escribe el código y sus pruebas.

> Este documento es **cara al cliente**: se lee, se discute y se firma con él. No lleva nombres
> de archivo, comandos, tecnologías ni rutas — eso vive en la documentación interna. El flujo
> técnico equivalente está en `AGENTS.md` y en `docs/specs/README.md`.

---

## Versionado de este documento

El brief se versiona porque el cliente lo lee y lo acuerda: sin una versión, "el brief" es
ambiguo apenas cambia una línea, y no se puede decir sobre cuál hubo acuerdo.

`MAJOR` — cambia el alcance acordado · `MINOR` — se agrega o se precisa un requisito sin mover el
alcance · `PATCH` — redacción y aclaraciones.

**Actualizar la tabla de estado de los problemas no cambia la versión**: anota el avance, no el
acuerdo. Es la única sección que se edita sin conversarlo con el cliente, y la mantiene al día el
`Release-Manager` en `/ship`.

| Versión | Fecha | Qué cambió |
|---------|-------|------------|
| 1.0.0 | [YYYY-MM-DD] | Versión inicial, a partir de la reunión de relevamiento. |

---

## Notas

[Cualquier nota adicional, preguntas o aclaraciones necesarias]
