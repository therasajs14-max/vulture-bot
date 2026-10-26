"""Vulture Bot - Authentication API Endpoints."""

from __future__ import annotations

import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.database.session import get_db
from app.database.models.user import User, OAuthAccount
from app.database.models.email import AuditEvent
from app.auth.dependencies import get_current_user, get_current_user_optional
from app.security.auth import (
    create_session_token,
    decode_session_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserProfileResponse(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    is_admin: bool
    is_superadmin: bool
    theme: str
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None


class DemoLoginRequest(BaseModel):
    email: str = "admin@vulture.local"
    name: str = "Administrator"
    is_admin: bool = True


@router.get("/me", response_model=UserProfileResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Return the profile and permissions of the currently authenticated user."""
    settings = get_settings()
    is_admin = user.is_admin or user.is_superadmin or (user.email.lower() in settings.admin_emails_list)
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        is_admin=is_admin,
        is_superadmin=user.is_superadmin,
        theme=user.theme,
        ai_provider=user.ai_provider or settings.ai_provider,
        ai_model=user.ai_model or settings.ollama_model,
    )


@router.post("/demo-login")
async def demo_login(
    payload: DemoLoginRequest,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Zero-setup sign in for local development.

    Creates the user if not existing and sets a signed HttpOnly session cookie.
    Allows easy switching between Admin and standard Student/User roles.
    """
    settings = get_settings()
    stmt = select(User).where(User.email == payload.email.lower().strip())
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user:
        is_admin = payload.is_admin or (payload.email.lower() in settings.admin_emails_list)
        user = User(
            email=payload.email.lower().strip(),
            name=payload.name,
            is_admin=is_admin,
            is_superadmin=is_admin,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_session_token({"sub": user.id, "email": user.email})

    # Set secure HttpOnly session cookie
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_max_age,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
    )

    db.add(AuditEvent(
        user_id=user.id,
        event_type="auth.login",
        resource_type="user",
        resource_id=user.id,
        description=f"User {user.email} signed in via local session.",
        ip_address=request.client.host if request.client else None,
    ))
    await db.commit()

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_admin": user.is_admin,
        }
    }


@router.get("/google/url")
async def get_google_auth_url():
    """Generate Google OAuth 2.0 authorization URL."""
    settings = get_settings()
    if not settings.google_client_id:
        return {
            "configured": False,
            "message": "Google Client ID is not configured. Please add GOOGLE_CLIENT_ID to .env. Use Demo Sign In for instant local access."
        }

    state = secrets.token_urlsafe(16)
    scope = "openid%20profile%20email"
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.google_client_id}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&redirect_uri={settings.google_redirect_uri}"
        f"&state={state}"
        f"&access_type=offline"
        f"&prompt=select_account"
    )
    return {
        "configured": True,
        "url": auth_url,
        "state": state
    }


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Clear session cookie and invalidate session."""
    settings = get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        samesite="lax",
    )
    if user:
        db.add(AuditEvent(
            user_id=user.id,
            event_type="auth.logout",
            resource_type="user",
            resource_id=user.id,
            description=f"User {user.email} signed out.",
        ))
        await db.commit()

    return {"success": True, "message": "Successfully logged out."}
