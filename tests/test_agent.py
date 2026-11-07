from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agentic_forecast_review.agent import AgentRun, replay, save_run
from agentic_forecast_review.cases import Family, build_family
from agentic_forecast_review.kill_gate import check_pair, evidence, gate
from agentic_forecast_review.schemas import (
    MAX_TURNS,
    MissingScope,
    Packet,
    TerminalState,
    ToolResult,
)

QUALITY = {
    "tool": "check_quality",
    "series": ["CA_2_FOODS"],
    "days": {"start_day": 169, "end_day": 196},
}
EXPECTED = (TerminalState.STOP_UNTRUSTWORTHY, TerminalState.ANSWER)


@pytest.fixture(scope="module")
def family() -> Family:
    return build_family()


def _run(family: Family, number: int = 2) -> AgentRun:
    case = family.cases[number - 1]
    return AgentRun(case, family.snapshots[case.snapshot_id])


def test_the_model_never_sees_the_snapshot_id_or_fingerprint(family: Family) -> None:
    reply = _run(family).request({"tool": "resolve_context"}, "look", [])
    assert "snapshot_id" not in reply["fields"] and "result_hash" not in reply
    assert reply["fields"]["n_series"] == 30


def test_budget_leaves_room_for_finish(family: Family) -> None:
    run = _run(family)
    for _ in range(MAX_TURNS - 1):
        assert run.request(QUALITY, "check", [])["ok"]
    refused = run.request(QUALITY, "check", [])
    assert refused == {"ok": False, "error": "budget exhausted: call finish now"}
    assert len(run.steps) == MAX_TURNS - 1


def test_refused_request_uses_a_turn_without_a_call(family: Family) -> None:
    run = _run(family)
    reply = run.request({**QUALITY, "days": {"start_day": 1, "end_day": 300}}, "x", [])
    assert not reply["ok"]
    bad = run.request({"tool": "nonsense"}, "y", [])
    assert not bad["ok"] and run.steps[1].call is None
    assert any("refused request" in note for note in run.notes)


def test_unknown_refs_are_dropped_and_capped(family: Family) -> None:
    run = _run(family)
    run.request(QUALITY, "a", [])
    run.request(QUALITY, "b", [])
    run.request(QUALITY, "c", ["dq2", "zz9", "dq1", "dq2"])
    assert run.steps[2].observation_refs == ("dq2", "dq1")
    assert any("zz9" in note for note in run.notes)


def test_clarify_gets_metric_options_and_bad_outcomes_are_refused(
    family: Family,
) -> None:
    run = _run(family, 8)
    assert not run.finish("MAYBE", [], [], [], "unsure", [])["ok"]
    assert run.finish("CLARIFY", [], [], ["metric"], "which metric?", [])["ok"]
    assert run.packet is not None and run.packet.clarification is not None
    assert run.packet.clarification.options == {
        MissingScope.METRIC: ("mae", "signed_bias")
    }
    assert run.request(QUALITY, "after", []) == {
        "ok": False,
        "error": "the run is finished",
    }


def test_finish_refuses_rows_no_tool_returned(family: Family) -> None:
    run = _run(family)
    run.request(QUALITY, "check", [])
    claim = {"label": "FINDING", "text": "days are missing", "rows": ["dq1"]}
    reply = run.finish("STOP_UNTRUSTWORTHY", [claim], [], [], "stop", ["dq1"])
    assert not reply["ok"] and "row IDs" in reply["error"] and run.packet is None


def test_incomplete_packet_is_valid(family: Family) -> None:
    run = _run(family)
    for _ in range(MAX_TURNS - 1):
        run.request(QUALITY, "check", [])
    packet = run.incomplete("no valid finish")
    assert packet.terminal_state is TerminalState.INCOMPLETE
    assert packet.cost.turns == MAX_TURNS


def test_replay_catches_a_changed_reply_and_saves_records(
    family: Family, tmp_path: Path
) -> None:
    run = _run(family)
    run.request(QUALITY, "check", [])
    assert run.finish("INCOMPLETE", [], [], [], "stop", ["dq1"])["ok"]
    assert run.packet is not None
    record: dict[str, Any] = {
        "case_id": run.case.case_id,
        "started_at": "2026-11-07T10:00:00+00:00",
        "requests": run.requests,
        "packet": run.packet.model_dump(mode="json"),
    }
    case, snapshot = run.case, run.snapshot
    assert replay(record, case, snapshot) == run.packet
    tampered = Packet.model_validate(record["packet"]).model_dump(mode="json")
    tampered["trace"][0]["result"]["result_hash"] = "b" * 64
    with pytest.raises(ValueError, match="differs"):
        replay({**record, "packet": tampered}, case, snapshot)
    with pytest.raises(ValueError, match="fewer requests"):
        replay({**record, "requests": []}, case, snapshot)
    path = save_run(record, tmp_path)
    assert path.parent == tmp_path / "dev" / run.case.case_id and path.is_file()


def _pair(
    family: Family, quality_a: dict[str, Any], quality_b: dict[str, Any]
) -> tuple[Packet, Packet]:
    packets = []
    for number, extra in ((2, quality_a), (6, quality_b)):
        run = _run(family, number)
        run.request({"tool": "resolve_context"}, "context", [])
        run.request(QUALITY, "quality", ["ctx1"])
        if extra:
            run.request(extra, "follow up", ["dq2"])
        state = "STOP_UNTRUSTWORTHY" if number == 2 else "ANSWER"
        claims = [{"label": "INFERENCE", "text": "the model under-forecasts"}]
        assert run.finish(state, claims, [], [], "done", ["dq2"])["ok"]
        assert run.packet is not None
        packets.append(run.packet)
    return packets[0], packets[1]


def test_gate_passes_when_the_split_follows_and_cites_the_evidence(
    family: Family,
) -> None:
    inspect = {
        "tool": "inspect_series",
        "series_id": "CA_2_FOODS",
        "days": QUALITY["days"],
    }
    a, b = _pair(family, {}, inspect)
    check = check_pair(a, b, EXPECTED)
    assert check.passed and (
        check.first_different_observation,
        check.first_different_step,
    ) == (2, 3)


def test_identical_paths_or_wrong_exits_fail_the_gate(family: Family) -> None:
    a, b = _pair(family, {}, {})
    assert not check_pair(a, b, EXPECTED).diverged
    inspect = {
        "tool": "inspect_series",
        "series_id": "CA_2_FOODS",
        "days": QUALITY["days"],
    }
    a, b = _pair(family, {}, inspect)
    assert not check_pair(a, b, (TerminalState.ANSWER, TerminalState.ANSWER)).passed


def test_snapshot_identity_is_not_evidence() -> None:
    def result(snapshot_id: str) -> ToolResult:
        return ToolResult(
            call_id="ctx1",
            ok=True,
            fields={"snapshot_id": snapshot_id, "n_series": 30},
            result_hash="a" * 64,
        )

    assert evidence(result("snap_a")) == evidence(result("snap_b"))


def test_gate_needs_two_of_three(family: Family) -> None:
    inspect = {
        "tool": "inspect_series",
        "series_id": "CA_2_FOODS",
        "days": QUALITY["days"],
    }
    good = check_pair(*_pair(family, {}, inspect), EXPECTED)
    bad = check_pair(*_pair(family, {}, {}), EXPECTED)
    assert gate([good, good, bad]) and not gate([good, bad, bad])
