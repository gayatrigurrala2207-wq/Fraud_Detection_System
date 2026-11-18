.PHONY: setup test check

setup:
	cd backend && uv sync --locked

test:
	cd backend && uv run --locked python -m pytest

check:
	cd backend && uv lock --check
	cd backend && uv run --locked python -m pytest
