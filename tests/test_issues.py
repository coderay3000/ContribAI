import httpx
import respx
from pydantic import SecretStr

from contribai.github.client import GitHubClient
from contribai.github.issues import get_open_issues


def _issue(number: int, **extra: object) -> dict[str, object]:
    return {
        "number": number,
        "title": f"Issue {number}",
        "body": None,
        "html_url": f"https://github.com/o/r/issues/{number}",
        "state": "open",
        "comments": 0,
        "labels": [],
        "assignees": [],
        "user": None,
        "milestone": None,
        "created_at": "2026-10-01T00:00:00Z",
        "updated_at": "2026-10-02T00:00:00Z",
        **extra,
    }


@respx.mock
async def test_get_open_issues_filters_out_pull_requests() -> None:
    payload = [_issue(1), _issue(2, pull_request={"url": "https://api.github.com/x"})]
    respx.get("https://api.github.com/repos/o/r/issues").mock(
        return_value=httpx.Response(200, json=payload)
    )
    async with GitHubClient(token=SecretStr("fake-token")) as client:
        issues = await get_open_issues(client, "o/r")

    assert [issue.number for issue in issues] == [1]
