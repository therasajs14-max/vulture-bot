"""Vulture Bot - Email Drafts, Approval, and Batch Dispatch API."""

from __future__ import annotations

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database.session import get_db
from app.database.models.email import (
    EmailDraft, EmailBatch, BatchRecipient, ApprovalRecord, AuditEvent
)
from app.database.models.user import User
from app.auth.dependencies import get_current_user, get_current_admin
from app.approvals.service import ApprovalService

router = APIRouter(prefix="/api/email", tags=["email"])


class CreateDraftRequest(BaseModel):
    task_name: str
    subject: str
    body_template: str
    dataset_id: Optional[str] = None
    conversation_id: Optional[str] = None
    is_personalized: bool = True
    selection_description: Optional[str] = None


class UpdateDraftRequest(BaseModel):
    subject: Optional[str] = None
    body_template: Optional[str] = None
    task_name: Optional[str] = None
    is_personalized: Optional[bool] = None


class ApproveDraftRequest(BaseModel):
    decision_reason: Optional[str] = "Approved by administrator."


class DispatchBatchRequest(BaseModel):
    idempotency_key: Optional[str] = None


@router.post("/drafts")
async def create_draft(
    payload: CreateDraftRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an email draft from AI output or user input."""
    draft = EmailDraft(
        user_id=user.id,
        conversation_id=payload.conversation_id,
        dataset_id=payload.dataset_id,
        task_name=payload.task_name.strip(),
        subject=payload.subject.strip(),
        body_template=payload.body_template.strip(),
        is_personalized=payload.is_personalized,
        selection_description=payload.selection_description,
        status="draft",
    )
    db.add(draft)
    await db.commit()
    await db.refresh(draft)

    # Prepare initial preview
    review_data = await ApprovalService.prepare_draft_for_review(db, draft.id)
    return {"success": True, "draft": review_data}


@router.get("/drafts/{draft_id}/review")
async def review_draft(
    draft_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full preview of the draft, recipients, and approval requirements."""
    try:
        review_data = await ApprovalService.prepare_draft_for_review(db, draft_id)
        # Check if an approval already exists
        app_stmt = select(ApprovalRecord).where(ApprovalRecord.draft_id == draft_id)
        approval = (await db.execute(app_stmt)).scalar_one_or_none()

        review_data["approval"] = {
            "status": approval.status if approval else "none",
            "approver_id": approval.approver_id if approval else None,
            "decided_at": approval.decided_at.isoformat() if approval and approval.decided_at else None,
            "reason": approval.decision_reason if approval else None,
        }
        return review_data
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/drafts/{draft_id}")
async def update_draft(
    draft_id: str,
    payload: UpdateDraftRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update draft subject or body. Automatically invalidates any existing approval."""
    draft = await db.get(EmailDraft, draft_id)
    if not draft or draft.user_id != user.id:
        raise HTTPException(status_code=404, detail="Draft not found.")

    if payload.subject is not None:
        draft.subject = payload.subject.strip()
    if payload.body_template is not None:
        draft.body_template = payload.body_template.strip()
    if payload.task_name is not None:
        draft.task_name = payload.task_name.strip()
    if payload.is_personalized is not None:
        draft.is_personalized = payload.is_personalized

    draft.version += 1
    # Invalidate previous approval if modified
    app_stmt = select(ApprovalRecord).where(ApprovalRecord.draft_id == draft_id)
    approval = (await db.execute(app_stmt)).scalar_one_or_none()
    if approval and approval.status == "approved":
        approval.status = "invalidated"
        approval.decision_reason = "Invalidated due to draft content modification."
        draft.status = "draft"

    await db.commit()
    # Recalculate review
    review_data = await ApprovalService.prepare_draft_for_review(db, draft.id)
    return {"success": True, "draft": review_data, "approval_invalidated": True}


@router.post("/drafts/{draft_id}/approve")
async def approve_draft(
    draft_id: str,
    payload: ApproveDraftRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Explicitly approve an email draft. Requires Administrator role."""
    try:
        approval = await ApprovalService.approve_draft(
            db=db,
            draft_id=draft_id,
            admin_user=admin,
            decision_reason=payload.decision_reason,
        )
        return {
            "success": True,
            "status": approval.status,
            "approved_by": admin.email,
            "content_hash": approval.approved_content_hash,
            "recipient_count": approval.approved_recipient_count,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/drafts/{draft_id}/dispatch")
async def dispatch_approved_batch(
    draft_id: str,
    payload: DispatchBatchRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Execute sending an approved batch with idempotency key."""
    try:
        batch = await ApprovalService.execute_batch(
            db=db,
            draft_id=draft_id,
            admin_user=admin,
            idempotency_key=payload.idempotency_key,
        )
        return {
            "success": True,
            "batch_id": batch.id,
            "status": batch.status,
            "total_recipients": batch.total_recipients,
            "sent_count": batch.sent_count,
            "failed_count": batch.failed_count,
            "email_provider": batch.email_provider,
        }
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/batches/{batch_id}/results")
async def get_batch_results(
    batch_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get per-recipient delivery statuses for an email batch."""
    batch = await db.get(EmailBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    stmt = select(BatchRecipient).where(BatchRecipient.batch_id == batch_id)
    recipients = (await db.execute(stmt)).scalars().all()

    return {
        "batch_id": batch.id,
        "status": batch.status,
        "started_at": batch.started_at.isoformat() if batch.started_at else None,
        "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
        "total_recipients": batch.total_recipients,
        "sent_count": batch.sent_count,
        "failed_count": batch.failed_count,
        "email_provider": batch.email_provider,
        "recipients": [
            {
                "id": r.id,
                "email": r.recipient_email,
                "name": r.recipient_name,
                "status": r.status,
                "error": r.error_message,
                "sent_at": r.sent_at.isoformat() if r.sent_at else None,
                "provider_message_id": r.provider_message_id,
            }
            for r in recipients
        ],
    }


@router.get("/audit")
async def get_audit_trail(
    limit: int = Query(50, le=200),
    user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve system audit logs for administrative security monitoring."""
    stmt = select(AuditEvent).order_by(desc(AuditEvent.created_at)).limit(limit)
    events = (await db.execute(stmt)).scalars().all()

    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "description": e.description,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]
