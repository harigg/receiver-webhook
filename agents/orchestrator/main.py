"""Orchestrator agent — coordinates specialist agents for PR review."""
import asyncio
import logging
import sys

sys.path.insert(0, "/app/shared")

from lib.base_agent import BaseAgent, MODEL_BALANCED
from lib.github_client import GitHubClient

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Orchestrator", model=MODEL_BALANCED)
        self.github = GitHubClient()

    @property
    def system_prompt(self) -> str:
        return """You are the Orchestrator Agent for an AI-powered code review system.
Your job is to:
1. Coordinate specialist agents (architect, coder, security, tester, docs)
2. Synthesize their individual reviews into a coherent, actionable PR review
3. Prioritize findings by severity: Critical > High > Medium > Low
4. Write a clear, concise final review summary

Format your final review as:
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
"""

    async def handle_pr_review(self, owner: str, repo: str, pr_number: int) -> None:
        """Run multi-agent PR review and post result as a GitHub PR review."""
        logger.info(f"Starting PR review: {owner}/{repo}#{pr_number}")

        pr = await self.github.get_pr(owner, repo, pr_number)
        diff = await self.github.get_pr_diff(owner, repo, pr_number)

        pr_context = f"""
Repository: {owner}/{repo}
PR #{pr_number}: {pr.get('title', '')}
Author: {pr.get('user', {}).get('login', '')}
Base branch: {pr.get('base', {}).get('label', 'main')}
Description: {pr.get('body', 'No description provided')}

Diff:
{diff[:8000]}
"""

        from agents.architect.main import ArchitectAgent
        from agents.coder.main import CoderAgent
        from agents.security.main import SecurityAgent
        from agents.tester.main import TesterAgent

        results = await asyncio.gather(
            ArchitectAgent().think(f"Review this PR for architectural concerns:\n{pr_context}"),
            CoderAgent().think(f"Review this PR for code quality:\n{pr_context}"),
            SecurityAgent().think(f"Review this PR for security issues:\n{pr_context}"),
            TesterAgent().think(f"Review this PR for test coverage:\n{pr_context}"),
            return_exceptions=True,
        )

        architect_review, code_review, security_review, test_review = results

        synthesis_prompt = f"""
Synthesize these specialist reviews into a final PR review:

## Architecture Review:
{architect_review}

## Code Quality Review:
{code_review}

## Security Review:
{security_review}

## Test Coverage Review:
{test_review}

PR Context:
{pr_context[:2000]}
"""
        final_review = await self.think(synthesis_prompt)

        # Determine GitHub review event type based on findings
        review_event = "COMMENT"
        if "critical" in final_review.lower():
            review_event = "REQUEST_CHANGES"

        comment = f"""{final_review}

---
*Reviewed by AI agents: Orchestrator + Architect + Coder + Security + Tester*
"""
        await self.github.post_pr_review(owner, repo, pr_number, body=comment, event=review_event)
        logger.info(f"PR review posted: {owner}/{repo}#{pr_number}")

        # Notifications
        from lib.notifier import notify_all
        pr_url = pr.get("html_url", f"https://github.com/{owner}/{repo}/pull/{pr_number}")
        await notify_all(
            f":mag: AI PR Review complete\n"
            f"*{owner}/{repo}* — PR #{pr_number}: {pr.get('title', '')}\n"
            f"{pr_url}"
        )
