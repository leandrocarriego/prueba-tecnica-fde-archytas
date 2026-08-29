<!-- GENERADO por scripts/diagrams/export.sh — NO editar a mano.
     Fuente: los .mmd de esta carpeta. Regenerar: scripts/diagrams/export.sh -->

# Diagramas

> Vista renderizada de los diagramas de esta feature. Fuente: los `.mmd` de esta
> carpeta. Convención: `docs/specs/DIAGRAMS.md`. Las imágenes para el cliente se
> generan en `dist/diagramas/` con `make diagrams`.

## Ciclo de vida de una actualización de precios

```mermaid
---
title: Ciclo de vida de una actualización de precios
---
stateDiagram-v2
    state "Programada" as Programada
    state "En curso" as EnCurso
    state "No iniciada por superposición" as Rechazada
    state "Terminada con éxito" as Exitosa
    state "Fallida" as Fallida

    [*] --> Programada
    Programada --> EnCurso: llega el momento, o alguien la pide a mano
    Programada --> Rechazada: ya hay otra en curso
    EnCurso --> Exitosa: el portal respondió y se procesó la lista
    EnCurso --> Fallida: el portal no respondió
    Exitosa --> Programada: queda agendada la siguiente
    Fallida --> Programada: queda agendada la siguiente
    Rechazada --> [*]

    note right of Exitosa
        Es la que fecha la pantalla de precios.
        Si la pidió una persona, se le informa
        el resultado y queda registrado quién
        la pidió y cuándo
    end note

    note right of Fallida
        Se registra con su motivo. Recién cuando
        se acumulan dos consultas programadas
        seguidas sin una exitosa, el sistema lo
        señala en pantalla y avisa al dueño por
        WhatsApp, una sola vez por interrupción
    end note
```

## Qué le pasa a cada fila de la lista que llega del portal

```mermaid
---
title: Qué le pasa a cada fila de la lista que llega del portal
---
stateDiagram-v2
    state "Recibida del portal" as Recibida
    state "No se pudo interpretar" as Ilegible
    state "De un producto que el sistema no conoce" as Desconocida
    state "Apartada, esperando una decisión" as Apartada
    state "Resuelta por una persona" as Resuelta
    state "Precio vigente registrado" as Registrada
    state "Dejada fuera de la lista" as Descartada

    [*] --> Recibida
    Recibida --> Registrada: se entiende y el producto es conocido
    Recibida --> Ilegible: no se entiende lo que dice
    Recibida --> Desconocida: se entiende, pero el producto no está entre los conocidos
    Ilegible --> Apartada
    Desconocida --> Apartada
    Apartada --> Resuelta: una persona decide qué hacer con el caso
    Resuelta --> Registrada: la decisión le da un producto conocido y un precio
    Resuelta --> Descartada: la decisión lo deja fuera
    Registrada --> [*]
    Descartada --> [*]

    note right of Desconocida
        No ocurre con la primera lista: esa es
        la que establece cuáles son los
        productos conocidos
    end note

    note right of Apartada
        Visible con su motivo y contada, sin
        frenar al resto de las filas. Un caso
        igual que llegue después no agrega otro
        pendiente: se mantiene uno solo
    end note

    note right of Resuelta
        La decisión queda guardada como regla,
        con quién la tomó y cuándo. Los casos
        iguales que lleguen después se resuelven
        solos. Si esa regla se deja sin efecto,
        vuelven a quedar apartados
    end note
```

## Ciclo de vida del precio de un producto conocido

```mermaid
---
title: Ciclo de vida del precio de un producto conocido
---
stateDiagram-v2
    state "Sin precio todavía" as Sin
    state "Precio vigente" as Vigente
    state "Precio vigente, destacado por suba" as Destacado
    state "Último precio conservado y señalado" as Conservado

    [*] --> Sin
    Sin --> Vigente: la primera lista trae su precio
    Vigente --> Vigente: la lista lo trae con el mismo precio
    Vigente --> Destacado: subió más que el porcentaje definido
    Destacado --> Vigente: la actualización siguiente no supera el porcentaje
    Vigente --> Conservado: deja de figurar en la lista
    Destacado --> Conservado: deja de figurar en la lista
    Conservado --> Vigente: vuelve a figurar en la lista

    note right of Vigente
        Cada vez que el precio cambia se agrega
        un punto a su historial, con su fecha.
        Al registrarse por primera vez también
        se suma el historial que el portal ya
        publicaba para ese producto
    end note

    note right of Conservado
        El sistema nunca da de baja un producto
        por su cuenta: conserva el último precio
        conocido y lo señala para que lo revise
        una persona
    end note
```

