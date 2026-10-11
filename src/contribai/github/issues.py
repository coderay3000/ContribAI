import logging

from pydantic import ValidationError

from contribai.github.client import GitHubClient
from contribai.github.validation import validate_full_name
from contribai.schemas.github import Issue

logger = logging.getLogger(__name__)


async def get_open_issues(client: GitHubClient, full_name: str, max_pages: int = 2) -> list[Issue]:
    validate_full_name(full_name)
    raw_items = await client.get_paginated(
        f"/repos/{full_name}/issues",
        params={"state": "open", "per_page": 100, "sort": "updated", "direction": "desc"},
        max_pages=max_pages,
    )

    issues: list[Issue] = []
    for item in raw_items:
        if "pull_request" in item:
            continue  # GitHub's issues endpoint also returns PRs
        try:
            issues.append(Issue.model_validate(item))
        except ValidationError:
            logger.warning("Skipping malformed issue #%s in %s", item.get("number", "?"), full_name)
    return issues
