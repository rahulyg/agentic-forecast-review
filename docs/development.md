# Development

How the repository is built and checked. Prerequisite: [uv](https://docs.astral.sh/uv/),
which fetches a suitable Python if needed.

```
make install                # install everything (uv sync --locked)
uv run pre-commit install   # once per clone: strip outputs and regenerate src/ on commit
```

## Working on it

All code is written in `nbs/`; `src/` is generated from it and never edited by hand.
Open a notebook in VS Code and pick the `.venv` kernel. After changing a notebook:

```
make export      # regenerate src/ from the notebooks
make all         # export, strip outputs, lint, pytest, run the notebook examples
```

Notebooks show each function working on a normal example; `tests/` checks that bad
input is rejected. Each check lives in one place only.

Re-running `nbs/06_generator.ipynb` rewrites `cases/dev/fam_01/` with the same bytes;
a test fails if the committed snapshot ever differs from a fresh run.

Live model calls (from weekend 3) need `OPENROUTER_API_KEY` in the shell or in an
ignored repo-root `.env`. Nothing in the current code calls a model.

## Settings files

| File | What it is |
|---|---|
| `pyproject.toml` | Project name, Python version, libraries, tool settings |
| `uv.lock` | Exact library versions, so installs are identical everywhere |
| `Makefile` | Shortcuts: `make export`, `make test`, `make all` |
| `.github/workflows/ci.yml` | GitHub runs `make all` on every push and checks nothing changed |
| `.pre-commit-config.yaml` | Before each commit: regenerate `src/`, strip notebook outputs, lint |
| `.gitignore` | What git never uploads (`.env`, `.venv`, caches) |
| `.vscode/settings.json` | Points VS Code at the project's Python and runs notebooks from `nbs/` |
