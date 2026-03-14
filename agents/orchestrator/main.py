"""Orchestrator agent — coordinates specialist agents for PR review.

Flow:
  1. Recall memory about this repo + author (MCP memory server)
  2. Fan out to specialist agents in parallel
  3. Synthesise all reviews (with memory context)
  4. Post formal GitHub PR review
  5. Save new observations to memory
  6. Notify Slack + WhatsApp
"""
import asyncio
import logging
import sys

sys.path.insert(0, "/app/shared")

from lib.base_agent import BaseAgent, MODEL_BALANCED
from lib.github_client import GitHubClient
from lib.mcp_memory import MEMORY_TOOLS, handle_tool_call, recall

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Orchestrator", model=MODEL_BALANCED)
        self.github = GitHubClient()

    @property
    def system_prompt(self) -> str:
        return """You are the Orchestrator Agent for an AI-powered code review system.

You have two memory tools available:
- memory_recall: search past observations about a repo or author BEFORE writing your review
- memory_save: save new observations AFTER completing your review

Always start by recalling memory for the repo and author.
Always end by saving 1-3 concise observations learned from this review.

Synthesise specialist reviews into a final PR review formatted as:

## AI Code Review Summary

### Overall Assessment
<APPROVE/REQUEST_CHANGES/COMMENT> — <one line summary>

### Critical Issues (must fix before merge)
<list or "None">

### High Priority
<list or "None">

### Suggestions
<list or "None">

### Positive Observations
<list>

Be direct and actionable. Prioritise: Critical > High > Medium > Low.
"""

    async def handle_pr_review(self, owner: str, repo: str, pr_number: int) -> None:
        repo_full = f"{owner}/{repo}"
        logger.info(f"Starting PR review: {repo_full}#{pr_number}")

        # Fetch PR data from GitHub
        pr, diff = await asyncio.gather(
            self.github.get_pr(owner, repo, pr_number),
            self.github.get_pr_diff(owner, repo, pr_number),
        )

        author = pr.get("user", {}).get("login", "unknown")

        pr_context = f"""
Repository: {repo_full}
PR #{pr_number}: {pr.get('title', '')}
Author: {author}
Base branch: {pr.get('base', {}).get('label', 'main')}
Description: {pr.get('body', 'No description provided')}

Diff:
{diff[:8000]}
"""

        # Fan out to specialists in parallel
        from agents.architect.main import ArchitectAgent
        from agents.coder.main import CoderAgent
        from agents.security.main import SecurityAgent
        from agents.tester.main import TesterAgent

        specialist_results = await asyncio.gather(
            ArchitectAgent().think(f"Review this PR for architectural concerns:\n{pr_context}"),
            CoderAgent().think(f"Review this PR for code quality:\n{pr_context}"),
            SecurityAgent().think(f"Review this PR for security issues:\n{pr_context}"),
            TesterAgent().think(f"Review this PR for test coverage:\n{pr_context}"),
            return_exceptions=True,
        )
        architect_r, code_r, security_r, test_r = specialist_results

        # Build synthesis prompt — orchestrator will use memory tools
        synthesis_prompt = f"""
You are reviewing PR #{pr_number} in {repo_full} by @{author}.

Start by recalling memory for "{repo_full}" and "{author}".

Here are the specialist reviews:

## Architecture Review:
{architect_r}

## Code Quality Review:
{code_r}

## Security Review:
{security_r}

## Test Coverage Review:
{test_r}

PR context:
{pr_context[:2000]}

After writing your final review, save 1-3 observations about this repo or author that
would be useful for future reviews.
"""
        final_review = await self.think_with_tools(
            user_message=synthesis_prompt,
            tools=MEMORY_TOOLS,
            tool_handler=handle_tool_call,
        )

        # Determine review event from content
        review_event = "REQUEST_CHANGES" if "critical" in final_review.lower() else "COMMENT"

        comment = f"""{final_review}

---
*Reviewed by AI agents: Orchestrator · Architect · Coder · Security · Tester*
"""
        await self.github.post_pr_review(owner, repo, pr_number, body=comment, event=review_event)
        logger.info(f"PR review posted: {repo_full}#{pr_number}")

        # Notify
        from lib.notifier import notify_all
        pr_url = pr.get("html_url", f"https://github.com/{repo_full}/pull/{pr_number}")
        await notify_all(
            f":mag: AI PR Review complete\n"
            f"*{repo_full}* — PR #{pr_number}: {pr.get('title', '')}\n"
            f"{pr_url}"
        )