## El dueño — qué puede hacer y qué ve

```mermaid
---
title: El dueño — qué puede hacer y qué ve
---
flowchart TD
    A["El dueño abre la aplicación"] --> B["Pantalla de precios"]
    B --> C["La fecha y la hora de la última actualización que terminó con éxito"]
    B --> D["Los productos que subieron más que el porcentaje que él definió, destacados"]
    B --> E["El aviso visible cuando la actualización lleva dos consultas seguidas sin funcionar"]

    A --> F["Ajusta los dos parámetros de la actualización"]
    F --> G["Cada cuánto se consulta el portal"]
    F --> H["A partir de qué porcentaje de suba se destaca un producto"]
    G --> I["La frecuencia nueva rige desde la consulta siguiente"]
    H --> J["Cambia qué productos quedan destacados"]
    F --> K["Mientras no cambie un parámetro rige su valor inicial: cada 12 horas y subas mayores al 10%"]

    A --> L["Puede pedir la lista a mano, sin esperar a la próxima consulta"]

    M["La actualización lleva dos consultas seguidas sin éxito"] --> N["Le llega un aviso por WhatsApp"]
    N --> O["Mientras la causa siga siendo la misma, no se repite"]
```

## Actualización de la lista de precios — de punta a punta

```mermaid
---
title: Actualización de la lista de precios — de punta a punta
---
sequenceDiagram
    autonumber
    actor Duenio as El dueño
    participant Sistema as El sistema
    participant Portal as Portal del proveedor
    actor Marcela as Marcela, compras
    actor Julian as Julián, ventas

    Duenio->>Sistema: Define cada cuánto se consulta y qué suba se destaca
    Note over Sistema: Mientras no los cambie rigen los valores iniciales:<br/>cada 12 horas y toda suba mayor al 10%

    loop Con la frecuencia configurada
        Sistema->>Portal: Entra por su cuenta y pide la lista de precios del día
        alt El portal responde
            Portal-->>Sistema: La lista publicada
            Sistema->>Sistema: Conserva la lista tal como llegó
            Sistema->>Sistema: Actualiza el precio de cada producto conocido
            Sistema->>Portal: De cada producto nuevo para él, trae el historial ya publicado
            Sistema->>Sistema: Aparta lo que no entiende y lo que no conoce
            Sistema->>Sistema: Señala los productos conocidos que no vinieron
            Sistema->>Sistema: Destaca las subas por encima del porcentaje definido
        else El portal no responde
            Sistema->>Sistema: Registra el fallo con su motivo
            Note over Sistema: Recién tras dos consultas seguidas sin éxito
            Sistema-->>Duenio: Avisa por WhatsApp, una sola vez por interrupción
        end
    end

    Duenio->>Sistema: Mira cuándo fue la última actualización que salió bien
    Marcela->>Sistema: Necesita el precio ahora y pide la lista a mano
    Sistema-->>Marcela: Le informa si la trajo o si falló
    Marcela->>Sistema: Revisa lo apartado y decide qué hacer con cada caso
    Sistema->>Sistema: Guarda la decisión como regla y deja de apartar los casos iguales
    Julian->>Sistema: Abre un producto
    Sistema-->>Julian: Su evolución en el tiempo y la variación contra el mes anterior
```

## Julián, ventas — qué puede hacer y qué ve

```mermaid
---
title: Julián, ventas — qué puede hacer y qué ve
---
flowchart TD
    A["Julián quiere entender qué se está encareciendo"] --> B["Abre la lista de precios vigente"]
    B --> C["Abre un producto"]
    C --> D["Ve la evolución de su precio en el tiempo"]
    D --> E["Un punto por cada vez que el precio cambió, con su fecha"]
    E --> H["Desde el primer día incluye el historial que el portal ya tenía publicado"]
    C --> F["Ve la variación entre el precio vigente y el último precio del mes calendario anterior"]
    B --> G["Ve destacados los productos que subieron más que el porcentaje que definió el dueño"]
```

