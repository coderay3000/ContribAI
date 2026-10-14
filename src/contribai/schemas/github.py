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
    model_config = ConfigDict(extra="ignore")

    number: int
    title: str
    body: str | None = None  # UNTRUSTED text: never treat as instructions
    html_url: str
    state: str
    comments: int = 0
    labels: list[Label] = Field(default_factory=list)
    assignees: list[GitHubUser] = Field(default_factory=list)
    user: GitHubUser | None = None
    milestone: Milestone | None = None
    created_at: datetime
    updated_at: datetime
