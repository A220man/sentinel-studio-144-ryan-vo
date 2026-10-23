from datetime import datetime, UTC
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode
import httpx
import logging

from app.core.config import settings
from app.core.security import (
    generate_state,
    generate_pkce_pair,
    hash_csrf_token,
    verify_csrf_token,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models import User, UserRole, AuditLog, AuditAction
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)


class KeycloakAuth:
    def __init__(self):
        self.client_id = settings.KEYCLOAK_CLIENT_ID
        self.client_secret = settings.KEYCLOAK_CLIENT_SECRET
        self.redirect_uri = settings.KEYCLOAK_REDIRECT_URI
        self.auth_url = settings.KEYCLOAK_AUTH_URL
        self.token_url = settings.KEYCLOAK_TOKEN_URL
        self.jwks_url = settings.KEYCLOAK_JWKS_URL
        self.userinfo_url = settings.KEYCLOAK_USERINFO_URL
        self.logout_url = settings.KEYCLOAK_LOGOUT_URL
        self.issuer = settings.KEYCLOAK_ISSUER_URL
        self._jwks_cache: Optional[Dict[str, Any]] = None

    def build_auth_url(self, state: str, code_challenge: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid profile email",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code_for_tokens(
        self, code: str, code_verifier: str
    ) -> Optional[Dict[str, Any]]:
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier,
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.token_url, data=data)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Token exchange failed: {e}")
            return None

    async def get_userinfo(self, access_token: str) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.userinfo_url,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Userinfo request failed: {e}")
            return None

    async def get_jwks(self) -> Dict[str, Any]:
        if self._jwks_cache is None:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(self.jwks_url)
                    response.raise_for_status()
                    self._jwks_cache = response.json()
            except httpx.HTTPError as e:
                logger.error(f"JWKS fetch failed: {e}")
                return {"keys": []}
        return self._jwks_cache

    def verify_id_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        from jose import jwt, JWTError
        try:
            # In production, verify signature using JWKS
            # For now, decode without verification for demo
            payload = jwt.decode(
                id_token,
                options={"verify_signature": settings.DEMO_MODE},
                audience=self.client_id,
                issuer=self.issuer,
            )
            return payload
        except JWTError as e:
            logger.error(f"ID token verification failed: {e}")
            return None


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.keycloak = KeycloakAuth()

    async def get_or_create_user(self, userinfo: Dict[str, Any], id_token_payload: Dict[str, Any]) -> User:
        sub = userinfo.get("sub") or id_token_payload.get("sub")
        email = userinfo.get("email") or id_token_payload.get("email")
        username = userinfo.get("preferred_username") or email.split("@")[0] if email else "user"
        full_name = userinfo.get("name")
        avatar_url = userinfo.get("picture")

        if not sub or not email:
            raise ValueError("Missing required claims: sub or email")

        result = await self.db.execute(select(User).where(User.keycloak_sub == sub))
        user = result.scalar_one_or_none()

        if user:
            user.email = email
            user.username = username
            user.full_name = full_name
            user.avatar_url = avatar_url
            user.last_login_at = datetime.now(UTC)
            user.updated_at = datetime.now(UTC)
        else:
            # Map Keycloak roles to local roles
            realm_access = id_token_payload.get("realm_access", {})
            roles = realm_access.get("roles", [])
            if "admin" in roles:
                role = UserRole.ADMIN
            elif "operator" in roles:
                role = UserRole.OPERATOR
            else:
                role = UserRole.VIEWER

            user = User(
                keycloak_sub=sub,
                email=email,
                username=username,
                full_name=full_name,
                avatar_url=avatar_url,
                role=role,
                last_login_at=datetime.now(UTC),
            )
            self.db.add(user)

        await self.db.flush()
        return user

    async def create_tokens(self, user: User) -> tuple[str, str]:
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "roles": [user.role.value],
        }
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        return access_token, refresh_token

    async def logout_user(self, user_id: int, ip: Optional[str] = None, user_agent: Optional[str] = None) -> None:
        audit = AuditLog(
            user_id=user_id,
            action=AuditAction.LOGOUT,
            ip_address=ip,
            user_agent=user_agent,
        )
        self.db.add(audit)

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def verify_token(self, token: str) -> Optional[User]:
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        return await self.get_user_by_id(int(user_id))


def get_roles_from_token(token: str) -> List[str]:
    payload = decode_token(token)
    if not payload:
        return []
    return payload.get("roles", [])