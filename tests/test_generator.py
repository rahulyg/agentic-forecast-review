from __future__ import annotations

from agentic_forecast_review.generator import generate


def test_same_seed_same_bytes_different_seed_different_id() -> None:
    first, again, other = generate(7), generate(7), generate(8)
    assert first.files() == again.files()
    assert first.snapshot_id == again.snapshot_id
    assert other.snapshot_id != first.snapshot_id


def test_row_ids_are_unique() -> None:
    snapshot = generate()
    ids = [row.row_id for row in snapshot.actuals + snapshot.forecasts]
    assert len(ids) == len(set(ids))


def test_forecasts_only_use_days_up_to_the_issue_day() -> None:
    snapshot = generate()
    actual = {(row.series_id, row.day): row.value for row in snapshot.actuals}
    for row in snapshot.forecasts:
        if row.model_version == "seasonal_naive_v1":
            same_weekday_last_week = row.issue_day - 6 + (row.horizon - 1) % 7
            assert same_weekday_last_week <= row.issue_day
            assert row.value == actual[(row.series_id, same_weekday_last_week)]
