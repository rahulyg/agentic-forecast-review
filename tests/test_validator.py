from __future__ import annotations

import pytest

from agentic_forecast_review.cases import build_family
from agentic_forecast_review.schemas import Cost, Packet, TerminalState, TraceStep
from agentic_forecast_review.validator import known_identifiers, stray_digits

ALLOWED = {"CA_2_FOODS", "CA_2", "synthetic_v3", "cmp2"}


@pytest.mark.parametrize(
    "text",
    [
        "CA_2_FOODS9 looks off",
        "XCA_2_FOODS looks off",
        "v3 is worse",
        "in Q4",
        "{ev:cmp2.n_actual} of 28 days",
        "{ev:cmp2.n_actual}4 days",
        "١٢ days",
        "CA_2-1 looks off",
    ],
)
def test_digits_outside_whole_identifiers_are_caught(text: str) -> None:
    assert stray_digits(text, ALLOWED)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "CA_2 FOODS and CA_2_FOODS, (synthetic_v3)",
        "{ev:cmp2.n_actual}/{ev:cmp2.n_expected} actual days",
        "four days are missing",
    ],
)
def test_clean_text_passes(text: str) -> None:
    assert stray_digits(text, ALLOWED) == []


def test_identifiers_come_from_the_case_snapshot_and_trace() -> None:
    family = build_family()
    case = family.cases[0]
    snapshot = family.snapshots[case.snapshot_id]
    packet = Packet(
        case_id=case.case_id,
        runner="agent",
        snapshot_id=case.snapshot_id,
        terminal_state=TerminalState.INCOMPLETE,
        trace=(TraceStep(turn=1, summary="stop"),),
        cost=Cost(turns=1, calls=0, usd=0, seconds=0),
    )
    known = known_identifiers(case, snapshot, packet)
    assert {"CA_2_FOODS", "CA_2", "synthetic_v3", case.snapshot_id} <= known
    assert "act__CA_2_FOODS__d0177" in known
