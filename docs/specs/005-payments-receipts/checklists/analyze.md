# 005-payments-receipts — Consistencia spec ↔ plan ↔ tasks

<!-- ARTEFACTO INTERNO. Hallazgos de `/analyze`. Los registra el Lead; los corrige el rol dueño de cada documento. -->

**Feature:** 005-payments-receipts · **Corrido el:** 2026-08-31 · **Rol:** Lead

## Veredicto: **consistente** (2.ª corrida, 2026-08-31)

La primera corrida dio **inconsistente** con seis hallazgos, dos de ellos bloqueantes. **Los seis
están cerrados**: cuatro corrigiendo documentos y dos con una decisión del humano tomada el mismo
día. El detalle de cada uno se conserva abajo, con su cierre — sirve para entender por qué los
documentos dicen lo que dicen.

**Lo que el veredicto significa y lo que no.** Consistente quiere decir que `spec.md`, `plan.md` y
`tasks.md` describen la misma cosa. **No** quiere decir que la feature esté lista: el Constitution
Check declara el Artículo II **incumplido, sin excepción concedida**, así que la 005 **no pasa al
gate de calidad** hasta que la cuarentena de pagos llegue a una persona. Esa es ahora una condición
escrita en el plan, que es exactamente lo que antes faltaba.

## Veredicto original: **inconsistente** (1.ª corrida)

Seis hallazgos, **dos de ellos bloqueantes**. Ninguno es de redacción: los dos bloqueantes son un
Constitution Check que no pasa y un requisito firmado que llegó a `tasks.md` sin que el plan
decidiera nada sobre él.

**Aclaración de contexto, porque cambia cómo se lee todo lo que sigue.** `/analyze` está pensado
para correr **antes** de escribir código. Acá el código ya existe: la feature se construyó en el
changeset de la 004 a la 009, y el `plan.md` y el `tasks.md` se escribieron después, como actas.
Eso no invalida la corrida —los tres documentos tienen que describir la misma cosa igual—, pero sí
cambia qué significa un hallazgo: **no está frenando una implementación, está midiendo una que ya
ocurrió**. Lo que este documento puede hacer todavía es impedir que la feature pase al gate de
calidad con desacuerdos sin registrar.

## Lo que sí cierra

Antes de los hallazgos, lo que se verificó y está bien, porque un informe que sólo lista problemas
no dice cuánto del trabajo está sano:

- **Los 59 requisitos firmados tienen fila en la tabla de cobertura de `tasks.md`**, cada uno con al
  menos una tarea y al menos un test. Ninguno quedó huérfano.
- **Los 59 tienen criterio de aceptación en la spec**, y no hay criterio que no corresponda a un
  requisito. La correspondencia es exacta en las dos direcciones.
- **Las diez historias tienen tareas.** Ninguna quedó sin construir en el desglose.
- **La spec no tiene marcadores pendientes ni decisiones técnicas filtradas**: cero apariciones de
  endpoint, tabla, schema, stack o ruta de archivo. Está en `Estado: Aprobado`, firmada el
  2026-08-29.
- **El Contexto de traspaso está y es útil**, con sus tres destinatarios —Developer, Tester,
  Code-Reviewer— y con instrucciones que un agente puede seguir sin volver a leer el plan.
- **Los módulos que el plan nombra existen** —`portal`, `ingestion`, `purchases`, `notifications`,
  `operations`, `identity`— y ninguno se crea. El plan argumenta explícitamente por qué **no** hay un
  módulo `payments`, que es la decisión de fronteras que esta feature podía equivocar.
- **La tarea 41 no responde a ningún requisito y está bien que exista**: es higiene sobre un campo
  muerto (`receipt_number`), no alcance nuevo, y el desglose lo dice con todas las letras.

## Hallazgos

### A-1 · El Constitution Check no pasa, y la cadena avanzó igual

