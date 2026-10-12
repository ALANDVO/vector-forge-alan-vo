from __future__ import annotations

import asyncio
import hashlib
import os
import uuid
from typing import Any

from app.mcp.server import MCPToolResult, MCPServer
from app.services.evidence_service import EvidenceService
from app.models.evidence import EvidenceType, SessionStatus
from app.analysis.javascript.tool import analyze_javascript_application


_evidence_service: EvidenceService | None = None


def set_evidence_service(service: EvidenceService) -> None:
    global _evidence_service
    _evidence_service = service


def get_evidence_service() -> EvidenceService | None:
    return _evidence_service


async def register_core_tools(server: MCPServer) -> None:
    server.register_tool(
        "analyze_javascript_application",
        "Analyze a JavaScript/TypeScript application directory, extracting functions, calls, imports, and exports. Returns evidence IDs for follow-up queries.",
        {
            "type": "object",
            "properties": {
                "input_path": {"type": "string", "description": "Absolute path to the directory or file to analyze"},
                "format": {"type": "string", "enum": ["directory", "file"], "default": "directory"},
                "include_node_modules": {"type": "boolean", "default": False},
                "max_files": {"type": "integer", "default": 1000},
            },
            "required": ["input_path"],
        },
        handle_analyze_javascript,
    )
    server.register_tool(
        "binary_session",
        "Create a binary analysis session with Ghidra. Returns session ID for follow-up operations.",
        {
            "type": "object",
            "properties": {
                "target_path": {"type": "string", "description": "Absolute path to the binary file"},
                "provider": {"type": "string", "enum": ["ghidra"], "default": "ghidra"},
                "ghidra_project_path": {"type": "string", "description": "Optional path to pre-imported Ghidra project (read-only)"},
            },
            "required": ["target_path"],
        },
        handle_binary_session,
    )
    server.register_tool(
        "binary_overview",
        "Get overview of binary: segments, functions, imports, exports, strings.",
        {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Binary session ID from binary_session"},
            },
            "required": ["session_id"],
        },
        handle_binary_overview,
    )
    server.register_tool(
        "cancel_analysis",
        "Cancel a running analysis by session ID.",
        {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID to cancel"},
            },
            "required": ["session_id"],
        },
        handle_cancel_analysis,
    )
    server.register_tool(
        "get_evidence",
        "Get evidence record by ID with optional edges.",
        {
            "type": "object",
            "properties": {
                "evidence_id": {"type": "string", "description": "Evidence record ID"},
                "include_edges": {"type": "boolean", "default": False},
            },
            "required": ["evidence_id"],
        },
        handle_get_evidence,
    )
    server.register_tool(
        "search_evidence",
        "Search evidence by name or qualified name within a session.",
        {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID to search within"},
                "query": {"type": "string", "description": "Search query"},
                "evidence_types": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["session_id", "query"],
        },
        handle_search_evidence,
    )


_active_tasks: dict[str, asyncio.Task] = {}


async def handle_analyze_javascript(arguments: dict) -> MCPToolResult:
    service = get_evidence_service()
    if not service:
        return MCPToolResult(content=[{"type": "text", "text": "Evidence service not available"}], isError=True)

    input_path = arguments.get("input_path", "")
    format_ = arguments.get("format", "directory")
    include_node_modules = arguments.get("include_node_modules", False)
    max_files = arguments.get("max_files", 1000)

    if not input_path or not os.path.isabs(input_path):
        return MCPToolResult(content=[{"type": "text", "text": "input_path must be an absolute path"}], isError=True)

    if not os.path.exists(input_path):
        return MCPToolResult(content=[{"type": "text", "text": f"Path does not exist: {input_path}"}], isError=True)

    target_hash = ""
    if format_ == "file":
        with open(input_path, "rb") as f:
            target_hash = hashlib.sha256(f.read()).hexdigest()
    else:
        hasher = hashlib.sha256()
        for root, dirs, files in os.walk(input_path):
            if not include_node_modules and "node_modules" in root:
                continue
            for f in sorted(files):
                if f.endswith((".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs")):
                    fp = os.path.join(root, f)
                    try:
                        with open(fp, "rb") as fh:
                            hasher.update(fh.read())
                    except Exception:
                        pass
        target_hash = hasher.hexdigest()

    session = await service.create_session("javascript", input_path, target_hash, {"format": format_, "include_node_modules": include_node_modules, "max_files": max_files})

    task_id = str(uuid.uuid4())
    task = asyncio.create_task(_run_js_analysis(task_id, session.id, input_path, format_, include_node_modules, max_files))
    _active_tasks[task_id] = task

    try:
        result = await task
    finally:
        _active_tasks.pop(task_id, None)

    return result


