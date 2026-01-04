# SPDX-License-Identifier: GPL-3.0-or-later
"""Nixhub.io API integration for package version lookup."""

import json
import time
from pathlib import Path

import platformdirs
import requests

from .models import NixhubCommit, NixhubRelease
from .search import APIError

NIXHUB_API_URL = "https://www.nixhub.io/packages"
CACHE_MAX_AGE_SECONDS = 60 * 60  # 1 hour

# In-memory cache for loaded package data
_package_cache: dict[str, dict] = {}


class PackageNotFoundError(APIError):
    """Raised when package is not found on nixhub."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Package '{name}' not found")


class VersionNotFoundError(APIError):
    """Raised when version is not found for a package."""

    def __init__(self, name: str, version: str, available: list[str]):
        self.name = name
        self.version = version
        self.available = available
        super().__init__(f"Version '{version}' not found for '{name}'")


def _get_cache_dir() -> Path:
    """Get the cache directory for Nixhub data."""
    cache_dir = Path(platformdirs.user_cache_dir("mcp-nix")) / "nixhub"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _load_cached_package(name: str) -> dict | None:
    """Load package data from cache if valid (1 hour TTL)."""
    # Check in-memory cache first
    if name in _package_cache:
        data = _package_cache[name]
        if time.time() - data.get("cached_at", 0) <= CACHE_MAX_AGE_SECONDS:
            return data["package"]

    # Check disk cache
    cache_path = _get_cache_dir() / f"{name}.json"
    if not cache_path.exists():
        return None

    try:
        data = json.loads(cache_path.read_text())
        cached_at = data.get("cached_at", 0)
        if time.time() - cached_at > CACHE_MAX_AGE_SECONDS:
            return None
        # Store in memory cache
        _package_cache[name] = data
        return data["package"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def _save_package_to_cache(name: str, package_data: dict) -> None:
    """Save package data to cache."""
    cache_path = _get_cache_dir() / f"{name}.json"
    data = {
        "cached_at": time.time(),
        "package": package_data,
    }
    cache_path.write_text(json.dumps(data))
    # Also store in memory cache
    _package_cache[name] = data


def fetch_package(name: str) -> dict:
    """Fetch package data from Nixhub API or cache."""
    # Try cache first
    cached = _load_cached_package(name)
    if cached is not None:
        return cached

    # Fetch from API
    url = f"{NIXHUB_API_URL}/{name}?_data=routes/_nixhub.packages.$pkg._index"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 404:
            raise PackageNotFoundError(name)
        resp.raise_for_status()
    except requests.Timeout as exc:
        raise APIError("Connection timed out fetching package from Nixhub") from exc
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            raise PackageNotFoundError(name) from exc
        raise APIError(f"Failed to fetch package from Nixhub: {exc}") from exc

    try:
        data = resp.json()
    except json.JSONDecodeError as exc:
        raise APIError("Invalid JSON response from Nixhub") from exc

    # Check if package exists
    if not data or "releases" not in data:
        raise PackageNotFoundError(name)

    # Cache and return
    _save_package_to_cache(name, data)
    return data


class NixhubSearch:
    """Nixhub API search functionality."""

    @staticmethod
    def get_versions(name: str) -> list[NixhubRelease]:
        """Get all available versions for a package."""
        data = fetch_package(name)
        releases = data.get("releases", [])
        return [NixhubRelease.model_validate(r) for r in releases]

    @staticmethod
    def get_commit(name: str, version: str) -> NixhubCommit:
        """Get the nixpkgs commit hash for a specific package version."""
        data = fetch_package(name)
        releases = data.get("releases", [])

        # Find the matching version
        for release in releases:
            if release.get("version") == version:
                platforms = release.get("platforms", [])
                if platforms:
                    # Return the first platform's commit info
                    platform = platforms[0]
                    return NixhubCommit(
                        name=name,
                        version=version,
                        attribute_path=platform.get("attribute_path", ""),
                        commit_hash=platform.get("commit_hash", ""),
                    )

        # Version not found - provide available versions
        available = [r.get("version", "") for r in releases if r.get("version")]
        raise VersionNotFoundError(name, version, available)
