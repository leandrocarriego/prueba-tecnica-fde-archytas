import type { Metadata } from 'next'
import { IBM_Plex_Mono, Instrument_Sans } from 'next/font/google'
import { Toaster } from '@/components/ui/toast'
import './globals.css'

// Two typefaces, and the split is the design system's ("taller ordenado"):
// Instrument Sans carries every piece of text, IBM Plex Mono carries money,
// dates and codes so their columns line up. Both are exposed as CSS variables
// that `app/globals.css` feeds to Tailwind's `font-sans` / `font-mono`.
const sans = Instrument_Sans({
  subsets: ['latin'],
  variable: '--font-instrument-sans',
  display: 'swap',
})

const mono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-plex-mono',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Plataforma Cordillera',
  description: 'Plataforma de gestión de Ferretería Industrial Cordillera',
}

// There is no theme script here any more, and that is the point: the platform
// has one theme, the light one (`app/globals.css` explains why). What used to
// be here read the operating system's preference and switched the whole app to
// a dark theme nobody could turn off.
//
// `suppressHydrationWarning` went with it: it was there because that script
// wrote a class onto <html> before React arrived. With one theme, the server
// and the browser render the same markup, and silencing the warning would only
// hide a real mismatch the day one appears.

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`${sans.variable} ${mono.variable}`}>
      <body className="font-sans antialiased">
        {children}
        <Toaster />
      </body>
    </html>
  )
}
