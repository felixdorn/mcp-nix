# SPDX-License-Identifier: GPL-3.0-or-later
"""NüschtOS-based option search logic (nixvim, nix-darwin, etc.)."""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import platformdirs
import requests
from pydantic import BaseModel, Field, field_validator

import pyixx

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
}

CACHE_MAX_AGE_SECONDS = 60 * 60  # 1 hour

# In-memory cache for loaded indices (keyed by instance name)
_index_cache: dict[str, "IndexData"] = {}


def _get_cache_dir() -> Path:
    """Get the cache directory for NüschtOS data."""
    cache_dir = Path(platformdirs.user_cache_dir("mcp-nix")) / "nuschtos"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _get_instance_cache_dir(instance: str) -> Path:
    """Get the cache directory for a specific instance."""
    cache_dir = _get_cache_dir() / instance
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


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
class IndexData:
    """Loaded index data."""

    index: pyixx.Index
    meta: pyixx.IndexMeta
    chunks: dict[int, list[dict]] = field(default_factory=dict)


def _load_cached_index(instance: str) -> bytes | None:
    """Load index from cache if valid (1 hour TTL)."""
    cache_dir = _get_instance_cache_dir(instance)
    index_path = cache_dir / "index.ixx"
    meta_path = cache_dir / "index_meta.json"

    if not index_path.exists() or not meta_path.exists():
        return None

    try:
        meta = json.loads(meta_path.read_text())
        cached_at = meta.get("cached_at", 0)
        if time.time() - cached_at > CACHE_MAX_AGE_SECONDS:
            return None
        return index_path.read_bytes()
    except (OSError, json.JSONDecodeError):
        return None


def _save_index_to_cache(instance: str, data: bytes) -> None:
    """Save index to cache."""
    cache_dir = _get_instance_cache_dir(instance)
    index_path = cache_dir / "index.ixx"
    meta_path = cache_dir / "index_meta.json"

    index_path.write_bytes(data)
    meta_path.write_text(json.dumps({"cached_at": time.time()}))


def _fetch_index(instance: str) -> bytes:
    """Fetch index.ixx for an instance."""
    if instance not in INSTANCES:
        raise APIError(f"Unknown instance: {instance}")

    base_url = INSTANCES[instance]
    url = f"{base_url}/index.ixx"

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content
    except requests.Timeout as exc:
        raise APIError(f"Connection timed out fetching index for {instance}") from exc
    except requests.HTTPError as exc:
        raise APIError(f"Failed to fetch index for {instance}: {exc}") from exc


def _get_index(instance: str) -> IndexData:
    """Get index for an instance, using cache if available."""
    # Check in-memory cache
    if instance in _index_cache:
        return _index_cache[instance]

    # Check disk cache
    data = _load_cached_index(instance)
    if data is None:
        data = _fetch_index(instance)
        _save_index_to_cache(instance, data)

    # Parse index
    index = pyixx.Index.read(data)
    meta = index.meta()
    index_data = IndexData(index=index, meta=meta)

    # Cache in memory
    _index_cache[instance] = index_data
    return index_data


def _load_cached_chunk(instance: str, chunk: int) -> list[dict] | None:
    """Load a metadata chunk from cache."""
    cache_dir = _get_instance_cache_dir(instance)
    chunk_path = cache_dir / f"meta_{chunk}.json"

    if not chunk_path.exists():
        return None

    try:
        return json.loads(chunk_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _save_chunk_to_cache(instance: str, chunk: int, data: list[dict]) -> None:
    """Save a metadata chunk to cache."""
    cache_dir = _get_instance_cache_dir(instance)
    chunk_path = cache_dir / f"meta_{chunk}.json"
    chunk_path.write_text(json.dumps(data))


def _fetch_chunk(instance: str, chunk: int) -> list[dict]:
    """Fetch a metadata chunk for an instance."""
    if instance not in INSTANCES:
        raise APIError(f"Unknown instance: {instance}")

    base_url = INSTANCES[instance]
    url = f"{base_url}/meta/{chunk}.json"

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.Timeout as exc:
        raise APIError(f"Connection timed out fetching chunk {chunk} for {instance}") from exc
    except requests.HTTPError as exc:
        raise APIError(f"Failed to fetch chunk {chunk} for {instance}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise APIError(f"Failed to parse chunk {chunk} for {instance}: {exc}") from exc


def _get_chunk(instance: str, chunk: int, index_data: IndexData) -> list[dict]:
    """Get a metadata chunk, using cache if available."""
    # Check in-memory cache
    if chunk in index_data.chunks:
        return index_data.chunks[chunk]

    # Check disk cache
    data = _load_cached_chunk(instance, chunk)
    if data is None:
        data = _fetch_chunk(instance, chunk)
        _save_chunk_to_cache(instance, chunk, data)

    # Cache in memory
    index_data.chunks[chunk] = data
    return data


def _get_option_by_idx(instance: str, idx: int, index_data: IndexData) -> dict | None:
    """Get option data by index."""
    chunk, pos = index_data.index.get_chunk_for_idx(idx)
    chunk_data = _get_chunk(instance, chunk, index_data)

    if pos < len(chunk_data):
        return chunk_data[pos]
    return None


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

        results = index_data.index.search(query, max_results=limit, scope_id=scope_id)

        options = []
        for result in results:
            opt_data = _get_option_by_idx(instance, result.idx, index_data)
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

        opt_data = _get_option_by_idx(instance, idx, index_data)
        if opt_data:
            return NuschtoOption.model_validate(opt_data)
        return None

    @staticmethod
    def get_option_children(prefix: str, project: str) -> list[NuschtoOption]:
        """Get all child options under a prefix (e.g., 'programs.vim')."""
        instance, index_data, scope_id = NuschtosSearch._get_project_context(project)

        # Search with prefix wildcard
        results = index_data.index.search(f"{prefix}.*", max_results=500, scope_id=scope_id)

        options = []
        prefix_dot = f"{prefix}."
        for result in results:
            if result.name.startswith(prefix_dot):
                opt_data = _get_option_by_idx(instance, result.idx, index_data)
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
