from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd

from metric_timeseries_analysis.analysis.context import AnalysisContext
from metric_timeseries_analysis.analysis.forecasting.prophet_forecaster import (
    ProphetForecaster,
    TrendForecaster,
)
from metric_timeseries_analysis.analysis.options import TrendPredictionOptions
from metric_timeseries_analysis.analysis.profile import ProfileAnalysisResult
from metric_timeseries_analysis.errors import MetricAnalysisError
from metric_timeseries_analysis.series.model import DataPoint, MetricSeriesMap


_MINIMUM_HISTORY = timedelta(days=7)
_FORECAST_HOURS = 168


class TrendPrediction:
    """基于 Prophet 的指标七天趋势预测。

    要求至少七天历史数据，按小时聚合后使用固定 Prophet 线性增长模型，
    预测未来 168 小时并返回紧凑摘要。
    """

    name = "trend_prediction"

    def __init__(self, forecaster: TrendForecaster | None = None) -> None:
        self._forecaster = forecaster or ProphetForecaster()

    def run(
        self,
        series_by_metric: MetricSeriesMap,
        context: AnalysisContext,
        options: TrendPredictionOptions,
    ) -> ProfileAnalysisResult:
        del context, options
        findings = []
        forecasts = {}
        for metric_name, series in series_by_metric.items():
            history = _prepare_hourly_history(series)
            forecast_rows = self._forecaster.forecast(
                history,
                periods=_FORECAST_HOURS,
            )
            forecast = _summarize_forecast(forecast_rows)
            forecasts[metric_name] = forecast
            direction = forecast["direction"]
            findings.append(
                {
                    "kind": f"{direction}_trend",
                    "severity": "info" if direction == "flat" else "warning",
                    "metric_name": metric_name,
                    "confidence": 1.0,
                    "evidence": forecast,
                }
            )
        return {
            "summary": "Forecasted the next seven days with Prophet.",
            "forecast_by_metric": forecasts,
            "findings": findings,
        }


def _prepare_hourly_history(series: list[DataPoint]) -> pd.DataFrame:
    history = pd.DataFrame(
        {
            "ds": pd.to_datetime(
                [point["timestamp"] for point in series],
                unit="ms",
                utc=True,
            ),
            "y": [point["value"] for point in series],
        }
    ).dropna()
    if history.empty or history["ds"].max() - history["ds"].min() < _MINIMUM_HISTORY:
        raise MetricAnalysisError(
            "invalid_request",
            "trend_prediction requires at least 7 days of metric history",
        )

    history["ds"] = history["ds"].dt.floor("h")
    history = (
        history.groupby("ds", as_index=False)["y"]
        .mean()
        .sort_values("ds")
        .reset_index(drop=True)
    )
    history["ds"] = history["ds"].dt.tz_convert(None)
    return history


def _summarize_forecast(forecast: pd.DataFrame) -> dict[str, Any]:
    if len(forecast) != _FORECAST_HOURS:
        raise MetricAnalysisError(
            "internal_error",
            "Prophet did not return the expected forecast length",
        )

    timestamps = pd.to_datetime(forecast["ds"], errors="coerce")
    values = pd.to_numeric(forecast["yhat"], errors="coerce").to_numpy(
        dtype=np.float64
    )
    if timestamps.isna().any() or not np.isfinite(values).all():
        raise MetricAnalysisError(
            "internal_error",
            "Prophet returned invalid forecast values",
        )

    first = float(values[0])
    last = float(values[-1])
    change = last - first
    if change > 1e-9:
        direction = "upward"
    elif change < -1e-9:
        direction = "downward"
    else:
        direction = "flat"

    return {
        "forecast_hours": _FORECAST_HOURS,
        "start_time": _timestamp_ms(timestamps.iloc[0]),
        "end_time": _timestamp_ms(timestamps.iloc[-1]),
        "first_predicted_value": first,
        "last_predicted_value": last,
        "min_predicted_value": float(np.min(values)),
        "max_predicted_value": float(np.max(values)),
        "mean_predicted_value": float(np.mean(values)),
        "change": change,
        "change_ratio": change / abs(first) if abs(first) > 1e-9 else None,
        "direction": direction,
    }


def _timestamp_ms(value: Any) -> int:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")
    return int(timestamp.timestamp() * 1000)
