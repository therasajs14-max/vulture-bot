"""Vulture Bot - High-Level AI Orchestration Service."""

from __future__ import annotations

import json
from typing import AsyncGenerator, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.ai.base import BaseAIProvider, ChatMessage, StreamChunk, Role
from app.ai.gemini_provider import GeminiProvider
from app.ai.ollama_provider import OllamaProvider
from app.ai.tools import get_available_tools
from app.config import get_settings, AIProvider
from app.database.models.conversation import Conversation, Message
from app.database.models.file import Dataset, DatasetRecord


SYSTEM_PROMPT = """You are Vulture Bot, a professional, production-ready AI Assistant with advanced document intelligence, data analytics, and administrative email drafting capabilities.

CORE GUIDELINES:
1. Tone: Professional, clear, concise, and helpful.
2. Accuracy: Never hallucinate or invent dates, deadlines, room numbers, requirements, or student data. Use only information provided by the user or extracted from uploaded datasets. If details are missing, explicitly ask the user for them.
3. Student Email Workflow:
   - When asked to prepare emails or announcements, summarize the target group (department, year, valid recipients).
   - Propose an accurate, professional Subject line and Body.
   - Use safe placeholders like {name}, {task}, {department}, {register_number} for personalization.
   - When an uploaded file contains individual tasks, topics, or assignments per student, always include the `{task}` placeholder in the email body (for example: "Your assigned task: {task}"). Each student will receive their own specific task!
   - Clarify to the user that emails are created as DRAFTS and require explicit Administrator Approval via the Review Panel before any message can be dispatched.
4. General Chat: You are a multi-purpose assistant. You can answer general questions, assist with coding, analyze text, write essays, summarize documents, and perform calculations.
5. Code & Formatting: Use proper GitHub-flavored Markdown tables, lists, and syntax-highlighted code blocks.
"""


class AIService:
    """Orchestrates conversations, active AI providers, and context management."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.gemini = GeminiProvider()
        self.ollama = OllamaProvider()

    def get_provider(self, requested_provider: Optional[str] = None) -> BaseAIProvider:
        prov = (requested_provider or self.settings.ai_provider).lower()
        if prov == "gemini":
            return self.gemini
        elif prov == "ollama":
            return self.ollama
        # Default fallback
        if self.gemini.api_key:
            return self.gemini
        return self.ollama

    async def get_status(self) -> dict[str, Any]:
        """Check status of all configured AI providers."""
        gemini_ready = await self.gemini.is_available()
        ollama_ready = await self.ollama.is_available()

        gemini_models = await self.gemini.list_models() if gemini_ready else []
        ollama_models = await self.ollama.list_models() if ollama_ready else []

        active_provider = self.settings.ai_provider
        is_active_ready = (
            (active_provider == AIProvider.GEMINI and gemini_ready) or
            (active_provider == AIProvider.OLLAMA and ollama_ready)
        )

        return {
            "active_provider": active_provider.value if hasattr(active_provider, "value") else str(active_provider),
            "is_ready": is_active_ready,
            "providers": {
                "gemini": {
                    "available": gemini_ready,
                    "default_model": self.gemini.default_model,
                    "models": gemini_models[:8],
                },
                "ollama": {
                    "available": ollama_ready,
                    "base_url": self.ollama.base_url,
                    "default_model": self.ollama.default_model,
                    "models": ollama_models,
                }
            }
        }

    async def prepare_context(
        self,
        conversation_id: str,
        user_message: str,
        db: AsyncSession,
        max_history_turns: int = 10,
    ) -> list[ChatMessage]:
        """Build sliding-window chat history with system prompt and dataset context."""
        messages: list[ChatMessage] = [
            ChatMessage(role=Role.SYSTEM, content=SYSTEM_PROMPT)
        ]

        # Check if conversation has any associated datasets or files
        dataset_res = await db.execute(
            select(Dataset)
            .join(Dataset.source_file)
            .where(Dataset.source_file.has(conversation_id=conversation_id))
        )
        datasets = dataset_res.scalars().all()
        if datasets:
            summary_parts = ["AVAILABLE DATASETS IN THIS CONVERSATION:"]
            for ds in datasets:
                summary_parts.append(
                    f"- Dataset '{ds.name}' (ID: {ds.id}): {ds.total_rows} rows ({ds.valid_rows} valid). Columns: {ds.columns_json}"
                )
            messages.append(
                ChatMessage(
                    role=Role.SYSTEM,
                    content="\n".join(summary_parts)
                )
            )

        # Retrieve recent message history
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(max_history_turns * 2)
        )
        res = await db.execute(stmt)
        db_messages = list(reversed(res.scalars().all()))

        for m in db_messages:
            if m.content:
                messages.append(ChatMessage(role=m.role, content=m.content))

        # Add current user message
        messages.append(ChatMessage(role=Role.USER, content=user_message))
        return messages

    async def stream_response(
        self,
        conversation_id: str,
        user_message: str,
        db: AsyncSession,
        model: Optional[str] = None,
        provider_name: Optional[str] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream response chunks from the active AI provider."""
        provider = self.get_provider(provider_name)

        # If primary provider is not ready, try fallback
        if not await provider.is_available():
            # Check fallback
            if provider.name == "ollama" and await self.gemini.is_available():
                provider = self.gemini
            elif provider.name == "gemini" and await self.ollama.is_available():
                provider = self.ollama
            else:
                yield StreamChunk(
                    error="No AI provider is currently available. Please configure your Gemini API Key in Settings or start Ollama locally.",
                    is_done=True,
                )
                return

        context_messages = await self.prepare_context(conversation_id, user_message, db)
        tools = get_available_tools()

        async for chunk in provider.chat_stream(
            messages=context_messages,
            model=model,
            tools=tools,
        ):
            yield chunk
