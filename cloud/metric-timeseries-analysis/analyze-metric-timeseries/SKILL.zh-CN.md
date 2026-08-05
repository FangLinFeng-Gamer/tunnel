---
name: analyze-metric-timeseries
description: 分析数据库和云服务诊断中的一个或两个云监控指标时序数据，包括阈值频次、突增/突降、异常关联、中位数与 p75、相邻点趋势和趋势预测。适用于诊断流程需要紧凑指标证据且不应将原始数据点放入模型上下文的场景。
---

# 分析指标时序数据

使用这个 skill 将指标查询转换为紧凑的诊断证据。内置脚本在内部获取 CES 数据、按指标独立缓存、执行一个分析 profile，并返回不包含原始数据点的结构化 JSON。

## 执行流程

1. 确认任务需要时序判断，而不是只查询当前值。
2. 根据诊断问题选择 profile。
3. 对数据库指标，填写 `metric.namespace`、`metric.metric_name` 或 `metric.dimensions` 前，先阅读 `references/ces-database-metric-parameters.zh-CN.md`。
4. 从用户输入或可信 tool 结果中收集资源标识、自然语言时间范围和其他输入。
5. 将用户时间范围解析为 `time_window.from` 和 `time_window.to`。
6. 按必填清单检查；存在缺失时，一次询问后停止。
7. 只有不清楚所选 profile 参数时才查看其帮助。
8. 将紧凑 JSON 放入 `--args`，按公开 CLI 准确调用一次。
9. 根据 `success` 或 `error` 分支处理，不得发明其他调用形式。

## 必填输入

执行前确认以下字段都有明确值：

- [ ] `region`
- [ ] `project_id`
- [ ] `metric.namespace`
- [ ] `metric.metric_name`，值为非空的准确指标 ID 数组
- [ ] 每个 `metric.dimensions[].name` 和 `.value`
- [ ] 用户可理解的时间范围，例如“最近一小时”或“昨天 09:00 到 12:00”
- [ ] `period`
- [ ] `analysis.profile`
- [ ] 使用 `sliding_window_threshold_frequency_detection` 时的 `analysis.threshold`
- [ ] 使用 `coincident_anomaly_detection` 时的 `analysis.time_point`

存在无法确定的必填值时，必须一次性向用户询问所有缺失字段。必填字段缺失时，不要运行或重试脚本。不得猜值或提交示例占位值。可选 profile 参数可以省略，由脚本应用默认值。

## 解析时间范围

构造 `MetricAnalysisSpec` 前，将用户的自然语言时间范围转换为整数毫秒时间戳：

- 相对时间表达以当前日期和时间为基准解析。
- 用户明确提供时区时使用该时区，否则使用会话或用户时区。
- 将解析后的起点写入 `time_window.from`，终点写入 `time_window.to`，并确保 `from < to`。
- 完全没有时间范围时，用自然语言询问用户需要分析哪个时间段。
- 时区或边界歧义会显著改变范围时，用自然语言向用户澄清。

不要让用户提供毫秒时间戳，也不要让用户自行完成转换。

## 选择 Profile

| Profile | 适用场景 |
| --- | --- |
| `sliding_window_threshold_frequency_detection` | 诊断需要判断指标高于或低于阈值的频次。 |
| `spike_drop_detection` | 诊断需要突增或突降证据。 |
| `coincident_anomaly_detection` | 诊断需要判断两个指标是否都在故障发生前出现异常。 |
| `median_p75_statistics` | 诊断需要中位数和 p75 基线。 |
| `rising_trend_detection` | 诊断需要根据相邻点变化判断上升、下降或方向不明确。 |
| `trend_prediction` | 诊断需要未来七天预测，并且已有至少七天历史数据。 |

不要猜测 profile 参数，只查看当前所选 profile：

```bash
python3 scripts/analyze_metric_timeseries.py profile <profile-name> --help
```

## 执行命令

严格按照以下对象结构构造输入。占位符只用于表示结构，不得原样提交：

```json
{
  "region": "<region>",
  "project_id": "<project-id>",
  "metric": {
    "namespace": "<namespace>",
    "metric_name": ["<metric-name>"],
    "dimensions": [{"name": "<dimension-name>", "value": "<dimension-value>"}]
  },
  "time_window": {"from": <resolved-ms>, "to": <resolved-ms>},
  "period": <period-seconds>,
  "analysis": {"profile": "<profile-name>"}
}
```

所选 profile 的参数只能添加在 `analysis` 中，且必须是文档中定义的参数。将全部占位符替换为明确值后，把对象序列化为紧凑 JSON：

除 `coincident_anomaly_detection` 必须传入两个指标名称外，其他 profile 只能传入一个指标名称。关联分析还要把自然语言故障时间解析为毫秒时间戳并写入 `analysis.time_point`；默认回看故障发生前 1800 秒。

```bash
python3 scripts/analyze_metric_timeseries.py \
  analyze --args '<MetricAnalysisSpec JSON>'
```

`--args` 接收 JSON 对象字符串，不接收文件路径，也不接收逐字段参数。

## 处理结果

- `success=true`：使用 `summary`、`findings` 以及可选的 `statistics` 或 `forecast` 作为诊断证据。
- `missing_required_input`：读取完整的 `missing_fields` 列表。先从可信上下文补充字段，再一次性向用户询问所有仍无法确定的值。在全部字段就绪前必须停止，不得再次调用脚本。
- 其他 `invalid_request`：根据 `message` 报告被拒绝的字段或参数。
- `query_too_large`：提高 `period` 或按时间拆分查询，同时保持用户的诊断意图。
- `data_fetch_failed`：停止并报告内部 CES MCP CLI 适配失败。
- `internal_error`：停止并报告分析内部失败。
- Argparse 退出码为 `2`：运行 `python3 scripts/analyze_metric_timeseries.py analyze --help`，按文档修正语法后只重试一次。

不要在 prompt、tool 结果或最终回答中包含原始数据点。

## 易错事项

- 内置路径相对于当前 skill 根目录执行。
- 运行环境需要 Python 3.10+、`requirements.txt` 中的依赖，以及已经配置好的 `huaweicloud-mcp` 命令。
- 脚本是唯一公开执行入口。不要使用 `python -c`，不要导入内部模块、实例化 profile 类或直接调用 CES。
- CES 分批获取、`average` 聚合方式、按指标独立的 dataset 存储、缓存策略和 cache key 都是内部实现。
- 维度名称由具体指标决定。只有目标 CES 指标定义了 `instance_id` 时才使用它。
- 失败后不要试探其他 Python import、类名、子命令或参数传递方式。

## 参考资料

对于华为云数据库指标，在选择 namespace、准确指标 ID、维度 key 或维度顺序前，阅读 `references/ces-database-metric-parameters.zh-CN.md`。

对于 RDS for MySQL 实例或数据库代理指标，阅读 `references/rds-mysql-metric-catalog.zh-CN.md`，将官方指标名称映射为准确指标 ID。

仅在以下情况读取 `references/analysis-contract.zh-CN.md`：

- 需要精确字段约束或 profile 默认参数；
- 需要解释 profile 特有的 `statistics`、`forecast` 或 finding evidence，或者涉及 CES 查询限制、缓存行为或完整错误契约。
