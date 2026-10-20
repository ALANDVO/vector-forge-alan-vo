import { useState, useEffect } from 'react'
 import { useSearchParams } from 'react-router-dom'
 import { useAuth } from './AuthProvider'
import { AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { apiClient } from '@/api/client'

export function LoginPage() {
  const { login, isLoading } = useAuth()
  const [searchParams] = useSearchParams()
  const error = searchParams.get('error')

  const handleDemoLogin = async () => {
    try {
      await apiClient.get('/auth/login')
      window.location.href = '/dashboard'
    } catch {
      // The login endpoint redirects, so this won't be reached in demo mode
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Sign in to Vector Forge</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 p-3 rounded border border-red-200">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="space-y-3">
            <Button
              className="w-full"
              size="lg"
              onClick={handleDemoLogin}
              disabled={isLoading}
            >
              Continue with Demo Mode (Localhost)
            </Button>

            <Button
              className="w-full"
              size="lg"
              variant="outline"
              onClick={login}
              disabled={isLoading}
            >
              Sign in with Keycloak (OIDC)
            </Button>
        </div>

        <div className="space-y-1 text-center text-sm text-muted-foreground">
          <p>Demo mode only works from localhost (127.0.0.1)</p>
          <p className="mt-1">For production, configure Keycloak OIDC in environment variables</p>
        </div>

        <div className="pt-4 border-t">
            <h4 className="text-sm font-medium mb-2">System Status</h4>
            <SystemStatus />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function SystemStatus() {
  const [health, setHealth] = useState<{
    status?: string
    demo_mode?: boolean
    oidc_enabled?: boolean
  }>({})

  useEffect(() => {
    apiClient.health().then(setHealth).catch(console.error)
  }, [])

  if (!health.status) {
    return <div className="text-sm text-muted-foreground">Loading...</div>
  }

  return (
    <div className="space-y-1 text-sm">
      <div className="flex justify-between">
        <span>Environment:</span>
        <span className="font-medium">{health.demo_mode ? 'Development (Demo)' : 'Production'}</span>
      </div>
      <div className="flex justify-between">
        <span>OIDC:</span>
        <span className="font-medium">{health.oidc_enabled ? 'Configured' : 'Not configured'}</span>
      </div>
      <div className="flex justify-between">
        <span>Status:</span>
        <span className="font-medium">{health.status}</span>
      </div>
    </div>
  )
}
