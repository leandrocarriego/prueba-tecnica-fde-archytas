'use client'

// Toast — sonner, con el helper `useToast().addToast(...)` que usa la app.
// Vive acá para que los call sites importen siempre de `@/components/ui/toast`
// y cambiar de librería no toque ninguna pantalla.
import { Toaster, toast } from 'sonner'

export { Toaster, toast }

export function useToast() {
  return {
    addToast: (options: {
      type: 'success' | 'error' | 'info' | 'warning'
      title: string
      description?: string
      duration?: number
    }) => {
      const { type, title, description, duration = 5000 } = options
      switch (type) {
        case 'success':
          toast.success(title, { description, duration })
          break
        case 'error':
          toast.error(title, { description, duration })
          break
        case 'warning':
          toast.warning(title, { description, duration })
          break
        case 'info':
          toast.info(title, { description, duration })
          break
      }
    },
  }
}
