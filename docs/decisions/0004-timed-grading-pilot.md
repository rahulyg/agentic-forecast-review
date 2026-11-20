# 0004: Timed grading pilot (weekend 5)

**Status:** Accepted, 19 November 2026.

## Pilot protocol

Rahul authorized Fizz, a Codex agent, to grade the six development packets in the
timed W5 pilot in place of a person. Fizz reapplied H1–H5 to each packet and its answer
key with runner labels withheld. This was a second reading of the same packets by the
same grader. All 30 answers matched the untimed dry run.

The timer ran from opening each packet to recording its five answers, including
the interaction overhead during that interval. [Scores and elapsed minutes](../../grading/pilot/scores.csv)
record the measured times. The resulting `m` measures agent grading time. The held-out
evaluation plan still calls for human grading. Report the agent pilot, prior exposure
to the packets, and the timing basis with the evaluation results.

## Held-out sample size

[The plan](../ground-zero.md#8-evaluation-part-2-the-investigation-not-whether-it-sounds-convincing)
calls for 30 cases, with two agent runs and one baseline run per case. The six pilot
packets took 35.902 seconds total, so `m = 35.902 / (6 × 60) = 0.099728`
minutes per packet.

Under the [grading-time rule](../rubric.md#grading-time-rule-plan-section-8), reduce
`n` to `max(20, floor(600 / (3 × m)))` if `3 × n × m > 600` minutes.
At the planned count, `3 × 30 × m = 8.9755` minutes at the observed agent pace.
The budget rule retains **`n = 30`**. This count was set before unsealing.

## Findings

- The packet renderer displays cited-row counts without the rows. Counts alone
  cannot establish whether a claim follows from the cited evidence. The pilot
  graded H2 from the evidence visible in the packet.
- The packets' writing styles can give away the runner despite shuffling and
  hidden labels. Short templated steps and longer conversational steps are
  distinguishable. Report both limitations with the evaluation results.
