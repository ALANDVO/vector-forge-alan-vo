from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import BLOB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def gen_uuid() -> str:
    return str(uuid.uuid4())


class EvidenceType(str, enum.Enum):
    FUNCTION = "function"
    CALL = "call"
    IMPORT = "import"
    EXPORT = "export"
    VARIABLE = "variable"
    CLASS = "class"
    INTERFACE = "interface"
    TYPE = "type"
    FILE = "file"
    MODULE = "module"
    BINARY_SEGMENT = "binary_segment"
    BINARY_FUNCTION = "binary_function"
    BINARY_STRING = "binary_string"
    BINARY_IMPORT = "binary_import"
    PROCESS_EVENT = "process_event"
    PROCESS_EXIT = "process_exit"
    PROCESS_FS = "process_fs"
    PROCESS_NET = "process_net"
    UNKNOWN = "unknown"


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    session_type: Mapped[str] = mapped_column(String(50), nullable=False)  # javascript, binary, process
    target_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    target_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, native_enum=False), default=SessionStatus.ACTIVE, nullable=False
    )
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    evidence: Mapped[list["EvidenceRecord"]] = relationship(
        "EvidenceRecord", back_populates="session", cascade="all, delete-orphan", lazy="selectin"
    )
    snapshots: Mapped[list["AnalysisSnapshot"]] = relationship(
        "AnalysisSnapshot", back_populates="session", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_sessions_target_hash", "target_hash"),
        Index("ix_sessions_status", "status"),
        Index("ix_sessions_created_at", "created_at"),
    )


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False)
    evidence_type: Mapped[EvidenceType] = mapped_column(Enum(EvidenceType, native_enum=False), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    qualified_name: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    source_file: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    source_line: Mapped[Optional[int]] = mapped_column(nullable=True)
    source_column: Mapped[Optional[int]] = mapped_column(nullable=True)
    source_end_line: Mapped[Optional[int]] = mapped_column(nullable=True)
    source_end_column: Mapped[Optional[int]] = mapped_column(nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    properties: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    session: Mapped[AnalysisSession] = relationship("AnalysisSession", back_populates="evidence")
    outgoing_edges: Mapped[list["EvidenceEdge"]] = relationship(
        "EvidenceEdge", foreign_keys="EvidenceEdge.source_id", back_populates="source", cascade="all, delete-orphan"
    )
    incoming_edges: Mapped[list["EvidenceEdge"]] = relationship(
        "EvidenceEdge", foreign_keys="EvidenceEdge.target_id", back_populates="target", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_evidence_session_type", "session_id", "evidence_type"),
        Index("ix_evidence_name", "name"),
        Index("ix_evidence_qualified_name", "qualified_name"),
        Index("ix_evidence_source_file", "source_file"),
        Index("ix_evidence_content_hash", "content_hash"),
    )


class EvidenceEdge(Base):
    __tablename__ = "evidence_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("evidence_records.id", ondelete="CASCADE"), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), ForeignKey("evidence_records.id", ondelete="CASCADE"), nullable=False)
    edge_type: Mapped[str] = mapped_column(String(50), nullable=False)  # calls, imports, contains, references, etc.
    properties: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    source: Mapped[EvidenceRecord] = relationship("EvidenceRecord", foreign_keys=[source_id], back_populates="outgoing_edges")
    target: Mapped[EvidenceRecord] = relationship("EvidenceRecord", foreign_keys=[target_id], back_populates="incoming_edges")

    __table_args__ = (
        UniqueConstraint("session_id", "source_id", "target_id", "edge_type", name="uq_evidence_edge"),
        Index("ix_edges_session", "session_id"),
        Index("ix_edges_source", "source_id"),
        Index("ix_edges_target", "target_id"),
        Index("ix_edges_type", "edge_type"),
    )


class AnalysisSnapshot(Base):
    __tablename__ = "analysis_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False)
    target_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # ghidra, jadx, etc.
    provider_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    data: Mapped[bytes] = mapped_column(BLOB, nullable=False)  # Compressed serialized evidence
    snapshot_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    session: Mapped[AnalysisSession] = relationship("AnalysisSession", back_populates="snapshots")

    __table_args__ = (
        UniqueConstraint("session_id", "target_hash", "provider", name="uq_snapshot"),
        Index("ix_snapshots_target_hash", "target_hash"),
        Index("ix_snapshots_expires_at", "expires_at"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("analysis_sessions.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_audit_session", "session_id"),
        Index("ix_audit_user", "user_id"),
        Index("ix_audit_action", "action"),
        Index("ix_audit_created_at", "created_at"),
    )