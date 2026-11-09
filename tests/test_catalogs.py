"""Regression checks for the current external catalog contracts."""

from types import SimpleNamespace

import pytest

from mcp_nix import nix_nomad, nixhub, nuschtos
from mcp_nix.cache import APIError


def test_nomad_current_html_and_empty_catalog():
    html = """<div class="option" id="option-job"><h3 class="option-name"><a>job</a></h3>
    <div class="option-type">Type: <code>submodule</code></div>
    <div class="option-description"><p>Nomad jobs.</p></div>
    <div class="option-default"><code>{ }</code></div></div>"""
    result = nix_nomad._parse_options(html)
    assert result["job"].description == "Nomad jobs."
    assert result["job"].type == "submodule"
    with pytest.raises(APIError, match="no option declarations"):
        nix_nomad._parse_options("<h1>Welcome</h1>")


def test_nixhub_v2_request_and_commit(monkeypatch):
    def request(url, callback, **kwargs):
        assert url == "https://search.devbox.sh/v2/pkg"
        assert kwargs["params"] == {"name": "nodejs"}
        return callback(
            SimpleNamespace(
                json=lambda: {
                    "releases": [
                        {"version": "20.11.0", "platforms": [{"commit_hash": "a" * 40, "attribute_path": "nodejs_20"}]}
                    ]
                }
            )
        )

    monkeypatch.setattr(nixhub._cache, "request", request)
    result = nixhub.NixhubSearch.get_commit("nodejs", "20.11.0")
    assert result.commit_hash == "a" * 40
    with pytest.raises(nixhub.VersionNotFoundError):
        nixhub.NixhubSearch.get_commit("nodejs", "999")


def test_nixhub_only_maps_real_404_to_missing_package(monkeypatch):
    def fail(*args, **kwargs):
        raise APIError("HTTP 500 containing unrelated number 404", status_code=500)

    monkeypatch.setattr(nixhub._cache, "request", fail)
    with pytest.raises(APIError) as caught:
        nixhub.fetch_package("nodejs")
    assert not isinstance(caught.value, nixhub.PackageNotFoundError)


def test_nuschtos_configuration_and_scope_mapping():
    meta = nuschtos._parse_catalog_config(
        'chunkSize:300,dataBase:"/data/",scopes:[{name:"disko"},{name:"nix-darwin"}],title:"Search"'
    )
    assert meta.chunk_size == 300
    assert nuschtos._get_scope_id_for_project("nix-darwin", SimpleNamespace(meta=meta)) == 1


def test_nuschtos_rejects_mixed_generations(monkeypatch):
    data = nuschtos.IndexData(
        index=SimpleNamespace(), meta=nuschtos.CatalogMeta(300, ["nix-darwin"]), fingerprint="generation", expires_at=1
    )
    monkeypatch.setattr(nuschtos, "_get_chunk", lambda *args: [{"name": "wrong.option"}])
    monkeypatch.setattr(nuschtos._cache, "clear", lambda: None)
    monkeypatch.setattr(nuschtos, "_index_cache", {"nuschtos": data})
    with pytest.raises(APIError, match="catalog changed"):
        nuschtos._get_option_by_idx("nuschtos", 0, data, "correct.option")
    assert "nuschtos" not in nuschtos._index_cache


def test_nuschtos_children_do_not_stop_at_500(monkeypatch):
    index = SimpleNamespace(
        size=lambda: 700,
        search=lambda query, max_results, scope_id: [
            SimpleNamespace(idx=i, name=f"programs.x{i}") for i in range(max_results)
        ],
    )
    data = SimpleNamespace(index=index)
    monkeypatch.setattr(nuschtos.NuschtosSearch, "_get_project_context", lambda project: ("nixvim", data, 0))
    monkeypatch.setattr(nuschtos, "_get_option_by_idx", lambda instance, idx, data, name: {"name": name})
    assert len(nuschtos.NuschtosSearch.get_option_children("programs", "nixvim")) == 700
