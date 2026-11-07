from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agentic_forecast_review.cases import Family, build_family, load_case, write_family
from agentic_forecast_review.gateway import Gateway
from agentic_forecast_review.generator import generate, read_snapshot, write_snapshot
from agentic_forecast_review.schemas import (
    CompareRunsArgs,
    DayRange,
    EvidenceRowsArgs,
    InspectSeriesArgs,
    Metric,
    PlantedCondition,
    TerminalState,
)
from agentic_forecast_review.tools import (
    MAX_EVIDENCE_ROWS,
    TOOLS,
    compare_runs,
    evidence_rows,
    inspect_series,
)

PERIOD = {"start_day": 169, "end_day": 196}
WINDOW = {"start_day": 141, "end_day": 168}
REQUESTS: list[dict[str, Any]] = [
    {"tool": "resolve_context"},
    {
        "tool": "compare_runs",
        "series": ["CA_2_FOODS", "TX_1_HOBBIES"],
        "metric": "mae",
        "period": PERIOD,
        "window": WINDOW,
    },
    {"tool": "inspect_series", "series_id": "CA_2_FOODS", "days": PERIOD},
    {
        "tool": "check_quality",
        "series": ["CA_2_FOODS"],
        "days": {"start_day": 141, "end_day": 196},
    },
    {
        "tool": "evidence_rows",
        "row_ids": ["act__CA_2_FOODS__d0175", "act__CA_2_FOODS__d0171"],
    },
]


@pytest.fixture(scope="module")
def family() -> Family:
    return build_family()


def _facts(family: Family, number: int) -> dict[str, Any]:
    case = family.cases[number - 1]
    gateway = Gateway(case, family.snapshots[case.snapshot_id], TOOLS)
    facts: dict[str, Any] = {}
    for request in REQUESTS[1:4]:
        result = gateway.call(request).result
        assert result.ok, result.error
        facts |= {k.removeprefix("ca_2_foods__"): v for k, v in result.fields.items()}
    return facts


CLEAN = {
    "n_actual_period": 28,
    "missing_days": 0,
    "duplicate_rows": 0,
    "version_count": 1,
    "horizon_range": "1-28",
}
SIGNALS = {
    2: {"n_actual_period": 24, "missing_days": 4},
    3: {"n_actual_period": 31, "duplicate_rows": 3},
    4: {"version_count": 2},
    5: {"horizon_range": "1-7,22-28"},
}


@pytest.mark.parametrize("number", [1, 2, 3, 4, 5, 6, 7, 8, 9])
def test_each_condition_shows_in_its_tool_and_nowhere_else(
    family: Family, number: int
) -> None:
    facts = _facts(family, number)
    expected = CLEAN | SIGNALS.get(number, {})
    assert {name: facts[name] for name in expected} == expected
    if number == 4:
        assert (facts["model_window"], facts["model_period"]) == (
            "synthetic_v2",
            "synthetic_v3",
        )
    else:
        assert facts["model_window"] == facts["model_period"]
    clean = _facts(family, 1)
    if number == 6:
        assert facts["bias_period"] < clean["bias_period"] - 5
    elif number not in SIGNALS:
        assert facts["bias_period"] == clean["bias_period"]


@pytest.mark.parametrize("number", [2, 3, 4, 5, 6])
def test_every_planted_data_condition_looks_like_a_worse_error(
    family: Family, number: int
) -> None:
    assert _facts(family, number)["mae_delta"] > 0 >= _facts(family, 1)["mae_delta"]


def test_no_tool_output_names_the_answer(family: Family) -> None:
    secrets = [condition.value for condition in PlantedCondition]
    secrets += [state.value.lower() for state in TerminalState]
    for case in family.cases:
        gateway = Gateway(case, family.snapshots[case.snapshot_id], TOOLS)
        for request in REQUESTS:
            result = gateway.call(request).result
            assert result.ok, result.error
            text = json.dumps(result.model_dump(mode="json")).lower()
            assert not [secret for secret in secrets if secret in text]


def test_unknown_series_and_too_many_rows_are_refused(family: Family) -> None:
    case = family.cases[0]
    gateway = Gateway(case, family.snapshots[case.snapshot_id], TOOLS)
    unknown = gateway.call({**REQUESTS[1], "series": ["CA_9_FOODS"]}).result
    assert not unknown.ok and "unknown series: CA_9_FOODS" in (unknown.error or "")
    with pytest.raises(ValueError, match="at most"):
        evidence_rows(
            generate(),
            196,
            EvidenceRowsArgs(
                row_ids=tuple(f"r{i}" for i in range(MAX_EVIDENCE_ROWS + 1))
            ),
        )


def test_days_without_forecasts_are_refused() -> None:
    with pytest.raises(ValueError, match="no days"):
        inspect_series(
            generate(),
            196,
            InspectSeriesArgs(
                series_id="CA_2_FOODS", days=DayRange(start_day=1, end_day=7)
            ),
        )


def test_tools_ignore_days_after_the_review_day() -> None:
    args = CompareRunsArgs(
        series=("CA_2_FOODS",),
        metric=Metric.MAE,
        period=DayRange(**PERIOD),
        window=DayRange(**WINDOW),
    )
    fields = compare_runs(generate(), 180, args).fields
    assert fields["ca_2_foods__n_expected_period"] == 12
    assert fields["ca_2_foods__n_actual_period"] == 12


def test_a_duplicated_row_appears_twice_in_the_evidence(family: Family) -> None:
    case = family.cases[2]
    rows = evidence_rows(
        family.snapshots[case.snapshot_id],
        196,
        EvidenceRowsArgs(row_ids=("act__CA_2_FOODS__d0171",)),
    )
    assert rows.fields == {"n_rows": 1, "n_found": 1} and len(rows.table) == 2


def test_changed_snapshot_files_are_refused(tmp_path: Path) -> None:
    write_snapshot(generate(), tmp_path)
    actuals = tmp_path / "actuals.csv"
    actuals.write_text(actuals.read_text().replace(",49\n", ",50\n", 1))
    with pytest.raises(ValueError, match="do not match"):
        read_snapshot(tmp_path)


def test_load_case_reads_a_case_and_its_snapshot(
    family: Family, tmp_path: Path
) -> None:
    write_family(family, tmp_path)
    case, snapshot = load_case(tmp_path, "fam_01__c2")
    assert case == family.cases[1]
    assert snapshot == family.snapshots[case.snapshot_id]