**Documento a corregir:** `plan.md`, y la decisión es del **humano** · **Rol dueño:** Backend-Architect
propone, el humano aprueba · **Bloquea `/implement`:** sí, para las tareas 17, 18 y 60.

El Constitution Check del plan marca el **Artículo II — Nada se descarta** como **Parcial**, y el
propio plan aclara, correctamente, que *"no es una excepción aprobada: es un hallazgo"*. Una fila de
`staging.payment_row` que no se puede tipar queda en cuarentena y **no genera ninguna fila en
`operations.exception`**: nadie se entera.

El problema de consistencia no es la brecha —está bien registrada— sino lo que se hizo con ella:

- `CONSTITUTION.md` dice que **un plan que no pasa el Constitution Check no avanza**, aunque sea
  técnicamente correcto.
- `agents/skills/tasks.md` tiene como precondición explícita que **el Constitution Check haya
  pasado**.
- La feature avanzó a implementación **y** a desglose con el Check en Parcial y sin excepción
  aprobada.

**Corrección.** No la puede hacer un agente: una excepción a la constitución **la aprueba el humano y
queda registrada en el plan**. Las dos salidas posibles son del humano, no del Lead:

1. **Aprobar la excepción**, registrándola en el Constitution Check con su justificación y qué
   alternativa se descartó — y entonces las tareas 17, 18 y 60 quedan como deuda declarada.
2. **Tratarla como bloqueante**, y entonces esas tres tareas se hacen antes de que la feature vaya al
   gate de calidad.

**Elevo la decisión, no la tomo.** Y va con el dato que la hace más grande de lo que parece: ver A-4.


> ✅ **Cerrado el 2026-08-31.** El humano decidió **no aprobar ninguna excepción**: la cuarentena
> muda es trabajo bloqueante. El Constitution Check pasó de «Parcial» a **«No cumple»**, con la
> decisión, su fecha y la condición de gate escritas en el plan. La deuda dejó de estar implícita.
### A-2 · RF-43 llegó a `tasks.md` sin que el plan decidiera nada sobre él

**Documento a corregir:** `plan.md` · **Rol dueño:** Backend-Architect · **Bloquea `/implement`:** sí,
para la tarea 15.

RF-43 está firmado: *"Cuando una persona resuelva que un comprobante apartado y un pago cargado a mano
son el mismo pago, el sistema debe conservar uno solo y registrar quién lo decidió y cuándo."*

El plan lo registra como hallazgo H-14 y dice qué **no** hay —no hay ruta, `void_payment` rechaza los
de origen `PORTAL` y `split_payment` duplicaría el pago—, pero **no decide nada**: no hay ruta en la
tabla de contratos, no hay entrada en `contracts/README.md`, no hay forma resuelta. La tarea 15 del
desglose hereda ese vacío y enuncia el problema en lugar de una solución.

Son tres preguntas de diseño abiertas, y las tres tienen consecuencias sobre reglas ya firmadas:

- **¿Cuál de los dos pagos sobrevive?** Si sobrevive el del portal, hay que dejar sin efecto uno
  cargado a mano —eso ya existe—. Si sobrevive el manual, hay que dejar sin efecto uno del portal, y
  **RF-23 lo prohíbe**. La regla firmada dice que un pago traído del portal no se borra.
- **¿Dónde queda registrado que eran el mismo?** RF-43 pide quién lo decidió y cuándo; hoy ninguna
  acción de la feature publica `ManualChangeRecorded` (eso es H-9, tarea 29).
- **¿Qué pasa si después llega un tercer comprobante idéntico?**

**Corrección:** el Backend-Architect cierra esas tres en `plan.md` y en `contracts/`, y recién
entonces la tarea 15 se puede escribir como tarea. Hoy es un enunciado.


> ✅ **Cerrado el 2026-08-31.** Decisión de arquitectura, sin volver al cliente: **sobrevive el pago
> del portal**, por `POST /payments/{id}/same-as`. Es la única salida que no rompe RF-23. El diseño
> está en `plan.md` → *Enfoque*, el contrato completo en `contracts/README.md`, y la tarea 15 pasó de
> enunciar el problema a describir la solución.
### A-3 · RF-41 y RF-52 no aparecen en ninguna parte del plan

