# SPDX-License-Identifier: GPL-3.0-or-later
"""Nixhub.io API integration for package version lookup."""

from .cache import get_cache
from .models import NixhubCommit, NixhubRelease
from .search import APIError

NIXHUB_API_URL = "https://www.nixhub.io/packages"

_cache = get_cache("nixhub")


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


def fetch_package(name: str) -> dict:
    """Fetch package data from Nixhub API or cache."""
    url = f"{NIXHUB_API_URL}/{name}?_data=routes/_nixhub.packages.$pkg._index"

    def parse_package(r) -> dict:
        data = r.json()
        if not data or "releases" not in data:
            raise PackageNotFoundError(name)
        return data

    try:
        return _cache.request(url, parse_package)
    except APIError as e:
        if "404" in str(e):
            raise PackageNotFoundError(name) from e
        raise


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
