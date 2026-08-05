from __future__ import annotations

from typing import Any

from metric_timeseries_analysis.ces.limits import validate_ces_query_limits
from metric_timeseries_analysis.ces.query_builder import build_ces_batch_query
from metric_timeseries_analysis.errors import MetricAnalysisError


def plan_ces_batches(
    single_queries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Pack single-metric queries without allowing CES to shorten their range."""
    batches: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []

    for query in single_queries:
        single_error = validate_ces_query_limits(query)
        if single_error:
            _raise_limit_error(single_error)

        candidate = [*pending, query]
        candidate_query = build_ces_batch_query(candidate)
        if pending and validate_ces_query_limits(candidate_query):
            batches.append(build_ces_batch_query(pending))
            pending = [query]
        else:
            pending = candidate

    if pending:
        batches.append(build_ces_batch_query(pending))
    return batches


def _raise_limit_error(error: dict[str, Any]) -> None:
    raise MetricAnalysisError(
        str(error["error"]),
        str(error["message"]),
        **{
            key: value
            for key, value in error.items()
            if key not in {"success", "error", "message"}
        },
    )
