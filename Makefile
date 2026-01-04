.PHONY: lint check test fmt pyixx-check

lint:
	uv run ruff check --fix .
	uv run ruff format .
	uv run ty check mcp_nix

pyixx-check:
	cd pyixx && cargo clippy --all-targets -- -D warnings

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run ty check mcp_nix

test:
	uv run pytest

fmt:
	uv run ruff format .
	cd pyixx && cargo fmt
