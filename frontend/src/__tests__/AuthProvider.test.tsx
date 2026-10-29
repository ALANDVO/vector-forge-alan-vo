import { render, screen, act, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ReactNode } from 'react'
import { AuthProvider, useAuth } from '@/auth/AuthProvider'

// Mock apiClient
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    health: vi.fn(),
  },
}))

import { apiClient } from '@/api/client'

// Test component that uses useAuth
const TestComponent = () => {
  const { user, isLoading, isAuthenticated, login, logout, refreshUser, hasRole, hasAnyRole } = useAuth()
  
  return (
    <div>
      <div data-testid="user-id">{user?.user_id ?? 'null'}</div>
      <div data-testid="is-loading">{isLoading.toString()}</div>
      <div data-testid="is-authenticated">{isAuthenticated.toString()}</div>
      <div data-testid="user-roles">{user?.roles.join(',') ?? 'null'}</div>
      <button onClick={login} data-testid="login-btn">Login</button>
      <button onClick={logout} data-testid="logout-btn">Logout</button>
      <button onClick={refreshUser} data-testid="refresh-btn">Refresh</button>
      <div data-testid="has-viewer">{hasRole('viewer').toString()}</div>
      <div data-testid="has-admin">{hasRole('admin').toString()}</div>
      <div data-testid="has-any-viewer-admin">{hasAnyRole(['viewer', 'admin']).toString()}</div>
      <div data-testid="has-any-operator-admin">{hasAnyRole(['operator', 'admin']).toString()}</div>
    </div>
  )
}

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>{children}</AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('AuthProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default: not authenticated
    ;(apiClient.get as any).mockRejectedValue(new Error('Not authenticated'))
    ;(apiClient.post as any).mockResolvedValue({ data: { message: 'OK' } })
    ;(apiClient.health as any).mockResolvedValue({
      data: { status: 'ok', demo_mode: true, oidc_enabled: false }
    })
  })

  it('provides auth context to children', () => {
    const Wrapper = createWrapper()
    render(<TestComponent />, { wrapper: Wrapper })
    
    expect(screen.getByTestId('user-id')).toHaveTextContent('null')
    expect(screen.getByTestId('is-loading')).toHaveTextContent('true')
    expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false')
  })

  it('loads user on mount when authenticated', async () => {
    const mockUser = {
      user_id: 'demo-user',
      roles: ['viewer', 'operator'],
      email: 'demo@local',
      name: 'Demo User'
    }
    ;(apiClient.get as any).mockResolvedValue({ data: mockUser })
    
    const Wrapper = createWrapper()
    render(<TestComponent />, { wrapper: Wrapper })
    
    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false')
    })
    
    expect(screen.getByTestId('user-id')).toHaveTextContent('demo-user')
    expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true')
    expect(screen.getByTestId('user-roles')).toHaveTextContent('viewer,operator')
  })

  it('hasRole returns true for user role', async () => {
    const mockUser = {
      user_id: 'demo-user',
      roles: ['viewer', 'operator'],
      email: 'demo@local',
      name: 'Demo User'
    }
    ;(apiClient.get as any).mockResolvedValue({ data: mockUser })
    
    const Wrapper = createWrapper()
    render(<TestComponent />, { wrapper: Wrapper })
    
    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false')
    })
    
    expect(screen.getByTestId('has-viewer')).toHaveTextContent('true')
    expect(screen.getByTestId('has-admin')).toHaveTextContent('false')
  })

  it('hasAnyRole returns true when user has any of the roles', async () => {
    const mockUser = {
      user_id: 'demo-user',
      roles: ['viewer'],
      email: 'demo@local',
      name: 'Demo User'
    }
    ;(apiClient.get as any).mockResolvedValue({ data: mockUser })
    
    const Wrapper = createWrapper()
    render(<TestComponent />, { wrapper: Wrapper })
    
    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false')
    })
    
    expect(screen.getByTestId('has-any-viewer-admin')).toHaveTextContent('true')
    expect(screen.getByTestId('has-any-operator-admin')).toHaveTextContent('false')
  })

  it('login redirects to /auth/login', () => {
    const Wrapper = createWrapper()
    render(<TestComponent />, { wrapper: Wrapper })
    
    const originalLocation = window.location.href
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(window as any).location = { href: '' }
    
    act(() => {
      screen.getByTestId('login-btn').click()
    })
    
    expect(window.location.href).toBe('/auth/login')
    
    // Restore
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(window as any).location = { href: originalLocation }
  })

  it('logout calls API and clears user', async () => {
    const mockUser = {
      user_id: 'demo-user',
      roles: ['viewer', 'operator'],
      email: 'demo@local',
      name: 'Demo User'
    }
    ;(apiClient.get as any).mockResolvedValue({ data: mockUser })
    ;(apiClient.post as any).mockResolvedValue({ data: { message: 'Logged out successfully' } })
    
    const Wrapper = createWrapper()
    render(<TestComponent />, { wrapper: Wrapper })
    
    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false')
    })
    
    expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true')
    
    act(() => {
      screen.getByTestId('logout-btn').click()
    })
    
    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/auth/logout')
      expect(screen.getByTestId('user-id')).toHaveTextContent('null')
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false')
    })
  })

  it('refreshUser re-fetches user', async () => {
    const mockUser = {
      user_id: 'demo-user',
      roles: ['viewer', 'operator'],
      email: 'demo@local',
      name: 'Demo User'
    }
    ;(apiClient.get as any).mockResolvedValue({ data: mockUser })
    
    const Wrapper = createWrapper()
    render(<TestComponent />, { wrapper: Wrapper })
    
    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false')
    })
    
    // Clear mock calls
    vi.clearAllMocks()
    ;(apiClient.get as any).mockResolvedValue({ data: { ...mockUser, roles: ['viewer', 'operator', 'admin'] } })
    
    act(() => {
      screen.getByTestId('refresh-btn').click()
    })
    
    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/auth/me')
    })
  })

  it('handles API error gracefully', async () => {
    ;(apiClient.get as any).mockRejectedValue(new Error('Network error'))
    
    const Wrapper = createWrapper()
    render(<TestComponent />, { wrapper: Wrapper })
    
    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false')
    })
    
    expect(screen.getByTestId('user-id')).toHaveTextContent('null')
    expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false')
  })
})
