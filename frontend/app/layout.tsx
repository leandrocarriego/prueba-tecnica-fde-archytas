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

// Apply the persisted theme before hydration, so the page does not flash the
// wrong one. The key is namespaced to this product.
const themeInitScript = `
(function () {
  try {
    var stored = localStorage.getItem('cordillera-theme');
    var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (stored === 'dark' || (!stored && prefersDark)) {
      document.documentElement.classList.add('dark');
    }
  } catch (e) {}
})();
`

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="es" className={outfit.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="font-sans antialiased">
        {children}
        <Toaster />
      </body>
    </html>
  )
}
