from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LicenseInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    spdx_id: str | None = None
    name: str


class Repository(BaseModel):
    model_config = ConfigDict(extra="ignore")

    full_name: str
    html_url: str
    description: str | None = None
    language: str | None = None
    stargazers_count: int
    open_issues_count: int
    topics: list[str] = Field(default_factory=list)
    archived: bool
    fork: bool
    license: LicenseInfo | None = None
    pushed_at: datetime


class GitHubUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    login: str


class Label(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str


class Milestone(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str


class Issue(BaseModel):
    """An open GitHub issue. title/body are UNTRUSTED text written by strangers."""

    model_config = ConfigDict(extra="ignore")

    number: int
    title: str
    body: str | None = None
    state: str
    html_url: str
    locked: bool = False
    comments: int = 0
    labels: list[Label] = Field(default_factory=list)
    user: GitHubUser | None = None
    assignees: list[GitHubUser] = Field(default_factory=list)
    milestone: Milestone | None = None
    created_at: datetime
    updated_at: datetime
