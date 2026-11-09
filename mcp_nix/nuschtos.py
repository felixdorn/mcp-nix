# SPDX-License-Identifier: GPL-3.0-or-later
"""NüschtOS-based option search logic (nixvim, nix-darwin, etc.)."""

import hashlib
import json
import re
from dataclasses import dataclass, field
from time import monotonic
from urllib.parse import urljoin, urlparse

from pydantic import BaseModel, Field, field_validator

import pyixx

from .cache import DEFAULT_EXPIRE, get_cache
from .models import SearchResult, _lines
from .search import APIError, InvalidLimitError
from .utils import html_to_text

# Search instances - base URLs for index/meta files
INSTANCES = {
    "nuschtos": "https://search.xn--nschtos-n2a.de",
    "nixvim": "https://nix-community.github.io/nixvim/search",
}

# Projects map to an instance + optional scope filter (by name)
PROJECTS = {
    "nixvim": {
        "name": "NixVim",
        "instance": "nixvim",
        "scope": None,  # Single-scope instance, use scope 0
        "description": "Neovim configuration framework for Nix",
    },
    "nix-darwin": {
        "name": "nix-darwin",
        "instance": "nuschtos",
        "scope": "nix-darwin",  # Scope name in nuschtos instance
        "description": "Nix modules for Darwin (macOS)",
    },
    "impermanence": {
        "name": "impermanence",
        "instance": "nuschtos",
        "scope": "impermanence",
        "description": "Opt-in persistence on NixOS with ephemeral root",
    },
    "microvm": {
        "name": "MicroVM.nix",
        "instance": "nuschtos",
        "scope": "MicroVM.nix",
        "description": "Declarative NixOS MicroVMs",
    },
    "simple-nixos-mailserver": {
        "name": "Simple NixOS Mailserver",
        "instance": "nuschtos",
        "scope": "simple-nixos-mailserver",
        "description": "Complete NixOS email server setup",
    },
    "sops-nix": {
        "name": "sops-nix",
        "instance": "nuschtos",
        "scope": "sops-nix",
        "description": "Declarative secrets management with SOPS",
    },
    "nixos-hardware": {
        "name": "NixOS Hardware",
        "instance": "nuschtos",
        "scope": "nixos-hardware",
        "description": "Hardware-specific NixOS modules",
    },
    "disko": {
        "name": "Disko",
        "instance": "nuschtos",
        "scope": "disko",
        "description": "Declarative disk partitioning for NixOS",
    },
}

_cache = get_cache("nuschtos")

# In-memory cache for loaded indices (pyixx.Index can't be serialized)
_index_cache: dict[str, "IndexData"] = {}


def _get_instance_for_project(project: str) -> str:
    """Get the instance name for a project."""
    if project not in PROJECTS:
        raise InvalidProjectError(project, list(PROJECTS.keys()))
    instance = PROJECTS[project]["instance"]
    assert isinstance(instance, str)
    return instance


def _get_scope_id_for_project(project: str, index_data: "IndexData") -> int | None:
    """Get the scope ID for a project, resolving by name if needed."""
    scope = PROJECTS[project].get("scope")
    if scope is None:
        return None  # No scope filter, search all

    # If scope is an int, use directly
    if isinstance(scope, int):
        return scope

    # Resolve scope name to ID
    for i, scope_name in enumerate(index_data.meta.scopes):
        if scope_name == scope:
            return i

    raise APIError(f"Scope '{scope}' not found in instance. Available: {index_data.meta.scopes}")


