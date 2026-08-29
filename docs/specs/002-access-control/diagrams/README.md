<!-- GENERADO por scripts/diagrams/export.sh — NO editar a mano.
     Fuente: los .mmd de esta carpeta. Regenerar: scripts/diagrams/export.sh -->

# Diagramas

> Vista renderizada de los diagramas de esta feature. Fuente: los `.mmd` de esta
> carpeta. Convención: `docs/specs/DIAGRAMS.md`. Las imágenes para el cliente se
> generan en `dist/diagramas/` con `make diagrams`.

## El ciclo de vida de un acceso

```mermaid
---
title: El ciclo de vida de un acceso
---
stateDiagram-v2
    state "Invitado, sin clave definida" as Invitado
    state "Activo" as Activo
    state "Bloqueado por intentos fallidos" as Bloqueado
    state "Desactivado" as Desactivado

    [*] --> Invitado: el dueño lo da de alta con la persona, su teléfono y su rol
    Invitado --> Activo: la persona define su clave desde la invitación
    Activo --> Bloqueado: más intentos fallidos seguidos que el límite
    Bloqueado --> Activo: vence el tiempo del bloqueo
    Activo --> Desactivado: el dueño lo desactiva
    Invitado --> Desactivado: el dueño lo desactiva antes de que acepte la invitación
    Bloqueado --> Desactivado: el dueño lo desactiva
    Desactivado --> Invitado: la persona vuelve al equipo y el dueño reactiva su acceso
    Desactivado --> [*]

    note right of Invitado
        Mientras no defina su clave no puede entrar.
        El dueño nunca la conoce ni se la puede poner
    end note

    note right of Bloqueado
        No entra ni con la clave correcta, y el bloqueo
        queda a la vista del dueño entre los intentos
        rechazados
    end note

    note right of Desactivado
        Deja de entrar en el momento y sus sesiones
        abiertas se cierran, pero su nombre sigue
        figurando en todo lo que registró. Si vuelve,
        es la misma persona: define una clave nueva y
        la anterior ya no sirve
    end note
```

## El ciclo de vida de una sesión

```mermaid
---
title: El ciclo de vida de una sesión
---
stateDiagram-v2
    state "Abierta" as Abierta
    state "Cerrada" as Cerrada

    [*] --> Abierta: la persona entra con su acceso
    Abierta --> Cerrada: la persona cierra su sesión
    Abierta --> Cerrada: pasa el tiempo de inactividad sin uso, ocho horas al arrancar
    Abierta --> Cerrada: el dueño desactiva ese acceso
    Cerrada --> [*]

    note right of Abierta
        La pantalla muestra el nombre de quien trabaja,
        y cada consulta se verifica igual, una por una
    end note

    note right of Cerrada
        Volver atrás en el navegador no devuelve la
        pantalla anterior con datos: hay que entrar
        de nuevo
    end note
```

## El dueño — administra los accesos y mira quién entró

```mermaid
---
title: El dueño — administra los accesos y mira quién entró
---
flowchart TD
    A["El dueño entra con su propio acceso"] --> B["Ve todas las secciones del sistema"]
    A --> C["Abre la administración de accesos"]

    C --> D{"¿Qué necesita hacer?"}
    D -->|Sumar a alguien| E["Carga la persona, su correo, su teléfono y uno de los tres roles"]
    E --> F["El sistema le manda la invitación para que ella defina su clave"]
    F --> G["Mientras no la defina, ese acceso no entra"]

    D -->|Cambiar lo que ve alguien| H["Le cambia el rol al acceso"]
    H --> I{"¿Lo quiere poner como dueño?"}
    I -->|Sí| J["El sistema no lo permite: el dueño es uno solo"]
    I -->|No| K["Al volver a entrar, esa persona ve las secciones de su rol nuevo"]

    D -->|Alguien deja el equipo| L["Desactiva su acceso"]
    L --> M["Sus sesiones abiertas se cierran y ya no puede entrar"]
    M --> N["Su nombre sigue figurando en todo lo que registró"]

    D -->|Alguien vuelve al equipo| V["Reactiva su acceso"]
    V --> W["El sistema le manda una invitación nueva para que ella defina otra clave"]
    W --> X["La clave que usaba antes no vuelve a servir"]
    X --> Y["Sigue siendo la misma persona: lo viejo y lo nuevo figuran bajo un solo nombre"]

    D -->|Sacarse a sí mismo| O["El sistema no lo permite"]

    E --> P["Cada alta, cambio de rol y desactivación queda registrado con qué cambió, quién y cuándo"]
    H --> P
    L --> P
    V --> P

    A --> Q["Abre la lista de ingresos e intentos rechazados"]
    Q --> R["Quién entró y cuándo"]
    Q --> S["A quién se le negó el paso, qué quiso ver y cuándo"]
    Q --> T["Qué accesos quedaron bloqueados por intentos fallidos"]

    B --> U["Ajusta desde los parámetros el tiempo de sesión y el límite de intentos"]
```

