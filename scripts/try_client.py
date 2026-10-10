import asyncio
import logging

from contribai.config import get_settings
from contribai.github.client import GitHubClient
from contribai.github.repositories import get_repository

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    settings = get_settings()
    async with GitHubClient(token=settings.github_token) as client:
        repo = await get_repository(client, "langchain-ai/langgraph")
        print(repo.full_name, repo.language, repo.pushed_at)
        print(repo.license)
        print(repo.topics[:5])


asyncio.run(main())
