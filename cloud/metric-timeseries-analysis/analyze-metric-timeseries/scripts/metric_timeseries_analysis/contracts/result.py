from __future__ import annotations

from typing import Any

from metric_timeseries_analysis.analysis.profile import ProfileAnalysisResult


def build_result(
    spec: dict[str, Any],
    profile: str,
    analysis: ProfileAnalysisResult,
) -> dict[str, Any]:
    metric_names = spec["metric"]["metric_name"]
    result = {
        "success": True,
        "metric_name": metric_names,
        "profile": profile,
        "summary": analysis["summary"],
        "findings": analysis.get("findings", []),
    }
    if "statistics_by_metric" in analysis:
        result["statistics"] = analysis["statistics_by_metric"].get(metric_names[0], {})
    if "forecast_by_metric" in analysis:
        result["forecast"] = analysis["forecast_by_metric"].get(metric_names[0], {})
    return result
