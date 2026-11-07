from __future__ import annotations

from typing import Any

import pytest

from agentic_forecast_review.gateway import Gateway, ToolOutput, result_hash
from agentic_forecast_review.generator import Snapshot, generate
from agentic_forecast_review.schemas import (
    CanonicalScope,
    Case,
    RunSetting,
    Split,
    ToolName,
)

QUALITY = {
    "tool": "check_quality",
    "series": ["CA_2_FOODS"],
    "days": {"start_day": 150, "end_day": 160},
}


@pytest.fixture(scope="module")
def snapshot() -> Snapshot:
    return generate()


def _case(snapshot: Snapshot, review_day: int = 180) -> Case:
    return Case(
        case_id="t1",
        family_id="tests",
        split=Split.DEV,
        snapshot_id=snapshot.snapshot_id,
        review_day=review_day,
        request_text="test",
        canonical_scope=CanonicalScope(metric=None, period=None, window=None),
    )


def _echo(snapshot: Snapshot, review_day: int, args: Any) -> ToolOutput:
    return ToolOutput(fields={"review_day": review_day})


def _gateway(snapshot: Snapshot, setting: RunSetting | None = None) -> Gateway:
    tools = {name: _echo for name in ToolName if name is not ToolName.INSPECT_SERIES}
    return Gateway(_case(snapshot), snapshot, tools, setting)


@pytest.mark.parametrize("request_", ["hello", None, 5, [], {"tool": 5}, {}])
def test_garbage_becomes_a_failed_reply(snapshot: Snapshot, request_: object) -> None:
    reply = _gateway(snapshot).call(request_)
    assert reply.call is None and not reply.result.ok and reply.result.error
    assert reply.result.call_id == "bad1"


def test_unknown_tool_is_refused(snapshot: Snapshot) -> None:
    reply = _gateway(snapshot).call({**QUALITY, "tool": "delete_everything"})
    assert not reply.result.ok and reply.result.call_id == "bad1"


@pytest.mark.parametrize(
    "change",
    [
        {"days": {"start_day": 150, "end_day": 181}},
        {"tool": "evidence_rows", "row_ids": ["act__CA_2_FOODS__d0181"]},
        {
            "tool": "evidence_rows",
            "row_ids": ["fc__CA_2_FOODS__synthetic_v3__d0168__h13"],
        },
    ],
)
def test_days_after_the_review_day_are_refused(
    snapshot: Snapshot, change: dict[str, object]
) -> None:
    request = {**QUALITY, **change}
    if request["tool"] == "evidence_rows":
        request = {"tool": "evidence_rows", "row_ids": change["row_ids"]}
    reply = _gateway(snapshot).call(request)
    assert reply.call is not None and not reply.result.ok
    assert "after the review day 180" in (reply.result.error or "")


def test_rows_up_to_the_review_day_pass(snapshot: Snapshot) -> None:
    row_ids = ["act__CA_2_FOODS__d0180", "fc__CA_2_FOODS__synthetic_v3__d0168__h12"]
    reply = _gateway(snapshot).call({"tool": "evidence_rows", "row_ids": row_ids})
    assert reply.result.ok and reply.result.fields == {"review_day": 180}


def test_named_tool_fails_once_and_others_never(snapshot: Snapshot) -> None:
    setting = RunSetting(case_id="t1", fail_first_call_to=ToolName.CHECK_QUALITY)
    gateway = _gateway(snapshot, setting)
    first = gateway.call({"tool": "resolve_context"}).result
    failed = gateway.call(QUALITY).result
    retried = gateway.call(QUALITY).result
    assert first.ok and retried.ok
    assert not failed.ok and failed.error == "timeout"
    assert [first.call_id, failed.call_id, retried.call_id] == ["ctx1", "dq2", "dq3"]


def test_missing_tool_and_tool_errors_become_failed_replies(snapshot: Snapshot) -> None:
    def refuses(snapshot: Snapshot, review_day: int, args: Any) -> ToolOutput:
        raise ValueError("unknown series")

    gateway = Gateway(_case(snapshot), snapshot, {ToolName.CHECK_QUALITY: refuses})
    assert gateway.call(QUALITY).result.error == "unknown series"
    absent = gateway.call({"tool": "resolve_context"}).result
    assert absent.error == "resolve_context is not available"


def test_snapshot_must_match_the_case(snapshot: Snapshot) -> None:
    with pytest.raises(ValueError, match="snapshot"):
        Gateway(_case(snapshot), generate(8), {})


def test_hash_covers_content_but_not_the_call_name() -> None:
    base = result_hash(True, None, {"a": 1}, ("r1",), ({"day": 1},))
    assert base == result_hash(True, None, {"a": 1}, ("r1",), ({"day": 1},))
    assert base != result_hash(True, None, {"a": 1}, ("r1",), ({"day": 2},))
    assert result_hash(False, "timeout", {}, (), ()) != result_hash(
        False, "bad", {}, (), ()
    )
