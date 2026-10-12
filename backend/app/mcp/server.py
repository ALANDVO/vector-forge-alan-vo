from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str
    params: dict | list | None = None


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    result: Any = None
    error: Optional["JSONRPCError"] = None


class JSONRPCError(BaseModel):
    code: int
    message: str
    data: Any = None


class MCPTool(BaseModel):
    name: str
    description: str
    inputSchema: dict = Field(default_factory=dict)


class MCPToolCall(BaseModel):
    name: str
    arguments: dict = Field(default_factory=dict)


class MCPToolResult(BaseModel):
    content: list[dict] = Field(default_factory=list)
    isError: bool = False
    structuredContent: dict | None = None


class MCPInitializeParams(BaseModel):
    protocolVersion: str = "2024-11-05"
    capabilities: dict = Field(default_factory=dict)
    clientInfo: dict = Field(default_factory=dict)


class MCPInitializeResult(BaseModel):
    protocolVersion: str = "2024-11-05"
    capabilities: dict = Field(default_factory=dict)
    serverInfo: dict = Field(default_factory=dict)


@dataclass
class MCPToolDefinition:
    name: str
    description: str
    input_schema: dict
    handler: Callable[[dict], Any]


class MCPTransport(ABC):
    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @abstractmethod
    async def send(self, message: JSONRPCResponse) -> None:
        pass

    @abstractmethod
    def on_message(self, handler: Callable[[JSONRPCRequest], None]) -> None:
        pass


class MCPServer:
    def __init__(self, name: str = "vector-forge", version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.tools: dict[str, MCPToolDefinition] = {}
        self.transport: Optional[MCPTransport] = None
        self._initialized = False
        self._shutdown_requested = False

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: dict,
        handler: Callable[[dict], Any],
    ) -> None:
        self.tools[name] = MCPToolDefinition(name, description, input_schema, handler)

    def unregister_tool(self, name: str) -> bool:
        return self.tools.pop(name, None) is not None

    async def initialize(self, transport: MCPTransport) -> None:
        self.transport = transport
        transport.on_message(self._handle_request)
        await transport.start()

    async def shutdown(self) -> None:
        self._shutdown_requested = True
        if self.transport:
            await self.transport.stop()

    def _handle_request(self, request: JSONRPCRequest) -> None:
        import asyncio
        asyncio.create_task(self._process_request(request))

    async def _process_request(self, request: JSONRPCRequest) -> None:
        if not self.transport:
            return

        response = JSONRPCResponse(id=request.id)

        try:
            if request.method == "initialize":
                result = await self._handle_initialize(request.params or {})
                response.result = result.model_dump()
            elif request.method == "tools/list":
                result = await self._handle_tools_list()
                response.result = result
            elif request.method == "tools/call":
                result = await self._handle_tool_call(request.params or {})
                response.result = result.model_dump()
            elif request.method == "notifications/cancelled":
                await self._handle_cancellation(request.params or {})
                return  # No response for notifications
            elif request.method == "shutdown":
                await self.shutdown()
                response.result = {}
            else:
                response.error = JSONRPCError(
                    code=-32601,
                    message=f"Method not found: {request.method}",
                )
        except Exception as e:
            response.error = JSONRPCError(
                code=-32603,
                message=f"Internal error: {str(e)}",
            )

        await self.transport.send(response)

    async def _handle_initialize(self, params: dict) -> MCPInitializeResult:
        self._initialized = True
        return MCPInitializeResult(
            serverInfo={"name": self.name, "version": self.version},
            capabilities={
                "tools": {"listChanged": True},
            },
        )

    async def _handle_tools_list(self) -> dict:
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.input_schema,
                }
                for tool in self.tools.values()
            ]
        }

    async def _handle_tool_call(self, params: dict) -> MCPToolResult:
        tool_call = MCPToolCall(**params)
        tool = self.tools.get(tool_call.name)
        if not tool:
            return MCPToolResult(
                content=[{"type": "text", "text": f"Tool not found: {tool_call.name}"}],
                isError=True,
            )

        try:
            result = await tool.handler(tool_call.arguments)
            if isinstance(result, MCPToolResult):
                return result
            return MCPToolResult(
                content=[{"type": "text", "text": str(result)}],
                structuredContent=result if isinstance(result, dict) else None,
            )
        except Exception as e:
            return MCPToolResult(
                content=[{"type": "text", "text": f"Tool error: {str(e)}"}],
                isError=True,
            )

    async def _handle_cancellation(self, params: dict) -> None:
        # Cancellation handled by individual tool handlers checking context
        pass


class StdioTransport(MCPTransport):
    def __init__(self):
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._handler: Optional[Callable[[JSONRPCRequest], None]] = None
        self._running = False

    async def start(self) -> None:
        import sys
        import asyncio

        self._reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(self._reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
        self._writer = asyncio.StreamWriter(sys.stdout, {}, None, asyncio.get_event_loop())
        self._running = True
        asyncio.create_task(self._read_loop())

    async def stop(self) -> None:
        self._running = False
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

    async def send(self, message: JSONRPCResponse) -> None:
        if self._writer:
            data = message.model_dump_json(exclude_none=True) + "\n"
            self._writer.write(data.encode())
            await self._writer.drain()

    def on_message(self, handler: Callable[[JSONRPCRequest], None]) -> None:
        self._handler = handler

    async def _read_loop(self) -> None:
        import asyncio

        while self._running:
            try:
                line = await self._reader.readline()
                if not line:
                    break
                line = line.decode().strip()
                if not line:
                    continue
                request = JSONRPCRequest.model_validate_json(line)
                if self._handler:
                    self._handler(request)
            except Exception:
                # Ignore parse errors, continue reading
                pass


import asyncio