**Documento a corregir:** `plan.md` · **Rol dueño:** Backend-Architect · **Bloquea `/implement`:** no.

Son los dos requisitos de H8 sobre la anticipación del aviso: que el dueño la defina (RF-41) y que
sean tres días mientras no la toque (RF-52). El plan **nunca los nombra** —ni en Contratos, ni en
Pantallas, ni en *Lo que corre solo*—, aunque sí menciona el parámetro `receipt.notice_days` y su
proyección.

Están construidos, y lo verifiqué: el parámetro existe en el catálogo con `initial=3` y
`consumed_by="purchases"`, y el panel del 003 es genérico sobre el catálogo, así que el dueño ya lo
cambia desde una pantalla que existe. **El problema es de trazabilidad, no de alcance**: el Tester y
`/converge` no tienen dónde ir a buscar la evidencia, y un requisito que el plan no nombra es un
requisito que nadie va a verificar.

**Corrección:** dos líneas en el plan, diciendo que la superficie de RF-41 es el panel de parámetros
de la 003 y que RF-52 lo fija el `initial` del catálogo.


> ✅ **Cerrado el 2026-08-31.** El plan dice ahora que RF-52 lo fija el `initial=3` del catálogo y
> que la superficie de RF-41 es el panel de parámetros de la 003, que se dibuja solo desde el
> catálogo. No había código que escribir: había un requisito que nadie podía encontrar.
### A-4 · El alcance de la tarea 17 excede la feature, y eso es una decisión de orquestación

**Documento a corregir:** ninguno todavía · **Rol dueño:** **Lead**, con el humano · **Bloquea
`/implement`:** sí, para la tarea 17.

La brecha del Artículo II de A-1 **no es de la 005**. Verificado contra el código: cinco
normalizaciones publican su evento de cuarentena —precios, historial, facturas, órdenes, ventas— y la
de pagos no; pero **de esas cinco, sólo las dos de precios tienen suscriptor**. Arreglarlo sólo acá
—publicando `PaymentRowsQuarantined` sin que nadie lo escuche— no cambiaría nada para nadie.

Es la misma brecha en 004, 007 y 009. La decisión que hay que tomar antes de escribir código:

- ¿es **una feature transversal propia**, con su spec y su número, que cierra la cuarentena muda de
  las cinco normalizaciones y su llegada a `operations.exception`?
- ¿o se hace **por feature**, aceptando que hasta que estén las cuatro nadie se entera de nada?

La tarea 17 ya dice *"confirmar el alcance con el Lead antes de empezar"*. Esta es la confirmación
que falta, y la elevo al humano porque implica abrir —o no— una spec nueva.


> ✅ **Cerrado el 2026-08-31.** El humano decidió que el trabajo vive en **una feature transversal
> propia, la 011**, que todavía no tiene spec. Las tareas 17 y 18 se retiran del alcance de la 005 y
> quedan marcadas ↗️; **RF-08 sigue siendo alcance firmado de esta spec**, así que el gate de la 005
> queda condicionado a que la 011 cierre. **La spec de la 011 se escribió y se firmó el 2026-08-31**
> (`011-set-aside-visibility`, 23 requisitos): lo próximo para ella es `/plan`.
### A-5 · H8 de esta feature depende de infraestructura que el plan adjudica a la 007

**Documento a corregir:** `plan.md` (una nota) · **Rol dueño:** Backend-Architect · **Bloquea
`/implement`:** no.

El plan declara que `notifications` no agrega ninguna tabla porque **reusa `notification_recipient`,
`notification_route` y la ventana horaria que construyó la 007**. Mientras las seis specs se entreguen
juntas es inofensivo. Deja de serlo en dos escenarios que hoy están abiertos:

