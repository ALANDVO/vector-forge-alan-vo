import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { apiClient } from '@/api/client'

interface User {
  user_id: string
  roles: string[]
  email?: string
  name?: string
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: () => void
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
  hasRole: (role: string) => boolean
  hasAnyRole: (roles: string[]) => boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    try {
      const response = await apiClient.get('/auth/me')
      setUser(response.data)
    } catch {
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshUser()
  }, [refreshUser])

  const login = useCallback(() => {
    window.location.href = '/auth/login'
  }, [])

  const logout = useCallback(async () => {
    try {
      await apiClient.post('/auth/logout')
    } catch {
      // Ignore logout errors
    } finally {
      setUser(null)
      // Redirect to Keycloak logout if configured
      try {
        const response = await apiClient.get('/auth/logout')
        if (response.data.logout_url) {
          window.location.href = response.data.logout_url
          return
        }
      } catch {
        // Ignore
      }
      window.location.href = '/'
    }
  }, [])

  const hasRole = useCallback((role: string) => {
    return user?.roles.includes(role) ?? false
  }, [user])

  const hasAnyRole = useCallback((roles: string[]) => {
    return user?.roles.some(r => roles.includes(r)) ?? false
  }, [user])

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        refreshUser,
        hasRole,
        hasAnyRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}