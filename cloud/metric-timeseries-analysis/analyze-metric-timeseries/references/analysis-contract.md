# Metric Time-Series Analysis Contract

This skill is a common capability for service-category skills. It hides CES fetch, dataset persistence, and cache behavior behind a compact script call.

Pass `MetricAnalysisSpec` directly through the CLI `--args` option as a JSON object string. `--args` is not a file path, and callers do not create a temporary spec file.

CLI input:

```bash
python3 scripts/analyze_metric_timeseries.py \
  analyze --args '<MetricAnalysisSpec JSON>'
```

CLI output is exactly one compact JSON object: `AnalysisResult` on a completed analysis or the error object defined below.

The CLI above is the public execution boundary. Callers must not import implementation modules or invoke profile classes directly. Before calling it, callers must resolve every required field from user input or trusted tool output. If any required field is unavailable, ask the user for all missing fields together and do not invoke the CLI until they are supplied.

## Boundary

Visible to service skills:

```text
MetricAnalysisSpec -> AnalysisResult
```

Hidden from service skills:

```text
CES raw API response
raw datapoints
DatasetStore implementation
cache index
terminal output truncation details
```

## MetricAnalysisSpec

`time_window.from` and `time_window.to` are technical CLI fields, not user-facing inputs. The calling skill accepts a natural-language time range and resolves it to integer millisecond timestamps before constructing this object.

Required fields:

```text
region
project_id
metric.namespace
metric.metric_name
metric.dimensions
time_window.from
time_window.to
period
analysis.profile
```

Optional fields:

```text
analysis profile options
```

The caller does not provide an aggregation filter. The implementation always uses the CES `average` aggregation.

`metric.metric_name` is a non-empty array of unique metric-name strings. Existing single-series profiles require exactly one item. `coincident_anomaly_detection` requires exactly two items. All items share the same namespace, dimensions, region, project, time window, period, and internal aggregation.

`metric.dimensions[].name` is not hardcoded. Use the dimension key from the target CES metric documentation, such as `instance_id` only when that metric defines `instance_id` as its dimension.

CES field constraints are validated before fetching: `project_id` is 1-64 characters, timestamps are within the CES millisecond range, namespace and metric names follow the CES formats, and each metric has 1-4 dimensions. Profile options are also strict: unknown options, wrong JSON types, invalid choices, and inconsistent window settings are rejected.

Profile parameter help is available from the bundled CLI:

```bash
python3 scripts/analyze_metric_timeseries.py profiles
python3 scripts/analyze_metric_timeseries.py profile <profile-name>
python3 scripts/analyze_metric_timeseries.py profile <profile-name> --help
```

`profile <profile-name>` prints JSON with `min_metric_count`, `max_metric_count`, option names, types, defaults, choices, and an `example_analysis` block that can be copied into `MetricAnalysisSpec.analysis`.

Profile options:

| Profile | Options |
| --- | --- |
| `sliding_window_threshold_frequency_detection` | `threshold` is required; `direction`, `window_points`, and `min_frequency` are optional. |
| `spike_drop_detection` | `box_scale`, `direction`, `window_size`, `residual_sen`, and `nonzero` are optional. Defaults: `3`, `up`, `3600`, `10`, and `false`. |
| `median_p75_statistics` | `smoothing_time` is an optional positive integer in seconds and defaults to `900`. |
| `rising_trend_detection` | No additional options. |
| `trend_prediction` | No additional options. Requires at least seven days of metric history. |
| `coincident_anomaly_detection` | Exactly two metrics. `time_point` is required in milliseconds; `lookback_seconds` defaults to `1800`. The spike/drop options `box_scale`, `direction`, `window_size`, `residual_sen`, and `nonzero` are optional. |

For `median_p75_statistics`, the script derives an odd median-smoothing window from `ceil(smoothing_time / effective_period)`, uses zero padding at both series boundaries, and computes median and p75 from the smoothed values. `period = 1` uses an effective period of 60 seconds.

For `spike_drop_detection`, `window_size` is a smoothing duration in seconds. The script first applies edge-padded mean smoothing and skips outlier detection when the residual range is below `residual_sen`. It then applies edge-padded median smoothing and detects box-plot outliers in both the residual sequence and the first difference of the smoothed trend. `direction` accepts `up`, `down`, or `all`; `box_scale` controls the IQR bounds; `nonzero=true` excludes zeros while estimating those bounds.

For `rising_trend_detection`, the script applies `np.diff` to adjacent values and counts positive and negative differences. More positive differences produce `judge=true` and an upward result; more negative differences produce a downward result; equal counts produce no clear trend. Zero differences do not affect the direction comparison. This profile does not forecast future values.

Its finding evidence has this shape:

```json
{
  "kind": "rising_trend",
  "severity": "warning",
  "metric_name": "cpu_util",
  "confidence": 1.0,
  "evidence": {
    "judge": true,
    "trend": "upward",
    "increasing_count": 3,
    "decreasing_count": 1,
    "unchanged_count": 0,
    "comparison_count": 4
  }
}
```

For `trend_prediction`, timestamps are floored to the hour and values in the same hour are averaged. The timezone is removed before fitting `Prophet(growth="linear", changepoint_range=0.9)`. The model predicts 168 hourly values with `include_history=false`. The 168 derived points remain internal; `forecast` and finding evidence contain only their start/end time, first/last/min/max/mean value, total change, change ratio, and direction.

For `coincident_anomaly_detection`, the script applies the same spike/drop detector used by `spike_drop_detection` independently to both metrics. It reports a coincident anomaly only when both metrics contain an anomaly in the closed interval `[time_point - lookback_seconds, time_point]`. The default interval is the 30 minutes before the incident. Events after `time_point` are not evidence. The result includes compact per-metric anomaly summaries and does not expose raw datapoints.

