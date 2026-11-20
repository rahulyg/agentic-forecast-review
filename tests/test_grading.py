from __future__ import annotations

from typing import Any

import pytest

from agentic_forecast_review.agent import AgentRun
from agentic_forecast_review.cases import Family, build_family
from agentic_forecast_review.grading import (
    AutoGrade,
    auto_grade,
    packet_text,
    summary,
)
from agentic_forecast_review.schemas import Packet

QUALITY = {
    "tool": "check_quality",
    "series": ["CA_2_FOODS"],
    "days": {"start_day": 141, "end_day": 196},
}


@pytest.fixture(scope="module")
def family() -> Family:
    return build_family()


def _packet(
    family: Family,
    number: int,
    outcome: str,
    claims: list[dict[str, Any]] | None = None,
    missing: list[str] | None = None,
) -> Packet:
    case = family.cases[number - 1]
    run = AgentRun(case, family.snapshots[case.snapshot_id])
    run.request(QUALITY, "check", [])
    reply = run.finish(outcome, list(claims or []), [], missing or [], "done", ["dq1"])
    assert reply["ok"], reply
    assert run.packet is not None
    return run.packet


def _grade(family: Family, number: int, packet: Packet) -> AutoGrade:
    case = family.cases[number - 1]
    return auto_grade(
        packet, case, family.snapshots[case.snapshot_id], family.manifest[number - 1]
    )


def test_an_unneeded_clarify_fails_the_ending(family: Family) -> None:
    grade = _grade(family, 1, _packet(family, 1, "CLARIFY", missing=["metric"]))
    assert not grade.ending_ok and not grade.passed and not grade.ambiguous


def test_clarify_must_name_exactly_the_missing_parts(family: Family) -> None:
    right = _grade(family, 8, _packet(family, 8, "CLARIFY", missing=["metric"]))
    wrong = _grade(
        family, 8, _packet(family, 8, "CLARIFY", missing=["metric", "period"])
    )
    assert right.passed and right.ambiguous
    assert wrong.ending_ok and not wrong.clarify_ok and not wrong.passed


def test_cited_rows_must_have_been_returned(family: Family) -> None:
    claim = {
        "label": "FINDING",
        "text": "{ev:dq1.ca_2_foods__missing_days} days are missing.",
        "rows": ["act__CA_2_FOODS__d0175"],
    }
    good_packet = _packet(family, 2, "STOP_UNTRUSTWORTHY", claims=[claim])
    unseen = good_packet.claims[0].model_copy(
        update={"row_refs": ("act__CA_2_FOODS__d0100",)}
    )
    bad_packet = good_packet.model_copy(update={"claims": (unseen,)})
    assert _grade(family, 2, good_packet).passed
    assert not _grade(family, 2, bad_packet).rows_ok


def test_summary_counts_slices_separately(family: Family) -> None:
    grades = [
        _grade(family, 1, _packet(family, 1, "INCOMPLETE")),
        _grade(family, 8, _packet(family, 8, "CLARIFY", missing=["metric"])),
    ]
    counts = summary(grades)
    assert counts["paired ending"] == "0/1" and counts["ambiguous ending"] == "1/1"


def test_packet_text_hides_the_runner(family: Family) -> None:
    text = packet_text(
        _packet(family, 8, "CLARIFY", missing=["metric"]), family.cases[7]
    )
    assert "**Asks about:** metric" in text
    assert "runner" not in text and "agent" not in text.lower()
