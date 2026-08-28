# [Nombre de la feature] — Especificación

<!--
  ESTE ES EL ÚNICO ARTEFACTO CARA AL CLIENTE. Se lee, se discute y se firma con él.
  NO lleva decisiones técnicas: nada de stack, endpoints, schemas, tablas ni rutas
  de archivo. Todo eso va en plan.md.
  Las notas como esta no salen en el PDF: el exportador las descarta.
-->

**Estado:** Borrador · **Feature:** [NNN-feature-slug] · **Fecha:** [YYYY-MM-DD]

<!-- `/approve-spec` completa Aprobada por y Fecha de aprobación, y pasa Estado a Aprobado. -->

## Problema

<!-- Qué le duele hoy al cliente. Si resuelve uno de los doce problemas del brief, nombralo: "Resuelve P4 — El problema de los proveedores". -->

## Objetivo

<!-- Una o dos frases: qué va a poder hacer el negocio cuando esto esté. En términos del negocio, no del sistema. -->

## Actores

| Actor | Qué hace con esta feature |
|---|---|
| [Dueño / Compras / Ventas / El sistema] | |

## Historias de usuario

<!--
  Priorizadas y ENTREGABLES DE FORMA INDEPENDIENTE: si sólo se construye H1, el
  cliente ya tiene algo que usar. Ese corte es lo que permite entregar por partes
  y es la razón de que estén numeradas por prioridad, no por orden narrativo.
-->

### H1 — [Título corto] *(prioridad más alta)*
Como **[actor]**, quiero **[qué]**, para **[por qué]**.

**Cómo se prueba que anda:** [una frase que alguien del negocio pueda verificar a mano]

### H2 — [Título corto]
Como **[actor]**, quiero **[qué]**, para **[por qué]**.

**Cómo se prueba que anda:**

## Requisitos funcionales

<!--
  En formato EARS: cada requisito es atómico, sin ambigüedad, y se puede verificar.
  De acá salen los tests, uno a uno. Los cinco patrones:

    Siempre        El sistema debe <respuesta>.
    Ante un evento Cuando <disparador>, el sistema debe <respuesta>.
    Durante un estado  Mientras <estado>, el sistema debe <respuesta>.
    Ante un problema   Si <condición>, entonces el sistema debe <respuesta>.
    Condicional    Donde <la opción esté activada>, el sistema debe <respuesta>.

  Reglas: un requisito por línea, un solo "debe", sin "y/o", sin adjetivos sin
  medida ("rápido", "amigable"). Si no se puede escribir así, todavía no está claro.
  Numerarlos RF-01, RF-02… y no reutilizar números dentro de la feature.
-->

| ID | Requisito | Historia |
|----|-----------|----------|
| RF-01 | Cuando [disparador], el sistema debe [respuesta]. | H1 |
| RF-02 | Si [condición], entonces el sistema debe [respuesta]. | H1 |
| RF-03 | Mientras [estado], el sistema debe [respuesta]. | H2 |

## Reglas de negocio

<!-- Lo que siempre vale, independientemente del flujo. Si una regla viene de la constitución (nada se descarta, el portal es de sólo lectura), nombrala en términos del negocio, no del artículo. -->

- 

## Criterios de aceptación

<!-- Uno por requisito funcional, redactado como algo observable. Es lo que el cliente marca cuando lo ve andando, y lo que /converge contrasta contra el código. -->

- [ ] **RF-01** — 
- [ ] **RF-02** — 
- [ ] **RF-03** — 

## Fuera de alcance

<!-- Lo que alguien podría suponer incluido y no lo está. Esta sección evita discusiones en la entrega. -->

- 

## Preguntas abiertas

<!--
  Todo lo que falte definir, marcado como [NECESITA ACLARACIÓN: pregunta concreta].
  Una spec con preguntas abiertas NO se firma: primero se resuelven con /clarify.
  Cuando no queda ninguna, esta sección se borra.
-->

- [NECESITA ACLARACIÓN: ]
