from __future__ import annotations

import pandas as pd

from metric_timeseries_analysis.analysis.context import AnalysisContext
from metric_timeseries_analysis.analysis.options import MedianP75Options
from metric_timeseries_analysis.analysis.profile import ProfileAnalysisResult
from metric_timeseries_analysis.series.model import MetricSeriesMap
from metric_timeseries_analysis.series.smoothing import smooth, smoothing_window_size


class MedianP75Statistics:
    """平滑后的中位数和 P75 统计。

    根据平滑时间和指标时间粒度计算奇数窗口，对序列执行两端补零的
    滑动中值平滑，再对平滑结果计算中位数和 75 分位数。
    """

    name = "median_p75_statistics"

    def run(
        self,
        series_by_metric: MetricSeriesMap,
        context: AnalysisContext,
        options: MedianP75Options,
    ) -> ProfileAnalysisResult:
        findings = []
        statistics = {}
        for metric_name, series in series_by_metric.items():
            values = [point["value"] for point in series]
            window_size = smoothing_window_size(
                options.smoothing_time,
                context.granularity_seconds,
            )
            smoothed = smooth(
                values,
                method="median",
                window_size=window_size,
                boundary="zero",
            )
            smoothed_series = pd.Series(smoothed, dtype="float64")
            stats = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "median": float(smoothed_series.quantile(0.5, interpolation="linear")),
                "p75": float(smoothed_series.quantile(0.75, interpolation="linear")),
            }
            statistics[metric_name] = stats
            findings.append({"kind": "distribution_summary", "severity": "info", "metric_name": metric_name, "confidence": 1.0, "evidence": stats})
        return {"summary": "Computed median and p75 statistics for the requested metric.", "statistics_by_metric": statistics, "findings": findings}
