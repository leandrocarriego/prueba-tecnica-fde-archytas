<!-- GENERADO por scripts/diagrams/export.sh — NO editar a mano.
     Fuente: los .mmd de esta carpeta. Regenerar: scripts/diagrams/export.sh -->

# Diagramas

> Vista renderizada de los diagramas de esta feature. Fuente: los `.mmd` de esta
> carpeta. Convención: `docs/specs/DIAGRAMS.md`. Las imágenes para el cliente se
> generan en `dist/diagramas/` con `make diagrams`.

## Qué le pasa a cada factura que llega del portal

```mermaid
---
title: Qué le pasa a cada factura que llega del portal
---
stateDiagram-v2
    state "Obtenida del portal, con su archivo guardado" as Obtenida
    state "Leída con certeza" as Leida
    state "Con algún dato en duda" as Dudosa
    state "Con el proveedor sin identificar" as SinProveedor
    state "De un proveedor que no está en el padrón" as FueraDelPadron
    state "Repetida, con un total distinto" as Discrepante
    state "Apartada, esperando una decisión" as Apartada
    state "Resuelta por una persona" as Resuelta
    state "Registrada, con sus cuatro datos" as Registrada

    [*] --> Obtenida
    Obtenida --> Leida: se leen número, fecha, proveedor y total
    Obtenida --> Dudosa: un dato no se pudo leer con certeza
    Obtenida --> Apartada: el archivo tiene una forma que el sistema no reconoce

    Leida --> Registrada: el proveedor queda identificado
    Leida --> SinProveedor: el nombre no alcanza para saber cuál es
    Leida --> FueraDelPadron: el proveedor no es ninguno de los ocho
    Leida --> Discrepante: ya había una igual, con otro total

    Dudosa --> Apartada
    SinProveedor --> Apartada
    FueraDelPadron --> Apartada
    Discrepante --> Apartada

    Apartada --> Resuelta: una persona confirma el dato o asigna el proveedor
    Resuelta --> Registrada
    Registrada --> [*]

    note right of Obtenida
        El archivo se conserva tal como llegó
        y no se vuelve a tocar. Si mañana
        mejora la forma de leerlo, se puede
        volver a leer sin pedirle nada al portal
    end note

    note right of Apartada
        Contada y visible con su motivo, sin
        frenar el procesamiento de las demás.
        Nada se descarta y nada se completa
        por suposición
    end note

    note right of Registrada
        Nunca queda registrada sin número, sin
        fecha, sin proveedor o sin total. La
        misma factura entra una sola vez, y si
        llegó varias, lo indica
    end note
```

## Qué le pasa a cada forma de escribir el nombre de un proveedor

```mermaid
---
title: Qué le pasa a cada forma de escribir el nombre de un proveedor
---
stateDiagram-v2
    state "Grafía nueva, observada en una factura" as Nueva
    state "Reconocida contra el padrón" as Reconocida
    state "Ambigua, esperando una decisión" as Ambigua
    state "Asignada a un proveedor por una persona" as Asignada
    state "Dejada sin efecto" as SinEfecto

    [*] --> Nueva
    Nueva --> Reconocida: el nombre corresponde sin dudas a un proveedor del padrón
    Nueva --> Ambigua: podría ser de dos, o de ninguno
    Ambigua --> Asignada: una persona dice a qué proveedor corresponde
    Reconocida --> [*]
    Asignada --> SinEfecto: la decisión estaba equivocada y se anula
    SinEfecto --> Ambigua: las facturas que resolvía vuelven a quedar apartadas

    note right of Asignada
        Antes de guardarla, el sistema dice a
        cuántas facturas apartadas alcanza.
        Al confirmar, las resuelve a todas y
        se aplica a las que lleguen después
    end note

    note right of Asignada
        Queda a la vista con quién la decidió
        y cuándo: una decisión equivocada
        tiene que poder corregirse
    end note
```

## El dueño — qué mira y qué decide

