# SPDX-License-Identifier: GPL-3.0-or-later
"""Unified options abstraction layer for all Nix projects."""

from dataclasses import dataclass
from typing import Protocol

from .cache import APIError
from .models import SearchResult, _lines

# =============================================================================
# Models
# =============================================================================


@dataclass
class UnifiedOption:
    """Normalized option representation for all projects."""

    name: str
    type: str
    description: str
    default: str
    example: str
    declaration_url: str | None
    project: str

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


@dataclass
class VersionInfo:
    """Version/channel metadata."""

    id: str
    name: str
    is_default: bool = False

    def __str__(self) -> str:
        default_marker = " (default)" if self.is_default else ""
        return f"• {self.name}{default_marker}"


# =============================================================================
# Exceptions
# =============================================================================


class InvalidProjectError(APIError):
    """Raised when an invalid project is specified."""

    def __init__(self, project: str, available: list[str]):
        self.project = project
        self.available = available
        super().__init__(f"Invalid project: {project}. Available: {', '.join(available)}")


# =============================================================================
# Protocol
# =============================================================================


class OptionsBackend(Protocol):
    """Protocol for project-specific option backends."""

    def search_options(self, query: str, limit: int, version: str) -> SearchResult[UnifiedOption]:
        """Search for options."""
        ...

    def get_option(self, name: str, version: str) -> UnifiedOption | None:
        """Get option by exact name."""
        ...

    def get_option_children(self, prefix: str, version: str) -> list[UnifiedOption]:
        """Get all child options under a prefix."""
        ...

    def list_versions(self) -> list[VersionInfo]:
        """List available versions."""
        ...

    def get_default_version(self) -> str:
        """Get the default version."""
        ...

    def validate_version(self, version: str) -> tuple[str, str | None]:
        """Validate version, returns (effective_version, warning_or_none)."""
        ...

    def supports_declaration_read(self) -> bool:
        """Whether this backend supports reading declaration source code."""
        ...


# =============================================================================
# Client classes (thin wrappers around existing search modules)
# =============================================================================


class NixOSClient:
    """Client wrapping search.py NixOSSearch."""

    def __init__(self):
        from .search import NixOSSearch

        self._search = NixOSSearch

    def search_options(self, query: str, limit: int, channel: str):
        return self._search.search_options(query, limit, channel)

    def get_option(self, name: str, channel: str):
        return self._search.get_option(name, channel)

    def get_option_children(self, prefix: str, channel: str):
        return self._search.get_option_children(prefix, channel)

    def list_channels(self):
        return self._search.list_channels()


class HomeManagerClient:
    """Client wrapping homemanager.py HomeManagerSearch."""

    def __init__(self):
        from .homemanager import HomeManagerSearch

        self._search = HomeManagerSearch

    def search_options(self, query: str, limit: int, release: str):
        return self._search.search_options(query, limit, release)

    def get_option(self, name: str, release: str):
        return self._search.get_option(name, release)

    def get_option_children(self, prefix: str, release: str):
        return self._search.get_option_children(prefix, release)

    def list_releases(self):
        return self._search.list_releases()


class NuschtosClient:
    """Client wrapping nuschtos.py NuschtosSearch."""

    def __init__(self):
        from .nuschtos import NuschtosSearch

        self._search = NuschtosSearch

    def search_options(self, query: str, limit: int, project: str):
        return self._search.search_options(query, limit, project)

    def get_option(self, name: str, project: str):
        return self._search.get_option(name, project)

    def get_option_children(self, prefix: str, project: str):
        return self._search.get_option_children(prefix, project)


class NixNomadClient:
    """Client wrapping nix_nomad.py NixNomadSearch."""

    def __init__(self):
        from .nix_nomad import NixNomadSearch

        self._search = NixNomadSearch

    def search_options(self, query: str, limit: int):
        return self._search.search_options(query, limit)

    def get_option(self, name: str):
        return self._search.get_option(name)

    def get_option_children(self, prefix: str):
        return self._search.get_option_children(prefix)


# =============================================================================
# Backend implementations
# =============================================================================


def _nixos_decl_to_github_url(decl: str, channel: str) -> str:
    """Convert NixOS declaration path to GitHub URL."""
    branch = "nixos-unstable" if channel == "unstable" else f"nixos-{channel}"
    return f"https://github.com/NixOS/nixpkgs/blob/{branch}/{decl}"


