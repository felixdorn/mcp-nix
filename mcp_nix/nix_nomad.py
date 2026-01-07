# SPDX-License-Identifier: GPL-3.0-or-later
"""nix-nomad option search via HTML parsing."""

import json
import time
from pathlib import Path

import platformdirs
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, field_validator

from .models import SearchResult, _lines
from .search import APIError
from .utils import html_to_text

NIX_NOMAD_URL = "https://tristanpemble.github.io/nix-nomad/"
CACHE_MAX_AGE_SECONDS = 60 * 60  # 1 hour

# In-memory cache for parsed options
_options_cache: dict[str, "NixNomadOption"] | None = None
_cache_loaded_at: float = 0


class NixNomadOption(BaseModel):
    """nix-nomad configuration option."""

    name: str
    type: str = ""
    description: str = ""
    default: str = Field(default="")
    example: str = Field(default="")

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
        return _lines(
            ("Option", self.name),
            ("Type", self.type),
            ("Description", self.description),
            ("Default", self.default),
            ("Example", self.example),
        )


def _get_cache_dir() -> Path:
    """Get the cache directory for nix-nomad data."""
    cache_dir = Path(platformdirs.user_cache_dir("mcp-nix")) / "nix-nomad"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _load_cached_html() -> str | None:
    """Load HTML from cache if valid (1 hour TTL)."""
    cache_dir = _get_cache_dir()
    html_path = cache_dir / "index.html"
    meta_path = cache_dir / "meta.json"

    if not html_path.exists() or not meta_path.exists():
        return None

    try:
        meta = json.loads(meta_path.read_text())
        cached_at = meta.get("cached_at", 0)
        if time.time() - cached_at > CACHE_MAX_AGE_SECONDS:
            return None
        return html_path.read_text()
    except (OSError, json.JSONDecodeError):
        return None


def _save_html_to_cache(html: str) -> None:
    """Save HTML to cache."""
    cache_dir = _get_cache_dir()
    html_path = cache_dir / "index.html"
    meta_path = cache_dir / "meta.json"

    html_path.write_text(html)
    meta_path.write_text(json.dumps({"cached_at": time.time()}))


def _fetch_html() -> str:
    """Fetch the nix-nomad documentation HTML."""
    try:
        resp = requests.get(NIX_NOMAD_URL, timeout=30)
        resp.raise_for_status()
        return resp.text
    except requests.Timeout as exc:
        raise APIError("Connection timed out fetching nix-nomad documentation") from exc
    except requests.HTTPError as exc:
        raise APIError(f"Failed to fetch nix-nomad documentation: {exc}") from exc


def _parse_options(html: str) -> dict[str, NixNomadOption]:
    """Parse options from the DocBook HTML documentation."""
    soup = BeautifulSoup(html, "html.parser")
    options: dict[str, NixNomadOption] = {}

    # Find all option entries in the variablelist
    # Structure: <dl class="variablelist"><dt>...<a id="opt-{name}">...
    for dt in soup.find_all("dt"):
        # Get option name from the anchor id or code element
        anchor = dt.find("a", id=lambda x: x and x.startswith("opt-"))
        if not anchor:
            continue

        code = dt.find("code", class_="option")
        if not code:
            continue

        name = code.get_text(strip=True)
        if not name:
            continue

        # Get the corresponding dd element
        dd = dt.find_next_sibling("dd")
        if not dd:
            continue

        # Parse fields from dd
        option_type = ""
        description = ""
        default = ""
        example = ""

        # Process paragraphs
        paragraphs = dd.find_all("p", recursive=False)
        for i, p in enumerate(paragraphs):
            text = p.get_text(strip=True)
            em = p.find("em")

            if em:
                em_text = em.get_text(strip=True)
                if em_text == "Type:":
                    # Type is the rest of the paragraph
                    em.decompose()
                    option_type = p.get_text(strip=True)
                elif em_text == "Default:":
                    # Default may be in a code block or literal
                    em.decompose()
                    code_block = p.find("code")
                    default = code_block.get_text(strip=True) if code_block else p.get_text(strip=True)
                elif em_text == "Example:":
                    # Example may be in a pre block following this p
                    em.decompose()
                    pre = p.find_next_sibling("pre")
                    if pre:
                        example = pre.get_text(strip=True)
                    else:
                        code_block = p.find("code")
                        example = code_block.get_text(strip=True) if code_block else p.get_text(strip=True)
                elif em_text == "Declared by:":
                    pass  # Skip declaration info
            elif i == 0 and not text.startswith(("Type:", "Default:", "Example:", "Declared by:")):
                # First paragraph without em label is the description
                description = text

        options[name] = NixNomadOption(
            name=name,
            type=option_type,
            description=description,
            default=default,
            example=example,
        )

    return options


def _get_options() -> dict[str, NixNomadOption]:
    """Get all options, loading from cache or fetching as needed."""
    global _options_cache, _cache_loaded_at

    # Check in-memory cache
    if _options_cache is not None and time.time() - _cache_loaded_at < CACHE_MAX_AGE_SECONDS:
        return _options_cache

    # Try disk cache
    html = _load_cached_html()
    if html is None:
        html = _fetch_html()
        _save_html_to_cache(html)

    # Parse options
    _options_cache = _parse_options(html)
    _cache_loaded_at = time.time()

    return _options_cache


class NixNomadSearch:
    """nix-nomad option search functionality."""

    @staticmethod
    def search_options(query: str, limit: int) -> SearchResult[NixNomadOption]:
        """Search for nix-nomad options by name or description."""
        options = _get_options()
        query_lower = query.lower()

        # Score options by relevance
        scored: list[tuple[int, NixNomadOption]] = []
        for opt in options.values():
            score = 0
            name_lower = opt.name.lower()
            desc_lower = opt.description.lower()

            # Exact name match
            if query_lower == name_lower:
                score = 1000
            # Name starts with query
            elif name_lower.startswith(query_lower):
                score = 100
            # Query in name
            elif query_lower in name_lower:
                score = 50
            # Query in description
            elif query_lower in desc_lower:
                score = 10

            if score > 0:
                scored.append((score, opt))

        # Sort by score descending
        scored.sort(key=lambda x: (-x[0], x[1].name))

        results = [opt for _, opt in scored[:limit]]
        return SearchResult(items=results, total=len(scored))

    @staticmethod
    def get_option(name: str) -> NixNomadOption | None:
        """Get an option by exact name."""
        options = _get_options()
        return options.get(name)

    @staticmethod
    def get_option_children(prefix: str) -> list[NixNomadOption]:
        """Get all child options under a prefix."""
        options = _get_options()
        prefix_dot = f"{prefix}."

        children = []
        for name, opt in options.items():
            if name.startswith(prefix_dot):
                children.append(opt)

        # Sort by name
        children.sort(key=lambda x: x.name)
        return children
