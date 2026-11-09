# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only MCP tools with typed results and bounded output."""

from functools import wraps
from inspect import signature
from threading import RLock
from typing import Annotated

from anyio.to_thread import run_sync
from fastmcp.exceptions import ToolError
from fastmcp.tools.tool import ToolResult
from pydantic import BaseModel, Field

from . import mcp
from .models import NoogleFunction, Package
from .nixhub import NixhubSearch, PackageNotFoundError, VersionNotFoundError
from .noogle import FunctionNotFoundError, NoogleSearch
from .options import InvalidProjectError, UnifiedOption, get_backend
from .responses import (
    CommitResponse,
    FunctionResponse,
    OptionResponse,
    SearchResponse,
    SourceResponse,
    VersionsResponse,
)
from .search import APIError, InvalidChannelError, NixOSSearch
from .sources import fetch_source

Limit = Annotated[int, Field(ge=1, le=100)]
LineLimit = Annotated[int, Field(ge=1, le=1000)]
Name = Annotated[str, Field(min_length=1)]
_LOCKS: dict[str, RLock] = {}


def _format_error(exc: Exception) -> str:
    if isinstance(exc, InvalidChannelError):
        return f"Error: Invalid channel '{exc.channel}'. Available: {', '.join(exc.available)}"
    if isinstance(exc, InvalidProjectError):
        return f"Error: Invalid project '{exc.project}'. Available: {', '.join(exc.available)}"
    if isinstance(exc, PackageNotFoundError):
        return f"Error: Package '{exc.name}' not found on nixhub"
    if isinstance(exc, VersionNotFoundError):
        versions = ", ".join(exc.available[:5])
        if len(exc.available) > 5:
            versions += f", ... ({len(exc.available)} total)"
        return f"Error: Version '{exc.version}' not found for '{exc.name}'. Available: {versions}"
    if isinstance(exc, FunctionNotFoundError):
        return f"Error: Function '{exc.path}' not found on Noogle"
    return f"Error: {exc}"


def _tool(schema: type[BaseModel]):
    def register(fn):
        sig = signature(fn)

        @wraps(fn)
        async def run(*args, **kwargs):
            arguments = sig.bind(*args, **kwargs).arguments
            project = arguments.get("project", "")
            if project:
                key = project if project in {"nixos", "homemanager", "nixvim", "nix-nomad"} else "nuschtos"
            elif fn.__name__ in {"search_nixpkgs", "read_derivation"}:
                key = "nixos"
            elif fn.__name__ in {"search_nix_stdlib", "help_for_stdlib_function"}:
                key = "noogle"
            else:
                key = "nixhub"
            lock = _LOCKS.setdefault(key, RLock())

            def invoke():
                # Serialize shared index/cache state per backend, while other backends and
                # the protocol event loop remain responsive. HTTP requests have timeouts.
                with lock:
                    try:
                        return fn(*args, **kwargs)
                    except APIError as exc:
                        raise ToolError(_format_error(exc)) from exc

            return await run_sync(invoke)

        return mcp.tool(
            title=fn.__name__.replace("_", " ").title(),
            annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
            output_schema=schema.model_json_schema(by_alias=False),
        )(run)

    return register


def _reply(response: BaseModel) -> ToolResult:
    data = response.model_dump(mode="json")
    return ToolResult(content=data["result"], structured_content=data)


def _query(value: str) -> str:
    value = value.strip()
    if not value:
        raise ToolError("Error: Search query must not be empty")
    return value


def _position_to_github_url(position: str, channel: str) -> str | None:
    if not position:
        return None
    branch = "nixos-unstable" if channel == "unstable" else f"nixos-{channel}"
    return f"https://github.com/NixOS/nixpkgs/blob/{branch}/{position.split(':')[0]}"


