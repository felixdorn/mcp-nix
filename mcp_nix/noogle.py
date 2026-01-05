# SPDX-License-Identifier: GPL-3.0-or-later
"""Noogle (noogle.dev) client for Nix standard library function search."""

import gzip
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import platformdirs
import requests
from bs4 import BeautifulSoup
from wasmtime import Engine, Func, Instance, Linker, Memory, Module, Store

from .models import FunctionInput, NoogleExample, NoogleFunction, SearchResult
from .search import APIError

# =============================================================================
# Exceptions
# =============================================================================


class NoogleError(APIError):
    """Base exception for Noogle errors."""


class FunctionNotFoundError(NoogleError):
    """Raised when a function is not found on Noogle."""

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Function '{path}' not found on Noogle")


# =============================================================================
# Caching
# =============================================================================


def _get_cache_dir() -> Path:
    """Get the cache directory for Noogle data."""
    cache_dir = Path(platformdirs.user_cache_dir("mcp-nix")) / "noogle"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


# In-memory cache for PagefindSearch instance (singleton)
_pagefind_instance: "PagefindSearch | None" = None


def _get_pagefind() -> "PagefindSearch":
    """Get or create the PagefindSearch singleton."""
    global _pagefind_instance
    if _pagefind_instance is None:
        _pagefind_instance = PagefindSearch()
    return _pagefind_instance


# =============================================================================
# Pagefind WASM Search Engine
# =============================================================================


