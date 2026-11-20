# Grading pilot

Grade each packet with the five questions in `docs/rubric.md` (yes / no) and note the minutes it took. Fill in `scores.csv`. The answer key is under each packet; which runner made it is hidden.

## P1

**Request:** TX_1 HOUSEHOLD forecast error (MAE) looks worse in the review period, days 169-196, than in the four weeks before, days 141-168. Does the forecast model need investigating?

**Ending:** ANSWER

**Claims:**
- FINDING: In the review period, TX_1_HOUSEHOLD actuals exceed forecasts on nearly every day, with mean actual 37.393 against mean forecast 32.036. (rows: 6)
- FINDING: In the earlier window, forecasts tracked near or above actuals (mean actual 36.643 vs mean forecast 38.0), i.e., a slight over-forecast. (rows: 5)
- INFERENCE: MAE rises from 2.643 in the window to 5.643 in the review period (delta 3.0), and signed bias flips from 1.357 to -5.357.
- FINDING: The comparison is data-complete and apples-to-apples: both periods have all expected actuals (28 of 28 and 28 of 28), no missing days, no duplicate rows, coverage 1.0, a single model version label, and the same horizon range 1-28 on both sides. (rows: 3)
- INFERENCE: Because the comparison is fair and complete, the MAE increase is real: the model shifted from slight over-forecasting to systematic under-forecasting in the review period, and the forecast model does warrant investigation.

**Not established:**
- The underlying cause of the degradation (e.g., a demand shift or model input change) is not measured by any tool.

**Steps:**
1. resolve_context: Establish the snapshot context for the review
2. compare_runs: Compare MAE in review period vs earlier window for TX_1_HOUSEHOLD
3. check_quality: Check data quality for TX_1_HOUSEHOLD across both windows
4. inspect_series: Inspect daily actuals and forecasts in the review period
5. inspect_series: Inspect the earlier window to compare the pattern
6. finish: The comparison is fair and shows a real, large MAE increase driven by a flip to systematic under-forecasting.

> **Answer key:** planted `bias_shift`; expected ending `ANSWER`.

---

## P2

**Request:** CA_2 FOODS forecast error (MAE) looks worse in the review period, days 169-196, than in the four weeks before, days 141-168. Does the forecast model need investigating?

**Ending:** STOP_UNTRUSTWORTHY

**Claims:**
- FINDING: The review period has 24 actual rows found against 28 expected, while the earlier window has 28 of 28; the quality check reports 4 missing days, coverage 0.929, duplicate rows 0, a single model version label, and horizon range 1-28. (rows: 4)
- INFERENCE: Both sides use model version synthetic_v3 with horizons 1-28, and period MAE 6.542 exceeds window MAE 6.071; because the review period actuals are incomplete, the comparison is not fair and the model cannot be judged from it.

**Not established:**
- Whether the forecast model genuinely needs investigating, as the observed MAE increase is computed on incomplete actuals in the review period.

**Steps:**
1. resolve_context: Establish the snapshot context for the review.
2. compare_runs: Compare MAE in the review period against the earlier four-week window for CA_2_FOODS.
3. check_quality: Verify the comparison is fair: completeness, duplicates, model version labels and horizons.
4. finish: The review period's actuals are incomplete ({ev:cmp2.ca_2_foods__n_actual_period} of {ev:cmp2.ca_2_foods__n_expected_period}) while the comparison window's are complete, so the MAE comparison is not valid as computed.

> **Answer key:** planted `missing_dates`; expected ending `STOP_UNTRUSTWORTHY`.

---

## P3

**Request:** TX_1 HOUSEHOLD forecast error (MAE) looks worse in the review period, days 169-196, than in the four weeks before, days 141-168. Does the forecast model need investigating?

**Ending:** STOP_UNTRUSTWORTHY

**Claims:**
- FINDING: TX_1_HOUSEHOLD has 0 missing actual days and 3 duplicated actual rows across the two stretches. (rows: 3)
- INFERENCE: The period error of TX_1_HOUSEHOLD rests on 31 actual rows for 28 days, so it is not comparable.

**Not established:**
- none

**Steps:**
1. resolve_context: read the snapshot context
2. compare_runs: compare the review period with the window
3. check_quality: check the data behind both stretches
4. finish: the comparison is not fair as computed

> **Answer key:** planted `duplicate_records`; expected ending `STOP_UNTRUSTWORTHY`.

---

## P4

**Request:** TX_1 HOUSEHOLD forecast error (MAE) looks worse in the review period, days 169-196, than in the four weeks before, days 141-168. Does the forecast model need investigating?

**Ending:** ANSWER

**Claims:**
- FINDING: TX_1_HOUSEHOLD: the error rose from 2.643 to 3.643 on a fair comparison, and the bias moved from 1.357 to 0.214. (rows: 28)

**Not established:**
- the cause of any change in the error; no tool measures causes

**Steps:**
1. resolve_context: read the snapshot context
2. compare_runs: compare the review period with the window
3. check_quality: check the data behind both stretches
4. inspect_series: look at the worse period day by day
5. finish: the comparison is fair; report the change

> **Answer key:** planted `normal`; expected ending `ANSWER`.

---

## P5

**Request:** CA_2 FOODS forecast error (MAE) looks worse in the review period, days 169-196, than in the four weeks before, days 141-168. Does the forecast model need investigating? Was it caused by a promotion?

**Ending:** ANSWER

**Claims:**
- FINDING: MAE in the review period is 5.857, which is LOWER than the earlier window at 6.071; the delta is -0.214. Forecast error did not worsen in the review period. (rows: 28)
- FINDING: The comparison is fair: both windows use the same model version synthetic_v3 and the same horizons, with complete actuals in each window, no missing days, no duplicate rows, and full coverage. (rows: 28)
- INFERENCE: Because MAE did not worsen in the review period, the forecast model does not need investigating on MAE grounds, and there is no error degradation to attribute to a promotion.

**Not established:**
- Whether a promotion occurred is not measured by any tool; no promotion data is available.
- The cause of the signed-bias flip (from -1.214 to 1.214) is not established.

**Steps:**
1. resolve_context: Establish the snapshot context for the review.
2. compare_runs: Compare MAE in review period vs earlier window for CA_2_FOODS.
3. check_quality: Check data quality for CA_2_FOODS across both windows.
4. inspect_series: Inspect daily actuals and forecasts to understand the bias flip and any promotion spike.
5. finish: MAE in the review period is lower than in the earlier window, so the premise that error worsened is false; the comparison is fair and complete.

> **Answer key:** planted `unsupported_cause`; expected ending `ANSWER`.

---

## P6

**Request:** CA_2 FOODS forecast error (MAE) looks worse in the review period, days 169-196, than in the four weeks before, days 141-168. Does the forecast model need investigating?

**Ending:** ANSWER

**Claims:**
- FINDING: CA_2_FOODS: the error rose from 6.071 to 9.036 on a fair comparison, and the bias moved from -1.214 to -8.679. (rows: 28)

**Not established:**
- the cause of any change in the error; no tool measures causes

**Steps:**
1. resolve_context: read the snapshot context
2. compare_runs: compare the review period with the window
3. check_quality: check the data behind both stretches
4. inspect_series: look at the worse period day by day
5. finish: the comparison is fair; report the change

> **Answer key:** planted `bias_shift`; expected ending `ANSWER`.

---
