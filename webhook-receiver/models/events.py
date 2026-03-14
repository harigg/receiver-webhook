"""Pydantic models for Gitea webhook payloads."""
from typing import Any
from pydantic import BaseModel


class GiteaUser(BaseModel):
    id: int
    login: str
    full_name: str = ""
    email: str = ""
    avatar_url: str = ""


class GiteaRepo(BaseModel):
    id: int
    name: str
    full_name: str
    owner: GiteaUser
    html_url: str
    clone_url: str
    default_branch: str = "main"


class GiteaCommit(BaseModel):
    id: str
    message: str
    url: str
    author: dict[str, Any] = {}


class PushEvent(BaseModel):
    ref: str
    before: str
    after: str
    repository: GiteaRepo
    pusher: GiteaUser
    commits: list[GiteaCommit] = []


class PullRequestEvent(BaseModel):
    action: str   # opened, closed, synchronized, reopened, review_requested
    number: int
    pull_request: dict[str, Any]
    repository: GiteaRepo
    sender: GiteaUser


class IssueEvent(BaseModel):
    action: str   # opened, closed, reopened, edited
    issue: dict[str, Any]
    repository: GiteaRepo
    sender: GiteaUser
