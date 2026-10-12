# Changelog

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to Vector Forge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-12

### Added
- Core FastAPI backend with health endpoints
- SQLite database with SQLAlchemy 2.0 models for sessions, evidence, edges, snapshots, audit log
- Evidence service with CRUD, pagination, filtering, search, and export
- MCP server with JSON-RPC 2.0 over stdio and HTTP (SSE)
- MCP tools: `analyze_javascript_application`, `binary_session`, `binary_overview`, `cancel_analysis`, `get_evidence`, `search_evidence`
- JavaScript/TypeScript analyzer with regex-based AST parsing
- Call graph building and import/export resolution
- React 18 + TypeScript + Vite frontend
- Dashboard with session overview and health status
- Sessions list with filtering, pagination, and session creation modal
- Session detail view with evidence browser, tabs, and search
- Health check page with system status
- OIDC authentication with Keycloak (authorization code + PKCE)
- Demo mode for localhost-only development
- Role-based access control (viewer, operator, admin)
- Docker Compose with backend, frontend, Keycloak, and persistent volumes
- CI workflow with pytest, npm build/test, Docker builds
- Comprehensive test suite (backend: 12+ tests, frontend: 3+ tests)

### Security
- JWT token validation with JWKS caching
- HttpOnly cookie support for session management
- CSRF protection on state-changing operations
- Input validation on all API endpoints
- Demo mode refuses to start in production
- No secrets in logs or error messages

### Infrastructure
- Non-root Docker users
- Health checks on all services
- SQLite persistent storage with WAL mode
- Tailwind CSS for responsive UI
- TanStack Query for server state management