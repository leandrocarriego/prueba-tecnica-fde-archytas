# Constitución — Plataforma Cordillera

Los principios **no negociables** del proyecto. Es la autoridad número uno: cuando este
documento y cualquier otro se contradicen, gana este.

Es deliberadamente corto. No repite la arquitectura (`ARCHITECTURE.md`), las reglas operativas
(`AGENTS.md`) ni las convenciones de código (`CONVENTIONS.md`): contiene sólo lo que **ningún
plan, ninguna feature y ninguna urgencia pueden violar**. Si una regla admite excepciones
razonables, no pertenece acá.

**Versión** 2.0.0 · **Ratificada** 2026-08-28 · **Última reforma** 2026-08-28 (Artículo IV)

---

## Artículo I — El origen es ajeno y de solo lectura

SIGProv no es nuestro, no tiene API y no se escribe. Toda operación de escritura vive en
nuestra base de datos.

La extracción es **automatización de navegador**. El portal expone endpoints JSON internos:
**no se usan**. Se lo trata como el sistema viejo sin integración que representa, y se lee de la
pantalla renderizada.

*Por qué es no negociable:* usar esos endpoints haría que el sistema dependiera de un contrato
que nadie nos prometió y que puede desaparecer sin aviso. Y una escritura contra un sistema de
un tercero, con una cuenta compartida, es un riesgo que no nos corresponde tomar.

## Artículo II — Nada se descarta

Un dato que no se puede interpretar **no se pierde y no rompe la ingesta**: va a cuarentena y
genera una excepción para revisión humana.

Cada decisión humana sobre una excepción se guarda como regla reutilizable. La limpieza de
datos es una función visible del producto, no un detalle del pipeline.

*Por qué es no negociable:* el pedido del cliente lo dice dos veces con sus palabras —"que si
algo no se puede resolver solo, nos avise". Un sistema que descarta en silencio le miente a
quien lo mira.

## Artículo III — El flujo de datos es unidireccional, y `raw` es inmutable

`raw` → `staging` → `core`. En un solo sentido.

`raw` guarda lo extraído tal cual llegó, con su hash, y **nunca se sobrescribe ni se corrige**.
Toda corrección ocurre en la transformación hacia `staging`, y por lo tanto es reproducible: se
puede reconstruir el estado desde el origen sin volver a extraer.

*Por qué es no negociable:* si se puede editar `raw`, se pierde la única evidencia de qué dijo
el portal, y ninguna diferencia con el origen vuelve a ser explicable.

## Artículo IV — Las fronteras entre módulos son reales o no existen

Un módulo **nunca importa otro módulo**. Se comunican publicando **eventos de dominio**.

Todo lo que hay dentro de un módulo es privado, su `service.py` incluido. Lo que un módulo
necesita contarle al resto del negocio es un hecho consumado —un evento en pasado, inmutable,
que lleva identificadores y no entidades— y quien lo necesite se suscribe sin que el emisor se
entere. El catálogo de eventos es vocabulario compartido y no pertenece a ningún módulo.

La única excepción es la **autorización HTTP**: una request tiene que saber si puede seguir
antes de que corra su handler, y un evento no responde eso a tiempo. Está acotada por nombre de
archivo en el test, y ampliarla exige editar el test a propósito.

Un handler corre en la transacción de quien publicó, y si falla, la aborta. Un evento no es un
lugar donde el trabajo desaparece en silencio (Artículo II).

Esta regla no se sostiene con disciplina ni con revisiones: está **verificada por un test que
rompe el build**. Cualquier principio de arquitectura que dependa sólo de que alguien lo lea es
una aspiración, no una regla.

Si respetar la frontera resulta incómodo, la frontera está mal trazada: se corrige la frontera,
nunca la regla.

*Por qué es no negociable:* es lo único que distingue un monolito modular de un monolito. Un
import cruzado es una dependencia de compilación sobre la forma interna de otro: mientras exista,
nadie puede renombrar un método sin romper código que no es suyo, y la modularidad es decorativa.

*Costo que se acepta a cambio:* una lectura sincrónica entre módulos deja de ser gratis. El módulo
que necesita datos ajenos mantiene su propia proyección alimentada por eventos. Cuando eso resulta
imposible, casi siempre significa que los dos módulos son en realidad uno.

