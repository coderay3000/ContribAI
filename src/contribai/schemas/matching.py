from pydantic import BaseModel, ConfigDict, Field


class FactorScore(BaseModel):
    """One factor's verdict: a 0..1 value and a human-readable reason."""

    model_config = ConfigDict(frozen=True)

    value: float = Field(ge=0, le=1)
    reason: str
