---
name: analyze-metric-timeseries
description: Analyzes cloud monitoring metric time series for database and service diagnostics, including threshold frequency, spike/drop anomalies, median and p75 baselines, direction-count rising trends, and trend forecasting. Use when a diagnostic workflow needs metric evidence from CES or similar monitoring data without placing raw datapoints in model context.
---

# Analyze Metric Time-Series

Use this skill to turn one cloud metric query into compact diagnostic evidence. The bundled script fetches CES data internally, caches it, runs one analysis profile, and returns structured JSON without exposing raw datapoints.

## Workflow

1. Confirm that the task needs time-series judgment rather than a current-value lookup.
2. Choose the profile that matches the diagnostic question.
3. For a database metric, read `references/ces-database-metric-parameters.md` before filling `metric.namespace`, `metric.metric_name`, or `metric.dimensions`.
4. Collect resource identifiers, a natural-language time range, and the remaining inputs from the user or trusted tool results.
5. Resolve the user's time range into `time_window.from` and `time_window.to`.
6. Check the required-input list. If anything is missing, ask once and stop.
7. Inspect profile help only when its options are unclear.
8. Run the public CLI exactly once with compact JSON in `--args`.
9. Branch on `success` or `error`; do not invent another calling convention.

## Required Inputs

Before execution, confirm concrete values for:

- [ ] `region`
- [ ] `project_id`
- [ ] `metric.namespace`
- [ ] `metric.metric_name`
- [ ] Every `metric.dimensions[].name` and `.value`
- [ ] A user-facing time range, such as "the last hour" or "yesterday from 09:00 to 12:00"
- [ ] `period`
- [ ] `analysis.profile`
- [ ] `analysis.threshold` when using `sliding_window_threshold_frequency_detection`

If any required value is unavailable, ask the user for all missing fields in one clarification. Do not run or retry the script while required fields are missing. Never invent values or submit example placeholders. Optional profile parameters may be omitted so the script applies its defaults.

## Resolve The Time Window

Convert the user's natural-language time range into integer millisecond timestamps before building `MetricAnalysisSpec`:

- Resolve relative expressions against the current date and time.
- Use an explicit user timezone when provided; otherwise use the session or user timezone.
- Set the resolved start to `time_window.from` and end to `time_window.to`, with `from < to`.
- If the range is missing, ask which period to analyze in natural language.
- If timezone or boundary ambiguity would materially change the range, ask a natural-language clarification.

Never ask the user to provide millisecond timestamps or perform the conversion.

## Choose A Profile

| Profile | Use when |
| --- | --- |
| `sliding_window_threshold_frequency_detection` | The diagnosis needs the frequency of values above or below a threshold. |
| `spike_drop_detection` | The diagnosis needs abrupt spike or drop evidence. |
| `median_p75_statistics` | The diagnosis needs median and p75 baseline values. |
| `rising_trend_detection` | The diagnosis needs upward, downward, or unclear direction from adjacent changes. |
| `trend_prediction` | The diagnosis needs a seven-day forecast and at least seven days of history are available. |

Do not guess profile options. Inspect only the selected profile:

```bash
python3 scripts/analyze_metric_timeseries.py profile <profile-name> --help
```

## Run

Build exactly this object shape. The placeholders show structure only; never submit them:

```json
{
  "region": "<region>",
  "project_id": "<project-id>",
  "metric": {
    "namespace": "<namespace>",
    "metric_name": "<metric-name>",
    "dimensions": [{"name": "<dimension-name>", "value": "<dimension-value>"}]
  },
  "time_window": {"from": <resolved-ms>, "to": <resolved-ms>},
  "period": <period-seconds>,
  "analysis": {"profile": "<profile-name>"}
}
```

Add only documented options for the selected profile under `analysis`. After replacing every placeholder with a concrete value, serialize the object as compact JSON:

```bash
python3 scripts/analyze_metric_timeseries.py \
  analyze --args '<MetricAnalysisSpec JSON>'
```

`--args` accepts a JSON object string, not a file path or individual field flags.

## Handle Results

- `success=true`: use `summary`, `findings`, and optional `statistics` or `forecast` as diagnostic evidence.
- `missing_required_input`: read the complete `missing_fields` list. Resolve fields from trusted context first, then ask the user for every still-unresolved value in one clarification. Because `retryable=false`, stop and do not call the script again until all values are available.
- Other `invalid_request`: report the rejected field or option from `message`.
- `query_too_large`: increase `period` or split the query by time; preserve the user's diagnostic intent.
- `data_fetch_failed`: stop and report that the internal CES MCP CLI adapter failed.
- `internal_error`: stop and report that analysis failed internally.
- Argparse exit code `2`: run `python3 scripts/analyze_metric_timeseries.py analyze --help`, correct the documented syntax, and retry once.

Never include raw datapoints in prompts, tool results, or final answers.

## Gotchas

- Run bundled paths relative to this skill's root.
- The environment needs Python 3.10+, packages from `requirements.txt`, and a configured `huaweicloud-mcp` command.
- The script is the only public execution entry point. Do not use `python -c`, import internal modules, instantiate profile classes, or call CES directly.
- CES fetching, the `average` aggregation filter, dataset storage, cache policy, and cache keys are internal.
- A dimension name is metric-specific. Use `instance_id` only when the target CES metric defines that dimension.
- Do not probe alternative Python imports, class names, subcommands, or parameter styles after a failure.

## References

For a Huawei Cloud database metric, read `references/ces-database-metric-parameters.md` before selecting the namespace, exact metric ID, dimension keys, or dimension order.

For an RDS for MySQL instance or database proxy metric, read
`references/rds-mysql-metric-catalog.md` to map the official metric name to the
exact metric ID.

Read `references/analysis-contract.md` only when:

- exact field constraints or profile defaults are needed;
- profile-specific `statistics`, `forecast`, or finding evidence must be interpreted;
- CES query limits, cache behavior, or the complete error contract is relevant.
