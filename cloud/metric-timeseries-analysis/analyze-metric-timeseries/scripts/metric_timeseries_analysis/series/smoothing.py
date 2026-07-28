from __future__ import annotations

import math
from typing import Literal

import numpy as np
import numpy.typing as npt
import pandas as pd

from metric_timeseries_analysis.errors import MetricAnalysisError


SmoothingMethod = Literal["median", "mean"]
BoundaryMode = Literal["zero", "edge", "reflect", "shrink", "drop"]

_SUPPORTED_METHODS = {"median", "mean"}
_SUPPORTED_BOUNDARIES = {"zero", "edge", "reflect", "shrink", "drop"}


def effective_period_seconds(period: int) -> int:
    return 60 if period == 1 else period


def smoothing_window_size(smoothing_time: int, period: int) -> int:
    if isinstance(smoothing_time, bool) or not isinstance(smoothing_time, int) or smoothing_time <= 0:
        raise MetricAnalysisError(
            "invalid_request",
            "smoothing_time must be a positive integer",
        )
    effective_period = effective_period_seconds(period)
    if effective_period <= 0:
        raise MetricAnalysisError(
            "invalid_request",
            "period must resolve to a positive number of seconds",
        )
    points = math.ceil(smoothing_time / effective_period)
    return points // 2 * 2 + 1


def smooth(
    values: npt.ArrayLike,
    *,
    method: SmoothingMethod,
    window_size: int,
    boundary: BoundaryMode,
) -> list[float]:
    array = np.asarray(values, dtype=np.float64)
    _validate_smoothing_request(array, method, window_size, boundary)
    if window_size == 1:
        return array.tolist()

    if boundary == "shrink":
        return _smooth_shrinking_window(array, method, window_size)

    if boundary == "drop":
        if len(array) < window_size:
            raise MetricAnalysisError(
                "invalid_request",
                "series must contain at least window_size datapoints for drop boundary mode",
            )
        windows = np.lib.stride_tricks.sliding_window_view(array, window_size)
        return _aggregate_windows(windows, method).tolist()

    padding = window_size // 2
    if boundary == "zero":
        padded = np.pad(array, padding, mode="constant", constant_values=0)
    elif boundary == "edge":
        padded = np.pad(array, padding, mode="edge")
    else:
        pad_mode = "edge" if len(array) == 1 else "reflect"
        padded = np.pad(array, padding, mode=pad_mode)
    windows = np.lib.stride_tricks.sliding_window_view(padded, window_size)
    return _aggregate_windows(windows, method).tolist()


def _smooth_shrinking_window(
    array: np.ndarray,
    method: SmoothingMethod,
    window_size: int,
) -> list[float]:
    rolling = pd.Series(array).rolling(
        window=window_size,
        center=True,
        min_periods=1,
    )
    result = rolling.median() if method == "median" else rolling.mean()
    return result.astype(float).tolist()


def _aggregate_windows(
    windows: np.ndarray,
    method: SmoothingMethod,
) -> np.ndarray:
    if method == "median":
        return np.median(windows, axis=-1)
    return np.mean(windows, axis=-1)


def _validate_smoothing_request(
    array: np.ndarray,
    method: str,
    window_size: int,
    boundary: str,
) -> None:
    if array.ndim != 1 or array.size == 0:
        raise MetricAnalysisError(
            "invalid_request",
            "smoothing requires a non-empty one-dimensional series",
        )
    if not np.isfinite(array).all():
        raise MetricAnalysisError(
            "invalid_request",
            "smoothing values must all be finite numbers",
        )
    if method not in _SUPPORTED_METHODS:
        raise MetricAnalysisError(
            "invalid_request",
            f"unsupported smoothing method: {method}",
        )
    if boundary not in _SUPPORTED_BOUNDARIES:
        raise MetricAnalysisError(
            "invalid_request",
            f"unsupported smoothing boundary mode: {boundary}",
        )
    if isinstance(window_size, bool) or not isinstance(window_size, int) or window_size <= 0:
        raise MetricAnalysisError(
            "invalid_request",
            "window_size must be a positive integer",
        )
    if window_size % 2 == 0:
        raise MetricAnalysisError(
            "invalid_request",
            "window_size must be odd",
        )
