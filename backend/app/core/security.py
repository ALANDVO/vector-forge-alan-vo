from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from jose import jwt, JWTError
from pydantic import BaseModel

from app.core.config import get_settings


class TokenPayload(BaseModel):
    sub: str
    email: Optional[str] = None
    name: Optional[str] = None
    roles: list[str] = []
    exp: int
    iat: int
    aud: Optional[str] = None
    iss: Optional[str] = None
    nonce: Optional[str] = None

@dataclass
class Principal:
    user_id: str
    email: Optional[str]
    name: Optional[str]
    roles: set[str]

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_any_role(self, roles: list[str]) -> bool:
        return any(r in self.roles for r in roles)


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# In-memory JWKS cache (in production, fetch from Keycloak)
_jwks_cache: dict = {}
_jwks_fetched_at: float = 0
JWKS_TTL = 3600  # 1 hour


async def fetch_jwks() -> dict:
    import httpx

    global _jwks_cache, _jwks_fetched_at
    settings = get_settings()

    if not settings.oidc_enabled:
        return {}

    now = time.time()
    if _jwks_cache and (now - _jwks_fetched_at) < JWKS_TTL:
        return _jwks_cache

    jwks_url = f"{settings.OIDC_ISSUER_URL.rstrip('/')}/protocol/openid-connect/certs"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_fetched_at = now
        return _jwks_cache


def get_signing_key(jwks: dict, kid: str) -> Optional[dict]:
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


async def validate_token(token: str) -> TokenPayload:
    settings = get_settings()

    if not settings.oidc_enabled:
        raise AuthError("OIDC not configured", 503)

    try:
        header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise AuthError(f"Invalid token header: {e}", 401)

    kid = header.get("kid")
    if not kid:
        raise AuthError("Token missing kid header", 401)

    jwks = await fetch_jwks()
    key = get_signing_key(jwks, kid)
    if not key:
        raise AuthError("Signing key not found", 401)

    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.OIDC_AUDIENCE,
            issuer=settings.OIDC_ISSUER_URL,
            options={"verify_exp": True, "verify_aud": True, "verify_iss": True},
        )
    except JWTError as e:
        raise AuthError(f"Token validation failed: {e}", 401)

    return TokenPayload(**payload)


def create_demo_principal() -> Principal:
    settings = get_settings()
    if not settings.demo_mode_allowed:
        raise AuthError("Demo mode not allowed", 403)
    roles = set(settings.DEMO_USER_ROLES.split(","))
    return Principal(
        user_id=settings.DEMO_USER_ID,
        email="demo@local",
        name="Demo User",
        roles=roles,
    )


def token_to_principal(payload: TokenPayload) -> Principal:
    return Principal(
        user_id=payload.sub,
        email=payload.email,
        name=payload.name,
        roles=set(payload.roles),
    )


def require_role(principal: Principal, role: str) -> None:
    if not principal.has_role(role):
        raise AuthError(f"Required role: {role}", 403)


def require_any_role(principal: Principal, roles: list[str]) -> None:
    if not principal.has_any_role(roles):
        raise AuthError(f"Required one of roles: {roles}", 403)