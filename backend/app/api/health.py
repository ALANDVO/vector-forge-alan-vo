from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_session)):
    settings = get_settings()
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "demo_mode": settings.demo_mode_allowed,
        "oidc_enabled": settings.oidc_enabled,
    }


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_session)):
    try:
        await db.execute(text("SELECT 1"))
        return {"ready": True}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ready": False}