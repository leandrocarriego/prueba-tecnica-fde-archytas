# Recorrido a mano — 012, tareas 13, 21, 30 y 43

**Corrido el 2026-09-01** contra el stack local: Postgres y RabbitMQ en Docker, el backend nativo
en `:8000` y el frontend **en su build de producción** en `:3100`.

Cuatro tareas de la 012 no se pueden fijar con un test: son los recorridos de cierre de cada ola.
Lo que un test de render puede afirmar es que un elemento existe; lo que hace falta saber acá es
si **la misma señal se dibuja igual en tres pantallas distintas**, si una columna de números queda
en columna, y si una pantalla que nadie monta en un test sigue renderizando después de que se le
cambió la forma a los cuarenta archivos que la componen.

Se recorre con el **sistema operativo en modo oscuro** (`color_scheme="dark"` en Chromium), que es
lo que `RF-20` pide probar: la plataforma tiene un solo tema y es el claro.

**Contra el build y no contra `next dev`**, a propósito. El servidor de desarrollo instrumenta los
componentes por su cuenta y sobre `/ventas` —que redirige apenas se monta— emite
`Failed to execute 'measure' on 'Performance': 'SalesRoot' cannot have a negative time stamp`. Se
verificó que **no existe en el build**: en `:3100` la misma ruta redirige a `/ventas/revision` sin
un solo error de página, cinco veces seguidas. Un recorrido no debería anotar como defecto del
producto algo que sólo hace la herramienta con la que se lo mira.

## Cómo se repite

```bash
make dev                                             # Postgres y RabbitMQ
cd backend && uv run uvicorn app.main:app --port 8000 &
cd frontend && npm run build && npx next start -p 3100 &
docker exec -i cordillera_postgres psql -U cordillera -d cordillera \
  < docs/specs/012-design-system/evidence/datos-del-recorrido.sql
cd backend && uv run python ../docs/specs/012-design-system/evidence/recorrido.py
```

`recorrido.py` emite su propia invitación para el acceso de Ventas —la aplicación manda el enlace
por WhatsApp y guarda sólo su hash, que es lo correcto— y recorre con **dos accesos**: uno de dueño
y uno de Ventas. Con uno solo, `RF-17`, `RF-18` y `RF-22` pasan por omisión sin probar nada.

`datos-del-recorrido.sql` es el juego de datos, todo con el prefijo `T012`: un proveedor con dos
grafías, tres facturas —una vencida sin recibo, una parcial de siete dígitos y una de cuatro—, sus
pagos, el vencimiento que lleva la vencida al calendario, dos ventas apartadas, dos productos y
tres pendientes de revisión. Sin eso, media pantalla se ve en su cara vacía y el recorrido no
prueba nada.

## Lo que se verificó

**100 verificaciones, 100 en verde.** El detalle línea por línea está en `recorrido.txt`.

| Requisito | Resultado | Evidencia |
|---|---|---|
| `RF-01`, `RF-02` · las dieciséis secciones, Mi cuenta y las de sesión, sobre el mismo papel | ✅ las 17 rutas renderizan y las 17 dan `rgb(244, 242, 237)` de fondo | `rf01-*.png` |
| `RF-03` · la barra lista las dieciséis secciones | ✅ | `rf01-tablero.png` |
| `RF-04` · el nombre de quien trabaja y la salida | ✅ con los dos accesos | `rf17-el-menu-de-ventas.png` |
| `RF-05` · las pantallas de sesión con la misma identidad | ✅ ingreso, invitación e invitación guardada, recuperación | `rf05-*.png` |
| `RF-06` · **la misma píldora en tres pantallas** | ✅ «Venció sin recibo» da el mismo trío en `/facturas`, `/calendario` y la ficha: texto `rgb(163,43,30)`, fondo `rgb(251,234,231)`, borde `rgb(239,206,200)` | `rf06-*.png` |
| `RF-08` · lo no confirmado se distingue sin leer la etiqueta | ✅ de las dos grafías del proveedor, sólo la que reconoció el sistema va punteada | `rf08-lo-no-confirmado.png` |
| `RF-09`, `RF-10` · la plata en columna | ✅ cifras de 7 y de 11 caracteres, todas terminando en la misma vertical (x = 943), en IBM Plex Mono | `rf06-facturas.png` |
| `RF-11` · como mucho un naranja por pantalla | ✅ en las 17; los que hay son «Actualizar ahora», «Agregar», «Dar de alta e invitar», «Cambiar la clave», «Registrar pago» | — |
| `RF-13` · el color de enlace no modifica datos | ✅ ningún botón que guarda, corrige o borra sale en azul, en las cinco pantallas de plata y en las nueve de decisión | — |
| `RF-17`, `RF-18`, `RF-22` · el menú con un acceso de Ventas | ✅ nueve entradas, sin Facturas, Órdenes, Accesos ni Parámetros; ningún título de grupo sin entradas debajo | `rf17-el-menu-de-ventas.png` |
| `RF-20` · un solo tema, con el SO en oscuro | ✅ en las 17 pantallas y en las de sesión | todas |
| `RF-21` · cero naranja donde se decide | ✅ en las nueve rutas, **con datos en las nueve** | `rf21-una-pantalla-de-decision.png` |
| `RF-24` · al entrar se cae en el tablero | ✅ `/` termina en `/tablero` | `rf24-la-raiz-cae-en-el-tablero.png` |
| ninguna pantalla se rompe al renderizar | ✅ cero errores de página en el recorrido completo | — |

