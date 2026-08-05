from __future__ import annotations

import re
from typing import Any

from metric_timeseries_analysis.analysis.profile_catalog import (
    PROFILE_DEFINITIONS,
    normalize_profile_analysis,
    validate_profile_metric_count,
)
from metric_timeseries_analysis.ces.query_builder import build_ces_query
from metric_timeseries_analysis.constants import DEFAULT_FILTER
from metric_timeseries_analysis.errors import MetricAnalysisError

_CES_TIMESTAMP_MIN = 1_111_111_111_111
_CES_TIMESTAMP_MAX = 9_999_999_999_999
_CES_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
_CES_NAMESPACE_PATTERN = re.compile(
    r"^[A-Za-z][A-Za-z0-9_-]*\.[A-Za-z][A-Za-z0-9_-]*$"
)


def find_missing_required_fields(args: dict[str, Any]) -> list[str]:
    """Return every absent required field without validating supplied values."""
    missing: list[str] = []
    _append_if_missing(missing, "region", args.get("region"))
    _append_if_missing(missing, "project_id", args.get("project_id"))

    metric = args.get("metric")
    if metric is None:
        missing.extend(
            (
                "metric.namespace",
                "metric.metric_name",
                "metric.dimensions",
            )
        )
    elif isinstance(metric, dict):
        _append_if_missing(missing, "metric.namespace", metric.get("namespace"))
        metric_names = metric.get("metric_name")
        _append_if_missing(missing, "metric.metric_name", metric_names)
        if isinstance(metric_names, list):
            for index, metric_name in enumerate(metric_names):
                _append_if_missing(
                    missing,
                    f"metric.metric_name[{index}]",
                    metric_name,
                )
        dimensions = metric.get("dimensions")
        if _is_missing(dimensions):
            missing.append("metric.dimensions")
        elif isinstance(dimensions, list):
            for index, dimension in enumerate(dimensions):
                if not isinstance(dimension, dict):
                    continue
                _append_if_missing(
                    missing,
                    f"metric.dimensions[{index}].name",
                    dimension.get("name"),
                )
                _append_if_missing(
                    missing,
                    f"metric.dimensions[{index}].value",
                    dimension.get("value"),
                )

    window = args.get("time_window")
    if window is None:
        missing.extend(("time_window.from", "time_window.to"))
    elif isinstance(window, dict):
        _append_if_missing(missing, "time_window.from", window.get("from"))
        _append_if_missing(missing, "time_window.to", window.get("to"))

    _append_if_missing(missing, "period", args.get("period"))

    analysis = args.get("analysis")
    if analysis is None:
        missing.append("analysis.profile")
    elif isinstance(analysis, dict):
        profile = analysis.get("profile")
        _append_if_missing(missing, "analysis.profile", profile)
        if isinstance(profile, str) and profile in PROFILE_DEFINITIONS:
            for option in PROFILE_DEFINITIONS[profile].options:
                if option.required:
                    _append_if_missing(
                        missing,
                        f"analysis.{option.name}",
                        analysis.get(option.name),
                    )

    return missing


def normalize_metric_analysis_spec(args: dict[str, Any]) -> dict[str, Any]:
    metric = _require_object(args.get("metric"), "metric")
    window = _require_object(args.get("time_window"), "time_window")
    analysis = args.get("analysis") or {}
    if not isinstance(analysis, dict):
        raise MetricAnalysisError("invalid_request", "analysis must be an object when provided")

    metric_names = _normalize_metric_names(metric.get("metric_name"))
    namespace = _require_text(metric.get("namespace"), "metric.namespace")
    region = _require_text(args.get("region"), "region")
    project_id = _require_text(args.get("project_id"), "project_id")
    start_ms = _to_int(window.get("from"), "time_window.from")
    end_ms = _to_int(window.get("to"), "time_window.to")
    period = _to_int(args.get("period"), "period")
    data_filter = DEFAULT_FILTER
    _validate_text_length(project_id, "project_id", 1, 64)
    _validate_namespace(namespace)
    for metric_name in metric_names:
        _validate_ces_name(metric_name, "metric.metric_name", 96)
    _validate_timestamp(start_ms, "time_window.from")
    _validate_timestamp(end_ms, "time_window.to")

    profile = _require_text(analysis.get("profile"), "analysis.profile")
    if profile not in PROFILE_DEFINITIONS:
        raise MetricAnalysisError("invalid_request", f"unsupported analysis profile: {profile}")
    validate_profile_metric_count(profile, len(metric_names))
    normalized_analysis = normalize_profile_analysis(profile, analysis)
    if profile == "coincident_anomaly_detection":
        time_point = normalized_analysis["time_point"]
        _validate_timestamp(time_point, "analysis.time_point")
        if not start_ms <= time_point <= end_ms:
            raise MetricAnalysisError(
                "invalid_request",
                "analysis.time_point must be inside time_window",
            )
        lookback_start = time_point - normalized_analysis["lookback_seconds"] * 1000
        if lookback_start < start_ms:
            raise MetricAnalysisError(
                "invalid_request",
                "time_window must cover the complete correlation lookback window",
            )

    dimensions = _normalize_dimensions(metric.get("dimensions"))
    ces_queries = [
        build_ces_query(
            project_id=project_id,
            region=region,
            namespace=namespace,
            metric_name=metric_name,
            dimensions=dimensions,
            start_ms=start_ms,
            end_ms=end_ms,
            period=period,
            data_filter=data_filter,
        )
        for metric_name in metric_names
    ]

    return {
        "region": region,
        "project_id": project_id,
        "metric": {
            "metric_name": metric_names,
            "namespace": namespace,
            "dimensions": dimensions,
        },
        "time_window": {"from": start_ms, "to": end_ms},
        "period": period,
        "filter": data_filter,
        "analysis": normalized_analysis,
        "ces_queries": ces_queries,
    }


