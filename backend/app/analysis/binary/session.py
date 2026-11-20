from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

import structlog

from app.analysis.binary.snapshot_cache import SnapshotCache, compute_target_hash

logger = structlog.get_logger(__name__)


@dataclass
class BinarySession:
    """Represents a binary analysis session with Ghidra."""

    session_id: str
    target_path: str
    target_hash: str
    status: str = "initialized"  # initialized, running, completed, cancelled, failed
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    cache: SnapshotCache = field(default_factory=SnapshotCache)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session to dict for API responses."""
        return {
            "session_id": self.session_id,
            "target_path": self.target_path,
            "target_hash": self.target_hash,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "has_evidence": self.evidence is not None,
            "error": self.error,
        }

    @property
    def is_terminal(self) -> bool:
        """Check if session is in a terminal state."""
        return self.status in ("completed", "cancelled", "failed")

    async def save_evidence(self, evidence: Dict[str, Any]) -> None:
        """Save analysis evidence and update status."""
        self.evidence = evidence
        self.status = "completed"
        self.completed_at = datetime.now(timezone.utc).isoformat()
        await self.cache.set(
            self.target_hash, evidence, self.session_id
        )
        logger.info("session_evidence_saved", session_id=self.session_id)

    async def mark_failed(self, error: str) -> None:
        """Mark session as failed with error message."""
        self.error = error
        self.status = "failed"
        self.completed_at = datetime.now(timezone.utc).isoformat()
        logger.error("session_failed", session_id=self.session_id, error=error)

    async def mark_cancelled(self) -> None:
        """Mark session as cancelled."""
        self.status = "cancelled"
        self.completed_at = datetime.now(timezone.utc).isoformat()
        logger.info("session_cancelled", session_id=self.session_id)
