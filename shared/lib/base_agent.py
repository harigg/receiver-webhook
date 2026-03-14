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

    # ------------------------------------------------------------------
    # Core: agentic tool-use loop
    # ------------------------------------------------------------------

    async def think_with_tools(
        self,
        user_message: str,
        tools: list[dict],
        tool_handler: Any,          # async callable: (name, input) -> str
        max_tokens: int = 4096,
        max_rounds: int = 10,
    ) -> str:
        """Run the Claude tool-use loop until stop_reason is end_turn.

        Claude may call tools multiple times (e.g. recall memory, then save).
        Each tool_use block is dispatched to tool_handler and the result fed back.
        """
        messages = [{"role": "user", "content": user_message}]

        for round_num in range(max_rounds):
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=max_tokens,
                system=self.system_prompt,
                tools=tools,
                messages=messages,
            )
            logger.debug(
                f"[{self.name}] round {round_num+1} stop_reason={response.stop_reason} "
                f"tokens={response.usage.input_tokens}+{response.usage.output_tokens}"
            )

            if response.stop_reason == "end_turn":
                return next(
                    (b.text for b in response.content if b.type == "text"), ""
                )

            if response.stop_reason == "tool_use":
                # Append assistant turn
                messages.append({"role": "assistant", "content": response.content})

                # Execute all tool calls in parallel
                tool_blocks = [b for b in response.content if b.type == "tool_use"]
                results = await asyncio.gather(
                    *[tool_handler(b.name, b.input) for b in tool_blocks],
                    return_exceptions=True,
                )

                tool_results = [
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result) if not isinstance(result, Exception)
                                   else f"Tool error: {result}",
                    }
                    for block, result in zip(tool_blocks, results)
                ]
                messages.append({"role": "user", "content": tool_results})
            else:
                # max_tokens or other stop — return whatever text we have
                return next(
                    (b.text for b in response.content if b.type == "text"), ""
                )

        logger.warning(f"[{self.name}] hit max_rounds={max_rounds}")
        return ""

    # ------------------------------------------------------------------
    # Simple call (no tools) — used by specialist agents for fast review
    # ------------------------------------------------------------------

    async def think(self, user_message: str, max_tokens: int = 4096) -> str:
        logger.info(f"[{self.name}] Processing: {user_message[:100]}...")
        response = await asyncio.to_thread(
            self.client.messages.create,
            model=self.model,
            max_tokens=max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        result = response.content[0].text
        logger.info(
            f"[{self.name}] Done. "
            f"tokens={response.usage.input_tokens}+{response.usage.output_tokens}"
        )
        return result

    async def think_with_context(self, messages: list[dict], max_tokens: int = 4096) -> str:
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
