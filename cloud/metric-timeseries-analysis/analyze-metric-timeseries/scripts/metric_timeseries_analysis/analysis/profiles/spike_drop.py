from __future__ import annotations

from metric_timeseries_analysis.analysis.context import AnalysisContext
from metric_timeseries_analysis.analysis.detectors.spike_drop_detector import (
    SpikeDropDetector,
)
from metric_timeseries_analysis.analysis.options import SpikeDropOptions
from metric_timeseries_analysis.analysis.profile import ProfileAnalysisResult
from metric_timeseries_analysis.series.model import MetricSeriesMap


class SpikeDropDetection:
    """指标突增或突降检测。"""

    name = "spike_drop_detection"

    def __init__(self, detector: SpikeDropDetector | None = None) -> None:
        self.detector = detector or SpikeDropDetector()

    def run(
        self,
        series_by_metric: MetricSeriesMap,
        context: AnalysisContext,
        options: SpikeDropOptions,
    ) -> ProfileAnalysisResult:
        findings = self.detector.detect(series_by_metric, context, options)
        return {
            "summary": (
                "Detected sudden spikes or drops."
                if findings
                else "No sudden spike or drop was detected."
            ),
            "findings": findings[:20],
        }
