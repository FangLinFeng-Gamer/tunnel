from __future__ import annotations

import numpy as np

from metric_timeseries_analysis.analysis.context import AnalysisContext
from metric_timeseries_analysis.analysis.options import SpikeDropOptions
from metric_timeseries_analysis.analysis.profile import ProfileAnalysisResult
from metric_timeseries_analysis.series.model import MetricSeriesMap
from metric_timeseries_analysis.series.smoothing import smooth, smoothing_window_size
from metric_timeseries_analysis.series.statistics import box_plot_outlier_bounds


class SpikeDropDetection:
    """指标突增或突降检测。

    先用均值平滑后的残差范围过滤正常小波动，再分别对中值平滑残差
    和中值平滑趋势的一阶差分执行箱线图异常检测。
    """

    name = "spike_drop_detection"

    def run(
        self,
        series_by_metric: MetricSeriesMap,
        context: AnalysisContext,
        options: SpikeDropOptions,
    ) -> ProfileAnalysisResult:
        findings = []
        for metric_name, series in series_by_metric.items():
            values = np.fromiter(
                (point["value"] for point in series),
                dtype=np.float64,
                count=len(series),
            )
            if values.size == 0:
                continue

            window_points = smoothing_window_size(
                options.window_size,
                context.granularity_seconds,
            )
            mean_filtered = np.asarray(
                smooth(
                    values,
                    method="mean",
                    window_size=window_points,
                    boundary="edge",
                ),
                dtype=np.float64,
            )
            noise = values - mean_filtered
            if float(np.ptp(noise)) < options.residual_sen:
                continue

            median_filtered = np.asarray(
                smooth(
                    values,
                    method="median",
                    window_size=window_points,
                    boundary="edge",
                ),
                dtype=np.float64,
            )
            residuals = values - median_filtered
            residual_low, residual_high = box_plot_outlier_bounds(
                residuals,
                box_scale=options.box_scale,
                nonzero=options.nonzero,
            )

            trend_differences = np.diff(median_filtered)
            trend_low, trend_high = box_plot_outlier_bounds(
                trend_differences,
                box_scale=options.box_scale,
                nonzero=options.nonzero,
            )
            trend_differences = np.insert(trend_differences, 0, 0.0)

            residual_up = residuals > residual_high
            residual_down = residuals < residual_low
            trend_up = trend_differences > trend_high
            trend_down = trend_differences < trend_low
            up = residual_up | trend_up
            down = residual_down | trend_down

            if options.direction == "up":
                abnormal_indices = np.flatnonzero(up)
            elif options.direction == "down":
                abnormal_indices = np.flatnonzero(down)
            else:
                abnormal_indices = np.flatnonzero(up | down)

            for raw_index in abnormal_indices:
                index = int(raw_index)
                is_up = (
                    options.direction == "up"
                    or (
                        options.direction == "all"
                        and _is_upward_anomaly(
                            index,
                            residuals,
                            trend_differences,
                            up,
                            down,
                        )
                    )
                )
                triggers = []
                if residual_up[index] if is_up else residual_down[index]:
                    triggers.append("residual")
                if trend_up[index] if is_up else trend_down[index]:
                    triggers.append("trend")
                findings.append(
                    {
                        "kind": "spike" if is_up else "drop",
                        "severity": "warning",
                        "metric_name": metric_name,
                        "confidence": 1.0,
                        "time_window": {
                            "start": series[index]["timestamp"],
                            "end": series[index]["timestamp"],
                        },
                        "evidence": {
                            "value": float(values[index]),
                            "residual": float(residuals[index]),
                            "residual_bounds": {
                                "low": residual_low,
                                "high": residual_high,
                            },
                            "trend_delta": float(trend_differences[index]),
                            "trend_bounds": {
                                "low": trend_low,
                                "high": trend_high,
                            },
                            "triggers": triggers,
                            "window_size": options.window_size,
                            "window_points": window_points,
                        },
                    }
                )
        return {
            "summary": (
                "Detected sudden spikes or drops."
                if findings
                else "No sudden spike or drop was detected."
            ),
            "findings": findings[:20],
        }


def _is_upward_anomaly(
    index: int,
    residuals: np.ndarray,
    trend_differences: np.ndarray,
    up: np.ndarray,
    down: np.ndarray,
) -> bool:
    if up[index] and not down[index]:
        return True
    if down[index] and not up[index]:
        return False
    signal = residuals[index] if residuals[index] != 0 else trend_differences[index]
    return bool(signal >= 0)
