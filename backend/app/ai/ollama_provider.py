"""Vulture Bot - Ollama AI Provider."""

from __future__ import annotations

import json
from typing import AsyncGenerator, Optional, Any
import httpx

from app.ai.base import BaseAIProvider, ChatMessage, StreamChunk, ToolDefinition, ToolCall, Role
from app.config import get_settings


class OllamaProvider(BaseAIProvider):
    """Local Ollama AI Provider."""

    def __init__(self, base_url: Optional[str] = None, default_model: Optional[str] = None):
        settings = get_settings()
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.default_model = default_model or settings.ollama_model

    @property
    def name(self) -> str:
        return "ollama"

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return [self.default_model]

    def _convert_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        ollama_msgs = []
        for msg in messages:
            role_str = str(msg.role).lower()
            if "system" in role_str:
                role = "system"
            elif "assistant" in role_str:
                role = "assistant"
            elif "tool" in role_str:
                role = "tool"
            else:
                role = "user"

            item: dict[str, Any] = {"role": role, "content": msg.content}
            if msg.tool_calls:
                item["tool_calls"] = msg.tool_calls
            ollama_msgs.append(item)
        return ollama_msgs

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[list[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        available = await self.is_available()
        if not available:
            yield StreamChunk(
                error=f"Ollama is not reachable at {self.base_url}. Please ensure Ollama is installed and running (`ollama serve`), or switch to Google Gemini in settings.",
                is_done=True,
            )
            return

        model_name = model or self.default_model
        payload: dict[str, Any] = {
            "model": model_name,
            "messages": self._convert_messages(messages),
            "stream": True,
            "options": {
                "temperature": temperature,
            }
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                    if response.status_code != 200:
                        err_text = await response.aread()
                        yield StreamChunk(
                            error=f"Ollama error ({response.status_code}): {err_text.decode('utf-8', errors='ignore')}",
                            is_done=True,
                        )
                        return

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk_data = json.loads(line)
                            msg = chunk_data.get("message", {})
                            content = msg.get("content", "")
                            if content:
                                yield StreamChunk(content=content)
                            if chunk_data.get("done", False):
                                yield StreamChunk(is_done=True)
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            yield StreamChunk(error=f"Error connecting to Ollama: {str(e)}", is_done=True)

    async def chat(
        self,
        messages: list[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[list[ToolDefinition]] = None,
        temperature: float = 0.7,
    ) -> ChatMessage:
        content = ""
        async for chunk in self.chat_stream(messages, model=model, tools=tools, temperature=temperature):
            if chunk.error:
                return ChatMessage(role=Role.ASSISTANT, content=f"Error: {chunk.error}")
            if chunk.content:
                content += chunk.content
        return ChatMessage(role=Role.ASSISTANT, content=content)
