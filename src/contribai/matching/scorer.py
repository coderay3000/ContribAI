import re

from contribai.schemas.github import Issue, Repository
from contribai.schemas.matching import FactorScore
from contribai.schemas.profile import DeveloperProfile, ExperienceLevel, Skill

NEUTRAL = 0.5
_EVIDENCE_FULL_TRUST = 5
_TOPIC_BOOST = 0.5

_EXPERIENCE_RANK = {
    ExperienceLevel.BEGINNER: 1,
    ExperienceLevel.INTERMEDIATE: 2,
    ExperienceLevel.ADVANCED: 3,
}
_RANK_NAME = {rank: level.value for level, rank in _EXPERIENCE_RANK.items()}

_LABEL_DIFFICULTY = {
    "good first issue": 1,
    "first timers only": 1,
    "beginner": 1,
    "easy": 1,
    "starter": 1,
    "intermediate": 2,
    "medium": 2,
    "advanced": 3,
    "hard": 3,
    "difficult": 3,
    "complex": 3,
}


def _normalize(text: str) -> str:
    return re.sub(r"[-_\s]+", " ", text.strip().lower())


def _factor(value: float, reason: str) -> FactorScore:
    return FactorScore(value=min(1.0, max(0.0, value)), reason=reason)


def _effective_level(skill: Skill) -> float:
    confidence = 0.5 + 0.5 * min(skill.evidence_count / _EVIDENCE_FULL_TRUST, 1.0)
    return skill.level / 10 * confidence


def skill_match(profile: DeveloperProfile, repo: Repository, issue: Issue) -> FactorScore:
    skills = {_normalize(skill.name): skill for skill in profile.skills}
    reasons: list[str] = []

    language_score: float | None = None
    if repo.language:
        skill = skills.get(_normalize(repo.language))
        if skill is None:
            language_score = 0.0
            reasons.append(f"you have no {repo.language} skill listed")
        else:
            language_score = _effective_level(skill)
            reasons.append(
                f"language {repo.language} matches your skill "
                f"(level {skill.level:g}/10, {skill.evidence_count} evidence)"
            )

    matched = [topic for topic in repo.topics if _normalize(topic) in skills]
    topic_score = max(
        (_effective_level(skills[_normalize(topic)]) for topic in matched), default=0.0
    )
    if matched:
        reasons.append("topic match: " + ", ".join(matched))

    if language_score is None:
        value = topic_score
    else:
        value = language_score + (1 - language_score) * topic_score * _TOPIC_BOOST
    return _factor(value, "; ".join(reasons) or "no skill overlap with this repository")


def domain_match(profile: DeveloperProfile, repo: Repository, issue: Issue) -> FactorScore:
    if not profile.preferred_domains:
        return _factor(NEUTRAL, "no preferred domains set, so this factor is neutral")

    topics = {_normalize(topic) for topic in repo.topics}
    description = _normalize(repo.description or "")

    matched: list[str] = []
    for domain in profile.preferred_domains:
        key = _normalize(domain)
        in_description = re.search(rf"\b{re.escape(key)}\b", description) is not None
        if key in topics or in_description:
            matched.append(domain)

    value = len(matched) / len(profile.preferred_domains)
    if matched:
        reason = "matches your preferred domains: " + ", ".join(matched)
    else:
        reason = "none of your preferred domains appear in this repo's topics or description"
    return _factor(value, reason)


def difficulty_fit(profile: DeveloperProfile, repo: Repository, issue: Issue) -> FactorScore:
    ranks: list[int] = []
    for label in issue.labels:
        rank = _LABEL_DIFFICULTY.get(_normalize(label.name))
        if rank is not None:
            ranks.append(rank)

    if not ranks:
        return _factor(NEUTRAL, "no difficulty label on the issue, so this factor is neutral")

    issue_rank = max(ranks)
    developer_rank = _EXPERIENCE_RANK[profile.experience_level]
    value = 1 - abs(issue_rank - developer_rank) / 2
    reason = (
        f"issue looks {_RANK_NAME[issue_rank]} (from its labels), "
        f"you are {profile.experience_level.value}"
    )
    return _factor(value, reason)
