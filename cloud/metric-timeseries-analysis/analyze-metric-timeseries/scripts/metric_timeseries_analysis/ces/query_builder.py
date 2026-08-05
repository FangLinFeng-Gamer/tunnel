from __future__ import annotations

from typing import Any

from metric_timeseries_analysis.constants import BACKEND_VERSION, NORMALIZATION_VERSION


def build_ces_query(
    *,
    project_id: str,
    region: str,
    namespace: str,
    metric_name: str,
    dimensions: list[dict[str, str]],
    start_ms: int,
    end_ms: int,
    period: int,
    data_filter: str,
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "region": region,
        "request_body": {
            "metrics": [
                {
                    "namespace": namespace,
                    "metric_name": metric_name,
                    "dimensions": dimensions,
                }
            ],
            "from": start_ms,
            "to": end_ms,
            "period": period,
            "filter": data_filter,
        },
        "normalization_version": NORMALIZATION_VERSION,
        "backend_version": BACKEND_VERSION,
    }


def build_ces_batch_query(single_queries: list[dict[str, Any]]) -> dict[str, Any]:
    if not single_queries:
        raise ValueError("single_queries must not be empty")
    first = single_queries[0]
    first_body = first["request_body"]
    shared_fields = (
        "project_id",
        "region",
        "normalization_version",
        "backend_version",
    )
    body_fields = ("from", "to", "period", "filter")
    for query in single_queries[1:]:
        if any(query[field] != first[field] for field in shared_fields):
            raise ValueError("CES batch queries must share routing and backend fields")
        if any(query["request_body"][field] != first_body[field] for field in body_fields):
            raise ValueError("CES batch queries must share time, period, and filter fields")

    return {
        "project_id": first["project_id"],
        "region": first["region"],
        "request_body": {
            "metrics": [
                metric
                for query in single_queries
                for metric in query["request_body"]["metrics"]
            ],
            "from": first_body["from"],
            "to": first_body["to"],
            "period": first_body["period"],
            "filter": first_body["filter"],
        },
        "normalization_version": first["normalization_version"],
        "backend_version": first["backend_version"],
    }
