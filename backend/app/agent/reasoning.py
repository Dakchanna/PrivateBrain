from __future__ import annotations
import asyncio
import json
from typing import Any, Optional
import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

TOOL_CALL_DELIMITER = "<<<TOOL_CALL>>>"
TOOL_RESULT_DELIMITER = "<<<TOOL_RESULT>>>"


class OllamaClient:
    """
    Direct Ollama HTTP client for tool-calling agent loop.
    Supports structured tool invocation via prompt engineering +
    JSON response parsing (compatible with any instruction-tuned model).
    """

    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = (base_url or settings.model_base_url).rstrip("/")
        self.model = model or settings.agent_model
        self._available: Optional[bool] = None

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                self._available = r.status_code == 200
                return self._available
        except Exception:
            self._available = False
            return False

    async def chat(self, messages: list[dict], temperature: float = 0.1,
                   tools_schema: list[dict] | None = None) -> str:
        """
        Call Ollama /api/chat endpoint. Returns model text response.
        If tools_schema is provided, injects a tool-use instruction section.
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        # Inject tool schema if Ollama version supports native tools
        if tools_schema:
            payload["tools"] = tools_schema

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()

                # Handle native tool_calls response (Ollama >= 0.3)
                message = data.get("message", {})
                tool_calls = message.get("tool_calls", [])
                if tool_calls:
                    # Return structured tool call info
                    return json.dumps({"tool_calls": tool_calls})

                return message.get("content", "")
        except httpx.ConnectError:
            logger.warning({"event": "ollama_unavailable", "url": self.base_url})
            raise ConnectionError(f"Ollama not reachable at {self.base_url}")
        except Exception as e:
            logger.error({"event": "ollama_error", "error": str(e)})
            raise

    async def generate_decision(self, system_prompt: str, user_message: str,
                                conversation: list[dict] | None = None) -> str:
        """Send agent conversation and get a decision response."""
        messages = [{"role": "system", "content": system_prompt}]
        if conversation:
            messages.extend(conversation)
        messages.append({"role": "user", "content": user_message})
        return await self.chat(messages, temperature=0.05)


# Global singleton
ollama_client = OllamaClient()