class NixOSOptionsBackend:
    """Backend for NixOS options."""

    def __init__(self):
        self._client = NixOSClient()

    def search_options(self, query: str, limit: int, version: str) -> SearchResult[UnifiedOption]:
        result = self._client.search_options(query, limit, version)
        items = [self._to_unified(opt, version) for opt in result.items]
        return SearchResult(items=items, total=result.total)

    def get_option(self, name: str, version: str) -> UnifiedOption | None:
        opt = self._client.get_option(name, version)
        if opt is None:
            return None
        return self._to_unified(opt, version)

    def get_option_children(self, prefix: str, version: str) -> list[UnifiedOption]:
        children = self._client.get_option_children(prefix, version)
        return [self._to_unified(opt, version) for opt in children]

    def list_versions(self) -> list[VersionInfo]:
        channels = self._client.list_channels()
        return [VersionInfo(id=ch.id, name=f"{ch.id} ({ch.branch})", is_default=ch.is_default) for ch in channels]

    def get_default_version(self) -> str:
        return "unstable"

    def validate_version(self, version: str) -> tuple[str, str | None]:
        channels = self._client.list_channels()
        valid_ids = [ch.id for ch in channels]
        if version in valid_ids:
            return (version, None)
        default = self.get_default_version()
        return (default, f"Version '{version}' not found, using '{default}' instead.")

    def supports_declaration_read(self) -> bool:
        return True

    def _to_unified(self, opt, version: str) -> UnifiedOption:
        from .models import Option

        assert isinstance(opt, Option)
        decl_url = _nixos_decl_to_github_url(opt.declarations[0], version) if opt.declarations else None
        return UnifiedOption(
            name=opt.name,
            type=opt.type,
            description=opt.description,
            default=opt.default,
            example=opt.example,
            declaration_url=decl_url,
            project="nixos",
        )


class HomeManagerOptionsBackend:
    """Backend for Home Manager options."""

    def __init__(self):
        self._client = HomeManagerClient()

    def search_options(self, query: str, limit: int, version: str) -> SearchResult[UnifiedOption]:
        result = self._client.search_options(query, limit, version)
        items = [self._to_unified(opt) for opt in result.items]
        return SearchResult(items=items, total=result.total)

    def get_option(self, name: str, version: str) -> UnifiedOption | None:
        opt = self._client.get_option(name, version)
        if opt is None:
            return None
        return self._to_unified(opt)

    def get_option_children(self, prefix: str, version: str) -> list[UnifiedOption]:
        children = self._client.get_option_children(prefix, version)
        return [self._to_unified(opt) for opt in children]

    def list_versions(self) -> list[VersionInfo]:
        releases = self._client.list_releases()
        return [VersionInfo(id=r.value, name=r.name, is_default=r.is_default) for r in releases]

    def get_default_version(self) -> str:
        return "unstable"

    def validate_version(self, version: str) -> tuple[str, str | None]:
        releases = self._client.list_releases()
        valid_names = [r.name for r in releases]
        valid_values = [r.value for r in releases]
        if version in valid_names or version in valid_values or version == "unstable":
            return (version, None)
        default = self.get_default_version()
        return (default, f"Version '{version}' not found, using '{default}' instead.")

    def supports_declaration_read(self) -> bool:
        return True

    def _to_unified(self, opt) -> UnifiedOption:
        from .models import HomeManagerOption

        assert isinstance(opt, HomeManagerOption)
        decl_url = opt.declarations[0].get("url") if opt.declarations else None
        return UnifiedOption(
            name=opt.title,  # Home Manager uses 'title' instead of 'name'
            type=opt.type,
            description=opt.description,
            default=opt.default,
            example=opt.example,
            declaration_url=decl_url,
            project="homemanager",
        )


