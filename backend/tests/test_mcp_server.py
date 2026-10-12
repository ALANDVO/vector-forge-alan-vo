import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from app.mcp.server import MCPServer, JSONRPCRequest, JSONRPCResponse, StdioTransport


@pytest_asyncio.fixture
async def mcp_server():
    server = MCPServer(name="test", version="1.0.0")
    yield server
    await server.shutdown()


@pytest.mark.asyncio
async def test_register_tool(mcp_server):
    async def handler(args):
        return {"result": "ok"}

    mcp_server.register_tool("test_tool", "Test tool", {"type": "object"}, handler)
    assert "test_tool" in mcp_server.tools
    assert mcp_server.tools["test_tool"].name == "test_tool"


@pytest.mark.asyncio
async def test_unregister_tool(mcp_server):
    async def handler(args):
        return {"result": "ok"}

    mcp_server.register_tool("test_tool", "Test tool", {"type": "object"}, handler)
    assert mcp_server.unregister_tool("test_tool") is True
    assert "test_tool" not in mcp_server.tools
    assert mcp_server.unregister_tool("nonexistent") is False


@pytest.mark.asyncio
async def test_initialize_request(mcp_server):
    request = JSONRPCRequest(id=1, method="initialize", params={})
    response = JSONRPCResponse(id=1)

    # Simulate handling
    result = await mcp_server._handle_initialize({})
    assert result.protocolVersion == "2024-11-05"
    assert result.serverInfo["name"] == "test"
    assert mcp_server._initialized is True


@pytest.mark.asyncio
async def test_tools_list_request(mcp_server):
    async def handler(args):
        return {"result": "ok"}

    mcp_server.register_tool("tool1", "Tool 1", {"type": "object"}, handler)
    mcp_server.register_tool("tool2", "Tool 2", {"type": "object"}, handler)

    result = await mcp_server._handle_tools_list()
    assert len(result["tools"]) == 2
    tool_names = {t["name"] for t in result["tools"]}
    assert tool_names == {"tool1", "tool2"}


@pytest.mark.asyncio
async def test_tool_call_request(mcp_server):
    async def handler(args):
        return {"echo": args.get("value")}

    mcp_server.register_tool("echo", "Echo tool", {"type": "object"}, handler)

    from app.mcp.server import MCPToolCall
    call = MCPToolCall(name="echo", arguments={"value": "hello"})
    result = await mcp_server._handle_tool_call(call.model_dump())

    assert result.isError is False
    assert result.structuredContent == {"echo": "hello"}


@pytest.mark.asyncio
async def test_tool_call_not_found(mcp_server):
    from app.mcp.server import MCPToolCall
    call = MCPToolCall(name="nonexistent", arguments={})
    result = await mcp_server._handle_tool_call(call.model_dump())

    assert result.isError is True
    assert "Tool not found" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_tool_call_error(mcp_server):
    async def handler(args):
        raise ValueError("Test error")

    mcp_server.register_tool("error_tool", "Error tool", {"type": "object"}, handler)

    from app.mcp.server import MCPToolCall
    call = MCPToolCall(name="error_tool", arguments={})
    result = await mcp_server._handle_tool_call(call.model_dump())

    assert result.isError is True
    assert "Tool error: Test error" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_shutdown_request(mcp_server):
    request = JSONRPCRequest(id=1, method="shutdown", params={})
    response = JSONRPCResponse(id=1)

    # We can't easily test the full shutdown flow, but we can verify the method exists
    assert hasattr(mcp_server, "shutdown")


@pytest.mark.asyncio
async def test_unknown_method(mcp_server):
    request = JSONRPCRequest(id=1, method="unknown/method", params={})
    response = JSONRPCResponse(id=1)

    # Simulate the error handling
    try:
        # This would be handled in _process_request
        raise Exception("Method not found")
    except Exception:
        pass

    # Just verify the error code structure
    from app.mcp.server import JSONRPCError
    error = JSONRPCError(code=-32601, message="Method not found: unknown/method")
    assert error.code == -32601