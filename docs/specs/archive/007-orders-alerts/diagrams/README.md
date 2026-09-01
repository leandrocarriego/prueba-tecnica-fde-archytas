<!-- GENERADO por scripts/diagrams/export.sh — NO editar a mano.
     Fuente: los .mmd de esta carpeta. Regenerar: scripts/diagrams/export.sh -->

# Diagramas

> Vista renderizada de los diagramas de esta feature. Fuente: los `.mmd` de esta
> carpeta. Convención: `docs/specs/DIAGRAMS.md`. Las imágenes para el cliente se
> generan en `dist/diagramas/` con `make diagrams`.

## El camino de un aviso que sale del sistema

```mermaid
---
title: El camino de un aviso que sale del sistema
---
stateDiagram-v2
    state "Hay un aviso inmediato para enviar" as Inmediato
    state "En espera de la franja" as EnEspera
    state "Hay un resumen diario para enviar" as Resumen
    state "Entregado por WhatsApp" as Entregado
    state "No entregado" as NoEntregado
    state "Sin aviso hacia afuera" as SinAviso

    [*] --> Inmediato: entra un reclamo de pago o un aviso de vencimiento próximo
    Inmediato --> EnEspera: el aviso inmediato entró fuera de la franja de avisos
    EnEspera --> Entregado: comienza la franja siguiente
    Inmediato --> Entregado: sale al número registrado de quien recibe ese tipo de aviso
    Inmediato --> NoEntregado: el envío falla, y queda registrado y señalado en la pantalla de mensajes

    [*] --> Resumen: llega la hora configurada del resumen diario
    Resumen --> Entregado: sale al número registrado de quien recibe el resumen
    Resumen --> NoEntregado: el envío falla, y queda registrado y señalado en la pantalla de mensajes

    [*] --> SinAviso: es un aviso de stock bajo o un mensaje sin clasificar
    [*] --> SinAviso: ya se mandó el aviso inmediato por ese mismo mensaje
    [*] --> SinAviso: el mensaje ya estaba en la bandeja al ponerse en marcha el sistema
    [*] --> SinAviso: la persona perdió el acceso al sistema

    Entregado --> [*]
    NoEntregado --> [*]
    SinAviso --> [*]

    note right of EnEspera
        Fuera de la franja acordada el aviso inmediato espera
        al comienzo de la siguiente. Un canal que despierta a
        alguien de madrugada por algo que se resuelve a las 9
        se silencia, y silenciado deja de existir
    end note

    note right of Resumen
        Lleva los mensajes pendientes y las órdenes
        estancadas, cada orden una vez por día. La franja
        es de los avisos inmediatos: el resumen sale a su
        hora configurada
    end note

    note right of SinAviso
        El mensaje se ve igual en la pantalla: lo que no
        sale es el aviso. La pantalla es donde se
        resuelve, no donde uno se entera
    end note
```

## El camino de un mensaje de la bandeja

```mermaid
---
title: El camino de un mensaje de la bandeja
---
stateDiagram-v2
    state "Traído de la bandeja del portal" as Traido
    state "Clasificado por tipo" as Clasificado
    state "Sin clasificar" as SinClasificar
    state "Pendiente" as Pendiente
    state "Pendiente, con responsable" as ConResponsable
    state "Resuelto" as Resuelto

    [*] --> Traido: el sistema lo trae antes de que pase una hora desde que apareció
    Traido --> Clasificado: es un reclamo de pago, un vencimiento próximo o un stock bajo
    Traido --> SinClasificar: su tipo no se puede determinar, y aun así se muestra
    Clasificado --> Pendiente
    SinClasificar --> Pendiente
    Pendiente --> ConResponsable: se le asigna el dueño o alguien de compras
    Pendiente --> Resuelto: una persona lo marca resuelto
    ConResponsable --> Resuelto: una persona lo marca resuelto
    Resuelto --> [*]

    note right of Traido
        Si el remitente no coincide con ningún proveedor
        del padrón, el mensaje se muestra igual, señalando
        que quedó sin identificar. Nada se descarta
    end note

    note right of Pendiente
        Mientras siga pendiente se cuenta en la pantalla
        y entra en el resumen diario. Los que ya estaban
        en la bandeja al ponerse en marcha nacen acá, sin
        que se avise por ellos
    end note

    note right of Resuelto
        Queda registrado quién lo resolvió y cuándo, con
        las notas que se hayan dejado, y deja de aparecer
        en el resumen diario
    end note
```

## El camino de una orden de compra

