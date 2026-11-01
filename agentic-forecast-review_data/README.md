# Exported fixture data (draft)

A one-off export of the data built by `nbs/90_explore_fixture_data.ipynb` with
`SEED = 7`, for browsing in a spreadsheet. It uses the draft W2 recipe; the real
generator (W2 step 2) will write its own files under `cases/dev/`.

| File | Rows | Contents |
|---|---|---|
| `1_actual_sales_long.csv` | 5,880 | Actual sales: one row per series per day |
| `2_actual_sales_by_day.csv` | 196 | The same numbers, one row per day, one column per series |
| `3_forecasts_with_actuals.csv` | 5,040 | Forecasts from both models, with the matching actual for comparison |

10 stores (CA_1–4, TX_1–3, WI_1–3) × 3 categories (FOODS, HOUSEHOLD, HOBBIES) =
30 series, days 1–196. Forecasts are issued on days 112, 140 and 168 for the next
28 days.
