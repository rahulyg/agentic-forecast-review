from __future__ import annotations

import math
from pathlib import Path

import pytest

from agentic_forecast_review.credentials import ENV_VAR, openrouter_api_key
from agentic_forecast_review.evidence import find_evidence, metric_evidence
from agentic_forecast_review.fixtures import (
    Observation,
    load_observations,
    seasonal_naive,
)
from agentic_forecast_review.metrics import mae, signed_bias


def test_loader_rejects_wrong_columns(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("id,day,value\nx,1,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="columns"):
        load_observations(bad)


def test_loader_rejects_gaps(tmp_path: Path) -> None:
    gappy = tmp_path / "gappy.csv"
    gappy.write_text("series_id,day,value\nx,1,1\nx,3,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="contiguous"):
        load_observations(gappy)


@pytest.mark.parametrize("period", [0, -1])
def test_seasonal_naive_rejects_bad_period(period: int) -> None:
    with pytest.raises(ValueError, match="period"):
        seasonal_naive((), period=period, horizon=1)


def test_seasonal_naive_requires_full_history_and_one_step_horizon() -> None:
    history = (Observation("x", 1, 1.0),)
    with pytest.raises(ValueError, match="history"):
        seasonal_naive(history, period=7, horizon=1)
    with pytest.raises(ValueError, match="horizon"):
        seasonal_naive(history * 7, period=7, horizon=2)


@pytest.mark.parametrize(
    ("actual", "predicted"),
    [
        ([], []),
        ([1.0], []),
        ([math.nan], [1.0]),
        ([math.inf], [1.0]),
        ([-math.inf], [1.0]),
    ],
)
def test_metrics_reject_invalid_inputs(
    actual: list[float], predicted: list[float]
) -> None:
    with pytest.raises(ValueError):
        mae(actual, predicted)
    with pytest.raises(ValueError):
        signed_bias(actual, predicted)


def test_lookup_requires_exactly_one_row() -> None:
    row = metric_evidence(
        series_id="x",
        model_version="seasonal_naive_v0",
        origin_day=7,
        horizon=1,
        metric="mae",
        value=3.0,
    )
    kwargs = {
        "series_id": "x",
        "model_version": "seasonal_naive_v0",
        "origin_day": 7,
        "horizon": 1,
        "metric": "mae",
    }
    with pytest.raises(LookupError, match="0"):
        find_evidence((), **kwargs)
    with pytest.raises(LookupError, match="2"):
        find_evidence((row, row), **kwargs)


def test_openrouter_placeholder_key_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(ENV_VAR, "replace_with_your_openrouter_api_key")
    with pytest.raises(RuntimeError, match="missing or a placeholder"):
        openrouter_api_key()


def test_openrouter_key_read_from_dotenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(ENV_VAR, raising=False)
    (tmp_path / ".env").write_text(f"{ENV_VAR}=test-key\n", encoding="utf-8")
    assert openrouter_api_key() == "test-key"
