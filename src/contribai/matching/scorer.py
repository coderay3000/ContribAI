import re
from datetime import UTC, datetime

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

_ISSUE_HALF_LIFE_DAYS = 30
_REPO_HALF_LIFE_DAYS = 60
_ISSUE_ACTIVITY_SHARE = 0.6

_BASE_HOURS = {1: 3.0, 2: 8.0, 3: 20.0}
_DEFAULT_RANK = 2
_HOURS_PER_COMMENT = 0.5
_MAX_COUNTED_COMMENTS = 10
_PLANNING_WEEKS = 2

_DOC_DESCRIPTION_SHARE = 0.4
_DOC_LICENSE_SHARE = 0.3
_DOC_TOPICS_SHARE = 0.3
_DOC_TOPICS_FULL = 3

_FRIENDLY_BASE = 0.4
_FRIENDLY_LABEL_BONUS = 0.3
_FRIENDLY_UNASSIGNED_BONUS = 0.3
_INVITING_LABELS = {
    "help wanted",
    "good first issue",
    "first timers only",
    "contributions welcome",
    "up for grabs",
}


def _normalize(text: str) -> str:
    return re.sub(r"[-_\s]+", " ", text.strip().lower())


def _factor(value: float, reason: str) -> FactorScore:
    return FactorScore(value=min(1.0, max(0.0, value)), reason=reason)


def _effective_level(skill: Skill) -> float:
    confidence = 0.5 + 0.5 * min(skill.evidence_count / _EVIDENCE_FULL_TRUST, 1.0)
    return skill.level / 10 * confidence


def _difficulty_rank(issue: Issue) -> int | None:
    ranks: list[int] = []
    for label in issue.labels:
        rank = _LABEL_DIFFICULTY.get(_normalize(label.name))
        if rank is not None:
            ranks.append(rank)
    return max(ranks) if ranks else None


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
    issue_rank = _difficulty_rank(issue)
    if issue_rank is None:
        return _factor(NEUTRAL, "no difficulty label on the issue, so this factor is neutral")

    developer_rank = _EXPERIENCE_RANK[profile.experience_level]
    value = 1 - abs(issue_rank - developer_rank) / 2
    reason = (
        f"issue looks {_RANK_NAME[issue_rank]} (from its labels), "
        f"you are {profile.experience_level.value}"
    )
    return _factor(value, reason)


def _age_days(moment: datetime, now: datetime) -> float:
    return max(0.0, (now - moment).total_seconds() / 86400)


def _freshness(age_days: float, half_life_days: float) -> float:
    return 0.5 ** (age_days / half_life_days)


def issue_activity(
    profile: DeveloperProfile,
    repo: Repository,
    issue: Issue,
    *,
    now: datetime | None = None,
) -> FactorScore:
    if now is None:
        now = datetime.now(UTC)

    issue_age = _age_days(issue.updated_at, now)
    repo_age = _age_days(repo.pushed_at, now)
    value = _ISSUE_ACTIVITY_SHARE * _freshness(issue_age, _ISSUE_HALF_LIFE_DAYS) + (
        1 - _ISSUE_ACTIVITY_SHARE
    ) * _freshness(repo_age, _REPO_HALF_LIFE_DAYS)
    reason = f"issue updated {issue_age:.0f} days ago, repo last pushed {repo_age:.0f} days ago"
    return _factor(value, reason)


def effort_fit(profile: DeveloperProfile, repo: Repository, issue: Issue) -> FactorScore:
    rank = _difficulty_rank(issue)
    if rank is None:
        rank = _DEFAULT_RANK

    discussion_hours = min(issue.comments, _MAX_COUNTED_COMMENTS) * _HOURS_PER_COMMENT
    estimated_hours = _BASE_HOURS[rank] + discussion_hours
    capacity_hours = profile.weekly_hours * _PLANNING_WEEKS

    value = 1.0 if estimated_hours <= capacity_hours else capacity_hours / estimated_hours
    reason = (
        f"rough estimate {estimated_hours:g}h vs your capacity of "
        f"{capacity_hours}h over {_PLANNING_WEEKS} weeks"
    )
    return _factor(value, reason)


def documentation_quality(profile: DeveloperProfile, repo: Repository, issue: Issue) -> FactorScore:
    value = 0.0
    weak: list[str] = []

    if repo.description and repo.description.strip():
        value += _DOC_DESCRIPTION_SHARE
    else:
        weak.append("description")

    if repo.license is not None:
        value += _DOC_LICENSE_SHARE
    else:
        weak.append("license")

    topics_part = min(len(repo.topics) / _DOC_TOPICS_FULL, 1.0)
    value += _DOC_TOPICS_SHARE * topics_part
    if topics_part < 1.0:
        weak.append("topics")

    reason = (
        "description, license and topics all present"
        if not weak
        else ("missing or thin: " + ", ".join(weak))
    )
    return _factor(value, reason)


def contribution_friendliness(
    profile: DeveloperProfile, repo: Repository, issue: Issue
) -> FactorScore:
    if repo.archived:
        return _factor(0.0, "repository is archived, nothing can be contributed")
    if issue.locked:
        return _factor(0.0, "issue is locked, only maintainers can comment")

    value = _FRIENDLY_BASE
    reasons: list[str] = []

    inviting = [label.name for label in issue.labels if _normalize(label.name) in _INVITING_LABELS]
    if inviting:
        value += _FRIENDLY_LABEL_BONUS
        reasons.append("invites contributors via label: " + ", ".join(inviting))

    if issue.assignees:
        reasons.append("already assigned to someone")
    else:
        value += _FRIENDLY_UNASSIGNED_BONUS
        reasons.append("nobody is assigned")

    return _factor(value, "; ".join(reasons))
