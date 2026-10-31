"""Strict loading and splitting of synthetic fixture series."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite
from pathlib import Path


@dataclass(frozen=True)
class Observation:
    series_id: str
    day: int
    value: float


def load_observations(path: Path) -> tuple[Observation, ...]:
    """Load a single, contiguous series from a strict CSV fixture."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["series_id", "day", "value"]:
            raise ValueError("fixture columns must be series_id,day,value")
        rows = tuple(reader)
    if not rows:
        raise ValueError("fixture must contain at least one observation")

    observations: list[Observation] = []
    for row in rows:
        try:
            series_id = row["series_id"].strip()
            day = int(row["day"])
            value = float(row["value"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("fixture contains an invalid observation") from exc
        if not series_id or not isfinite(value):
            raise ValueError("fixture contains an invalid observation")
        observations.append(Observation(series_id, day, value))

    series_ids = {item.series_id for item in observations}
    days = [item.day for item in observations]
    if len(series_ids) != 1 or days != list(range(1, len(days) + 1)):
        raise ValueError(
            "fixture must be one series with contiguous days starting at 1"
        )
    return tuple(observations)


def split_at_origin(
    observations: Sequence[Observation], *, origin_day: int
) -> tuple[tuple[Observation, ...], tuple[Observation, ...]]:
    """Split history (day <= origin) from the target period (day > origin)."""
    if origin_day < 1:
        raise ValueError("origin_day must be positive")
    train = tuple(item for item in observations if item.day <= origin_day)
    target = tuple(item for item in observations if item.day > origin_day)
    if not train or not target or train[-1].day != origin_day:
        raise ValueError("origin_day must split observed history from a future target")
    return train, target


def seasonal_naive(
    history: Sequence[Observation], *, period: int, horizon: int
) -> float:
    """Repeat the value from one season before the forecast day."""
    if period <= 0:
        raise ValueError("period must be positive")
    if horizon != 1:
        raise ValueError("only horizon=1 is supported so far")
    if len(history) < period:
        raise ValueError("history must contain one full period")
    return history[-period].value