def _append_if_missing(missing: list[str], field: str, value: Any) -> None:
    if _is_missing(value):
        missing.append(field)


def _is_missing(value: Any) -> bool:
    return value is None or value == [] or (
        isinstance(value, str) and not value.strip()
    )


def _require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MetricAnalysisError("invalid_request", f"{field} must be an object")
    return value


def _require_text(value: Any, field: str) -> str:
    if value is None or value == "":
        raise MetricAnalysisError("invalid_request", f"{field} is required")
    if not isinstance(value, str):
        raise MetricAnalysisError("invalid_request", f"{field} must be a string")
    text = value.strip()
    if not text:
        raise MetricAnalysisError("invalid_request", f"{field} is required")
    return text


def _normalize_metric_names(value: Any) -> list[str]:
    field = "metric.metric_name"
    if not isinstance(value, list):
        raise MetricAnalysisError("invalid_request", f"{field} must be an array of strings")
    if not value:
        raise MetricAnalysisError("invalid_request", f"{field} must not be empty")
    names = [_require_text(item, f"{field}[{index}]") for index, item in enumerate(value)]
    if len(set(names)) != len(names):
        raise MetricAnalysisError("invalid_request", f"{field} must not contain duplicates")
    return names


def _to_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MetricAnalysisError("invalid_request", f"{field} must be an integer") from None
    return value


def _normalize_dimensions(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise MetricAnalysisError("invalid_request", "metric.dimensions must be a CES-style list of {name, value} objects")
    if len(value) > 4:
        raise MetricAnalysisError("invalid_request", "metric.dimensions supports at most 4 items")
    dimensions: list[dict[str, str]] = []
    seen_names: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise MetricAnalysisError("invalid_request", "metric.dimensions list items must be objects")
        name = _require_text(item.get("name"), "metric.dimensions.name")
        dimension_value = _require_text(item.get("value"), "metric.dimensions.value")
        _validate_ces_name(name, "metric.dimensions.name", 32)
        _validate_text_length(dimension_value, "metric.dimensions.value", 1, 256)
        if name in seen_names:
            raise MetricAnalysisError("invalid_request", f"duplicate metric dimension name: {name}")
        seen_names.add(name)
        dimensions.append({"name": name, "value": dimension_value})
    if not dimensions:
        raise MetricAnalysisError("invalid_request", "metric.dimensions must not be empty")
    return sorted(dimensions, key=lambda item: item["name"])


def _validate_text_length(value: str, field: str, minimum: int, maximum: int) -> None:
    if not minimum <= len(value) <= maximum:
        raise MetricAnalysisError(
            "invalid_request",
            f"{field} length must be between {minimum} and {maximum}",
        )


def _validate_namespace(value: str) -> None:
    _validate_text_length(value, "metric.namespace", 3, 32)
    if not _CES_NAMESPACE_PATTERN.fullmatch(value):
        raise MetricAnalysisError(
            "invalid_request",
            "metric.namespace must match service.item",
        )


def _validate_ces_name(value: str, field: str, maximum: int) -> None:
    _validate_text_length(value, field, 1, maximum)
    if not _CES_NAME_PATTERN.fullmatch(value):
        raise MetricAnalysisError(
            "invalid_request",
            f"{field} must start with a letter and contain only letters, digits, underscore, or hyphen",
        )


def _validate_timestamp(value: int, field: str) -> None:
    if not _CES_TIMESTAMP_MIN <= value <= _CES_TIMESTAMP_MAX:
        raise MetricAnalysisError(
            "invalid_request",
            f"{field} must be between {_CES_TIMESTAMP_MIN} and {_CES_TIMESTAMP_MAX}",
        )
