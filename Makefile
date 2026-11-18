.PHONY: setup test check

setup:
	uv sync --locked

test:
	uv run --locked python -m pytest

check:
	uv lock --check
	uv run --locked python -m pytest
