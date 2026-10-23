from datetime import datetime, UTC
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Cookie
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.auth import KeycloakAuth, AuthService
from app.core.security import generate_state, generate_pkce_pair, create_access_token, create_refresh_token, generate_csrf_token, hash_csrf_token
from app.api.deps import get_db, get_optional_user
from app.schemas.auth import (
    AuthURLResponse,
    CallbackRequest,
    Token,
    LogoutResponse,
    MessageResponse,
    UserResponse,
)
from app.models import User, UserRole, AuditLog, AuditAction

router = APIRouter(prefix="/auth", tags=["auth"])

keycloak_auth = KeycloakAuth()


@router.get("/login", response_model=AuthURLResponse)
async def login(request: Request) -> AuthURLResponse:
    state = generate_state()
    code_verifier, code_challenge = generate_pkce_pair()

    auth_url = keycloak_auth.build_auth_url(state, code_challenge)

    response = AuthURLResponse(
        auth_url=auth_url,
        state=state,
        code_verifier=code_verifier,
    )

    return response


@router.post("/callback", response_model=Token)
async def callback(
    request: Request,
    response: Response,
    callback_data: CallbackRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    if not callback_data.code or not callback_data.state or not callback_data.code_verifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required parameters",
        )

    tokens = await keycloak_auth.exchange_code_for_tokens(
        callback_data.code, callback_data.code_verifier
    )
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange code for tokens",
        )

    access_token_kc = tokens.get("access_token")
    id_token = tokens.get("id_token")
    refresh_token_kc = tokens.get("refresh_token")

    userinfo = await keycloak_auth.get_userinfo(access_token_kc)
    if not userinfo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to fetch user info",
        )

    id_token_payload = keycloak_auth.verify_id_token(id_token) if id_token else {}

    auth_service = AuthService(db)
    user = await auth_service.get_or_create_user(userinfo, id_token_payload)

    local_access, local_refresh = await auth_service.create_tokens(user)

    response.set_cookie(
        key="access_token",
        value=local_access,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=local_refresh,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )

    csrf_token = generate_csrf_token()
    response.set_cookie(
        key="csrf_token",
        value=hash_csrf_token(csrf_token),
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    return Token(
        access_token=local_access,
        refresh_token=local_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(None, alias="refresh_token"),
    db: AsyncSession = Depends(get_db),
) -> Token:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    payload = None
    try:
        from jose import jwt
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(int(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    local_access, local_refresh = await auth_service.create_tokens(user)

    response.set_cookie(
        key="access_token",
        value=local_access,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=local_refresh,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )

    csrf_token = generate_csrf_token()
    response.set_cookie(
        key="csrf_token",
        value=hash_csrf_token(csrf_token),
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    return Token(
        access_token=local_access,
        refresh_token=local_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> LogoutResponse:
    if current_user:
        auth_service = AuthService(db)
        await auth_service.logout_user(current_user.id)

    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    response.delete_cookie("csrf_token", path="/")

    logout_url = None
    if settings.KEYCLOAK_CLIENT_SECRET:
        logout_url = f"{keycloak_auth.logout_url}?client_id={settings.KEYCLOAK_CLIENT_ID}&post_logout_redirect_uri={settings.ALLOWED_ORIGINS[0]}"

    return LogoutResponse(message="Logged out successfully", logout_url=logout_url)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_optional_user)) -> User:
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return current_user