from __future__ import annotations

import numpy as np

from metric_timeseries_analysis.analysis.context import AnalysisContext
from metric_timeseries_analysis.analysis.options import RisingTrendOptions
from metric_timeseries_analysis.analysis.profile import ProfileAnalysisResult
from metric_timeseries_analysis.series.model import MetricSeriesMap


class RisingTrendDetection:
    """相邻数据点方向计数趋势检测。

    对相邻数据点做一阶差分，分别统计上升和下降次数；上升次数更多时
    判定为上升趋势，下降次数更多时判定为下降趋势，否则无明显变化。
    """

    name = "rising_trend_detection"

    def run(
        self,
        series_by_metric: MetricSeriesMap,
        context: AnalysisContext,
        options: RisingTrendOptions,
    ) -> ProfileAnalysisResult:
        del context, options
        findings = []
        for metric_name, series in series_by_metric.items():
            if len(series) < 2:
                continue

            values = np.fromiter(
                (point["value"] for point in series),
                dtype=np.float64,
                count=len(series),
            )
            differences = np.diff(values)
            increasing_count = int(np.count_nonzero(differences > 0))
            decreasing_count = int(np.count_nonzero(differences < 0))
            unchanged_count = int(np.count_nonzero(differences == 0))

            if increasing_count > decreasing_count:
                judge = True
                trend = "upward"
                kind = "rising_trend"
                severity = "warning"
            elif decreasing_count > increasing_count:
                judge = False
                trend = "downward"
                kind = "falling_trend"
                severity = "info"
            else:
                judge = False
                trend = "no_clear_change"
                kind = "no_clear_trend"
                severity = "info"

            findings.append(
                {
                    "kind": kind,
                    "severity": severity,
                    "metric_name": metric_name,
                    "confidence": 1.0,
                    "evidence": {
                        "judge": judge,
                        "trend": trend,
                        "increasing_count": increasing_count,
                        "decreasing_count": decreasing_count,
                        "unchanged_count": unchanged_count,
                        "comparison_count": len(differences),
                    },
                }
            )

        if not findings:
            return {
                "summary": "Insufficient data to determine the metric trend.",
                "findings": [],
            }

        trend = findings[0]["evidence"]["trend"]
        summaries = {
            "upward": "The metric shows a rising trend.",
            "downward": "The metric shows a falling trend.",
            "no_clear_change": "The metric shows no clear directional trend.",
        }
        return {
            "summary": summaries[trend],
            "findings": findings,
        }
