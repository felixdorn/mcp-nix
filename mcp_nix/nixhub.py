# SPDX-License-Identifier: GPL-3.0-or-later
"""Nixhub.io API integration for package version lookup."""

import json

import requests

from .cache import get_cache, get_or_set
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

    def fetch() -> dict:
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

        if not data or "releases" not in data:
            raise PackageNotFoundError(name)

        return data

    return get_or_set(_cache, f"package:{name}", fetch)


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
