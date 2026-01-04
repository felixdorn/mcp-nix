.PHONY: lint check test fmt

lint:
	uv run ruff check --fix .
	uv run ruff format .
	uv run ty check mcp_nix

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run ty check mcp_nix

test:
	uv run pytest

fmt:
	uv run ruff format .
	cd pyixx && cargo fmt
