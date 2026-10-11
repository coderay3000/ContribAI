import re

_FULL_NAME_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


def validate_full_name(full_name: str) -> None:
    parts = full_name.split("/")
    if not _FULL_NAME_RE.fullmatch(full_name) or any(p in (".", "..") for p in parts):
        raise ValueError(f"Invalid repository name: {full_name!r}")
