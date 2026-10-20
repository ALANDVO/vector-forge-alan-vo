from __future__ import annotations

import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.core.security import AuthError, Principal, create_demo_principal, token_to_principal, validate_token
from app.api.dependencies import get_current_principal

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(request: Request) -> Response:
    """Initiate OIDC authorization code flow with PKCE."""
    settings = get_settings()

    if settings.demo_mode_allowed:
        client_host = request.client.host if request.client else "unknown"
        if client_host in ("127.0.0.1", "localhost", "::1"):
            # Demo mode: create a demo principal and set cookie
            principal = create_demo_principal()
            response = RedirectResponse(url="/dashboard")
            response.set_cookie(
                key="demo_auth",
                value="true",
                httponly=True,
                secure=False,  # False for localhost dev
                samesite="lax",
                max_age=3600 * 24,  # 24 hours
            )
            return response

    if not settings.oidc_enabled:
        raise HTTPException(
            status_code=503,
            detail="OIDC not configured. Set OIDC_ISSUER_URL and OIDC_CLIENT_SECRET or enable DEMO_MODE for development.",
        )

    # Generate PKCE parameters
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = code_verifier  # In production, use S256: base64url(sha256(code_verifier))
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)

    # Store PKCE params in session (simplified: using signed cookie)
    # In production, use a proper session store
    params = {
        "response_type": "code",
        "client_id": settings.OIDC_CLIENT_ID,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "scope": settings.OIDC_SCOPES,
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "plain",  # Use "S256" in production
    }

    auth_url = f"{settings.OIDC_ISSUER_URL}/protocol/openid-connect/auth?{urlencode(params)}"

    response = RedirectResponse(url=auth_url)
    response.set_cookie(
        key="oidc_state",
        value=state,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=600,  # 10 minutes
    )
    response.set_cookie(
        key="oidc_code_verifier",
        value=code_verifier,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=600,
    )
    response.set_cookie(
        key="oidc_nonce",
        value=nonce,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=600,
    )

    return response


@router.get("/callback")
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> Response:
    """Handle OIDC callback and exchange code for tokens."""
    settings = get_settings()

    if settings.demo_mode_allowed:
        client_host = request.client.host if request.client else "unknown"
        if client_host in ("127.0.0.1", "localhost", "::1"):
            principal = create_demo_principal()
            response = RedirectResponse(url="/dashboard")
            response.set_cookie(
                key="demo_auth",
                value="true",
                httponly=True,
                secure=False,
                samesite="lax",
                max_age=3600 * 24,
            )
            return response

    if not settings.oidc_enabled:
        raise HTTPException(
            status_code=503,
            detail="OIDC not configured",
        )

    # Verify state parameter
    stored_state = request.cookies.get("oidc_state")
    if not stored_state or state != stored_state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    if error:
        raise HTTPException(
            status_code=400,
            detail=f"OIDC error: {error} - {error_description or 'No description'}",
        )

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Exchange code for tokens
    code_verifier = request.cookies.get("oidc_code_verifier")
    if not code_verifier:
        raise HTTPException(status_code=400, detail="Missing code verifier")

    try:
        import httpx

        token_url = f"{settings.OIDC_ISSUER_URL}/protocol/openid-connect/token"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.OIDC_REDIRECT_URI,
            "client_id": settings.OIDC_CLIENT_ID,
            "client_secret": settings.OIDC_CLIENT_SECRET,
            "code_verifier": code_verifier,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            token_response = await client.post(token_url, data=data)
            token_response.raise_for_status()
            tokens = token_response.json()

        access_token = tokens.get("access_token")
        id_token = tokens.get("id_token")
        refresh_token = tokens.get("refresh_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="No access token in response")

        # Validate ID token
        from app.core.security import validate_token

        payload = await validate_token(id_token or access_token)
        principal = token_to_principal(payload)

        # Create response with tokens in HttpOnly cookies
        response = RedirectResponse(url="/dashboard")
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=settings.is_production,
            samesite="lax",
            max_age=3600,  # 1 hour
        )
        if refresh_token:
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=settings.is_production,
                samesite="lax",
                max_age=3600 * 24 * 30,  # 30 days
            )
        response.set_cookie(
            key="user_id",
            value=principal.user_id,
            httponly=False,  # Frontend needs to read this
            secure=settings.is_production,
            samesite="lax",
            max_age=3600 * 24,
        )

        # Clear PKCE cookies
        response.delete_cookie("oidc_state")
        response.delete_cookie("oidc_code_verifier")
        response.delete_cookie("oidc_nonce")

        return response

    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Token exchange failed: {str(e)}")
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/logout")
async def logout(request: Request, response: Response) -> dict:
    """Logout and clear auth cookies."""
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    response.delete_cookie("user_id")
    response.delete_cookie("demo_auth")
    response.delete_cookie("oidc_state")
    response.delete_cookie("oidc_code_verifier")
    response.delete_cookie("oidc_nonce")

    settings = get_settings()
    if settings.oidc_enabled:
        # Redirect to Keycloak logout
        logout_url = f"{settings.OIDC_ISSUER_URL}/protocol/openid-connect/logout"
        return {"logout_url": logout_url, "message": "Logged out successfully"}

    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_user(principal: Principal = Depends(get_current_principal)) -> dict:
    """Get current authenticated user info."""
    return {
        "user_id": principal.user_id,
        "roles": principal.roles,
        "email": principal.email,
        "name": principal.name,
    }


@router.post("/refresh")
async def refresh_token(request: Request, response: Response) -> dict:
    """Refresh access token using refresh token."""
    settings = get_settings()
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    if not settings.oidc_enabled:
        raise HTTPException(status_code=503, detail="OIDC not configured")

    try:
        import httpx

        token_url = f"{settings.OIDC_ISSUER_URL}/protocol/openid-connect/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": settings.OIDC_CLIENT_ID,
            "client_secret": settings.OIDC_CLIENT_SECRET,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            token_response = await client.post(token_url, data=data)
            token_response.raise_for_status()
            tokens = token_response.json()

        access_token = tokens.get("access_token")
        new_refresh_token = tokens.get("refresh_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="No access token in response")

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=settings.is_production,
            samesite="lax",
            max_age=3600,
        )
        if new_refresh_token:
            response.set_cookie(
                key="refresh_token",
                value=new_refresh_token,
                httponly=True,
                secure=settings.is_production,
                samesite="lax",
                max_age=3600 * 24 * 30,
            )

        return {"message": "Token refreshed"}

    except httpx.HTTPError as e:
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        raise HTTPException(status_code=401, detail=f"Token refresh failed: {str(e)}")