class NuschtoOption(BaseModel):
    """NüschtOS-style option (nixvim, nix-darwin, etc.)."""

    name: str
    type: str = ""
    description: str = ""
    default: str = Field(default="")
    example: str = Field(default="")
    declarations: list[str] = Field(default_factory=list)
    read_only: bool = False

    @field_validator("type", "default", "example", mode="before")
    @classmethod
    def coerce_none_to_str(cls, v):
        return str(v) if v is not None else ""

    @field_validator("description", "default", "example", mode="after")
    @classmethod
    def clean_html(cls, v):
        return html_to_text(v) if v else ""

    def format_short(self) -> str:
        """Format for search results listing."""
        lines = [f"• {self.name}"]
        if self.type:
            lines.append(f"  Type: {self.type}")
        if self.description:
            desc = self.description
            if len(desc) > 120:
                desc = desc[:117] + "..."
            lines.append(f"  {desc}")
        return "\n".join(lines)

    def __str__(self) -> str:
        """Format for detailed info."""
        result = _lines(
            ("Option", self.name),
            ("Type", self.type),
            ("Description", self.description),
            ("Default", self.default),
            ("Example", self.example),
        )
        if self.declarations:
            result += f"\nSource: {self.declarations[0]}"
        return result


@dataclass
class CatalogMeta:
    """Deployment configuration, kept alongside the binary index."""

    chunk_size: int
    scopes: list[str]


def _parse_catalog_config(bundle: str) -> CatalogMeta:
    chunk = re.search(r"chunkSize:(\d+)", bundle)
    scopes = re.search(r"scopes:\[(.*?)\],title:", bundle, re.DOTALL)
    if not chunk or not scopes:
        raise APIError("Could not discover NüschtOS catalog configuration")
    names = re.findall(r'name:("(?:\\.|[^"\\])*")', scopes[1])
    if not names or int(chunk[1]) <= 0:
        raise APIError("Invalid NüschtOS catalog configuration")
    return CatalogMeta(chunk_size=int(chunk[1]), scopes=[json.loads(name) for name in names])


def _get_catalog_config(instance: str) -> CatalogMeta:
    base = INSTANCES[instance].rstrip("/") + "/"
    scripts = _cache.request(base, lambda r: [tag["src"] for tag in r.soup().select("script[src]")])
    for src in scripts:
        url = urljoin(base, src)
        if urlparse(url).netloc != urlparse(base).netloc:
            continue
        if "main-" in src:
            return _cache.request(url, lambda r: _parse_catalog_config(r.text))
    raise APIError("Could not find the NüschtOS application bundle")


@dataclass
class IndexData:
    """Loaded index data."""

    index: pyixx.Index
    meta: CatalogMeta
    fingerprint: str
    expires_at: float
    chunks: dict[int, list[dict]] = field(default_factory=dict)


def _get_index_bytes(instance: str) -> bytes:
    """Get index bytes for an instance, using cache if available."""
    if instance not in INSTANCES:
        raise APIError(f"Unknown instance: {instance}")

    url = f"{INSTANCES[instance]}/data/options/index.ixx"
    return _cache.request(url, lambda r: r.content)


def _get_index(instance: str) -> IndexData:
    """Get index for an instance, using cache if available."""
    # Check in-memory cache (pyixx.Index can't be serialized)
    cached = _index_cache.get(instance)
    if cached is not None and cached.expires_at > monotonic():
        return cached

    data = _get_index_bytes(instance)
    meta = _get_catalog_config(instance)
    try:
        index = pyixx.Index.read(data)
    except ValueError as exc:
        raise APIError("Unsupported NüschtOS index format; update mcp-nix/pyixx") from exc
    index_data = IndexData(
        index=index, meta=meta, fingerprint=hashlib.sha256(data).hexdigest(), expires_at=monotonic() + DEFAULT_EXPIRE
    )

    _index_cache[instance] = index_data
    return index_data


def _get_chunk(instance: str, chunk: int, index_data: IndexData) -> list[dict]:
    """Get a metadata chunk, using cache if available."""
    # Check in-memory cache
    if chunk in index_data.chunks:
        return index_data.chunks[chunk]

    if instance not in INSTANCES:
        raise APIError(f"Unknown instance: {instance}")

    url = f"{INSTANCES[instance]}/data/options/chunks/{chunk}.json"

    def use(r):
        data = r.json()
        if not isinstance(data, list) or not data:
            raise APIError("Invalid NüschtOS option chunk")
        index_data.chunks[chunk] = data
        return data

    # Partition caches by index generation; chunks are mutable deployment assets.
    return _cache.request(url, use, params={"index": index_data.fingerprint})