```mermaid
---
title: El camino de una orden de compra
---
stateDiagram-v2
    state "Apartada para revisión" as Apartada
    state "En curso, antes de la recepción" as EnCurso {
        state "Pendiente de envío" as Pendiente
        state "Enviada" as Enviada
        state "Confirmada" as Confirmada
        [*] --> Pendiente
        Pendiente --> Enviada: el portal la muestra enviada
        Enviada --> Confirmada: el portal la muestra confirmada
    }
    state "Señalada como estancada" as Estancada
    state "Recibida" as Recibida

    [*] --> Apartada: su proveedor no se puede identificar con certeza
    [*] --> EnCurso: el sistema la trae del portal con su proveedor identificado
    Apartada --> EnCurso: el dueño o compras le asigna un proveedor del padrón
    Apartada --> EnCurso: otra orden igual ya se resolvió y esa decisión alcanza a ésta
    EnCurso --> Estancada: lleva en el mismo estado más días que el límite configurado
    Estancada --> EnCurso: avanza de estado y deja de estar señalada
    EnCurso --> Recibida: el portal la muestra recibida
    Estancada --> Recibida: llega la mercadería y deja de estar señalada
    Recibida --> [*]

    note right of Apartada
        Nada se descarta y nada se supone: queda
        apartada con su motivo, sin asignarla al
        proveedor que más se le parece. Sigue en la
        lista con el nombre tal como llegó, se cuenta
        aparte y se puede pedir ver sólo esas. La
        resuelven el dueño y compras asignándole uno de
        los ocho proveedores del padrón, y queda
        registrado quién lo decidió y cuándo. Esa
        decisión se guarda como criterio: alcanza a las
        otras que estaban apartadas escritas de esa
        misma forma y a las que lleguen después.
        Mientras siga apartada no se la compara con
        ninguna otra
    end note

    note right of Estancada
        El reloj es del sistema, no del portal: cuenta
        desde que lo ve por sí mismo. El día uno no hay
        ninguna señalada. Una orden ya recibida no se
        estanca
    end note

    note right of Recibida
        Además del estado, cada orden muestra desde
        cuándo el sistema la viene viendo así. Las
        anteriores a la puesta en marcha muestran
        cuántos días pasaron desde el pedido
    end note
```

## El dueño — qué mira, qué recibe y qué ajusta

```mermaid
---
title: El dueño — qué mira, qué recibe y qué ajusta
---
flowchart TD
    A["El dueño quiere saber qué quedó sin resolver y de quién es"] --> B["Ve lo mismo que compras: las órdenes de compra y la pantalla de mensajes"]
    B --> C["Cuántas órdenes hay en cada estado y cuántas están estancadas"]
    C --> D["Mira sólo esas, en lugar de recorrer las cuarenta"]
    B --> E["Cuántos mensajes siguen pendientes, quién es responsable de cada uno y quién resolvió cada uno"]
    B --> E2["Cuántas órdenes quedaron apartadas por no poder identificar a su proveedor, y las resuelve igual que compras"]

    A --> F["Recibe por WhatsApp el resumen diario, a la hora configurada"]
    F --> G["Lleva los mensajes pendientes y las órdenes estancadas"]
    G --> H["Lo ya resuelto no aparece, y cada orden estancada figura una vez por día"]

    A --> I["Define quién recibe cada tipo de aviso"]
    I --> J["Arranca con los reclamos y los vencimientos hacia compras, y el resumen hacia él"]
    J --> K["Cambiado el destinatario, el aviso siguiente llega a quien indicó"]

    A --> L["Ajusta en el panel de configuración del sistema los cuatro valores de esta funcionalidad"]
    L --> M["Los días para considerar estancada una orden, que arrancan en 15"]
    L --> N["La ventana de pedido repetido, que arranca en 15 días"]
    L --> O["La hora del resumen diario, que arranca a las 8:00"]
    L --> P["La franja en la que puede sonar un aviso, que arranca de lunes a viernes de 8:00 a 18:00"]
    M --> Q["No hay valores escondidos en las pantallas de órdenes ni de mensajes"]
    N --> Q
    O --> Q
    P --> Q
```

## Órdenes de compra y avisos — de punta a punta

