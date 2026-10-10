import re

from pydantic import ValidationError

from contribai.github.client import GitHubClient, GitHubError
from contribai.schemas.github import Repository

_FULL_NAME_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


def _validate_full_name(full_name: str) -> None:
    parts = full_name.split("/")
    if not _FULL_NAME_RE.fullmatch(full_name) or any(p in (".", "..") for p in parts):
        raise ValueError(f"Invalid repository name: {full_name!r}")


async def get_repository(client: GitHubClient, full_name: str) -> Repository:
    _validate_full_name(full_name)
    data = await client.get(f"/repos/{full_name}")
    try:
        return Repository.model_validate(data)
    except ValidationError as exc:
        raise GitHubError(f"Unexpected response shape for {full_name}") from exc
