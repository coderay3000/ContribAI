import asyncio
import logging

from contribai.config import get_settings
from contribai.github.client import GitHubClient

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    settings = get_settings()
    async with GitHubClient(token=settings.github_token) as client:
        data = await client.get("/repos/langchain-ai/langgraph")
        print(data["full_name"], data["stargazers_count"], data["topics"])


if __name__ == "__main__":
    asyncio.run(main())

# import asyncio
# import logging

# from contribai.config import get_settings
# from contribai.github.client import GitHubClient

# logging.basicConfig(level=logging.INFO)

# async def main() -> None:
#      settings = get_settings()


#      async with GitHubClient(token=settings.github_token) as client:
#           try:
#               data = await client.get("/user")
#               print("Authentication successful!")
#               print("Authenticated GitHub user:", data["login"])

#           except Exception as exc:
#               print(f"Request failed: {exc}")

# if __name__ == "__main__":
#       asyncio.run(main())
