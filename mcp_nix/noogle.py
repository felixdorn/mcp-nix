# SPDX-License-Identifier: GPL-3.0-or-later
"""Noogle function search using its published JSON dataset."""

import re

from .cache import APIError, get_cache
from .models import FunctionInput, NoogleExample, NoogleFunction, SearchResult

DATA_URL = "https://noogle.dev/api/v1/data"
_cache = get_cache("noogle")


class NoogleError(APIError):
    """Base exception for Noogle errors."""


class FunctionNotFoundError(NoogleError):
    """Raised when a function is not found on Noogle."""

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Function '{path}' not found on Noogle")


def _parse_function(record: dict, revision: str) -> NoogleFunction:
    meta = record["meta"]
    path = ".".join(meta["path"])
    content = record.get("content") or {}
    markdown = content.get("content") or ""
    description = re.split(r"\n#+\s+(?:Inputs|Type|Examples)\b", markdown, maxsplit=1)[0].strip()
    position = (content.get("source") or {}).get("position") or meta.get("attr_position") or {}
    source_file = position.get("file", "").split("-source/", 1)[-1]
    source_line = position.get("line")
    source_url = None
    if revision and source_file and not source_file.startswith("/"):
        source_url = f"https://github.com/NixOS/nixpkgs/blob/{revision}/{source_file}"
        if source_line:
            source_url += f"#L{source_line}"
    inputs = [
        FunctionInput(name=name, position=int(number))
        for name, number in re.findall(r"`([^`]+)`\s*\n:\s*(\d+)\\?\. Function argument", markdown)
    ]
    examples = []
    for code in re.findall(r"```nix\s*\n(.*?)```", markdown, re.DOTALL):
        # Keep complete multi-expression examples instead of splitting at the first =>.
        examples.append(NoogleExample(code=code.strip()))
    return NoogleFunction(
        name=meta["path"][-1],
        path=path,
        description=description or None,
        type_signature=(meta.get("signature") or "").strip() or None,
        inputs=inputs,
        examples=examples,
        source_url=source_url,
        source_file=source_file or None,
        source_line=source_line,
        aliases=[".".join(alias) for alias in (meta.get("aliases") or [])],
        categories=meta["path"][:-1],
    )


def _get_functions() -> list[NoogleFunction]:
    def parse(response):
        data = response.json()
        records = data["data"]
        if not isinstance(records, list) or not records:
            raise NoogleError("Noogle returned an empty or invalid function catalog")
        revision = data.get("upstreamInfo", {}).get("rev", "")
        return [_parse_function(record, revision) for record in records]

    return _cache.request(DATA_URL, parse, timeout=30)


class NoogleSearch:
    """Search function paths, aliases, signatures and documentation."""

    @staticmethod
    def search_functions(query: str, limit: int) -> SearchResult[NoogleFunction]:
        if not query.strip():
            raise NoogleError("Search query must not be empty")
        if not 1 <= limit <= 100:
            raise NoogleError("Limit must be between 1 and 100")
        terms = query.casefold().split()
        matches = []
        for function in _get_functions():
            paths = [function.path, *function.aliases]
            text = " ".join([*paths, function.type_signature or "", function.description or ""]).casefold()
            if all(term in text for term in terms):
                score = max(
                    3
                    if query.casefold() == path.casefold().split(".")[-1]
                    else 2
                    if query.casefold() in path.casefold()
                    else 1
                    for path in paths
                )
                matches.append((score, function))
        matches.sort(key=lambda item: (-item[0], item[1].path))
        return SearchResult(items=[item[1] for item in matches[:limit]], total=len(matches))

    @staticmethod
    def get_function(path: str) -> NoogleFunction:
        functions = _get_functions()
        for function in functions:
            if path == function.path:
                return function
        for function in functions:
            if path in function.aliases:
                return function
        raise FunctionNotFoundError(path)
