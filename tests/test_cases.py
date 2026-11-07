from __future__ import annotations

from collections import Counter
from dataclasses import astuple
from pathlib import Path

import pytest

from agentic_forecast_review.cases import (
    DEV_FAMILIES,
    DUPLICATE_DAYS,
    FAMILY_ID,
    MISSING_DAYS,
    SERIES_ID,
    Family,
    FamilySpec,
    build_family,
)
from agentic_forecast_review.generator import ActualRow, Snapshot
from agentic_forecast_review.schemas import PlantedCondition

DEV = Path(__file__).resolve().parents[1] / "cases" / "dev"


@pytest.fixture(scope="module")
def family() -> Family:
    return build_family()


def _snapshot(family: Family, condition: PlantedCondition) -> Snapshot:
    for case, entry in zip(family.cases, family.manifest, strict=True):
        if entry.planted is condition:
            return family.snapshots[case.snapshot_id]
    raise AssertionError(condition)


def _rows(rows: tuple[ActualRow, ...]) -> Counter[tuple[object, ...]]:
    return Counter(astuple(row) for row in rows)


def test_committed_case_files_match_a_fresh_build(family: Family) -> None:
    folder = DEV / FAMILY_ID / "cases"
    expected = {f"{case.case_id}.json": case for case in family.cases}
    assert sorted(path.name for path in folder.iterdir()) == sorted(expected)
    for name, case in expected.items():
        on_disk = (folder / name).read_text(encoding="utf-8")
        assert on_disk == case.model_dump_json(indent=2) + "\n", name
    families = [build_family(spec) for spec in DEV_FAMILIES]
    for name, entries in (
        ("manifest.jsonl", [e for f in families for e in f.manifest]),
        ("run_settings.jsonl", [s for f in families for s in f.run_settings]),
    ):
        lines = "".join(entry.model_dump_json() + "\n" for entry in entries)
        assert (DEV / name).read_text(encoding="utf-8") == lines, name


def test_family_is_deterministic(family: Family) -> None:
    again = build_family()
    other = build_family(FamilySpec(FAMILY_ID, 8, SERIES_ID))
    assert again.cases == family.cases
    assert not set(other.snapshots) & set(family.snapshots)


def test_conditions_outside_the_data_reuse_the_base(family: Family) -> None:
    base = _snapshot(family, PlantedCondition.NORMAL)
    for condition in (
        PlantedCondition.TOOL_FAILURE,
        PlantedCondition.AMBIGUOUS_REQUEST,
        PlantedCondition.UNSUPPORTED_CAUSE,
    ):
        assert _snapshot(family, condition) is base


def test_missing_and_duplicate_rows_touch_only_their_days(family: Family) -> None:
    base = _snapshot(family, PlantedCondition.NORMAL)
    missing = _snapshot(family, PlantedCondition.MISSING_DATES)
    removed = _rows(base.actuals) - _rows(missing.actuals)
    assert sorted((row[1], row[4]) for row in removed) == [
        (SERIES_ID, day) for day in MISSING_DAYS
    ]
    assert missing.forecasts == base.forecasts

    duplicated = _snapshot(family, PlantedCondition.DUPLICATE_RECORDS)
    added = _rows(duplicated.actuals) - _rows(base.actuals)
    assert sorted((row[1], row[4]) for row in added) == [
        (SERIES_ID, day) for day in DUPLICATE_DAYS
    ]
    assert duplicated.forecasts == base.forecasts


def test_version_and_bias_changes_touch_only_their_forecasts(family: Family) -> None:
    base = _snapshot(family, PlantedCondition.NORMAL)
    for condition, issue_day in (
        (PlantedCondition.VERSION_MISMATCH, 140),
        (PlantedCondition.BIAS_SHIFT, 168),
    ):
        changed = _snapshot(family, condition)
        assert changed.actuals == base.actuals
        pairs = [
            (old, new)
            for old, new in zip(base.forecasts, changed.forecasts, strict=True)
            if old != new
        ]
        assert pairs
        for old, new in pairs:
            assert old.issue_day == issue_day and old.model_version == "synthetic_v3"
            if condition is PlantedCondition.VERSION_MISMATCH:
                assert (
                    new.model_version == "synthetic_v2" and new.horizon == old.horizon
                )
            else:
                assert old.series_id.endswith("_FOODS") and new.value < old.value


def test_horizon_mismatch_keeps_one_forecast_per_day(family: Family) -> None:
    base = _snapshot(family, PlantedCondition.NORMAL)
    changed = _snapshot(family, PlantedCondition.HORIZON_MISMATCH)
    assert changed.actuals == base.actuals
    early = [row for row in base.forecasts if row.issue_day == 112]
    assert [row for row in changed.forecasts if row.issue_day == 112] == early
    targets = Counter(
        (row.series_id, row.model_version, row.target_day)
        for row in changed.forecasts
        if row.target_day > 140
    )
    assert len(targets) == 30 * 2 * 56 and set(targets.values()) == {1}


def test_nothing_the_agent_sees_names_the_answer(family: Family) -> None:
    secrets = [condition.value for condition in PlantedCondition]
    visible = [case.model_dump_json() for case in family.cases]
    visible += [
        text
        for snapshot in family.snapshots.values()
        for text in snapshot.files().values()
    ]
    for text in visible:
        assert not [secret for secret in secrets if secret in text.lower()]
