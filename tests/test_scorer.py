from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from contribai.matching.scorer import (
    NEUTRAL,
    contribution_friendliness,
    difficulty_fit,
    documentation_quality,
    domain_match,
    effort_fit,
    issue_activity,
    skill_match,
)
from contribai.schemas.github import Issue, Repository
from contribai.schemas.profile import DeveloperProfile

NOW = datetime(2026, 10, 14, tzinfo=UTC)


def _ago(days: float) -> str:
    return (NOW - timedelta(days=days)).isoformat()


def _repo(**overrides: Any) -> Repository:
    data: dict[str, Any] = {
        "full_name": "o/r",
        "html_url": "https://github.com/o/r",
        "stargazers_count": 10,
        "open_issues_count": 1,
        "archived": False,
        "fork": False,
        "pushed_at": "2026-10-01T00:00:00Z",
    }
    data.update(overrides)
    return Repository.model_validate(data)


def _issue(labels: list[str] | None = None, **overrides: Any) -> Issue:
    data: dict[str, Any] = {
        "number": 1,
        "title": "t",
        "state": "open",
        "html_url": "https://github.com/o/r/issues/1",
        "created_at": "2026-10-01T00:00:00Z",
        "updated_at": "2026-10-02T00:00:00Z",
        "labels": [{"name": name} for name in labels or []],
    }
    data.update(overrides)
    return Issue.model_validate(data)


def _profile(
    skills: list[dict[str, Any]] | None = None,
    domains: list[str] | None = None,
    level: str = "intermediate",
    weekly_hours: int = 10,
) -> DeveloperProfile:
    return DeveloperProfile.model_validate(
        {
            "username": "dev",
            "skills": skills or [],
            "preferred_domains": domains or [],
            "experience_level": level,
            "weekly_hours": weekly_hours,
        }
    )


# ---------- skill_match ----------


def test_skill_match_language_with_full_evidence() -> None:
    profile = _profile([{"name": "Python", "level": 8, "evidence_count": 5}])

    result = skill_match(profile, _repo(language="Python"), _issue())

    assert result.value == pytest.approx(0.8)
    assert "Python" in result.reason


def test_skill_match_discounts_skills_without_evidence() -> None:
    profile = _profile([{"name": "Python", "level": 8, "evidence_count": 0}])

    result = skill_match(profile, _repo(language="Python"), _issue())

    assert result.value == pytest.approx(0.4)


def test_skill_match_is_zero_when_language_is_unknown_to_developer() -> None:
    profile = _profile([{"name": "Rust", "level": 9, "evidence_count": 5}])

    result = skill_match(profile, _repo(language="Python"), _issue())

    assert result.value == 0.0
    assert "no Python skill" in result.reason


def test_skill_match_topics_only_add_a_bonus() -> None:
    profile = _profile(
        [
            {"name": "Python", "level": 8, "evidence_count": 5},
            {"name": "FastAPI", "level": 6, "evidence_count": 5},
        ]
    )

    result = skill_match(profile, _repo(language="Python", topics=["fastapi", "chatgpt"]), _issue())

    assert result.value == pytest.approx(0.86)


def test_skill_match_normalizes_topic_names() -> None:
    profile = _profile([{"name": "Machine Learning", "level": 7, "evidence_count": 5}])

    result = skill_match(profile, _repo(topics=["machine-learning"]), _issue())

    assert result.value == pytest.approx(0.7)


# ---------- domain_match ----------


def test_domain_match_via_topic() -> None:
    result = domain_match(_profile(domains=["MLOps"]), _repo(topics=["mlops"]), _issue())

    assert result.value == 1.0


def test_domain_match_via_description_word() -> None:
    result = domain_match(_profile(domains=["ai"]), _repo(description="An AI toolkit"), _issue())

    assert result.value == 1.0


def test_domain_match_partial() -> None:
    result = domain_match(_profile(domains=["ai", "backend"]), _repo(topics=["ai"]), _issue())

    assert result.value == pytest.approx(0.5)


def test_domain_match_is_neutral_without_preferences() -> None:
    result = domain_match(_profile(), _repo(topics=["ai"]), _issue())

    assert result.value == NEUTRAL


def test_domain_match_is_zero_when_nothing_matches() -> None:
    result = domain_match(_profile(domains=["gaming"]), _repo(topics=["ai"]), _issue())

    assert result.value == 0.0


# ---------- difficulty_fit ----------


def test_difficulty_fit_perfect_match() -> None:
    profile = _profile(level="beginner")

    result = difficulty_fit(profile, _repo(), _issue(["Good First Issue"]))

    assert result.value == 1.0


