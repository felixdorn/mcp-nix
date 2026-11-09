# Contributing to mcp-nix

Use Python 3.13, [uv](https://docs.astral.sh/uv/), and a Rust toolchain. `nix develop` provides the development environment. Python commands run through `uv`; the lockfile includes the local `pyixx` workspace.

```sh
uv sync --locked
make check
make pyixx-check
make test
```

`make test` runs deterministic backend, cache, protocol, and actual stdio-process tests without contacting public services. Fixtures should resemble upstream responses and cover schema changes and error recovery. The protocol tests assert `isError`, output schemas, concurrency, and pagination.

```sh
make test-live
nix build .#checks.$(nix eval --impure --raw --expr builtins.currentSystem).startup --no-link
```

`make test-live` explicitly exercises public services. It checks successful results and stable properties rather than snapshotting changing versions, documentation, or source revisions. Use `XDG_CACHE_HOME` to choose a fresh cache directory when diagnosing upstream failures. CI runs live checks daily and on manual dispatch; PR checks use deterministic tests and Nix startup checks on Linux and macOS.

## Architecture

- `__init__.py` owns the FastMCP instance, `ALL_TOOLS`, and the `--exclude` CLI flag.
- `tools.py` registers nine read-only tools. Its decorator dispatches synchronous backend work to worker threads and serializes shared state per backend. HTTP requests have bounded timeouts; cancellation does not forcibly interrupt an in-flight synchronous request.
- `responses.py` defines typed output schemas. Results retain readable text in `content` and expose typed fields in `structuredContent`.
- `options.py` adapts NixOS, Home Manager, NüschtOS, and nix-nomad into a common option interface.
- `cache.py` validates responses before storing them, distinguishes request parameters and headers, and translates HTTP/connection failures into `APIError`.
- `noogle.py` uses Noogle's JSON dataset. `nixhub.py` uses Jetify's documented v2 package API.
- `pyixx/` wraps the pinned upstream binary index reader. Deployment configuration supplies scope names and chunk size separately from the current index format.

## Adding or changing tools

Register the handler in `tools.py` using `_tool(YourResponseModel)` and add its name to `ALL_TOOLS`. Return `_reply(YourResponseModel(...))`; keep the text useful and the structured data consistent with the schema. Raise `ToolError` for explicit failures or `APIError` for backend failures. Empty search matches are successful empty results.

Include input bounds, accurate descriptions, deterministic protocol tests, and an opt-in live smoke case if the tool depends on an external service. Search results should identify canonical attributes/paths and effective versions. Sources and child lists must have explicit limits and continuation fields. Update the README's tool table when adding a tool.

## Changing backends and caches

Use `get_cache(namespace).request(url, callback, ...)`. The callback parses and validates a response; an incompatible cached response is evicted and fetched once more. Invalid fresh responses are not cached. Raise actionable `APIError` messages when an upstream schema is missing, rather than returning an empty catalog.

Cache mutable data with a TTL. In-memory indexes must expire too. For an index and associated chunks, partition caches by index generation and verify the returned record matches the indexed name. Do not cache deployment-relative chunks forever.

For Python formatting and types, run `make check` or `make lint`. For the native extension, run `make pyixx-check` and `cargo fmt --manifest-path pyixx/Cargo.toml`.

## Releases

The catalog-format update requires `pyixx` 0.2.0. Publish that version using the existing **Publish pyixx** workflow before publishing an mcp-nix release with the new dependency. Local workspace and Nix builds use the source checkout and do not need a PyPI release.

The Python package currently supports Python 3.13 and FastMCP 2.14.2 through the 2.x series. Major SDK upgrades need separate compatibility tests for installed clients and stdio lifecycle changes; updating the lockfile alone does not establish compatibility.
