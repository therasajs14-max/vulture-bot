"""Vulture Bot - Google Gemini AI Provider."""

from __future__ import annotations

import json
from typing import AsyncGenerator, Optional, Any
import httpx

from app.ai.base import BaseAIProvider, ChatMessage, StreamChunk, ToolDefinition, ToolCall, Role
from app.config import get_settings


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI Provider with async streaming and tool call support."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self._settings = get_settings()
        self.api_key = api_key or self._settings.gemini_api_key
        self.default_model = default_model or self._settings.gemini_model or "gemini-1.5-flash"

    @property
    def name(self) -> str:
        return "gemini"

    async def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 5)

    async def list_models(self) -> list[str]:
        if not await self.is_available():
            return []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(f"{self.BASE_URL}/models?key={self.api_key}")
                if res.status_code == 200:
                    data = res.json()
                    models = [
                        m["name"].replace("models/", "")
                        for m in data.get("models", [])
                        if "generateContent" in m.get("supportedGenerationMethods", [])
                    ]
                    return models or ["gemini-1.5-flash", "gemini-1.5-pro"]
        except Exception:
            pass
        return ["gemini-1.5-flash", "gemini-1.5-pro"]

    def _convert_messages(self, messages: list[ChatMessage]) -> tuple[Optional[dict[str, Any]], list[dict[str, Any]]]:
        """Convert standard messages to Gemini contents and system_instruction format."""
        system_instruction = None
        contents = []

        for msg in messages:
            role_str = str(msg.role).lower()
            if "system" in role_str:
                system_instruction = {"parts": [{"text": msg.content}]}
            elif "user" in role_str:
                contents.append({
                    "role": "user",
                    "parts": [{"text": msg.content}]
                })
            elif "assistant" in role_str:
                parts = []
                if msg.content:
                    parts.append({"text": msg.content})
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        parts.append({
                            "functionCall": {
                                "name": tc.get("name"),
                                "args": tc.get("arguments", {})
                            }
                        })
                contents.append({
                    "role": "model",
                    "parts": parts or [{"text": ""}]
                })
            elif "tool" in role_str:
                contents.append({
                    "role": "function",
                    "parts": [{
                        "functionResponse": {
                            "name": msg.name or "tool_result",
                            "response": {"result": msg.content}
                        }
                    }]
                })

        return system_instruction, contents

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[list[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        if not await self.is_available():
            yield StreamChunk(
                error="Gemini API key is not configured. Please add GEMINI_API_KEY to your settings.",
                is_done=True,
            )
            return

        model_name = model or self.default_model
        system_instruction, contents = self._convert_messages(messages)

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            }
        }
        if system_instruction:
            payload["system_instruction"] = system_instruction
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens

        url = f"{self.BASE_URL}/models/{model_name}:streamGenerateContent?alt=sse&key={self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        err_text = await response.aread()
                        yield StreamChunk(
                            error=f"Gemini API error ({response.status_code}): {err_text.decode('utf-8', errors='ignore')[:300]}",
                            is_done=True,
                        )
                        return

                    buffer = ""
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            try:
                                chunk_json = json.loads(data_str)
                                candidates = chunk_json.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    for part in parts:
                                        if "text" in part:
                                            yield StreamChunk(content=part["text"])
                                        elif "functionCall" in part:
                                            fn = part["functionCall"]
                                            yield StreamChunk(
                                                tool_calls=[ToolCall(
                                                    id=fn.get("name", "call"),
                                                    name=fn.get("name"),
                                                    arguments=fn.get("args", {})
                                                )]
                                            )
                            except json.JSONDecodeError:
                                pass

            yield StreamChunk(is_done=True)
        except Exception as e:
            yield StreamChunk(error=f"Error communicating with Gemini: {str(e)}", is_done=True)

    async def chat(
        self,
        messages: list[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[list[ToolDefinition]] = None,
        temperature: float = 0.7,
    ) -> ChatMessage:
        content = ""
        tool_calls = []
        async for chunk in self.chat_stream(messages, model=model, tools=tools, temperature=temperature):
            if chunk.error:
                return ChatMessage(role=Role.ASSISTANT, content=f"Error: {chunk.error}")
            if chunk.content:
                content += chunk.content
            if chunk.tool_calls:
                for tc in chunk.tool_calls:
                    tool_calls.append({"id": tc.id, "name": tc.name, "arguments": tc.arguments})

        return ChatMessage(
            role=Role.ASSISTANT,
            content=content,
            tool_calls=tool_calls if tool_calls else None
        )
