import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Search, ChevronLeft, ChevronRight, Database, AlertCircle } from 'lucide-react'
import { apiClient } from '@/api/client'
import { clsx } from 'clsx'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'

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

interface SessionListResponse {
  items: Session[]
  total: number
  limit: number
  offset: number
}

export function SessionsList() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [typeFilter, setTypeFilter] = useState<string>('')
  const limit = 20

  const { data, isLoading, error } = useQuery<SessionListResponse>({
    queryKey: ['sessions', { page, limit, search, statusFilter, typeFilter }],
    queryFn: () => apiClient.listSessions({
      limit,
      offset: page * limit,
      ...(search && { name: search }),
      ...(statusFilter && { status: statusFilter as any }),
      ...(typeFilter && { session_type: typeFilter }),
    }),
  })

  const createMutation = useMutation({
    mutationFn: (data: { session_type: string; target_path: string; target_hash?: string; config?: Record<string, unknown> }) =>
      apiClient.createSession(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
    },
  })


  const statusLabels: Record<string, string> = {
    active: 'Active',
    closed: 'Closed',
    failed: 'Failed',
    cancelled: 'Cancelled',
  }

  const handleCreateSession = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    createMutation.mutate({
      session_type: formData.get('session_type') as string,
      target_path: formData.get('target_path') as string,
      target_hash: formData.get('target_hash') as string || undefined,
    })
    ;(e.target as HTMLFormElement).reset()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Analysis Sessions</h1>
          <p className="text-muted-foreground mt-1">
            Manage and view your reverse engineering analysis sessions
          </p>
        </div>
        <Button
          onClick={() => document.getElementById('create-session-modal')?.classList.remove('hidden')}
        >
          <Plus className="w-4 h-4 mr-2" />
          New Session
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Search sessions..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(0); }}
                className="pl-10"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
              className="input w-full sm:w-40"
            >
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="closed">Closed</option>
              <option value="failed">Failed</option>
              <option value="cancelled">Cancelled</option>
            </select>
            <select
              value={typeFilter}
              onChange={(e) => { setTypeFilter(e.target.value); setPage(0); }}
              className="input w-full sm:w-40"
            >
              <option value="">All Types</option>
              <option value="javascript">JavaScript</option>
              <option value="binary">Binary</option>
              <option value="process">Process</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Sessions Table */}
      <Card>
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent mx-auto" />
            <p className="text-muted-foreground mt-2">Loading sessions...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500">
            <AlertCircle className="w-6 h-6 mx-auto mb-2" />
            <p>Failed to load sessions</p>
          </div>
        ) : data?.items.length === 0 ? (
          <CardContent className="p-8 text-center">
            <Database className="w-12 h-12 mx-auto text-muted-foreground/50 mb-3" />
            <p className="text-muted-foreground">No sessions found</p>
            <p className="text-sm text-muted-foreground/70 mt-1">
              {search || statusFilter || typeFilter ? 'Try adjusting your filters' : 'Create your first analysis session'}
            </p>
            <Button className="mt-4" onClick={() => document.getElementById('create-session-modal')?.classList.remove('hidden')}>
              <Plus className="w-4 h-4 mr-2" />
              Create Session
            </Button>
          </CardContent>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left p-4 font-medium text-muted-foreground">Target</th>
                    <th className="text-left p-4 font-medium text-muted-foreground">Type</th>
                    <th className="text-left p-4 font-medium text-muted-foreground">Status</th>
                    <th className="text-left p-4 font-medium text-muted-foreground">Created</th>
                    <th className="text-left p-4 font-medium text-muted-foreground">Updated</th>
                    <th className="text-right p-4 font-medium text-muted-foreground">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.items.map((session) => (
                    <tr key={session.id} className="border-b border-border/50 hover:bg-accent/50">
                      <td className="p-4">
                        <Link to={`/sessions/${session.id}`} className="font-medium hover:text-primary">
                          {session.target_path}
                        </Link>
                        {session.target_hash && (
                          <p className="text-xs text-muted-foreground font-mono mt-1">
                            {session.target_hash.slice(0, 16)}...
                          </p>
                        )}
                      </td>
                      <td className="p-4">
                        <Badge variant="secondary">{session.session_type}</Badge>
                      </td>
                      <td className="p-4">
                        <Badge
                          className={clsx(
                            session.status === 'active' && 'bg-green-100 text-green-800',
                            session.status === 'closed' && 'bg-blue-100 text-blue-800',
                            session.status === 'failed' && 'bg-red-100 text-red-800',
                            session.status === 'cancelled' && 'bg-yellow-100 text-yellow-800'
                          )}
                        >
                          {statusLabels[session.status] || session.status}
                        </Badge>
                      </td>
                      <td className="p-4 text-sm text-muted-foreground">
                        {new Date(session.created_at).toLocaleString()}
                      </td>
                      <td className="p-4 text-sm text-muted-foreground">
                        {new Date(session.updated_at).toLocaleString()}
                      </td>
                      <td className="p-4 text-right">
                        <Link
                          to={`/sessions/${session.id}`}
                          className="text-sm text-primary hover:underline"
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {data && data.total > limit && (
              <div className="flex items-center justify-between p-4 border-t border-border">
                <p className="text-sm text-muted-foreground">
                  Showing {page * limit + 1} to {Math.min((page + 1) * limit, data.total)} of {data.total}
                </p>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}>
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <Button variant="outline" onClick={() => setPage(p => p + 1)} disabled={(page + 1) * limit >= data.total}>
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>

      {/* Create Session Modal */}
      <div id="create-session-modal" className="fixed inset-0 z-50 hidden overflow-y-auto">
        <div className="flex min-h-full items-center justify-center p-4">
          <div className="fixed inset-0 bg-black/50" onClick={() => document.getElementById('create-session-modal')?.classList.add('hidden')} />
          <div className="relative bg-card rounded-lg shadow-xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Create New Session</h2>
              <button
                onClick={() => document.getElementById('create-session-modal')?.classList.add('hidden')}
                className="text-muted-foreground hover:text-foreground"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <form onSubmit={handleCreateSession} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Session Type</label>
                <select name="session_type" className="input w-full" required>
                  <option value="javascript">JavaScript/TypeScript Analysis</option>
                  <option value="binary" disabled>Binary Analysis (Ghidra) - Coming Soon</option>
                  <option value="process" disabled>Process Capture - Coming Soon</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Target Path (absolute)</label>
                <Input
                  name="target_path"
                  type="text"
                  placeholder="/path/to/analyze"
                  className="font-mono text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Target Hash (optional)</label>
                <Input
                  name="target_hash"
                  type="text"
                  placeholder="SHA256 hash for deduplication"
                  className="font-mono text-sm"
                />
              </div>
              <div className="flex gap-3 pt-4">
                <Button
                  type="button"
                  variant="secondary"
                  className="flex-1"
                  onClick={() => document.getElementById('create-session-modal')?.classList.add('hidden')}
                >
                  Cancel
                </Button>
                <Button type="submit" className="flex-1" disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Creating...' : 'Create Session'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}