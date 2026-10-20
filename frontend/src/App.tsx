import { AuthProvider } from '@/auth/AuthProvider'
import { LoginPage } from '@/auth/LoginPage'
import { LoginCallback } from '@/auth/LoginCallback'
import { useAuth } from '@/auth/AuthProvider'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Dashboard } from '@/components/Dashboard'
import { SessionsList } from '@/components/SessionsList'
import { SessionDetail } from '@/components/SessionDetail'
import { HealthCheck } from '@/components/HealthCheck'
import { Layout } from '@/components/Layout'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/callback" element={<LoginCallback />} />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/sessions" element={<SessionsList />} />
                  <Route path="/sessions/:sessionId" element={<SessionDetail />} />
                  <Route path="/health" element={<HealthCheck />} />
                  <Route path="*" element={<Navigate to="/dashboard" replace />} />
                </Routes>
              </Layout>
            </PrivateRoute>
          }
        />
      </Routes>
    </AuthProvider>
  )
}

export default App