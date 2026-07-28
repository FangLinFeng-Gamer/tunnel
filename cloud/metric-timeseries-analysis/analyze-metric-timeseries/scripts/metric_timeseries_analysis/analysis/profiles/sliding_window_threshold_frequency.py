from __future__ import annotations

import numpy as np

from metric_timeseries_analysis.analysis.context import AnalysisContext
from metric_timeseries_analysis.analysis.options import SlidingWindowThresholdOptions
from metric_timeseries_analysis.analysis.profile import ProfileAnalysisResult
from metric_timeseries_analysis.series.model import MetricSeriesMap


class SlidingWindowThresholdFrequencyDetection:
    """滑动窗口阈值频次检测。

    按固定数据点数量滑动窗口，统计窗口内达到阈值条件的数据点数量；
    命中次数达到 min_frequency 时，返回对应时间窗口和命中证据。
    """

    name = "sliding_window_threshold_frequency_detection"

    def run(
        self,
        series_by_metric: MetricSeriesMap,
        context: AnalysisContext,
        options: SlidingWindowThresholdOptions,
    ) -> ProfileAnalysisResult:
        del context
        findings = []
        for metric_name, series in series_by_metric.items():
            if len(series) < options.window_points:
                continue

            values = np.fromiter(
                (point["value"] for point in series),
                dtype=np.float64,
                count=len(series),
            )
            hit_mask = (
                values <= options.threshold
                if options.direction == "below"
                else values >= options.threshold
            )
            hit_counts = np.convolve(
                hit_mask.astype(np.int64),
                np.ones(options.window_points, dtype=np.int64),
                mode="valid",
            )

            for start_index in np.flatnonzero(
                hit_counts >= options.min_frequency
            ):
                start = int(start_index)
                end = start + options.window_points - 1
                hits = int(hit_counts[start])
                findings.append(
                    {
                        "kind": "threshold_frequency",
                        "severity": "warning",
                        "metric_name": metric_name,
                        "confidence": hits / options.window_points,
                        "time_window": {
                            "start": series[start]["timestamp"],
                            "end": series[end]["timestamp"],
                        },
                        "evidence": {
                            "threshold": options.threshold,
                            "direction": options.direction,
                            "window_points": options.window_points,
                            "hit_count": hits,
                            "min_frequency": options.min_frequency,
                        },
                    }
                )
        return {
            "summary": (
                "Found threshold-frequency windows."
                if findings
                else "No threshold-frequency window was found."
            ),
            "findings": findings[:20],
        }
