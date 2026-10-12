from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from app.mcp.server import JSONRPCRequest, JSONRPCResponse, MCPTransport


class HTTPTransport(MCPTransport):
    def __init__(self, app: FastAPI, path: str = "/mcp"):
        self.app = app
        self.path = path
        self._handler: Optional[Callable[[JSONRPCRequest], None]] = None
        self._pending_responses: dict[str | int, asyncio.Queue] = {}
        self._setup_routes()

    def _setup_routes(self) -> None:
        @self.app.post(self.path)
        async def mcp_post(request: Request):
            body = await request.body()
            try:
                req = JSONRPCRequest.model_validate_json(body)
            except Exception:
                return Response(
                    content=JSONRPCResponse(
                        id=None,
                        error={"code": -32700, "message": "Parse error"},
                    ).model_dump_json(exclude_none=True),
                    media_type="application/json",
                )

            if self._handler:
                self._handler(req)

            # Wait for response if request has id
            if req.id is not None:
                queue: asyncio.Queue = asyncio.Queue()
                self._pending_responses[req.id] = queue
                try:
                    response = await asyncio.wait_for(queue.get(), timeout=30.0)
                    return Response(content=response.model_dump_json(exclude_none=True), media_type="application/json")
                except asyncio.TimeoutError:
                    return Response(
                        content=JSONRPCResponse(
                            id=req.id,
                            error={"code": -32603, "message": "Request timeout"},
                        ).model_dump_json(exclude_none=True),
                        media_type="application/json",
                    )
                finally:
                    self._pending_responses.pop(req.id, None)

            return Response(status_code=202)

        @self.app.get(self.path)
        async def mcp_sse(request: Request):
            async def event_generator():
                queue: asyncio.Queue = asyncio.Queue()
                client_id = id(queue)
                self._pending_responses[client_id] = queue

                try:
                    while True:
                        response = await queue.get()
                        yield {"data": response.model_dump_json(exclude_none=True)}
                except asyncio.CancelledError:
                    pass
                finally:
                    self._pending_responses.pop(client_id, None)

            return EventSourceResponse(event_generator())

    async def start(self) -> None:
        pass  # Routes already registered

    async def stop(self) -> None:
        for queue in self._pending_responses.values():
            await queue.put(JSONRPCResponse(id=None, error={"code": -32603, "message": "Server shutting down"}))
        self._pending_responses.clear()

    async def send(self, message: JSONRPCResponse) -> None:
        if message.id is not None:
            queue = self._pending_responses.get(message.id)
            if queue:
                await queue.put(message)
        else:
            # Broadcast to all SSE clients
            for queue in self._pending_responses.values():
                if not isinstance(queue._getters[0] if queue._getters else None, asyncio.Queue):
                    await queue.put(message)

    def on_message(self, handler: Callable[[JSONRPCRequest], None]) -> None:
        self._handler = handler