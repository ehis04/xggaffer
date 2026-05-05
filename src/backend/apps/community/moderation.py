import re

from .models import BannedWord


def get_matching_banned_words(text: str) -> list[str]:
    body = (text or "").lower()
    if not body:
        return []

    matches: list[str] = []
    for term in BannedWord.objects.filter(is_active=True).values_list("term", flat=True):
        normalized = term.strip().lower()
        if not normalized:
            continue

        if " " in normalized:
            matched = normalized in body
        else:
            matched = re.search(rf"(?<!\w){re.escape(normalized)}(?!\w)", body) is not None

        if matched:
            matches.append(term)

    return matches


def body_requires_review(text: str) -> bool:
    return bool(get_matching_banned_words(text))
