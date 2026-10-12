import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Search, Download, ChevronLeft, ChevronRight, Database, AlertCircle, GitBranch, Package } from 'lucide-react'
import { apiClient } from '@/api/client'
import { clsx } from 'clsx'
import { useState } from 'react'


interface Evidence {
  id: string
  type: string
  name: string
  qualified_name: string | null
  source_file: string | null
  source_line: number | null
  source_column: number | null
  source_end_line: number | null
  source_end_column: number | null
  content_hash: string | null
  properties: Record<string, unknown>
  provenance: Record<string, unknown>
  created_at: string
}

interface EvidenceListResponse {
  items: Evidence[]
  total: number
  limit: number
  offset: number
}

interface SessionDetailResponse {
  id: string
  session_type: string
  target_path: string
  target_hash: string | null
  status: string
  config: Record<string, unknown>
  created_at: string
  updated_at: string
  closed_at: string | null
  error_message: string | null
}

const TypeIcon: Record<string, React.ComponentType<{ className?: string }>> = {
  function: Database,
  class: GitBranch,
  import: Package,
  export: Package,
  module: Database,
  file: Database,
}

function TypeIconWrapper({ type, className }: { type: string; className?: string }) {
  const Icon = TypeIcon[type] || Database
  return <Icon className={className} />
}

const statusColors: Record<string, string> = {
  active: 'bg-green-100 text-green-800',
  closed: 'bg-blue-100 text-blue-800',
  failed: 'bg-red-100 text-red-800',
  cancelled: 'bg-yellow-100 text-yellow-800',
}

