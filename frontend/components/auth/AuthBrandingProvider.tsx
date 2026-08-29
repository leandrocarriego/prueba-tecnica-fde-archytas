'use client'

import React, { createContext, useContext, ReactNode } from 'react'
import { AuthBrandingConfig, getBrandingConfig } from '@/lib/branding'

const BrandingContext = createContext<AuthBrandingConfig | null>(null)

export function AuthBrandingProvider({ children }: { children: ReactNode }) {
  const config = getBrandingConfig()

  return <BrandingContext.Provider value={config}>{children}</BrandingContext.Provider>
}

export function useBranding() {
  const context = useContext(BrandingContext)
  if (!context) {
    throw new Error('useBranding must be used within AuthBrandingProvider')
  }
  return context
}