## AnalysisResult

`AnalysisResult` is the compact JSON object printed by the script. It is the only result service skills should use as metric evidence.

Required success shape:

```json
{
  "success": true,
  "metric_name": ["cpu_util"],
  "profile": "trend_prediction",
  "summary": "Forecasted the next seven days with Prophet.",
  "findings": []
}
```

`findings` is always an array. Event-detection profiles return matching structured records or an empty array when no event is detected. Statistical and trend profiles return their corresponding structured summary records.

Optional fields:

```text
statistics             Compact statistics for the requested metric.
forecast               Compact forecast for the requested metric.
```

`trend_prediction.forecast` fields:

```text
forecast_hours          Always 168.
start_time              First forecast timestamp in milliseconds.
end_time                Last forecast timestamp in milliseconds.
first_predicted_value   First hourly Prophet yhat.
last_predicted_value    Last hourly Prophet yhat.
min_predicted_value     Minimum yhat over 168 hours.
max_predicted_value     Maximum yhat over 168 hours.
mean_predicted_value    Mean yhat over 168 hours.
change                  Last predicted value minus first predicted value.
change_ratio            change / abs(first_predicted_value), or null when the first value is zero.
direction               upward, downward, or flat.
```

`median_p75_statistics` returns:

```json
{
  "success": true,
  "metric_name": ["cpu_util"],
  "profile": "median_p75_statistics",
  "summary": "Computed median and p75 statistics for the requested metric.",
  "findings": [
    {
      "kind": "distribution_summary",
      "severity": "info",
      "metric_name": "cpu_util",
      "confidence": 1.0,
      "evidence": {
        "count": 4,
        "min": 10.0,
        "max": 40.0,
        "median": 25.0,
        "p75": 30.0
      }
    }
  ],
  "statistics": {
    "count": 4,
    "min": 10.0,
    "max": 40.0,
    "median": 25.0,
    "p75": 30.0
  }
}
```

For this profile, `count`, `min`, and `max` describe the valid input series; `median` and `p75` are computed from the zero-padded median-smoothed series.

For `coincident_anomaly_detection`, the top-level `metric_name` contains both requested names. A matching finding has `kind = "coincident_anomaly"`; its evidence contains `time_point`, `lookback_seconds`, and one compact anomaly summary for each metric. When either metric has no anomaly in the incident lookback interval, `findings` is empty and `summary` explains which condition was not met.

The success result is an LLM-visible allowlist. It must not contain raw datapoints, `analysis_id`, `dataset_ref`, cache state, file paths, hashes, byte counts, or internal `statistics_by_metric` / `forecast_by_metric` maps. Operational and cache metadata remain in internal logs, DatasetStore, and the cache index.

## CES Query Limit

The script plans one or more Huawei Cloud CES batch requests. Each emitted request enforces:

```text
metrics_count <= 500
metrics_count * (to - from) / period <= 3000
serialized CES request body <= 512KB
```

For `period = 1`, the script follows the CES API behavior and treats the effective period as 60 seconds for this limit calculation.

Only cache misses are included in CES requests. When adding another metric would exceed a limit, the planner starts another request without shortening that metric's requested time range. A single metric that exceeds the datapoint limit by itself fails with `query_too_large`; a single request body over 512KB fails with `invalid_request`.

## Cache

The script caches CES time-series datasets, not analysis results. Every cache entry and dataset contains exactly one metric, even when several metrics were fetched in one CES request. A batch response is split by metric before persistence; a partial cache hit therefore fetches only the missing metrics.

Cache key:

```text
sha256(canonical normalized CES query)
```

Included in the key:

```text
project_id
region
namespace
metric name
dimensions as CES MetricInfo `{name, value}` array
from/to
period
internal aggregation (`average`)
normalization version
backend version
```

Excluded from the key:

```text
user natural language
skill name
analysis profile
analysis options
dataset path
trace id
```

Eviction triggers:

```text
1. Lazy eviction on cache get when TTL, index, dataset path, or sha256 validation fails.
2. Capacity eviction on cache put when max bytes or max entries is exceeded. Expired entries are removed first, then LRU entries.
```

Cache policy is service-owned and cannot be overridden by `MetricAnalysisSpec`. Capacity counts all persisted files in each dataset. Each planned CES batch acquires only its involved single-metric cache-key locks in stable order and rechecks the cache after locking. One caller performs each miss while concurrent callers reuse the dataset; locks are released before the next batch.

Default cache root:

```text
${HERMES_HOME:-$HOME/.hermes}/datasets/metric-analysis
```

## Error Contract

`query_too_large` means one metric exceeds the CES datapoint limit without shortening its requested time range.

`data_fetch_failed` means the internal MCP CLI adapter or backend command failed.

`missing_required_input` means one or more required fields are absent. It returns every absent field in one response and must not trigger an automatic retry:

```json
{
  "success": false,
  "error": "missing_required_input",
  "message": "Missing required inputs: project_id, time_window.to. Collect all missing values before retrying.",
  "missing_fields": ["project_id", "time_window.to"]
}
```

The caller first resolves `missing_fields` from trusted context, then asks the user for every unresolved value in one clarification. A missing `time_window.from` or `time_window.to` means the caller should ask for a natural-language time range, not millisecond timestamps.

`invalid_request` means a supplied `MetricAnalysisSpec` field has an invalid type, value, combination, or unsupported option.

`internal_error` uses a fixed generic message and does not expose exception types, paths, or backend details.

All errors are returned as compact JSON:

```json
{
  "success": false,
  "error": "query_too_large",
  "message": "metrics_count * (to - from) / period exceeds 3000"
}
```
