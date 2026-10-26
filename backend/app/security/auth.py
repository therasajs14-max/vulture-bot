"""Vulture Bot - Security and Cryptographic Utilities."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import html

from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.app_secret_key, salt="vulture-session-salt")


def hash_password(password: str) -> str:
    """Hash a password securely."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_session_token(data: dict[str, Any]) -> str:
    """Create a signed, tamper-proof session token."""
    serializer = get_serializer()
    return serializer.dumps(data)


def decode_session_token(token: str, max_age: Optional[int] = None) -> Optional[dict[str, Any]]:
    """Decode and verify a session token."""
    settings = get_settings()
    serializer = get_serializer()
    age = max_age or settings.session_max_age
    try:
        data = serializer.loads(token, max_age=age)
        return data
    except (BadSignature, SignatureExpired):
        return None


def compute_content_hash(*parts: str) -> str:
    """Compute a SHA-256 hash across content pieces for approval integrity."""
    hasher = hashlib.sha256()
    for part in parts:
        hasher.update((part or "").encode("utf-8"))
        hasher.update(b"|||")
    return hasher.hexdigest()


def generate_idempotency_key() -> str:
    """Generate a high-entropy idempotency key."""
    return secrets.token_hex(24)


def sanitize_text(text: str) -> str:
    """Basic text sanitization against XSS while preserving legitimate characters."""
    if not text:
        return ""
    return html.escape(text.strip())


def sanitize_filename(filename: str) -> str:
    """Ensure safe filesystem filenames without path traversal."""
    import re
    # Remove directory separators and null bytes
    clean = re.sub(r"[\\/*?:\'\"<>|\x00-\x1f]", "_", filename)
    clean = clean.replace("..", "_")
    return clean[:128] or "unnamed_file"


def escape_spreadsheet_formula(value: Any) -> Any:
    """Prevent CSV/Excel Formula Injection (DDE attacks)."""
    if isinstance(value, str):
        if value.startswith(("=", "+", "-", "@", "\t", "\r")):
            return "'" + value
    return value
