from __future__ import annotations

from typing import Any, Generic, Protocol, Required, TypeVar, TypedDict

from metric_timeseries_analysis.analysis.context import AnalysisContext
from metric_timeseries_analysis.series.model import MetricSeriesMap


class ProfileAnalysisResult(TypedDict, total=False):
    summary: Required[str]
    findings: Required[list[dict[str, Any]]]
    statistics_by_metric: dict[str, dict[str, Any]]
    forecast_by_metric: dict[str, dict[str, Any]]


OptionsT = TypeVar("OptionsT")


class AnalysisProfile(Protocol, Generic[OptionsT]):
    name: str

    def run(
        self,
        series_by_metric: MetricSeriesMap,
        context: AnalysisContext,
        options: OptionsT,
    ) -> ProfileAnalysisResult:
        ...
