import math
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Weights(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    skill_match: float = Field(default=0.30, ge=0, le=1)
    difficulty_fit: float = Field(default=0.20, ge=0, le=1)
    domain_match: float = Field(default=0.15, ge=0, le=1)
    effort_fit: float = Field(default=0.10, ge=0, le=1)
    issue_activity: float = Field(default=0.10, ge=0, le=1)
    documentation_quality: float = Field(default=0.10, ge=0, le=1)
    contribution_friendliness: float = Field(default=0.05, ge=0, le=1)

    @model_validator(mode="after")
    def must_sum_to_one(self) -> Self:
        total = sum(self.model_dump().values())
        if not math.isclose(total, 1.0, abs_tol=1e-9):
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        return self
