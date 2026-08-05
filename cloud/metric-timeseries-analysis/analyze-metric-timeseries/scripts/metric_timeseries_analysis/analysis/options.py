from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, cast


ThresholdDirection = Literal["above", "below"]
SpikeDropDirection = Literal["up", "down", "all"]


@dataclass(frozen=True, slots=True)
class SlidingWindowThresholdOptions:
    threshold: float
    direction: ThresholdDirection
    window_points: int
    min_frequency: int


@dataclass(frozen=True, slots=True)
class SpikeDropOptions:
    box_scale: float
    direction: SpikeDropDirection
    window_size: int
    residual_sen: float
    nonzero: bool


@dataclass(frozen=True, slots=True)
class CoincidentAnomalyOptions:
    time_point: int
    lookback_seconds: int
    box_scale: float
    direction: SpikeDropDirection
    window_size: int
    residual_sen: float
    nonzero: bool

    def spike_drop_options(self) -> SpikeDropOptions:
        return SpikeDropOptions(
            box_scale=self.box_scale,
            direction=self.direction,
            window_size=self.window_size,
            residual_sen=self.residual_sen,
            nonzero=self.nonzero,
        )


@dataclass(frozen=True, slots=True)
class MedianP75Options:
    smoothing_time: int


@dataclass(frozen=True, slots=True)
class RisingTrendOptions:
    pass


@dataclass(frozen=True, slots=True)
class TrendPredictionOptions:
    pass


def build_sliding_window_threshold_options(
    analysis: Mapping[str, Any],
) -> SlidingWindowThresholdOptions:
    return SlidingWindowThresholdOptions(
        threshold=float(analysis["threshold"]),
        direction=cast(ThresholdDirection, analysis["direction"]),
        window_points=int(analysis["window_points"]),
        min_frequency=int(analysis["min_frequency"]),
    )


def build_spike_drop_options(analysis: Mapping[str, Any]) -> SpikeDropOptions:
    return SpikeDropOptions(
        box_scale=float(analysis["box_scale"]),
        direction=cast(SpikeDropDirection, analysis["direction"]),
        window_size=int(analysis["window_size"]),
        residual_sen=float(analysis["residual_sen"]),
        nonzero=bool(analysis["nonzero"]),
    )


def build_coincident_anomaly_options(
    analysis: Mapping[str, Any],
) -> CoincidentAnomalyOptions:
    return CoincidentAnomalyOptions(
        time_point=int(analysis["time_point"]),
        lookback_seconds=int(analysis["lookback_seconds"]),
        box_scale=float(analysis["box_scale"]),
        direction=cast(SpikeDropDirection, analysis["direction"]),
        window_size=int(analysis["window_size"]),
        residual_sen=float(analysis["residual_sen"]),
        nonzero=bool(analysis["nonzero"]),
    )


def build_median_p75_options(analysis: Mapping[str, Any]) -> MedianP75Options:
    return MedianP75Options(smoothing_time=int(analysis["smoothing_time"]))


def build_rising_trend_options(
    analysis: Mapping[str, Any],
) -> RisingTrendOptions:
    del analysis
    return RisingTrendOptions()


def build_trend_prediction_options(
    analysis: Mapping[str, Any],
) -> TrendPredictionOptions:
    del analysis
    return TrendPredictionOptions()