class PagefindSearch:
    """Python implementation of Pagefind search using WASM."""

    BASE_URL = "https://noogle.dev"
    PAGEFIND_PATH = "/pagefind"

    def __init__(self):
        self.session = requests.Session()
        self._store: Store | None = None
        self._instance: Instance | None = None
        self._memory: Memory | None = None
        self.ptr: int | None = None
        self.loaded_chunks: set[str] = set()
        self.entry: dict | None = None

    @property
    def store(self) -> Store:
        """Get the store, ensuring it's initialized."""
        if self._store is None:
            raise NoogleError("WASM runtime not initialized")
        return self._store

    @property
    def instance(self) -> Instance:
        """Get the instance, ensuring it's initialized."""
        if self._instance is None:
            raise NoogleError("WASM runtime not initialized")
        return self._instance

    @property
    def memory(self) -> Memory:
        """Get the memory, ensuring it's initialized."""
        if self._memory is None:
            raise NoogleError("WASM runtime not initialized")
        return self._memory

    def _get_func(self, name: str) -> Func:
        """Get a function export by name."""
        export = self.instance.exports(self.store)[name]
        if not isinstance(export, Func):
            raise NoogleError(f"Export '{name}' is not a function")
        return export

    def _fetch(self, path: str) -> bytes:
        """Fetch a resource from Noogle."""
        url = f"{self.BASE_URL}{self.PAGEFIND_PATH}/{path}"
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content

    def _decompress(self, data: bytes) -> bytes:
        """Decompress Pagefind data (gzip with signature)."""
        # Check if already decompressed
        if data[:12] == b"pagefind_dcd":
            return data[12:]
        # Decompress gzip
        decompressed = gzip.decompress(data)
        if decompressed[:12] != b"pagefind_dcd":
            raise NoogleError("Invalid pagefind data: missing signature")
        return decompressed[12:]

    def _init_wasm(self):
        """Initialize the WASM runtime."""
        # Load entry to get language/hash info
        entry_data = self._fetch("pagefind-entry.json")
        self.entry = json.loads(entry_data)

        # Get the English index info
        lang_info = self.entry["languages"].get("en")
        if not lang_info:
            # Fall back to first available language
            lang_info = list(self.entry["languages"].values())[0]

        index_hash = lang_info["hash"]
        wasm_lang = lang_info.get("wasm", "en")

        # Load and decompress WASM
        wasm_compressed = self._fetch(f"wasm.{wasm_lang}.pagefind")
        wasm_bytes = self._decompress(wasm_compressed)

        # Load and decompress metadata
        meta_compressed = self._fetch(f"pagefind.{index_hash}.pf_meta")
        meta_bytes = self._decompress(meta_compressed)

        # Initialize WASM runtime
        engine = Engine()
        self._store = Store(engine)
        module = Module(engine, wasm_bytes)

        # Create linker with empty imports (pagefind doesn't need any)
        linker = Linker(engine)

        # Instantiate
        self._instance = linker.instantiate(self._store, module)
        memory_export = self._instance.exports(self._store)["memory"]
        if not isinstance(memory_export, Memory):
            raise NoogleError("Memory export is not a Memory object")
        self._memory = memory_export

        # Initialize pagefind with metadata
        self.ptr = self._call_init_pagefind(meta_bytes)

    def _write_bytes(self, data: bytes) -> tuple[int, int]:
        """Write bytes to WASM memory and return (ptr, len)."""
        malloc = self._get_func("__wbindgen_malloc")
        ptr: int = malloc(self.store, len(data))
        mem_data = self.memory.data_ptr(self.store)

        # Write data to memory
        for i, b in enumerate(data):
            mem_data[ptr + i] = b

        return ptr, len(data)

    def _write_string(self, s: str) -> tuple[int, int]:
        """Write a UTF-8 string to WASM memory."""
        return self._write_bytes(s.encode("utf-8"))

    def _read_string(self, ptr: int, length: int) -> str:
        """Read a UTF-8 string from WASM memory."""
        mem_data = self.memory.data_ptr(self.store)
        data = bytes(mem_data[ptr : ptr + length])
        return data.decode("utf-8")

    def _call_init_pagefind(self, meta_bytes: bytes) -> int:
        """Call init_pagefind and return the pointer."""
        init_fn = self._get_func("init_pagefind")
        ptr, length = self._write_bytes(meta_bytes)
        return init_fn(self.store, ptr, length)

    def _call_request_indexes(self, query: str) -> str:
        """Get required index chunks for a query."""
        request_indexes = self._get_func("request_indexes")
        add_to_stack = self._get_func("__wbindgen_add_to_stack_pointer")
        free = self._get_func("__wbindgen_free")

        query_ptr, query_len = self._write_string(query)

        # Allocate return space on stack
        retptr: int = add_to_stack(self.store, -16)

        request_indexes(self.store, retptr, self.ptr, query_ptr, query_len)

        # Read return values
        mem = self.memory.data_ptr(self.store)
        r0 = int.from_bytes(mem[retptr : retptr + 4], "little")
        r1 = int.from_bytes(mem[retptr + 4 : retptr + 8], "little")

        result = self._read_string(r0, r1)

        # Cleanup
        add_to_stack(self.store, 16)
        free(self.store, r0, r1)

        return result

    def _call_load_index_chunk(self, chunk_bytes: bytes):
        """Load an index chunk into the search engine."""
        load_fn = self._get_func("load_index_chunk")
        ptr, length = self._write_bytes(chunk_bytes)
        self.ptr = load_fn(self.store, self.ptr, ptr, length)

    def _call_search(self, query: str, filters: str = "{}", sort: str = "", exact: bool = False) -> str:
        """Execute search and return raw results."""
        search_fn = self._get_func("search")
        add_to_stack = self._get_func("__wbindgen_add_to_stack_pointer")
        free = self._get_func("__wbindgen_free")

        query_ptr, query_len = self._write_string(query)
        filter_ptr, filter_len = self._write_string(filters)
        sort_ptr, sort_len = self._write_string(sort)

        retptr: int = add_to_stack(self.store, -16)

        search_fn(
            self.store,
            retptr,
            self.ptr,
            query_ptr,
            query_len,
            filter_ptr,
            filter_len,
            sort_ptr,
            sort_len,
            1 if exact else 0,
        )

        mem = self.memory.data_ptr(self.store)
        r0 = int.from_bytes(mem[retptr : retptr + 4], "little")
        r1 = int.from_bytes(mem[retptr + 4 : retptr + 8], "little")

        result = self._read_string(r0, r1)

        add_to_stack(self.store, 16)
        free(self.store, r0, r1)

        return result

    def _load_chunks(self, chunk_list: str):
        """Load required index chunks."""
        chunks = [c for c in chunk_list.split() if c and c not in self.loaded_chunks]

        for chunk_hash in chunks:
            chunk_compressed = self._fetch(f"index/{chunk_hash}.pf_index")
            chunk_bytes = self._decompress(chunk_compressed)
            self._call_load_index_chunk(chunk_bytes)
            self.loaded_chunks.add(chunk_hash)

    def _load_fragment(self, fragment_hash: str) -> dict:
        """Load a search result fragment."""
        fragment_compressed = self._fetch(f"fragment/{fragment_hash}.pf_fragment")
        fragment_bytes = self._decompress(fragment_compressed)
        return json.loads(fragment_bytes.decode("utf-8"))

    def search(self, query: str, limit: int = 20) -> tuple[list[NoogleFunction], int]:
        """Search for functions. Returns (results, total_count)."""
        if self._instance is None:
            self._init_wasm()

        # Normalize query
        normalized = query.lower().strip()
        normalized = re.sub(r"[.`~!@#$%^&*()\[\]\\|:;'\",<>/?-]", "", normalized)
        normalized = re.sub(r"\s{2,}", " ", normalized).strip()

        # Get and load required chunks
        chunk_list = self._call_request_indexes(normalized)
        self._load_chunks(chunk_list)

        # Execute search
        raw_result = self._call_search(normalized)

        # Parse results: "count:hash@score@locs hash@score@locs...:filters__PF_UNFILTERED_DELIM__totalfilters"
        parts = raw_result.split(":", 2)
        total_count = int(parts[0]) if parts[0] else 0

        results = []
        if len(parts) > 1 and parts[1]:
            # Extract results before filters
            results_part = parts[1].split("__PF_UNFILTERED_DELIM__")[0]
            result_entries = results_part.split()

            for entry in result_entries[:limit]:
                entry_parts = entry.split("@")
                if len(entry_parts) >= 2:
                    fragment_hash = entry_parts[0]

                    # Load fragment for details
                    try:
                        fragment = self._load_fragment(fragment_hash)
                        url = fragment.get("url", "")
                        # Remove .html extension and convert to path
                        clean_url = url.replace(".html", "")
                        # Convert URL to path: /f/lib/strings/map -> lib.strings.map
                        path = clean_url.replace("/f/", "").replace("/", ".")

                        results.append(
                            NoogleFunction(
                                name=path.split(".")[-1] if path else "",
                                path=path,
                                description=fragment.get("content", "")[:200] if fragment.get("content") else None,
                            )
                        )
                    except Exception:
                        # Skip failed fragments
                        pass

        return results, total_count