## Lo que encontró, y que las aserciones no veían

Los dos defectos que siguen no los encontró ninguna afirmación del recorrido: los encontró
**mirar la captura**. Los dos están corregidos, y el recorrido se volvió a correr entero después.

### D-1 · la fila de facturas decía dos veces lo mismo

`InvoiceTable` sacaba de las advertencias la que la píldora ya dice, comparando el texto completo
contra `'Venció sin recibo'`. La advertencia que escribe `warningsFor` es **«Venció sin recibo de
recepción»**, así que la comparación no coincidía nunca: la fila mostraba la píldora roja y,
debajo, la misma frase en ámbar. Ahora se filtra por el comienzo del texto, que es lo que hace que
la coincidencia no dependa de cómo esté redactada la advertencia.

### D-2 · «PagadoEstado»

Las celdas de la tabla de facturas llevaban `py-2` y ningún aire horizontal, así que la columna
`Pagado` —alineada a la derecha— quedaba pegada a `Estado` y el encabezado se leía «PagadoEstado».
Es exactamente lo que `UI-08` gobierna. Se le dio `px-3` a las celdas, sin aire en la primera ni en
la última para que la tabla siga alineada con el resto de la pantalla. Al hacerlo, el número de
factura pasó a partirse en dos renglones: un código se compara de un vistazo, así que lleva
`whitespace-nowrap`.

## Tres afirmaciones del recorrido que estaban mal, y el producto bien

Vale anotarlas porque la primera corrida las dio en rojo, y las tres eran del guion:

1. **La píldora del calendario.** Se leía la página antes de que terminara de repintar el mes
   anterior. Se espera a que la ventana nueva esté en la URL.
2. **«y 2 más en este día» en azul.** El recorrido marcaba *todo* botón dibujado en azul de dato.
   `RF-13` no dice eso: dice que el azul no puede estar sobre lo que **modifica**. Abrir un día no
   modifica nada. Ahora se reconoce por el verbo con el que la pantalla nombra la acción.
3. **«Compras» sin título con un acceso de Ventas.** Era una suposición sobre el mapa de permisos
   que reparte el backend, y es falsa: un acceso de Ventas alcanza el calendario, así que el grupo
   Compras tiene una entrada y su título corresponde. `RF-18` se afirma ahora como lo que es —
   ningún título sin entradas debajo—, y el caso en que un grupo queda entero afuera lo fija el
   test de render de la tarea 12, que puede pedir el mapa de permisos que quiera.

## Observaciones que no son de esta feature

Ninguna es un defecto de la 012 y ninguna se tocó, porque el traspaso dice que esta feature no
cambia el contenido de ninguna pantalla. Van para el `Lead`:

- **Plurales de uno.** «1 ventas sumadas», «1 registros excluidos», «1 ventas apartadas esperan una
  decisión», «1 en revisión quedaron afuera». Son de las features 004 y 009. El aviso que la 012 sí
  agregó al tablero está en singular cuando corresponde («Este total deja 1 registro afuera»), así
  que la asimetría se nota más ahora que antes.
- **El teléfono del proveedor no va en mono y el CUIT sí.** `RF-09` nombra importes, fechas y
  códigos; un teléfono es discutible, y la decisión es del `Solution-Designer`.
- **El anillo del día elegido en el calendario usa el acento.** Es una decisión escrita de la guía
  —«el foco también usa el acento, para que se vea sobre papel»— y no un botón, así que no gasta el
  presupuesto de `RF-21`. Queda dicho para que el `Code-Reviewer` lo confirme y no lo descubra.

## El entorno, y lo que quedó en él

- **La base local está en la revisión `0021`, que no existe en esta rama.** Llegó de otro lado y no
  se tocó: `alembic upgrade head` falla contra ella. La aplicación anda igual, pero **no es una base
  reproducible desde este árbol**, y eso conviene resolverlo antes de confiar en cualquier prueba
  que dependa del esquema.
- Quedaron en la base de desarrollo las filas del recorrido (prefijo `T012`) y un acceso de Ventas
  (`ventas@example.com`). Se borran con:

```sql
delete from operations.exception where fingerprint like 't012-%';
delete from core.product_price where product_id in (9001, 9002);
delete from core.product where id in (9001, 9002);
delete from core.receipt_incident where id = 9001;
delete from core.sale where id in (9001, 9002);
delete from core.supplier_alias where id in (9001, 9002);
delete from core.due_date where id = 9001;
delete from core.payment where id in (9001, 9002);
delete from core.invoice where id in (9001, 9002, 9003);
delete from core.supplier where id in (9001, 9002);
delete from users where email = 'ventas@example.com';
```

- Al dueño (`dueno@example.com`) se le puso una clave conocida para poder entrar. No es una
  credencial de terceros (Artículo VII): es el acceso a nuestra propia aplicación en la máquina de
  quien prueba, no está en el repositorio y conviene cambiarla.
