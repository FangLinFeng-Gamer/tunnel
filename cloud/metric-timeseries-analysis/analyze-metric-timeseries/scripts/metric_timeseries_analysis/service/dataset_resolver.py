from __future__ import annotations

from typing import Any

from metric_timeseries_analysis.cache.dataset_store import load_dataset, persist_dataset
from metric_timeseries_analysis.cache.index_store import cache_get, cache_put
from metric_timeseries_analysis.cache.key import cache_key_for
from metric_timeseries_analysis.cache.locking import cache_key_locks
from metric_timeseries_analysis.ces.batch_planner import plan_ces_batches
from metric_timeseries_analysis.ces.fetcher import CesFetcher
from metric_timeseries_analysis.ces.response_splitter import split_ces_batch_response
from metric_timeseries_analysis.series.model import MetricSeriesMap


class MetricDatasetResolver:
    def __init__(self, fetcher: CesFetcher) -> None:
        self.fetcher = fetcher

    def resolve(self, spec: dict[str, Any]) -> MetricSeriesMap:
        queries = spec["ces_queries"]
        query_by_name = {
            _query_metric_name(query): query
            for query in queries
        }
        cache_keys = {
            name: cache_key_for(query)
            for name, query in query_by_name.items()
        }

        series_by_metric: MetricSeriesMap = {}
        for planned_batch in plan_ces_batches(queries):
            batch_names = [
                str(metric["metric_name"])
                for metric in planned_batch["request_body"]["metrics"]
            ]
            with cache_key_locks([cache_keys[name] for name in batch_names]):
                missing_queries: list[dict[str, Any]] = []
                for name in batch_names:
                    cached = cache_get(cache_keys[name])
                    if cached:
                        series_by_metric.update(
                            load_dataset(cached["dataset_ref"])["series_by_metric"]
                        )
                    else:
                        missing_queries.append(query_by_name[name])

                for batch_query in plan_ces_batches(missing_queries):
                    raw = self.fetcher.fetch(batch_query)
                    split_raw = split_ces_batch_response(raw, batch_query)
                    for metric in batch_query["request_body"]["metrics"]:
                        name = str(metric["metric_name"])
                        single_query = query_by_name[name]
                        single_spec = _single_metric_spec(spec, name, single_query)
                        dataset = persist_dataset(
                            single_spec,
                            split_raw[name],
                            cache_keys[name],
                        )
                        cache_put(cache_keys[name], single_spec, dataset)
                        series_by_metric.update(dataset["series_by_metric"])

        return {
            name: series_by_metric[name]
            for name in spec["metric"]["metric_name"]
        }


def _query_metric_name(query: dict[str, Any]) -> str:
    return str(query["request_body"]["metrics"][0]["metric_name"])


def _single_metric_spec(
    spec: dict[str, Any],
    metric_name: str,
    ces_query: dict[str, Any],
) -> dict[str, Any]:
    return {
        **spec,
        "metric": {**spec["metric"], "metric_name": metric_name},
        "ces_query": ces_query,
    }
