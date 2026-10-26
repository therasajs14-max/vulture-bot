"""Vulture Bot - Streaming Chat API with Server-Sent Events (SSE)."""

from __future__ import annotations

import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.database.models.conversation import Conversation, Message
from app.database.models.user import User
from app.auth.dependencies import get_current_user
from app.ai.service import AIService

router = APIRouter(prefix="/api/chat", tags=["chat"])
ai_service = AIService()


class ChatStreamRequest(BaseModel):
    conversation_id: str
    message: str
    model_provider: Optional[str] = None
    model_name: Optional[str] = None


@router.post("/stream")
async def stream_chat(
    payload: ChatStreamRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream AI response tokens via Server-Sent Events (SSE)."""
    # 1. Verify user owns the conversation
    stmt = select(Conversation).where(
        Conversation.id == payload.conversation_id,
        Conversation.user_id == user.id,
    )
    conv = (await db.execute(stmt)).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    # 2. Record user message
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=payload.message.strip(),
    )
    db.add(user_msg)

    # 3. Auto-update title if it's the initial message
    if conv.title == "New Conversation" and payload.message:
        words = payload.message.strip().split()
        short_title = " ".join(words[:6])
        if len(short_title) > 40:
            short_title = short_title[:40] + "..."
        conv.title = short_title

    await db.commit()

    # 4. Stream generator
    async def event_generator():
        full_content = []
        try:
            async for chunk in ai_service.stream_response(
                conversation_id=conv.id,
                user_message=payload.message,
                db=db,
                model=payload.model_name,
                provider_name=payload.model_provider,
            ):
                if chunk.error:
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": chunk.error})
                    }
                    full_content.append(f"\n\n[Error: {chunk.error}]")
                    break

                if chunk.content:
                    full_content.append(chunk.content)
                    yield {
                        "event": "message",
                        "data": json.dumps({"content": chunk.content})
                    }

                if chunk.is_done:
                    yield {
                        "event": "done",
                        "data": json.dumps({"done": True})
                    }
                    break

            # Persist assistant message
            assistant_content = "".join(full_content)
            assistant_msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content=assistant_content or "No response generated.",
            )
            db.add(assistant_msg)
            await db.commit()

        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }

    return EventSourceResponse(event_generator())