## Marcela, compras — qué puede hacer y qué ve

```mermaid
---
title: Marcela, compras — qué puede hacer y qué ve
---
flowchart TD
    A["Marcela tiene que controlar lo que le facturan"] --> B["Abre la lista de precios vigente"]
    B --> C["Ve el código, la descripción y el precio de cada producto"]
    C --> D{"¿El precio está actualizado al momento que ella necesita?"}
    D -->|Sí| E["Controla la factura contra ese precio"]
    D -->|No| F["Pide la actualización a mano"]

    F --> G{"¿Ya hay una actualización en curso?"}
    G -->|Sí| H["El sistema le informa que ya hay una en curso y no inicia otra"]
    G -->|No| I["El sistema entra al portal y trae la lista, y queda registrado que la pidió ella"]
    I --> J["Al terminar le informa si trajo la lista o si falló"]
    H --> C
    J --> C

    A --> K["Revisa lo que el sistema apartó"]
    K --> L{"¿Por qué se apartó este caso?"}
    L -->|No se pudo interpretar la fila| M["Señala a qué producto conocido corresponde y con qué precio"]
    L -->|Es un producto que el sistema no conoce| N["Decide si lo incorpora a los conocidos o lo deja fuera"]
    L -->|Es un conocido que dejó de figurar| O["Decide si lo da por discontinuado o lo mantiene vigente"]

    M --> P["El caso queda resuelto y sale de los pendientes"]
    N --> P
    O --> P
    P --> Q["La decisión queda guardada como regla, con su nombre y la fecha"]
    Q --> R["Los casos iguales que lleguen después se resuelven solos, sin volver a apartarse"]
    R --> S{"¿La regla estaba equivocada?"}
    S -->|Sí| T["La deja sin efecto y esos casos vuelven a la pantalla de revisión"]
    S -->|No| U["La pantalla de revisión se mantiene vacía"]
    T --> K
```

## El sistema — qué hace en cada consulta al portal

```mermaid
---
title: El sistema — qué hace en cada consulta al portal
---
flowchart TD
    A["Llega el momento de consultar, según la frecuencia configurada"] --> B["Entrar al portal y pedir la lista del día"]
    B --> C{"¿El portal respondió?"}

    C -->|No| D["Registrar el fallo junto con su motivo"]
    D --> E{"¿Van dos consultas programadas seguidas sin éxito?"}
    E -->|Sí| F["Señalarlo en la pantalla de precios y avisar al dueño por WhatsApp, una sola vez"]
    E -->|No| Z["Esperar a la próxima consulta"]
    F --> Z

    C -->|Sí| G["Conservar la lista tal como llegó del portal"]
    G --> H{"¿Es la primera lista que obtiene el sistema?"}
    H -->|Sí| I["Registrar como productos conocidos todos los que figuran en ella"]
    H -->|No| J["Recorrer la lista fila por fila"]
    I --> I2["Por cada producto recién conocido, traer del portal el historial que ya publica"]
    I2 --> I3{"¿Se pudo leer ese historial?"}
    I3 -->|Sí| I4["Sumarlo a su evolución, sin repetir un precio que ya estaba"]
    I3 -->|No| I5["Apartarlo para revisión, sin perder el precio vigente del producto"]
    I4 --> J
    I5 --> J

    J --> K{"¿Se entiende la fila?"}
    K -->|No| L["Apartarla con su motivo, sin frenar el resto"]
    K -->|Sí| M{"¿El producto es conocido?"}
    M -->|No| N["Apartarlo con su motivo, sin darlo de alta"]
    M -->|Sí| O["Registrar su precio vigente y, si cambió, agregar un punto a su historial"]
    O --> P{"¿Subió más que el porcentaje definido por el dueño?"}
    P -->|Sí| Q["Destacar el producto"]
    P -->|No| R["Dejarlo sin destacar"]

    L --> S["Al terminar de recorrer la lista"]
    N --> S
    Q --> S
    R --> S

    S --> T["Conservar el último precio de los productos conocidos que no vinieron, y señalarlos"]
    T --> U["Informar cuántas filas quedaron apartadas"]
    U --> V["Guardar la fecha y la hora de esta actualización exitosa"]
    V --> Z
```

