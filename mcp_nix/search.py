# SPDX-License-Identifier: GPL-3.0-or-later
"""NixOS package and option search logic."""

import json
import re
from dataclasses import dataclass
from typing import Any

import requests

from .cache import APIError, get_cache
from .models import Channel, Option, Package, SearchResult

_cache = get_cache("search")


# Re-export for backward compatibility
__all__ = ["APIError", "InvalidChannelError", "InvalidLimitError", "NixOSSearch"]


@dataclass
class ElasticsearchConfig:
    """Configuration extracted from bundle.js."""

    schema_version: int
    url: str
    username: str
    password: str
    channels: list[dict[str, str]]
    default_channel: str


def get_config() -> ElasticsearchConfig:
    """Get Elasticsearch config, using cache if available."""

    def parse_bundle(r) -> ElasticsearchConfig:
        bundle = r.text

        schema_match = re.search(r'elasticsearchMappingSchemaVersion:parseInt\("(\d+)"\)', bundle)
        url_match = re.search(r'elasticsearchUrl:"([^"]+)"', bundle)
        username_match = re.search(r'elasticsearchUsername:"([^"]+)"', bundle)
        password_match = re.search(r'elasticsearchPassword:"([^"]+)"', bundle)
        channels_match = re.search(r"nixosChannels:JSON\.parse\('([^']+)'\)", bundle)

        if not all([schema_match, url_match, username_match, password_match, channels_match]):
            raise APIError("Failed to extract credentials from search.nixos.org.")

        assert schema_match and url_match and username_match and password_match and channels_match
        channels_data = json.loads(channels_match.group(1))

        return ElasticsearchConfig(
            schema_version=int(schema_match.group(1)),
            url=url_match.group(1),
            username=username_match.group(1),
            password=password_match.group(1),
            channels=channels_data["channels"],
            default_channel=channels_data["default"],
        )

    return _cache.request("https://search.nixos.org/bundle.js", parse_bundle)


def get_channels() -> dict[str, str]:
    """Get channel ID to index mapping."""
    config = get_config()
    channels = {}
    for ch in config.channels:
        branch = ch["branch"]
        channel_id = ch["id"]
        suffix = branch[6:] if branch.startswith("nixos-") else branch
        index = f"latest-{config.schema_version}-nixos-{suffix}"
        channels[channel_id] = index
    return channels


def get_auth() -> tuple[str, str]:
    """Get Elasticsearch auth credentials."""
    config = get_config()
    return (config.username, config.password)


def get_api_url() -> str:
    """Get Elasticsearch API URL."""
    config = get_config()
    if config.url.startswith("/"):
        return f"https://search.nixos.org{config.url}"
    return config.url


class InvalidChannelError(APIError):
    """Raised when an invalid channel is specified."""

    def __init__(self, channel: str, available: list[str]):
        self.channel = channel
        self.available = available
        super().__init__(f"Invalid channel: {channel}")


class InvalidLimitError(APIError):
    """Raised when limit is out of range."""

    def __init__(self, limit: int):
        self.limit = limit
        super().__init__(f"Invalid limit: {limit}")