# =============================================================================
# HTML Parser for Function Details
# =============================================================================


def _extract_next_data(html: str) -> list[Any]:
    """Extract and parse Next.js flight data from script tags."""
    soup = BeautifulSoup(html, "html.parser")
    chunks: list[Any] = []

    for script in soup.find_all("script"):
        text = script.string
        if not text or "self.__next_f.push" not in text:
            continue

        match = re.search(r'self\.__next_f\.push\(\[1,"(.+)"\]\)', text, re.DOTALL)
        if not match:
            continue

        raw = match.group(1)
        unescaped = raw.encode().decode("unicode_escape")

        for line in unescaped.split("\n"):
            if not line.strip():
                continue
            colon_idx = line.find(":")
            if colon_idx == -1:
                continue
            json_part = line[colon_idx + 1 :]
            try:
                parsed = json.loads(json_part)
                chunks.append(parsed)
            except json.JSONDecodeError:
                pass

    return chunks


def _find_in_structure(data: Any, predicate: Callable[[Any], bool]) -> list[Any]:
    """Recursively find all items matching predicate in nested structure."""
    results = []

    if predicate(data):
        results.append(data)

    if isinstance(data, dict):
        for v in data.values():
            results.extend(_find_in_structure(v, predicate))
    elif isinstance(data, list):
        for item in data:
            results.extend(_find_in_structure(item, predicate))

    return results


def _find_by_key(data: Any, key: str) -> list[Any]:
    """Find all values for a specific key in nested structure."""
    results = []

    if isinstance(data, dict):
        if key in data:
            results.append(data[key])
        for v in data.values():
            results.extend(_find_by_key(v, key))
    elif isinstance(data, list):
        for item in data:
            results.extend(_find_by_key(item, key))

    return results


