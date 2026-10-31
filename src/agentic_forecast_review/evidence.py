"""Addressable evidence rows: every displayed number traces to one of these."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceRow:
    row_id: str
    series_id: str
    model_version: str
    origin_day: int
    horizon: int
    metric: str
    value: float
    unit: str


def metric_evidence(
    *,
    series_id: str,
    model_version: str,
    origin_day: int,
    horizon: int,
    metric: str,
    value: float,
    unit: str = "units",
) -> EvidenceRow:
    """Build an evidence row whose ID is stable across re-runs."""
    return EvidenceRow(
        row_id=f"{series_id}__{model_version}__origin_{origin_day}__h{horizon}__{metric}",
        series_id=series_id,
        model_version=model_version,
        origin_day=origin_day,
        horizon=horizon,
        metric=metric,
        value=value,
        unit=unit,
    )


def find_evidence(
    rows: Sequence[EvidenceRow],
    *,
    series_id: str,
    model_version: str,
    origin_day: int,
    horizon: int,
    metric: str,
) -> EvidenceRow:
    """Return the single row matching every key, or raise LookupError."""
    matches = [
        row
        for row in rows
        if (row.series_id, row.model_version, row.origin_day, row.horizon, row.metric)
        == (series_id, model_version, origin_day, horizon, metric)
    ]
    if len(matches) != 1:
        raise LookupError(f"expected exactly one evidence row, found {len(matches)}")
    return matches[0]
