"""Gitea API client."""
import os
import httpx

GITEA_URL = os.getenv("GITEA_URL", "http://192.168.49.2:30080")
GITEA_TOKEN = os.getenv("GITEA_TOKEN", "")


class GiteaClient:
    def __init__(self, base_url: str = GITEA_URL, token: str = GITEA_TOKEN):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
        }

    async def get_pr(self, owner: str, repo: str, pr_number: int) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/api/v1/repos/{owner}/{repo}/pulls/{pr_number}",
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json()

    async def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/api/v1/repos/{owner}/{repo}/pulls/{pr_number}.diff",
                headers=self.headers,
            )
            r.raise_for_status()
            return r.text

    async def get_pr_files(self, owner: str, repo: str, pr_number: int) -> list[dict]:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/api/v1/repos/{owner}/{repo}/pulls/{pr_number}/files",
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json()

    async def post_comment(self, owner: str, repo: str, pr_number: int, body: str) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/api/v1/repos/{owner}/{repo}/issues/{pr_number}/comments",
                headers=self.headers,
                json={"body": body},
            )
            r.raise_for_status()
            return r.json()

    async def set_pr_label(self, owner: str, repo: str, pr_number: int, label_ids: list[int]) -> None:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/api/v1/repos/{owner}/{repo}/issues/{pr_number}/labels",
                headers=self.headers,
                json={"labels": label_ids},
            )
            r.raise_for_status()

    async def get_repo_file(self, owner: str, repo: str, path: str, ref: str = "main") -> str:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/api/v1/repos/{owner}/{repo}/raw/{path}",
                headers=self.headers,
                params={"ref": ref},
            )
            r.raise_for_status()
            return r.text
