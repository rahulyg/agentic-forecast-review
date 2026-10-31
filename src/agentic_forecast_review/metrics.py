"""Deterministic forecast-error metrics."""

from __future__ import annotations

from collections.abc import Sequence
from math import fsum, isfinite


def _check_pair(actual: Sequence[float], predicted: Sequence[float]) -> None:
    if not actual:
        raise ValueError("actual must be nonempty")
    if len(actual) != len(predicted):
        raise ValueError("actual and predicted must have equal lengths")
    if not all(isfinite(value) for value in (*actual, *predicted)):
        raise ValueError("actual and predicted must contain only finite values")


def mae(actual: Sequence[float], predicted: Sequence[float]) -> float:
    """Mean absolute error: the average size of the misses."""
    _check_pair(actual, predicted)
    return fsum(
        abs(observed - forecast) for observed, forecast in zip(actual, predicted)
    ) / len(actual)


def signed_bias(actual: Sequence[float], predicted: Sequence[float]) -> float:
    """Mean of forecast minus actual; negative means underprediction."""
    _check_pair(actual, predicted)
    return fsum(
        forecast - observed for observed, forecast in zip(actual, predicted)
    ) / len(actual)