```mermaid
---
title: Órdenes de compra y avisos — de punta a punta
---
sequenceDiagram
    autonumber
    participant Portal as El portal del proveedor
    participant Sistema as El sistema
    actor Marcela as Marcela, compras
    actor Duenio as El dueño
    actor Julian as Julián, ventas

    loop Con la frecuencia configurada
        Sistema->>Portal: Entra por su cuenta y pide las órdenes de compra
        Portal-->>Sistema: Cada orden con su proveedor, su fecha, su monto y su estado
        Sistema->>Sistema: Registra en qué estado la ve y desde cuándo la viene viendo así

        alt El proveedor de la orden se identifica con certeza
            Sistema->>Sistema: La registra y la muestra en su punto del recorrido, del pedido a la recepción
        else No se puede identificar con certeza
            Sistema->>Sistema: La aparta para revisión, sin asignarla al proveedor que más se le parece
            Note over Sistema,Marcela: Sigue en la lista con el nombre tal como llegó y se cuenta aparte.<br/>Mientras no se sepa de quién es, no se la compara con ninguna otra
        end

        opt Lleva, antes de la recepción, más días que el límite configurado sin moverse
            Sistema->>Sistema: La señala como estancada
            Note over Sistema: Una orden ya recibida no se estanca
        end

        opt Ese producto ya se le pidió al mismo proveedor dentro de la ventana configurada
            Sistema->>Sistema: La señala como posible pedido repetido y muestra el pedido anterior
            Note over Sistema,Marcela: Señala, no bloquea: la orden queda igual en la lista, con su estado
        end
    end

    Marcela->>Sistema: Abre las órdenes y filtra por estado o por proveedor
    Sistema-->>Marcela: Cuántas hay en cada estado, cuántas están estancadas y desde cuándo espera cada una
    Marcela->>Sistema: Descarta un señalamiento de pedido repetido
    Sistema->>Sistema: Registra quién lo descartó y cuándo

    Marcela->>Sistema: Pide ver sólo las órdenes apartadas y le asigna a una un proveedor del padrón
    Sistema->>Sistema: La asocia a ese proveedor, registra quién lo decidió y cuándo, y la saca de las apartadas
    Sistema->>Sistema: Guarda esa forma de escribir el nombre como criterio y resuelve con ella las otras apartadas escritas igual
    Note over Sistema,Marcela: La decisión se toma una sola vez: la orden que llegue después escrita así entra<br/>identificada, sin pasar por revisión
    Note over Sistema,Marcela: Resolverla no da de alta un proveedor: si es de alguien fuera del padrón,<br/>el motivo lo dice y sumar un proveedor se decide aparte

    loop De modo que no pase más de una hora desde que un mensaje aparece
        Sistema->>Portal: Pide los mensajes de la bandeja
        Portal-->>Sistema: Reclamos de pago, avisos de vencimiento próximo y avisos de stock bajo
        Sistema->>Sistema: Clasifica cada mensaje por tipo y busca su remitente en el padrón de proveedores
        Note over Sistema: Nada se descarta: sin tipo se muestra como sin clasificar,<br/>y sin remitente reconocido se muestra señalando que quedó sin identificar
        Sistema->>Sistema: Lo registra como pendiente

        alt Es un reclamo de pago o un vencimiento próximo, dentro de la franja de avisos
            Sistema-->>Marcela: Le avisa por WhatsApp en el momento, al número registrado de quien recibe ese tipo de aviso
        else Es un reclamo o un vencimiento fuera de la franja
            Sistema->>Sistema: Retiene el aviso y lo envía al comenzar la franja siguiente
        else Es un aviso de stock bajo o quedó sin clasificar
            Sistema->>Sistema: Queda a la vista en la pantalla de mensajes, sin salir del sistema
        end

        opt El aviso no se pudo entregar
            Sistema->>Sistema: Registra el fallo y lo señala en la pantalla de mensajes
        end
    end
    Note over Sistema,Marcela: Por el mismo mensaje manda un solo aviso inmediato, y mientras siga pendiente se cuenta en el resumen.<br/>Los que ya estaban en la bandeja al ponerse en marcha quedan pendientes, sin ningún aviso

    Marcela->>Sistema: Abre los mensajes y filtra por tipo, por proveedor o por estado
    Marcela->>Sistema: Toma un reclamo como responsable, deja una nota y lo marca resuelto
    Sistema->>Sistema: Registra quién lo resolvió y cuándo, y cuenta un pendiente menos

    Sistema-->>Duenio: A la hora configurada, el resumen diario por WhatsApp
    Note over Sistema,Duenio: Lleva los mensajes pendientes y las órdenes estancadas.<br/>Lo resuelto no entra, y una orden estancada figura una vez por día.<br/>La franja es de los avisos inmediatos: el resumen sale a su hora configurada

    Duenio->>Sistema: Ajusta los días de estancamiento, la ventana de pedido repetido, la hora del resumen y la franja de avisos
    Duenio->>Sistema: Define quién recibe cada tipo de aviso
    Sistema-->>Duenio: Los avisos siguientes salen con los valores nuevos

    opt Una persona pierde el acceso al sistema
        Sistema->>Sistema: Deja de enviarle avisos
    end

    Julian->>Sistema: Intenta abrir las órdenes de compra o la bandeja de mensajes
    Sistema-->>Julian: No tiene permiso, ni siquiera conociendo la dirección de la pantalla
```

