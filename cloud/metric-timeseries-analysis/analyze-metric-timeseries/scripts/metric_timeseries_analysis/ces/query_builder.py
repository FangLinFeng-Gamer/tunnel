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