def test_difficulty_fit_normalizes_hyphenated_labels() -> None:
    profile = _profile(level="intermediate")

    result = difficulty_fit(profile, _repo(), _issue(["good-first-issue"]))

    assert result.value == pytest.approx(0.5)


def test_difficulty_fit_far_apart_is_zero() -> None:
    profile = _profile(level="beginner")

    result = difficulty_fit(profile, _repo(), _issue(["hard"]))

    assert result.value == 0.0


def test_difficulty_fit_is_neutral_without_difficulty_label() -> None:
    result = difficulty_fit(_profile(), _repo(), _issue(["bug"]))

    assert result.value == NEUTRAL


# ---------- issue_activity ----------


def test_issue_activity_is_max_when_everything_is_fresh() -> None:
    issue = _issue(updated_at=_ago(0))
    repo = _repo(pushed_at=_ago(0))

    result = issue_activity(_profile(), repo, issue, now=NOW)

    assert result.value == pytest.approx(1.0)


def test_issue_activity_halves_at_the_half_life() -> None:
    issue = _issue(updated_at=_ago(30))
    repo = _repo(pushed_at=_ago(0))

    result = issue_activity(_profile(), repo, issue, now=NOW)

    assert result.value == pytest.approx(0.7)


def test_issue_activity_is_near_zero_for_very_old_items() -> None:
    issue = _issue(updated_at=_ago(365))
    repo = _repo(pushed_at=_ago(365))

    result = issue_activity(_profile(), repo, issue, now=NOW)

    assert result.value < 0.05


def test_issue_activity_ignores_dates_in_the_future() -> None:
    issue = _issue(updated_at=_ago(-5))
    repo = _repo(pushed_at=_ago(0))

    result = issue_activity(_profile(), repo, issue, now=NOW)

    assert result.value == pytest.approx(1.0)


# ---------- effort_fit ----------


def test_effort_fit_small_issue_fits_easily() -> None:
    result = effort_fit(_profile(weekly_hours=10), _repo(), _issue(["good first issue"]))

    assert result.value == 1.0


def test_effort_fit_without_label_assumes_medium() -> None:
    result = effort_fit(_profile(weekly_hours=10), _repo(), _issue())

    assert result.value == 1.0
    assert "8h" in result.reason


def test_effort_fit_shrinks_when_issue_exceeds_capacity() -> None:
    result = effort_fit(_profile(weekly_hours=5), _repo(), _issue(["hard"]))

    assert result.value == pytest.approx(0.5)


def test_effort_fit_counts_long_discussions_as_extra_effort() -> None:
    result = effort_fit(_profile(weekly_hours=5), _repo(), _issue(comments=10))

    assert result.value == pytest.approx(10 / 13)


# ---------- documentation_quality ----------


def test_documentation_quality_full() -> None:
    repo = _repo(
        description="A toolkit",
        license={"name": "MIT License", "spdx_id": "MIT"},
        topics=["a", "b", "c"],
    )

    result = documentation_quality(_profile(), repo, _issue())

    assert result.value == pytest.approx(1.0)


def test_documentation_quality_nothing_present() -> None:
    result = documentation_quality(_profile(), _repo(), _issue())

    assert result.value == 0.0
    assert "description" in result.reason


def test_documentation_quality_description_only() -> None:
    result = documentation_quality(_profile(), _repo(description="A toolkit"), _issue())

    assert result.value == pytest.approx(0.4)


def test_documentation_quality_blank_description_does_not_count() -> None:
    result = documentation_quality(_profile(), _repo(description="   "), _issue())

    assert result.value == 0.0


# ---------- contribution_friendliness ----------


def test_friendliness_is_zero_for_archived_repo() -> None:
    result = contribution_friendliness(_profile(), _repo(archived=True), _issue(["help wanted"]))

    assert result.value == 0.0


def test_friendliness_is_zero_for_locked_issue() -> None:
    result = contribution_friendliness(_profile(), _repo(), _issue(locked=True))

    assert result.value == 0.0


def test_friendliness_maximum_for_inviting_unassigned_issue() -> None:
    result = contribution_friendliness(_profile(), _repo(), _issue(["help wanted"]))

    assert result.value == pytest.approx(1.0)


def test_friendliness_unassigned_without_invitation() -> None:
    result = contribution_friendliness(_profile(), _repo(), _issue())

    assert result.value == pytest.approx(0.7)


def test_friendliness_drops_when_already_assigned() -> None:
    issue = _issue(assignees=[{"login": "someone"}])

    result = contribution_friendliness(_profile(), _repo(), issue)

    assert result.value == pytest.approx(0.4)
