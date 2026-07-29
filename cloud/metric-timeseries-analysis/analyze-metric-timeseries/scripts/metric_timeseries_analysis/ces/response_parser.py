from __future__ import annotations

from typing import Any

from metric_timeseries_analysis.errors import MetricAnalysisError
from metric_timeseries_analysis.series.model import MetricSeriesMap


def unwrap_mcp_cli_envelope(payload: Any, expected_tool_name: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise MetricAnalysisError("data_fetch_failed", "MCP CLI output must be a JSON object")

    actual_tool_name = payload.get("tool")
    if actual_tool_name != expected_tool_name:
        raise MetricAnalysisError(
            "data_fetch_failed",
            f"MCP CLI returned unexpected tool: {actual_tool_name!r}",
        )

    if not isinstance(payload.get("arguments"), dict):
        raise MetricAnalysisError("data_fetch_failed", "MCP CLI envelope is missing arguments")

    content = payload.get("content")
    content_count = payload.get("content_count")
    if not isinstance(content, list) or type(content_count) is not int:
        raise MetricAnalysisError(
            "data_fetch_failed",
            "MCP CLI envelope must contain content and content_count",
        )
    if content_count != len(content):
        raise MetricAnalysisError(
            "data_fetch_failed",
            "MCP CLI content_count does not match content length",
        )
    if content_count != 1:
        raise MetricAnalysisError(
            "data_fetch_failed",
            "CES MCP CLI must return exactly one content item",
        )

    result = payload.get("result")
    if not isinstance(result, dict) or result != content[0]:
        raise MetricAnalysisError(
            "data_fetch_failed",
            "MCP CLI envelope must expose its single content item as result",
        )
    if not isinstance(result.get("metrics"), list):
        raise MetricAnalysisError(
            "data_fetch_failed",
            "CES MCP result must contain a metrics list",
        )
    return result


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