def _parse_noogle_data(chunks: list[Any]) -> NoogleFunction:
    """Parse extracted Next.js data into NoogleFunction."""

    path = ""
    name = ""
    for chunk in chunks:
        ids = _find_in_structure(chunk, lambda x: isinstance(x, dict) and x.get("variant") == "h2" and "id" in x)
        for item in ids:
            if "id" in item and "." in item["id"]:
                path = item["id"]
                name = path.split(".")[-1]
                break
        if path:
            break

    description = None
    for chunk in chunks:
        metas = _find_in_structure(chunk, lambda x: isinstance(x, dict) and x.get("name") == "description")
        for meta in metas:
            if "content" in meta:
                description = meta["content"]
                break
        if description:
            break

    categories = []
    for chunk in chunks:
        metas = _find_in_structure(
            chunk,
            lambda x: isinstance(x, dict)
            and isinstance(x.get("data-pagefind-meta"), str)
            and x["data-pagefind-meta"].startswith("category:"),
        )
        for meta in metas:
            cat = meta["data-pagefind-meta"].replace("category:", "")
            if cat not in categories:
                categories.append(cat)

    source_url = None
    source_file = None
    source_line = None
    for chunk in chunks:
        hrefs = _find_in_structure(
            chunk,
            lambda x: isinstance(x, dict)
            and isinstance(x.get("href"), str)
            and "github.com/nixos/nixpkgs/tree/" in x.get("href", ""),
        )
        for item in hrefs:
            source_url = item["href"]
            match = re.search(r"/tree/[^/]+/(.+?)#L(\d+)", source_url)
            if match:
                source_file = match.group(1)
                source_line = int(match.group(2))
            break
        if source_url:
            break

    aliases = []
    for chunk in chunks:
        links = _find_in_structure(
            chunk,
            lambda x: isinstance(x, dict)
            and isinstance(x.get("href"), str)
            and x.get("href", "").startswith("/f/")
            and x.get("rel") == "canonical",
        )
        for link in links:
            href = link["href"]
            alias_path = href.replace("/f/", "").replace("/", ".")
            if (
                alias_path
                and alias_path != path
                and alias_path not in aliases
                and alias_path.startswith("lib.")
                and "#" not in alias_path
            ):
                aliases.append(alias_path)

    type_signature = None
    inputs = []
    examples = []

    for chunk in chunks:
        inner_htmls = _find_by_key(chunk, "dangerouslySetInnerHTML")
        for inner in inner_htmls:
            if not isinstance(inner, dict) or "__html" not in inner:
                continue

            html_content = inner["__html"]
            soup = BeautifulSoup(html_content, "html.parser")

            type_code = soup.select_one("code.hljs.language-haskell")
            if type_code and not type_signature:
                type_signature = type_code.get_text().strip()

            for dt in soup.find_all("dt"):
                code = dt.find("code")
                if not code:
                    continue
                input_name = code.get_text(strip=True)

                dd = dt.find_next_sibling("dd")
                if dd:
                    dd_text = dd.get_text(strip=True)
                    match = re.match(r"(\d+)\.\s*Function argument", dd_text)
                    if match:
                        inputs.append(
                            FunctionInput(
                                name=input_name,
                                position=int(match.group(1)),
                            )
                        )

            for example_div in soup.select("div.example"):
                title = None
                title_h2 = example_div.find("h2")
                if title_h2:
                    title = title_h2.get_text(separator=" ", strip=True)

                code_block = example_div.select_one("code.hljs.language-nix")
                if code_block:
                    code_text = code_block.get_text().strip()

                    if "=>" in code_text:
                        parts = code_text.split("=>", 1)
                        code = parts[0].strip()
                        result = parts[1].strip() if len(parts) > 1 else None
                    else:
                        code = code_text
                        result = None

                    examples.append(NoogleExample(title=title, code=code, result=result))

    return NoogleFunction(
        name=name,
        path=path,
        description=description,
        type_signature=type_signature,
        inputs=inputs,
        examples=examples,
        source_url=source_url,
        source_file=source_file,
        source_line=source_line,
        aliases=aliases,
        categories=categories,
    )


def _fetch_noogle_function(function_path: str) -> NoogleFunction:
    """Fetch and parse a Noogle function page."""
    path = function_path.replace(".", "/")
    path = f"/f/{path}" if not path.startswith("/") else f"/f{path}"

    url = f"https://noogle.dev{path}"

    try:
        response = requests.get(url, timeout=30, allow_redirects=True)
        if response.status_code == 404:
            raise FunctionNotFoundError(function_path)
        response.raise_for_status()
    except requests.Timeout as e:
        raise NoogleError("Connection timed out fetching function from Noogle") from e
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise FunctionNotFoundError(function_path) from e
        raise NoogleError(f"Failed to fetch function from Noogle: {e}") from e

    chunks = _extract_next_data(response.text)
    return _parse_noogle_data(chunks)


# =============================================================================
# Public API
# =============================================================================


class NoogleSearch:
    """Noogle search functionality."""

    @staticmethod
    def search_functions(query: str, limit: int) -> SearchResult[NoogleFunction]:
        """Search for Nix standard library functions."""
        try:
            pagefind = _get_pagefind()
            results, total = pagefind.search(query, limit)
            return SearchResult(items=results, total=total)
        except requests.RequestException as e:
            raise NoogleError(f"Failed to search Noogle: {e}") from e

    @staticmethod
    def get_function(path: str) -> NoogleFunction:
        """Get detailed info for a function by path (e.g., lib.strings.map)."""
        return _fetch_noogle_function(path)
