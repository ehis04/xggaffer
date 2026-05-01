"""Helpers for resolving Understat team page slugs."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import unquote, urlparse


KNOWN_UNDERSTAT_TEAM_SLUGS = {
    "Manchester_United",
    "Real_Madrid",
    "Bayern_Munich",
    "Juventus",
    "Paris_Saint_Germain",
}

_TEAM_SLUG_ALIASES = {
    "man utd": "Manchester_United",
    "man united": "Manchester_United",
    "manchester united": "Manchester_United",
    "manchester united fc": "Manchester_United",
    "real madrid": "Real_Madrid",
    "real madrid cf": "Real_Madrid",
    "bayern": "Bayern_Munich",
    "bayern munich": "Bayern_Munich",
    "fc bayern": "Bayern_Munich",
    "fc bayern munchen": "Bayern_Munich",
    "juventus": "Juventus",
    "juventus fc": "Juventus",
    "psg": "Paris_Saint_Germain",
    "paris sg": "Paris_Saint_Germain",
    "paris saint germain": "Paris_Saint_Germain",
    "paris saint-germain": "Paris_Saint_Germain",
    "paris saint germain fc": "Paris_Saint_Germain",
}


def _extract_team_slug_candidate(value: str) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return ""

    parsed = urlparse(candidate)
    if parsed.netloc and parsed.path:
        parts = [unquote(part) for part in parsed.path.split("/") if part]
        try:
            team_index = parts.index("team")
        except ValueError:
            return candidate

        if team_index + 1 < len(parts):
            return parts[team_index + 1].strip()

    return candidate


def _normalise_alias(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("_", " ").replace("-", " ")
    value = re.sub(r"[^A-Za-z0-9 ]+", " ", value)
    return " ".join(value.casefold().split())


def _titlecase_slug(value: str) -> str:
    parts = [part for part in re.split(r"[\s_-]+", value.strip()) if part]
    if not parts:
        return ""

    return "_".join(part[:1].upper() + part[1:].lower() for part in parts)


def canonicalise_understat_team_slug(value: str | None) -> str:
    """Return the Understat team slug expected by /team/{slug}/{season} URLs."""

    candidate = _extract_team_slug_candidate(str(value or ""))
    if not candidate:
        return ""

    if candidate in KNOWN_UNDERSTAT_TEAM_SLUGS:
        return candidate

    alias = _normalise_alias(candidate)
    resolved = _TEAM_SLUG_ALIASES.get(alias)
    if resolved:
        return resolved

    if re.search(r"[\s-]", candidate) or ("_" in candidate and candidate == candidate.casefold()):
        return _titlecase_slug(candidate)

    return candidate
