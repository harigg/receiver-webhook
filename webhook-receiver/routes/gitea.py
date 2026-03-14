"""Gitea webhook handler routes."""
import asyncio
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook/gitea")

WEBHOOK_SECRET = ""  # Set via env var WEBHOOK_SECRET if needed


async def handle_pull_request(payload: dict[str, Any]) -> None:
    """Route PR events to the PR review multi-agent system."""
    action = payload.get("action")
    pr_number = payload.get("number")
    repo = payload.get("repository", {}).get("full_name")

    logger.info(f"PR event: action={action} pr=#{pr_number} repo={repo}")

    if action in ("opened", "synchronized", "reopened"):
        # Import here to avoid circular deps
        from agents.orchestrator.main import OrchestratorAgent
        orchestrator = OrchestratorAgent()
        await orchestrator.handle_pr_review(
            owner=payload["repository"]["owner"]["login"],
            repo=payload["repository"]["name"],
            pr_number=pr_number,
        )


async def handle_push(payload: dict[str, Any]) -> None:
    """Handle push events (e.g. trigger CI)."""
    ref = payload.get("ref", "")
    repo = payload.get("repository", {}).get("full_name")
    commits = payload.get("commits", [])
    logger.info(f"Push event: ref={ref} repo={repo} commits={len(commits)}")


async def handle_issue(payload: dict[str, Any]) -> None:
    """Handle issue events."""
    action = payload.get("action")
    issue_number = payload.get("issue", {}).get("number")
    repo = payload.get("repository", {}).get("full_name")
    logger.info(f"Issue event: action={action} issue=#{issue_number} repo={repo}")


@router.post("")
async def gitea_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_gitea_event: str = Header(default=""),
):
    payload = await request.json()
    event = x_gitea_event.lower()
    logger.info(f"Received Gitea event: {event}")

    if event == "pull_request":
        background_tasks.add_task(handle_pull_request, payload)
    elif event == "push":
        background_tasks.add_task(handle_push, payload)
    elif event in ("issues", "issue_comment"):
        background_tasks.add_task(handle_issue, payload)
    else:
        logger.warning(f"Unhandled event type: {event}")

    return {"status": "received", "event": event}
