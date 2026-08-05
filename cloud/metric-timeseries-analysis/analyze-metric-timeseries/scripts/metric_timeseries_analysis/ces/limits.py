from __future__ import annotations

import json
import math
from typing import Any

from metric_timeseries_analysis.constants import (
    CES_MAX_DATAPOINTS,
    CES_MAX_METRICS,
    CES_MAX_REQUEST_BYTES,
    CES_PERIODS_SECONDS,
)


def validate_ces_limits(spec: dict[str, Any]) -> dict[str, Any] | None:
    return validate_ces_query_limits(spec["ces_query"])


def validate_ces_query_limits(query: dict[str, Any]) -> dict[str, Any] | None:
    request_body = query["request_body"]
    metrics_count = len(request_body["metrics"])
    period = int(request_body["period"])
    start_ms = int(request_body["from"])
    end_ms = int(request_body["to"])

    request_bytes = len(
        json.dumps(request_body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    if request_bytes > CES_MAX_REQUEST_BYTES:
        return {
            "success": False,
            "error": "invalid_request",
            "message": "CES request body must not exceed 512KB",
            "request_bytes": request_bytes,
            "limit_bytes": CES_MAX_REQUEST_BYTES,
        }
    if metrics_count > CES_MAX_METRICS:
        return {"success": False, "error": "query_too_large", "message": f"CES supports at most {CES_MAX_METRICS} metrics per request"}
    if period not in CES_PERIODS_SECONDS:
        return {"success": False, "error": "invalid_request", "message": "period must be one of 1, 60, 300, 1200, 3600, 14400, 86400"}
    if end_ms <= start_ms:
        return {"success": False, "error": "invalid_request", "message": "time_window.to must be greater than time_window.from"}

    estimated = metrics_count * (end_ms - start_ms) / _period_ms_for_limit(period)
    if estimated > CES_MAX_DATAPOINTS:
        return {
            "success": False,
            "error": "query_too_large",
            "message": "metrics_count * (to - from) / period exceeds 3000",
            "estimated_datapoints": math.ceil(estimated),
            "limit": CES_MAX_DATAPOINTS,
            "suggestion": {"increase_period": True, "split_by_metric": metrics_count > 1, "split_by_time": True},
        }
    return None


def _period_ms_for_limit(period_seconds: int) -> int:
    return 60_000 if period_seconds == 1 else period_seconds * 1000
