# 0002: Notebooks are the source

**Status:** Accepted, 1 November 2026. Reverses the "no notebooks" choice made when the
repository was reset.

## Context

The owner reads and reviews this project's code and finds plain `.py` modules hard to
follow. Notebooks put a short explanation and a worked example next to each
piece of code. The rest of the project (tests, CI, the agent, the baseline) still needs
ordinary importable modules.

## Decision

- **All code is written in Jupyter notebooks in `nbs/`.** Each notebook starts with a
  short intro and gives each function a one-line explanation.
- **`src/agentic_forecast_review/` is generated** from cells marked `#| export` by
  nbdev (`make export`). Generated files carry a "do not edit" header and are never
  edited by hand. `__init__.py` and `_modidx.py` are generated too.
- **Checks live in exactly one place.** Notebooks hold one to three worked examples per
  function: the normal case, with visible output and an `assert`. `tests/` (pytest)
  holds edge cases and rejection rules. A check never appears in both.
- **Outputs are stripped before commit** (`make clean-nbs`, also run by the pre-commit
  hook). CI regenerates `src/`, strips the notebooks, runs every check, and fails if
  anything differs from what was committed.
- No `from __future__ import annotations` in exported code: nbdev writes `__all__`
  first, and the project targets Python 3.12+.
- The seal verifier runs as `uv run verify-seal` instead of `python -m`.

## Consequences

- One more dev tool (nbdev) and one rule: edit the notebook, then `make export`.
- Module docstrings now live as notebook Markdown, not in the generated `.py` files.
- Code review on GitHub shows changes in both the notebook and the generated module.
