import Link from 'next/link'

import { Button } from '@/components/ui/button'
import { Notice } from '@/components/ui/notice'
import { count } from '@/lib/format'

/**
 * Lo que un indicador dejó afuera, **arriba** del número (`RF-14`, `RF-15`).
 *
 * Es la única parte de esta feature donde cambia el orden del contenido, y la
 * spec lo pide con todas las letras: el aviso estaba debajo del importe, en un
 * renglón gris del mismo tamaño que el resto, así que se leía el número —o se
 * lo copiaba a un mensaje— sin haber pasado nunca por la advertencia de que no
 * estaba completo. Primero se dice si se puede confiar en el dato; después se
 * lo muestra.
 *
 * Y lleva su salida (`RF-15`): un aviso que dice «faltan 12 registros» y no
 * dice dónde verlos no es un aviso, es una queja.
 *
 * **Acá se gasta el único naranja del tablero** (`UI-05`). La guía visual lo
 * dibuja así en `3b` —franja ámbar arriba de todo, con el botón de obra a la
 * derecha— y es coherente con lo que el naranja significa: resolver lo que
 * quedó afuera es *la* tarea de esta pantalla; todo lo demás es mirar.
 */
export function Excluded({
  howMany,
  href,
  children,
}: {
  howMany: number
  href?: string
  children?: React.ReactNode
}) {
  if (howMany === 0) return null

  return (
    <Notice
      tone="warn"
      title={
        howMany === 1
          ? 'Este total deja 1 registro afuera'
          : `Este total deja ${count(howMany)} registros afuera`
      }
      action={
        href ? (
          <Button asChild variant="brand" size="sm">
            <Link href={href}>Ver cuáles</Link>
          </Button>
        ) : undefined
      }
    >
      {children}
    </Notice>
  )
}
