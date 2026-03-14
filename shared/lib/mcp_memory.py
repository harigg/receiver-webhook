"""MCP Memory client — wraps the memory server's knowledge graph tools.

Connects to the mcp-memory service via SSE and exposes:
  - save_repo_observation(repo, text)   → remember facts about a repo
  - save_author_observation(author, text) → remember facts about an author
  - recall(query)                        → retrieve relevant memories
  - as_tools()                           → returns Anthropic tool defs for Claude
"""
import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)

MCP_MEMORY_URL = os.getenv("MCP_MEMORY_URL", "http://mcp-memory.agents.svc.cluster.local:8080")


# ---------------------------------------------------------------------------
# Low-level JSON-RPC over HTTP (supergateway exposes the MCP server via HTTP)
# ---------------------------------------------------------------------------

async def _rpc(method: str, params: dict) -> dict:
    """Call an MCP tool on the memory server."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{MCP_MEMORY_URL}/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        )
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"MCP error: {data['error']}")
        return data.get("result", {})


async def _call_tool(name: str, arguments: dict) -> str:
    result = await _rpc("tools/call", {"name": name, "arguments": arguments})
    content = result.get("content", [])
    return " ".join(c.get("text", "") for c in content if c.get("type") == "text")


# ---------------------------------------------------------------------------
# High-level helpers used by agents
# ---------------------------------------------------------------------------

async def save_repo_observation(repo: str, observation: str) -> None:
    """Persist a fact about a repository."""
    try:
        await _call_tool("create_entities", {
            "entities": [{"name": repo, "entityType": "repository", "observations": [observation]}]
        })
        logger.info(f"[memory] saved repo observation: {repo}")
    except Exception as e:
        logger.warning(f"[memory] failed to save repo observation: {e}")


async def save_author_observation(author: str, observation: str) -> None:
    """Persist a fact about a code author."""
    try:
        await _call_tool("create_entities", {
            "entities": [{"name": author, "entityType": "author", "observations": [observation]}]
        })
        logger.info(f"[memory] saved author observation: {author}")
    except Exception as e:
        logger.warning(f"[memory] failed to save author observation: {e}")


async def recall(query: str) -> str:
    """Search the knowledge graph and return relevant memories as text."""
    try:
        result = await _call_tool("search_nodes", {"query": query})
        return result or "No relevant memories found."
    except Exception as e:
        logger.warning(f"[memory] recall failed: {e}")
        return "Memory unavailable."


# ---------------------------------------------------------------------------
# Anthropic tool definitions — pass these into Claude so it can use memory
# ---------------------------------------------------------------------------

MEMORY_TOOLS: list[dict] = [
    {
        "name": "memory_save",
        "description": (
            "Save a persistent observation about a repository or code author. "
            "Use after completing a review to remember patterns, preferences, or issues "
            "that will be relevant for future reviews."
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
                    "description": "Whether this is about a repo or a person"
                },
                "observation": {
                    "type": "string",
                    "description": "Concise factual observation to remember"
                }
            },
            "required": ["entity_name", "entity_type", "observation"]
        }
    },
    {
        "name": "memory_recall",
        "description": (
            "Search past observations about repositories and authors. "
            "Call this at the start of a review to retrieve relevant context "
            "from previous reviews."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for, e.g. repo name, author, or topic"
                }
            },
            "required": ["query"]
        }
    }
]


async def handle_tool_call(tool_name: str, tool_input: dict) -> str:
    """Dispatch a tool call from Claude to the MCP memory server."""
    if tool_name == "memory_save":
        entity_type = tool_input["entity_type"]
        if entity_type == "repository":
            await save_repo_observation(tool_input["entity_name"], tool_input["observation"])
        else:
            await save_author_observation(tool_input["entity_name"], tool_input["observation"])
        return "Observation saved."
    elif tool_name == "memory_recall":
        return await recall(tool_input["query"])
    return f"Unknown tool: {tool_name}"
