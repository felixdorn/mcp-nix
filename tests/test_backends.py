"""Backend contracts with small, stable upstream-shaped fixtures."""

from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup

from mcp_nix import homemanager, search
from mcp_nix.cache import APIError
from mcp_nix.models import Package
from mcp_nix.options import HomeManagerOptionsBackend


def test_nixos_discovers_hashed_bundle(monkeypatch):
    homepage = SimpleNamespace(
        soup=lambda: BeautifulSoup(
            '<script src="https://other.test/tracker.js"></script><script src="/static/js/index.abc.js"></script>',
            "html.parser",
        )
    )
    bundle = SimpleNamespace(
        text='elasticsearchMappingSchemaVersion:parseInt("53"),'
        'elasticsearchUrl:"/backend",elasticsearchUsername:"user",'
        'elasticsearchPassword:"password",nixosChannels:JSON.parse(\'{"channels":'
        '[{"id":"unstable","branch":"nixos-unstable"}],"default":"unstable"}\')'
    )
    calls = []

    def request(url, callback):
        calls.append(url)
        return callback(homepage if url.endswith("/") else bundle)

    monkeypatch.setattr(search._cache, "request", request)
    config = search.get_config()
    assert config.schema_version == 53
    assert calls == ["https://search.nixos.org/", "https://search.nixos.org/static/js/index.abc.js"]


def test_nullable_package_metadata_and_attribute():
    package = Package.model_validate(
        {
            "package_pname": "python",
            "package_attr_name": "python313",
            "package_pversion": "3.13",
            "package_description": None,
            "package_position": None,
            "package_homepage": ["https://python.org"],
        }
    )
    assert package.description == ""
    assert package.position == ""
    assert package.homepage == "https://python.org"
    assert "python313" in package.format_short()


@pytest.mark.parametrize("release", ["25.11", "release-25.11", "26.05", "26.05 (stable)", "unstable"])
def test_home_manager_release_aliases(monkeypatch, release):
    config = homemanager.HomeManagerConfig(
        releases=[
            {"name": 25.11, "value": "release-25.11"},
            {"name": "26.05 (stable)", "value": "release-26.05"},
            {"name": "unstable", "value": "master"},
        ],
        default_release="release-26.05",
    )
    monkeypatch.setattr(homemanager, "get_config", lambda: config)
    value, warning = HomeManagerOptionsBackend().validate_version(release)
    assert warning is None
    assert value == ("master" if release == "unstable" else "release-25.11" if "25.11" in release else "release-26.05")
    assert homemanager.HomeManagerSearch._get_release_value(value) == value


def test_home_manager_does_not_hide_discovery_errors(monkeypatch):
    def fail():
        raise APIError("offline")

    monkeypatch.setattr(homemanager, "get_config", fail)
    with pytest.raises(APIError, match="offline"):
        HomeManagerOptionsBackend().validate_version("unstable")


def test_home_manager_memory_cache_expires(monkeypatch):
    monkeypatch.setattr(homemanager, "_release_cache", {})
    clock = [0]
    monkeypatch.setattr(homemanager, "monotonic", lambda: clock[0])
    calls = []
    monkeypatch.setattr(
        homemanager, "_get_options", lambda release: calls.append(release) or [{"title": "programs.git.enable"}]
    )
    homemanager.get_release_data("master")
    homemanager.get_release_data("master")
    assert len(calls) == 1
    clock[0] = homemanager.DEFAULT_EXPIRE + 1
    homemanager.get_release_data("master")
    assert len(calls) == 2
