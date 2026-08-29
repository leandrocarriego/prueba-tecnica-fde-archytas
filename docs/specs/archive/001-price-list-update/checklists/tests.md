# Actualización de la lista de precios — Hallazgos de la suite

<!-- ARTEFACTO INTERNO. Hallazgos que dejó `add_tests`. Los registra el Lead; los resuelve el rol dueño. -->

**Feature:** 001-price-list-update · **Ejecutado:** 2026-08-29 · **Rol:** Tester, registrado por el Lead

## Veredicto: **la suite pasa** — dos preguntas para la spec y un hallazgo menor de código

> **Actualización del 2026-08-29.** Las dos preguntas **están decididas por el cliente** y aplicadas:
> H1 y H2 entraron a la spec como **RF-41, RF-42 y RF-43**, con su código y sus tests, y **H3 se
> cerró borrando los dos métodos muertos**. La suite quedó en **411 en verde con 95,57% de
> cobertura**, `mypy` limpio y `ruff` sin hallazgos. **No queda ningún hallazgo abierto.**

Las 49 tareas quedaron cubiertas y no hay ningún test en rojo ni ningún `xfail`. Lo que sigue no
son fallas: son **dos casos borde que la spec firmada no define**, y por eso la suite no los fija.
La regla del rol es explícita —*"si la spec no dice qué pasa en un caso borde, escalás al
`Solution-Designer` en vez de inventar el comportamiento esperado"*—, así que acá quedan escritos
con lo que hoy hace el sistema, verificado, y con la decisión que hace falta.

**Ninguno se resuelve con `/clarify`.** Esa skill exige que la spec **no** esté en `Estado:
Aprobado`: después de la firma, un cambio de alcance es una spec nueva, no una aclaración
(`agents/skills/clarify.md`). La decisión de por dónde va cada uno es del `Solution-Designer` con
el cliente.

## Lo que se verificó y pasa

| Chequeo | Resultado |
|---|---|
| Suite completa | 407 tests en verde (147 unit · 258 integración · 4 e2e · 89 portal · 7 slow) |
| Cobertura (`TEST-05`, umbral 80%) | 95.29% |
| Tests de arquitectura | 62/62, sin debilitar |
| `TEST-03` — parsers contra archivos fijados | sí: ningún test abre un navegador ni toca SIGProv |
| Corolario de `TEST-03` — corre con el portal y RabbitMQ apagados | sí: ninguna task se encola de verdad |
| `TEST-04` — idempotencia de cada task nueva | las cuatro, por su cuerpo async |
| `xfail` pendientes | ninguno |
| Archivos modificados fuera de `backend/tests/` | ninguno |

## Hallazgos

### H1 · Un archivo del día vacío inunda la cola y la corrida dice que salió bien — ✅ **resuelto**

> **Decisión del cliente (2026-08-29): hay que verificar si el archivo del día está vacío.** Una
> lista sin una sola fila de datos es **una consulta que falló**, no cien productos que
> desaparecieron: se registra como fallida con su motivo (**RF-41**) y no señala a nadie como
> faltante (**RF-42**). Toma el mismo camino que cualquier otra falla de extracción, así que la
> pantalla lo muestra (RF-11) y el aviso al dueño sale por donde ya salía (RF-12).
>
> **Aplicado en** `ingestion/parsers.py` (`parse_price_list` levanta `ExtractionError` cuando no
> queda ninguna fila), con dos tests unitarios y dos de integración —`test_an_empty_list_is_a_failed_consultation`
> y `test_an_empty_list_flags_nobody_as_missing`—.
>
> **Consecuencia que conviene saber**: como el handler corre en la transacción del publicador
> (Artículo IV), la corrida se deshace entera y **el archivo vacío no queda en `raw`**. Es lo mismo
> que ya pasaba con cualquier consulta fallida, no una excepción nueva.

<details><summary>El hallazgo original</summary>

**decide: Solution-Designer**

**Qué pasa hoy, verificado.** Si el portal entrega un archivo con estructura válida y **cero filas
de datos** (sólo los encabezados), el parser devuelve cero filas —lo cual es correcto: no hay nada
que interpretar—, ningún producto conocido "vino en la lista", y `catalog` hace exactamente lo que
la spec le pide: conserva el último precio de cada uno (RF-08) y los señala para revisión (RF-28).
Con el padrón cargado eso son **100 casos pendientes de una sola corrida**, y los 100 precios
marcados como no vigentes.

**Por qué no es un bug.** Cada requisito involucrado se cumple al pie de la letra, y la regla de
negocio firmada dice que ante un producto que dejó de aparecer el sistema *aparta y avisa*, nunca
decide solo. El sistema está haciendo lo que se acordó.

**Por qué igual importa.** La corrida se cierra como **exitosa**, así que la detección de
interrupción de RF-11 y RF-12 no se entera: una exportación rota del proveedor se ve, desde la
pantalla, igual que un día en que no cambió ningún precio. El aviso al dueño no sale, y lo que
queda es una cola de 100 casos que nadie pidió.

**Qué hay que decidir.** Si una lista sin filas es *una lista* o *una consulta fallida*. Si es lo
segundo, es un requisito nuevo —del tipo *"Si la lista obtenida no trae ninguna fila, entonces el
sistema debe tratar la consulta como fallida"*— y entra por una spec nueva o por un cambio firmado
de esta, no por una aclaración.

