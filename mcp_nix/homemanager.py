# SPDX-License-Identifier: GPL-3.0-or-later
"""Home Manager option search logic."""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import platformdirs
import requests
import yaml
from lunr import lunr
from lunr.index import Index

from .models import HomeManagerOption, HomeManagerRelease, SearchResult
from .search import APIError, InvalidLimitError

CONFIG_URL = "https://raw.githubusercontent.com/mipmip/home-manager-option-search/main/config.yaml"
OPTIONS_BASE_URL = "https://home-manager-options.extranix.com/data"

CACHE_MAX_AGE_SECONDS = 60 * 60  # 1 hour

# In-memory cache for loaded release data (options + index)
_release_cache: dict[str, "ReleaseData"] = {}


def _get_cache_dir() -> Path:
    """Get the cache directory for Home Manager data."""
    cache_dir = Path(platformdirs.user_cache_dir("mcp-nix")) / "homemanager"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@dataclass
class HomeManagerConfig:
    """Configuration for Home Manager releases."""

    releases: list[dict[str, str]]
    default_release: str

    def to_dict(self) -> dict:
        return {
            "releases": self.releases,
            "default_release": self.default_release,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HomeManagerConfig":
        return cls(
            releases=data["releases"],
            default_release=data["default_release"],
        )


@dataclass
class ReleaseData:
    """Loaded release data with search index."""

    options: list[dict]
    index: Index
    by_title: dict[str, dict] = field(default_factory=dict)


def _load_cached_config() -> HomeManagerConfig | None:
    """Load config from cache if valid (1 hour TTL)."""
    cache_path = _get_cache_dir() / "config.json"
    if not cache_path.exists():
        return None

    try:
        data = json.loads(cache_path.read_text())
        cached_at = data.get("cached_at", 0)
        if time.time() - cached_at > CACHE_MAX_AGE_SECONDS:
            return None
        return HomeManagerConfig.from_dict(data["config"])
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def _save_config_to_cache(config: HomeManagerConfig) -> None:
    """Save config to cache."""
    cache_path = _get_cache_dir() / "config.json"
    data = {
        "cached_at": time.time(),
        "config": config.to_dict(),
    }
    cache_path.write_text(json.dumps(data))


def fetch_config() -> HomeManagerConfig:
    """Fetch and parse Home Manager config from GitHub."""
    try:
        resp = requests.get(CONFIG_URL, timeout=10)
        resp.raise_for_status()
    except requests.Timeout as exc:
        raise APIError("Connection timed out fetching Home Manager config") from exc
    except requests.HTTPError as exc:
        raise APIError(f"Failed to fetch Home Manager config: {exc}") from exc

    try:
        config = yaml.safe_load(resp.text)
        releases = config.get("params", {}).get("releases", [])
        default_release = config.get("params", {}).get("release_current_stable", "master")
        return HomeManagerConfig(releases=releases, default_release=default_release)
    except yaml.YAMLError as exc:
        raise APIError(f"Failed to parse Home Manager config: {exc}") from exc


def get_config() -> HomeManagerConfig:
    """Get Home Manager config, using cache if available."""
    cached = _load_cached_config()
    if cached is not None:
        return cached

    config = fetch_config()
    _save_config_to_cache(config)
    return config


def _is_stable_release(release_value: str) -> bool:
    """Check if a release is stable (not master/unstable)."""
    return release_value.startswith("release-")


def _get_options_cache_path(release_value: str) -> Path:
    """Get the cache path for a specific release's options."""
    safe_name = release_value.replace("/", "-")
    return _get_cache_dir() / f"options-{safe_name}.json"


def _load_cached_options(release_value: str) -> list[dict] | None:
    """Load options from cache if valid.

    Stable releases: cached forever (they don't change).
    Master: cached for 1 hour.
    """
    cache_path = _get_options_cache_path(release_value)
    if not cache_path.exists():
        return None

    try:
        data = json.loads(cache_path.read_text())

        # For stable releases, cache forever
        if _is_stable_release(release_value):
            return data.get("options", [])

        # For master, check TTL
        cached_at = data.get("cached_at", 0)
        if time.time() - cached_at > CACHE_MAX_AGE_SECONDS:
            return None
        return data.get("options", [])
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def _save_options_to_cache(release_value: str, options: list[dict]) -> None:
    """Save options to cache."""
    cache_path = _get_options_cache_path(release_value)
    data = {
        "cached_at": time.time(),
        "options": options,
    }
    cache_path.write_text(json.dumps(data))


def fetch_options(release_value: str) -> list[dict]:
    """Fetch options JSON for a release."""
    url = f"{OPTIONS_BASE_URL}/options-{release_value}.json"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.Timeout as exc:
        raise APIError(f"Connection timed out fetching options for {release_value}") from exc
    except requests.HTTPError as exc:
        raise APIError(f"Failed to fetch options for {release_value}: {exc}") from exc

    try:
        data = resp.json()
        return data.get("options", [])
    except (json.JSONDecodeError, KeyError) as exc:
        raise APIError(f"Failed to parse options for {release_value}: {exc}") from exc


def _build_index(options: list[dict]) -> tuple[Index, dict[str, dict]]:
    """Build a lunr search index from options."""
    by_title = {}

    def doc_gen():
        for i, opt in enumerate(options):
            title = opt.get("title", "")
            by_title[str(i)] = opt
            yield {
                "id": str(i),
                "title": title,
                "description": opt.get("description", "") or "",
            }

    idx = lunr(ref="id", fields=["title", "description"], documents=list(doc_gen()))
    return idx, by_title


def get_release_data(release_value: str) -> ReleaseData:
    """Get release data with search index, using cache."""
    # Check in-memory cache first
    if release_value in _release_cache:
        return _release_cache[release_value]

    # Load options from disk cache or fetch
    cached = _load_cached_options(release_value)
    if cached is not None:
        options = cached
    else:
        options = fetch_options(release_value)
        _save_options_to_cache(release_value, options)

    # Build search index
    idx, by_title = _build_index(options)
    data = ReleaseData(options=options, index=idx, by_title=by_title)

    # Cache in memory
    _release_cache[release_value] = data
    return data


class InvalidReleaseError(APIError):
    """Raised when an invalid release is specified."""

    def __init__(self, release: str, available: list[str]):
        self.release = release
        self.available = available
        super().__init__(f"Invalid release: {release}")


class HomeManagerSearch:
    """Home Manager option search functionality."""

    @staticmethod
    def _get_release_value(release: str) -> str:
        """Get the release value from release name. Raises InvalidReleaseError if invalid."""
        config = get_config()
        # Check if it's already a valid value
        for r in config.releases:
            if r["value"] == release or r["name"] == release:
                return r["value"]
        # Also accept common aliases
        if release == "unstable":
            return "master"
        available = [r["name"] for r in config.releases]
        raise InvalidReleaseError(release, available)

    @staticmethod
    def _validate_limit(limit: int) -> None:
        if not 1 <= limit <= 100:
            raise InvalidLimitError(limit)

    @staticmethod
    def search_options(query: str, limit: int, release: str) -> SearchResult[HomeManagerOption]:
        """Search for Home Manager options using lunr index."""
        HomeManagerSearch._validate_limit(limit)
        release_value = HomeManagerSearch._get_release_value(release)

        data = get_release_data(release_value)
        results = data.index.search(query)
        total = len(results)

        options = []
        for result in results[:limit]:
            opt = data.by_title.get(result["ref"])
            if opt:
                options.append(HomeManagerOption.model_validate(opt))

        return SearchResult(items=options, total=total)

    @staticmethod
    def get_option(name: str, release: str) -> HomeManagerOption | None:
        """Get detailed info about a Home Manager option."""
        release_value = HomeManagerSearch._get_release_value(release)
        data = get_release_data(release_value)

        for opt in data.options:
            if opt.get("title") == name:
                return HomeManagerOption.model_validate(opt)
        return None

    @staticmethod
    def get_option_children(prefix: str, release: str) -> list[HomeManagerOption]:
        """Get all child options under a prefix (e.g., 'programs.git')."""
        release_value = HomeManagerSearch._get_release_value(release)
        data = get_release_data(release_value)
        prefix_dot = f"{prefix}."

        return [
            HomeManagerOption.model_validate(opt) for opt in data.options if opt.get("title", "").startswith(prefix_dot)
        ]

    @staticmethod
    def list_releases() -> list[HomeManagerRelease]:
        """List available Home Manager releases."""
        config = get_config()
        return [
            HomeManagerRelease(
                name=r["name"],
                value=r["value"],
                is_default=r["value"] == config.default_release,
            )
            for r in config.releases
        ]
