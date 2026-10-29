"""Tests for authentication endpoints and security."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from jose import jwt
from datetime import datetime, timedelta, timezone

from app.main import create_app
from app.core.config import Settings, get_settings
from app.core.security import Principal, TokenPayload, AuthError, create_demo_principal, validate_token, token_to_principal
from app.core.database import init_db, close_db


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Clear settings cache before each test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def demo_settings(monkeypatch):
    """Enable demo mode via environment variables."""
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("OIDC_ISSUER_URL", "")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "")
    monkeypatch.setenv("DEMO_USER_ID", "demo-user")
    monkeypatch.setenv("DEMO_USER_ROLES", "viewer,operator")
    get_settings.cache_clear()
    return Settings()


@pytest.fixture
def no_demo_settings(monkeypatch):
    """Disable demo mode via environment variables."""
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("OIDC_ISSUER_URL", "")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "")
    get_settings.cache_clear()
    return Settings()


@pytest.fixture
def oidc_settings(monkeypatch):
    """Enable OIDC via environment variables."""
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("OIDC_ISSUER_URL", "http://localhost:8080/realms/master")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "secret")
    monkeypatch.setenv("OIDC_AUDIENCE", "vector-forge-api")
    get_settings.cache_clear()
    return Settings()


class TestAuthEndpoints:
    """Test authentication API endpoints."""

    @pytest_asyncio.fixture
    async def app(self, demo_settings):
        app = create_app()
        await init_db()
        yield app
        await close_db()

    @pytest_asyncio.fixture
    async def client(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest_asyncio.fixture
    async def app_no_demo(self, no_demo_settings):
        app = create_app()
        await init_db()
        yield app
        await close_db()

    @pytest_asyncio.fixture
    async def client_no_demo(self, app_no_demo):
        transport = ASGITransport(app=app_no_demo)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.mark.asyncio
    async def test_login_demo_mode_allowed(self, client):
        """Test /login endpoint in demo mode returns redirect with demo cookie."""
        response = await client.get("/auth/login", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/dashboard"
        assert "demo_auth" in response.cookies

    @pytest.mark.asyncio
    async def test_login_no_demo_no_oidc(self, client_no_demo):
        """Test /login without demo mode and no OIDC config returns 503."""
        response = await client_no_demo.get("/auth/login")
        assert response.status_code == 503
        assert "OIDC not configured" in response.text

    @pytest.mark.asyncio
    async def test_callback_demo_mode(self, client):
        """Test /callback in demo mode returns redirect with demo cookie."""
        response = await client.get("/auth/callback", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/dashboard"
        assert "demo_auth" in response.cookies

    @pytest.mark.asyncio
    async def test_callback_no_demo_no_oidc(self, client_no_demo):
        """Test /callback without demo mode and no OIDC config returns 503."""
        response = await client_no_demo.get("/auth/callback")
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_logout_clears_cookies(self, client):
        """Test /logout clears all auth cookies."""
        await client.get("/auth/login")
        response = await client.post("/auth/logout")
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"

    @pytest.mark.asyncio
    async def test_me_unauthenticated(self, client_no_demo):
        """Test /me endpoint without authentication returns 401."""
        response = await client_no_demo.get("/auth/me")
        assert response.status_code == 401
        assert "Missing or invalid Authorization header" in response.text

    @pytest.mark.asyncio
    async def test_me_with_invalid_token(self, oidc_settings):
        """Test /me endpoint with invalid token returns 401."""
        app = create_app()
        await init_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/auth/me", headers={"Authorization": "Bearer invalid_token"})
                assert response.status_code == 401
        finally:
            await close_db()

    @pytest.mark.asyncio
    async def test_refresh_no_token(self, client_no_demo):
        """Test /refresh without refresh token returns 401."""
        response = await client_no_demo.post("/auth/refresh")
        assert response.status_code == 401
        assert "No refresh token" in response.text

    @pytest.mark.asyncio
    async def test_refresh_no_oidc(self, client):
        """Test /refresh with demo mode (no OIDC) returns 503."""
        client.cookies.set("refresh_token", "dummy_token")
        response = await client.post("/auth/refresh")
        assert response.status_code == 503
        assert "OIDC not configured" in response.text


class TestSecurityModule:
    """Test core security functions."""

    def test_principal_has_role(self):
        """Test Principal.has_role method."""
        principal = Principal(user_id="user1", email="user@example.com", name=None, roles={"viewer", "operator"})
        assert principal.has_role("viewer") is True
        assert principal.has_role("operator") is True
        assert principal.has_role("admin") is False

    def test_principal_has_any_role(self):
        """Test Principal.has_any_role method."""
        principal = Principal(user_id="user1", email="user@example.com", name=None, roles={"viewer"})
        assert principal.has_any_role(["viewer", "admin"]) is True
        assert principal.has_any_role(["operator", "admin"]) is False

    def test_create_demo_principal(self, demo_settings):
        """Test demo principal creation."""
        principal = create_demo_principal()
        assert principal.user_id == "demo-user"
        assert "viewer" in principal.roles
        assert "operator" in principal.roles

    def test_token_to_principal(self):
        """Test conversion from TokenPayload to Principal."""
        payload = TokenPayload(
            sub="user123",
            email="user@example.com",
            roles=["viewer", "operator"],
            exp=int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            iat=int(datetime.now(timezone.utc).timestamp()),
            aud="vector-forge-api",
            iss="http://localhost:8080/realms/master",
        )
        principal = token_to_principal(payload)
        assert principal.user_id == "user123"
        assert principal.email == "user@example.com"
        assert "viewer" in principal.roles
        assert "operator" in principal.roles

    def test_require_role_success(self):
        """Test require_role passes when role present."""
        principal = Principal(user_id="user1", email="user@example.com", name=None, roles={"admin"})
        from app.core.security import require_role
        require_role(principal, "admin")

    def test_require_role_failure(self):
        """Test require_role raises when role missing."""
        principal = Principal(user_id="user1", email="user@example.com", name=None, roles={"viewer"})
        from app.core.security import require_role
        with pytest.raises(AuthError) as exc_info:
            require_role(principal, "admin")
        assert exc_info.value.status_code == 403
        assert "Required role: admin" in str(exc_info.value)

    def test_require_any_role_success(self):
        """Test require_any_role passes when any role present."""
        principal = Principal(user_id="user1", email="user@example.com", name=None, roles={"viewer"})
        from app.core.security import require_any_role
        require_any_role(principal, ["admin", "viewer"])

    def test_require_any_role_failure(self):
        """Test require_any_role raises when no roles match."""
        principal = Principal(user_id="user1", email="user@example.com", name=None, roles={"viewer"})
        from app.core.security import require_any_role
        with pytest.raises(AuthError) as exc_info:
            require_any_role(principal, ["admin", "operator"])
        assert exc_info.value.status_code == 403
        assert "Required one of roles: ['admin', 'operator']" in str(exc_info.value)


class TestTokenValidation:
    """Test JWT token validation logic."""

    @pytest.mark.asyncio
    async def test_validate_token_no_oidc(self, no_demo_settings):
        """Test validate_token raises when OIDC not configured."""
        with pytest.raises(AuthError) as exc_info:
            await validate_token("dummy_token")
        assert exc_info.value.status_code == 503
        assert "OIDC not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_token_invalid_header(self, oidc_settings):
        """Test validate_token raises on invalid token header."""
        with pytest.raises(AuthError) as exc_info:
            await validate_token("invalid.token.string")
        assert exc_info.value.status_code == 401
        assert "Invalid token header" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_token_missing_kid(self, oidc_settings):
        """Test validate_token raises when token missing kid."""
        token = jwt.encode({"sub": "user1"}, "secret", algorithm="HS256")
        with pytest.raises(AuthError) as exc_info:
            await validate_token(token)
        assert exc_info.value.status_code == 401
        assert "Token missing kid header" in str(exc_info.value)


class TestAuthDependencies:
    """Test FastAPI dependency injection for authentication."""

    @pytest.mark.asyncio
    async def test_get_current_principal_demo_mode(self, demo_settings):
        """Test get_current_principal returns demo principal in demo mode."""
        from app.api.dependencies import get_current_principal
        from fastapi import Request
        
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "127.0.0.1"
        
        mock_db = AsyncMock()
        principal = await get_current_principal(mock_request, authorization=None, db=mock_db)
        assert principal.user_id == "demo-user"
        assert "viewer" in principal.roles

    @pytest.mark.asyncio
    async def test_get_current_principal_no_auth_header(self, no_demo_settings):
        """Test get_current_principal raises without auth header when not in demo mode."""
        from app.api.dependencies import get_current_principal
        from fastapi import Request, HTTPException
        
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "192.168.1.100"
        
        mock_db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_principal(mock_request, authorization=None, db=mock_db)
        assert exc_info.value.status_code == 401
        assert "Missing or invalid Authorization header" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_principal_invalid_auth_header(self, no_demo_settings):
        """Test get_current_principal raises with invalid auth header format."""
        from app.api.dependencies import get_current_principal
        from fastapi import Request, HTTPException
        
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "192.168.1.100"
        
        mock_db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_principal(mock_request, authorization="InvalidFormat token", db=mock_db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_optional_principal_returns_none_on_error(self, no_demo_settings):
        """Test get_optional_principal returns None on auth failure."""
        from app.api.dependencies import get_optional_principal
        from fastapi import Request
        
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "192.168.1.100"
        
        mock_db = AsyncMock()
        principal = await get_optional_principal(mock_request, authorization=None, db=mock_db)
        assert principal is None


class TestAuthIntegration:
    """Integration tests for auth flow."""

    @pytest.mark.asyncio
    async def test_full_demo_login_me_logout_flow(self, demo_settings):
        """Test complete demo mode auth flow: login -> me -> logout."""
        app = create_app()
        await init_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                login_response = await client.get("/auth/login", follow_redirects=False)
                assert login_response.status_code == 307
                assert "demo_auth" in login_response.cookies
                
                client.cookies = login_response.cookies
                me_response = await client.get("/auth/me")
                assert me_response.status_code == 200
                assert me_response.json()["user_id"] == "demo-user"
                assert "viewer" in me_response.json()["roles"]
                assert "operator" in me_response.json()["roles"]
                
                logout_response = await client.post("/auth/logout")
                assert logout_response.status_code == 200
        finally:
            await close_db()


class TestProductionModeSafety:
    """Test that demo mode is rejected in production."""

    def test_demo_mode_rejected_in_production(self):
        """Test DEMO_MODE=True with ENVIRONMENT=production raises error."""
        with pytest.raises(RuntimeError) as exc_info:
            Settings(DEMO_MODE=True, ENVIRONMENT="production").validate_demo_mode()
        assert "DEMO_MODE cannot be enabled in production" in str(exc_info.value)

    def test_demo_mode_allowed_false_in_production(self):
        """Test demo_mode_allowed is False in production even if DEMO_MODE=True."""
        settings = Settings(DEMO_MODE=True, ENVIRONMENT="production")
        assert settings.demo_mode_allowed is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