def _source(url: str, version: str, start_line: int, limit: int, warning: str | None = None) -> ToolResult:
    source = fetch_source(url)
    lines = source.content.splitlines()
    if start_line > max(1, len(lines)):
        raise ToolError(f"Error: start_line {start_line} exceeds source length ({len(lines)} lines)")
    end = min(len(lines), start_line - 1 + limit)
    excerpt = "\n".join(lines[start_line - 1 : end])
    text = (
        f"Note: {warning}\n\n" if warning else ""
    ) + f"Reference: {url}\nSource: lines {start_line}-{end} of {len(lines)}\n\n{excerpt}"
    next_line = end + 1 if end < len(lines) else None
    if next_line:
        text += f"\n\nMore lines available; call again with start_line={next_line}."
    return _reply(
        SourceResponse(
            result=text,
            url=url,
            start_line=start_line,
            end_line=end,
            total_lines=len(lines),
            next_start_line=next_line,
            version=version,
        )
    )


@_tool(SearchResponse[Package])
def search_nixpkgs(query: Name, channel: str = "unstable", limit: Limit = 20) -> ToolResult:
    """Search Nixpkgs package attributes, versions and descriptions.

    Use an exact returned attribute with read_derivation to read package source.
    channel is unstable or an available release; list_versions(project="nixos") lists releases.
    limit bounds the number of returned packages (1-100).
    """
    query = _query(query)
    result = NixOSSearch.search_packages(query, limit, channel)
    text = f"Showing {len(result.items)} of {result.total} packages:\n" + "\n\n".join(
        p.format_short() for p in result.items
    )
    if not result.items:
        text = f"No packages found matching '{query}'"
    return _reply(
        SearchResponse[Package](
            result=text, items=result.items, total=result.total, returned=len(result.items), version=channel
        )
    )


@_tool(SourceResponse)
def read_derivation(
    name: Name, channel: str = "unstable", start_line: Annotated[int, Field(ge=1)] = 1, limit: LineLimit = 200
) -> ToolResult:
    """Read a range of lines from a package's Nix source.

    name is an exact package attribute returned by search_nixpkgs.
    Follow next_start_line to read more. limit is 1-1000 lines; start_line is one-based.
    """
    package = NixOSSearch.get_package(name, channel)
    if package is None:
        raise ToolError(f"Error: Package '{name}' not found")
    url = _position_to_github_url(package.position, channel)
    if not url:
        raise ToolError(f"Error: No source position available for '{name}'")
    return _source(url, channel, start_line, limit)


@_tool(SearchResponse[UnifiedOption])
def search_options(project: Name, query: Name, version: str = "", limit: Limit = 20) -> ToolResult:
    """Search configuration options by name or description.

    project: nixos, homemanager, nixvim, nix-darwin, impermanence, microvm,
    simple-nixos-mailserver, sops-nix, nixos-hardware, disko, or nix-nomad.
    Use list_versions(project) to discover versions; an empty version uses the default.
    limit bounds the number of results (1-100).
    """
    backend = get_backend(project)
    effective, warning = backend.validate_version(version or backend.get_default_version())
    result = backend.search_options(_query(query), limit, effective)
    text = f"Showing {len(result.items)} of {result.total} options:\n" + "\n\n".join(
        o.format_short() for o in result.items
    )
    if not result.items:
        text = f"No {project} options found matching '{query}'"
    if warning:
        text = f"Note: {warning}\n\n{text}"
    return _reply(
        SearchResponse[UnifiedOption](
            result=text,
            items=result.items,
            total=result.total,
            returned=len(result.items),
            version=effective,
            warning=warning,
        )
    )


@_tool(VersionsResponse)
def list_versions(project: Name) -> ToolResult:
    """List valid versions for any project supported by search_options.

    Each record includes its canonical ID, display name and whether it is the default.
    """
    versions = get_backend(project).list_versions()
    return _reply(
        VersionsResponse(result=f"{project} versions:\n" + "\n\n".join(map(str, versions)), versions=versions)
    )


