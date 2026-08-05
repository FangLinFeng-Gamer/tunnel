from __future__ import annotations

from typing import Any

from metric_timeseries_analysis.errors import MetricAnalysisError


def split_ces_batch_response(
    raw: dict[str, Any],
    batch_query: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    metrics = raw.get("metrics")
    if not isinstance(metrics, list):
        raise MetricAnalysisError(
            "data_fetch_failed",
            "CES response must contain a metrics list",
        )

    requested_names = [
        str(metric["metric_name"])
        for metric in batch_query["request_body"]["metrics"]
    ]
    response_by_name: dict[str, dict[str, Any]] = {}
    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        metric_name = metric.get("metric_name")
        if not isinstance(metric_name, str) or metric_name not in requested_names:
            continue
        if metric_name in response_by_name:
            raise MetricAnalysisError(
                "data_fetch_failed",
                f"CES response contains duplicate metric: {metric_name}",
            )
        response_by_name[metric_name] = metric

    missing = [name for name in requested_names if name not in response_by_name]
    if missing:
        raise MetricAnalysisError(
            "data_fetch_failed",
            f"CES response is missing requested metrics: {', '.join(missing)}",
        )

    shared = {key: value for key, value in raw.items() if key != "metrics"}
    return {
        name: {**shared, "metrics": [response_by_name[name]]}
        for name in requested_names
    }
