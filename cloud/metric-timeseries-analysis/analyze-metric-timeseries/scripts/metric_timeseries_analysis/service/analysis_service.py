from __future__ import annotations

from typing import Any

from metric_timeseries_analysis.analysis.context import AnalysisContext
from metric_timeseries_analysis.analysis.registry import run_analysis
from metric_timeseries_analysis.cache.dataset_store import load_dataset, persist_dataset
from metric_timeseries_analysis.cache.index_store import cache_get, cache_put
from metric_timeseries_analysis.cache.key import cache_key_for
from metric_timeseries_analysis.cache.locking import cache_key_lock
from metric_timeseries_analysis.ces.fetcher import CesFetcher
from metric_timeseries_analysis.ces.limits import validate_ces_limits
from metric_timeseries_analysis.ces.mcp_cli_fetcher import McpCliCesFetcher
from metric_timeseries_analysis.contracts.result import build_result
from metric_timeseries_analysis.contracts.spec import (
    find_missing_required_fields,
    normalize_metric_analysis_spec,
)
from metric_timeseries_analysis.errors import MetricAnalysisError


class MetricAnalysisService:
    def __init__(self, fetcher: CesFetcher | None = None) -> None:
        self.fetcher = fetcher or McpCliCesFetcher()

    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            missing_fields = find_missing_required_fields(payload)
            if missing_fields:
                fields = ", ".join(missing_fields)
                return {
                    "success": False,
                    "error": "missing_required_input",
                    "message": (
                        f"Missing required inputs: {fields}. "
                        "Collect all missing values before retrying."
                    ),
                    "missing_fields": missing_fields,
                    "retryable": False,
                }

            spec = normalize_metric_analysis_spec(payload)
            limit_error = validate_ces_limits(spec)
            if limit_error:
                return limit_error

            cache_key = cache_key_for(spec["ces_query"])
            with cache_key_lock(cache_key):
                cached = cache_get(cache_key)
                if cached:
                    dataset = load_dataset(cached["dataset_ref"])
                else:
                    raw = self.fetcher.fetch(spec["ces_query"])
                    dataset = persist_dataset(spec, raw, cache_key)
                    cache_put(cache_key, spec, dataset)

            profile = spec["analysis"]["profile"]
            context = AnalysisContext.from_period(spec["period"])
            analysis = run_analysis(
                profile,
                dataset["series_by_metric"],
                context,
                spec["analysis"],
            )
            return build_result(spec, profile, analysis)
        except MetricAnalysisError as exc:
            if exc.code == "internal_error":
                return {
                    "success": False,
                    "error": "internal_error",
                    "message": "Metric analysis failed unexpectedly",
                }
            return {"success": False, "error": exc.code, "message": exc.message, **exc.extra}
        except Exception:
            return {
                "success": False,
                "error": "internal_error",
                "message": "Metric analysis failed unexpectedly",
            }
