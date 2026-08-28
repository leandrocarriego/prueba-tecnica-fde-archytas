# Skill — Escribir la spec de una feature

Tags: [specs] [sdd] [cara-al-cliente]

Rol dueño: **Solution-Designer**.

## Objetivo
Escribir la definición funcional de una feature nueva: qué hace y para quién. La salida es
`docs/specs/<NNN-feature>/spec.md`, **el único artefacto cara al cliente**.

## Cuándo usarla
- Al arrancar una feature, antes de cualquier decisión técnica.
- Cuando el cliente pide algo que no cubre ninguna spec, ni activa ni archivada.

## Precondiciones
- Existe `docs/PROJECT_BRIEF.md` con el alcance acordado.
- Hay una descripción de qué tiene que hacer la feature. Si no la hay, se pide: **no se inventa
  el alcance**.

## Reglas (ESTRICTO)
- **Ninguna decisión técnica.** Sin stack, endpoints, schemas, tablas ni rutas de archivo: eso va
  en `plan.md`. Si se cuela acá, el gate del cliente deja de ser sobre el alcance.
- **Nada que contradiga las reglas del dominio** (`CONSTITUTION.md`, artículos I a III).
- **No se marca como `Aprobado`.** Eso lo hace la skill `approve_spec`, cuando el cliente firma.
- Lo que no esté definido se escribe como `[NECESITA ACLARACIÓN: pregunta concreta]`. **No se
  resuelve suponiendo**: es preferible una spec con tres preguntas abiertas que una con tres
  invenciones que el cliente firma sin notarlas.

## Pasos (ORDEN OBLIGATORIO)
1. Leer `docs/PROJECT_BRIEF.md`. Si la feature resuelve uno de los doce problemas, nombrarlo
   (`P4`) y reusar el vocabulario del cliente, no uno nuevo. Leer también el bloque del problema
   en `docs/FDE_ASSESSMENT.md`: ahí están las consultas abiertas que el relevamiento dejó por
   escrito, y cada una que siga sin respuesta se arrastra a la spec como
   `[NECESITA ACLARACIÓN: …]` en vez de resolverse suponiendo. **Nada de lo técnico de ese
   documento entra en la spec.**
2. Calcular el número: el siguiente al mayor **entre `docs/specs/` y `docs/specs/archive/`**. Un
   número no se reutiliza nunca.
3. Elegir el slug: dos o tres palabras, kebab-case, **en inglés** y sin tildes
   (`001-portal-extraction`). El contenido va en español; sólo el nombre va en inglés.
4. Crear `docs/specs/<NNN-slug>/` y copiar `docs/specs/spec.template.md` como `spec.md`.
5. Completarla con los dos formatos, que hacen falta los dos:
   - **Historias de usuario** — para quién y por qué. Priorizadas y **entregables de forma
     independiente**: si sólo se construye H1, el cliente ya tiene algo que usar.
   - **Requisitos funcionales en EARS** — qué exactamente. Atómicos y verificables. De cada uno
     sale al menos un test.
6. Escribir un criterio de aceptación por requisito, redactado como algo que el cliente puede
   observar andando.

## Validación
- [ ] La spec no tiene una sola decisión técnica.
- [ ] Cada requisito está en uno de los cinco patrones EARS.
- [ ] Cada requisito tiene su criterio de aceptación.
- [ ] Cada historia es entregable por sí sola.
- [ ] Se informó el número que tomó la feature, cuántos requisitos quedaron y qué preguntas
      abiertas hay. Con preguntas abiertas sigue `clarify`; sin ellas, `approve_spec`.

## Errores comunes (evitar)
- Resolver una ambigüedad suponiendo, en vez de marcarla.
- Reutilizar un número de una feature archivada.
- Escribir el slug en español, o el contenido en inglés.