## Julián, ventas — hasta dónde llega con esta funcionalidad

```mermaid
---
title: Julián, ventas — hasta dónde llega con esta funcionalidad
---
flowchart TD
    A["Julián entra con su acceso de ventas"] --> B["Las órdenes de compra no aparecen en su menú"]
    B --> C["La bandeja de mensajes tampoco, ni los avisos de stock bajo"]
    C --> D["Copia la dirección exacta de esas pantallas y las abre"]
    D --> E["El sistema le avisa que no tiene permiso, en lugar de mostrárselas"]
    E --> F["Tampoco figura entre las personas a las que se les puede asignar un mensaje"]
    F --> G["Los reclamos y los vencimientos llegan a compras, y el resumen diario al dueño"]
```

## Marcela, compras — qué ve y qué resuelve

```mermaid
---
title: Marcela, compras — qué ve y qué resuelve
---
flowchart TD
    A["Marcela sigue las compras y trabaja los mensajes que hoy caen en la bandeja del portal"] --> B["Abre la lista de órdenes de compra"]
    B --> C["Ve cada orden con su proveedor, su fecha, su monto y su estado"]
    C --> D["Ve en qué punto del recorrido está, del pedido a la recepción, y desde cuándo el sistema la ve así"]
    D --> E["Filtra por estado o por proveedor, y ve cuántas hay en cada estado"]
    E --> F["Pide ver sólo las estancadas, en lugar de recorrer las cuarenta"]
    F --> G["De las órdenes que vienen del sistema viejo ve cuántos días pasaron desde el pedido"]

    C --> H{"¿El sistema la señaló como posible pedido repetido?"}
    H -->|Sí| I["Ve cuál es el pedido anterior con el que coincide"]
    I --> J{"¿Era efectivamente el mismo pedido?"}
    J -->|No| K["Descarta el señalamiento, y queda registrado con su nombre y la fecha"]
    J -->|Sí| L["Decide si igual se pide: el sistema avisa, no bloquea"]

    C --> V{"¿El sistema pudo identificar al proveedor de la orden?"}
    V -->|No| W["La ve en la lista con el nombre tal como llegó, señalada como sin identificar y contada aparte"]
    W --> X["Pide ver sólo las apartadas y le asigna uno de los ocho proveedores del padrón"]
    X --> Y["La orden queda con ese proveedor, con su nombre y la fecha registrados, y sale de las apartadas"]
    Y --> Y1["Esa forma de escribir el nombre queda guardada como criterio: no se la vuelve a preguntar"]
    Y1 --> Y2["Las otras órdenes apartadas escritas de esa misma forma quedan resueltas con la misma decisión"]
    W --> Z["Si es de alguien que no está en el padrón, el motivo lo dice: sumar un proveedor es una decisión del negocio"]

    A --> M["Abre la pantalla de mensajes"]
    M --> N["Los ve separados por tipo, con el proveedor que los mandó y el estado de cada uno"]
    N --> O["Filtra por tipo, por proveedor o por estado"]
    O --> P["Toma un reclamo como responsable, deja una nota y lo marca resuelto"]
    P --> Q["Deja de contarse entre los pendientes, y queda registrado que lo resolvió ella y cuándo"]

    A --> R["Recibe por WhatsApp, en su número registrado, los reclamos de pago y los avisos de vencimiento próximo"]
    R --> S["Le llegan en el momento dentro de la franja acordada; lo que entra fuera de hora espera al comienzo de la siguiente"]
    S --> T["Por el mismo mensaje le llega un solo aviso inmediato, no uno cada vez que el sistema lo procesa"]
    T --> U["Si un aviso no se pudo entregar, lo ve señalado en la pantalla de mensajes"]
```

## El sistema — qué hace con cada mensaje de la bandeja

