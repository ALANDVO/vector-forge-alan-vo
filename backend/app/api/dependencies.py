from __future__ import annotations

from collections.abc import AsyncGenerator
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.security import AuthError, Principal, create_demo_principal, token_to_principal, validate_token
from app.services.evidence_service import EvidenceService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_session() as session:
        yield session


def get_evidence_service(db: AsyncSession = Depends(get_db)) -> EvidenceService:
    return EvidenceService(db)


async def get_current_principal(
    request: Request,
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Principal:
    settings = get_settings()

    # Demo mode: localhost only, no auth header required
    if settings.demo_mode_allowed:
        client_host = request.client.host if request.client else "unknown"
        if client_host in ("127.0.0.1", "localhost", "::1"):
            return create_demo_principal()

    # OIDC token validation
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:]  # Remove "Bearer "
    try:
        payload = await validate_token(token)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    return token_to_principal(payload)


async def get_optional_principal(
    request: Request,
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Principal | None:
    try:
        return await get_current_principal(request, authorization, db)
    except HTTPException:
        return None