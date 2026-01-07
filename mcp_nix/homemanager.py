# SPDX-License-Identifier: GPL-3.0-or-later
"""Home Manager option search logic."""

from dataclasses import dataclass, field

from lunr import lunr
from lunr.index import Index

from .cache import DEFAULT_EXPIRE, get_cache
from .models import HomeManagerOption, HomeManagerRelease, SearchResult
from .search import APIError, InvalidLimitError

CONFIG_URL = "https://raw.githubusercontent.com/mipmip/home-manager-option-search/main/config.yaml"
OPTIONS_BASE_URL = "https://home-manager-options.extranix.com/data"

_cache = get_cache("homemanager")

# In-memory cache for loaded release data (lunr Index can't be serialized)
_release_cache: dict[str, "ReleaseData"] = {}


@dataclass
class HomeManagerConfig:
    """Configuration for Home Manager releases."""

    releases: list[dict[str, str]]
    default_release: str


@dataclass
class ReleaseData:
    """Loaded release data with search index."""

    options: list[dict]
    index: Index
    by_title: dict[str, dict] = field(default_factory=dict)


def get_config() -> HomeManagerConfig:
    """Get Home Manager config, using cache if available."""

    def parse_config(r) -> HomeManagerConfig:
        config = r.yaml()
        releases = config.get("params", {}).get("releases", [])
        default_release = config.get("params", {}).get("release_current_stable", "master")
        return HomeManagerConfig(releases=releases, default_release=default_release)

    return _cache.request(CONFIG_URL, parse_config)


def _is_stable_release(release_value: str) -> bool:
    """Check if a release is stable (not master/unstable)."""
    return release_value.startswith("release-")


def _get_options(release_value: str) -> list[dict]:
    """Get options for a release, using cache if available."""
    url = f"{OPTIONS_BASE_URL}/options-{release_value}.json"
    # Stable releases cached forever, master for 1 hour
    expire = None if _is_stable_release(release_value) else DEFAULT_EXPIRE
    return _cache.request(url, lambda r: r.json().get("options", []), expire=expire)


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
    # Check in-memory cache first (lunr Index can't be serialized)
    if release_value in _release_cache:
        return _release_cache[release_value]

    options = _get_options(release_value)
    idx, by_title = _build_index(options)
    data = ReleaseData(options=options, index=idx, by_title=by_title)

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