class NixOSSearch:
    """NixOS package and option search functionality."""

    @staticmethod
    def _es_query(
        index: str, query: dict[str, Any], size: int = 20, from_: int = 0
    ) -> tuple[list[dict[str, Any]], int]:
        """Execute ES query and return (hits, total_count)."""
        api_url = get_api_url()
        auth = get_auth()
        try:
            resp = requests.post(
                f"{api_url}/{index}/_search",
                json={"query": query, "size": size, "from": from_},
                auth=auth,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "hits" in data:
                hits_data = data.get("hits", {})
                if isinstance(hits_data, dict):
                    hits = list(hits_data.get("hits", []))
                    total = hits_data.get("total", {})
                    total_count = total.get("value", 0) if isinstance(total, dict) else total
                    return hits, total_count
            return [], 0
        except requests.Timeout as exc:
            raise APIError("Connection timed out") from exc
        except requests.HTTPError as exc:
            raise APIError(str(exc)) from exc
        except Exception as exc:
            raise APIError(str(exc)) from exc

    @staticmethod
    def _es_query_all(index: str, query: dict[str, Any], batch_size: int = 100) -> list[dict[str, Any]]:
        """Fetch all results using pagination."""
        all_hits = []
        from_ = 0
        while True:
            hits, _ = NixOSSearch._es_query(index, query, size=batch_size, from_=from_)
            if not hits:
                break
            all_hits.extend(hits)
            if len(hits) < batch_size:
                break
            from_ += batch_size
        return all_hits

    @staticmethod
    def _get_channel_index(channel: str) -> str:
        """Get the ES index for a channel. Raises InvalidChannelError if invalid."""
        channels = get_channels()
        if channel not in channels:
            raise InvalidChannelError(channel, list(channels.keys()))
        return channels[channel]

    @staticmethod
    def _validate_limit(limit: int) -> None:
        if not 1 <= limit <= 100:
            raise InvalidLimitError(limit)

    @staticmethod
    def search_packages(query: str, limit: int, channel: str) -> SearchResult[Package]:
        """Search for NixOS packages."""
        NixOSSearch._validate_limit(limit)
        index = NixOSSearch._get_channel_index(channel)

        q = {
            "bool": {
                "must": [{"term": {"type": "package"}}],
                "should": [
                    {"match": {"package_pname": {"query": query, "boost": 3}}},
                    {"match": {"package_description": query}},
                ],
                "minimum_should_match": 1,
            }
        }

        hits, total = NixOSSearch._es_query(index, q, limit)
        packages = [Package.model_validate(hit.get("_source", {})) for hit in hits]
        return SearchResult(items=packages, total=total)

    @staticmethod
    def search_options(query: str, limit: int, channel: str) -> SearchResult[Option]:
        """Search for NixOS options."""
        NixOSSearch._validate_limit(limit)
        index = NixOSSearch._get_channel_index(channel)

        q = {
            "bool": {
                "must": [{"term": {"type": "option"}}],
                "should": [
                    {"wildcard": {"option_name": f"*{query}*"}},
                    {"match": {"option_description": query}},
                ],
                "minimum_should_match": 1,
            }
        }

        hits, total = NixOSSearch._es_query(index, q, limit)
        options = [Option.model_validate(hit.get("_source", {})) for hit in hits]
        return SearchResult(items=options, total=total)

    @staticmethod
    def get_package(name: str, channel: str) -> Package | None:
        """Get detailed info about a package."""
        index = NixOSSearch._get_channel_index(channel)
        query = {"bool": {"must": [{"term": {"type": "package"}}, {"term": {"package_pname": name}}]}}
        hits, _ = NixOSSearch._es_query(index, query, 1)
        if not hits:
            return None
        return Package.model_validate(hits[0].get("_source", {}))

    @staticmethod
    def get_option(name: str, channel: str) -> Option | None:
        """Get detailed info about an option."""
        index = NixOSSearch._get_channel_index(channel)
        query = {"bool": {"must": [{"term": {"type": "option"}}, {"term": {"option_name": name}}]}}
        hits, _ = NixOSSearch._es_query(index, query, 1)
        if not hits:
            return None
        return Option.model_validate(hits[0].get("_source", {}))

    @staticmethod
    def get_option_children(prefix: str, channel: str) -> list[Option]:
        """Get all child options under a prefix (e.g., 'services.nginx')."""
        index = NixOSSearch._get_channel_index(channel)
        query = {
            "bool": {
                "must": [
                    {"term": {"type": "option"}},
                    {"prefix": {"option_name": f"{prefix}."}},
                ]
            }
        }
        hits = NixOSSearch._es_query_all(index, query)
        return [Option.model_validate(hit.get("_source", {})) for hit in hits]

    @staticmethod
    def list_channels() -> list[Channel]:
        """List available NixOS channels."""
        config = get_config()
        return [
            Channel(
                id=ch["id"],
                branch=ch["branch"],
                status=ch.get("status", ""),
                is_default=ch["id"] == config.default_channel,
            )
            for ch in config.channels
        ]