**Cómo reproducirlo.** Primera corrida con `price-list-2026-08-28.xlsx`; segunda con un `.xlsx` de
los mismos encabezados y ninguna fila. Medido: la corrida queda `SUCCEEDED` con resultado
`{updated: 0, unchanged: 0, highlighted: 0, quarantined: 0}`, 100 casos pendientes y
`is_stalled: false`.

**Un dato que puede servir para resolverlo.** El resultado de esa corrida es la anomalía escrita:
una actualización exitosa que no tocó **ni un solo** precio, ni siquiera para dejarlo igual. Hoy
nadie lee ese número; es el lugar más barato donde apoyar la decisión, sea cual sea.

</details>

### H2 · Un historial publicado vacío se trata como falla técnica — ✅ **resuelto**

> **Decisión del cliente (2026-08-29): un producto sin historial no es un error.** La importación
> termina sin puntos y sin ruido (**RF-43**), y el precio vigente del producto no se toca. Lo que
> sigue siendo falla técnica es que la pantalla **no tenga** la tabla: eso significa que el portal
> cambió.
>
> **Verificado antes de decidir**, como pedía el hallazgo: se recorrieron 25 productos del portal el
> 2026-08-29 y todos publican entre 1 y 11 puntos. **El caso no ocurre hoy**; la regla es defensiva.
>
> **Aplicado en** `ingestion/parsers.py`: `_TableRows` ahora distingue *tabla ausente* de *tabla sin
> filas*, con el test `test_a_table_that_publishes_no_price_is_not_a_failure`.

<details><summary>El hallazgo original</summary>

**decide: Solution-Designer**

**Qué pasa hoy, verificado.** `parse_product_history` levanta `ExtractionError` cuando la pantalla
no tiene **ninguna** fila de precios, sin distinguir dos situaciones distintas: que el portal haya
cambiado la estructura —donde el error es lo correcto, y así lo pide `add_integration`— y que el
producto simplemente no tenga historial publicado. En el segundo caso la task reintenta dos veces,
se rinde y deja **sólo una línea de log**: no hay punto, no hay caso en la cola de revisión, y no
hay `JobRun` propio, porque la visita al historial es consecuencia de registrar un producto y no
una corrida que alguien pidió (así lo decidió `plan.md`).

**Por qué no es un bug contra la spec.** RF-39 habla del historial que *no se puede interpretar*,
que no es lo mismo que un historial que no existe. La spec no dice qué es un producto sin
historial publicado.

**Por qué igual importa.** Es la única situación de la feature donde algo queda sin resolver y **no
aparece en ninguna pantalla**, que es justo lo que el Artículo II prohíbe. Además el parser de la
lista y el del historial se contradicen: uno tolera cero filas y el otro las trata como falla.

**Qué tan probable es.** Poco, hoy: el brief mide *"entre 2 y 11 puntos cada uno"* para los cien
productos, así que un historial vacío no se observó nunca en el portal. Es un caso defensivo, y
conviene confirmarlo con `/portal` antes de gastar una decisión del cliente en él.

**Qué hay que decidir.** Si un producto sin historial publicado es un hecho normal —y entonces la
importación termina sin puntos y sin ruido— o una anomalía que tiene que quedar en la cola de
revisión con su motivo.

</details>

### H3 · Dos métodos de repositorio sin llamadores — ✅ **resuelto**

> **Borrados el 2026-08-29.** De las dos salidas que ofrecía el hallazgo, se tomó la segunda: no
> tenían consumidor previsto —ni una pantalla, ni el reproceso, que lee `raw` y no `staging`—, así
> que se fueron los dos métodos y el import de `RowStatus` que sólo ellos usaban. Si mañana aparece
> quien los necesite, son tres líneas. La suite sigue en **411 en verde** y la cobertura **subió a
> 95,57%**, que es lo que pasa cuando lo que se borra es código muerto y no un test.

`rows_of_batch` y `history_rows_of_product`, en `app/modules/ingestion/repository.py`, no los usaba
nadie: ni `app/`, ni la suite. No se testearon a propósito —cubrir código muerto para levantar el
número de cobertura es el instinto exactamente equivocado—. O tienen un consumidor previsto que
todavía no llegó, y entonces vale un comentario que lo diga, o se borran.

## Qué se hace con esto

| Hallazgo | Rol | Camino |
|---|---|---|
| H1 | Solution-Designer | ✅ **Cerrado el 2026-08-29.** El cliente decidió que sí es una consulta fallida. Entró como **cambio firmado de esta spec** (RF-41, RF-42), no como spec nueva |
| H2 | Solution-Designer | ✅ **Cerrado el 2026-08-29.** Confirmado con el portal que el caso no ocurre; el cliente decidió que es un hecho normal (RF-43), no una excepción para la cola |
| H3 | Developer | ✅ **Cerrado el 2026-08-29.** Los dos métodos se borraron; no había consumidor previsto |

Ninguno de los tres frenaba el gate de calidad ni el `/converge`: el código implementaba lo que se
firmó, y estas eran preguntas sobre lo que **no** se firmó. Con H1 y H2 decididos, ahora también
están firmadas.