def _get_option_by_idx(instance: str, idx: int, index_data: IndexData, expected_name: str) -> dict | None:
    """Get option data by index."""
    chunk, pos = divmod(idx, index_data.meta.chunk_size)
    chunk_data = _get_chunk(instance, chunk, index_data)

    if pos < len(chunk_data) and chunk_data[pos].get("name") == expected_name:
        return chunk_data[pos]
    # Do not return a different option if upstream deploys between index/chunk fetches.
    _index_cache.pop(instance, None)
    _cache.clear()
    raise APIError("NüschtOS catalog changed while loading; retry the request")


class InvalidProjectError(APIError):
    """Raised when an invalid project is specified."""

    def __init__(self, project: str, available: list[str]):
        self.project = project
        self.available = available
        super().__init__(f"Invalid project: {project}. Available: {', '.join(available)}")


class NuschtosSearch:
    """NüschtOS-style option search functionality."""

    @staticmethod
    def _validate_project(project: str) -> None:
        if project not in PROJECTS:
            raise InvalidProjectError(project, list(PROJECTS.keys()))

    @staticmethod
    def _validate_limit(limit: int) -> None:
        if not 1 <= limit <= 100:
            raise InvalidLimitError(limit)

    @staticmethod
    def _get_project_context(project: str) -> tuple[str, IndexData, int | None]:
        """Get instance, index data, and scope ID for a project."""
        NuschtosSearch._validate_project(project)
        instance = _get_instance_for_project(project)
        index_data = _get_index(instance)
        scope_id = _get_scope_id_for_project(project, index_data)
        return instance, index_data, scope_id

    @staticmethod
    def search_options(query: str, limit: int, project: str) -> SearchResult[NuschtoOption]:
        """Search for options in a NüschtOS-based project."""
        NuschtosSearch._validate_limit(limit)
        instance, index_data, scope_id = NuschtosSearch._get_project_context(project)

        results = index_data.index.search(query, max_results=index_data.index.size(), scope_id=scope_id)

        options = []
        for result in results[:limit]:
            opt_data = _get_option_by_idx(instance, result.idx, index_data, result.name)
            if opt_data:
                options.append(NuschtoOption.model_validate(opt_data))

        return SearchResult(items=options, total=len(results))

    @staticmethod
    def get_option(name: str, project: str) -> NuschtoOption | None:
        """Get detailed info about an option by exact name."""
        instance, index_data, scope_id = NuschtosSearch._get_project_context(project)

        # Use scope 0 if no scope filter (single-scope instance)
        lookup_scope = scope_id if scope_id is not None else 0
        idx = index_data.index.get_idx_by_name(lookup_scope, name)

        if idx is None:
            return None

        opt_data = _get_option_by_idx(instance, idx, index_data, name)
        if opt_data:
            return NuschtoOption.model_validate(opt_data)
        return None

    @staticmethod
    def get_option_children(prefix: str, project: str) -> list[NuschtoOption]:
        """Get all child options under a prefix (e.g., 'programs.vim')."""
        instance, index_data, scope_id = NuschtosSearch._get_project_context(project)

        # Search with prefix wildcard
        results = index_data.index.search(f"{prefix}.*", max_results=index_data.index.size(), scope_id=scope_id)

        options = []
        prefix_dot = f"{prefix}."
        for result in results:
            if result.name.startswith(prefix_dot):
                opt_data = _get_option_by_idx(instance, result.idx, index_data, result.name)
                if opt_data:
                    options.append(NuschtoOption.model_validate(opt_data))

        return options

    @staticmethod
    def list_projects() -> list[dict]:
        """List available projects."""
        return [
            {
                "id": project_id,
                "name": info["name"],
                "description": info["description"],
            }
            for project_id, info in PROJECTS.items()
        ]
