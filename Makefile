.PHONY: lint check test test-live fmt pyixx-check

lint:
	uv run --locked ruff check --fix .
	uv run --locked ruff format .
	uv run --locked ty check mcp_nix

pyixx-check:
	uv run --locked cargo clippy --manifest-path pyixx/Cargo.toml --locked --all-targets -- -D warnings

check:
	uv run --locked ruff check .
	uv run --locked ruff format --check .
	uv run --locked ty check mcp_nix

test:
	uv run --locked pytest

test-live:
	uv run --locked pytest -m live

fmt:
	uv run --locked ruff format .
	cd pyixx && cargo fmt
