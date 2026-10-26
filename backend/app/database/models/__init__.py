"""Vulture Bot - Database models package."""

from app.database.models.user import User, OAuthAccount
from app.database.models.conversation import Conversation, Message
from app.database.models.file import UploadedFile, Dataset, DatasetColumn, DatasetRecord
from app.database.models.email import (
    EmailDraft,
    EmailBatch,
    BatchRecipient,
    ApprovalRecord,
    AuditEvent,
)

__all__ = [
    "User",
    "OAuthAccount",
    "Conversation",
    "Message",
    "UploadedFile",
    "Dataset",
    "DatasetColumn",
    "DatasetRecord",
    "EmailDraft",
    "EmailBatch",
    "BatchRecipient",
    "ApprovalRecord",
    "AuditEvent",
]
