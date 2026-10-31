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
    split_at_origin,
)
from agentic_forecast_review.metrics import mae, signed_bias

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_weekly_01.csv"


def test_fixture_to_evidence_row_end_to_end() -> None:
    observations = load_observations(FIXTURE)
    history, target = split_at_origin(observations, origin_day=7)
    forecast = seasonal_naive(history, period=7, horizon=1)
    value = mae([target[0].value], [forecast])
    row = metric_evidence(
        series_id=target[0].series_id,
        model_version="seasonal_naive_v0",
        origin_day=7,
        horizon=1,
        metric="mae",
        value=value,
    )
    assert value == 3.0
    assert row.row_id == "synthetic_weekly_01__seasonal_naive_v0__origin_7__h1__mae"


def test_loader_and_split_real_fixture() -> None:
    observations = load_observations(FIXTURE)
    train, target = split_at_origin(observations, origin_day=7)
    assert len(train) == 7 and target[0].value == 13.0


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


def test_mae_mean() -> None:
    assert mae([1.0, 5.0], [3.0, 2.0]) == 2.5


def test_signed_bias_is_forecast_minus_actual() -> None:
    assert signed_bias([10.0, 10.0], [8.0, 9.0]) == -1.5
    assert signed_bias([10.0], [12.0]) == 2.0


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
    assert find_evidence((row,), **kwargs) is row
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