@_tool(OptionResponse)
def show_option_details(
    project: Name, name: Name, version: str = "", limit: Limit = 50, offset: Annotated[int, Field(ge=0)] = 0
) -> ToolResult:
    """Get an exact option, or a page of child options under a prefix.

    Supports the same projects as search_options. An empty version uses the default.
    For a prefix, follow next_offset until null to exhaust its children.
    limit is 1-100 children per call. Source references can be read with read_option_declaration.
    """
    backend = get_backend(project)
    effective, warning = backend.validate_version(version or backend.get_default_version())
    option = backend.get_option(name, effective)
    prefix = f"Note: {warning}\n\n" if warning else ""
    if option is not None:
        text = prefix + str(option)
        if option.declaration_url:
            text += f"\nReference: {option.declaration_url}"
        return _reply(OptionResponse(result=text, option=option, total=1, version=effective, warning=warning))
    children = sorted(backend.get_option_children(name, effective), key=lambda o: o.name)
    page = children[offset : offset + limit]
    next_offset = offset + len(page) if offset + len(page) < len(children) else None
    text = prefix + f"'{name}' has {len(children)} child options; showing {len(page)} from offset {offset}:\n"
    text += "\n\n".join(o.format_short() for o in page)
    if not children:
        text = prefix + f"No option or children found for '{name}'"
    elif next_offset is not None:
        text += f"\n\nMore children available; call again with offset={next_offset}."
    return _reply(
        OptionResponse(
            result=text,
            children=page,
            total=len(children),
            offset=offset,
            next_offset=next_offset,
            version=effective,
            warning=warning,
        )
    )


@_tool(SourceResponse)
def read_option_declaration(
    project: Name, name: Name, version: str = "", start_line: Annotated[int, Field(ge=1)] = 1, limit: LineLimit = 200
) -> ToolResult:
    """Read a range of lines from an option's Nix declaration.

    Supports the projects in search_options, except nix-nomad, whose declarations are generated.
    Use an exact option name. Follow next_start_line for additional source lines.
    """
    backend = get_backend(project)
    if not backend.supports_declaration_read():
        raise ToolError(
            f"Error: {project} options don't have readable declarations. "
            "They are auto-generated from external specifications (Nomad HCL)."
        )
    effective, warning = backend.validate_version(version or backend.get_default_version())
    option = backend.get_option(name, effective)
    if option is None:
        raise ToolError(f"Error: Option '{name}' not found")
    if not option.declaration_url:
        raise ToolError(f"Error: No declaration URL available for '{name}'")
    return _source(option.declaration_url, effective, start_line, limit, warning)


@_tool(CommitResponse)
def find_nixpkgs_commit_with_package_version(name: Name, version: Name) -> ToolResult:
    """Find the nixpkgs commit and attribute for an exact package version using NixHub.

    If the package or version is unavailable, returns an error with available-version hints.
    """
    commit = NixhubSearch.get_commit(name, version)
    return _reply(CommitResponse(result=str(commit), commit=commit))


@_tool(SearchResponse[NoogleFunction])
def search_nix_stdlib(query: Name, limit: Limit = 20) -> ToolResult:
    """Search Nix function paths, aliases, signatures and documentation on Noogle.

    Use help_for_stdlib_function with an exact returned path for complete documentation.
    limit is 1-100 functions.
    """
    result = NoogleSearch.search_functions(_query(query), limit)
    text = f"Showing {len(result.items)} of {result.total} functions:\n" + "\n\n".join(
        f.format_short() for f in result.items
    )
    if not result.items:
        text = f"No Nix stdlib functions found matching '{query}'"
    return _reply(
        SearchResponse[NoogleFunction](result=text, items=result.items, total=result.total, returned=len(result.items))
    )


@_tool(FunctionResponse)
def help_for_stdlib_function(path: Name) -> ToolResult:
    """Read the signature, arguments, examples and source reference for a Nix function.

    path is a function path or alias, e.g. lib.strings.splitString or builtins.map.
    """
    function = NoogleSearch.get_function(path)
    return _reply(FunctionResponse(result=str(function), function=function))
