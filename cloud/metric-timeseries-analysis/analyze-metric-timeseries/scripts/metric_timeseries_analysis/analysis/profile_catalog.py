from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from metric_timeseries_analysis.errors import MetricAnalysisError


@dataclass(frozen=True)
class ProfileOption:
    name: str
    value_type: str
    required: bool
    description: str
    default: Any = None
    choices: tuple[str, ...] = ()
    example: Any = None


@dataclass(frozen=True)
class ProfileDefinition:
    name: str
    summary: str
    use_for: str
    options: tuple[ProfileOption, ...]


PROFILE_DEFINITIONS = {
    "sliding_window_threshold_frequency_detection": ProfileDefinition(
        name="sliding_window_threshold_frequency_detection",
        summary="Count threshold crossings inside rolling windows.",
        use_for="Use when a diagnosis needs to know how frequently a metric stays above or below a threshold.",
        options=(
            ProfileOption(
                name="threshold",
                value_type="number",
                required=True,
                description="Threshold value compared with each datapoint.",
                example=80,
            ),
            ProfileOption(
                name="direction",
                value_type="string",
                required=False,
                description="Comparison direction.",
                default="above",
                choices=("above", "below"),
                example="above",
            ),
            ProfileOption(
                name="window_points",
                value_type="integer",
                required=False,
                description="Number of datapoints in each rolling window.",
                default=3,
                example=5,
            ),
            ProfileOption(
                name="min_frequency",
                value_type="integer",
                required=False,
                description="Minimum threshold hits required inside a window. Defaults to ceil(window_points / 2).",
                example=3,
            ),
        ),
    ),
    "spike_drop_detection": ProfileDefinition(
        name="spike_drop_detection",
        summary="Detect residual or smoothed-trend spike and drop outliers.",
        use_for="Use when a diagnosis needs abrupt anomaly evidence after filtering normal fluctuation.",
        options=(
            ProfileOption(
                name="box_scale",
                value_type="number",
                required=False,
                description="IQR multiplier used to derive box-plot outlier bounds.",
                default=3.0,
                example=3.0,
            ),
            ProfileOption(
                name="direction",
                value_type="string",
                required=False,
                description="Detect upward, downward, or both anomaly directions.",
                default="up",
                choices=("up", "down", "all"),
                example="all",
            ),
            ProfileOption(
                name="window_size",
                value_type="integer",
                required=False,
                description="Mean and median smoothing duration in seconds.",
                default=3600,
                example=3600,
            ),
            ProfileOption(
                name="residual_sen",
                value_type="number",
                required=False,
                description="Minimum mean-filter residual range required before outlier detection.",
                default=10.0,
                example=10.0,
            ),
            ProfileOption(
                name="nonzero",
                value_type="boolean",
                required=False,
                description="Exclude zero values when deriving box-plot bounds.",
                default=False,
                example=False,
            ),
        ),
    ),
    "median_p75_statistics": ProfileDefinition(
        name="median_p75_statistics",
        summary="Compute median and p75 distribution statistics.",
        use_for="Use when a diagnosis needs compact baseline values for comparison.",
        options=(
            ProfileOption(
                name="smoothing_time",
                value_type="integer",
                required=False,
                description="Median-smoothing duration in seconds before computing median and p75.",
                default=900,
                example=900,
            ),
        ),
    ),
    "rising_trend_detection": ProfileDefinition(
        name="rising_trend_detection",
        summary="Determine whether adjacent datapoint changes are mostly rising.",
        use_for="Use when a diagnosis needs upward, downward, or unclear direction evidence from change counts.",
        options=(),
    ),
    "trend_prediction": ProfileDefinition(
        name="trend_prediction",
        summary="Forecast the next seven days with an hourly Prophet model.",
        use_for="Use when at least seven days of metric history are available and the diagnosis needs a future trend forecast.",
        options=(),
    ),
}


def list_profile_names() -> list[str]:
    return sorted(PROFILE_DEFINITIONS)


def get_profile_definition(name: str) -> ProfileDefinition:
    return PROFILE_DEFINITIONS[name]


def normalize_profile_analysis(profile_name: str, analysis: dict[str, Any]) -> dict[str, Any]:
    definition = PROFILE_DEFINITIONS[profile_name]
    options_by_name = {option.name: option for option in definition.options}
    unsupported = sorted(set(analysis) - {"profile"} - set(options_by_name))
    if unsupported:
        raise MetricAnalysisError(
            "invalid_request",
            f"unsupported analysis options: {', '.join(unsupported)}",
        )

    normalized: dict[str, Any] = {"profile": profile_name}
    for option in definition.options:
        value = analysis.get(option.name)
        if value is None:
            value = option.default
        if value is None:
            if option.required:
                raise MetricAnalysisError("invalid_request", f"analysis.{option.name} is required")
            continue
        normalized[option.name] = _normalize_option(option, value)

    if profile_name == "sliding_window_threshold_frequency_detection":
        window_points = normalized["window_points"]
        if "min_frequency" not in normalized:
            normalized["min_frequency"] = math.ceil(window_points / 2)
        if normalized["min_frequency"] > window_points:
            raise MetricAnalysisError(
                "invalid_request",
                "analysis.min_frequency must not exceed analysis.window_points",
            )
    return normalized


def _normalize_option(option: ProfileOption, value: Any) -> Any:
    field = f"analysis.{option.name}"
    if option.value_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise MetricAnalysisError("invalid_request", f"{field} must be an integer")
        normalized = value
    elif option.value_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise MetricAnalysisError("invalid_request", f"{field} must be a number")
        try:
            normalized = float(value)
        except OverflowError:
            raise MetricAnalysisError("invalid_request", f"{field} must be a finite number") from None
        if not math.isfinite(normalized):
            raise MetricAnalysisError("invalid_request", f"{field} must be a finite number")
    elif option.value_type == "string":
        if not isinstance(value, str) or not value:
            raise MetricAnalysisError("invalid_request", f"{field} must be a non-empty string")
        normalized = value
    elif option.value_type == "boolean":
        if not isinstance(value, bool):
            raise MetricAnalysisError("invalid_request", f"{field} must be a boolean")
        normalized = value
    else:
        raise RuntimeError(f"unsupported profile option type: {option.value_type}")

    if option.choices and normalized not in option.choices:
        raise MetricAnalysisError(
            "invalid_request",
            f"{field} must be one of {', '.join(option.choices)}",
        )
    if option.name in {
        "window_points",
        "min_frequency",
        "smoothing_time",
        "window_size",
    } and normalized < 1:
        raise MetricAnalysisError("invalid_request", f"{field} must be greater than 0")
    if option.name == "box_scale" and normalized <= 0:
        raise MetricAnalysisError("invalid_request", f"{field} must be greater than 0")
    if option.name == "residual_sen" and normalized < 0:
        raise MetricAnalysisError(
            "invalid_request",
            f"{field} must be greater than or equal to 0",
        )
    return normalized


def profile_definition_to_dict(definition: ProfileDefinition) -> dict[str, Any]:
    example_analysis = {"profile": definition.name}
    for option in definition.options:
        if option.example is not None:
            example_analysis[option.name] = option.example
        elif option.default is not None:
            example_analysis[option.name] = option.default

    return {
        "name": definition.name,
        "summary": definition.summary,
        "use_for": definition.use_for,
        "options": [
            {
                "name": option.name,
                "type": option.value_type,
                "required": option.required,
                "default": option.default,
                "choices": list(option.choices),
                "description": option.description,
                "example": option.example,
            }
            for option in definition.options
        ],
        "example_analysis": example_analysis,
    }