## Artículo V — Spec primero, y con firma

Ninguna feature pasa a planificación técnica sin una `spec.md` **aprobada por el cliente**.

La spec es funcional y cara al cliente: no lleva decisiones técnicas. La planificación que
arranca antes de la firma resuelve un alcance que nadie acordó.

Al terminar, el código se verifica contra lo que se firmó (`/converge`), no sólo contra su
propia calidad. Si el código y la spec no describen el mismo producto, la decisión de qué
corregir —el código o el acuerdo— **es del humano, no del agente**.

*Por qué es no negociable:* es el único mecanismo que impide que el producto derive lejos de lo
que el cliente pidió, en un proceso donde la mayor parte del trabajo la hacen agentes.

## Artículo VI — Lo que no está tipado y testeado no está terminado

Todo el código lleva tipos completos y pasa sus chequeos. La lógica de negocio tiene tests
unitarios; los endpoints y la base, tests de integración; los parsers del portal se testean
contra HTML fijado, nunca contra el portal en vivo.

Un test **nunca** se debilita para pasar un gate. Si un test molesta, o el código está mal o el
test está mal: las dos cosas se arreglan, ninguna se silencia.

*Por qué es no negociable:* la extracción corre sin nadie mirando, de madrugada. Lo único que
avisa de una regresión es la suite.

## Artículo VII — Las credenciales de terceros viven solo en el entorno

Las credenciales del portal son de una cuenta compartida que no nos pertenece. Nunca en la base
de datos, nunca en el repositorio, nunca en un log, nunca en un traceback.

*Por qué es no negociable:* filtrarlas no compromete nuestro sistema, compromete el de otro.

## Artículo VIII — Un idioma para cada audiencia

La documentación va en **español**, porque se lee, se discute y se firma con el cliente y el
equipo. El código va en **inglés**. Los strings que ve el usuario, en español.

*Por qué es no negociable:* la spec es un documento contractual. Un documento que el cliente no
puede leer no puede ser firmado por el cliente.

## Artículo IX — Las dependencias entran por la puerta

Backend con `uv`, frontend con `npm`, y siempre con su lockfile actualizado en el mismo commit.
Nada de `pip install`, `requirements.txt`, ni edición a mano de versiones.

*Por qué es no negociable:* un build que no es reproducible no es verificable, y todo lo demás
que dice esta constitución depende de poder verificar.

---

## Constitution Check

Todo `plan.md` se valida contra esta constitución antes de pasar a `/tasks`. El plan declara
explícitamente:

- Que ningún artículo resulta violado por el enfoque elegido.
- Si algún artículo **parece** exigir una excepción: cuál, por qué, y qué alternativa se
  descartó. Una excepción a esta constitución no la aprueba un agente — la aprueba el humano, y
  queda registrada en el plan.

Un plan que no pasa el Constitution Check no avanza, aunque sea técnicamente correcto.

## Reforma

Esta constitución se modifica sólo con decisión humana explícita, y el cambio incluye:

1. Actualizar la versión y la fecha de este documento.
2. Revisar `ARCHITECTURE.md`, `AGENTS.md` y `CONVENTIONS.md` para que no la contradigan.
3. Cuando el artículo sea verificable por una prueba automática, actualizar o crear el test que
   lo verifica — un artículo nuevo que dependa sólo de la lectura nace debilitado.

## Versionado

`MAJOR` — se elimina o se redefine un artículo · `MINOR` — se agrega un artículo o una
obligación material · `PATCH` — redacción, ejemplos, aclaraciones que no cambian el alcance.

## Dónde vive este documento

En la raíz, junto al resto de la gobernanza, y la carga `AGENTS.md` con un import para que esté
siempre en contexto.

GitHub Spec Kit —que inspiró el flujo SDD de este repositorio— esperaría la constitución en
`.specify/memory/constitution.md`. **No se instaló**, y por eso este archivo se queda donde una
persona lo busca. La razón es la misma por la que `AGENTS.md` no vive dentro de `.claude/`: la
autoridad del proyecto no se guarda en la carpeta de una herramienta que se puede cambiar.
