import pytest
from pydantic import ValidationError

from contribai.matching.weights import Weights


def test_default_weights_sum_to_one() -> None:
    weights = Weights()

    assert sum(weights.model_dump().values()) == pytest.approx(1.0)


def test_weights_that_do_not_sum_to_one_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Weights(skill_match=0.5)


def test_negative_weight_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Weights(skill_match=-0.1, difficulty_fit=0.6)


def test_custom_weights_that_sum_to_one_are_accepted() -> None:
    weights = Weights(
        skill_match=0.40,
        difficulty_fit=0.20,
        domain_match=0.05,
        effort_fit=0.10,
        issue_activity=0.10,
        documentation_quality=0.10,
        contribution_friendliness=0.05,
    )

    assert weights.skill_match == 0.40


def test_weights_are_immutable() -> None:
    weights = Weights()

    with pytest.raises(ValidationError):
        weights.skill_match = 0.9  # type: ignore[misc]
