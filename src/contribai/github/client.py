import logging
import time
from types import TracebackType
from typing import Any, Self

import httpx
from pydantic import SecretStr

logger = logging.getLogger(__name__)


class GitHubError(Exception):
    """Base error for every GitHub-related failure."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GitHubNotFoundError(GitHubError):
    """Resource does not exist (or is not visible to this token)."""


class GitHubRateLimitError(GitHubError):
    """We hit a rate limit. retry_after is in seconds, if GitHub told us."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message, status_code=403)
        self.retry_after = retry_after


def _is_rate_limited(response: httpx.Response) -> bool:
    if response.status_code == 429:
        return True
    if response.status_code != 403:
        return False
    # 403 can mean rate limit OR missing permission. Headers tell them apart.
    if "retry-after" in response.headers:  # secondary rate limit
        return True
    return response.headers.get("x-ratelimit-remaining") == "0"  # primary


def _retry_after_seconds(response: httpx.Response) -> float | None:
    if "retry-after" in response.headers:
        return float(response.headers["retry-after"])
    reset = response.headers.get("x-ratelimit-reset")
    if reset is not None:
        return max(0.0, float(reset) - time.time())
    return None


class GitHubClient:
    def __init__(
        self,
        token: SecretStr,
        base_url: str = "https://api.github.com",
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {token.get_secret_value()}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

    async def _request(self, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
        try:
            response = await self._client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise GitHubError(f"Timeout calling GitHub: {url}") from exc
        except httpx.RequestError as exc:
            raise GitHubError(f"Network error calling GitHub: {url}") from exc

        self._log_rate_limit(url, response)

        if response.is_success:
            return response
        if _is_rate_limited(response):
            raise GitHubRateLimitError(
                f"Rate limited on {url}", retry_after=_retry_after_seconds(response)
            )
        if response.status_code == 404:
            raise GitHubNotFoundError(f"Not found: {url}", status_code=404)
        raise GitHubError(
            f"GitHub returned {response.status_code} for {url}",
            status_code=response.status_code,
        )

    @staticmethod
    def _parse_json(response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError as exc:
            raise GitHubError(
                "GitHub returned a non-JSON response", status_code=response.status_code
            ) from exc

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = await self._request(path, params)
        return self._parse_json(response)

    async def get_paginated(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        max_pages: int = 3,
    ) -> list[Any]:
        items: list[Any] = []
        url: str | None = path
        page_params = params
        for _ in range(max_pages):
            if url is None:
                break
            response = await self._request(url, page_params)
            items.extend(self._parse_json(response))
            url = response.links.get("next", {}).get("url")
            page_params = None
            if url is not None and not url.startswith(self._base_url):
                raise GitHubError("Refusing to follow pagination link to another host")
        return items

    @staticmethod
    def _log_rate_limit(path: str, response: httpx.Response) -> None:
        logger.info(
            "GET %s -> %s (rate limit remaining: %s)",
            path,
            response.status_code,
            response.headers.get("x-ratelimit-remaining", "?"),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()