export function SessionDetail() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [evidencePage, setEvidencePage] = useState(0)
  const [evidenceSearch, setEvidenceSearch] = useState('')
  const [evidenceTypeFilter, setEvidenceTypeFilter] = useState<string>('')
  const evidenceLimit = 50

  const { data: session, isLoading: sessionLoading, error: sessionError } = useQuery<SessionDetailResponse>({
    queryKey: ['session', sessionId],
    queryFn: () => apiClient.getSession(sessionId!),
    enabled: !!sessionId,
  })

  const { data: evidence, isLoading: evidenceLoading } = useQuery<EvidenceListResponse>({
    queryKey: ['evidence', sessionId, { page: evidencePage, limit: evidenceLimit, search: evidenceSearch, type: evidenceTypeFilter }],
    queryFn: () => apiClient.listEvidence(sessionId!, {
      name: evidenceSearch || undefined,
      evidence_type: evidenceTypeFilter || undefined,
      limit: evidenceLimit,
      offset: evidencePage * evidenceLimit,
    }),
    enabled: !!sessionId,
  })

  if (sessionLoading) {
    return <div className="flex items-center justify-center h-64"><div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" /></div>
  }

  if (sessionError || !session) {
    return (
      <div className="text-center py-8">
        <AlertCircle className="w-12 h-12 mx-auto text-red-500 mb-3" />
        <h2 className="text-xl font-semibold">Session not found</h2>
        <p className="text-muted-foreground mt-1">The requested session does not exist.</p>
      </div>
    )
  }

  const handleExport = async () => {
    const blob = await apiClient.exportSession(sessionId!)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `session-${sessionId}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div>
            <h1 className="text-2xl font-bold text-foreground">{session.target_path}</h1>
            <p className="text-muted-foreground mt-1">{session.session_type} analysis • {new Date(session.created_at).toLocaleString()}</p>
          </div>
          <div className="flex items-center gap-3">
            <Badge className={clsx('px-3 py-1 text-sm', statusColors[session.status])}>{session.status}</Badge>
            <Button variant="outline" onClick={handleExport} disabled={evidenceLoading}><Download className="w-4 h-4 mr-2" />Export JSON</Button>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-4 text-sm">
          <div><p className="text-muted-foreground">Session ID</p><p className="font-mono text-xs">{session.id}</p></div>
          <div><p className="text-muted-foreground">Type</p><p>{session.session_type}</p></div>
          <div><p className="text-muted-foreground">Target Hash</p><p className="font-mono text-xs">{session.target_hash?.slice(0, 32) || 'N/A'}...</p></div>
          <div><p className="text-muted-foreground">Status</p><p className={clsx('font-medium capitalize', statusColors[session.status].replace('bg-', 'text-').replace('/100', ''))}>{session.status}</p></div>
          {session.error_message && <div className="md:col-span-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-800 text-sm"><strong>Error: </strong>{session.error_message}</div>}
        </CardContent>
      </Card>

      <Tabs defaultValue="evidence" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="evidence">Evidence ({evidence?.total || 0})</TabsTrigger>
          <TabsTrigger value="functions">Functions</TabsTrigger>
          <TabsTrigger value="imports">Imports</TabsTrigger>
        </TabsList>

        <TabsContent value="evidence" className="mt-4"><EvidenceTable evidence={evidence} loading={evidenceLoading} page={evidencePage} setPage={setEvidencePage} search={evidenceSearch} setSearch={setEvidenceSearch} typeFilter={evidenceTypeFilter} setTypeFilter={setEvidenceTypeFilter} total={evidence?.total || 0} limit={evidenceLimit} /></TabsContent>
        <TabsContent value="functions" className="mt-4"><EvidenceTable evidence={evidence} loading={evidenceLoading} page={evidencePage} setPage={setEvidencePage} search={evidenceSearch} setSearch={setEvidenceSearch} typeFilter="function" setTypeFilter={setEvidenceTypeFilter} total={evidence?.items.filter(e => e.type === 'function').length || 0} limit={evidenceLimit} /></TabsContent>
        <TabsContent value="imports" className="mt-4"><EvidenceTable evidence={evidence} loading={evidenceLoading} page={evidencePage} setPage={setEvidencePage} search={evidenceSearch} setSearch={setEvidenceSearch} typeFilter="import" setTypeFilter={setEvidenceTypeFilter} total={evidence?.items.filter(e => e.type === 'import').length || 0} limit={evidenceLimit} /></TabsContent>
      </Tabs>
    </div>
  )
}

interface EvidenceTableProps {
  evidence: EvidenceListResponse | undefined
  loading: boolean
  page: number
  setPage: (page: number | ((prev: number) => number)) => void
  search: string
  setSearch: (search: string) => void
  typeFilter: string
  setTypeFilter: (type: string) => void
  total: number
  limit: number
}

function EvidenceTable({ evidence, loading, page, setPage, search, setSearch, typeFilter, setTypeFilter, total, limit }: EvidenceTableProps) {
  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1"><Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" /><Input placeholder="Search evidence..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} className="pl-10" /></div>
        <select value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value); setPage(0); }} className="input w-full sm:w-48"><option value="">All Types</option><option value="function">Function</option><option value="class">Class</option><option value="import">Import</option><option value="export">Export</option><option value="module">Module</option><option value="file">File</option></select>
      </div>

      {loading ? <div className="p-8 text-center"><div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent mx-auto" /><p className="text-muted-foreground mt-2">Loading evidence...</p></div> : evidence?.items.length === 0 ? <div className="p-8 text-center"><Database className="w-12 h-12 mx-auto text-muted-foreground/50 mb-3" /><p className="text-muted-foreground">No evidence found</p></div> : (
        <>
          <div className="rounded-lg border bg-card overflow-hidden"><table className="w-full"><thead><tr className="border-b border-border bg-muted/50"><th className="text-left p-3 font-medium text-muted-foreground">Name</th><th className="text-left p-3 font-medium text-muted-foreground">Type</th><th className="text-left p-3 font-medium text-muted-foreground">Source</th><th className="text-left p-3 font-medium text-muted-foreground">Line</th><th className="text-right p-3 font-medium text-muted-foreground">Actions</th></tr></thead><tbody>{evidence?.items.map((item) => (<tr key={item.id} className="border-b border-border/50 hover:bg-accent/50"><td className="p-3"><div className="font-mono text-sm">{item.name}</div>{item.qualified_name && item.qualified_name !== item.name && <div className="text-xs text-muted-foreground truncate max-w-xs">{item.qualified_name}</div>}</td><td className="p-3"><Badge variant="outline" className="gap-1"><TypeIconWrapper type={item.type} className="w-3 h-3" />{item.type}</Badge></td><td className="p-3 text-sm text-muted-foreground truncate max-w-xs">{item.source_file || '-'}</td><td className="p-3 text-sm text-muted-foreground font-mono">{item.source_line ? `${item.source_line}` : '-'}</td><td className="p-3 text-right"><button className="text-primary hover:underline text-sm">View</button></td></tr>))}</tbody></table></div>
          {total > limit && <div className="flex items-center justify-between"><p className="text-sm text-muted-foreground">Showing {page * limit + 1} to {Math.min((page + 1) * limit, total)} of {total}</p><div className="flex gap-2"><Button variant="outline" size="sm" onClick={() => setPage((p: number) => Math.max(0, p - 1))} disabled={page === 0}><ChevronLeft className="w-4 h-4" /></Button><Button variant="outline" size="sm" onClick={() => setPage((p: number) => p + 1)} disabled={(page + 1) * limit >= total}><ChevronRight className="w-4 h-4" /></Button></div></div>}
        </>
      )}
    </div>
  )
}