"""Contracts shared by the agent, the scripted baseline and the grader.

These models are the weekend 0+1 deliverable (Figure 8 of the plan). They fix
shapes and cross-field rules; tool behaviour and the stray-digit validator come
later and build on them.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

MAX_TURNS = 8
MAX_CALLS = 8
MAX_OBSERVATION_REFS = 2

CallId = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")]
Identifier = Annotated[str, StringConstraints(min_length=1, pattern=r"^\S+$")]
FieldValue = int | float | str | bool

# {ev:<call_id>.<field>}: the only way a number may appear in model-written text.
POINTER_TOKEN = re.compile(r"\{ev:([a-z][a-z0-9_]*)\.([a-z][a-z0-9_]*)\}")


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TerminalState(StrEnum):
    ANSWER = "ANSWER"
    CLARIFY = "CLARIFY"
    STOP_UNTRUSTWORTHY = "STOP_UNTRUSTWORTHY"
    INCOMPLETE = "INCOMPLETE"


class MissingScope(StrEnum):
    """Scope parameters a CLARIFY exit may name as missing."""

    METRIC = "metric"
    WINDOW = "window"
    SERIES = "series"
    PERIOD = "period"


class Metric(StrEnum):
    MAE = "mae"
    SIGNED_BIAS = "signed_bias"


class PlantedCondition(StrEnum):
    NORMAL = "normal"
    MISSING_DATES = "missing_dates"
    DUPLICATE_RECORDS = "duplicate_records"
    VERSION_MISMATCH = "version_mismatch"
    HORIZON_MISMATCH = "horizon_mismatch"
    BIAS_SHIFT = "bias_shift"
    TOOL_FAILURE = "tool_failure"
    AMBIGUOUS_REQUEST = "ambiguous_request"
    UNSUPPORTED_CAUSE = "unsupported_cause"


class ToolName(StrEnum):
    RESOLVE_CONTEXT = "resolve_context"
    COMPARE_RUNS = "compare_runs"
    INSPECT_SERIES = "inspect_series"
    CHECK_QUALITY = "check_quality"
    EVIDENCE_ROWS = "evidence_rows"


class Split(StrEnum):
    DEV = "dev"
    HELDOUT = "heldout"


class ClaimLabel(StrEnum):
    FINDING = "FINDING"
    INFERENCE = "INFERENCE"


# --- Cases and manifest ------------------------------------------------------


class DayRange(_Frozen):
    """Inclusive range of fixture days."""

    start_day: int = Field(ge=1)
    end_day: int = Field(ge=1)

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.end_day < self.start_day:
            raise ValueError("end_day must not be before start_day")
        return self


class CanonicalScope(_Frozen):
    """The structured form of a request, read by the scripted baseline.

    ``period`` is the review period being assessed; ``window`` is the earlier
    period it is compared against. ``None`` marks a parameter the request leaves
    ambiguous.
    """

    metric: Metric | None
    period: DayRange | None
    window: DayRange | None
    series: tuple[Identifier, ...] | None = Field(default=None, min_length=1)

    def missing(self) -> frozenset[MissingScope]:
        return frozenset(
            MissingScope(name)
            for name in ("metric", "period", "window", "series")
            if getattr(self, name) is None
        )

    @model_validator(mode="after")
    def _window_precedes_period(self) -> Self:
        if (
            self.period is not None
            and self.window is not None
            and self.window.end_day >= self.period.start_day
        ):
            raise ValueError("window must end before period starts")
        return self


class Case(_Frozen):
    """What the agent and the baseline are given. Never contains ground truth."""

    case_id: Identifier
    family_id: Identifier
    split: Split
    snapshot_id: Identifier
    review_day: int = Field(ge=1)
    request_text: str = Field(min_length=1)
    canonical_scope: CanonicalScope

    @model_validator(mode="after")
    def _scope_before_cutoff(self) -> Self:
        period = self.canonical_scope.period
        if period is not None and period.end_day > self.review_day:
            raise ValueError("period must end on or before review_day")
        return self


class ManifestEntry(_Frozen):
    """Ground truth for one case. Read by the grader only."""

    case_id: Identifier
    family_id: Identifier
    planted: PlantedCondition
    expected_terminal: TerminalState
    expected_missing: frozenset[MissingScope] = frozenset()
    matched_case_id: Identifier | None = None

    @model_validator(mode="after")
    def _clarify_consistency(self) -> Self:
        clarify = self.expected_terminal is TerminalState.CLARIFY
        if clarify != bool(self.expected_missing):
            raise ValueError(
                "expected_missing must be non-empty exactly when CLARIFY is expected"
            )
        if self.matched_case_id == self.case_id:
            raise ValueError("a case cannot be matched with itself")
        return self


# --- Tool calls --------------------------------------------------------------


class ResolveContextArgs(_Frozen):
    tool: Literal[ToolName.RESOLVE_CONTEXT] = ToolName.RESOLVE_CONTEXT


class CompareRunsArgs(_Frozen):
    tool: Literal[ToolName.COMPARE_RUNS] = ToolName.COMPARE_RUNS
    series: tuple[Identifier, ...] = Field(min_length=1)
    metric: Metric
    period: DayRange
    window: DayRange
    model_version: Identifier | None = None


class InspectSeriesArgs(_Frozen):
    tool: Literal[ToolName.INSPECT_SERIES] = ToolName.INSPECT_SERIES
    series_id: Identifier
    days: DayRange


class CheckQualityArgs(_Frozen):
    tool: Literal[ToolName.CHECK_QUALITY] = ToolName.CHECK_QUALITY
    series: tuple[Identifier, ...] = Field(min_length=1)
    days: DayRange


class EvidenceRowsArgs(_Frozen):
    tool: Literal[ToolName.EVIDENCE_ROWS] = ToolName.EVIDENCE_ROWS
    row_ids: tuple[Identifier, ...] = Field(min_length=1)


ToolArgs = Annotated[
    ResolveContextArgs
    | CompareRunsArgs
    | InspectSeriesArgs
    | CheckQualityArgs
    | EvidenceRowsArgs,
    Field(discriminator="tool"),
]


class ToolCall(_Frozen):
    call_id: CallId
    args: ToolArgs


class ToolResult(_Frozen):
    """A bounded observation. ``fields`` are what pointer tokens may reference."""

    call_id: CallId
    ok: bool
    fields: dict[
        Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")], FieldValue
    ] = {}
    row_ids: tuple[Identifier, ...] = ()
    error: str | None = None
    result_hash: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]

    @model_validator(mode="after")
    def _error_iff_failed(self) -> Self:
        if self.ok == (self.error is not None):
            raise ValueError("error must be set exactly when ok is false")
        return self


# --- Trace and packet --------------------------------------------------------


class TraceStep(_Frozen):
    """One model turn (or one baseline step) and the call it made, if any."""

    turn: int = Field(ge=1)
    summary: str = Field(min_length=1, max_length=280)
    observation_refs: tuple[CallId, ...] = Field(
        default=(), max_length=MAX_OBSERVATION_REFS
    )
    call: ToolCall | None = None
    result: ToolResult | None = None

    @model_validator(mode="after")
    def _call_and_result_pair(self) -> Self:
        if (self.call is None) != (self.result is None):
            raise ValueError("call and result must both be present or both absent")
        if self.call and self.result and self.call.call_id != self.result.call_id:
            raise ValueError("result call_id must match the call")
        return self


class Claim(_Frozen):
    """Model-written text. Numbers appear only as pointer tokens."""

    label: ClaimLabel
    template: str = Field(min_length=1)
    row_refs: tuple[Identifier, ...] = ()

    def tokens(self) -> list[tuple[str, str]]:
        return POINTER_TOKEN.findall(self.template)

    @model_validator(mode="after")
    def _findings_cite_rows(self) -> Self:
        if self.label is ClaimLabel.FINDING and not self.row_refs:
            raise ValueError("a FINDING must cite at least one source row")
        return self


class Clarification(_Frozen):
    missing: frozenset[MissingScope] = Field(min_length=1)
    options: dict[MissingScope, tuple[str, ...]] = {}

    @model_validator(mode="after")
    def _options_for_missing_only(self) -> Self:
        if not set(self.options) <= self.missing:
            raise ValueError("options may only be given for missing parameters")
        return self


class Cost(_Frozen):
    turns: int = Field(ge=0)
    calls: int = Field(ge=0)
    usd: float = Field(ge=0)
    seconds: float = Field(ge=0)


class Packet(_Frozen):
    """The review packet both runners produce, graded the same way."""

    case_id: Identifier
    runner: Literal["agent", "baseline"]
    snapshot_id: Identifier
    terminal_state: TerminalState
    claims: tuple[Claim, ...] = ()
    clarification: Clarification | None = None
    not_established: tuple[str, ...] = ()
    trace: tuple[TraceStep, ...]
    cost: Cost

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if (self.terminal_state is TerminalState.CLARIFY) != (
            self.clarification is not None
        ):
            raise ValueError("clarification must be present exactly for CLARIFY")
        if self.terminal_state is TerminalState.ANSWER and not self.claims:
            raise ValueError("an ANSWER must contain at least one claim")

        calls = [step.call for step in self.trace if step.call is not None]
        if self.cost.turns != len(self.trace) or self.cost.calls != len(calls):
            raise ValueError("cost turns and calls must match the trace")
        if self.runner == "agent" and (
            len(self.trace) > MAX_TURNS or len(calls) > MAX_CALLS
        ):
            raise ValueError("agent trace exceeds the turn or call budget")
        if [step.turn for step in self.trace] != list(range(1, len(self.trace) + 1)):
            raise ValueError("trace turns must be numbered 1..n in order")

        results: dict[str, ToolResult] = {}
        for step in self.trace:
            for ref in step.observation_refs:
                if ref not in results:
                    raise ValueError(
                        f"observation_refs cites unknown or later call {ref!r}"
                    )
            if step.call is not None and step.result is not None:
                if step.call.call_id in results:
                    raise ValueError(f"duplicate call_id {step.call.call_id!r}")
                results[step.call.call_id] = step.result

        for claim in self.claims:
            for call_id, field in claim.tokens():
                result = results.get(call_id)
                if result is None or field not in result.fields:
                    raise ValueError(
                        f"pointer token {{ev:{call_id}.{field}}} does not resolve"
                    )
        return self

    def render(self) -> list[str]:
        """Claims with every pointer token replaced by its validated value."""
        values = {
            (step.result.call_id, name): value
            for step in self.trace
            if step.result is not None
            for name, value in step.result.fields.items()
        }
        return [
            POINTER_TOKEN.sub(
                lambda match: str(values[(match.group(1), match.group(2))]),
                claim.template,
            )
            for claim in self.claims
        ]
