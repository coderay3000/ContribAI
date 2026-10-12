from typing import Any

import pytest
from pydantic import ValidationError

from contribai.schemas.profile import DeveloperProfile, ExperienceLevel


def _profile_data() -> dict[str, Any]:
    return {
        "username": "dev",
        "skills": [
            {"name": "Python", "level": 7.0, "evidence_count": 12},
            {"name": "FastAPI", "level": 6.0, "evidence_count": 3},
        ],
        "preferred_domains": ["ai", "mlops"],
        "experience_level": "intermediate",
        "weekly_hours": 10,
    }


def test_valid_profile_is_parsed() -> None:
    profile = DeveloperProfile.model_validate(_profile_data())

    assert profile.skills[0].name == "Python"
    assert profile.experience_level is ExperienceLevel.INTERMEDIATE


def test_skill_level_above_10_is_rejected() -> None:
    data = _profile_data()
    data["skills"][0]["level"] = 11

    with pytest.raises(ValidationError):
        DeveloperProfile.model_validate(data)


def test_duplicate_skill_names_are_rejected() -> None:
    data = _profile_data()
    data["skills"].append({"name": "python", "level": 5.0})

    with pytest.raises(ValidationError):
        DeveloperProfile.model_validate(data)


def test_unknown_experience_level_is_rejected() -> None:
    data = _profile_data()
    data["experience_level"] = "expert"

    with pytest.raises(ValidationError):
        DeveloperProfile.model_validate(data)


def test_unknown_field_is_rejected() -> None:
    data = _profile_data()
    data["skils"] = []

    with pytest.raises(ValidationError):
        DeveloperProfile.model_validate(data)
