# [Nombre de la feature] — Plan técnico

<!--
  ARTEFACTO INTERNO. Acá van las decisiones técnicas que spec.md no puede llevar.
  No se exporta al cliente.
-->

**Feature:** [NNN-feature-slug] · **Spec aprobada el:** [YYYY-MM-DD] · **Fecha:** [YYYY-MM-DD]

<!-- Si la spec no está Aprobada, este documento no debería existir todavía (Artículo V). -->

## Constitution Check

<!--
  Obligatorio antes de pasar a /tasks. Se declara explícitamente, artículo por
  artículo, que el enfoque elegido no viola ninguno. Un plan que no pasa este
  chequeo no avanza, aunque sea técnicamente correcto.
-->

| Artículo | Cumple | Cómo |
|---|---|---|
| I — El origen es ajeno y de sólo lectura | | |
| II — Nada se descarta | | |
| III — Flujo unidireccional, `raw` inmutable | | |
| IV — Las fronteras entre módulos son reales | | |
| V — Spec primero, y con firma | | |
| VI — Lo que no está tipado y testeado no está terminado | | |
| VII — Las credenciales de terceros viven sólo en el entorno | | |
| VIII — Un idioma para cada audiencia | | |
| IX — Las dependencias entran por la puerta | | |

**Excepciones solicitadas:** ninguna.

<!--
  Si alguna hace falta: cuál, por qué, y qué alternativa se descartó. Una excepción
  a la constitución NO la aprueba un agente — la aprueba el humano, y queda acá.
-->

## Enfoque

<!-- Cómo se resuelve, en tres o cuatro párrafos. Lo suficiente para que otro pueda implementarlo sin adivinar. -->

## Módulos afectados

| Módulo | Qué cambia | Nuevo |
|---|---|---|
| | | |

<!-- Un módulo nuevo se justifica por una capacidad del negocio con lenguaje propio, no por acumulación de archivos (ARCHITECTURE.md → Agregar un módulo o una feature). -->

## Eventos de dominio

<!--
  Los módulos NO se importan entre sí: se comunican por eventos (Artículo IV).
  Listar los que esta feature publica o consume. Van en app/shared/events/catalog.py,
  en pasado, inmutables, con identificadores y no entidades (GEN-08).
  Si no hay ninguno, escribir "Ninguno" y no borrar la sección.
-->

| Evento | Lo publica | Lo consume | Qué lleva |
|---|---|---|---|
| | | | |

## Datos

<!-- Entidades, campos y estados nuevos o modificados. El detalle largo va en data-model.md. Toda tabla nueva necesita su migración (DB-01). -->

## Contratos

<!-- Endpoints y sus schemas, o el puntero a contracts/. Toda ruta declara su autorización (PY-09). -->

## Alternativas descartadas

<!-- Qué más se consideró y por qué no. Evita que la próxima persona repita el análisis. El detalle largo va en research.md. -->

## Riesgos

| Riesgo | Impacto | Cómo se mitiga |
|---|---|---|
| | | |

## Contexto de traspaso

<!--
  OBLIGATORIO. Lo leen el Developer, el Tester y el Code-Reviewer. Si esta sección
  no existe o dejó de ser verdad, la feature no está lista (Definition of Done).
-->

**Para el Developer** — [por dónde empezar, qué NO tocar, qué decisión ya está tomada y no hay que rediscutir]

**Para el Tester** — [qué es lo que puede romperse de verdad, qué casos borde importan, qué se prueba con HTML fijado]

**Para el Code-Reviewer** — [qué convenciones son las que están en juego acá, dónde mirar primero]
