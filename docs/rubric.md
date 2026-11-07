# Grading rubric

Every packet is graded twice: by code (`nbs/13_grading`) and by a person, with this
rubric. The person sees the packet as text (`packet_text`) and the case's answer key,
but **not which runner made it**; packets are shuffled. The model never grades itself.

## What code already checks

The ending matches the answer key; a CLARIFY names exactly the missing scope parts;
every row a FINDING cites was returned by a tool; no typed numbers; the agent stayed
within its budget. The person does not re-check these.

## The five questions (yes / no)

| | Question | "Yes" means |
|---|---|---|
| H1 | **Investigated enough?** | Before concluding, the packet looked at what the case needed: for a stop, it found the data problem; for an answer, it established the comparison was fair. |
| H2 | **Claims supported?** | Every claim follows from the numbers and rows it cites; none contradicts the evidence. |
| H3 | **Answers the request?** | The conclusion is about the series, period and question asked. |
| H4 | **No invented cause?** | Nothing is claimed that no tool measured; causes the tools cannot show are left as not established. |
| H5 | **Clear?** | A reviewer could act on it within a minute. |

**Complete task success** = every code check passes **and** H1–H4 are yes. H5 is reported
separately and does not decide success.

Note the time each packet takes, from opening it to the last answer.

## Grading-time rule (plan, section 8)

From the pilot, `m` = mean minutes per packet. Held-out packets to grade = `n` × 3 (agent
twice, baseline once). If `3nm` > 600 minutes, `n` = ⌊600 / 3m⌋, never below 20; this is
disclosed with the results. `n` is fixed before the held-out seeds are unsealed.