## Accesos por persona — de punta a punta

```mermaid
---
title: Accesos por persona — de punta a punta
---
sequenceDiagram
    autonumber
    actor Duenio as El dueño
    participant Sistema as El sistema
    actor Marcela as Marcela, compras
    actor Julian as Julián, ventas

    Duenio->>Sistema: Da de alta un acceso con la persona, su correo, su teléfono y su rol
    Sistema-->>Marcela: Le manda una invitación por WhatsApp
    Note over Sistema,Marcela: Hasta que no define su clave, ese acceso no entra.<br/>El dueño nunca la conoce ni se la puede poner
    Marcela->>Sistema: Define su propia clave desde la invitación
    Sistema->>Sistema: El acceso queda activo

    Marcela->>Sistema: Entra con su acceso
    Sistema->>Sistema: Registra quién ingresó y cuándo
    Sistema-->>Marcela: Muestra su nombre en pantalla y sólo sus secciones

    Julian->>Sistema: Entra y pega la dirección de la pantalla de proveedores
    Sistema->>Sistema: Verifica el permiso antes de responder
    Sistema-->>Julian: Le avisa que no tiene permiso, en lugar de mostrarle la pantalla
    Sistema->>Sistema: Registra el intento con su nombre, qué quiso ver y cuándo

    Julian->>Sistema: Abre el calendario de vencimientos e intenta mover uno
    Sistema-->>Julian: Lo deja consultarlo y le rechaza el cambio

    alt Marcela olvida su clave
        Marcela->>Sistema: Pide recuperar su acceso
        Sistema-->>Marcela: Le manda un enlace por WhatsApp, sin que el dueño intervenga
        Marcela->>Sistema: Define una clave nueva y la anterior deja de servir
    end

    alt Alguien prueba claves hasta acertar
        Sistema->>Sistema: Al quinto intento fallido seguido bloquea ese acceso quince minutos
        Sistema-->>Duenio: El bloqueo aparece entre los intentos rechazados que él ve
    end

    Duenio->>Sistema: Mira quién entró y a quién se le negó el paso
    Duenio->>Sistema: Desactiva el acceso de quien deja el equipo
    Sistema->>Sistema: Cierra sus sesiones y conserva su nombre en todo lo que registró

    alt Esa persona vuelve al equipo
        Duenio->>Sistema: Reactiva su acceso
        Sistema-->>Marcela: Le manda por WhatsApp una invitación nueva para definir otra clave
        Note over Sistema,Marcela: La clave anterior no vuelve a servir.<br/>Es la misma persona: su historial no se parte en dos
    end
```

## Julián, ventas — con qué entra y hasta dónde llega

```mermaid
---
title: Julián, ventas — con qué entra y hasta dónde llega
---
flowchart TD
    A["Entra con su acceso y la pantalla muestra su nombre"] --> B["Ve sólo las secciones de ventas"]
    B --> C["Ventas, tablero comercial, stock, rubros y catálogo"]

    B --> D["Precios: los consulta y ve su evolución"]
    D --> E["Pedir la lista a mano y resolver lo apartado no es suyo"]

    B --> F["Calendario de vencimientos: lo consulta"]
    F --> G{"¿Puede mover un vencimiento?"}
    G -->|No| H["El sistema le rechaza el cambio aunque vea la pantalla"]

    B --> I["Proveedores, facturas de compra y pagos: no aparecen en su menú"]
    I --> J["Copia la dirección exacta de la pantalla de proveedores y la abre"]
    J --> K["El sistema le avisa que no tiene permiso, en lugar de mostrársela"]
    K --> L["El intento queda registrado con su nombre, qué quiso ver y cuándo"]
    L --> M["El dueño lo ve en su lista de intentos rechazados"]

    B --> N["La administración de accesos y la lista de ingresos no son suyas"]
```

