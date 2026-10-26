"""Vulture Bot - Base AI Provider Interfaces and Types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional, Any, Callable
from enum import Enum


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ChatMessage:
    role: Role | str
    content: str
    tool_calls: Optional[list[dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON schema


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class StreamChunk:
    content: str = ""
    is_done: bool = False
    tool_calls: Optional[list[ToolCall]] = None
    error: Optional[str] = None


class BaseAIProvider(ABC):
    """Abstract interface for AI Providers (Ollama, Gemini, etc.)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider is configured and reachable."""
        pass

    @abstractmethod
    async def list_models(self) -> list[str]:
        """List available models for this provider."""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[list[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream chat completions from the model."""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[list[ToolDefinition]] = None,
        temperature: float = 0.7,
    ) -> ChatMessage:
        """Non-streaming chat completion."""
        pass
