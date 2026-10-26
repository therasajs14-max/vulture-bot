"""Vulture Bot - Multi-Provider Email Service with Safe Personalization and Mock Mode."""

from __future__ import annotations

import asyncio
import base64
import html
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Any

from app.config import get_settings, EmailProvider


@dataclass
class EmailSendResult:
    success: bool
    provider_message_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = datetime.now(timezone.utc)


class BaseEmailProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        recipient_name: Optional[str] = None,
    ) -> EmailSendResult:
        pass


class MockEmailProvider(BaseEmailProvider):
    """Safe Mock Email Provider for local development and automated testing.

    Does not send real emails. Records all messages sent in an internal log
    for inspection and verification in the UI and test suites.
    """

    def __init__(self):
        self.sent_messages: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "mock"

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        recipient_name: Optional[str] = None,
    ) -> EmailSendResult:
        # Simulate slight network latency
        await asyncio.sleep(0.05)

        msg_id = f"mock-msg-{len(self.sent_messages) + 1}-{int(datetime.now(timezone.utc).timestamp())}"
        record = {
            "id": msg_id,
            "to_email": to_email,
            "recipient_name": recipient_name,
            "subject": subject,
            "body_text": body_text,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        self.sent_messages.append(record)

        return EmailSendResult(
            success=True,
            provider_message_id=msg_id,
        )


class SMTPEmailProvider(BaseEmailProvider):
    """Real SMTP email sender via aiosmtplib."""

    def __init__(self):
        self.settings = get_settings()

    @property
    def name(self) -> str:
        return "smtp"

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        recipient_name: Optional[str] = None,
    ) -> EmailSendResult:
        import aiosmtplib

        if not self.settings.smtp_host or not self.settings.smtp_username:
            return EmailSendResult(
                success=False,
                error="SMTP is not configured. Set SMTP_HOST and SMTP_USERNAME in environment.",
            )

        # Smart hostname auto-correction
        host = (self.settings.smtp_host or "").strip()
        lower_host = host.lower()
        if "@" in lower_host or lower_host.endswith(".gmail.com") or lower_host in ("gmail.com", "gmail"):
            host = "smtp.gmail.com"
        elif "outlook" in lower_host or "hotmail" in lower_host or lower_host.endswith(".office365.com"):
            host = "smtp.office365.com"
        elif "yahoo" in lower_host:
            host = "smtp.mail.yahoo.com"

        username = (self.settings.smtp_username or "").strip()
        if "gmail" in host and "@" not in username:
            return EmailSendResult(
                success=False,
                error=f"Invalid Gmail username '{username}'. Gmail requires your full email address as username (e.g. {username}@gmail.com).",
            )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = username
        msg["To"] = f"{recipient_name} <{to_email}>" if recipient_name else to_email

        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        # Smart TLS negotiation based on standard SMTP ports
        use_tls = False
        start_tls = False

        if self.settings.smtp_port == 465:
            use_tls = True
            start_tls = False
        elif self.settings.smtp_port == 587:
            use_tls = False
            start_tls = True
        else:
            start_tls = bool(self.settings.smtp_use_tls)

        try:
            await aiosmtplib.send(
                msg,
                hostname=host,
                port=self.settings.smtp_port,
                username=username,
                password=self.settings.smtp_password,
                use_tls=use_tls,
                start_tls=start_tls,
                timeout=20.0,
            )
            return EmailSendResult(
                success=True,
                provider_message_id=f"smtp-{int(datetime.now(timezone.utc).timestamp())}",
            )
        except Exception as e:
            err_str = str(e)
            if "getaddrinfo failed" in err_str or "11001" in err_str:
                err_str = f"Cannot resolve mail server '{host}'. For Gmail, the SMTP Host must be exactly 'smtp.gmail.com'."
            elif "Authentication" in err_str or "535" in err_str or "Username and Password not accepted" in err_str:
                if "gmail" in host:
                    err_str += " (Note: Gmail requires a 16-character 'App Password', not your standard account password. Visit myaccount.google.com/apppasswords to generate one)."
            return EmailSendResult(
                success=False,
                error=f"SMTP send failed: {err_str}",
            )


class PersonalizationEngine:
    """Safe template renderer for student emails.

    Supports standard placeholders ({name}, {first_name}, {task}, {department},
    {year}, {section}, {register_number}, {email}) and any custom columns
    from the uploaded Excel / CSV sheet.
    Prevents prompt injection or code evaluation.
    """

    TASK_ALIASES = ["task", "assignment", "work", "topic", "project", "activity", "homework", "deliverable"]

    @classmethod
    def render(cls, template: str, student_data: dict[str, Any]) -> str:
        # Build normalized lowercase map of keys
        normalized: dict[str, Any] = {}
        for k, v in student_data.items():
            if k is not None:
                clean_k = re.sub(r"[^a-zA-Z0-9_]", "_", str(k).lower().strip())
                normalized[clean_k] = v
                normalized[str(k).lower().strip()] = v

        # If task placeholder is used but not found directly, search aliases
        if "task" not in normalized or not str(normalized.get("task", "")).strip():
            for alias in cls.TASK_ALIASES:
                if alias in normalized and str(normalized.get(alias, "")).strip():
                    normalized["task"] = normalized[alias]
                    break

        def replace_var(match):
            var_name = match.group(1).lower().strip()
            clean_var = re.sub(r"[^a-zA-Z0-9_]", "_", var_name)

            if var_name == "first_name":
                full_name = str(normalized.get("name", "")).strip()
                return full_name.split()[0] if full_name else "Student"

            val = normalized.get(clean_var, normalized.get(var_name, ""))
            if val is None or str(val).strip() == "" or str(val).lower() == "nan":
                # Graceful fallbacks
                if var_name in ("name", "student_name"):
                    return "Student"
                if var_name in ("task", "assignment"):
                    return "Assigned Project Deliverable"
                return ""
            return str(val).strip()

        # Match {variable}
        rendered = re.sub(r"\{([a-zA-Z0-9_]+)\}", replace_var, template)
        return rendered


def get_email_provider() -> BaseEmailProvider:
    settings = get_settings()
    if settings.email_provider == EmailProvider.SMTP:
        return SMTPEmailProvider()
    return MockEmailProvider()
