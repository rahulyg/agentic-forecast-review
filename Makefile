.PHONY: install lint test all

install:
	uv sync --locked

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy --strict src/

test:
	uv run pytest

all:
	$(MAKE) lint
	$(MAKE) test
