from __future__ import annotations

from typing import Any

from metric_timeseries_analysis.analysis.context import AnalysisContext
from metric_timeseries_analysis.analysis.detectors.spike_drop_detector import (
    SpikeDropDetector,
)
from metric_timeseries_analysis.analysis.options import CoincidentAnomalyOptions
from metric_timeseries_analysis.analysis.profile import ProfileAnalysisResult
from metric_timeseries_analysis.series.model import MetricSeriesMap


class CoincidentAnomalyDetection:
    """判断两个指标是否在故障发生前的同一回看窗口内出现异常。"""

    name = "coincident_anomaly_detection"

    def __init__(self, detector: SpikeDropDetector | None = None) -> None:
        self.detector = detector or SpikeDropDetector()

    def run(
        self,
        series_by_metric: MetricSeriesMap,
        context: AnalysisContext,
        options: CoincidentAnomalyOptions,
    ) -> ProfileAnalysisResult:
        metric_names = list(series_by_metric)
        findings = self.detector.detect(
            series_by_metric,
            context,
            options.spike_drop_options(),
        )
        window_start = options.time_point - options.lookback_seconds * 1000
        events_by_metric = {
            metric_name: [
                finding
                for finding in findings
                if finding["metric_name"] == metric_name
                and window_start
                <= int(finding["time_window"]["start"])
                <= options.time_point
            ]
            for metric_name in metric_names
        }
        correlated = bool(metric_names) and all(events_by_metric.values())
        if not correlated:
            return {
                "summary": (
                    "The requested metrics did not both have anomalies in the pre-incident window."
                ),
                "findings": [],
            }

        metric_evidence = [
            _metric_evidence(
                metric_name,
                series_by_metric[metric_name],
                events_by_metric[metric_name],
                window_start,
                options.time_point,
            )
            for metric_name in metric_names
        ]
        return {
            "summary": "Both requested metrics had anomalies in the pre-incident window.",
            "findings": [
                {
                    "kind": "coincident_anomaly",
                    "severity": "warning",
                    "metric_name": metric_names,
                    "confidence": 1.0,
                    "time_window": {
                        "start": window_start,
                        "end": options.time_point,
                    },
                    "evidence": {
                        "time_point": options.time_point,
                        "lookback_seconds": options.lookback_seconds,
                        "metrics": metric_evidence,
                    },
                }
            ],
        }


def _metric_evidence(
    metric_name: str,
    series: list[dict[str, Any]],
    events: list[dict[str, Any]],
    window_start: int,
    time_point: int,
) -> dict[str, Any]:
    nearest = min(
        events,
        key=lambda event: time_point - int(event["time_window"]["start"]),
    )
    values = [
        float(point["value"])
        for point in series
        if window_start <= int(point["timestamp"]) <= time_point
    ]
    event_values = [float(event["evidence"]["value"]) for event in events]
    kinds = sorted({str(event["kind"]) for event in events})
    abnormal_value = (
        min(event_values)
        if kinds == ["drop"]
        else max(event_values)
    )
    nearest_time = int(nearest["time_window"]["start"])
    return {
        "metric_name": metric_name,
        "abnormal": True,
        "kinds": kinds,
        "anomaly_count": len(events),
        "nearest_anomaly_time": nearest_time,
        "time_diff_ms": time_point - nearest_time,
        "min_value": min(values) if values else None,
        "abnormal_value": abnormal_value,
    }
