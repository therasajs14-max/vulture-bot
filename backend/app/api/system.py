"""Vulture Bot - System Diagnostics and Provider Status API."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import get_settings, EmailProvider
from app.database.session import get_db
from app.ai.service import AIService
from app.email.service import SMTPEmailProvider, MockEmailProvider, get_email_provider
from app.auth.dependencies import get_current_user
from app.database.models.user import User

router = APIRouter(prefix="/api/system", tags=["system"])
ai_service = AIService()


class ConfigureEmailRequest(BaseModel):
    provider: str  # "smtp" | "mock"
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True


class SendTestEmailRequest(BaseModel):
    to_email: str
    subject: Optional[str] = "Vulture Bot — Real Email Delivery Test"
    message: Optional[str] = "Hello! This is a real test email sent by Vulture Bot confirming live SMTP delivery."


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """System health check verifying database and application status."""
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    settings = get_settings()
    return {
        "status": "healthy" if db_ok else "degraded",
        "app_name": settings.app_name,
        "environment": settings.app_env,
        "database_connected": db_ok,
    }


@router.get("/ai-status")
async def get_ai_status():
    """Check connectivity and available models for Ollama and Gemini."""
    return await ai_service.get_status()


@router.get("/email-config")
async def get_email_config():
    """Get active email sending configuration (without password)."""
    settings = get_settings()
    return {
        "provider": settings.email_provider.value if hasattr(settings.email_provider, "value") else str(settings.email_provider),
        "smtp_host": settings.smtp_host,
        "smtp_port": settings.smtp_port,
        "smtp_username": settings.smtp_username,
        "smtp_use_tls": settings.smtp_use_tls,
        "is_configured": bool(settings.smtp_host and settings.smtp_username),
    }


@router.post("/configure-email")
async def configure_email(
    payload: ConfigureEmailRequest,
    user: User = Depends(get_current_user),
):
    """Update email provider settings dynamically."""
    settings = get_settings()
    clean_host = (payload.smtp_host or "").strip()
    if clean_host:
        lower_host = clean_host.lower()
        if "@" in lower_host or lower_host.endswith(".gmail.com") or lower_host in ("gmail.com", "gmail"):
            clean_host = "smtp.gmail.com"
        elif "outlook" in lower_host or "hotmail" in lower_host or lower_host.endswith(".office365.com"):
            clean_host = "smtp.office365.com"
        elif "yahoo" in lower_host:
            clean_host = "smtp.mail.yahoo.com"

    clean_username = (payload.smtp_username or "").strip()

    if payload.provider == "smtp":
        settings.email_provider = EmailProvider.SMTP
        settings.smtp_host = clean_host
        settings.smtp_port = payload.smtp_port
        settings.smtp_username = clean_username
        if payload.smtp_password:
            settings.smtp_password = payload.smtp_password
        settings.smtp_use_tls = payload.smtp_use_tls
    else:
        settings.email_provider = EmailProvider.MOCK

    # Persist to .env file
    try:
        from pathlib import Path
        env_path = Path(".env")
        if env_path.exists():
            env_content = env_path.read_text(encoding="utf-8")
            updates = {
                "EMAIL_PROVIDER": payload.provider,
                "SMTP_HOST": clean_host or "",
                "SMTP_PORT": str(payload.smtp_port),
                "SMTP_USERNAME": clean_username or "",
                "SMTP_USE_TLS": "true" if payload.smtp_use_tls else "false",
            }
            if payload.smtp_password:
                updates["SMTP_PASSWORD"] = payload.smtp_password

            for key, val in updates.items():
                if f"{key}=" in env_content:
                    import re
                    env_content = re.sub(rf"^{key}=.*$", f"{key}={val}", env_content, flags=re.MULTILINE)
                else:
                    env_content += f"\n{key}={val}"
            env_path.write_text(env_content, encoding="utf-8")
    except Exception as e:
        print(f"Warning: could not persist to .env: {e}")

    return {
        "success": True,
        "provider": settings.email_provider.value,
        "smtp_host": settings.smtp_host,
        "smtp_username": settings.smtp_username,
    }


@router.post("/test-email")
async def send_test_email(
    payload: SendTestEmailRequest,
    user: User = Depends(get_current_user),
):
    """Send a real verification email to verify actual delivery."""
    settings = get_settings()
    provider = get_email_provider()

    result = await provider.send_email(
        to_email=payload.to_email,
        subject=payload.subject or "Vulture Bot Delivery Test",
        body_text=payload.message or "Verification test from Vulture Bot.",
        recipient_name=user.name,
    )

    if not result.success:
        raise HTTPException(
            status_code=400,
            detail=f"Email dispatch failed: {result.error}",
        )

    return {
        "success": True,
        "provider": provider.name,
        "message_id": result.provider_message_id,
        "sent_to": payload.to_email,
        "delivery_note": (
            "Email dispatched via real SMTP server!"
            if provider.name == "smtp"
            else "Email saved in mock log (switch provider to SMTP in Settings to send to real inboxes)."
        ),
    }
