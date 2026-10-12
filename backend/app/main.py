from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from structlog import get_logger

from app.core.config import get_settings
from app.core.database import init_db, close_db
from app.api import health, evidence
from app.mcp import MCPServer, HTTPTransport, register_core_tools
from app.services.evidence_service import EvidenceService
from app.mcp.tools import set_evidence_service

logger = get_logger()


# Global MCP server instance
mcp_server: MCPServer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global mcp_server

    settings = get_settings()
    logger.info("Starting Vector Forge", version=settings.APP_VERSION, environment=settings.ENVIRONMENT)

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Initialize MCP server
    mcp_server = MCPServer(name="vector-forge", version=settings.APP_VERSION)
    await register_core_tools(mcp_server)

    # Set evidence service for MCP tools
    # Note: In a real app, we'd use dependency injection
    # For now, we'll create a session when needed

    # Start MCP HTTP transport if enabled
    if settings.MCP_TRANSPORT == "http":
        transport = HTTPTransport(app, path="/mcp")
        await mcp_server.initialize(transport)
        logger.info("MCP HTTP transport started", path="/mcp")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down Vector Forge")
    if mcp_server:
        await mcp_server.shutdown()
    await close_db()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Vector Forge API",
        description="Reverse engineering MCP server and API",
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:8080", "http://127.0.0.1:5173", "http://127.0.0.1:8080"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router)
    app.include_router(evidence.router)

    @app.get("/")
    async def root():
        return {
            "name": "Vector Forge",
            "version": settings.APP_VERSION,
            "description": "Reverse engineering MCP server and API",
            "docs": "/docs",
            "health": "/health",
            "mcp": "/mcp",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )