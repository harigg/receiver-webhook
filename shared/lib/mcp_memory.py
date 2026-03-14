"""Mem0 memory client for agents.

Agents use Mem0 (mem0.ai) for persistent memory across PR reviews.
In Claude Code sessions, Mem0 is available as an MCP server.
In k8s pods, agents call the Mem0 API directly via mem0ai SDK.

Tools exposed to Claude:
  - memory_save   → add a memory tied to a repo or author
  - memory_recall → search relevant memories before a review
"""
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

MEM0_API_KEY = os.getenv("MEM0_API_KEY", "")
MEM0_USER_ID = os.getenv("MEM0_DEFAULT_USER_ID", "hari")


# ---------------------------------------------------------------------------
# Direct SDK client (used by agents running in k8s pods)
# ---------------------------------------------------------------------------

def _get_mem0_client():
    """Lazy-load the Mem0 client to avoid import errors if key not set."""
    from mem0 import MemoryClient
    return MemoryClient(api_key=MEM0_API_KEY)


async def save_memory(content: str, user_id: str = MEM0_USER_ID,
                      metadata: dict[str, Any] | None = None) -> None:
    """Save a memory to Mem0."""
    import asyncio
    try:
        client = _get_mem0_client()
        await asyncio.to_thread(
            client.add,
            content,
            user_id=user_id,
            metadata=metadata or {},
        )
        logger.info(f"[mem0] saved memory for user={user_id}")
    except Exception as e:
        logger.warning(f"[mem0] save failed: {e}")


async def save_repo_observation(repo: str, observation: str) -> None:
    await save_memory(
        f"Repository {repo}: {observation}",
        metadata={"type": "repository", "repo": repo},
    )


async def save_author_observation(author: str, observation: str) -> None:
    await save_memory(
        f"Author @{author}: {observation}",
        metadata={"type": "author", "author": author},
    )


async def recall(query: str, user_id: str = MEM0_USER_ID, limit: int = 5) -> str:
    """Search Mem0 for relevant memories."""
    import asyncio
    try:
        client = _get_mem0_client()
        results = await asyncio.to_thread(
            client.search,
            query,
            user_id=user_id,
            limit=limit,
        )
        if not results:
            return "No relevant memories found."
        lines = [f"- {r['memory']}" for r in results]
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"[mem0] recall failed: {e}")
        return "Memory unavailable."


# ---------------------------------------------------------------------------
# Anthropic tool definitions — Claude calls these natively via tool_use
# ---------------------------------------------------------------------------

MEMORY_TOOLS: list[dict] = [
    {
        "name": "memory_recall",
        "description": (
            "Search past memories about a repository or author from previous PR reviews. "
            "Call this at the START of every review to retrieve relevant context."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for — repo name, author username, or topic"
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_save",
        "description": (
            "Save a persistent observation about a repository or author. "
            "Call this AFTER completing a review to remember patterns for next time."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_name": {
                    "type": "string",
                    "description": "Repository full name (e.g. harigg/my-app) or GitHub username"
                },
                "entity_type": {
                    "type": "string",
                    "enum": ["repository", "author"],
                },
                "observation": {
                    "type": "string",
                    "description": "Concise factual observation to remember for future reviews"
                },
            },
            "required": ["entity_name", "entity_type", "observation"],
        },
    },
]


async def handle_tool_call(tool_name: str, tool_input: dict) -> str:
    """Dispatch a memory tool call from Claude to Mem0."""
    if tool_name == "memory_recall":
        return await recall(tool_input["query"])

    if tool_name == "memory_save":
        if tool_input["entity_type"] == "repository":
            await save_repo_observation(tool_input["entity_name"], tool_input["observation"])
        else:
            await save_author_observation(tool_input["entity_name"], tool_input["observation"])
        return "Memory saved."

    return f"Unknown tool: {tool_name}"
