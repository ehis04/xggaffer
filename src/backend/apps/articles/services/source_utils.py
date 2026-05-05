"""
Cleans and validates external article source URLs

Normalises site domains, checks whether article URLs belong to the same source family, and removes tracking parameters from stored links
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from django.utils.text import slugify


# ---------------------------------------------------------------------------
# URL cleaning configuration
# ---------------------------------------------------------------------------

BLOCKED_URL_TOKENS = (
    'zclkvisitor',
    'campaignid=',
    'clickid=',
    'utm_',
)

TRACKING_QUERY_KEYS = {
    'campaignid',
    'clickid',
    'zclkvisitor',
}


# ---------------------------------------------------------------------------
# URL helper functions
# ---------------------------------------------------------------------------

# Extract the hostname from a URL or domain value
def _host(value: str | None) -> str:
    if not value:
        return ''

    parsed = urlparse(value)
    if parsed.hostname:
        return parsed.hostname.lower()

    cleaned = value.replace('http://', '').replace('https://', '').strip('/').split('/')[0]
    return cleaned.split(':', 1)[0].lower()


# Check whether an article URL belongs to the same source family as a site
def same_source_family(url_value: str, site_domain: str) -> bool:
    article_host = _host(url_value)
    site_host = _host(site_domain)
    if not article_host or not site_host:
        return False
    return (
        article_host == site_host
        or article_host.endswith(f'.{site_host}')
        or site_host.endswith(f'.{article_host}')
    )


# Normalise a stored site domain into a safe HTTPS domain
def normalize_site_domain(domain: str | None, site_name: str | None = None) -> str:
    host = _host(domain)
    if host and '.local' not in host:
        return f'https://{host}'

    if site_name:
        return f'https://www.{slugify(site_name)}.com'

    return ''


# Check whether a query parameter is used for tracking
def _is_tracking_key(key: str) -> bool:
    lowered = key.lower()
    return lowered.startswith('utm_') or lowered in TRACKING_QUERY_KEYS


# Sanitize an external article URL before saving it
def sanitize_external_url(
    value: str | None,
    *,
    site_domain: str | None = None,
    enforce_same_family: bool = False,
) -> str | None:
    if not value:
        return None

    try:
        parsed = urlparse(value)
    except Exception:
        return None

    if not (parsed.scheme in {'http', 'https'} and bool(parsed.netloc) and '.local' not in parsed.netloc.lower()):
        return None

    filtered_params = [
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if not _is_tracking_key(key)
    ]

    cleaned = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        '',
        urlencode(filtered_params, doseq=True),
        '',
    ))

    lowered = cleaned.lower()
    if any(token in lowered for token in BLOCKED_URL_TOKENS):
        return None

    if enforce_same_family and site_domain and not same_source_family(cleaned, site_domain):
        return None

    return cleaned