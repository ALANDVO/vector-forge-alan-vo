import { render, screen, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ReactNode } from 'react'
import App from '@/App'
import { AuthProvider } from '@/auth/AuthProvider'

// Mock apiClient
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    health: vi.fn(),
  },
}))

import { apiClient } from '@/api/client'

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

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(apiClient.get as any).mockRejectedValue(new Error('Not authenticated'))
    ;(apiClient.post as any).mockResolvedValue({ data: { message: 'OK' } })
    ;(apiClient.health as any).mockResolvedValue({
      data: { status: 'ok', demo_mode: true, oidc_enabled: false }
    })
  })

  it('renders without crashing (shows login page when not authenticated)', async () => {
    const Wrapper = createWrapper()
    render(<App />, { wrapper: Wrapper })

    // Wait for auth loading to complete
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 100))
    })

    // Should show login page
    expect(screen.getByText('Sign in to Vector Forge')).toBeInTheDocument()
  })
})