- si la **007 se difiere** o se saca del changeset, RF-38 de la 005 se cae sin que nada en el plan de
  la 005 lo anuncie;
- si hay que **partir la migración `0011`**, que el propio plan lista como riesgo, porque hoy crea
  las tablas de cuatro features juntas.

**Corrección:** una línea en *Módulos afectados* diciendo que H8 no es autónoma. No cambia código;
cambia lo que el Release-Manager sabe antes de decidir qué entra al merge.


> ✅ **Cerrado el 2026-08-31.** El plan lo dice en *Módulos afectados*: si la 007 se difiere o hay
> que partir la migración `0011`, **RF-38 se cae**. Es información para el Release-Manager antes del
> merge, no trabajo para el Developer.
### A-6 · Las dos tablas de trazabilidad pueden separarse

**Documento a corregir:** ninguno hoy · **Rol dueño:** Backend-Architect · **Bloquea `/implement`:** no.

`plan.md` mapea requisitos a rutas y a pantallas en dos tablas, y `tasks.md` los mapea a tareas y
tests en otra. Hoy coinciden —lo verifiqué requisito por requisito—, pero son tres tablas que hay que
actualizar a mano cada vez que se cierra un hallazgo. La primera que quede vieja va a mentir con la
autoridad de un documento interno.

Es una observación, no una corrección: la registro para que la próxima corrida de `/analyze` empiece
por ahí.


> ✅ **Cerrado el 2026-08-31.** El plan declara ahora cuál manda: él mapea requisitos a rutas y
> pantallas, `tasks.md` los mapea a tareas y tests, y **si alguna vez se contradicen gana la de
> `tasks.md`**, que es la que `/converge` recorre.
## Qué le pasa a la cadena

**Actualizado el 2026-08-31, con los seis hallazgos cerrados.** Ya no hay ninguna tarea esperando una
decisión: las que dependían de una la tienen. Lo que queda es trabajo.

- **La tarea 15 (RF-43) se puede empezar**: tiene diseño y contrato.
- **Las tareas 17 y 18 se fueron a la 011**, que hay que specificar antes de construir.
- **El gate de calidad de la 005 sigue cerrado** hasta que la 011 cierre, porque el Artículo II está
  declarado incumplido y sin excepción. No es un bloqueo nuevo: es el que antes estaba sin escribir.

Lo que sigue valiendo de la corrida original:

Lo que **sí** puede avanzar sin esperar nada, porque no depende de ningún hallazgo de este documento:
las 23 tareas pendientes restantes, empezando por las dos pantallas que faltan —la tarea 58
(repartos) y la 63 (incidentes)—, que tienen su backend entero, sus Server Actions escritas y ninguna
ambigüedad de diseño.

## Preguntas elevadas al humano — contestadas el 2026-08-31

| Pregunta | Respuesta |
|---|---|
| ¿Se aprueba la excepción al Artículo II o es trabajo bloqueante? (A-1) | **Trabajo bloqueante.** Sin excepción |
| ¿Feature transversal para la cuarentena muda, o por feature? (A-4) | **Feature transversal propia: la 011** |
| En RF-43, ¿cuál de los dos pagos sobrevive? (A-2) | **El del portal.** No hizo falta elevarla: es la única salida que no rompe RF-23, así que la cerró el arquitecto |

**Nada quedó abierto.** La última pregunta también se contestó el 2026-08-31: **la 011 se especifica
después de bajar las tareas pendientes** de la 005 y la 006, no ahora.

> **Qué implica esa secuencia, dicho antes de que sorprenda.** El gate de calidad de la 005 depende de
> que la 011 cierre, así que **la 005 no se puede entregar antes que la 011**: postergar la 011
> posterga el cierre de la 005, no lo adelanta. Y mientras tanto el Artículo II sigue incumplido —una
> fila ilegible del estado de cuenta no llega a nadie— durante todo el tiempo que tomen las 47 tareas
> pendientes. Es una decisión legítima y está tomada; queda escrita para que nadie la descubra el día
> del merge.
