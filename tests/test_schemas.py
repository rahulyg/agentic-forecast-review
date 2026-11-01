from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from agentic_forecast_review.schemas import (
    CanonicalScope,
    Case,
    CheckQualityArgs,
    Claim,
    ClaimLabel,
    CompareRunsArgs,
    DayRange,
    ManifestEntry,
    Metric,
    MissingScope,
    Packet,
    PlantedCondition,
    ResolveContextArgs,
    TerminalState,
    ToolCall,
    ToolResult,
    TraceStep,
)

HASH = "a" * 64
PERIOD = DayRange(start_day=29, end_day=35)
WINDOW = DayRange(start_day=22, end_day=28)


def _step(
    turn: int,
    call_id: str | None,
    args: Any = None,
    *,
    refs: tuple[str, ...] = (),
    fields: dict[str, Any] | None = None,
) -> TraceStep:
    if call_id is None:
        return TraceStep(turn=turn, summary="finish", observation_refs=refs)
    return TraceStep(
        turn=turn,
        summary="next check",
        observation_refs=refs,
        call=ToolCall(call_id=call_id, args=args),
        result=ToolResult(
            call_id=call_id, ok=True, fields=fields or {}, result_hash=HASH
        ),
    )


def _case_a_packet(**overrides: Any) -> Packet:
    """The STOP path of the worked example: counts differ, quality check finds gaps."""
    trace = (
        _step(1, "ctx1", ResolveContextArgs()),
        _step(
            2,
            "cmp2",
            CompareRunsArgs(
                series=("CA_2_FOODS",), metric=Metric.MAE, period=PERIOD, window=WINDOW
            ),
            refs=("ctx1",),
            fields={"n_actual": 24, "n_expected": 28},
        ),
        _step(
            3,
            "dq3",
            CheckQualityArgs(series=("CA_2_FOODS",), days=PERIOD),
            refs=("cmp2",),
            fields={"missing_dates": 4},
        ),
        _step(4, None, refs=("dq3",)),
    )
    values: dict[str, Any] = {
        "case_id": "dev_001a",
        "runner": "agent",
        "snapshot_id": "snap_9f3c",
        "terminal_state": TerminalState.STOP_UNTRUSTWORTHY,
        "claims": (
            Claim(
                label=ClaimLabel.FINDING,
                template="{ev:dq3.missing_dates} actual dates are missing in the period.",
                row_refs=("r1201", "r1202", "r1203", "r1204"),
            ),
            Claim(
                label=ClaimLabel.INFERENCE,
                template="The MAE change is not comparable as computed.",
            ),
        ),
        "not_established": ("whether the model deteriorated",),
        "trace": trace,
        "cost": {"turns": 4, "calls": 3, "usd": 0.04, "seconds": 11.2},
    }
    values.update(overrides)
    return Packet.model_validate(values)


def test_unresolvable_pointer_token_is_rejected() -> None:
    bad = Claim(label=ClaimLabel.INFERENCE, template="{ev:cmp2.mae_delta} worse.")
    with pytest.raises(ValidationError, match="does not resolve"):
        _case_a_packet(claims=(bad,))


def test_observation_refs_cannot_point_forward() -> None:
    packet = _case_a_packet()
    steps = list(packet.trace)
    steps[1] = steps[1].model_copy(update={"observation_refs": ("dq3",)})
    with pytest.raises(ValidationError, match="unknown or later"):
        _case_a_packet(trace=tuple(steps))


def test_observation_refs_are_capped_at_two() -> None:
    with pytest.raises(ValidationError):
        TraceStep(turn=1, summary="x", observation_refs=("a1", "b2", "c3"))


def test_finding_must_cite_rows() -> None:
    with pytest.raises(ValidationError, match="FINDING"):
        Claim(label=ClaimLabel.FINDING, template="no rows")


def test_clarify_requires_clarification_and_vice_versa() -> None:
    with pytest.raises(ValidationError, match="clarification"):
        _case_a_packet(terminal_state=TerminalState.CLARIFY)
    with pytest.raises(ValidationError, match="clarification"):
        _case_a_packet(clarification={"missing": ["metric"]})
    packet = _case_a_packet(
        terminal_state=TerminalState.CLARIFY,
        claims=(),
        clarification={
            "missing": ["metric"],
            "options": {"metric": ["mae", "signed_bias"]},
        },
    )
    assert packet.clarification is not None
    assert packet.clarification.missing == {MissingScope.METRIC}


