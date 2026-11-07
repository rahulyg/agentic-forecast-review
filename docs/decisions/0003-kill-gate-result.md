# 0003: Kill-gate result (weekend 3)

**Status:** Recorded, 7 November 2026. The gate **failed** by the criterion in the plan.
Whether to revise the criterion is the owner's decision and is still open; nothing after
weekend 3 starts until it is made.

## Context

The kill gate tests the project's premise on the matched pair `fam_01__c2` (four actual
days missing in the review period; expected STOP_UNTRUSTWORTHY) and `fam_01__c6` (clean
data, the model really under-forecasts; expected ANSWER). Both cases send the same
request, and in both the error looks worse. The criterion (plan, section 10), checked by
code in `nbs/11_kill_gate`, must hold in at least 2 of 3 runs:

1. the two runs make different sequences of calls;
2. the first differing step comes right after the first observation that differs between
   the cases, and cites it in `observation_refs`;
3. case 2 ends STOP_UNTRUSTWORTHY and case 6 ends ANSWER.

Observations are compared without the snapshot's own ID, which is identity, not
evidence.

## Setup

- Model `deepseek/deepseek-v4-flash-0731` through OpenRouter (via ADK's LiteLLM
  support), temperature 0, budget 8 turns / 8 calls.
- The model sees only the review day and the request (no case ID).
- At most three attempts were allowed, decided before the second attempt. Every run is
  saved under `runs/kill_gate/attempt_<n>/` with the hash of the prompt it used.

## Results

| Attempt | Change before it | Criterion 2 (runs) | Exits correct | Gate | Cost |
|---|---|---|---|---|---|
| 1 | first prompt (`f46556f96ca2`) | 0 / 3 | 2 / 3 | fail | $0.019 |
| 2 | prompt asks the model to let each result decide the next step (`420716c8a425`) | 0 / 3 | 3 / 3 | fail | $0.016 |
| 3 | the model no longer sees the snapshot ID; `compare_runs` also reports horizons (`34754b8c6423`) | 0 / 3 | 3 / 3 | **fail** | $0.023 |

Total model spend: $0.058 (of the $60 cap).

What attempt 3 did, in all three runs: both cases called `resolve_context`, then
`compare_runs`, then `check_quality`. Then they split. Case 2 stopped (STOP_UNTRUSTWORTHY),
citing the quality check that found the missing days. Case 6 went on to `inspect_series`
and answered (ANSWER), naming a systematic under-forecast and leaving its cause as not
established. The split cites the differing observations in every run.

It fails criterion 2 only by one step. The first observation that differs is the
comparison (step 2): its numbers differ between the cases. The agent always runs one
confirming data check (step 3) before it branches at step 4.

In every run of every attempt, the validator refused at least one `finish` that typed
numbers instead of pointer tokens; the agent then corrected it.

## Readings

- **Strict:** the agent follows a short fixed opening (context, compare, check) and only
  adapts after it. The premise "the agent's next step depends on the evidence" is not
  shown at the first differing observation.
- **Lenient:** confirming a red flag with one data check before acting is what a careful
  analyst does. Allowing one identical step between the first differing observation and
  the split (still requiring the split to cite a differing observation) gives a pass in
  3 / 3 runs of attempt 3. This is reported by the gate code as `lag=1`, and is **not**
  adopted.

## Options for the owner

1. Revise criterion 2 to allow one confirming step (`lag=1`), record the revision here,
   and treat the gate as passed on attempt 3's saved runs.
2. Keep the criterion, record weekend 3 as failed, and work on the agent before weekend 4,
   which needs a new attempt budget and a decision record.
3. Revise the premise, as the plan allows: report "the agent adapts after a confirming
   check, not immediately" as the finding.

## Consequences

- Attempts 1 and 2 were recorded before `compare_runs` reported horizons, so they cannot
  be replayed against today's tools; replay refuses them by design. Attempt 3 replays
  offline exactly.
- The prompt was changed on the very pair the gate uses, which risks fitting the agent to
  it. The held-out run (weekend 6) is the real test.
