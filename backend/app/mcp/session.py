from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class MCPSession:
    id: str = field(default_factory=lambda: str(uuid4()))
    client_info: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    last_activity: datetime = field(default_factory=utc_now)
    capabilities: dict = field(default_factory=dict)
    initialized: bool = False
    active_requests: dict[str, Any] = field(default_factory=dict)


class MCPSessionManager:
    def __init__(self):
        self._sessions: dict[str, MCPSession] = {}
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def create_session(self, client_info: dict = None) -> MCPSession:
        session = MCPSession(client_info=client_info or {})
        async with self._lock:
            self._sessions[session.id] = session
        try:
            yield session
        finally:
            async with self._lock:
                self._sessions.pop(session.id, None)

    async def get_session(self, session_id: str) -> Optional[MCPSession]:
        async with self._lock:
            return self._sessions.get(session_id)

    async def update_activity(self, session_id: str) -> None:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.last_activity = utc_now()

    async def register_request(self, session_id: str, request_id: str | int, request: Any) -> None:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.active_requests[str(request_id)] = request

    async def unregister_request(self, session_id: str, request_id: str | int) -> None:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.active_requests.pop(str(request_id), None)

    async def cancel_all_requests(self, session_id: str) -> None:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                for req in session.active_requests.values():
                    if hasattr(req, "cancel"):
                        req.cancel()
                session.active_requests.clear()

    async def list_sessions(self) -> list[MCPSession]:
        async with self._lock:
            return list(self._sessions.values())

    async def cleanup_stale(self, max_age_seconds: int = 3600) -> int:
        now = utc_now()
        removed = 0
        async with self._lock:
            stale = [
                sid for sid, s in self._sessions.items()
                if (now - s.last_activity).total_seconds() > max_age_seconds
            ]
            for sid in stale:
                self._sessions.pop(sid, None)
                removed += 1
        return removed