```mermaid
---
title: El sistema — qué hace con cada mensaje de la bandeja
---
flowchart TD
    A["De modo que no pase más de una hora desde que aparece, trae los mensajes de la bandeja"] --> B{"¿Se puede determinar el tipo del mensaje?"}
    B -->|Sí| C["Lo clasifica como reclamo de pago, vencimiento próximo o stock bajo"]
    B -->|No| D["Lo muestra como sin clasificar, en lugar de descartarlo"]
    C --> E{"¿El remitente coincide con un proveedor del padrón?"}
    D --> E
    E -->|Sí| F["Lo muestra con su proveedor identificado"]
    E -->|No| G["Lo muestra señalando que el remitente quedó sin identificar"]
    F --> H["Lo registra como pendiente"]
    G --> H

    H --> I{"¿Es un reclamo de pago o un vencimiento próximo?"}
    I -->|No| J["Queda a la vista en la pantalla de mensajes, sin salir del sistema"]
    I -->|Sí| K{"¿Ya avisó por este mismo mensaje?"}
    K -->|Sí| J
    K -->|No| L{"¿Está dentro de la franja de avisos?"}
    L -->|No| M["Retiene el aviso hasta que comienza la franja siguiente"]
    L -->|Sí| N["Avisa por WhatsApp al número registrado de quien recibe ese tipo de aviso"]
    M --> N
    N --> O{"¿Se pudo entregar?"}
    O -->|Sí| P["Queda avisado una sola vez, aunque el mensaje se procese de nuevo"]
    O -->|No| Q["Registra el fallo y lo señala en la pantalla de mensajes"]

    R["A la hora configurada arma el resumen diario"] --> S["Reúne los mensajes que siguen pendientes y las órdenes señaladas como estancadas"]
    S --> T["Deja afuera lo que ya está resuelto"]
    T --> U["Lo envía por WhatsApp a quien tenga configurado el resumen"]

    V["Al ponerse en marcha, los mensajes que ya estaban en la bandeja quedan registrados como pendientes"] --> W["Por ellos no envía ningún aviso"]
    X["Una persona pierde el acceso al sistema"] --> Y["Deja de enviarle avisos"]
```

## El sistema — qué hace con cada orden de compra

```mermaid
---
title: El sistema — qué hace con cada orden de compra
---
flowchart TD
    A["Con la frecuencia configurada, trae del portal las órdenes de compra"] --> B{"¿Se puede identificar con certeza al proveedor de la orden?"}
    B -->|No| C["La aparta para revisión, sin asignarla al proveedor que más se le parece"]
    B -->|Sí| D["La registra con su proveedor, su fecha, su monto y su estado"]

    C --> C1["Queda en la lista con el nombre tal como llegó y señalada como sin identificar, y se cuenta aparte"]
    C1 --> C2["El dueño o compras piden ver sólo las apartadas y le asignan uno de los ocho proveedores del padrón"]
    C2 --> C3["Registra quién lo decidió y cuándo, la orden deja de figurar entre las apartadas y sigue el mismo camino que las demás"]
    C2 --> C6["Guarda esa forma de escribir el nombre como criterio y resuelve con ella las otras órdenes que estaban apartadas escritas igual"]
    C6 --> C3
    C6 --> C7["De ahí en más, la orden que llegue escrita así se identifica sola y no vuelve a preguntarse"]
    C3 --> D
    C1 --> C4["Si es de alguien que no está en el padrón, el motivo lo dice: no se da de alta un proveedor desde la revisión"]

    D --> E["Anota desde cuándo la viene viendo en ese estado"]
    E --> F{"¿El portal la muestra ahora en otro estado?"}
    F -->|Sí| G["Actualiza el estado, anota la fecha en que vio el cambio, y la antigüedad vuelve a cero"]
    F -->|No| H{"¿Está antes de la recepción y lleva más días que el límite configurado?"}
    G --> H
    H -->|Sí| I["La señala como estancada, y la incluye en el resumen diario una vez por día"]
    H -->|No| J["Queda en la lista, con su estado y sin señalar"]
    I --> K["Deja de estar señalada cuando avanza de estado o cuando la mercadería llega"]

    C1 --> C5["Mientras no se sepa de quién es, no se la señala como pedido repetido: no hay con qué compararla"]

    D --> L{"¿Ese producto ya se le pidió al mismo proveedor dentro de la ventana configurada?"}
    L -->|Sí| M["La señala como posible pedido repetido y muestra el pedido anterior"]
    L -->|No| J
    M --> N["El señalamiento no impide registrarla: quien decide si igual se pide es el negocio"]

    O["Las órdenes anteriores a la puesta en marcha se listan mostrando cuántos días pasaron desde el pedido"] --> P["El primer día ninguna queda señalada como estancada: el reloj arranca cuando el sistema empieza a mirar"]
```

