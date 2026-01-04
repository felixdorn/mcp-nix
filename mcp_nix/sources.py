# SPDX-License-Identifier: GPL-3.0-or-later
"""Source code fetching and caching for declarations."""

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path

import platformdirs
import requests

from .search import APIError

CACHE_MAX_AGE_SECONDS = 60 * 60  # 1 hour


def _get_cache_dir() -> Path:
    """Get the cache directory for source files."""
    cache_dir = Path(platformdirs.user_cache_dir("mcp-nix")) / "sources"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _url_to_cache_key(url: str) -> str:
    """Convert a URL to a cache-safe filename."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


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


def _load_cached_source(url: str) -> CachedSource | None:
    """Load source from cache if valid (1 hour TTL)."""
    cache_dir = _get_cache_dir()
    cache_key = _url_to_cache_key(url)
    meta_path = cache_dir / f"{cache_key}.json"
    content_path = cache_dir / f"{cache_key}.txt"

    if not meta_path.exists() or not content_path.exists():
        return None

    try:
        meta = json.loads(meta_path.read_text())
        cached_at = meta.get("cached_at", 0)
        if time.time() - cached_at > CACHE_MAX_AGE_SECONDS:
            return None

        content = content_path.read_text()
        return CachedSource(
            content=content,
            line_count=meta.get("line_count", content.count("\n") + 1),
            url=url,
        )
    except (OSError, json.JSONDecodeError):
        return None


def _save_source_to_cache(url: str, content: str) -> None:
    """Save source to cache."""
    cache_dir = _get_cache_dir()
    cache_key = _url_to_cache_key(url)
    meta_path = cache_dir / f"{cache_key}.json"
    content_path = cache_dir / f"{cache_key}.txt"

    line_count = content.count("\n") + 1 if content else 0
    meta = {
        "cached_at": time.time(),
        "url": url,
        "line_count": line_count,
    }
    meta_path.write_text(json.dumps(meta))
    content_path.write_text(content)


def fetch_source(url: str) -> CachedSource:
    """Fetch source code from URL, using cache if available."""
    if not url:
        raise APIError("No URL provided")

    # Convert to raw URL if needed
    raw_url = to_raw_url(url)

    # Check cache first
    cached = _load_cached_source(raw_url)
    if cached is not None:
        return cached

    # Fetch from network
    try:
        resp = requests.get(raw_url, timeout=30)
        resp.raise_for_status()

        # Only accept text/plain (what GitHub/GitLab use for raw files)
        content_type = resp.headers.get("content-type", "").lower()
        if "text/plain" not in content_type:
            raise APIError(f"Unexpected content type '{content_type}' from {raw_url}")

        content = resp.text
    except requests.Timeout as e:
        raise APIError(f"Connection timed out fetching {raw_url}") from e
    except requests.HTTPError as e:
        raise APIError(f"Failed to fetch source: {e}") from e

    # Cache the result
    _save_source_to_cache(raw_url, content)

    line_count = content.count("\n") + 1 if content else 0
    return CachedSource(content=content, line_count=line_count, url=url)


def get_line_count(url: str) -> int | None:
    """Get line count for a source URL, fetching and caching if needed."""
    if not url:
        return None

    try:
        source = fetch_source(url)
        return source.line_count
    except APIError:
        return None
