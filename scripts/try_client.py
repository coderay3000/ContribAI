import asyncio
import logging

from contribai.config import get_settings
from contribai.github.client import GitHubClient
from contribai.github.issues import get_open_issues
from contribai.github.repositories import search_repositories

logging.basicConfig(level=logging.INFO)

QUERY = "language:python topic:machine-learning stars:>100 archived:false good-first-issues:>0"


async def main() -> None:
    settings = get_settings()
    async with GitHubClient(token=settings.github_token) as client:
        repos = await search_repositories(client, QUERY, per_page=5)
        for repo in repos:
            print(repo.full_name, repo.stargazers_count, repo.pushed_at.date())

        if repos:
            issues = await get_open_issues(client, repos[0].full_name)
            print(f"{len(issues)} open issues in {repos[0].full_name}")
            for issue in issues[:5]:
                print(f"#{issue.number} {issue.title} {[label.name for label in issue.labels]}")


asyncio.run(main())
