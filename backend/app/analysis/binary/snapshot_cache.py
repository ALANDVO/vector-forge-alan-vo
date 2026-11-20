from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import structlog

from app.core.database import get_session_factory


def compute_target_hash(content: bytes, algo: str = "sha256") -> str:
    """Compute a hash of the target binary content for cache lookup."""
    return hashlib.new(algo, content).hexdigest()


class SnapshotCache:
    """Cache for Ghidra analysis snapshots keyed by target hash."""

    def __init__(self):
        pass

    async def get(self, target_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve a cached analysis snapshot by hash."""
        async with get_session_factory()() as session:
            from sqlalchemy import select
            from app.models.evidence import AnalysisSnapshot

            result = await session.execute(
                select(AnalysisSnapshot).where(AnalysisSnapshot.target_hash == target_hash)
            )
            snapshot = result.scalar_one_or_none()
            if snapshot is None:
                return None
            return {
                "evidence": snapshot.evidence_data,
                "created_at": snapshot.created_at.isoformat(),
                "session_id": snapshot.session_id,
            }

    async def set(
        self,
        target_hash: str,
        evidence: Dict[str, Any],
        session_id: str,
    ) -> None:
        """Store an analysis snapshot in the cache."""
        async with get_session_factory()() as session:
            from sqlalchemy import insert
            from app.models.evidence import AnalysisSnapshot

            now = datetime.now(timezone.utc)
            await session.execute(
                insert(AnalysisSnapshot).values(
                    target_hash=target_hash,
                    evidence_data=evidence,
                    session_id=session_id,
                    created_at=now,
                )
            )
            await session.commit()
            logger.info("snapshot_cached", target_hash=target_hash[:16], session_id=session_id)

    async def invalidate(self, target_hash: str) -> int:
        """Invalidate a cached snapshot. Returns number of rows deleted."""
        async with get_session_factory()() as session:
            from sqlalchemy import delete
            from app.models.evidence import AnalysisSnapshot

            result = await session.execute(
                delete(AnalysisSnapshot).where(AnalysisSnapshot.target_hash == target_hash)
            )
            await session.commit()
            return result.rowcount
