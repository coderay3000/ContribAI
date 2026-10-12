import httpx
import pytest
import respx
from pydantic import SecretStr

from contribai.github.client import (
    GitHubClient,
    GitHubError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)


@respx.mock
async def test_get_returns_json_on_200() -> None:
    respx.get("https://api.github.com/repos/o/r").mock(
        return_value=httpx.Response(200, json={"full_name": "o/r"})
    )
    async with GitHubClient(token=SecretStr("fake-token")) as client:
        data = await client.get("/repos/o/r")
    assert data == {"full_name": "o/r"}


@respx.mock
async def test_get_raises_not_found_on_404() -> None:
    respx.get("https://api.github.com/repos/o/missing").mock(return_value=httpx.Response(404))
    async with GitHubClient(token=SecretStr("fake-token")) as client:
        with pytest.raises(GitHubNotFoundError):
            await client.get("/repos/o/missing")


@respx.mock
async def test_get_raises_rate_limit_on_403_with_zero_remaining() -> None:
    respx.get("https://api.github.com/repos/o/r").mock(
        return_value=httpx.Response(403, headers={"x-ratelimit-remaining": "0"})
    )
    async with GitHubClient(token=SecretStr("fake-token")) as client:
        with pytest.raises(GitHubRateLimitError):
            await client.get("/repos/o/r")


@respx.mock
async def test_get_raises_generic_error_on_403_with_quota_left() -> None:
    respx.get("https://api.github.com/repos/o/r").mock(
        return_value=httpx.Response(403, headers={"x-ratelimit-remaining": "42"})
    )

    async with GitHubClient(token=SecretStr("fake-token")) as client:
        with pytest.raises(GitHubError) as exc_info:
            await client.get("/repos/o/r")

    assert not isinstance(exc_info.value, GitHubRateLimitError)
    assert exc_info.value.status_code == 403


@respx.mock
async def test_get_raises_github_error_on_non_json_body() -> None:
    respx.get("https://api.github.com/repos/o/r").mock(
        return_value=httpx.Response(200, text="<html>oops</html>")
    )
    async with GitHubClient(token=SecretStr("fake-token")) as client:
        with pytest.raises(GitHubError):
            await client.get("/repos/o/r")
