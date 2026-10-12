import { useQuery } from '@tanstack/react-query'
import { Database, Activity, CheckCircle, AlertCircle, Wifi, WifiOff, Cpu, HardDrive } from 'lucide-react'
import { apiClient } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { clsx } from 'clsx'

interface HealthResponse {
  status: string
  version: string
  environment: string
  database: string
  demo_mode: boolean
  oidc_enabled: boolean
}

export function HealthCheck() {
  const { data: health, isLoading, error, refetch } = useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: () => apiClient.health(),
    refetchInterval: 10000,
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">System Health</h1>
          <p className="text-muted-foreground mt-1">
            Monitor the status of Vector Forge services
          </p>
        </div>
        <Button variant="outline" onClick={() => refetch()} disabled={isLoading}>
          <Activity className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">API Status</CardTitle>
            {isLoading ? (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            ) : error ? (
              <Badge variant="destructive">Error</Badge>
            ) : health?.status === 'ok' ? (
              <Badge variant="default">Healthy</Badge>
            ) : (
              <Badge variant="secondary">Degraded</Badge>
            )}
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className={clsx(
                'p-3 rounded-lg',
                health?.status === 'ok' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
              )}>
                <CheckCircle className="w-6 h-6" />
              </div>
              <div>
                <p className="text-2xl font-bold">{health?.status || 'Unknown'}</p>
                <p className="text-xs text-muted-foreground">Overall system status</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Database</CardTitle>
            {health?.database === 'ok' ? (
              <Badge variant="default">Connected</Badge>
            ) : (
              <Badge variant="destructive">Disconnected</Badge>
            )}
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className={clsx(
                'p-3 rounded-lg',
                health?.database === 'ok' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
              )}>
                <Database className="w-6 h-6" />
              </div>
              <div>
                <p className="text-2xl font-bold">{health?.database || 'Unknown'}</p>
                <p className="text-xs text-muted-foreground">SQLite persistent storage</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Authentication</CardTitle>
            {health?.demo_mode ? (
              <Badge variant="secondary">Demo Mode</Badge>
            ) : health?.oidc_enabled ? (
              <Badge variant="default">OIDC Enabled</Badge>
            ) : (
              <Badge variant="destructive">Not Configured</Badge>
            )}
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className={clsx(
                'p-3 rounded-lg',
                health?.demo_mode ? 'bg-blue-100 text-blue-600' :
                health?.oidc_enabled ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
              )}>
                {health?.demo_mode ? <HardDrive className="w-6 h-6" /> : health?.oidc_enabled ? <Wifi className="w-6 h-6" /> : <WifiOff className="w-6 h-6" />}
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {health?.demo_mode ? 'Local' : health?.oidc_enabled ? 'OIDC' : 'None'}
                </p>
                <p className="text-xs text-muted-foreground">
                  {health?.demo_mode ? 'Localhost access only' : health?.oidc_enabled ? 'Keycloak OIDC' : 'Not configured'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Version</CardTitle>
            <Badge variant="outline">{health?.version || 'Unknown'}</Badge>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-lg bg-primary/10 text-primary">
                <Cpu className="w-6 h-6" />
              </div>
              <div>
                <p className="text-2xl font-bold">{health?.version || 'Unknown'}</p>
                <p className="text-xs text-muted-foreground">Vector Forge API</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Info */}
      <Card>
        <CardHeader>
          <CardTitle>System Information</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Environment</span>
              <span className="font-mono">{health?.environment || 'Unknown'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Demo Mode</span>
              <Badge variant={health?.demo_mode ? 'default' : 'secondary'}>
                {health?.demo_mode ? 'Enabled' : 'Disabled'}
              </Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">OIDC Enabled</span>
              <Badge variant={health?.oidc_enabled ? 'default' : 'secondary'}>
                {health?.oidc_enabled ? 'Yes' : 'No'}
              </Badge>
            </div>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-muted-foreground">API Version</span>
              <span className="font-mono">{health?.version || 'Unknown'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Database Status</span>
              <Badge variant={health?.database === 'ok' ? 'default' : 'destructive'}>
                {health?.database || 'Unknown'}
              </Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Overall Status</span>
              <Badge variant={health?.status === 'ok' ? 'default' : 'secondary'}>
                {health?.status || 'Unknown'}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="text-red-800">
            <AlertCircle className="w-5 h-5 inline mr-2" />
            Failed to fetch health status: {error.message}
          </CardContent>
        </Card>
      )}
    </div>
  )
}