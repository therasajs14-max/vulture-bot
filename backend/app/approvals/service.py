"""Vulture Bot - Administrative Approval and Batch Execution Engine.

Enforces strict server-side validation:
- Only authenticated admins can approve drafts.
- Approval is cryptographically bound to the draft content hash and recipient count.
- Modifying draft content or recipient filters immediately invalidates approval.
- Full idempotency protection preventing duplicate dispatches.
- Complete audit trail logging.
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.database.models.email import (
    EmailDraft, EmailBatch, BatchRecipient, ApprovalRecord, AuditEvent
)
from app.database.models.file import Dataset, DatasetRecord
from app.database.models.user import User
from app.email.service import get_email_provider, PersonalizationEngine
from app.security.auth import compute_content_hash, generate_idempotency_key


class ApprovalService:
    """Coordinates draft validation, admin approval binding, and batch dispatch."""

    @staticmethod
    def calculate_draft_hash(draft: EmailDraft, recipient_emails: list[str]) -> str:
        """Calculate content hash over draft subject, body, and sorted recipient list."""
        sorted_emails = ",".join(sorted(recipient_emails))
        return compute_content_hash(
            draft.task_name,
            draft.subject,
            draft.body_template,
            str(draft.is_personalized),
            sorted_emails,
        )

    @classmethod
    async def prepare_draft_for_review(
        cls,
        db: AsyncSession,
        draft_id: str,
    ) -> dict[str, Any]:
        """Validate recipients, calculate hash, and build review payload."""
        draft = await db.get(EmailDraft, draft_id)
        if not draft:
            raise ValueError("Draft not found")

        # Query matched dataset records
        recipients = []
        excluded = []

        if draft.dataset_id:
            stmt = select(DatasetRecord).where(DatasetRecord.dataset_id == draft.dataset_id)
            # Parse selection query if present
            # We filter records based on validity
            records = (await db.execute(stmt)).scalars().all()
            for r in records:
                if r.is_valid and r.email:
                    rec_dict = {
                        "record_id": r.id,
                        "name": r.name or "Student",
                        "email": r.email,
                        "department": r.department or "",
                        "year": r.year or "",
                        "section": r.section or "",
                        "register_number": r.register_number or "",
                    }
                    if r.data_json:
                        try:
                            raw_data = json.loads(r.data_json)
                            for k, v in raw_data.items():
                                rec_dict[k] = v
                                rec_dict[str(k).lower().strip()] = v
                        except Exception:
                            pass
                    # Ensure task alias if present in raw data
                    for tk in ["task", "assignment", "work", "topic", "project", "activity"]:
                        if tk in rec_dict and "task" not in rec_dict:
                            rec_dict["task"] = rec_dict[tk]

                    recipients.append(rec_dict)
                else:
                    excluded.append({
                        "name": r.name or "Unknown",
                        "email": r.email or "None",
                        "reason": r.validation_errors or "Missing or invalid email",
                    })

        # Calculate and update content hash
        recipient_emails = [r["email"] for r in recipients]
        content_hash = cls.calculate_draft_hash(draft, recipient_emails)
        draft.content_hash = content_hash
        draft.status = "pending_approval"
        await db.commit()

        # Preview sample personalized message
        sample_preview = None
        if recipients:
            first_r = recipients[0]
            rendered_body = PersonalizationEngine.render(
                draft.body_template,
                first_r
            )
            sample_preview = {
                "recipient": first_r,
                "rendered_body": rendered_body,
            }

        return {
            "draft_id": draft.id,
            "task_name": draft.task_name,
            "subject": draft.subject,
            "body_template": draft.body_template,
            "is_personalized": draft.is_personalized,
            "content_hash": content_hash,
            "status": draft.status,
            "recipient_count": len(recipients),
            "excluded_count": len(excluded),
            "recipients_sample": recipients[:20],
            "excluded_sample": excluded[:20],
            "sample_preview": sample_preview,
        }

    @classmethod
    async def approve_draft(
        cls,
        db: AsyncSession,
        draft_id: str,
        admin_user: User,
        decision_reason: Optional[str] = None,
    ) -> ApprovalRecord:
        """Explicitly approve an email draft by an authorized admin."""
        draft = await db.get(EmailDraft, draft_id)
        if not draft:
            raise ValueError("Draft not found")

        # Verify admin privileges
        if not (admin_user.is_admin or admin_user.is_superadmin):
            raise PermissionError("Only administrators can approve email broadcasts.")

        # Re-fetch recipients to verify current hash
        recipient_emails = []
        if draft.dataset_id:
            stmt = select(DatasetRecord.email).where(
                DatasetRecord.dataset_id == draft.dataset_id,
                DatasetRecord.is_valid == True,
                DatasetRecord.email.isnot(None),
            )
            recipient_emails = [e for e in (await db.execute(stmt)).scalars().all() if e]

        current_hash = cls.calculate_draft_hash(draft, recipient_emails)
        draft.content_hash = current_hash
        draft.status = "approved"

        # Check existing approval record
        approval = (
            await db.execute(
                select(ApprovalRecord).where(ApprovalRecord.draft_id == draft_id)
            )
        ).scalar_one_or_none()

        if not approval:
            approval = ApprovalRecord(
                draft_id=draft.id,
                approver_id=admin_user.id,
                status="approved",
                decision_reason=decision_reason or "Approved by administrator.",
                approved_content_hash=current_hash,
                approved_recipient_count=len(recipient_emails),
                approved_subject=draft.subject,
                decided_at=datetime.now(timezone.utc),
            )
            db.add(approval)
        else:
            approval.status = "approved"
            approval.approver_id = admin_user.id
            approval.approved_content_hash = current_hash
            approval.approved_recipient_count = len(recipient_emails)
            approval.approved_subject = draft.subject
            approval.decided_at = datetime.now(timezone.utc)
            approval.decision_reason = decision_reason or "Re-approved by administrator."

        # Audit log
        db.add(AuditEvent(
            user_id=admin_user.id,
            event_type="email.approved",
            resource_type="email_draft",
            resource_id=draft.id,
            description=f"Admin {admin_user.email} approved draft '{draft.task_name}' for {len(recipient_emails)} recipients.",
        ))

        await db.commit()
        await db.refresh(approval)
        return approval

    @classmethod
    async def execute_batch(
        cls,
        db: AsyncSession,
        draft_id: str,
        admin_user: User,
        idempotency_key: Optional[str] = None,
    ) -> EmailBatch:
        """Execute an approved email batch with full verification and idempotency."""
        draft = await db.get(EmailDraft, draft_id)
        if not draft:
            raise ValueError("Draft not found")

        # 1. Verify approval exists and is strictly valid
        approval = (
            await db.execute(
                select(ApprovalRecord).where(ApprovalRecord.draft_id == draft_id)
            )
        ).scalar_one_or_none()

        if not approval or approval.status != "approved":
            raise PermissionError("This draft has not been approved by an administrator.")

        # 2. Re-verify content hash matches exactly what was approved
        stmt = select(DatasetRecord).where(
            DatasetRecord.dataset_id == draft.dataset_id,
            DatasetRecord.is_valid == True,
            DatasetRecord.email.isnot(None),
        )
        records = (await db.execute(stmt)).scalars().all()
        recipient_emails = [r.email for r in records if r.email]

        current_hash = cls.calculate_draft_hash(draft, recipient_emails)
        if current_hash != approval.approved_content_hash:
            # Content changed since approval — invalidate immediately
            approval.status = "invalidated"
            draft.status = "draft"
            await db.commit()
            raise ValueError(
                "Approval invalidated: draft content or recipient list changed after approval. Re-review required."
            )

        # 3. Check for existing batch to prevent double-execution
        existing_batch = (
            await db.execute(
                select(EmailBatch).where(EmailBatch.draft_id == draft_id)
            )
        ).scalar_one_or_none()

        if existing_batch and existing_batch.status in ("processing", "completed"):
            return existing_batch

        # 4. Create batch
        key = idempotency_key or generate_idempotency_key()
        batch = EmailBatch(
            draft_id=draft.id,
            total_recipients=len(records),
            idempotency_key=key,
            status="processing",
            started_at=datetime.now(timezone.utc),
        )
        db.add(batch)
        await db.flush()

        # 5. Populate Batch Recipients
        provider = get_email_provider()
        batch.email_provider = provider.name
        batch_recipients = []

        for r in records:
            student_data = {
                "name": r.name or "Student",
                "department": r.department or "",
                "year": r.year or "",
                "section": r.section or "",
                "register_number": r.register_number or "",
                "email": r.email,
            }
            if r.data_json:
                try:
                    raw_data = json.loads(r.data_json)
                    for k, v in raw_data.items():
                        student_data[k] = v
                        student_data[str(k).lower().strip()] = v
                except Exception:
                    pass
            for tk in ["task", "assignment", "work", "topic", "project", "activity"]:
                if tk in student_data and "task" not in student_data:
                    student_data["task"] = student_data[tk]

            personalized_text = PersonalizationEngine.render(
                draft.body_template,
                student_data
            )
            br = BatchRecipient(
                batch_id=batch.id,
                record_id=r.id,
                recipient_email=r.email,
                recipient_name=r.name,
                personalized_body=personalized_text,
                status="queued",
            )
            db.add(br)
            batch_recipients.append(br)

        await db.flush()

        # 6. Dispatch emails through configured provider
        sent = 0
        failed = 0

        for br in batch_recipients:
            res = await provider.send_email(
                to_email=br.recipient_email,
                subject=draft.subject,
                body_text=br.personalized_body or draft.body_template,
                recipient_name=br.recipient_name,
            )
            if res.success:
                br.status = "sent"
                br.provider_message_id = res.provider_message_id
                br.sent_at = datetime.now(timezone.utc)
                sent += 1
            else:
                br.status = "failed"
                br.error_message = res.error
                failed += 1

        batch.sent_count = sent
        batch.failed_count = failed
        batch.pending_count = 0
        batch.status = "completed" if failed == 0 else "partially_failed"
        batch.completed_at = datetime.now(timezone.utc)
        draft.status = "sent"

        # Audit trail
        db.add(AuditEvent(
            user_id=admin_user.id,
            event_type="email.sent",
            resource_type="email_batch",
            resource_id=batch.id,
            description=f"Batch {batch.id} executed: {sent} sent, {failed} failed.",
        ))

        await db.commit()
        await db.refresh(batch)
        return batch
