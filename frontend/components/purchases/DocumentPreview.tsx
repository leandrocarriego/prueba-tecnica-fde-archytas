import { Code } from '@/components/ui/amount'
import type { InvoiceDocument } from '@/lib/purchases/types'

/**
 * El original de una factura, mostrado y no sólo enlazado (`3g` de la guía).
 *
 * **Por qué se muestra acá adentro.** Lo que se decide en esta pantalla es si el
 * número de la tabla y el del papel son el mismo, y hasta ahora eso obligaba a
 * abrir el archivo en otra pestaña, mirarlo, volver y acordarse. El diseño pone
 * el documento al lado de los números por esa razón, y no por adorno: comparar
 * dos cosas que no están a la vista al mismo tiempo es comparar de memoria.
 *
 * **Cada formato se muestra como se puede mostrar, y el que no se puede lo
 * dice.** Un `<iframe>` para todo alcanza para un PDF, para una imagen y para un
 * texto, y deja un recuadro en blanco cuando lo que llegó fue una planilla —que
 * es uno de los dos formatos que el portal publica—. Un recuadro vacío es peor
 * que una frase: no dice que no se puede, deja pensando que algo se rompió.
 *
 * El original se sirve por `/api/proxy`, que es la única puerta del navegador
 * hacia la API: la sesión vive en una cookie que el JavaScript no lee, y el
 * proxy es quien la convierte en cabecera. Apuntar el `iframe` al backend
 * directamente mandaría una request sin credenciales — y, en el servidor, a un
 * host que el navegador no alcanza.
 */
export function DocumentPreview({
  invoiceId,
  document,
}: {
  invoiceId: number
  document: InvoiceDocument | null | undefined
}) {
  // Sin documento no hay nada que previsualizar, y la frase importa: significa
  // que lo que se ve arriba es lo que informó la tabla del portal y nada más.
  if (!document) {
    return (
      <p className="text-sm text-muted-foreground">
        El portal no publicó un archivo para esta factura. Lo que se ve arriba es lo que informó su
        tabla.
      </p>
    )
  }

  const href = `/api/proxy/invoices/${invoiceId}/file`
  const type = document.content_type ?? ''

  return (
    <div className="space-y-3">
      {/*
        Si el papel y la tabla dicen lo mismo, arriba de la prueba: es la
        conclusión, y la vista previa es en lo que se apoya.
      */}
      <p className="text-sm text-muted-foreground">
        {document.agrees
          ? 'Coincide con lo que informa el portal.'
          : (document.reason ?? 'No coincide con lo que informa el portal.')}
        {document.read_supplier_tax_id && (
          <>
            {' El archivo trae el CUIT '}
            <Code value={document.read_supplier_tax_id} />.
          </>
        )}
      </p>

      <Preview href={href} type={type} hasFile={document.has_file} excerpt={document.excerpt} />
    </div>
  )
}

/** El original, dibujado de la forma que su formato admite. */
function Preview({
  href,
  type,
  hasFile,
  excerpt,
}: {
  href: string
  type: string
  hasFile: boolean
  excerpt: string | null | undefined
}) {
  // Sin bytes que servir sólo queda lo que se pudo leer. No es un fallo: el
  // portal publica filas sin adjunto, y el recorte sigue siendo la evidencia.
  if (!hasFile) {
    return <Excerpt text={excerpt} />
  }

  if (type.startsWith('image/')) {
    return (
      <a href={href} rel="noreferrer" target="_blank" className="block">
        {/*
          `<img>` y no `next/image`: el original lo sirve el proxy con la cookie
          de la sesión, y el optimizador de Next lo pediría desde el servidor,
          sin ella. Además no es una imagen del producto — es un documento de un
          tamaño que nadie eligió.
        */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={href}
          alt="El original de la factura, como lo publicó el portal"
          className="max-h-96 w-full rounded-lg border border-border bg-muted object-contain"
        />
      </a>
    )
  }

  if (type === 'application/pdf' || type.startsWith('text/')) {
    return (
      <iframe
        src={href}
        title="El original de la factura, como lo publicó el portal"
        className="h-96 w-full rounded-lg border border-border bg-muted"
      />
    )
  }

  // Una planilla, o cualquier cosa que el navegador no dibuja. Se dice qué es y
  // se ofrece abrirla, en lugar de dejar un marco vacío.
  return (
    <div className="space-y-3 rounded-lg border border-border bg-muted p-4">
      <p className="text-sm text-muted-foreground">
        El original es un archivo que el navegador no puede mostrar acá
        {type && (
          <>
            {' ('}
            <Code value={type} />)
          </>
        )}
        . Se abre o se descarga con «Ver original», arriba.
      </p>
      <Excerpt text={excerpt} />
    </div>
  )
}

/** Lo que se pudo leer del archivo, que es la evidencia cuando no hay vista. */
function Excerpt({ text }: { text: string | null | undefined }) {
  return (
    <pre className="max-h-56 overflow-auto rounded-lg border border-border bg-muted p-3 text-xs">
      {text || 'Sin contenido legible.'}
    </pre>
  )
}
