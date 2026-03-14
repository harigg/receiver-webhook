"""Base agent class for all AI Company agents."""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

MODEL_FAST = "claude-haiku-4-5-20251001"
MODEL_BALANCED = "claude-sonnet-4-6"
MODEL_POWERFUL = "claude-opus-4-6"


class BaseAgent(ABC):
    """Base class for all specialist agents."""

    def __init__(self, name: str, model: str = MODEL_BALANCED):
        self.name = name
        self.model = model
        self.client = anthropic.Anthropic()

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt defining agent role and behavior."""

    async def think(self, user_message: str, max_tokens: int = 4096) -> str:
        """Send a message and get a response from the agent."""
        logger.info(f"[{self.name}] Processing: {user_message[:100]}...")

        response = await asyncio.to_thread(
            self.client.messages.create,
            model=self.model,
            max_tokens=max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        result = response.content[0].text
        logger.info(f"[{self.name}] Done. Tokens used: {response.usage.input_tokens}+{response.usage.output_tokens}")
        return result

    async def think_with_context(self, messages: list[dict], max_tokens: int = 4096) -> str:
        """Send a multi-turn conversation to the agent."""
        response = await asyncio.to_thread(
            self.client.messages.create,
            model=self.model,
            max_tokens=max_tokens,
            system=self.system_prompt,
            messages=messages,
        )
        return response.content[0].text

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, model={self.model!r})"