```mermaid
---
title: El dueño — qué mira y qué decide
---
flowchart TD
    A["El dueño quiere saber con cuántos proveedores trabaja y cuánto le compró a cada uno"] --> B["Abre la pantalla de proveedores"]
    B --> C["Ve ocho proveedores, no veinticuatro, y cuántos son"]
    C --> D["Abre uno y ve todas las formas en que llegó escrito su nombre"]
    D --> E["Ve sus datos fiscales, su contacto y su plazo de pago pactado"]

    E --> F["Pide un período"]
    F --> G["El total facturado por ese proveedor en ese período"]
    G --> H["Y cuántas facturas quedaron afuera del total por estar en revisión"]
    H --> I{"¿El número cierra con la suma hecha a mano?"}
    I -->|Sí| J["Puede confiar en el dato"]
    I -->|No| K["Las que faltan están en la pantalla de revisión, contadas y con su motivo"]

    A --> L["Ve todo el sistema, igual que compras"]
    L --> M["También resuelve facturas apartadas y asigna grafías"]
    K --> M
```

## Facturas y proveedores — de punta a punta

```mermaid
---
title: Facturas y proveedores — de punta a punta
---
sequenceDiagram
    autonumber
    participant Sistema as El sistema
    participant Portal as Portal del proveedor
    actor Marcela as Marcela, compras
    actor Duenio as El dueño
    actor Julian as Julián, ventas

    loop Con la frecuencia configurada
        Sistema->>Portal: Entra por su cuenta y pide las facturas de compra
        Portal-->>Sistema: Las facturas y sus archivos
        Sistema->>Sistema: Conserva cada archivo tal como llegó
        Sistema->>Sistema: Lee número, fecha, proveedor y total, sea PDF, imagen escaneada o planilla
        Sistema->>Sistema: Anota, dato por dato, si lo obtuvo con certeza o le quedó en duda

        alt La factura trae el CUIT del proveedor
            Sistema->>Sistema: Lo identifica por el CUIT, sin interpretar nada
        else No lo trae
            Sistema->>Sistema: Lo resuelve por el nombre contra el padrón de ocho proveedores
        end

        alt Todo quedó con certeza y el proveedor es del padrón
            Sistema->>Sistema: Registra la factura asociada a su proveedor
        else Un dato en duda, un proveedor ambiguo o uno que no está en el padrón
            Sistema->>Sistema: La aparta con su motivo, sin frenar a las demás
        end

        opt La misma factura ya estaba registrada
            Sistema->>Sistema: Conserva una sola y anota cuántas veces llegó
            Note over Sistema: Si el total difiere, no descarta ninguna:<br/>la aparta con los dos totales a la vista
        end
    end

    Marcela->>Sistema: Abre la pantalla de revisión
    Sistema-->>Marcela: Cada caso con su motivo y el recorte del archivo del que salió el dato
    Marcela->>Sistema: Confirma o corrige el dato, o asigna la grafía del nombre a un proveedor
    Sistema-->>Marcela: Le avisa a cuántas facturas apartadas alcanza esa asignación
    Marcela->>Sistema: Confirma
    Sistema->>Sistema: Resuelve esas facturas y guarda la decisión para las que lleguen después

    Marcela->>Sistema: Corrige el correo, el teléfono o el plazo pactado de un proveedor
    Sistema->>Sistema: Registra quién lo corrigió, cuándo y qué valor tenía antes

    Duenio->>Sistema: Abre un proveedor y pide un período
    Sistema-->>Duenio: Sus facturas, el total facturado y cuántas quedaron afuera por estar en revisión

    Julian->>Sistema: Intenta abrir las facturas de compra
    Sistema-->>Julian: No tiene permiso, ni siquiera conociendo la dirección de la pantalla
```

## Julián, ventas — hasta dónde llega con esta feature

```mermaid
---
title: Julián, ventas — hasta dónde llega con esta feature
---
flowchart TD
    A["Julián entra con su acceso de ventas"] --> B["Las facturas de compra no aparecen en su menú"]
    B --> C["Las cuentas de proveedores tampoco"]
    C --> D["Copia la dirección exacta de la pantalla de facturas y la abre"]
    D --> E["El sistema le avisa que no tiene permiso, en lugar de mostrársela"]
    E --> F["Resolver una factura apartada o asignar una grafía tampoco es suyo"]
    F --> G["Lo que le facturan a la empresa no revela nada de las ventas, y al revés tampoco"]
```

## Marcela, compras — qué puede hacer y qué ve

