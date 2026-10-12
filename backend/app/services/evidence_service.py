from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.evidence import (
    AnalysisSession,
    AnalysisSnapshot,
    AuditLog,
    EvidenceEdge,
    EvidenceRecord,
    EvidenceType,
    SessionStatus,
)
from app.core.config import get_settings


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def compute_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class EvidenceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # Session management
    async def create_session(
        self,
        session_type: str,
        target_path: str,
        target_hash: Optional[str] = None,
        config: Optional[dict] = None,
    ) -> AnalysisSession:
        session = AnalysisSession(
            session_type=session_type,
            target_path=target_path,
            target_hash=target_hash,
            config=config or {},
        )
        self.session.add(session)
        await self.session.flush()
        return session

    async def get_session(self, session_id: str) -> Optional[AnalysisSession]:
        result = await self.session.execute(
            select(AnalysisSession).where(AnalysisSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_session_with_evidence(self, session_id: str) -> Optional[AnalysisSession]:
        result = await self.session.execute(
            select(AnalysisSession)
            .options(selectinload(AnalysisSession.evidence))
            .where(AnalysisSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        session_type: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[AnalysisSession]:
        stmt = select(AnalysisSession).order_by(AnalysisSession.created_at.desc())
        if session_type:
            stmt = stmt.where(AnalysisSession.session_type == session_type)
        if status:
            stmt = stmt.where(AnalysisSession.status == status)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_sessions(
        self,
        session_type: Optional[str] = None,
        status: Optional[SessionStatus] = None,
    ) -> int:
        stmt = select(func.count(AnalysisSession.id))
        if session_type:
            stmt = stmt.where(AnalysisSession.session_type == session_type)
        if status:
            stmt = stmt.where(AnalysisSession.status == status)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update_session_status(
        self,
        session_id: str,
        status: SessionStatus,
        error_message: Optional[str] = None,
    ) -> Optional[AnalysisSession]:
        session = await self.get_session(session_id)
        if not session:
            return None
        session.status = status
        session.updated_at = utc_now()
        if status in (SessionStatus.CLOSED, SessionStatus.FAILED, SessionStatus.CANCELLED):
            session.closed_at = utc_now()
        if error_message:
            session.error_message = error_message
        await self.session.flush()
        return session

    # Evidence CRUD
    async def create_evidence(
        self,
        session_id: str,
        evidence_type: EvidenceType,
        name: str,
        qualified_name: Optional[str] = None,
        source_file: Optional[str] = None,
        source_line: Optional[int] = None,
        source_column: Optional[int] = None,
        source_end_line: Optional[int] = None,
        source_end_column: Optional[int] = None,
        content: Optional[bytes] = None,
        properties: Optional[dict] = None,
        provenance: Optional[dict] = None,
    ) -> EvidenceRecord:
        content_hash = compute_hash(content) if content else None
        record = EvidenceRecord(
            session_id=session_id,
            evidence_type=evidence_type,
            name=name,
            qualified_name=qualified_name,
            source_file=source_file,
            source_line=source_line,
            source_column=source_column,
            source_end_line=source_end_line,
            source_end_column=source_end_column,
            content_hash=content_hash,
            properties=properties or {},
            provenance=provenance or {},
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def bulk_create_evidence(self, records: list[EvidenceRecord]) -> list[EvidenceRecord]:
        self.session.add_all(records)
        await self.session.flush()
        return records

    async def get_evidence(self, evidence_id: str) -> Optional[EvidenceRecord]:
        result = await self.session.execute(
            select(EvidenceRecord).where(EvidenceRecord.id == evidence_id)
        )
        return result.scalar_one_or_none()

    async def get_evidence_with_edges(self, evidence_id: str) -> Optional[EvidenceRecord]:
        result = await self.session.execute(
            select(EvidenceRecord)
            .options(
                selectinload(EvidenceRecord.outgoing_edges),
                selectinload(EvidenceRecord.incoming_edges),
            )
            .where(EvidenceRecord.id == evidence_id)
        )
        return result.scalar_one_or_none()

    async def list_evidence(
        self,
        session_id: str,
        evidence_type: Optional[EvidenceType] = None,
        name_filter: Optional[str] = None,
        source_file: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[EvidenceRecord]:
        stmt = select(EvidenceRecord).where(EvidenceRecord.session_id == session_id)
        if evidence_type:
            stmt = stmt.where(EvidenceRecord.evidence_type == evidence_type)
        if name_filter:
            stmt = stmt.where(EvidenceRecord.name.ilike(f"%{name_filter}%"))
        if source_file:
            stmt = stmt.where(EvidenceRecord.source_file == source_file)
        stmt = stmt.order_by(EvidenceRecord.name).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_evidence(
        self,
        session_id: str,
        evidence_type: Optional[EvidenceType] = None,
        name_filter: Optional[str] = None,
    ) -> int:
        stmt = select(func.count(EvidenceRecord.id)).where(EvidenceRecord.session_id == session_id)
        if evidence_type:
            stmt = stmt.where(EvidenceRecord.evidence_type == evidence_type)
        if name_filter:
            stmt = stmt.where(EvidenceRecord.name.ilike(f"%{name_filter}%"))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def search_evidence(
        self,
        session_id: str,
        query: str,
        evidence_types: Optional[list[EvidenceType]] = None,
        limit: int = 50,
    ) -> Sequence[EvidenceRecord]:
        stmt = select(EvidenceRecord).where(EvidenceRecord.session_id == session_id)
        search_filter = or_(
            EvidenceRecord.name.ilike(f"%{query}%"),
            EvidenceRecord.qualified_name.ilike(f"%{query}%"),
        )
        stmt = stmt.where(search_filter)
        if evidence_types:
            stmt = stmt.where(EvidenceRecord.evidence_type.in_(evidence_types))
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # Edges
    async def create_edge(
        self,
        session_id: str,
        source_id: str,
        target_id: str,
        edge_type: str,
        properties: Optional[dict] = None,
    ) -> EvidenceEdge:
        edge = EvidenceEdge(
            session_id=session_id,
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            properties=properties or {},
        )
        self.session.add(edge)
        await self.session.flush()
        return edge

    async def bulk_create_edges(self, edges: list[EvidenceEdge]) -> list[EvidenceEdge]:
        self.session.add_all(edges)
        await self.session.flush()
        return edges

    async def get_outgoing_edges(
        self,
        source_id: str,
        edge_type: Optional[str] = None,
    ) -> Sequence[EvidenceEdge]:
        stmt = select(EvidenceEdge).where(EvidenceEdge.source_id == source_id)
        if edge_type:
            stmt = stmt.where(EvidenceEdge.edge_type == edge_type)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_incoming_edges(
        self,
        target_id: str,
        edge_type: Optional[str] = None,
    ) -> Sequence[EvidenceEdge]:
        stmt = select(EvidenceEdge).where(EvidenceEdge.target_id == target_id)
        if edge_type:
            stmt = stmt.where(EvidenceEdge.edge_type == edge_type)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # Snapshots
    async def create_snapshot(
        self,
        session_id: str,
        target_hash: str,
        provider: str,
        data: bytes,
        provider_version: Optional[str] = None,
        snapshot_metadata: Optional[dict] = None,
    ) -> AnalysisSnapshot:
        snapshot = AnalysisSnapshot(
            session_id=session_id,
            target_hash=target_hash,
            provider=provider,
            snapshot_metadata=snapshot_metadata or {},
            data=data,
        )
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def get_snapshot(
        self,
        session_id: str,
        target_hash: str,
        provider: str,
    ) -> Optional[AnalysisSnapshot]:
        result = await self.session.execute(
            select(AnalysisSnapshot).where(
                and_(
                    AnalysisSnapshot.session_id == session_id,
                    AnalysisSnapshot.target_hash == target_hash,
                    AnalysisSnapshot.provider == provider,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_snapshot(
        self,
        target_hash: str,
        provider: str,
    ) -> Optional[AnalysisSnapshot]:
        result = await self.session.execute(
            select(AnalysisSnapshot)
            .where(
                and_(
                    AnalysisSnapshot.target_hash == target_hash,
                    AnalysisSnapshot.provider == provider,
                )
            )
            .order_by(AnalysisSnapshot.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # Audit
    async def log_audit(
        self,
        action: str,
        resource_type: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        log = AuditLog(
            session_id=session_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    # Export
    async def export_session_evidence(self, session_id: str) -> dict:
        session = await self.get_session_with_evidence(session_id)
        if not session:
            return {}

        evidence_list = []
        for ev in session.evidence:
            evidence_list.append({
                "id": ev.id,
                "type": ev.evidence_type.value,
                "name": ev.name,
                "qualified_name": ev.qualified_name,
                "source_file": ev.source_file,
                "source_line": ev.source_line,
                "source_column": ev.source_column,
                "source_end_line": ev.source_end_line,
                "source_end_column": ev.source_end_column,
                "content_hash": ev.content_hash,
                "properties": ev.properties,
                "provenance": ev.provenance,
                "created_at": ev.created_at.isoformat(),
            })

        edges_list = []
        for ev in session.evidence:
            for edge in ev.outgoing_edges:
                edges_list.append({
                    "id": edge.id,
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "edge_type": edge.edge_type,
                    "properties": edge.properties,
                    "created_at": edge.created_at.isoformat(),
                })

        return {
            "session": {
                "id": session.id,
                "session_type": session.session_type,
                "target_path": session.target_path,
                "target_hash": session.target_hash,
                "status": session.status.value,
                "config": session.config,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "closed_at": session.closed_at.isoformat() if session.closed_at else None,
            },
            "evidence": evidence_list,
            "edges": edges_list,
            "exported_at": utc_now().isoformat(),
        }