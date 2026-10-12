import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Database, Activity, Search, Play } from 'lucide-react'
import { apiClient } from '@/api/client'
import { clsx } from 'clsx'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface HealthResponse {
  status: string
  version: string
  environment: string
  database: string
  demo_mode: boolean
  oidc_enabled: boolean
}

interface SessionListResponse {
  items: Session[]
  total: number
  limit: number
  offset: number
}

interface Session {
  id: string
  session_type: string
  target_path: string
  target_hash: string | null
  status: 'active' | 'closed' | 'failed' | 'cancelled'
  config: Record<string, unknown>
  created_at: string
  updated_at: string
  closed_at: string | null
  error_message: string | null
}

export function Dashboard() {
  const { data: health, isLoading: healthLoading, error: healthError } = useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: () => apiClient.health(),
    refetchInterval: 30000,
  })

  const { data: sessions, isLoading: sessionsLoading } = useQuery<SessionListResponse>({
    queryKey: ['sessions', { limit: 5 }],
    queryFn: () => apiClient.listSessions({ limit: 5 }),
    refetchInterval: 10000,
  })

  const statusColors: Record<string, string> = {
    active: 'bg-green-500',
    closed: 'bg-blue-500',
    failed: 'bg-red-500',
    cancelled: 'bg-yellow-500',
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Reverse engineering analysis overview
          </p>
        </div>
        <Link to="/sessions" className="btn-primary">
          <Play className="w-4 h-4 mr-2" />
          New Analysis
        </Link>
      </div>

      {/* Health Status */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">API Status</CardTitle>
            {healthLoading ? (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            ) : healthError ? (
              <Badge variant="destructive">Error</Badge>
            ) : (
              <Badge variant="default">Healthy</Badge>
            )}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {health?.status || 'Unknown'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Environment: {health?.environment || 'Unknown'}
            </p>
            <p className="text-xs text-muted-foreground">
              Version: {health?.version || 'Unknown'}
            </p>
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
            <div className="text-2xl font-bold">
              {health?.database || 'Unknown'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              SQLite persistent storage
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Demo Mode</CardTitle>
            {health?.demo_mode ? (
              <Badge variant="secondary">Enabled</Badge>
            ) : (
              <Badge variant="outline">Disabled</Badge>
            )}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {health?.demo_mode ? 'Local' : 'Auth Required'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {health?.demo_mode ? 'Localhost access only' : 'OIDC authentication required'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <ActionCard
          title="JavaScript Analysis"
          description="Analyze JS/TS applications for functions, calls, and imports"
          icon={<Search className="w-6 h-6" />}
          href="/sessions"
          badge="New"
        />
        <ActionCard
          title="Binary Analysis"
          description="Analyze native binaries with Ghidra (coming soon)"
          icon={<Database className="w-6 h-6" />}
          href="/sessions"
          disabled
        />
        <ActionCard
          title="Process Capture"
          description="Capture and compare process execution traces (coming soon)"
          icon={<Activity className="w-6 h-6" />}
          href="/sessions"
          disabled
        />
        <ActionCard
          title="Evidence Browser"
          description="Browse and search collected evidence across sessions"
          icon={<Search className="w-6 h-6" />}
          href="/sessions"
        />
      </div>

      {/* Recent Sessions */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Recent Sessions</h2>
          <Link to="/sessions" className="text-sm text-primary hover:underline">
            View all
          </Link>
        </div>
        {sessionsLoading ? (
          <Card>
            <CardContent className="py-8 text-center">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent mx-auto" />
              <p className="text-muted-foreground mt-2">Loading sessions...</p>
            </CardContent>
          </Card>
        ) : sessions?.items?.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center">
              <Database className="w-12 h-12 mx-auto text-muted-foreground/50 mb-3" />
              <p className="text-muted-foreground">No sessions yet</p>
              <p className="text-sm text-muted-foreground/70 mt-1">
                Start your first analysis to see results here
              </p>
              <Link to="/sessions" className="btn-primary mt-4 inline-flex">
                <Play className="w-4 h-4 mr-2" />
                Create Session
              </Link>
            </CardContent>
          </Card>
        ) : sessions?.items && (
          <div className="space-y-3">
            {sessions.items.slice(0, 5).map((session) => (
              <SessionRow key={session.id} session={session} statusColors={statusColors} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

interface SessionRowProps {
  session: Session
  statusColors: Record<string, string>
}

function SessionRow({ session, statusColors }: SessionRowProps) {
  const statusColor = statusColors[session.status] || 'bg-gray-500'

  return (
    <Link to={`/sessions/${session.id}`} className="block">
      <Card className="hover:shadow-md transition-shadow cursor-pointer">
        <CardContent className="py-3 px-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={clsx('w-2 h-2 rounded-full', statusColor)} />
              <div>
                <p className="font-medium text-sm">{session.target_path}</p>
                <p className="text-xs text-muted-foreground">
                  {session.session_type} • {new Date(session.created_at).toLocaleString()}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={clsx(
                  'px-2 py-1 rounded-full text-xs font-medium',
                  session.status === 'active' && 'bg-green-100 text-green-800',
                  session.status === 'closed' && 'bg-blue-100 text-blue-800',
                  session.status === 'failed' && 'bg-red-100 text-red-800',
                  session.status === 'cancelled' && 'bg-yellow-100 text-yellow-800'
                )}
              >
                {session.status}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}

interface ActionCardProps {
  title: string
  description: string
  icon: React.ReactNode
  href: string
  badge?: string
  disabled?: boolean
}

function ActionCard({ title, description, icon, href, badge, disabled }: ActionCardProps) {
  return (
    <Card className={clsx('h-full transition-all hover:shadow-lg', disabled && 'opacity-50 cursor-not-allowed')}>
      <CardContent className="p-6">
        <div className="flex items-start gap-4">
          <div className={clsx('p-3 rounded-lg bg-primary/10 text-primary', disabled && 'opacity-50')}>
            {icon}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-foreground">{title}</h3>
              {badge && (
                <Badge variant="secondary" className="px-2 py-0.5 text-xs font-medium bg-primary/10 text-primary rounded">
                  {badge}
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{description}</p>
            {!disabled && (
              <Link to={href} className="text-sm text-primary hover:underline mt-3 inline-block">
                Start →
              </Link>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}