"""Generic text cleaning and normalisation utilities for HTML and sports content."""
from __future__ import annotations

import html
import re

_BLOCK_BREAK_RE = re.compile(r'</?(p|div|br|li|ul|ol|h[1-6]|blockquote)[^>]*>', re.IGNORECASE)
_TAG_RE = re.compile(r'<[^>]+>')
_WHITESPACE_RE = re.compile(r'[ \t\f\v]+')
_PROMO_LINE_RE = re.compile(
    r'(?i)(live scores|table|top scorers|follow us on\s+\w+|continue reading\.{0,3})'
)


def strip_source_artifacts(text: str) -> str:
    normalized = text
    normalized = normalized.replace('⚽', '\n\n')
    normalized = normalized.replace('|', '\n')
    normalized = re.sub(r'\.(\s*)\[', '.\n\n[', normalized)
    normalized = re.sub(r'(?<!\n)\s*(\[[^\]]+\])', '\n\n\\1', normalized)
    normalized = re.sub(r'(?<=[a-z])(?=[A-Z][a-z]+\s[A-Z])', '\n\n', normalized)
    normalized = re.sub(r'(?i)\bcontinue reading\.{0,3}\b', '', normalized)
    lines = [line.strip() for line in normalized.split('\n')]
    kept_lines = [line for line in lines if line and not _PROMO_LINE_RE.fullmatch(line)]
    return '\n'.join(kept_lines)


def clean_html_text(value: str | None) -> str:
    if not value:
        return ''
    text = html.unescape(value)
    text = text.replace('\xa0', ' ')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = _BLOCK_BREAK_RE.sub('\n\n', text)
    text = _TAG_RE.sub(' ', text)
    text = strip_source_artifacts(text)
    text = _WHITESPACE_RE.sub(' ', text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    return text.strip()


def normalize_for_compare(value: str) -> str:
    lowered = value.casefold()
    lowered = re.sub(r'\s+', ' ', lowered)
    return lowered.strip(' .,!?:;"\'()[]{}')


def dedupe_paragraphs(value: str) -> str:
    paragraphs = [segment.strip() for segment in re.split(r'\n{2,}', value) if segment.strip()]
    if len(paragraphs) <= 1 and '\n' in value:
        paragraphs = [segment.strip() for segment in value.split('\n') if segment.strip()]
    deduped: list[str] = []
    seen: set[str] = set()
    for paragraph in paragraphs:
        key = normalize_for_compare(paragraph)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(paragraph)
    return '\n\n'.join(deduped)
