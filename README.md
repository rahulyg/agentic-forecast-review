# agentic-forecast-review

Code owns the numbers; the model owns bounded choices. An evidence-linked agent loop and offline evaluation suite for time-series review.

Analytics agents are hard to trust when free-text generation and arithmetic are mixed. This repository separates them: deterministic code computes every metric, and a bounded agent loop decides what to inspect next. Working over versioned, fingerprinted data snapshots with planted defects, the agent investigates apparent forecast deterioration, checks data quality before blaming the model, and is designed to compile a review packet in which no number appears in free text. The evaluation compares the agent's adaptive branching against a frozen scripted baseline.

**Status: design stage.** The foundation code below exists and is tested; the tools, agent loop, baseline and evaluation are not built yet, and no results exist. The full plan is in [docs/ground-zero.md](docs/ground-zero.md) ([printable PDF](docs/ground-zero.pdf)).

![System at a glance](docs/figures/02-system-at-a-glance.svg)

## How it works

1. A test case asks something like *"Which store-category forecasts need review this period? Is the apparent deterioration a data issue or a consistent miss?"*
2. A single agent (Google ADK, model via OpenRouter) answers it by calling five typed, read-only tools: resolve review context, compare forecast runs, inspect selected series, check data quality, retrieve evidence rows. It has at most 8 model turns and 8 tool calls.
3. Every run ends in one of four states — ANSWER, CLARIFY, STOP (comparison untrustworthy) or INCOMPLETE — and produces a review packet: findings linked to source rows, what is not established, the tool trace and the cost.
4. The model writes pointer tokens such as `{ev:cmp2.n_actual}`; code fills in every number from validated tool fields.
5. A scripted Python report gets the same tools and the same cases, with no call limit, and is frozen before any held-out case is unsealed. Code and a human rubric grade both; results are reported as paired `k/n` counts by case family.

A fair result may favour the script. That is a valid outcome and will be published as such.

## Results

No evaluation has been run. Results arrive in weekend 6 of the [schedule](docs/ground-zero.md#10-schedule-gates-and-limits).

## What's in this folder

**The project.** All code is written in notebooks; you only ever edit `nbs/`.

```
nbs/                            the source: explanation + code + worked examples
  00_fixtures.ipynb               load a series, split at origin, seasonal-naive
  01_metrics.ipynb                MAE and signed bias
  02_evidence.ipynb               evidence rows with stable, addressable row IDs
  03_schemas.ipynb                contracts for cases, manifest, tool calls, trace, packets
  04_sealing.ipynb                verifier for the sealed held-out case seeds
  05_credentials.ipynb            OpenRouter API key lookup
  06_generator.ipynb              builds the synthetic sales snapshot (actuals, forecasts, row IDs)
  90_explore_fixture_data.ipynb   a guided look at the data; nothing exported
  data/                           small sample data the examples use
src/agentic_forecast_review/    generated from nbs/ by `make export`; never edit by hand
cases/dev/fam_01/               the generated snapshot (written by 06_generator; don't edit)
tests/                          edge cases and rejection rules (pytest)
docs/
  ground-zero.md                  the project plan (+ ground-zero.pdf, figures/)
  decisions/                      decision records
  sealing.md                      how held-out seeds are sealed with age
  parking-lot.md                  ideas deferred for later
```

Notebooks show each function working on a normal example; `tests/` checks that bad
input is rejected. Each check lives in one place only.

**Settings files tools look for by name.** You don't edit these by hand.

| File | What it is |
|---|---|
| `pyproject.toml` | Project name, Python version, libraries, tool settings |
| `uv.lock` | Exact library versions, so installs are identical everywhere |
| `Makefile` | Shortcuts: `make export`, `make test`, `make all` |
| `.github/workflows/ci.yml` | GitHub runs `make all` on every push |
| `.pre-commit-config.yaml` | Before each commit: regenerate `src/`, strip notebook outputs, lint |
| `.gitignore` | What git never uploads (`.env`, `.venv`, caches) |

`README.md` is this page; `LICENSE` is MIT.

## Running it

Prerequisites: [uv](https://docs.astral.sh/uv/). uv fetches a suitable Python if needed.

```
make install     # install everything (uv sync --locked)
uv run pre-commit install   # once per clone: strip outputs and regenerate src/ on commit
```

Open a notebook in `nbs/` in VS Code and pick the `.venv` kernel. After changing a
notebook:

```
make export      # regenerate src/ from the notebooks
make all         # export, strip outputs, lint, pytest, run the notebook examples
```

Live model calls will need `OPENROUTER_API_KEY` in your shell or in an ignored repo-root `.env`. Nothing in the current code calls a model.

## License

MIT