async def _run_js_analysis(task_id: str, session_id: str, input_path: str, format_: str, include_node_modules: bool, max_files: int) -> MCPToolResult:
    service = get_evidence_service()
    if not service:
        return MCPToolResult(content=[{"type": "text", "text": "Evidence service not available"}], isError=True)

    try:
        task = asyncio.current_task()
        if task and task.cancelled():
            await service.update_session_status(session_id, SessionStatus.CANCELLED)
            return MCPToolResult(content=[{"type": "text", "text": "Analysis cancelled"}], isError=True)

        result = await analyze_javascript_application(service=service, session_id=session_id, input_path=input_path, format_=format_, include_node_modules=include_node_modules, max_files=max_files)
        await service.update_session_status(session_id, SessionStatus.CLOSED)
        return MCPToolResult(
            content=[{"type": "text", "text": f"Analysis complete. Session: {session_id}"}],
            structuredContent={"session_id": session_id, "evidence_count": result.get("evidence_count", 0), "functions": result.get("functions", 0), "calls": result.get("calls", 0), "imports": result.get("imports", 0)},
        )
    except asyncio.CancelledError:
        await service.update_session_status(session_id, SessionStatus.CANCELLED)
        return MCPToolResult(content=[{"type": "text", "text": "Analysis cancelled"}], isError=True)
    except Exception as e:
        await service.update_session_status(session_id, SessionStatus.FAILED, str(e))
        return MCPToolResult(content=[{"type": "text", "text": f"Analysis failed: {str(e)}"}], isError=True)


async def handle_binary_session(arguments: dict) -> MCPToolResult:
    return MCPToolResult(content=[{"type": "text", "text": "Binary analysis not yet implemented (Round 2)"}], isError=True)


async def handle_binary_overview(arguments: dict) -> MCPToolResult:
    return MCPToolResult(content=[{"type": "text", "text": "Binary analysis not yet implemented (Round 2)"}], isError=True)


async def handle_cancel_analysis(arguments: dict) -> MCPToolResult:
    session_id = arguments.get("session_id", "")
    if not session_id:
        return MCPToolResult(content=[{"type": "text", "text": "session_id required"}], isError=True)

    for task_id, task in _active_tasks.items():
        if session_id in task_id or task_id == session_id:
            task.cancel()
            return MCPToolResult(content=[{"type": "text", "text": f"Cancellation requested for session {session_id}"}])

    return MCPToolResult(content=[{"type": "text", "text": f"No active task found for session {session_id}"}], isError=True)


async def handle_get_evidence(arguments: dict) -> MCPToolResult:
    service = get_evidence_service()
    if not service:
        return MCPToolResult(content=[{"type": "text", "text": "Evidence service not available"}], isError=True)

    evidence_id = arguments.get("evidence_id", "")
    include_edges = arguments.get("include_edges", False)

    evidence = await service.get_evidence_with_edges(evidence_id) if include_edges else await service.get_evidence(evidence_id)
    if not evidence:
        return MCPToolResult(content=[{"type": "text", "text": f"Evidence not found: {evidence_id}"}], isError=True)

    result = {"id": evidence.id, "type": evidence.evidence_type.value, "name": evidence.name, "qualified_name": evidence.qualified_name, "source_file": evidence.source_file, "source_line": evidence.source_line, "source_column": evidence.source_column, "source_end_line": evidence.source_end_line, "source_end_column": evidence.source_end_column, "content_hash": evidence.content_hash, "properties": evidence.properties, "provenance": evidence.provenance, "created_at": evidence.created_at.isoformat()}

    if include_edges:
        result["outgoing_edges"] = [{"id": e.id, "target_id": e.target_id, "edge_type": e.edge_type, "properties": e.properties} for e in evidence.outgoing_edges]
        result["incoming_edges"] = [{"id": e.id, "source_id": e.source_id, "edge_type": e.edge_type, "properties": e.properties} for e in evidence.incoming_edges]

    return MCPToolResult(content=[{"type": "text", "text": f"Evidence: {evidence.name} ({evidence.evidence_type.value})"}], structuredContent=result)


async def handle_search_evidence(arguments: dict) -> MCPToolResult:
    service = get_evidence_service()
    if not service:
        return MCPToolResult(content=[{"type": "text", "text": "Evidence service not available"}], isError=True)

    session_id = arguments.get("session_id", "")
    query = arguments.get("query", "")
    evidence_types = arguments.get("evidence_types")
    limit = arguments.get("limit", 50)

    if not session_id or not query:
        return MCPToolResult(content=[{"type": "text", "text": "session_id and query required"}], isError=True)

    types = [EvidenceType(t) for t in evidence_types] if evidence_types else None
    results = await service.search_evidence(session_id, query, types, limit)

    return MCPToolResult(content=[{"type": "text", "text": f"Found {len(results)} results"}], structuredContent={"results": [{"id": e.id, "type": e.evidence_type.value, "name": e.name, "qualified_name": e.qualified_name, "source_file": e.source_file, "source_line": e.source_line} for e in results]})