"""Vulture Bot - Email, Approval, and Audit database models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text, func, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class EmailDraft(Base):
    """Email draft model."""

    __tablename__ = "email_drafts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    dataset_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Draft content
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_personalized: Mapped[bool] = mapped_column(Boolean, default=False)
    personalization_fields: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    # Selection criteria
    selection_query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: filters used
    selection_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="draft"
    )  # draft, pending_approval, approved, sending, sent, cancelled
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Content hash for approval invalidation
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    batch: Mapped[Optional["EmailBatch"]] = relationship(
        back_populates="draft", cascade="all, delete-orphan"
    )
    approval: Mapped[Optional["ApprovalRecord"]] = relationship(
        back_populates="draft", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<EmailDraft '{self.task_name}' ({self.status})>"


class EmailBatch(Base):
    """Email batch for bulk sending."""

    __tablename__ = "email_batches"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    draft_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("email_drafts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Batch metadata
    total_recipients: Mapped[int] = mapped_column(Integer, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    pending_count: Mapped[int] = mapped_column(Integer, default=0)

    # Idempotency
    idempotency_key: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, processing, completed, partially_failed, failed, cancelled

    # Sending account
    sending_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    draft: Mapped["EmailDraft"] = relationship(back_populates="batch")
    recipients: Mapped[list["BatchRecipient"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<EmailBatch {self.id[:8]}... ({self.status})>"


class BatchRecipient(Base):
    """Individual recipient in an email batch."""

    __tablename__ = "batch_recipients"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    batch_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("email_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    record_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("dataset_records.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Recipient info
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    personalized_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Delivery status
    status: Mapped[str] = mapped_column(
        String(20), default="queued"
    )  # queued, sending, sent, accepted, failed, skipped
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Idempotency
    send_attempt_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)

    # Timestamps
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    batch: Mapped["EmailBatch"] = relationship(back_populates="recipients")

    __table_args__ = (
        Index("ix_recipients_batch_status", "batch_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<BatchRecipient {self.recipient_email} ({self.status})>"


class ApprovalRecord(Base):
    """Admin approval record for email batches."""

    __tablename__ = "approval_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    draft_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("email_drafts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    approver_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Approval details
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, approved, rejected, invalidated
    decision_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Snapshot of what was approved
    approved_content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    approved_recipient_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    approved_subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    decided_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    draft: Mapped["EmailDraft"] = relationship(back_populates="approval")

    def __repr__(self) -> str:
        return f"<ApprovalRecord {self.status} by {self.approver_id[:8]}>"


class AuditEvent(Base):
    """Audit trail for security-sensitive operations."""

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # auth.login, auth.logout, email.approved, email.sent, file.uploaded, etc.

    # Event details
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON, no sensitive data

    # Request context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    def __repr__(self) -> str:
        return f"<AuditEvent {self.event_type} at {self.created_at}>"
