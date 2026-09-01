import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

/**
 * El período de **un** corte, sin tocar el de los demás (RF-05 de 009).
 *
 * Es un `form` con `method="get"` y nada de JavaScript: navegar cambia la URL,
 * y la pantalla se rearma en el servidor. Lo que hace que el corte de al lado no
 * se mueva son los campos ocultos: un `GET` reemplaza **toda** la query, así que
 * el período del otro corte tiene que viajar con éste para sobrevivir.
 *
 * Sin eso, cambiar el período de los precios reseteaba el de la facturación —
 * que es exactamente lo que RF-05 dice que no puede pasar.
 */
export function PeriodPicker({
  fromName,
  toName,
  from,
  to,
  keep,
}: {
  fromName: string
  toName: string
  from?: string
  to?: string
  keep: Record<string, string | undefined>
}) {
  return (
    <form method="get" className="flex flex-wrap items-end gap-2 text-xs text-muted-foreground">
      {Object.entries(keep).map(([name, value]) =>
        value ? <input key={name} type="hidden" name={name} value={value} /> : null
      )}
      <label className="flex flex-col gap-1">
        Desde
        <Input type="date" name={fromName} defaultValue={from ?? ''} />
      </label>
      <label className="flex flex-col gap-1">
        Hasta
        <Input type="date" name={toName} defaultValue={to ?? ''} />
      </label>
      <Button type="submit" variant="outline">
        Ver este período
      </Button>
    </form>
  )
}
