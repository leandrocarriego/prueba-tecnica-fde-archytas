<!-- GENERADO por scripts/diagrams/export.sh — NO editar a mano.
     Fuente: los .mmd de esta carpeta. Regenerar: scripts/diagrams/export.sh -->

# Diagramas

> Vista renderizada de los diagramas de esta feature. Fuente: los `.mmd` de esta
> carpeta. Convención: `docs/specs/DIAGRAMS.md`. Las imágenes para el cliente se
> generan en `dist/diagramas/` con `make diagrams`.

## Un dato — cómo se lo confirma y cómo se lo dibuja

```mermaid
---
title: Un dato — cómo se lo confirma y cómo se lo dibuja
---
stateDiagram-v2
    state "Leído del origen, sin confirmar" as SinConfirmar
    state "Confirmado por una persona" as Confirmado

    [*] --> SinConfirmar: el sistema lo lee del origen
    SinConfirmar --> Confirmado: una persona lo confirma

    note right of SinConfirmar
        Se distingue a simple vista
        del dato ya confirmado
    end note

    state "En cualquiera de los dos casos, la pastilla dice el estado" as Senal {
        state "Conforme" as S1
        state "Informativo" as S2
        state "Requiere decisión" as S3
        state "Vencido o con error" as S4
        state "Sin novedad" as S5
    }

    SinConfirmar --> Senal
    Confirmado --> Senal

    note right of Senal
        Cinco significados y nada más.
        El naranja no aparece acá: señala
        la acción que resuelve la pantalla,
        no un estado
    end note
```

## Una pantalla — las tres caras que siempre se ven igual

```mermaid
---
title: Una pantalla — las tres caras que siempre se ven igual
---
stateDiagram-v2
    [*] --> Cargando
    state "Cargando" as Cargando
    state "Con contenido" as ConContenido
    state "Sin resultados" as Vacia
    state "Con error" as Error

    Cargando --> ConContenido: hay datos para mostrar
    Cargando --> Vacia: no hay ningún resultado
    Cargando --> Error: no se pudo traer

    note right of Error
        Cargando, sin resultados y con error
        se dibujan con la misma forma en
        todas las secciones de la plataforma
    end note
```

## El dueño — el aviso antes que el número

```mermaid
---
title: El dueño — el aviso antes que el número
---
flowchart TD
    A["Entra con su acceso"] --> B["Encuentra el menú a la izquierda, agrupado por área,<br/>con la sección que está mirando señalada"]
    B --> C["Ve su nombre y la salida para cerrar sesión sin abrir ningún desplegable"]

    B --> D["Abre el tablero"]
    D --> E{"¿El indicador dejó registros afuera por dudosos?"}
    E -->|Sí| F["El aviso aparece por encima del número"]
    F --> G["Y trae el enlace para ir a resolver esos casos"]
    E -->|No| H["El tablero lo dice con todas las letras, en vez de no mostrar nada"]

    B --> I["Recorre el calendario y los proveedores"]
    I --> J["El mismo estado se dibuja igual que en el tablero:<br/>misma pastilla, mismo color"]
    I --> K["Distingue a simple vista lo que todavía nadie confirmó<br/>de lo que ya está confirmado"]

    B --> L["Ve todo el sistema: ninguna sección se le oculta"]

    M["En cada pantalla hay como mucho un botón naranja,<br/>y es el que resuelve lo que vino a hacer"]
    N["En el calendario, que es una lista de casos para decidir,<br/>no hay ninguno"]
```

## Un solo idioma visual — de punta a punta

```mermaid
---
title: Un solo idioma visual — de punta a punta
---
sequenceDiagram
    autonumber
    participant Sistema as El sistema
    actor Duenio as El dueño
    actor Marcela as Marcela, compras
    actor Julian as Julián, ventas

    Note over Sistema,Julian: La promesa que atraviesa el proyecto: si algo no se puede resolver solo, avisá.<br/>Un aviso sólo cumple esa promesa si se distingue de un adorno de un vistazo

    Sistema->>Sistema: Presenta todas las pantallas con la misma paleta, tipografía,<br/>espaciados y radios de la guía acordada
    Sistema->>Sistema: Un solo fondo de aplicación y un solo color de tarjeta

    Duenio->>Sistema: Abre la plataforma para ingresar
    Sistema-->>Duenio: Le presenta el ingreso con la misma identidad visual que el resto,<br/>igual que la invitación y la recuperación de contraseña

    Duenio->>Sistema: Entra y abre el tablero
    Sistema-->>Duenio: Le muestra el menú a la izquierda, agrupado por área,<br/>con la sección actual señalada y su nombre y la salida siempre visibles

    alt Un indicador dejó registros afuera por dudosos
        Sistema-->>Duenio: Pone el aviso por encima del número, con el enlace para ir a resolverlo
    else No dejó ninguno afuera
        Sistema-->>Duenio: Lo dice con todas las letras, en vez de no mostrar nada
    end

    Marcela->>Sistema: Recorre facturas, pagos y órdenes
    Sistema-->>Marcela: Dibuja cada estado con la misma pastilla y el mismo color en todas las pantallas
    Sistema-->>Marcela: Muestra importes, fechas y códigos en ancho fijo, con las cifras en columna
    Note over Sistema,Marcela: Lo leído del origen y todavía sin confirmar se distingue a simple vista<br/>de lo que ya confirmó una persona

    Marcela->>Sistema: Abre Revisar esto, que es una lista de casos para decidir
    Sistema-->>Marcela: No pinta ningún botón naranja: cada caso ofrece su acción en tinta o contorno

    Julian->>Sistema: Entra con su acceso y mira el menú
    Sistema-->>Julian: Lista Ventas y el catálogo, y no ofrece las secciones que no puede abrir
    Note over Sistema,Julian: El grupo que queda sin ninguna sección visible tampoco aparece

    Note over Sistema,Julian: En cada pantalla hay como mucho un botón naranja, y es el que resuelve<br/>la tarea principal: el naranja significa una sola cosa, acá decidís vos
```

