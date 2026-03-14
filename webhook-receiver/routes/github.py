"""GitHub webhook handler routes."""
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

sys_path_hack = None  # resolved via PYTHONPATH in deployment

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook/github")


async def handle_pull_request(payload: dict[str, Any]) -> None:
    action = payload.get("action")
    pr_number = payload.get("number")
    repo_full = payload.get("repository", {}).get("full_name", "")
    owner, repo = repo_full.split("/", 1) if "/" in repo_full else ("", repo_full)

    logger.info(f"GitHub PR event: action={action} pr=#{pr_number} repo={repo_full}")

    if action in ("opened", "synchronize", "reopened"):
        from agents.orchestrator.main import OrchestratorAgent
        orchestrator = OrchestratorAgent()
        await orchestrator.handle_pr_review(owner=owner, repo=repo, pr_number=pr_number)


async def handle_push(payload: dict[str, Any]) -> None:
    ref = payload.get("ref", "")
    repo = payload.get("repository", {}).get("full_name", "")
    commits = payload.get("commits", [])
    logger.info(f"GitHub push: ref={ref} repo={repo} commits={len(commits)}")


@router.post("")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(default=""),
    x_hub_signature_256: str = Header(default=""),
):
    body = await request.body()

    # Verify signature
    from lib.github_client import verify_webhook_signature
    if not verify_webhook_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = await request.json() if not body else __import__("json").loads(body)
    event = x_github_event.lower()
    logger.info(f"Received GitHub event: {event}")

    if event == "pull_request":
        background_tasks.add_task(handle_pull_request, payload)
    elif event == "push":
        background_tasks.add_task(handle_push, payload)
    elif event == "ping":
        return {"status": "pong"}
    else:
        logger.info(f"Unhandled GitHub event: {event}")

    return {"status": "received", "event": event}
