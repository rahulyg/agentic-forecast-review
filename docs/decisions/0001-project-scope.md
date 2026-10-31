# 0001: Project scope

**Status:** Accepted, 31 October 2026

## Context

The project needs a fixed scope that later work can be checked against. The full
reasoning is in [the Ground Zero plan](../ground-zero.md); this record keeps only the
decisions.

## Decision

- **What is built:** one read-only agent that reviews historical forecast performance
  and produces an evidence-linked review packet. Google ADK runs the loop; the model is
  reached through OpenRouter via ADK's LiteLLM support.
- **Boundary:** code owns all arithmetic, data access, validation and every displayed
  number. The model chooses tools and arguments, follows up, clarifies or stops, and
  explains. It never forecasts, retrains models or changes decisions.
- **Tools:** five typed, read-only tools — resolve review context, compare forecast
  runs, inspect selected series, check data quality, retrieve evidence rows.
- **Budget:** 8 model turns and 8 tool calls per run, retries included. Changes come
  only from the development-set pilot and are recorded here.
- **Terminal states:** ANSWER, CLARIFY, STOP_UNTRUSTWORTHY, INCOMPLETE.
- **Numbers:** the model writes pointer tokens; the packet assembler resolves them. A
  validator strips known identifiers and dates and rejects any remaining digit in free
  text.
- **Baseline:** a reasonable scripted report over the same tools, with no call limit,
  reading each case's structured `canonical_scope`. It is tagged `baseline-frozen`
  before the held-out seeds are sealed.
- **Inputs:** each case has `request_text` (agent) and `canonical_scope` (baseline).
  Ambiguous cases are scored as a separate slice, outside the paired comparison.
- **Data:** synthetic fixtures with planted defects and a hidden manifest. Real retail
  data is optional and only after everything else ships.
- **Kill gate:** weekend 3. Two matched cases must produce different tool sequences in
  at least 2 of 3 runs, diverging right after the first differing observation, with that
  observation in `observation_refs`, and both must end in the correct terminal state.
- **Not in version 1:** multiple agents, model training or promotion, inventory actions,
  new forecasting models, document search, long-term memory, fine-tuning, model routing.

## Consequences

- The evaluation can conclude that the script is as good or better; that result is
  published, not hidden.
- Any change that pushes the remaining estimate above about 100 hours is a scope change
  and needs a new decision record.
- No re-planning before 30 November 2026; ideas go to a parking-lot file.
