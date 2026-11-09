"""Noogle dataset parsing without frontend or WASM dependencies."""

from types import SimpleNamespace

import pytest

from mcp_nix import noogle


@pytest.fixture(autouse=True)
def catalog(monkeypatch):
    data = {
        "upstreamInfo": {"rev": "a" * 40},
        "data": [
            {
                "meta": {
                    "path": ["lib", "strings", "splitString"],
                    "aliases": [["lib", "splitString"]],
                    "signature": "String -> String -> [String]",
                    "attr_position": {"file": "/nix/store/abc-source/lib/strings.nix", "line": 42},
                },
                "content": {
                    "content": "Split a string.\n\n# Inputs\n\n`sep`\n: 1\\. Function argument\n\n"
                    '# Examples\n```nix\nsplitString "." "a.b"\n=> [ "a" "b" ]\n```'
                },
            }
        ],
    }
    monkeypatch.setattr(noogle._cache, "request", lambda url, parse, **kw: parse(SimpleNamespace(json=lambda: data)))


def test_lookup_alias_preserves_documentation():
    result = noogle.NoogleSearch.get_function("lib.splitString")
    assert result.path == "lib.strings.splitString"
    assert result.description == "Split a string."
    assert result.inputs[0].name == "sep"
    assert result.source_url == f"https://github.com/NixOS/nixpkgs/blob/{'a' * 40}/lib/strings.nix#L42"
    assert '=> [ "a" "b" ]' in result.examples[0].code


def test_search_path_signature_and_no_matches():
    assert noogle.NoogleSearch.search_functions("splitString", 1).total == 1
    assert noogle.NoogleSearch.search_functions("String ->", 1).total == 1
    assert noogle.NoogleSearch.search_functions("nonexistent", 1).items == []


def test_missing_function_is_actionable():
    with pytest.raises(noogle.FunctionNotFoundError):
        noogle.NoogleSearch.get_function("lib.missing")


def test_builtin_without_aliases_or_documentation():
    function = noogle._parse_function({"meta": {"path": ["builtins", "map"], "aliases": None}, "content": None}, "")
    assert function.path == "builtins.map"
    assert function.aliases == []
    assert function.source_url is None
