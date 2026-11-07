.PHONY: install export clean-nbs lint test nbtest seal all

install:
	uv sync --locked

# The notebooks in nbs/ are the source. This regenerates src/ from them.
export:
	uv run nbdev-export
	uv run ruff format --quiet src/

# Strip outputs and execution counts so notebooks are committed clean.
clean-nbs:
	uv run nbdev-clean

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy --strict src/

# Edge cases and rejection rules.
test:
	uv run pytest

# The worked examples inside the notebooks.
nbtest:
	uv run nbdev-test

# The sealed held-out seeds still match their public manifest (no decryption).
seal:
	uv run verify-seal

all:
	$(MAKE) export
	$(MAKE) clean-nbs
	$(MAKE) lint
	$(MAKE) test
	$(MAKE) nbtest
	$(MAKE) seal
