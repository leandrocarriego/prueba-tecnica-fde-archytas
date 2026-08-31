import type { Metadata } from 'next'
import { Outfit } from 'next/font/google'
import { Toaster } from '@/components/ui/toast'
import './globals.css'

// Outfit is the platform's typeface. Exposed as a CSS variable so Tailwind's
// `font-sans` picks it up.
const outfit = Outfit({ subsets: ['latin'], variable: '--font-sans', display: 'swap' })

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
    <html lang="es" className={outfit.variable}>
      <body className="font-sans antialiased">
        {children}
        <Toaster />
      </body>
    </html>
  )
}
