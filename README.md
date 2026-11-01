# agentic-forecast-review

Code owns the numbers; the model owns bounded choices. An evidence-linked agent loop and offline evaluation suite for time-series review.

**Status: in progress, weekend 2 of 7.** Built and tested so far: the contracts, the metrics, the evidence rows and the synthetic data generator. The tools, agent loop, baseline and evaluation are not built yet, and no results exist. The full plan is in [docs/ground-zero.md](docs/ground-zero.md) ([printable PDF](docs/ground-zero.pdf)).

![System at a glance](docs/figures/02-system-at-a-glance.svg)

## The problem

Analytics agents are hard to trust when free-text generation and arithmetic are mixed: a fluent answer can carry a wrong number, and nothing shows where it came from. This project separates the two. Deterministic code computes every metric, and a bounded agent loop only decides what to inspect next. Working over versioned, fingerprinted data snapshots with planted defects, the agent investigates apparent forecast deterioration, checks data quality before blaming the model, and compiles a review packet in which no number appears in free text. The evaluation compares the agent's adaptive branching against a frozen scripted baseline.

## How it works

1. A test case asks something like *"Which store-category forecasts need review this period? Is the apparent deterioration a data issue or a consistent miss?"*
2. A single agent (Google ADK, model via OpenRouter) answers it by calling five typed, read-only tools: resolve review context, compare forecast runs, inspect selected series, check data quality, retrieve evidence rows. It has at most 8 model turns and 8 tool calls.
3. Every run ends in one of four states — ANSWER, CLARIFY, STOP (comparison untrustworthy) or INCOMPLETE — and produces a review packet: findings linked to source rows, what is not established, the tool trace and the cost.
4. The model writes pointer tokens such as `{ev:cmp2.n_actual}`; code fills in every number from validated tool fields.
5. A scripted Python report gets the same tools and the same cases, with no call limit, and is frozen before any held-out case is unsealed. Code and a human rubric grade both; results are reported as paired `k/n` counts by case family.

A fair result may favour the script. That is a valid outcome and will be published as such.

## Results

No evaluation has been run. Results arrive in weekend 6 of the [schedule](docs/ground-zero.md#10-schedule-gates-and-limits).

## Design decisions

- **One agent, five read-only tools, a hard budget.** Scope and limits are fixed up front so later work can be checked against them ([0001](docs/decisions/0001-project-scope.md)).
- **Numbers only through pointer tokens.** The model cites a tool's named field; it never types a number. A validator rejects any stray digit.
- **Planted defects, hidden answer key.** Each test snapshot carries one known condition (missing days, a biased model, a version mismatch, …); only the grader sees which.
- **A frozen baseline, sealed held-out cases.** The scripted report is tagged before the held-out seeds are decrypted, so it cannot be tuned to them ([sealing](docs/sealing.md)).
- **Notebooks are the source.** Every module is written as a notebook with explanation and worked examples; the Python package is generated from them ([0002](docs/decisions/0002-notebooks-are-the-source.md)).

## What's here

```
nbs/                            the source: explanation + code + worked examples
  00_fixtures.ipynb               load a series, split at origin, seasonal-naive
  01_metrics.ipynb                MAE and signed bias
  02_evidence.ipynb               evidence rows with stable, addressable row IDs
  03_schemas.ipynb                contracts for cases, manifest, tool calls, trace, packets
  04_sealing.ipynb                verifier for the sealed held-out case seeds
  05_credentials.ipynb            OpenRouter API key lookup
  06_generator.ipynb              the synthetic sales snapshot: actuals, forecasts, row IDs
  90_explore_fixture_data.ipynb   a guided, charted look at the data
src/agentic_forecast_review/    generated from nbs/
cases/dev/                      generated snapshots
tests/                          edge cases and rejection rules
docs/                           the plan, decision records, figures, sealing, parking lot
```

## Verifying

Everything runs offline with no paid model calls. CI regenerates the code from the notebooks, runs every notebook example and every test, and fails if the committed snapshot differs from a fresh run. Setup and commands are in [docs/development.md](docs/development.md).

## License

MIT
