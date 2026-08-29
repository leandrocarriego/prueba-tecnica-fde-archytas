'use client'

import { useEffect, useState } from 'react'

/**
 * Client auth state for guards. Auth is an httpOnly cookie (not readable in JS), so we probe the
 * authenticated `/auth/me` endpoint through the proxy (which injects the Bearer token from the cookie).
 */
export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    fetch('/api/proxy/auth/me', { method: 'GET', cache: 'no-store' })
      .then(res => {
        if (active) {
          setIsAuthenticated(res.ok)
          setLoading(false)
        }
      })
      .catch(() => {
        if (active) {
          setIsAuthenticated(false)
          setLoading(false)
        }
      })
    return () => {
      active = false
    }
  }, [])

  return { isAuthenticated, loading }
}
