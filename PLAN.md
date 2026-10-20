# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

auth-oidc-keycloak

## Roadmap

### core-infrastructure — Core Infrastructure: FastAPI backend, React frontend, Docker, CI

Status: done

Acceptance:
- FastAPI app runs with health endpoint
- React + TypeScript + Vite frontend builds and serves
- Docker compose starts backend, frontend, Keycloak, SQLite
- CI workflow runs backend tests, frontend typecheck/build/test
- README with install/run/test steps
- portfolio.json at root with schema

Implementation: `backend/app/main.py`, `backend/requirements.txt`, `backend/Dockerfile`, `frontend/package.json`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `compose.yaml`, `.github/workflows/ci.yml`, `README.md`, `portfolio.json`

Tests: `backend/tests/test_health.py`, `backend/tests/test_mcp_server.py`, `backend/tests/test_js_parser.py`, `backend/tests/test_js_evidence.py`, `frontend/src/__tests__/App.test.tsx`

### mcp-server-core — MCP Server Core: JSON-RPC transport, tool registration, session management

Status: done

Acceptance:
- MCP server accepts stdio and HTTP connections
- Tools list returns registered reverse engineering tools
- Session creation and management works
- Cancellation signals propagate to running tools

Implementation: `backend/app/mcp/server.py`, `backend/app/mcp/transport.py`, `backend/app/mcp/tools.py`, `backend/app/mcp/session.py`

Tests: `backend/tests/test_mcp_server.py`

### javascript-analysis — JavaScript Application Analysis: AST parsing, call graph, evidence ledger

Status: done

Acceptance:
- Analyze directory of JS/TS files produces call graph
- Evidence ledger stores functions, calls, imports with source locations
- MCP tool 'analyze_javascript_application' returns structured results
- Results include evidence IDs for follow-up queries
- Cancellation stops analysis and cleans up

Implementation: `backend/app/analysis/javascript/parser.py`, `backend/app/analysis/javascript/graph.py`, `backend/app/analysis/javascript/evidence.py`, `backend/app/analysis/javascript/tool.py`

Tests: `backend/tests/test_js_parser.py`, `backend/tests/test_js_evidence.py`

### binary-analysis-ghidra — Binary Analysis with Ghidra: Provider interface, project management, snapshot cache

Status: planned

Acceptance:
- Ghidra provider launches headless analyzer
- Binary session opens target, runs analysis, produces evidence
- Snapshot cache stores/retrieves analysis results by target hash
- Pre-imported Ghidra project support (read-only)
- MCP tool 'binary_overview' and 'binary_session' work

Implementation: `backend/app/analysis/binary/ghidra_provider.py`, `backend/app/analysis/binary/session.py`, `backend/app/analysis/binary/snapshot_cache.py`, `backend/app/analysis/binary/tools.py`

Tests: `backend/tests/test_ghidra_provider.py`, `backend/tests/test_binary_session.py`, `backend/tests/test_snapshot_cache.py`

### process-capture-comparison — Process Capture & Comparison: PTY capture, temporal normalization, facet explanations

Status: planned

Acceptance:
- Capture command execution with stdout/stderr/timing
- Compare two captures with per-facet explanations
- Distinguish content/exit/timing differences
- MCP tool 'capture_process' and 'compare_captures' work

Implementation: `backend/app/analysis/process/capture.py`, `backend/app/analysis/process/comparison.py`, `backend/app/analysis/process/tools.py`

Tests: `backend/tests/test_process_capture.py`, `backend/tests/test_process_comparison.py`

### evidence-ledger-api — Evidence Ledger API: CRUD, pagination, filtering, export, follow-up queries

Status: done

Acceptance:
- REST API for evidence: list, get, search, export
- Follow-up tools: get_function, get_callers, get_imports
- Pagination and filtering by type, source, session
- Export to JSON/CSV with provenance

Implementation: `backend/app/api/evidence.py`, `backend/app/services/evidence_service.py`, `backend/app/models/evidence.py`

Tests: `backend/tests/test_evidence_api.py`, `backend/tests/test_evidence_service.py`

### frontend-dashboard — Frontend Dashboard: Analysis views, evidence browser, MCP connection

Status: done

Acceptance:
- Dashboard shows active sessions and recent analyses
- JavaScript analysis view with file tree and call graph
- Evidence browser with search, filter, detail view
- MCP connection status and tool invocation UI
- Process capture comparison view

Implementation: `frontend/src/components/Dashboard.tsx`, `frontend/src/components/JSAnalysisView.tsx`, `frontend/src/components/EvidenceBrowser.tsx`, `frontend/src/components/MCPConnection.tsx`, `frontend/src/components/ProcessComparison.tsx`, `frontend/src/api/client.ts`

Tests: `frontend/src/__tests__/Dashboard.test.tsx`, `frontend/src/__tests__/EvidenceBrowser.test.tsx`

### auth-oidc-keycloak — Authentication: OIDC with Keycloak, roles, demo mode

Status: done

Acceptance:
- Keycloak integration with authorization code + PKCE
- Backend validates tokens, enforces roles (viewer/operator/admin)
- Frontend login/logout flow with session storage
- Demo mode binds to localhost only, refuses in production
- Tests cover unauthenticated rejection and role denial

Implementation: `backend/app/core/auth.py`, `backend/app/core/security.py`, `backend/app/api/auth.py`, `frontend/src/auth/AuthProvider.tsx`, `frontend/src/auth/LoginCallback.tsx`

Tests: `backend/tests/test_auth.py`, `frontend/src/__tests__/AuthProvider.test.tsx`

### llm-adapters — LLM Adapters: OpenAI-compatible, Anthropic, Gemini, Ollama

Status: planned

Acceptance:
- Unified interface for LLM providers
- Configuration via LLM_PROVIDER, LLM_MODEL, LLM_BASE_URL, LLM_API_KEY
- Advisory explanations grounded in evidence records
- Provider errors surfaced clearly, no fabricated responses
- Keys only server-side, bounded timeouts

Implementation: `backend/app/llm/adapters.py`, `backend/app/llm/service.py`, `backend/app/api/llm.py`

Tests: `backend/tests/test_llm_adapters.py`, `backend/tests/test_llm_service.py`

### windows-native-authority — Windows Native Authority: Security descriptors, handle admission, Job Objects

Status: planned

Acceptance:
- TypeScript port for Windows capabilities
- Security descriptor creation/verification
- Reparse-point-safe path admission
- Atomic Job Object process launch
- Fail-closed when native capability unavailable

Implementation: `backend/app/windows/authority.py`, `backend/app/windows/port.ts`

Tests: `backend/tests/test_windows_authority.py`

