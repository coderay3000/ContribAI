import logging
from typing import Literal

from pydantic import ValidationError

from contribai.github.client import GitHubClient, GitHubError
from contribai.github.validation import validate_full_name
from contribai.schemas.github import Repository

logger = logging.getLogger(__name__)

SearchSort = Literal["stars", "forks", "help-wanted-issues", "updated"]


async def get_repository(client: GitHubClient, full_name: str) -> Repository:
    validate_full_name(full_name)
    data = await client.get(f"/repos/{full_name}")
    try:
        return Repository.model_validate(data)
    except ValidationError as exc:
        raise GitHubError(f"Unexpected response shape for {full_name}") from exc


async def search_repositories(
    client: GitHubClient,
    query: str,
    sort: SearchSort = "updated",
    per_page: int = 30,
) -> list[Repository]:
    params = {
        "q": query,
        "sort": sort,
        "order": "desc",
        "per_page": min(per_page, 100),
    }
    data = await client.get("/search/repositories", params=params)

    repos: list[Repository] = []
    for item in data.get("items", []):
        try:
            repos.append(Repository.model_validate(item))
        except ValidationError:
            logger.warning("Skipping malformed search result: %s", item.get("full_name", "?"))
    return repos
