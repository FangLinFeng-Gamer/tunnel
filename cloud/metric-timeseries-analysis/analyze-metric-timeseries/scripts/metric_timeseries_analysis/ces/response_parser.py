from __future__ import annotations

import json
from typing import Any

from metric_timeseries_analysis.errors import MetricAnalysisError
from metric_timeseries_analysis.series.model import MetricSeriesMap


def unwrap_backend_json(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise MetricAnalysisError("data_fetch_failed", "CES backend must return a JSON object")
    if "metrics" in payload:
        return payload
    for key in ("data", "result", "response"):
        value = payload.get(key)
        if isinstance(value, dict) and "metrics" in value:
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and "metrics" in parsed:
                return parsed
    return payload


def extract_series(raw: dict[str, Any], preferred_filter: str) -> MetricSeriesMap:
    metrics = raw.get("metrics")
    if not isinstance(metrics, list):
        raise MetricAnalysisError("invalid_request", "CES response must contain a metrics list")
    result: MetricSeriesMap = {}
    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        metric_name = str(metric.get("metric_name") or metric.get("metric") or "")
        datapoints = metric.get("datapoints") or []
        if not metric_name or not isinstance(datapoints, list):
            continue
        series = []
        for point in datapoints:
            if not isinstance(point, dict):
                continue
            timestamp = point.get("timestamp")
            if preferred_filter not in point:
                raise MetricAnalysisError(
                    "data_fetch_failed",
                    f"CES datapoint is missing requested aggregation field: {preferred_filter}",
                )
            value = point[preferred_filter]
            if timestamp is None or value is None:
                continue
            try:
                series.append({"timestamp": int(timestamp), "value": float(value)})
            except (TypeError, ValueError):
                continue
        if series:
            series.sort(key=lambda item: item["timestamp"])
            result[metric_name] = series
    return result