class NuschtosOptionsBackend:
    """Backend for NüschtOS-based projects (nixvim, nix-darwin, impermanence, microvm)."""

    def __init__(self, project_id: str):
        self._client = NuschtosClient()
        self._project_id = project_id

    def search_options(self, query: str, limit: int, version: str) -> SearchResult[UnifiedOption]:
        # Version is ignored - these projects don't have versions
        result = self._client.search_options(query, limit, self._project_id)
        items = [self._to_unified(opt) for opt in result.items]
        return SearchResult(items=items, total=result.total)

    def get_option(self, name: str, version: str) -> UnifiedOption | None:
        opt = self._client.get_option(name, self._project_id)
        if opt is None:
            return None
        return self._to_unified(opt)

    def get_option_children(self, prefix: str, version: str) -> list[UnifiedOption]:
        children = self._client.get_option_children(prefix, self._project_id)
        return [self._to_unified(opt) for opt in children]

    def list_versions(self) -> list[VersionInfo]:
        return [VersionInfo(id="latest", name="latest", is_default=True)]

    def get_default_version(self) -> str:
        return "latest"

    def validate_version(self, version: str) -> tuple[str, str | None]:
        # Only "latest" is valid
        if version == "latest" or version == "":
            return ("latest", None)
        return ("latest", f"Version '{version}' not found, using 'latest' instead.")

    def supports_declaration_read(self) -> bool:
        return True

    def _to_unified(self, opt) -> UnifiedOption:
        from .nuschtos import NuschtoOption

        assert isinstance(opt, NuschtoOption)
        decl_url = opt.declarations[0] if opt.declarations else None
        return UnifiedOption(
            name=opt.name,
            type=opt.type,
            description=opt.description,
            default=opt.default,
            example=opt.example,
            declaration_url=decl_url,
            project=self._project_id,
        )


class NixNomadOptionsBackend:
    """Backend for nix-nomad options."""

    def __init__(self):
        self._client = NixNomadClient()

    def search_options(self, query: str, limit: int, version: str) -> SearchResult[UnifiedOption]:
        result = self._client.search_options(query, limit)
        items = [self._to_unified(opt) for opt in result.items]
        return SearchResult(items=items, total=result.total)

    def get_option(self, name: str, version: str) -> UnifiedOption | None:
        opt = self._client.get_option(name)
        if opt is None:
            return None
        return self._to_unified(opt)

    def get_option_children(self, prefix: str, version: str) -> list[UnifiedOption]:
        children = self._client.get_option_children(prefix)
        return [self._to_unified(opt) for opt in children]

    def list_versions(self) -> list[VersionInfo]:
        return [VersionInfo(id="latest", name="latest", is_default=True)]

    def get_default_version(self) -> str:
        return "latest"

    def validate_version(self, version: str) -> tuple[str, str | None]:
        if version == "latest" or version == "":
            return ("latest", None)
        return ("latest", f"Version '{version}' not found, using 'latest' instead.")

    def supports_declaration_read(self) -> bool:
        # nix-nomad options are auto-generated from Nomad HCL, no readable source
        return False

    def _to_unified(self, opt) -> UnifiedOption:
        from .nix_nomad import NixNomadOption

        assert isinstance(opt, NixNomadOption)
        return UnifiedOption(
            name=opt.name,
            type=opt.type,
            description=opt.description,
            default=opt.default,
            example=opt.example,
            declaration_url=None,
            project="nix-nomad",
        )


# =============================================================================
# Registry
# =============================================================================

SUPPORTED_PROJECTS = [
    "nixos",
    "homemanager",
    "nixvim",
    "nix-darwin",
    "impermanence",
    "microvm",
    "simple-nixos-mailserver",
    "sops-nix",
    "nixos-hardware",
    "disko",
    "nix-nomad",
]

# Lazy-loaded backend instances
_backend_instances: dict[str, OptionsBackend] = {}


def _create_backend(project: str) -> OptionsBackend:
    """Create a backend instance for a project."""
    if project == "nixos":
        return NixOSOptionsBackend()
    elif project == "homemanager":
        return HomeManagerOptionsBackend()
    elif project in (
        "nixvim",
        "nix-darwin",
        "impermanence",
        "microvm",
        "simple-nixos-mailserver",
        "sops-nix",
        "nixos-hardware",
        "disko",
    ):
        return NuschtosOptionsBackend(project)
    elif project == "nix-nomad":
        return NixNomadOptionsBackend()
    else:
        raise InvalidProjectError(project, SUPPORTED_PROJECTS)


def get_backend(project: str) -> OptionsBackend:
    """Get the backend for a project (lazy-loaded singleton)."""
    if project not in SUPPORTED_PROJECTS:
        raise InvalidProjectError(project, SUPPORTED_PROJECTS)

    if project not in _backend_instances:
        _backend_instances[project] = _create_backend(project)

    return _backend_instances[project]