def test_clarification_options_only_for_missing_parameters() -> None:
    with pytest.raises(ValidationError, match="options"):
        _case_a_packet(
            terminal_state=TerminalState.CLARIFY,
            clarification={"missing": ["metric"], "options": {"period": ["W48"]}},
        )


def test_agent_budget_is_enforced_but_baseline_is_not() -> None:
    steps = tuple(_step(i, f"ctx{i}", ResolveContextArgs()) for i in range(1, 10)) + (
        _step(10, None),
    )
    cost = {"turns": 10, "calls": 9, "usd": 0.0, "seconds": 1.0}
    with pytest.raises(ValidationError, match="budget"):
        _case_a_packet(trace=steps, cost=cost, claims=())
    baseline = _case_a_packet(runner="baseline", trace=steps, cost=cost, claims=())
    assert baseline.cost.calls == 9


def test_cost_must_match_trace() -> None:
    with pytest.raises(ValidationError, match="cost"):
        _case_a_packet(cost={"turns": 2, "calls": 3, "usd": 0, "seconds": 0})


def test_tool_args_must_match_tool_name() -> None:
    with pytest.raises(ValidationError):
        ToolCall.model_validate(
            {"call_id": "x1", "args": {"tool": "check_quality", "row_ids": ["r1"]}}
        )


def test_failed_tool_result_needs_error() -> None:
    with pytest.raises(ValidationError, match="error"):
        ToolResult(call_id="a1", ok=False, result_hash=HASH)
    ToolResult(call_id="a1", ok=False, error="timeout", result_hash=HASH)


def test_table_rows_must_share_columns() -> None:
    with pytest.raises(ValidationError, match="same columns"):
        ToolResult(
            call_id="a1",
            ok=True,
            table=({"day": 1, "actual": 5}, {"day": 2}),
            result_hash=HASH,
        )


def test_pointer_tokens_cannot_reach_table() -> None:
    steps = list(_case_a_packet().trace)
    result = steps[2].result
    assert result is not None
    steps[2] = steps[2].model_copy(
        update={"result": result.model_copy(update={"table": ({"actual": 58},)})}
    )
    bad = Claim(label=ClaimLabel.INFERENCE, template="{ev:dq3.actual} units.")
    with pytest.raises(ValidationError, match="does not resolve"):
        _case_a_packet(trace=tuple(steps), claims=(bad,))


def test_window_must_precede_period() -> None:
    with pytest.raises(ValidationError, match="window"):
        CanonicalScope(metric=Metric.MAE, period=WINDOW, window=PERIOD)


def test_case_scope_cannot_pass_review_cutoff() -> None:
    scope = CanonicalScope(metric=Metric.MAE, period=PERIOD, window=WINDOW)
    with pytest.raises(ValidationError, match="review_day"):
        Case(
            case_id="dev_001a",
            family_id="fam_01",
            split="dev",
            snapshot_id="snap_9f3c",
            review_day=30,
            request_text="Is CA_2 FOODS worse?",
            canonical_scope=scope,
        )


def test_manifest_clarify_needs_expected_missing() -> None:
    with pytest.raises(ValidationError, match="expected_missing"):
        ManifestEntry(
            case_id="c1",
            family_id="f1",
            planted=PlantedCondition.AMBIGUOUS_REQUEST,
            expected_terminal=TerminalState.CLARIFY,
        )
    with pytest.raises(ValidationError, match="expected_missing"):
        ManifestEntry(
            case_id="c1",
            family_id="f1",
            planted=PlantedCondition.NORMAL,
            expected_terminal=TerminalState.ANSWER,
            expected_missing=frozenset({MissingScope.METRIC}),
        )


def test_models_are_frozen_and_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        DayRange(start_day=1, end_day=2, label="extra")  # type: ignore[call-arg]
    day_range = DayRange(start_day=1, end_day=2)
    with pytest.raises(ValidationError):
        day_range.start_day = 5  # type: ignore[misc]
