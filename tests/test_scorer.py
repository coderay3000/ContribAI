from typing import Any

import pytest

from contribai.matching.scorer import NEUTRAL, difficulty_fit, domain_match, skill_match
from contribai.schemas.github import Issue, Repository
from contribai.schemas.profile import DeveloperProfile


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


def _issue(labels: list[str] | None = None) -> Issue:
    return Issue.model_validate(
        {
            "number": 1,
            "title": "t",
            "state": "open",
            "html_url": "https://github.com/o/r/issues/1",
            "created_at": "2026-10-01T00:00:00Z",
            "updated_at": "2026-10-02T00:00:00Z",
            "labels": [{"name": name} for name in labels or []],
        }
    )


def _profile(
    skills: list[dict[str, Any]] | None = None,
    domains: list[str] | None = None,
    level: str = "intermediate",
) -> DeveloperProfile:
    return DeveloperProfile.model_validate(
        {
            "username": "dev",
            "skills": skills or [],
            "preferred_domains": domains or [],
            "experience_level": level,
            "weekly_hours": 10,
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
