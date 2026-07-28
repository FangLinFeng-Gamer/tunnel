---
name: analyze-metric-timeseries
description: Analyzes cloud monitoring metric time series for database and service diagnostics, including threshold frequency, spike/drop anomalies, median and p75 baselines, direction-count rising trends, and trend forecasting. Use when a diagnostic workflow needs metric evidence from CES or similar monitoring data without placing raw datapoints in model context.
---

# Analyze Metric Time-Series

Use this skill when a service diagnosis workflow needs compact analysis of monitoring metric time-series data. Run the bundled script with a `MetricAnalysisSpec` and use the returned `AnalysisResult` as diagnostic evidence.

Provide a compact `MetricAnalysisSpec` rather than raw datapoints. The bundled script fetches, caches, normalizes, and analyzes the metric time series, then prints a compact JSON `AnalysisResult`.

Before constructing CLI input or interpreting CLI output, read [references/analysis-contract.md](references/analysis-contract.md). It defines the complete `MetricAnalysisSpec`, profile options, `AnalysisResult`, and error JSON contracts.

## Script

Run:

```bash
python skills/metric-timeseries-analysis/analyze-metric-timeseries/scripts/analyze_metric_timeseries.py \
  analyze --args '{"region":"cn-north-4","project_id":"project-xxx","metric":{"namespace":"SYS.RDS","metric_name":"cpu_util","dimensions":[{"name":"instance_id","value":"rds-xxx"}]},"time_window":{"from":1784160000000,"to":1784764800000},"period":3600,"analysis":{"profile":"trend_prediction"}}'
```

`--args` takes the `MetricAnalysisSpec` JSON object as a string, not a file path. A calling skill should serialize the object to compact JSON and pass it directly; it does not create a temporary spec file.

CES fetching is internal to the bundled script. Do not put MCP CLI commands, raw CES queries, or raw datapoints in `MetricAnalysisSpec`.

Inspect profile parameters from the CLI instead of guessing them:

```bash
python skills/metric-timeseries-analysis/analyze-metric-timeseries/scripts/analyze_metric_timeseries.py profiles
python skills/metric-timeseries-analysis/analyze-metric-timeseries/scripts/analyze_metric_timeseries.py profile trend_prediction
python skills/metric-timeseries-analysis/analyze-metric-timeseries/scripts/analyze_metric_timeseries.py profile sliding_window_threshold_frequency_detection --help
```

## MetricAnalysisSpec

```json
{
  "region": "cn-north-4",
  "project_id": "project-xxx",
  "metric": {
    "namespace": "SYS.RDS",
    "metric_name": "cpu_util",
    "dimensions": [
      {
        "name": "instance_id",
        "value": "rds-xxx"
      }
    ]
  },
  "time_window": {
    "from": 1784200000000,
    "to": 1784210000000
  },
  "period": 300,
  "analysis": {
    "profile": "rising_trend_detection"
  }
}
```

The caller does not provide a CES aggregation filter. The script always queries and reads the `average` value.

`metric.dimensions` follows the Huawei Cloud CES `MetricInfo.dimensions` shape: an array of `{ "name": "...", "value": "..." }` objects. `dimensions[].name` must use the dimension key required by the target CES metric. The `instance_id` shown above is only an example and is valid only when that metric's CES documentation defines `instance_id` as its dimension.

The script validates CES field limits and rejects profile options that are unknown, have the wrong JSON type, or violate the profile's documented constraints. Cache policy is internal and is not accepted in `MetricAnalysisSpec`.

`analysis.profile` is required. Choose one profile from the table:

| Profile | Use For | Important Options |
| --- | --- | --- |
| `sliding_window_threshold_frequency_detection` | Count how often values cross a threshold inside rolling windows. Use for questions such as "how frequently CPU stays above 80%". | `threshold` required; `direction` is `above` or `below`; `window_points`; `min_frequency`. |
| `spike_drop_detection` | Detect residual or smoothed-trend spike/drop outliers after filtering normal fluctuation. Use for abrupt anomaly evidence. | Optional `box_scale`, `direction`, `window_size`, `residual_sen`, and `nonzero`. |
| `median_p75_statistics` | Median-smooth the series and compute baseline distribution statistics. Use when the diagnosis needs median and p75 values. | Optional `smoothing_time` in seconds; defaults to 900 seconds. |
| `rising_trend_detection` | Compare counts of rising and falling adjacent datapoint changes. Use when the diagnosis needs upward, downward, or unclear direction evidence. | No additional options. |
| `trend_prediction` | Use Prophet to forecast the next 168 hourly values from at least seven days of history. | No additional options. |

For `sliding_window_threshold_frequency_detection`, include:

```json
{
  "analysis": {
    "profile": "sliding_window_threshold_frequency_detection",
    "threshold": 80,
    "direction": "above",
    "window_points": 5,
    "min_frequency": 3
  }
}
```

## Result Contract

The script prints compact JSON only. It must not print raw datapoints.

```json
{
  "success": true,
  "metric_name": "cpu_util",
  "profile": "trend_prediction",
  "summary": "Forecasted the next seven days with Prophet.",
  "findings": [
    {
      "kind": "upward_trend",
      "severity": "warning",
      "metric_name": "cpu_util",
      "confidence": 1.0,
      "evidence": {
        "forecast_hours": 168,
        "start_time": 1784768400000,
        "end_time": 1785369600000,
        "first_predicted_value": 40.2,
        "last_predicted_value": 53.8,
        "min_predicted_value": 39.5,
        "max_predicted_value": 56.1,
        "mean_predicted_value": 47.3,
        "change": 13.6,
        "change_ratio": 0.3383,
        "direction": "upward"
      }
    }
  ],
  "forecast": {
    "forecast_hours": 168,
    "start_time": 1784768400000,
    "end_time": 1785369600000,
    "first_predicted_value": 40.2,
    "last_predicted_value": 53.8,
    "min_predicted_value": 39.5,
    "max_predicted_value": 56.1,
    "mean_predicted_value": 47.3,
    "change": 13.6,
    "change_ratio": 0.3383,
    "direction": "upward"
  }
}
```

## Rules For Service Skills

- Call this skill/script only when time-series judgment is needed.
- Do not call CES raw APIs directly from service-category skills.
- Do not include raw datapoints in prompts, tool results, or final answers.
- Use `summary`, `findings`, and the optional `statistics` or `forecast` from the script output as evidence.
- If the script returns `data_fetch_failed`, stop and report that the internal CES MCP CLI adapter failed in this environment.
- If the script returns `query_too_large`, narrow the time range, increase `period`, or split by metric/time.

See [references/analysis-contract.md](references/analysis-contract.md) for the full `MetricAnalysisSpec`, `AnalysisResult`, cache behavior, and error contract.