## Julián, ventas — el menú le ofrece sólo lo que puede abrir

```mermaid
---
title: Julián, ventas — el menú le ofrece sólo lo que puede abrir
---
flowchart TD
    A["Entra con su acceso"] --> B["Mira el menú principal"]
    B --> C["Encuentra Ventas como una entrada más, y la abre desde ahí"]
    B --> D["No lista Facturas, Órdenes de compra ni Accesos"]
    D --> E["No choca con una negativa después de hacer clic"]
    B --> F{"¿Quedó algún grupo sin ninguna sección visible?"}
    F -->|Sí| G["Tampoco aparece el título de ese grupo"]
    F -->|No| H["El grupo se muestra con las secciones que sí puede abrir"]

    C --> I["Revisa ventas y catálogo"]
    I --> J["Ve las mismas pastillas de estado que los demás,<br/>con las mismas formas y los mismos colores"]
    I --> K["Los importes y las fechas, en ancho fijo y alineados en columna"]

    L["Los permisos no cambian con esta feature:<br/>cambia que lo que no puede abrir ya no se le ofrece"]
```

## Marcela, compras — la plata en columna y los estados siempre iguales

```mermaid
---
title: Marcela, compras — la plata en columna y los estados siempre iguales
---
flowchart TD
    A["Entra con su acceso"] --> B["El menú le ofrece sólo las secciones que puede abrir"]

    B --> C["Trabaja sobre facturas, pagos y órdenes"]
    C --> D["Los importes, las fechas y los códigos se ven en tipografía de ancho fijo"]
    D --> E["Las cifras quedan alineadas en columna aunque tengan distinta cantidad de dígitos"]

    C --> F["Busca una factura vencida en el listado, en el calendario<br/>y en la ficha del proveedor"]
    F --> G["La señal es la misma pastilla roja en los tres lugares"]

    C --> H["Un dato leído del origen y todavía sin confirmar<br/>se distingue del que ya confirmó una persona"]

    B --> I["Abre Revisar esto"]
    I --> J["Es una lista de casos para decidir: ningún botón naranja"]
    J --> K["Cada caso ofrece su acción en tinta o contorno"]

    B --> L{"¿Qué botón resuelve esta pantalla?"}
    L -->|El de la tarea principal| M["Es el único naranja"]
    L -->|El resto| N["Contorno, gris o enlace, nunca naranja"]

    B --> O["Una pantalla cargando, una con error y una sin resultados<br/>se ven con la misma forma que en cualquier otra sección"]

    P["Nada de lo que calcula el sistema cambia acá:<br/>cambia cómo se muestra lo que ya estaba decidido"]
```

## El sistema — qué señal le corresponde a cada cosa

```mermaid
---
title: El sistema — qué señal le corresponde a cada cosa
---
flowchart TD
    A["Tiene algo que mostrar en pantalla"] --> B{"¿Qué es?"}

    B -->|El estado de un dato| C["Lo dibuja como una pastilla"]
    C --> D["Con uno de los cinco significados acordados:<br/>conforme, informativo, requiere decisión, vencido o con error, sin novedad"]
    D --> E["Nunca en naranja: el naranja señala la acción, no el estado"]

    B -->|Un importe, una fecha o un código| F["Tipografía de ancho fijo con cifras de ancho uniforme"]
    F --> G["Si es una columna de importes, la alinea para que las cifras queden en columna"]

    B -->|Una acción| H{"¿Resuelve la tarea principal de la pantalla?"}
    H -->|Sí, y es la única| I["Botón naranja"]
    H -->|No| J["Contorno, gris o enlace"]
    H -->|La pantalla es una lista de casos para decidir| K["Ningún naranja: tinta o contorno en cada caso"]
    J --> L["El color de enlace sólo navega o consulta,<br/>nunca modifica datos"]

    B -->|Un total| M{"¿Dejó registros afuera por dudosos?"}
    M -->|Sí| N["Muestra el aviso por encima del total"]
    N --> O["Y lo acompaña con la acción que permite resolverlo"]
    M -->|No, y es un indicador del tablero| P["Lo dice explícitamente"]
    M -->|No, y está fuera del tablero| Q["No muestra ningún aviso"]

    B -->|El menú| R["Oculta las secciones que la persona no puede abrir"]
    R --> S{"¿El grupo quedó vacío?"}
    S -->|Sí| T["Oculta también el título del grupo"]
    S -->|No| U["Muestra el grupo con lo que queda"]

    V["Y siempre sobre lo mismo: un solo fondo de aplicación, un solo color de tarjeta,<br/>un solo tema claro que no cambia con la configuración del dispositivo"]
```