```mermaid
---
title: Marcela, compras — qué puede hacer y qué ve
---
flowchart TD
    A["Marcela trabaja las facturas de compra y los proveedores"] --> B["Abre la lista de facturas"]
    B --> C["Ve número, fecha, proveedor, total y en qué formato llegó cada una"]
    C --> D["Busca por CUIT o por razón social, y filtra por fecha, proveedor o estado de revisión"]
    D --> E["Abre el archivo original de cualquier factura"]

    A --> F["Abre la pantalla de revisión"]
    F --> G{"¿Por qué se apartó este caso?"}
    G -->|Un dato quedó en duda| H["Ve el recorte del archivo del que salió y confirma o corrige el dato"]
    G -->|El proveedor no se pudo identificar| I["Asigna la grafía del nombre al proveedor que corresponde"]
    G -->|El proveedor no está en el padrón| J["No puede darlo de alta: el caso espera una decisión del negocio"]
    G -->|La misma factura llegó con otro total| K["Ve los dos totales y decide cuál queda"]

    I --> L["El sistema le avisa a cuántas facturas apartadas alcanza esa asignación"]
    L --> M["Confirma y todas esas facturas quedan resueltas de una vez"]
    M --> N["La próxima factura con esa misma grafía entra directo, sin pasar por revisión"]

    H --> O["El caso queda resuelto y sale de los pendientes"]
    K --> O
    M --> O
    O --> P["Queda registrado qué se decidió, quién lo decidió y cuándo"]

    N --> Q{"¿La asignación estaba equivocada?"}
    Q -->|Sí| R["La deja sin efecto y esas facturas vuelven a la revisión"]
    Q -->|No| S["La pantalla de revisión se mantiene vacía"]
    R --> F

    A --> T["Abre la ficha de un proveedor"]
    T --> U["Ve su razón social, su CUIT, su correo, su teléfono y su plazo de pago pactado"]
    U --> V["Corrige el correo, el teléfono o el plazo, y queda registrado con su nombre y el valor anterior"]
    V --> W["Si el portal trae después otro valor, el sistema lo señala en lugar de pisar la corrección"]
    U --> X["La razón social y el CUIT no se editan: son con lo que se reconoce al proveedor"]
```

## El sistema — qué hace con cada factura que trae del portal

```mermaid
---
title: El sistema — qué hace con cada factura que trae del portal
---
flowchart TD
    A["Con la frecuencia configurada, entra al portal y trae las facturas de compra"] --> B["Conserva el archivo de cada una tal como llegó"]
    B --> C{"¿Qué formato tiene el archivo?"}
    C -->|PDF con texto| D["Lee número, fecha, proveedor y total"]
    C -->|Imagen escaneada| D
    C -->|Planilla| D
    C -->|Una forma que no reconoce| E["La aparta para revisión, sin frenar a las demás"]

    D --> F["Anota, dato por dato, si lo obtuvo con certeza o le quedó en duda"]
    F --> G{"¿Algún dato quedó en duda?"}
    G -->|Sí| E
    G -->|No| H{"¿La factura trae el CUIT del proveedor?"}

    H -->|Sí| I["Identifica al proveedor por su CUIT"]
    H -->|No| J["Busca el nombre contra el padrón de ocho proveedores"]
    J --> K{"¿La grafía ya fue asignada antes por una persona?"}
    K -->|Sí| I
    K -->|No, y el nombre no es concluyente| E
    K -->|No está en el padrón| L["La aparta indicando que el proveedor no está en el padrón"]

    I --> M{"¿Esta factura ya estaba registrada?"}
    M -->|No| N["La registra con su proveedor, su número, su fecha y su total"]
    M -->|Sí, igual en todo| O["Conserva una sola y anota cuántas veces llegó"]
    M -->|Sí, pero con otro total| P["La aparta con los dos totales a la vista"]

    E --> Q["Queda contada y visible en la pantalla de revisión, con su motivo"]
    L --> Q
    P --> Q
    N --> R["Aparece en la lista de facturas y en la ficha de su proveedor"]
    O --> R

    S["Nunca da de alta un proveedor por su cuenta"] --- L
    T["Nunca completa un dato por suposición"] --- E
```