## Marcela, compras — con qué entra y hasta dónde llega

```mermaid
---
title: Marcela, compras — con qué entra y hasta dónde llega
---
flowchart TD
    A["Le llega la invitación por WhatsApp"] --> B["Define su propia clave"]
    B --> C["Entra con su acceso y la pantalla muestra su nombre"]
    C --> D["Ve sólo las secciones de compras"]

    D --> E["Proveedores, facturas, pagos, órdenes y recibos"]
    D --> F["Calendario de vencimientos: lo consulta y lo edita"]
    D --> G["Precios: los consulta, pide la lista a mano y resuelve lo apartado"]
    D --> H["Ventas y tablero comercial: no aparecen en su menú"]
    H --> I{"¿Y si pega la dirección de esa pantalla?"}
    I -->|Queda afuera igual| J["El sistema le avisa que no tiene permiso y registra el intento"]

    C --> K{"¿Qué pasa con su clave?"}
    K -->|La quiere cambiar| L["La cambia desde su propia pantalla y la anterior deja de servir"]
    K -->|Se la olvidó| M["Pide recuperar su acceso"]
    M --> N["Le llega un enlace por WhatsApp, sin que el dueño intervenga"]
    N --> O["Define una clave nueva y el enlace deja de servir"]
    K -->|La erró varias veces seguidas| P["Su acceso queda bloqueado un rato y el dueño lo ve"]

    C --> Q{"¿Dejó la pantalla abierta sin usarla?"}
    Q -->|Ocho horas sin uso| R["El sistema cierra la sesión y le pide entrar de nuevo"]
```

## El sistema — qué controla en cada ingreso y en cada consulta

```mermaid
---
title: El sistema — qué controla en cada ingreso y en cada consulta
---
flowchart TD
    A["Alguien presenta sus credenciales"] --> B{"¿Corresponden a un acceso que existe y está activo?"}
    B -->|No| C["Rechaza el ingreso sin decir cuál de los dos datos falló"]
    C --> D["Cuenta el intento fallido de ese acceso"]
    D --> E{"¿Superó el límite de intentos seguidos?"}
    E -->|No| F["Queda a la espera del próximo intento"]
    E -->|Sí| G["Bloquea ese acceso quince minutos y lo registra entre los intentos rechazados"]
    G --> H{"¿Venció el tiempo del bloqueo?"}
    H -->|Sí| I["Vuelve a permitir el ingreso de ese acceso"]

    B -->|Sí| J{"¿Ese acceso está bloqueado por intentos fallidos?"}
    J -->|Sí| K["Rechaza el ingreso aunque la clave sea correcta"]
    J -->|No| L["Deja entrar y registra quién ingresó y cuándo"]
    L --> M["Muestra el nombre de quien trabaja y sólo las secciones de su rol"]

    M --> N["Le llega una consulta"]
    N --> O{"¿Viene con una sesión activa?"}
    O -->|No| P["La rechaza y pide entrar"]
    O -->|Sí| Q{"¿El rol tiene habilitada esa sección?"}
    Q -->|No| R["Rechaza la consulta, lo informa y registra el intento"]
    Q -->|Sí| S{"¿La consulta cambia algo?"}
    S -->|No| T["Responde"]
    S -->|Sí| U{"¿La sección está habilitada como edición para ese rol?"}
    U -->|No| R
    U -->|Sí| T

    M --> V{"¿La sesión pasó el tiempo de inactividad sin uso?"}
    V -->|Sí| W["La cierra y vuelve a pedir entrar"]
    M --> X{"¿El dueño desactivó ese acceso?"}
    X -->|Sí| W
```

