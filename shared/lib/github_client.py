"""GitHub API client."""
import hashlib
import hmac
import os

import httpx

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_API_URL = "https://api.github.com"
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")


def verify_webhook_signature(payload_bytes: bytes, signature_header: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature."""
    if not WEBHOOK_SECRET:
        return True  # Skip verification if no secret configured
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


class GitHubClient:
    def __init__(self, token: str = GITHUB_TOKEN):
        self.base_url = GITHUB_API_URL
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_pr(self, owner: str, repo: str, pr_number: int) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json()

    async def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        headers = {**self.headers, "Accept": "application/vnd.github.diff"}
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers=headers,
            )
            r.raise_for_status()
            return r.text

    async def get_pr_files(self, owner: str, repo: str, pr_number: int) -> list[dict]:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files",
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json()

    async def post_pr_comment(self, owner: str, repo: str, pr_number: int, body: str) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments",
                headers=self.headers,
                json={"body": body},
            )
            r.raise_for_status()
            return r.json()

    async def post_pr_review(self, owner: str, repo: str, pr_number: int, body: str, event: str = "COMMENT") -> dict:
        """Submit a formal PR review (APPROVE, REQUEST_CHANGES, COMMENT)."""
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
                headers=self.headers,
                json={"body": body, "event": event},
            )
            r.raise_for_status()
            return r.json()

    async def get_repo_file(self, owner: str, repo: str, path: str, ref: str = "main") -> str:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/contents/{path}",
                headers={**self.headers, "Accept": "application/vnd.github.raw+json"},
                params={"ref": ref},
            )
            r.raise_for_status()
            return r.text

    async def create_check_run(self, owner: str, repo: str, name: str, head_sha: str,
                                status: str, conclusion: str = None, output: dict = None) -> dict:
        payload = {"name": name, "head_sha": head_sha, "status": status}
        if conclusion:
            payload["conclusion"] = conclusion
        if output:
            payload["output"] = output
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/check-runs",
                headers=self.headers,
                json=payload,
            )
            r.raise_for_status()
            return r.json()
