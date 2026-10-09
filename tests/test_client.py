import httpx
import pytest
import respx
from pydantic import SecretStr

from contribai.github.client import GitHubClient


@pytest.mark.asyncio
@respx.mock
async def test_get_returns_json_on_success() -> None:
    route = respx.get("https://api.github.com/repos/langchain-ai/langgraph").mock(
        return_value=httpx.Response(
            200,
            json={
                "full_name": "langchain-ai/langgraph",
                "stargazers_count": 42957,
            },
            headers={"x-ratelimit-remaining": "4999"},
        )
    )

    async with GitHubClient(token=SecretStr("test-token")) as client:
        data = await client.get("/repos/langchain-ai/langgraph")

    assert route.called
    assert data["full_name"] == "langchain-ai/langgraph"
    assert data["stargazers_count"] == 42957
