from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExperienceLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Skill(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    level: float = Field(ge=0, le=10)
    evidence_count: int = Field(default=0, ge=0)


class DeveloperProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    skills: list[Skill]
    preferred_domains: list[str] = Field(default_factory=list)
    experience_level: ExperienceLevel
    weekly_hours: int = Field(gt=0, le=80)

    @model_validator(mode="after")
    def skill_names_unique(self) -> Self:
        names = [skill.name.lower() for skill in self.skills]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate skill names in profile")
        return self
