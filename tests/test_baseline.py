from __future__ import annotations

import pytest

from agentic_forecast_review.baseline import run_baseline
from agentic_forecast_review.cases import Family, build_family
from agentic_forecast_review.schemas import (
    CanonicalScope,
    DayRange,
    Metric,
    MissingScope,
    RunSetting,
    TerminalState,
    ToolName,
)
from agentic_forecast_review.validator import known_identifiers, packet_stray_digits


@pytest.fixture(scope="module")
def family() -> Family:
    return build_family()


def test_every_missing_scope_part_is_asked_for(family: Family) -> None:
    case = family.cases[0].model_copy(
        update={
            "canonical_scope": CanonicalScope(
                metric=None, period=None, window=None, series=None
            )
        }
    )
    packet = run_baseline(case, family.snapshots[case.snapshot_id])
    assert packet.terminal_state is TerminalState.CLARIFY
    assert packet.clarification is not None
    assert packet.clarification.missing == set(MissingScope)
    assert packet.cost.calls == 0


def test_several_series_are_judged_one_by_one(family: Family) -> None:
    case = family.cases[0]
    scope = case.canonical_scope.model_copy(
        update={"series": ("CA_2_FOODS", "TX_1_HOBBIES", "WI_3_HOUSEHOLD")}
    )
    snapshot = family.snapshots[case.snapshot_id]
    packet = run_baseline(case.model_copy(update={"canonical_scope": scope}), snapshot)
    assert packet.terminal_state is TerminalState.ANSWER
    assert len(packet.claims) == 3
    assert packet_stray_digits(packet, known_identifiers(case, snapshot, packet)) == {}


def test_a_failing_tool_is_retried_once(family: Family) -> None:
    case = family.cases[0]
    setting = RunSetting(
        case_id=case.case_id, fail_first_call_to=ToolName.CHECK_QUALITY
    )
    packet = run_baseline(case, family.snapshots[case.snapshot_id], setting)
    calls = [step for step in packet.trace if step.call is not None]
    assert [step.result.ok for step in calls if step.result] == [
        True,
        True,
        False,
        True,
    ]
    assert packet.terminal_state is TerminalState.ANSWER


def test_gaps_in_the_window_also_stop_the_comparison(family: Family) -> None:
    case = family.cases[1]
    scope = CanonicalScope(
        metric=Metric.MAE,
        period=DayRange(start_day=183, end_day=196),
        window=DayRange(start_day=169, end_day=182),
        series=("CA_2_FOODS",),
    )
    packet = run_baseline(
        case.model_copy(update={"canonical_scope": scope}),
        family.snapshots[case.snapshot_id],
    )
    assert packet.terminal_state is TerminalState.STOP_UNTRUSTWORTHY
    assert any("window error" in claim.template for claim in packet.claims)
