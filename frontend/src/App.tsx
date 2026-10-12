import { Routes, Route, Navigate } from 'react-router-dom'
import { Dashboard } from '@/components/Dashboard'
import { SessionsList } from '@/components/SessionsList'
import { SessionDetail } from '@/components/SessionDetail'
import { HealthCheck } from '@/components/HealthCheck'
import { Layout } from '@/components/Layout'

function App() {
  return (
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
  )
}

export default App