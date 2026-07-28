from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, Mapping, TypeVar

from metric_timeseries_analysis.analysis.context import AnalysisContext
from metric_timeseries_analysis.analysis.options import (
    build_median_p75_options,
    build_rising_trend_options,
    build_sliding_window_threshold_options,
    build_spike_drop_options,
    build_trend_prediction_options,
)
from metric_timeseries_analysis.analysis.profile import (
    AnalysisProfile,
    ProfileAnalysisResult,
)
from metric_timeseries_analysis.analysis.profiles.median_p75 import MedianP75Statistics
from metric_timeseries_analysis.analysis.profiles.rising_trend import RisingTrendDetection
from metric_timeseries_analysis.analysis.profiles.sliding_window_threshold_frequency import SlidingWindowThresholdFrequencyDetection
from metric_timeseries_analysis.analysis.profiles.spike_drop import SpikeDropDetection
from metric_timeseries_analysis.analysis.profiles.trend_prediction import TrendPrediction
from metric_timeseries_analysis.errors import MetricAnalysisError
from metric_timeseries_analysis.series.model import MetricSeriesMap


OptionsT = TypeVar("OptionsT")


@dataclass(frozen=True)
class ProfileBinding(Generic[OptionsT]):
    analyzer: AnalysisProfile[OptionsT]
    options_factory: Callable[[Mapping[str, Any]], OptionsT]

    @property
    def name(self) -> str:
        return self.analyzer.name

    def run(
        self,
        series_by_metric: MetricSeriesMap,
        context: AnalysisContext,
        normalized_analysis: Mapping[str, Any],
    ) -> ProfileAnalysisResult:
        options = self.options_factory(normalized_analysis)
        return self.analyzer.run(series_by_metric, context, options)


class AnalysisProfileRegistry:
    def __init__(self) -> None:
        bindings: list[ProfileBinding[Any]] = [
            ProfileBinding(
                SlidingWindowThresholdFrequencyDetection(),
                build_sliding_window_threshold_options,
            ),
            ProfileBinding(SpikeDropDetection(), build_spike_drop_options),
            ProfileBinding(MedianP75Statistics(), build_median_p75_options),
            ProfileBinding(
                RisingTrendDetection(),
                build_rising_trend_options,
            ),
            ProfileBinding(TrendPrediction(), build_trend_prediction_options),
        ]
        self._bindings = {binding.name: binding for binding in bindings}

    def run(
        self,
        profile: str,
        series_by_metric: MetricSeriesMap,
        context: AnalysisContext,
        normalized_analysis: Mapping[str, Any],
    ) -> ProfileAnalysisResult:
        binding = self._bindings.get(profile)
        if binding is None:
            raise MetricAnalysisError("invalid_request", f"unsupported analysis profile: {profile}")
        return binding.run(series_by_metric, context, normalized_analysis)


DEFAULT_REGISTRY = AnalysisProfileRegistry()


def run_analysis(
    profile: str,
    series_by_metric: MetricSeriesMap,
    context: AnalysisContext,
    normalized_analysis: Mapping[str, Any],
) -> ProfileAnalysisResult:
    return DEFAULT_REGISTRY.run(
        profile,
        series_by_metric,
        context,
        normalized_analysis,
    )
