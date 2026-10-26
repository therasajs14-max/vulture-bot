"""Vulture Bot - Conversations and Messages API."""

from __future__ import annotations

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.database.session import get_db
from app.database.models.conversation import Conversation, Message
from app.database.models.user import User
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"
    model_provider: Optional[str] = None
    model_name: Optional[str] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    is_archived: Optional[bool] = None
    is_pinned: Optional[bool] = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    created_at: str


class ConversationSummary(BaseModel):
    id: str
    title: str
    is_archived: bool
    is_pinned: bool
    updated_at: str
    last_message: Optional[str] = None


@router.get("", response_model=List[ConversationSummary])
async def list_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    include_archived: bool = False,
):
    """List all conversations belonging to the current user."""
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user.id)
    )
    if not include_archived:
        stmt = stmt.where(Conversation.is_archived == False)

    stmt = stmt.order_by(Conversation.updated_at.desc())
    res = await db.execute(stmt)
    convs = res.scalars().all()

    summaries = []
    for c in convs:
        # Fetch last message
        last_msg_stmt = (
            select(Message.content)
            .where(Message.conversation_id == c.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_msg = (await db.execute(last_msg_stmt)).scalar_one_or_none()

        summaries.append(
            ConversationSummary(
                id=c.id,
                title=c.title,
                is_archived=c.is_archived,
                is_pinned=c.is_pinned,
                updated_at=c.updated_at.isoformat() if c.updated_at else "",
                last_message=(last_msg[:60] + "...") if last_msg else None,
            )
        )
    return summaries


@router.post("", response_model=ConversationSummary)
async def create_conversation(
    payload: ConversationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat conversation."""
    conv = Conversation(
        user_id=user.id,
        title=payload.title or "New Conversation",
        model_provider=payload.model_provider,
        model_name=payload.model_name,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)

    return ConversationSummary(
        id=conv.id,
        title=conv.title,
        is_archived=conv.is_archived,
        is_pinned=conv.is_pinned,
        updated_at=conv.updated_at.isoformat() if conv.updated_at else "",
        last_message=None,
    )


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get conversation details with all historical messages."""
    stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id,
    )
    conv = (await db.execute(stmt)).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    msg_stmt = (
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
    )
    messages = (await db.execute(msg_stmt)).scalars().all()

    return {
        "id": conv.id,
        "title": conv.title,
        "is_archived": conv.is_archived,
        "is_pinned": conv.is_pinned,
        "created_at": conv.created_at.isoformat() if conv.created_at else "",
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else "",
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "is_error": m.is_error,
                "created_at": m.created_at.isoformat() if m.created_at else "",
            }
            for m in messages
        ],
    }


@router.patch("/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update title or archive status of conversation."""
    stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id,
    )
    conv = (await db.execute(stmt)).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    if payload.title is not None:
        conv.title = payload.title.strip()
    if payload.is_archived is not None:
        conv.is_archived = payload.is_archived
    if payload.is_pinned is not None:
        conv.is_pinned = payload.is_pinned

    await db.commit()
    return {"success": True, "id": conv.id, "title": conv.title}


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and its messages."""
    stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id,
    )
    conv = (await db.execute(stmt)).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    await db.delete(conv)
    await db.commit()
    return {"success": True, "message": "Conversation deleted."}
