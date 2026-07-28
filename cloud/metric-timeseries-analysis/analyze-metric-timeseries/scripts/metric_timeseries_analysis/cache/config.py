from __future__ import annotations

from metric_timeseries_analysis.constants import (
    DEFAULT_CACHE_MAX_BYTES,
    DEFAULT_CACHE_MAX_ENTRIES,
    DEFAULT_HISTORICAL_TTL_SECONDS,
    DEFAULT_RECENT_TTL_SECONDS,
)


def cache_config() -> dict[str, int]:
    return {
        "recent_ttl_seconds": DEFAULT_RECENT_TTL_SECONDS,
        "historical_ttl_seconds": DEFAULT_HISTORICAL_TTL_SECONDS,
        "max_bytes": DEFAULT_CACHE_MAX_BYTES,
        "max_entries": DEFAULT_CACHE_MAX_ENTRIES,
    }
