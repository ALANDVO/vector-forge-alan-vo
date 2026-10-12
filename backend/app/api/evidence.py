from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_evidence_service, get_current_principal
from app.core.security import Principal, require_role
from app.models.evidence import EvidenceType, SessionStatus
from app.services.evidence_service import EvidenceService

router = APIRouter(prefix="/api/v1", tags=["evidence"])


@router.post("/sessions", status_code=201)
async def create_session(
    session_type: str,
    target_path: str,
    target_hash: str | None = None,
    config: dict | None = None,
    service: EvidenceService = Depends(get_evidence_service),
    principal: Principal = Depends(get_current_principal),
):
    require_role(principal, "operator")
    session = await service.create_session(session_type, target_path, target_hash, config)
    return {
        "id": session.id,
        "session_type": session.session_type,
        "target_path": session.target_path,
        "target_hash": session.target_hash,
        "status": session.status.value,
        "config": session.config,
        "created_at": session.created_at.isoformat(),
    }


@router.get("/sessions")
async def list_sessions(
    session_type: str | None = None,
    status: SessionStatus | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: EvidenceService = Depends(get_evidence_service),
    principal: Principal = Depends(get_current_principal),
):
    require_role(principal, "viewer")
    sessions = await service.list_sessions(session_type, status, limit, offset)
    total = await service.count_sessions(session_type, status)
    return {
        "items": [
            {
                "id": s.id,
                "session_type": s.session_type,
                "target_path": s.target_path,
                "target_hash": s.target_hash,
                "status": s.status.value,
                "config": s.config,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "closed_at": s.closed_at.isoformat() if s.closed_at else None,
            }
            for s in sessions
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    service: EvidenceService = Depends(get_evidence_service),
    principal: Principal = Depends(get_current_principal),
):
    require_role(principal, "viewer")
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return {
        "id": session.id,
        "session_type": session.session_type,
        "target_path": session.target_path,
        "target_hash": session.target_hash,
        "status": session.status.value,
        "config": session.config,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "closed_at": session.closed_at.isoformat() if session.closed_at else None,
        "error_message": session.error_message,
    }


@router.patch("/sessions/{session_id}/status")
async def update_session_status(
    session_id: str,
    status: SessionStatus,
    error_message: str | None = None,
    service: EvidenceService = Depends(get_evidence_service),
    principal: Principal = Depends(get_current_principal),
):
    require_role(principal, "operator")
    session = await service.update_session_status(session_id, status, error_message)
    if not session:
        raise HTTPException(404, "Session not found")
    return {
        "id": session.id,
        "status": session.status.value,
        "updated_at": session.updated_at.isoformat(),
        "closed_at": session.closed_at.isoformat() if session.closed_at else None,
    }


@router.get("/sessions/{session_id}/evidence")
async def list_evidence(
    session_id: str,
    evidence_type: EvidenceType | None = None,
    name_filter: str | None = Query(None, alias="name"),
    source_file: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: EvidenceService = Depends(get_evidence_service),
    principal: Principal = Depends(get_current_principal),
):
    require_role(principal, "viewer")
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    evidence = await service.list_evidence(session_id, evidence_type, name_filter, source_file, limit, offset)
    total = await service.count_evidence(session_id, evidence_type, name_filter)
    return {
        "items": [
            {
                "id": e.id,
                "type": e.evidence_type.value,
                "name": e.name,
                "qualified_name": e.qualified_name,
                "source_file": e.source_file,
                "source_line": e.source_line,
                "source_column": e.source_column,
                "source_end_line": e.source_end_line,
                "source_end_column": e.source_end_column,
                "content_hash": e.content_hash,
                "properties": e.properties,
                "provenance": e.provenance,
                "created_at": e.created_at.isoformat(),
            }
            for e in evidence
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/sessions/{session_id}/evidence/{evidence_id}")
async def get_evidence(
    session_id: str,
    evidence_id: str,
    include_edges: bool = False,
    service: EvidenceService = Depends(get_evidence_service),
    principal: Principal = Depends(get_current_principal),
):
    require_role(principal, "viewer")
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if include_edges:
        evidence = await service.get_evidence_with_edges(evidence_id)
    else:
        evidence = await service.get_evidence(evidence_id)
    if not evidence or evidence.session_id != session_id:
        raise HTTPException(404, "Evidence not found")
    result = {
        "id": evidence.id,
        "type": evidence.evidence_type.value,
        "name": evidence.name,
        "qualified_name": evidence.qualified_name,
        "source_file": evidence.source_file,
        "source_line": evidence.source_line,
        "source_column": evidence.source_column,
        "source_end_line": evidence.source_end_line,
        "source_end_column": evidence.source_end_column,
        "content_hash": evidence.content_hash,
        "properties": evidence.properties,
        "provenance": evidence.provenance,
        "created_at": evidence.created_at.isoformat(),
    }
    if include_edges:
        result["outgoing_edges"] = [
            {
                "id": edge.id,
                "target_id": edge.target_id,
                "edge_type": edge.edge_type,
                "properties": edge.properties,
            }
            for edge in evidence.outgoing_edges
        ]
        result["incoming_edges"] = [
            {
                "id": edge.id,
                "source_id": edge.source_id,
                "edge_type": edge.edge_type,
                "properties": edge.properties,
            }
            for edge in evidence.incoming_edges
        ]
    return result


@router.get("/sessions/{session_id}/evidence/{evidence_id}/callers")
async def get_callers(
    session_id: str,
    evidence_id: str,
    service: EvidenceService = Depends(get_evidence_service),
    principal: Principal = Depends(get_current_principal),
):
    require_role(principal, "viewer")
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    edges = await service.get_incoming_edges(evidence_id, "calls")
    caller_ids = [e.source_id for e in edges]
    callers = []
    for cid in caller_ids:
        ev = await service.get_evidence(cid)
        if ev:
            callers.append({
                "id": ev.id,
                "name": ev.name,
                "qualified_name": ev.qualified_name,
                "source_file": ev.source_file,
                "source_line": ev.source_line,
            })
    return {"callers": callers}


@router.get("/sessions/{session_id}/evidence/{evidence_id}/callees")
async def get_callees(
    session_id: str,
    evidence_id: str,
    service: EvidenceService = Depends(get_evidence_service),
    principal: Principal = Depends(get_current_principal),
):
    require_role(principal, "viewer")
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    edges = await service.get_outgoing_edges(evidence_id, "calls")
    callee_ids = [e.target_id for e in edges]
    callees = []
    for cid in callee_ids:
        ev = await service.get_evidence(cid)
        if ev:
            callees.append({
                "id": ev.id,
                "name": ev.name,
                "qualified_name": ev.qualified_name,
                "source_file": ev.source_file,
                "source_line": ev.source_line,
            })
    return {"callees": callees}


@router.get("/sessions/{session_id}/evidence/{evidence_id}/imports")
async def get_imports(
    session_id: str,
    evidence_id: str,
    service: EvidenceService = Depends(get_evidence_service),
    principal: Principal = Depends(get_current_principal),
):
    require_role(principal, "viewer")
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    edges = await service.get_outgoing_edges(evidence_id, "imports")
    import_ids = [e.target_id for e in edges]
    imports = []
    for iid in import_ids:
        ev = await service.get_evidence(iid)
        if ev:
            imports.append({
                "id": ev.id,
                "name": ev.name,
                "qualified_name": ev.qualified_name,
                "source_file": ev.source_file,
                "source_line": ev.source_line,
            })
    return {"imports": imports}


@router.get("/sessions/{session_id}/export")
async def export_session(
    session_id: str,
    service: EvidenceService = Depends(get_evidence_service),
    principal: Principal = Depends(get_current_principal),
):
    require_role(principal, "operator")
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    data = await service.export_session_evidence(session_id)
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=session-{session_id}.json"},
    )