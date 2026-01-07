# SPDX-License-Identifier: GPL-3.0-or-later
"""Source code fetching and caching for declarations."""

from dataclasses import dataclass

import requests

from .cache import get_cache, get_or_set
from .search import APIError

_cache = get_cache("sources")


def to_raw_url(url: str) -> str:
    """Convert a GitHub or GitLab blob URL to a raw URL."""
    if not url:
        return url
    # GitHub: https://github.com/owner/repo/blob/branch/path -> https://raw.githubusercontent.com/owner/repo/branch/path
    if "github.com" in url and "/blob/" in url:
        return url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    # GitLab: https://gitlab.com/owner/repo/-/blob/branch/path -> https://gitlab.com/owner/repo/-/raw/branch/path
    if "gitlab.com" in url and "/-/blob/" in url:
        return url.replace("/-/blob/", "/-/raw/")
    return url


@dataclass
class CachedSource:
    """Cached source file with metadata."""

    content: str
    line_count: int
    url: str


def fetch_source(url: str) -> CachedSource:
    """Fetch source code from URL, using cache if available."""
    if not url:
        raise APIError("No URL provided")

    raw_url = to_raw_url(url)

    def fetch() -> CachedSource:
        try:
            resp = requests.get(raw_url, timeout=30)
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "").lower()
            if "text/plain" not in content_type:
                raise APIError(f"Unexpected content type '{content_type}' from {raw_url}")

            content = resp.text
        except requests.Timeout as e:
            raise APIError(f"Connection timed out fetching {raw_url}") from e
        except requests.HTTPError as e:
            raise APIError(f"Failed to fetch source: {e}") from e

        line_count = content.count("\n") + 1 if content else 0
        return CachedSource(content=content, line_count=line_count, url=url)

    return get_or_set(_cache, raw_url, fetch)


def get_line_count(url: str) -> int | None:
    """Get line count for a source URL, fetching and caching if needed."""
    if not url:
        return None

    try:
        source = fetch_source(url)
        return source.line_count
    except APIError:
        return None
