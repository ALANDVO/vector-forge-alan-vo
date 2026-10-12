import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import App from '@/App'

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('App', () => {
  it('renders without crashing', () => {
    const Wrapper = createWrapper()
    render(<App />, { wrapper: Wrapper })
    // App renders routes, check for dashboard title (h1)
    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })
})

describe('Dashboard', () => {
  it('renders dashboard title', () => {
    const Wrapper = createWrapper()
    render(<App />, { wrapper: Wrapper })
    expect(screen.getByText('Reverse engineering analysis overview')).toBeInTheDocument()
  })
})